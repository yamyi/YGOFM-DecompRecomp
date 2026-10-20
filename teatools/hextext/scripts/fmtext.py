#!/usr/bin/env python3
"""Forbidden Memories text codec -- the charset and control codes behind TEA-Online's
"hextext" tool (route extend/tools/hextext), rebuilt from the game itself.

Charset: byte -> character, taken from gText_adwGlyphCodeTable (0x801D9000 in SLUS_014.11,
file 0x1C9800): one u32 per glyph, low 16 bits = the Shift-JIS code the glyph draws.  92
entries (0x00..0x5B); 0x00 is the space.  The table is frequency-ordered (e t a o i n s r h l).
Control bytes are 0xF6..0xFF (the typewriter TextBox_BuildStep dispatches 0xF0..0xFF through
the 16-entry table at 0x80090F18; 0xF0..0xF5 share a stub).  Bytes 0x5C..0xEF are unassigned
glyph slots.  The argument shapes below are the site's decoder (V.230825) cross-checked with
decomp findings F96/F103/F114/F116/F130/F131.

Importable:
    from fmtext import CHARSET, encode, decode, iter_tokens, bank_string, bank_strings
CLI:
    fmtext.py charset [SLUS]              print the table (from the EXE if given, else built-in)
    fmtext.py decode  SLUS (ID|0xOFF) ... decode bank strings by id (0x801C0000 table) or bank offset
    fmtext.py dump    SLUS [--table 0x801C0000|0x801C0800] [--from N --to M]
    fmtext.py encode  "text" [--terminate]  -> hex bytes
    fmtext.py patch   SLUS 0xBANKOFF "text" [--terminate] [-o OUT]   write encoded text into the bank
    fmtext.py find    SLUS "text"         search the bank for encoded text
"""
import argparse
import struct
import sys

# ------------------------------------------------------------------ constants
BANK_RAM = 0x801B0000
BANK_FILE = 0x1A0800                 # RAM = 0x80010000 + (file - 0x800)
OFFSETS_RAM = 0x801C0000             # u16 per string id (screen bank), 1100 entries used
OFFSETS2_RAM = 0x801C0800            # u16 per campaign text id (259 entries), = string id 1024+
GLYPH_TABLE_RAM = 0x801D9000
GLOBAL_OFFSETS_RAM = 0x801D5800      # ids >= 0x8000: base 0x801D0000 (card/location names)


def ram2file(ram):
    return ram - 0x80010000 + 0x800


# Built-in copy of the decoded glyph table (verified against the retail EXE).
CHARSET = {
    0x00: " ", 0x01: "e", 0x02: "t", 0x03: "a", 0x04: "o", 0x05: "i", 0x06: "n", 0x07: "s",
    0x08: "r", 0x09: "h", 0x0A: "l", 0x0B: ".", 0x0C: "d", 0x0D: "u", 0x0E: "m", 0x0F: "c",
    0x10: "g", 0x11: "y", 0x12: "w", 0x13: "f", 0x14: "p", 0x15: "b", 0x16: "k", 0x17: "!",
    0x18: "A", 0x19: "v", 0x1A: "I", 0x1B: "'", 0x1C: "T", 0x1D: "S", 0x1E: "M", 0x1F: ",",
    0x20: "D", 0x21: "O", 0x22: "W", 0x23: "H", 0x24: "Y", 0x25: "E", 0x26: "R", 0x27: "<<",
    0x28: ">>", 0x29: "G", 0x2A: "L", 0x2B: "C", 0x2C: "N", 0x2D: "B", 0x2E: "?", 0x2F: "P",
    0x30: "-", 0x31: "F", 0x32: "z", 0x33: "K", 0x34: "j", 0x35: "U", 0x36: "x", 0x37: "q",
    0x38: "0", 0x39: "V", 0x3A: "2", 0x3B: "J", 0x3C: "#", 0x3D: "1", 0x3E: "Q", 0x3F: "Z",
    0x40: '"', 0x41: "3", 0x42: "5", 0x43: "&", 0x44: "/", 0x45: "7", 0x46: "X", 0x47: "·",
    0x48: ":", 0x49: "♀", 0x4A: "4", 0x4B: ")", 0x4C: "(", 0x4D: "♂", 0x4E: "6",
    0x4F: "$", 0x50: "*", 0x51: ">", 0x52: "⊂", 0x53: "⊃", 0x54: "<", 0x55: "α",
    0x56: "+", 0x57: "8", 0x58: "←", 0x59: "9", 0x5A: "→", 0x5B: "%",
}
# Shift-JIS codes the glyphs draw (low half of the table words), for reference / encoding names.
SJIS = {
    0x01: 0x8285, 0x02: 0x8294, 0x03: 0x8281, 0x04: 0x828F, 0x05: 0x8289, 0x06: 0x828E, 0x07: 0x8293,
    0x08: 0x8292, 0x09: 0x8288, 0x0A: 0x828C, 0x0B: 0x8144, 0x0C: 0x8284, 0x0D: 0x8295, 0x0E: 0x828D,
    0x0F: 0x8283, 0x10: 0x8287, 0x11: 0x8299, 0x12: 0x8297, 0x13: 0x8286, 0x14: 0x8290, 0x15: 0x8282,
    0x16: 0x828B, 0x17: 0x8149, 0x18: 0x8260, 0x19: 0x8296, 0x1A: 0x8268, 0x1B: 0x8166, 0x1C: 0x8273,
    0x1D: 0x8272, 0x1E: 0x826C, 0x1F: 0x8143, 0x20: 0x8263, 0x21: 0x826E, 0x22: 0x8276, 0x23: 0x8267,
    0x24: 0x8278, 0x25: 0x8264, 0x26: 0x8271, 0x27: 0x8173, 0x28: 0x8174, 0x29: 0x8266, 0x2A: 0x826B,
    0x2B: 0x8262, 0x2C: 0x826D, 0x2D: 0x8261, 0x2E: 0x8148, 0x2F: 0x826F, 0x30: 0x817C, 0x31: 0x8265,
    0x32: 0x829A, 0x33: 0x826A, 0x34: 0x828A, 0x35: 0x8274, 0x36: 0x8298, 0x37: 0x8291, 0x38: 0x824F,
    0x39: 0x8275, 0x3A: 0x8251, 0x3B: 0x8269, 0x3C: 0x8194, 0x3D: 0x8250, 0x3E: 0x8270, 0x3F: 0x8279,
    0x40: 0x8168, 0x41: 0x8252, 0x42: 0x8254, 0x43: 0x8195, 0x44: 0x815E, 0x45: 0x8256, 0x46: 0x8277,
    0x47: 0x8145, 0x48: 0x8146, 0x49: 0x818A, 0x4A: 0x8253, 0x4B: 0x816A, 0x4C: 0x8169, 0x4D: 0x8189,
    0x4E: 0x8255, 0x4F: 0x8190, 0x50: 0x8196, 0x51: 0x8184, 0x52: 0x81BC, 0x53: 0x81BD, 0x54: 0x8183,
    0x55: 0x83BF, 0x56: 0x817B, 0x57: 0x8257, 0x58: 0x81A9, 0x59: 0x8258, 0x5A: 0x81A8, 0x5B: 0x8193,
}
REVERSE = {v: k for k, v in CHARSET.items()}
REVERSE.update({"«": 0x27, "»": 0x28, "[": 0x27, "]": 0x28, "’": 0x1B})

# text colour slots (F8 0A n / bytes 0x80..0x8F via D_801D5708). Site's names; 3/7 disagree
# between the site's two tables -- chunk-common says 3 green, 7 purple; the hextext menu says
# the opposite.  The duel-result tool's list (0 white 1 yellow 2 blue 3 green 4 grey 5 orange 6 red) wins.
COLOURS = {0: "white", 1: "yellow", 2: "blue", 3: "green", 4: "grey", 5: "orange", 6: "red", 7: "purple"}

# ------------------------------------------------------------------ control-code grammar
# Each entry: (total length, name, formatter) ; length None = variable, handled in iter_tokens.
# Offsets are little-endian u16 bank offsets unless noted.

def _u16(b, i):
    return b[i] | (b[i + 1] << 8)


def _f8(b, i):
    """F8 sub-commands (site's decoder)."""
    sub = b[i + 1] if i + 1 < len(b) else None
    tab = {
        0x00: (3, lambda: f"[CARD DATA {b[i+2]:02X}]"),
        0x01: (3, lambda: f"[CR+PAD TOP {b[i+2] - 256 if b[i+2] > 127 else b[i+2]}px]"),
        0x02: (3, lambda: f"[PAD LEFT {b[i+2]}px]"),
        0x03: (7, lambda: f"[PRINT VALUE @0x{struct.unpack_from('<I', b, i+2)[0]:08X} {b[i+6] & 0xF} chars "
                          f"{'ALL' if b[i+6] & 0xC0 == 0xC0 else 'RIGHT' if b[i+6] & 0xC0 == 0x80 else 'LEFT'}]"),
        0x04: (3, lambda: f"[FONT SIZE {b[i+2]:02X}]"),
        0x06: (4, lambda: f"[PAD LEFT SIGNED {struct.unpack_from('<h', b, i+2)[0]}px]"),
        0x09: (2, lambda: "[OPPONENT NAME]"),
        0x0A: (3, lambda: f"[COLOUR {COLOURS.get(b[i+2], b[i+2])}]"),
        0x0B: (3, lambda: f"[ICON {b[i+2]}]"),
        0x0D: (9, lambda: f"[DUEL opp={b[i+2]} win->{b[i+3]:02X} lose->{b[i+4]:02X} field={b[i+5]} "
                          f"music=0x{_u16(b, i+6):04X}]"),
        0x0E: (4, lambda: f"[MUSIC 0x{_u16(b, i+2):04X}]"),
        0x10: (None, None),   # sound effect: F8 10 hi lo [+2 delay bytes if lo & 0x80]
        0x11: (3, lambda: f"[STOP MUSIC {b[i+2]:02X}]"),
        0x15: (3, lambda: f"[SCREEN FX {b[i+2]:02X}]"),
        0x16: (None, None),   # F8 16 FF = automatic end of sequence; F8 16 xx = nothing
    }
    if sub == 0x10:
        n = 4 + (2 if i + 3 < len(b) and b[i + 3] & 0x80 else 0)
        s = f"[SFX {b[i+2]:02X}{b[i+3]:02X}" + (f" delay {_u16(b, i+4)}f" if n == 6 else "") + "]"
        return n, s
    if sub == 0x16:               # 0x800389C4: rec->flags &= ~8 ; no argument (site: "F8 16 FF = auto end")
        return 2, "[CLEAR BOX FLAG 8]"
    if sub in (0x17, 0x18):       # 0x800389D8 / 0x80038A44: skip 2*k bytes, k = byte at 0x8009B34E / 0x8009B355,
        ptrs = []                 # then jump to the u16 there.  Pointer count is not encoded; take the run of
        j = i + 2                 # nearby forward offsets (heuristic, max 8).
        rel = i - _CTX.get("bank_file", 0)
        while j + 1 < len(b) and len(ptrs) < 8:
            v = _u16(b, j)
            if not (rel < v < rel + 0x400):
                break
            ptrs.append(v); j += 2
        var = "8009B34E" if sub == 0x17 else "8009B355"
        return 2 + 2 * len(ptrs), f"[JUMP BY {var} " + " ".join(f"{v:04X}" for v in ptrs) + "]"
    if sub == 0x19:               # 0x80038AB0: n>0 -> Library_UpdateCardUsedFlag(n+0x1F), (n+0x6E0) = duelist met
        return 3, f"[UNLOCK DUELIST {b[i+2] if i+2 < len(b) else 0}]"
    if sub == 0x1A:               # 0x80038B08: delete the choice cursor object, state 2 ; no argument
        return 2, "[CLOSE CHOICE CURSOR]"
    if sub in tab and tab[sub][0]:
        n, f = tab[sub]
        return n, f()
    return 2, f"[F8 {sub:02X}]"    # 0x1B..0x1F -> stub func_80037D2C: consumes one byte


def _f7(b, i):
    sub = b[i + 1] if i + 1 < len(b) else None
    if sub == 0x05:            # background: F7 05 01 id type ; type&0x80 -> + y, xlo, xhi
        t = b[i + 3] if i + 3 < len(b) else 0
        n = 4 + (3 if t & 0x80 else 0)
        s = f"[BACKGROUND type={t & 0x3F} id={b[i+2]:02X}" + (f" y=-{b[i+4]} x=-{_u16(b, i+5)}" if n == 7 else "") + "]"
        return n, s
    if sub == 0x0F:
        d = _u16(b, i + 2)
        return 4, f"[TEXT DELAY {d}f]" if d else "[TEXT DELAY 0 = softlock]"
    if sub == 0x0A:
        return 2, "[WAIT BACKGROUND]"
    if sub == 0x0B:
        return 8, f"[BG MOVE x=-{_u16(b, i+2)} y=-{_u16(b, i+4)} {_u16(b, i+6)}f]"
    if sub == 0x10:
        return 4, f"[BG EFFECT {b[i+2]:02X}{b[i+3]:02X}]"
    return 2, f"[F7 {sub:02X}]"


def _f9(b, i):
    """func_80038D2C: v = u16.  bit 0x4000 -> Library_UpdateCardUsedFlag(v & 0xBFFF), 3 bytes.
    else: t = u16; if Campaign_TestStoryFlag(v) (bit 0x8000 inverts, F120) jump to t; 5 bytes."""
    v = _u16(b, i + 1) if i + 2 < len(b) else 0
    if v & 0x4000:
        return 3, f"[CARD FLAG {v & 0xBFFF:04X}]"      # site: 'SET/UNSET condition' (0x40xx / 0xC0xx)
    t = _u16(b, i + 3) if i + 4 < len(b) else 0
    return 5, f"[IF {'NOT ' if v & 0x8000 else ''}FLAG {v & 0x7FFF:03X} GOTO {t:04X}]"


def _fb(b, i, state):
    """func_80038BF0: f = byte; if f & 0x08 one more byte (value, default 15); if f & 0x80 a pointer
    list follows, entry gDialog_bChoice (0x8009B34D) is taken.  Low bits: choice count / box style."""
    f = b[i + 1] if i + 1 < len(b) else 0
    n = 2 + (1 if f & 0x08 else 0)
    if f & 0x80:
        k = state.get("choices", 2)
        ptrs = [_u16(b, i + n + 2 * j) for j in range(k) if i + n + 2 * j + 1 < len(b)]
        return n + 2 * len(ptrs), "[CHOICE TARGETS " + " ".join(f"{p:04X}" for p in ptrs) + "]"
    if 0 < (f & 0x07) <= 3 and f < 0x08:
        state["choices"] = f & 0x07
        return n, f"[CHOICES {f & 0x07}]"
    return n, f"[BOX STYLE {f:02X}" + (f" {b[i+2]:02X}" if n == 3 else "") + "]"


_CTX = {"bank_file": BANK_FILE}


def iter_tokens(b, start=0, stop_at_ff=True, bank_file=None):
    """Yield (offset, length, kind, text) over glyph bytes; kind = 'ch' | 'ctl' | 'end'.
    bank_file: file offset of the bank inside `b` (default BANK_FILE for a whole SLUS; pass 0 for a
    bare string) -- only used to judge F8 17/18 pointer runs."""
    _CTX["bank_file"] = BANK_FILE if bank_file is None else bank_file
    i = start
    state = {}
    while i < len(b):
        c = b[i]
        if c < 0xF0:
            if c in CHARSET:
                yield i, 1, "ch", CHARSET[c]
            elif 0x80 <= c <= 0x8F:
                yield i, 1, "ctl", f"[COLOUR SLOT {c & 0xF}]"
            else:
                yield i, 1, "ctl", f"[{c:02X}]"
            i += 1
            continue
        if c == 0xFF:
            yield i, 1, "end", "[END]"
            i += 1
            if stop_at_ff:
                return
            continue
        if c == 0xFE:
            n, s = 1, "[NL]"
        elif c == 0xFA:
            n, s = 1, "[PAGE]"
        elif c == 0xFD:
            n, s = 3, f"[GOTO {_u16(b, i+1):04X}]"
        elif c == 0xFC:
            n, s = 3, f"[INSERT {_u16(b, i+1):04X}]" + (" (player name)" if _u16(b, i + 1) == 0x125A else "")
        elif c == 0xFB:
            n, s = _fb(b, i, state)
        elif c == 0xF9:
            n, s = _f9(b, i)
        elif c == 0xF8:
            n, s = _f8(b, i)
        elif c == 0xF7:
            n, s = _f7(b, i)
        elif c == 0xF6:
            a1 = b[i + 1] if i + 1 < len(b) else 0
            kind = "THUMBNAIL" if 64 < a1 < 90 else "CHARACTER"
            n, s = 3, f"[{kind} {a1:02X} anim={b[i+2] if i+2 < len(b) else 0:02X}]"
        else:                      # F0..F5: func_80037D2C = 2-byte glyph escape, index (c-0xF0)<<8 | next
            g = ((c - 0xF0) << 8) | (b[i + 1] if i + 1 < len(b) else 0)
            n, s = 2, (CHARSET[g] if g in CHARSET else f"[GLYPH {g:03X}]")
        yield i, n, "ctl", s
        i += n


def decode(b, start=0, bank_file=None):
    return "".join(t for _, _, _, t in iter_tokens(b, start, bank_file=bank_file))


def encode(text, terminate=False):
    """ASCII text -> glyph bytes.  Unknown characters raise.  '\\n' -> FE."""
    out = bytearray()
    for ch in text:
        if ch == "\n":
            out.append(0xFE)
        elif ch in REVERSE:
            out.append(REVERSE[ch])
        else:
            raise ValueError(f"no glyph for {ch!r}")
    if terminate:
        out.append(0xFF)
    return bytes(out)


# ------------------------------------------------------------------ bank access

def bank_string(slus, ram_or_off):
    off = ram_or_off - BANK_RAM if ram_or_off >= BANK_RAM else ram_or_off
    return slus[BANK_FILE + off:]


def string_offset(slus, sid, table=OFFSETS_RAM):
    return struct.unpack_from("<H", slus, ram2file(table) + 2 * sid)[0]


def bank_strings(slus, table=OFFSETS_RAM, lo=0, hi=None):
    n = 1100 if table == OFFSETS_RAM else 259
    hi = n if hi is None else hi
    for sid in range(lo, hi):
        off = string_offset(slus, sid, table)
        yield sid, off, decode(slus, BANK_FILE + off)


def charset_from_exe(slus):
    out = {}
    base = ram2file(GLYPH_TABLE_RAM)
    for i in range(256):
        w = struct.unpack_from("<I", slus, base + 4 * i)[0]
        if i and w == 0:
            break
        sj = w & 0xFFFF
        try:
            ch = bytes([sj >> 8, sj & 0xFF]).decode("shift_jis") if sj else " "
        except UnicodeDecodeError:
            ch = "?"
        out[i] = (ch, sj, w >> 16)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("charset"); p.add_argument("slus", nargs="?")
    p = sub.add_parser("decode"); p.add_argument("slus"); p.add_argument("what", nargs="+")
    p.add_argument("--table", default="0x801C0000")
    p = sub.add_parser("dump"); p.add_argument("slus"); p.add_argument("--table", default="0x801C0000")
    p.add_argument("--from", dest="lo", type=int, default=0); p.add_argument("--to", dest="hi", type=int)
    p = sub.add_parser("encode"); p.add_argument("text"); p.add_argument("--terminate", action="store_true")
    p = sub.add_parser("patch"); p.add_argument("slus"); p.add_argument("bankoff"); p.add_argument("text")
    p.add_argument("--terminate", action="store_true"); p.add_argument("-o", "--out")
    p = sub.add_parser("find"); p.add_argument("slus"); p.add_argument("text")
    a = ap.parse_args()

    if a.cmd == "charset":
        if a.slus:
            for i, (ch, sj, hi) in charset_from_exe(open(a.slus, "rb").read()).items():
                print(f"0x{i:02X}  {ch!r:6}  sjis 0x{sj:04X}  hi 0x{hi:04X}")
        else:
            for i, ch in CHARSET.items():
                print(f"0x{i:02X}  {ch!r}")
        return
    if a.cmd == "encode":
        print(encode(a.text, a.terminate).hex(" "))
        return

    slus = bytearray(open(a.slus, "rb").read())
    if a.cmd == "decode":
        table = int(a.table, 0)
        for w in a.what:
            if w.lower().startswith("0x"):
                off = int(w, 16)
                off = off - BANK_RAM if off >= BANK_RAM else off
                print(f"@{off:04X}: {decode(slus, BANK_FILE + off)}")
            else:
                sid = int(w)
                off = string_offset(slus, sid, table)
                print(f"#{sid} @{off:04X}: {decode(slus, BANK_FILE + off)}")
    elif a.cmd == "dump":
        for sid, off, text in bank_strings(slus, int(a.table, 0), a.lo, a.hi):
            print(f"{sid:4d} {off:04X} {text}")
    elif a.cmd == "find":
        needle = encode(a.text)
        i = slus.find(needle, BANK_FILE)
        while i != -1 and i < BANK_FILE + 0x10000:
            print(f"bank +0x{i - BANK_FILE:04X} (file 0x{i:06X}, RAM 0x{BANK_RAM + i - BANK_FILE:08X}): {decode(slus, i)}")
            i = slus.find(needle, i + 1)
    elif a.cmd == "patch":
        off = int(a.bankoff, 0)
        off = off - BANK_RAM if off >= BANK_RAM else off
        enc = encode(a.text, a.terminate)
        old = bytes(slus[BANK_FILE + off: BANK_FILE + off + len(enc)])
        slus[BANK_FILE + off: BANK_FILE + off + len(enc)] = enc
        out = a.out or a.slus
        open(out, "wb").write(slus)
        print(f"bank +0x{off:04X}: {old.hex(' ')} -> {enc.hex(' ')}  ({decode(slus, BANK_FILE + off)}) written {out}")


if __name__ == "__main__":
    main()
