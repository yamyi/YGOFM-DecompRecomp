#!/usr/bin/env python3
"""Offline clone of TEA-Online "Memorycard name modifier" (extend/services/memorycard/name).

Works on a raw PS1 memory-card image (.mcr/.mcd/.mem, 128 KiB; 16 x 8 KiB blocks,
block 0 = directory).  Finds the Forbidden Memories save(s) by the directory entry's
product string (BASLUS-01411-YUGIOH for the US original; mods use other strings), shows
or replaces the 6-character player name at save-block offset 0x60C, and re-seals the
block so the game's loader accepts it.

Two sealing modes:

  proper  (default)  Recompute exactly what the game's own writer does
                     (func_8003CF14 + func_8003CFC8 in SLUS_014.11): CRC-16/XMODEM of
                     each of the three protected regions, the CRC stored twice as u16,
                     and the xorshift words that follow each region, then refresh the
                     mirror copy at block+0x880.  Verified byte-for-byte against a real
                     save written by the game.
  bypass             What the web tool does ("Yusaku CRC bypass"): zero the eight
                     xorshift words of region 3 (0x808..0x827) and the CRC slot 0x804,
                     and write CRC16(0x600..0x801) big-endian into 0x802 so that the
                     CRC of the whole region 0x600..0x803 is 0, which seeds the PRNG
                     with 0 and makes it emit zeros.  Only region 3 is touched (the name
                     lives there).  The mirror at +0x880 is left stale, as the site does.

Usage:
  mc_name.py list   CARD                    show FM saves and their names / checks
  mc_name.py verify CARD [--block N]        run the game's verifier on a block
  mc_name.py set    CARD NAME [--block N] [--bypass] [-o OUT]
  mc_name.py seal   CARD [--block N] [-o OUT]   re-seal without changing the name
  mc_name.py restore CARD --from STOCK [-o OUT] copy the stock block back (byte-exact)

Never run it on your only copy.
"""
import argparse
import shutil
import struct
import sys

BLOCK = 0x2000
SAVE = 0x200            # save struct starts after the 0x200 PS1 frame header
NAME_OFF = 0x60C        # block-relative; 6 x u16 Shift-JIS, 0 = end/space
MIRROR = 0x880          # func_8003D03C copies 0x680 bytes from +0x200 to +0x880
PRODUCT_US = b"BASLUS-01411-YUGIOH"

# ---------------------------------------------------------------- game algorithms

def crc16_xmodem(data: bytes) -> int:
    """func_8003CEB8: CRC-16, poly 0x1021, init 0, no reflection, no xorout."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


class Rng:
    """func_8003CE74: two-word xorshift-style generator, state D_8009AF64 (a) / D_8009AF68 (b)."""

    def __init__(self, seed16: int):
        self.a = self.b = (seed16 | (seed16 << 16)) & 0xFFFFFFFF

    def next(self) -> int:
        s0, s1 = self.a, self.b
        t = (((s1 << 31) | (s0 >> 1)) ^ (s0 << 12)) & 0xFFFFFFFF
        newb = (s1 + (s1 + (s0 & 1))) & 0xFFFFFFFF
        t ^= t >> 20
        self.b = newb
        self.a = t
        return t


# (data offset, data length, crc slot, first prng word (highest address), word count)
# offsets are relative to the save struct (block + 0x200)
REGIONS = [
    (0x000, 0x340, 0x37C, 0x378, 15),   # func_8003CF14 block 1
    (0x380, 0x06C, 0x3FC, 0x3F8, 4),    # func_8003CF14 block 2
    (0x400, 0x204, 0x604, 0x624, 8),    # func_8003CFC8
]


def seal_region(blk: bytearray, region) -> None:
    doff, dlen, crcslot, first, count = region
    base = SAVE
    crc = crc16_xmodem(bytes(blk[base + doff: base + doff + dlen]))
    struct.pack_into("<HH", blk, base + crcslot, crc, crc)
    rng = Rng(crc)
    p = base + first
    for _ in range(count):
        struct.pack_into("<I", blk, p, rng.next())
        p -= 4


def verify_region(blk: bytes, region):
    """func_8003D174 semantics: seed with the CRC, compare the words.  Returns (ok, crc)."""
    doff, dlen, _crcslot, first, count = region
    base = SAVE
    crc = crc16_xmodem(blk[base + doff: base + doff + dlen])
    rng = Rng(crc)
    p = base + first
    for _ in range(count):
        if struct.unpack_from("<I", blk, p)[0] != rng.next():
            return False, crc
        p -= 4
    return True, crc


def verify_block(blk: bytes):
    return [verify_region(blk, r) for r in REGIONS]


def seal_block_proper(blk: bytearray) -> None:
    for r in REGIONS:
        seal_region(blk, r)
    blk[MIRROR: MIRROR + 0x680] = blk[SAVE: SAVE + 0x680]


def seal_block_bypass(blk: bytearray) -> None:
    # site: setUint16(block+0x802, crc, big-endian); zero 9 u32 at 0x804..0x827
    crc = crc16_xmodem(bytes(blk[0x600:0x802]))
    struct.pack_into(">H", blk, 0x802, crc)
    blk[0x804:0x828] = bytes(0x24)


# ---------------------------------------------------------------- name codec (site's table)

def sjis_of(ch: str) -> int:
    if ch == " ":
        return 0
    b = ch.encode("shift_jis", errors="strict")
    # the game stores full-width forms: ASCII letters/digits -> 0x82xx, symbols -> 0x81xx
    if len(b) == 1:
        fw = ch.translate(str.maketrans(
            "".join(chr(c) for c in range(0x21, 0x7F)),
            "".join(chr(c + 0xFEE0) for c in range(0x21, 0x7F))))
        b = fw.encode("shift_jis")
    return (b[0] << 8) | b[1]


def name_decode(blk: bytes) -> str:
    out = ""
    for i in range(6):
        w = struct.unpack_from("<H", blk, NAME_OFF + 2 * i)[0]
        if w == 0:
            out += " "
            continue
        try:
            out += bytes([w >> 8, w & 0xFF]).decode("shift_jis")
        except UnicodeDecodeError:
            out += "?"
    return out.rstrip()


def name_encode(name: str) -> bytes:
    name = (name + "      ")[:6]
    return b"".join(struct.pack("<H", sjis_of(c)) for c in name)


# ---------------------------------------------------------------- card helpers

def load(path):
    d = bytearray(open(path, "rb").read())
    if len(d) != 16 * BLOCK or d[:2] != b"MC":
        sys.exit(f"{path}: not a raw 128 KiB PS1 memory card image")
    return d


def fm_blocks(card):
    """yield (block_no, product string) for directory entries that look like FM saves."""
    for n in range(1, 16):
        fr = card[0x80 * n: 0x80 * n + 0x80]
        state = fr[0]
        if state not in (0x51,):          # 0x51 = first block of a file; FM uses 1 block
            continue
        prod = bytes(fr[0x0A:0x1E]).split(b"\0")[0]
        if b"YUGIOH" in prod or prod.startswith(b"BASLUS-01411"):
            yield n, prod.decode("ascii", "replace")


def pick_block(card, want):
    blocks = list(fm_blocks(card))
    if want is not None:
        if want not in [b for b, _ in blocks]:
            print(f"warning: block {want} is not a recognised FM save; using it anyway", file=sys.stderr)
        return want
    if not blocks:
        sys.exit("no Forbidden Memories save found in the directory")
    if len(blocks) > 1:
        sys.exit("several FM saves; pick one with --block: " + ", ".join(f"{b} ({p})" for b, p in blocks))
    return blocks[0][0]


def block_view(card, n):
    return card[BLOCK * n: BLOCK * (n + 1)]


def report(card, n):
    blk = bytes(block_view(card, n))
    title = blk[4:0x44].decode("shift_jis", "replace").rstrip("\0 　")
    print(f"block {n}: title {title!r}")
    print(f"  name      : {name_decode(blk)!r}   raw {blk[NAME_OFF:NAME_OFF+12].hex(' ')}")
    for (doff, dlen, crcslot, first, count), (ok, crc) in zip(REGIONS, verify_block(blk)):
        stored = struct.unpack_from("<H", blk, SAVE + crcslot)[0]
        print(f"  region {doff+SAVE:03X}..{doff+SAVE+dlen-1:03X}: crc {crc:04X} stored {stored:04X} "
              f"words@{SAVE+first-4*(count-1):03X}..{SAVE+first+3:03X} {'OK' if ok else 'BAD'}")
    mirror_ok = blk[MIRROR:MIRROR + 0x680] == blk[SAVE:SAVE + 0x680]
    print(f"  mirror +0x880 {'matches' if mirror_ok else 'DIFFERS'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("card")
    p = sub.add_parser("verify"); p.add_argument("card"); p.add_argument("--block", type=int)
    p = sub.add_parser("set"); p.add_argument("card"); p.add_argument("name")
    p.add_argument("--block", type=int); p.add_argument("--bypass", action="store_true"); p.add_argument("-o", "--out")
    p = sub.add_parser("seal"); p.add_argument("card"); p.add_argument("--block", type=int); p.add_argument("-o", "--out")
    p = sub.add_parser("restore"); p.add_argument("card"); p.add_argument("--from", dest="stock", required=True)
    p.add_argument("--block", type=int); p.add_argument("-o", "--out")
    a = ap.parse_args()

    card = load(a.card)
    if a.cmd == "list":
        for n, prod in fm_blocks(card):
            print(f"[{prod}]")
            report(card, n)
        return
    n = pick_block(card, a.block)
    if a.cmd == "verify":
        report(card, n)
        return sys.exit(0 if all(ok for ok, _ in verify_block(bytes(block_view(card, n)))) else 1)

    out = a.out or a.card
    if a.cmd == "restore":
        stock = load(a.stock)
        card[BLOCK * n: BLOCK * (n + 1)] = stock[BLOCK * n: BLOCK * (n + 1)]
        open(out, "wb").write(card)
        print(f"block {n} restored from {a.stock} -> {out}")
        return

    blk = block_view(card, n)
    if a.cmd == "set":
        if len(a.name) > 6:
            sys.exit("name is at most 6 characters (the game's entry screen types 5)")
        bad = [c for c in a.name if c != " " and c not in
               "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-*/&$%!?.:"]
        if bad:
            print(f"warning: {bad} are outside the site's letter grid; encoded as full-width Shift-JIS anyway", file=sys.stderr)
        blk[NAME_OFF:NAME_OFF + 12] = name_encode(a.name)
        # keep the name-derived game id in step? No: the game only derives 0x534 at name entry (F135); leave it.
    if a.cmd == "set" and a.bypass:
        seal_block_bypass(blk)
    else:
        seal_block_proper(blk)
    card[BLOCK * n: BLOCK * (n + 1)] = blk
    open(out, "wb").write(card)
    report(card, n)
    print(f"written {out}")


if __name__ == "__main__":
    main()
