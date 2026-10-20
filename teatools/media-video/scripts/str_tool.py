#!/usr/bin/env python3
"""Inspect / decode / validate a PlayStation .STR video stream (MDEC BS v2),
the format TEA-Online's `extend/tools/media/video` encoder produces and the
one /DATA/MOVIE.STR uses on the Forbidden Memories disc.

Container (verified against the US disc, MOVIE.STR at LBA 202734):
  every 2048-byte sector starts with a 32-byte STR chunk header
      +0  u16  0x0160   magic
      +2  u16  0x8001   "video id"
      +4  u16  chunk index within the frame
      +6  u16  chunk count for the frame
      +8  u32  frame number (1-based)
      +12 u32  length in bytes of this frame's MDEC bitstream
      +16 u16  width          (320)
      +18 u16  height         (240)
      +20 8B   copy of the frame header below
      +28 4B   zero
  the remaining 2016 bytes are the frame's bitstream, split across `count`
  sectors.  The frame header (first 8 bytes of the reassembled bitstream) is
      +0  u16  number of 16-bit MDEC words: (codes+2, rounded up to 64) / 2
      +2  u16  0x3800   magic
      +4  u16  quantisation scale
      +6  u16  version  (2)
  followed by the big-endian-in-16-bit-words VLC bitstream: per block a 10-bit
  signed DC, then (run, level) AC codes, EOB = 0b10, end of stream = 0b0111111111.
  Blocks are Cr, Cb, Y0, Y1, Y2, Y3 per 16x16 macroblock, macroblocks in
  column-major order.

Commands
    info    <file>          census of sectors / frames / audio interleave
    decode  <file>          MDEC frames -> PNGs
    encode  <frame dir>     PNGs -> .STR   (the web tool's job, ported from its JS)
    check   <file>          will Forbidden Memories play this?
    extract <disc.bin>      pull MOVIE.STR out of a MODE2/2352 disc image

`encode` is a line-by-line port of the site's encoder (its S/Y/z/H/Z/ee/te): BT.601
colour, 2x2 chroma, the same fixed-point forward DCT, the same quant matrix, the
same PSX AC VLC table, and the same "smallest quant scale 1..63 that fits the
sector budget" search.  At the defaults (320x240, 15 fps, 2x CD) every frame gets
exactly 10 sectors.  It writes video only -- there is no XA audio, and the result
is a flat 2048-byte-per-sector payload, so putting it on a disc still needs an ISO
rebuild that adds Mode2 Form1 subheaders and EDC/ECC.

`file` may be a raw 2048-byte-per-sector .STR (what the web tool downloads and
what an ISO tool gives you) or a MODE2/2352 disc image plus --lba.
"""

import argparse
import os
import struct
import sys

import numpy as np

SECTOR = 2048
PAYLOAD = 2016
MOVIE_LBA = 202734           # /DATA/MOVIE.STR, US disc
MOVIE_SECTORS = 17300

# what the game itself demands, from SLUS_014.11 (see README):
GAME_SECTORS = 3080          # D_8009151C[0].size
GAME_FRAMES = 303            # D_8009151C[0].endFrame
GAME_W, GAME_H = 320, 240


# ------------------------------------------------------------------ reading --

def read_sectors(path, lba=None):
    """Yield 2048-byte sector payloads (+ submode byte when we can see one)."""
    size = os.path.getsize(path)
    raw = size % 2352 == 0 and size > 50 * 1024 * 1024
    with open(path, "rb") as fh:
        if not raw:
            while True:
                d = fh.read(SECTOR)
                if len(d) < SECTOR:
                    return
                yield d, None
        else:
            start = MOVIE_LBA if lba is None else lba
            for i in range(MOVIE_SECTORS):
                fh.seek((start + i) * 2352)
                s = fh.read(2352)
                if len(s) < 2352:
                    return
                yield s[24:24 + SECTOR], s[18]


def parse_header(payload):
    magic, vid, cn, cc, fn, blen, w, h = struct.unpack_from("<HHHHIIHH", payload)
    return dict(magic=magic, vid=vid, chunk=cn, chunks=cc, frame=fn,
                length=blen, w=w, h=h)


def frames(path, lba=None):
    """Reassemble frames: yield (header dict, bitstream bytes)."""
    cur, parts = None, []
    for payload, sub in read_sectors(path, lba):
        if sub is not None and sub not in (0x48, 0xC8):
            continue                                    # XA audio sector
        h = parse_header(payload)
        if h["magic"] != 0x0160:
            continue
        if h["chunk"] == 0:
            if parts:
                yield cur, b"".join(parts)
            cur, parts = h, []
        parts.append(payload[32:32 + PAYLOAD])
    if parts:
        yield cur, b"".join(parts)


# ---------------------------------------------------------------- MDEC VLC --

# [code_bits_without_sign, code_value, run, level] -- copied verbatim from the
# site's chunk, which is the standard PSX MDEC AC table.
AC_TABLE = [
    [2, 3, 0, 1], [3, 3, 1, 1], [4, 4, 0, 2], [4, 5, 2, 1], [5, 5, 0, 3],
    [5, 6, 4, 1], [5, 7, 3, 1], [6, 4, 7, 1], [6, 5, 6, 1], [6, 6, 1, 2],
    [6, 7, 5, 1], [7, 4, 2, 2], [7, 5, 9, 1], [7, 6, 0, 4], [7, 7, 8, 1],
    [8, 32, 13, 1], [8, 33, 0, 6], [8, 34, 12, 1], [8, 35, 11, 1], [8, 36, 3, 2],
    [8, 37, 1, 3], [8, 38, 0, 5], [8, 39, 10, 1], [10, 8, 16, 1], [10, 9, 5, 2],
    [10, 10, 0, 7], [10, 11, 2, 3], [10, 12, 1, 4], [10, 13, 15, 1],
    [10, 14, 14, 1], [10, 15, 4, 2], [12, 16, 0, 11], [12, 17, 8, 2],
    [12, 18, 4, 3], [12, 19, 0, 10], [12, 20, 2, 4], [12, 21, 7, 2],
    [12, 22, 21, 1], [12, 23, 20, 1], [12, 24, 0, 9], [12, 25, 19, 1],
    [12, 26, 18, 1], [12, 27, 1, 5], [12, 28, 3, 3], [12, 29, 0, 8],
    [12, 30, 6, 2], [12, 31, 17, 1], [13, 16, 10, 2], [13, 17, 9, 2],
    [13, 18, 5, 3], [13, 19, 3, 4], [13, 20, 2, 5], [13, 21, 1, 7],
    [13, 22, 1, 6], [13, 23, 0, 15], [13, 24, 0, 14], [13, 25, 0, 13],
    [13, 26, 0, 12], [13, 27, 26, 1], [13, 28, 25, 1], [13, 29, 24, 1],
    [13, 30, 23, 1], [13, 31, 22, 1], [14, 16, 0, 31], [14, 17, 0, 30],
    [14, 18, 0, 29], [14, 19, 0, 28], [14, 20, 0, 27], [14, 21, 0, 26],
    [14, 22, 0, 25], [14, 23, 0, 24], [14, 24, 0, 23], [14, 25, 0, 22],
    [14, 26, 0, 21], [14, 27, 0, 20], [14, 28, 0, 19], [14, 29, 0, 18],
    [14, 30, 0, 17], [14, 31, 0, 16], [15, 16, 0, 40], [15, 17, 0, 39],
    [15, 18, 0, 38], [15, 19, 0, 37], [15, 20, 0, 36], [15, 21, 0, 35],
    [15, 22, 0, 34], [15, 23, 0, 33], [15, 24, 0, 32], [15, 25, 1, 14],
    [15, 26, 1, 13], [15, 27, 1, 12], [15, 28, 1, 11], [15, 29, 1, 10],
    [15, 30, 1, 9], [15, 31, 1, 8], [16, 16, 1, 18], [16, 17, 1, 17],
    [16, 18, 1, 16], [16, 19, 1, 15], [16, 20, 6, 3], [16, 21, 16, 2],
    [16, 22, 15, 2], [16, 23, 14, 2], [16, 24, 13, 2], [16, 25, 12, 2],
    [16, 26, 11, 2], [16, 27, 31, 1], [16, 28, 30, 1], [16, 29, 29, 1],
    [16, 30, 28, 1], [16, 31, 27, 1],
]

QUANT = np.array([
    2, 16, 19, 22, 26, 27, 29, 34, 16, 16, 22, 24, 27, 29, 34, 37,
    19, 22, 26, 27, 29, 34, 34, 38, 22, 22, 26, 27, 29, 34, 37, 40,
    22, 26, 27, 29, 32, 35, 40, 48, 26, 27, 29, 32, 35, 40, 48, 58,
    26, 27, 29, 34, 38, 46, 56, 69, 27, 29, 35, 38, 46, 56, 69, 83],
    dtype=np.float64)

ZIGZAG = np.array([
    0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63])


def build_codes():
    codes = {}
    for bits, value, run, level in AC_TABLE:
        s = format(value, "0%db" % bits)
        codes[s] = (run, level)
    return codes


CODES = build_codes()
EOB = "10"
ESCAPE = "000001"
# 0b0111111111 is appended once after the last block as an end-of-stream marker.
# It is NOT prefix-free against the AC table ("011" is run=1 level=1), so a
# decoder must stop on the macroblock count, never on this pattern.
END = "0111111111"


class Bits:
    """MSB-first inside each little-endian 16-bit word."""

    def __init__(self, data):
        self.words = np.frombuffer(data[:len(data) // 2 * 2], "<u2")
        self.pos = 0

    def peek(self, n):
        out = []
        p = self.pos
        for _ in range(n):
            w, b = divmod(p, 16)
            if w >= len(self.words):
                break
            out.append("1" if (self.words[w] >> (15 - b)) & 1 else "0")
            p += 1
        return "".join(out)

    def take(self, n):
        s = self.peek(n)
        self.pos += len(s)
        return s


def _signed(bits):
    v = int(bits, 2)
    return v - (1 << len(bits)) if bits[0] == "1" else v


def decode_block(bs, qscale):
    coef = np.zeros(64)
    dc = bs.take(10)
    if len(dc) < 10:
        raise EOFError
    coef[0] = _signed(dc) * QUANT[0] * 8
    i = 1
    while True:
        window = bs.peek(16)
        if not window:
            raise EOFError
        if window.startswith(EOB):
            bs.take(2)
            return coef
        if window.startswith(ESCAPE):
            bs.take(6)
            run = int(bs.take(6), 2)
            level = _signed(bs.take(10))
        else:
            for n in range(2, 17):
                key = window[:n]
                if key in CODES:
                    run, level = CODES[key]
                    bs.take(n)
                    level = -level if bs.take(1) == "1" else level
                    break
            else:
                raise ValueError("bad VLC at bit %d: %s" % (bs.pos, window))
        i += run
        if i > 63:
            return coef
        coef[ZIGZAG[i]] = level * QUANT[ZIGZAG[i]] * qscale
        i += 1


_C = np.array([[(np.sqrt(1 / 8) if u == 0 else 0.5) *
                np.cos((2 * x + 1) * u * np.pi / 16)
                for x in range(8)] for u in range(8)])


def idct(coef):
    F = coef.reshape(8, 8) / 8.0
    return _C.T @ F @ _C


def decode_frame(payload, header=None):
    nwords, magic, qscale, version = struct.unpack_from("<HHHH", payload)
    if magic != 0x3800:
        raise ValueError("not an MDEC BS frame (magic %04x)" % magic)
    if version != 2:
        raise ValueError("only BS v2 is supported here (got v%d)" % version)
    w = header["w"] if header else GAME_W
    h = header["h"] if header else GAME_H
    mbx, mby = (w + 15) // 16, (h + 15) // 16
    bs = Bits(payload[8:])

    y = np.zeros((mby * 16, mbx * 16))
    cb = np.zeros((mby * 8, mbx * 8))
    cr = np.zeros((mby * 8, mbx * 8))
    try:
        for bx in range(mbx):                      # column-major macroblocks
            for by in range(mby):
                blocks = [idct(decode_block(bs, qscale)) for _ in range(6)]
                cr[by * 8:by * 8 + 8, bx * 8:bx * 8 + 8] = blocks[0]
                cb[by * 8:by * 8 + 8, bx * 8:bx * 8 + 8] = blocks[1]
                for k, (oy, ox) in enumerate(((0, 0), (0, 8), (8, 0), (8, 8))):
                    y[by * 16 + oy:by * 16 + oy + 8,
                      bx * 16 + ox:bx * 16 + ox + 8] = blocks[2 + k]
    except (StopIteration, EOFError):
        pass

    Y = y[:h, :w] + 128
    CB = np.repeat(np.repeat(cb, 2, 0), 2, 1)[:h, :w] + 128
    CR = np.repeat(np.repeat(cr, 2, 0), 2, 1)[:h, :w] + 128
    r = Y + 1.402 * (CR - 128)
    g = Y - 0.344136 * (CB - 128) - 0.714136 * (CR - 128)
    b = Y + 1.772 * (CB - 128)
    return np.clip(np.stack([r, g, b], -1), 0, 255).astype(np.uint8), qscale


# ------------------------------------------------------------------ commands --

def cmd_info(a):
    subs, dims, vers, qs = {}, {}, {}, []
    nvid = naud = 0
    order, seg_starts = [], []
    prev = None
    idx = -1
    for payload, sub in read_sectors(a.file, a.lba):
        idx += 1
        if sub is not None:
            subs[sub] = subs.get(sub, 0) + 1
            if sub not in (0x48, 0xC8):
                naud += 1
                continue
        h = parse_header(payload)
        if h["magic"] != 0x0160:
            continue
        nvid += 1
        dims[(h["w"], h["h"])] = dims.get((h["w"], h["h"]), 0) + 1
        if h["chunk"] == 0:
            if prev is not None and h["frame"] <= prev:
                seg_starts.append(idx)
            prev = h["frame"]
            order.append(h["frame"])
            _n, _m, q, v = struct.unpack_from("<HHHH", payload, 20)
            vers[v] = vers.get(v, 0) + 1
            qs.append(q)
    print(f"{a.file}")
    print(f"  sectors           {idx + 1}")
    if subs:
        print(f"  submodes          " +
              ", ".join(f"0x{k:02X}={v}" for k, v in sorted(subs.items())) +
              "   (0x48 video, 0x64 XA audio, 0xC8 video+EOF)")
    print(f"  video sectors     {nvid}   audio sectors {naud}")
    print(f"  frames            {len(order)}  (max frame number {max(order) if order else 0})")
    print(f"  dimensions        " + ", ".join(f"{w}x{h} x{n}" for (w, h), n in dims.items()))
    print(f"  BS version        " + ", ".join(f"v{k} x{v}" for k, v in vers.items()))
    if qs:
        print(f"  quant scale       {min(qs)}..{max(qs)}")
    if seg_starts:
        print(f"  stream restarts   at sector(s) {seg_starts}"
              f"  -> {len(seg_starts) + 1} copies of the same movie")
    if nvid:
        print(f"  at 2x CD (150 sectors/s): {(idx + 1) / 150:.2f} s of stream")


def cmd_check(a):
    ok = True
    n = 0
    fr = []
    for h, payload in frames(a.file, a.lba):
        n += 1
        fr.append(h)
    total = sum(1 for _ in read_sectors(a.file, a.lba))
    print(f"{a.file}: {total} sectors, {n} frames")
    for cond, msg in (
        (total >= GAME_SECTORS,
         f"needs >= {GAME_SECTORS} sectors (the game reads that many)"),
        (n >= GAME_FRAMES,
         f"needs >= {GAME_FRAMES} frames (StSetStream end frame)"),
        (all(h["w"] == GAME_W and h["h"] == GAME_H for h in fr),
         f"every frame must be {GAME_W}x{GAME_H}"),
    ):
        if not cond:
            ok = False
            print(f"  FAIL: {msg}")
    if fr:
        chunks = {h["chunks"] for h in fr}
        print(f"  chunks per frame: {sorted(chunks)} "
              f"(10 sectors/frame at 15 fps / 2x CD, XA audio included)")
    print("  OK" if ok else "  NOT PLAYABLE as-is")
    return 0 if ok else 1


def cmd_decode(a):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("needs Pillow for decode")
    os.makedirs(a.out, exist_ok=True)
    n = 0
    for h, payload in frames(a.file, a.lba):
        if a.skip and h["frame"] <= a.skip:
            continue
        rgb, q = decode_frame(payload, h)
        Image.fromarray(rgb).save(os.path.join(a.out, "frame%04d.png" % h["frame"]))
        n += 1
        if n >= a.count:
            break
    print(f"decoded {n} frame(s) into {a.out}")


def cmd_extract(a):
    with open(a.file, "rb") as fh, open(a.out, "wb") as out:
        for i in range(MOVIE_SECTORS):
            fh.seek((MOVIE_LBA + i) * 2352 + 24)
            out.write(fh.read(SECTOR))
    print(f"wrote {a.out} ({MOVIE_SECTORS * SECTOR} bytes)")



# =========================================================== ENCODER (BS v2) ==
# Straight port of the site's chunk (functions S, Y, z, H, Z, ee, te).  Every
# constant below is copied verbatim from the JavaScript.

# N: the site's fixed-point DCT basis (its `N`), 8x8, row u / column x.
DCT_N = np.array([
    23170, 23170, 23170, 23170, 23170, 23170, 23170, 23170,
    32138, 27245, 18204, 6392, -6392, -18204, -27245, -32138,
    30273, 12539, -12539, -30273, -30273, -12539, 12539, 30273,
    27245, -6392, -32138, -18204, 18204, 32138, 6392, -27245,
    23170, -23170, -23170, 23170, 23170, -23170, -23170, 23170,
    18204, -32138, 6392, 27245, -27245, -6392, 32138, -18204,
    12539, -30273, 30273, -12539, -12539, 30273, -30273, 12539,
    6392, -18204, 27245, -32138, 32138, -27245, 18204, -6392,
], dtype=np.int64).reshape(8, 8)


def _fdct(block):
    """The chunk's z(): in-place integer forward DCT of one 8x8 block."""
    e = block.astype(np.int64).reshape(8, 8)
    # pass 1: t[n][r] = ((sum_o trunc(e[r][o]*N[n][o]/8)) + 4095) >> 13
    prod = e[None, :, :] * DCT_N[:, None, :]                 # [n][r][o]
    prod = np.trunc(prod / 8).astype(np.int64)
    t = (prod.sum(axis=2) + 4095) >> 13                      # [n][r]
    # pass 2: e[i][s] = int16((sum_l t[s][l]*N[i][l]) + 4095 >> 13)
    prod2 = t[None, :, :] * DCT_N[:, None, :]                # [i][s][l]
    u = (prod2.sum(axis=2) + 4095) >> 13                     # [i][s]
    u = ((u & 0xFFFF) ^ 0x8000) - 0x8000                     # <<16>>16
    return u.reshape(64)


def _build_vlc():
    """The chunk's V(): (run, level) -> (bits, value), sign appended as LSB."""
    out = {}
    for bits, value, run, level in AC_TABLE:
        out[(run, level)] = (bits + 1, value << 1)
        out[(run, -level)] = (bits + 1, value << 1 | 1)
    return out


VLC = _build_vlc()


def _vlc(run, level):
    """The chunk's q(): table hit, or the 22-bit escape 000001 rrrrrr llllllllll."""
    hit = VLC.get((run, level))
    if hit:
        return hit
    return 22, 0x10000 | ((run << 10) | (level & 1023))


class BitWriter:
    """The chunk's H: 16 bits MSB-first per word, words stored little-endian."""

    def __init__(self, buf, max_size, used):
        self.buf, self.max = buf, max_size
        self.used = used
        self.value = 0
        self.left = 16

    def flush(self):
        if self.left < 16:
            if self.used >= self.max:
                return False
            self.buf[self.used] = self.value & 0xFF
            self.used += 1
            if self.used >= self.max:
                return False
            self.buf[self.used] = (self.value >> 8) & 0xFF
            self.used += 1
        self.left, self.value = 16, 0
        return True

    def write(self, nbits, value):
        value &= 0xFFFFFFFF
        if nbits > 16:
            if not self.write(nbits - 16, value >> 16):
                return False
            nbits, value = 16, value & 0xFFFF
        if self.left == 0 and not self.flush():
            return False
        while nbits > self.left:
            self.value = (self.value | ((value >> (nbits - self.left)) & 0xFFFF)) & 0xFFFF
            nbits -= self.left
            value &= (1 << nbits) - 1
            if not self.flush():
                return False
        if nbits >= 1:
            self.value = (self.value | ((value << (self.left - nbits)) & 0xFFFF)) & 0xFFFF
            self.left -= nbits
        return True


def _round_half_away(num, den):
    """The chunk's K(): round-half-away-from-zero of num/den."""
    q = num / den
    return int(np.floor(q + 0.5)) if q >= 0 else int(np.ceil(q - 0.5))


def _clamp_coef(v):
    """The chunk's Q(): int16 wrap, then clamp to [-512, 510]."""
    v = ((int(v) & 0xFFFF) ^ 0x8000) - 0x8000
    return -512 if v < -512 else (510 if v > 510 else v)


def rgb_to_planes(rgb, w, h):
    """The chunk's S(): RGB -> full-res luma + 2x2-subsampled interleaved Cr/Cb."""
    a = rgb.astype(np.float64)
    y = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    y = np.clip(np.round(y), 0, 255).astype(np.uint8)
    q = a.reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3))
    r, g, b = q[:, :, 0], q[:, :, 1], q[:, :, 2]
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b + 128
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b + 128
    c = np.zeros((h // 2, w), np.uint8)
    c[:, 0::2] = np.clip(np.round(cr), 0, 255).astype(np.uint8)
    c[:, 1::2] = np.clip(np.round(cb), 0, 255).astype(np.uint8)
    return y, c


def macroblocks(y, c, w, h):
    """The chunk's Y(): [Cr, Cb, Y00, Y01, Y10, Y11] per MB, column-major."""
    out = []
    for bx in range((w + 15) // 16):
        for by in range((h + 15) // 16):
            cr = c[by * 8:by * 8 + 8, bx * 16:bx * 16 + 16:2].astype(np.int64) - 128
            cb = c[by * 8:by * 8 + 8, bx * 16 + 1:bx * 16 + 16:2].astype(np.int64) - 128
            blocks = [cr.reshape(64), cb.reshape(64)]
            for oy, ox in ((0, 0), (0, 8), (8, 0), (8, 8)):
                blocks.append((y[by * 16 + oy:by * 16 + oy + 8,
                                 bx * 16 + ox:bx * 16 + ox + 8].astype(np.int64)
                               - 128).reshape(64))
            out.append(blocks)
    return out


def _encode_block(bw, coef, qtab):
    """The chunk's Z(). Returns the code count, or None if the budget ran out."""
    dc = _clamp_coef(_round_half_away(coef[0], qtab[0]))
    if not bw.write(10, dc & 1023):
        return None
    run, n = 0, 0
    for i in range(1, 64):
        s = ZIGZAG[i]
        v = _clamp_coef(_round_half_away(coef[s], qtab[s]))
        if v == 0:
            run += 1
        else:
            bits, value = _vlc(run, v)
            if not bw.write(bits, value):
                return None
            run, n = 0, n + 1
    if not bw.write(2, 2):                       # EOB = "10"
        return None
    return n + 2


def encode_frame(mbs, budget):
    """The chunk's ee(): smallest quant scale 1..63 that fits `budget` bytes."""
    dct = [[_fdct(b) for b in mb] for mb in mbs]
    for scale in range(1, 64):
        qtab = np.empty(64, np.int64)
        qtab[0] = 8 * int(QUANT[0])
        qtab[1:] = QUANT[1:].astype(np.int64) * scale
        buf = bytearray(budget + 4)
        bw = BitWriter(buf, budget, 8)
        codes, ok = 0, True
        for mb in dct:
            for blk in mb:
                got = _encode_block(bw, blk, qtab)
                if got is None:
                    ok = False
                    break
                codes += got
            if not ok:
                break
        if ok and bw.write(10, 511) and bw.flush():          # end-of-stream
            codes = (codes + 2 + 63) & ~63
            nwords = (codes + 1) >> 1
            out = bytearray(buf[:budget])
            struct.pack_into("<HHHH", out, 0, nwords, 0x3800, scale, 2)
            return bytes(out), scale, (bw.used + 3) & ~3
    raise RuntimeError("no quant scale 1..63 fits the per-frame byte budget "
                       "(lower the fps or raise the CD speed)")


def mux_str(frames_rgb, w, h, fps=15, cd_speed=2, video_id=0x8001, log=None):
    """The chunk's te(): frames -> a flat stream of 2048-byte STR sectors."""
    if w % 16 or h % 16:
        raise ValueError("width/height must be multiples of 16")
    per_sec = 75 * cd_speed                    # sectors the drive delivers per second
    out = bytearray()
    acc = pos = budget = 0
    frame_no = 0
    src = 0
    payload = b""
    used = 0
    done = False
    while not done or pos < budget:
        while pos >= budget:
            if src >= len(frames_rgb):
                done = True
                break
            frame_no += 1
            acc += per_sec
            budget = PAYLOAD * (acc // fps)
            acc %= fps
            pos = 0
            y, c = rgb_to_planes(frames_rgb[src], w, h)
            src += 1
            if src >= len(frames_rgb):
                done = True
            payload, _scale, used = encode_frame(macroblocks(y, c, w, h), budget)
            if log:
                log(frame_no, len(frames_rgb))
        if pos >= budget:
            break
        head = bytearray(32)
        struct.pack_into("<HHHHIIHH", head, 0, 0x0160, video_id,
                         pos // PAYLOAD, budget // PAYLOAD, frame_no, used, w, h)
        head[20:28] = payload[:8]
        sec = bytearray(SECTOR)
        sec[:32] = head
        sec[32:32 + PAYLOAD] = payload[pos:pos + PAYLOAD]
        out += sec
        pos += PAYLOAD
    return bytes(out)


def cmd_encode(a):
    try:
        from PIL import Image
    except ImportError:
        sys.exit("needs Pillow for encode")
    names = sorted(n for n in os.listdir(a.frames)
                   if n.lower().endswith((".png", ".bmp", ".jpg", ".jpeg")))
    if not names:
        sys.exit(f"no images in {a.frames}")
    limit = int(a.seconds * a.fps)
    names = names[:limit]
    pics = []
    for n in names:
        im = Image.open(os.path.join(a.frames, n)).convert("RGB")
        if im.size != (a.width, a.height):       # the site letterboxes, keeping AR
            s = min(a.width / im.width, a.height / im.height)
            nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
            bg = Image.new("RGB", (a.width, a.height), (0, 0, 0))
            bg.paste(im.resize((nw, nh), Image.LANCZOS),
                     ((a.width - nw) // 2, (a.height - nh) // 2))
            im = bg
        pics.append(np.asarray(im))
    print(f"encoding {len(pics)} frame(s) {a.width}x{a.height} "
          f"@ {a.fps} fps, {a.cd_speed}x CD")
    data = mux_str(pics, a.width, a.height, a.fps, a.cd_speed,
                   log=lambda i, n: print(f"  frame {i}/{n}", end="\r", flush=True))
    with open(a.out, "wb") as fh:
        fh.write(data)
    print(f"\nwrote {a.out}: {len(data)} bytes / {len(data) // SECTOR} sectors")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lba", type=int, default=None,
                   help="start LBA when reading a MODE2/2352 disc image")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("info");    q.add_argument("file"); q.set_defaults(fn=cmd_info)
    q = sub.add_parser("check");   q.add_argument("file"); q.set_defaults(fn=cmd_check)
    q = sub.add_parser("decode")
    q.add_argument("file")
    q.add_argument("--out", default="frames")
    q.add_argument("--count", type=int, default=1)
    q.add_argument("--skip", type=int, default=0)
    q.set_defaults(fn=cmd_decode)
    q = sub.add_parser("encode", help="PNG frames -> .STR (the web tool's job)")
    q.add_argument("frames", help="directory of numbered frame images")
    q.add_argument("--out", default="MOVIE.STR")
    q.add_argument("--width", type=int, default=320)
    q.add_argument("--height", type=int, default=240)
    q.add_argument("--fps", type=int, default=15)
    q.add_argument("--cd-speed", type=int, default=2, dest="cd_speed")
    q.add_argument("--seconds", type=float, default=22.0)
    q.set_defaults(fn=cmd_encode)
    q = sub.add_parser("extract")
    q.add_argument("file", help="MODE2/2352 disc image")
    q.add_argument("--out", default="MOVIE.STR")
    q.set_defaults(fn=cmd_extract)

    a = p.parse_args()
    # --lba is a top-level flag; make it visible to the subcommand namespace
    sys.exit(a.fn(a) or 0)


if __name__ == "__main__":
    main()
