#!/usr/bin/env python3
"""Offline clone of TEA-Online's "Free Duel Theme" process tool (extend/tools/process/freedueltheme).

  freeduel_theme.py inspect SLUS_014.11
  freeduel_theme.py apply   SLUS_014.11 out.11 [--all THEME] [--set OPP=THEME ...] [--csv file.csv]
  freeduel_theme.py restore SLUS_014.11 out.11

THEME is the BGM/"sound preset" index 0..0x38 (hex or decimal); OPP is the opponent id 1..39
(1 = Simon Muran ... 39 = the last campaign duelist, same order as the name strings 809..847).
CSV rows: opponent,theme.  Default theme for every opponent is 0x27 (the stock free-duel track).

What it does (see ../README.md): replaces the 84-byte body of init_800eb26c_fields_from_args
(0x80024DC8, file 0x155C8) so that gDuel_wBgmPreset (0x8009B36A) is loaded from a per-opponent
byte table at 0x801DB010 (file 0x1CB810, 40 bytes, index = opponent id) as 0x7000 + 16*table[id],
instead of the constant 0x7270.
"""
import argparse, base64, csv, sys

OFF_CODE = 0x155C8            # RAM 0x80024DC8
OFF_DATA = 0x1CB810           # RAM 0x801DB010, table[0..39]
N_OPP = 39
DEFAULT_THEME = 0x27

STOCK_CODE = base64.b64decode(
    'cHICJAqAATxqsyKkgHICJAqAATx0syKkAwACJAqAATxgsySgCoABPGGzJaAKgAE8cLMmpAqAATxysyekCoABPGSzIKAKgAE8abMgoAqAATxssiKg')
PATCH_CODE = bytes.fromhex(
    '1e80023c 21104500 10b04280 00000000 00110200 00704224'.replace(' ', '') +   # lui/addu/lb/nop/sll/addiu
    '00000000' * 4 +                                                             # 4 x nop
    '0a80013c 6ab322a4 80720224 74b322a4 60b324a0 61b325a0 70b326a4 72b327a4 64b320a0 69b320a0 6cb222a0'.replace(' ', ''))
assert len(STOCK_CODE) == 84 and len(PATCH_CODE) == 84

THEMES = {0x00: "Main Menu", 0x01: "Input Name Menu", 0x02: "Introduction Title Screen", 0x03: "Tournament Announcement",
          0x04: "Modern Times", 0x05: "Inside the Puzzle", 0x06: "Preliminary Face-Off", 0x07: "Finals Face Off",
          0x08: "Seto Kaiba Face-Off", 0x09: "Tournament Card Shop", 0x0A: "Metropolis 1", 0x27: "Free Duel (stock)",
          0x34: "Town Plaza Festival", 0x35: "Password Menu", 0x36: "Millenium Item Found", 0x37: "Forbidden Ruins",
          0x38: "Simon Muran"}   # full 57-entry list: ../themes.txt


def load(p):
    d = bytearray(open(p, 'rb').read())
    if not (1782579 <= len(d) <= 2097152) or d[:8] != b'PS-X EXE':
        sys.exit('not a SLUS_014.11-sized PS-X EXE')
    return d


def installed(d):
    return bytes(d[OFF_CODE:OFF_CODE + 84]) == PATCH_CODE


def inspect(d):
    if installed(d):
        print('process : installed')
        for i in range(1, N_OPP + 1):
            t = d[OFF_DATA + i]
            print(f'  opponent {i:2d}: theme 0x{t:02X} ({THEMES.get(t, "?")})  -> preset 0x{0x7000 + 16 * t:04X}')
    elif bytes(d[OFF_CODE:OFF_CODE + 84]) == STOCK_CODE:
        print('process : not installed (stock code at 0x155C8)')
    else:
        print('process : unknown bytes at 0x155C8 (other patch?)')


def apply(d, a):
    fresh = not installed(d)
    d[OFF_CODE:OFF_CODE + 84] = PATCH_CODE
    if fresh:
        d[OFF_DATA] = 0
        for i in range(1, N_OPP + 1):
            d[OFF_DATA + i] = DEFAULT_THEME
    if a.all is not None:
        for i in range(1, N_OPP + 1):
            d[OFF_DATA + i] = int(a.all, 0) & 0xFF
    for s in a.set or []:
        o, t = s.split('=')
        o = int(o, 0)
        if not 1 <= o <= N_OPP:
            sys.exit(f'opponent {o} out of range 1..{N_OPP}')
        d[OFF_DATA + o] = int(t, 0) & 0xFF
    if a.csv:
        for row in csv.reader(open(a.csv)):
            if not row or not row[0].strip().isdigit():
                continue
            o, t = int(row[0]), int(row[1], 0)
            if 1 <= o <= N_OPP:
                d[OFF_DATA + o] = t & 0xFF


def restore(d):
    d[OFF_CODE:OFF_CODE + 84] = STOCK_CODE
    d[OFF_DATA:OFF_DATA + 40] = bytes(40)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['inspect', 'apply', 'restore'])
    ap.add_argument('slus'); ap.add_argument('out', nargs='?')
    ap.add_argument('--all'); ap.add_argument('--set', action='append'); ap.add_argument('--csv')
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == 'inspect':
        inspect(d)
    else:
        if not a.out:
            sys.exit('need an output path')
        (apply if a.cmd == 'apply' else lambda d, a: restore(d))(d, a)
        open(a.out, 'wb').write(d); print('wrote', a.out)
