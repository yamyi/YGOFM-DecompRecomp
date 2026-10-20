#!/usr/bin/env python3
"""phoenix_battle.py -- offline clone of TEA-Online "Phoenix > Effects > Battle"
(Battlefield Demolisher Tool, extend/tools/phoenix/effects/battle).

The site injects a small MIPS routine into SLUS_014.11 and hooks it into the
duel's battle-aftermath phase (inside the 0x8001F560 mode handler, at the block
splat calls `func_8002061C`).  The routine looks up the two battling cards, finds
them in a 16-entry table, and forces who survives the battle:

  effect 0  "Marshmallon"        that card is never destroyed in battle
  effect 1  "Exploder Dragon"    both cards are destroyed, unless the other one
                                 is in the 14-entry exception list
  effect 2  "D.D. Warrior Lady"  both cards are destroyed, no exceptions

SLUS_014.11 layout (RAM = 0x80010000 + file_off - 0x800):

  file 0x10E30  RAM 0x80020630  16 B  hook A (4 words)
  file 0x10EB0  RAM 0x800206B0   8 B  hook B (2 words)
  file 0x1C57D0 RAM 0x801D4FD0 552 B  the routine
  file 0x1C59F8 RAM 0x801D51F8  68 B  data: 16 x u16 (id<<4 | effect), u32 -1,
                                      14 x u16 exception ids, u32 -1
  file 0x1C5A3C RAM 0x801D523C  20 B  the routine's tail (the card-690 guard)

0x801D4FD0..0x801D5250 is stock `gCard_asNameSortKey` (s16[722] at 0x801D4D8E),
so installing the process destroys the alphabetical sort keys of card ids
290..609 -- Build Deck / Trunk sorting is scrambled for those cards.

Usage:
  phoenix_battle.py check    SLUS                 # installed? which cards/effects?
  phoenix_battle.py install  SLUS [-o OUT]        # write hooks + routine, keep the lists
  phoenix_battle.py set      SLUS [-o OUT] --effect ID:EFFECT ... --exception ID ...
  phoenix_battle.py restore  SLUS STOCK [-o OUT]  # put the stock bytes back
  phoenix_battle.py names    SLUS ID ...          # print card names (sanity check)
"""
import argparse, sys

H = bytes.fromhex

# (file offset, patched bytes) -- verbatim from the site's Ve / We / Ye arrays.
HOOKS = [
    (0x10E30, H('f553070c' 'f09e1126' '6854070c' '80008234')),
    (0x10EB0, H('7454070c' '1d80073c')),
]
CODE = [
    (0x1C57D0, H(
        '000000000400228e1d80073c03004014d04fe0ac0800e0030000000021180000ffff0a24ffff0b24'
        '6a00469000000000c02806002328a600802805001a80063cd87ac6242110a6000c0042948f540708'
        '1d80063cf851c6240000c58400000000024105000d0002110f00a930faffa1040200c62405006010'
        '214040000e006105ffff09240800e00300000000215040000000228efe5307080100632406006014'
        '000000000000228e2150000121582001fe530708010063240200201501000224d04fe2a40200601500000000'
        'd24fe2a42a102b0103004014ffff02242e5407082118200121186001ffff65243500a01cffff2925'
        '1d80063c1c52c62417002015ffff6b25d04fe2ac94020c240c000c1500000000d04fe0a41d800d3c'
        '3253ad252168aa010000ad9101000c2402690d000300ac15000000004b540708d24fe0a40000c584'
        '000000000200aa1400000000d24fe0a4faffa1040200c6241700601500000000d04fe2ac94020c24'
        '0c004c1500000000d24fe0a41d800d3c3253ad252168a8010000ad9101000c2402690d000300ac15'
        '0000000063540708d04fe0a40000c584000000000200a81400000000d04fe0a4faffa1040200c624'
        '0800e00300000000ffff02240800e003d04fe2ac6c0282a31d80073cd04fe7840800238e0500e010'
        '00000000010003240200e01c00000000000003240800e00300000000d24fe7840c00228e0500e010'
        '00000000010002240200e01c00000000000002240800e00300000000')),
    (0x1C5A3C, H('b202052478ffa214000000000800e00300000000')),
]
DATA = 0x1C59F8         # RAM 0x801D51F8
DATA_LEN = 68
EFF_N, EXC_N = 16, 14
EXC = DATA + 36         # RAM 0x801D521C
EFFECTS = {0: 'Marshmallon (never destroyed)',
           1: 'Exploder Dragon (both destroyed, exceptions apply)',
           2: 'D.D. Warrior Lady (both destroyed, no exceptions)'}
ALIAS = {'marshmallon': 0, 'exploder': 1, 'exploderdragon': 1,
         'ddwl': 2, 'ddwarriorlady': 2}

# card name tables (see teatools/cardsdata/README.md)
NAME_OFF = 0x1C6000     # u16 per card id, RAM 0x801D5800 gText_aGlobalOffsets
NAME_TXT = 0x1C0800     # RAM 0x801D0000
# the site's glyph table (Ke): game character code -> ASCII
GLYPH = {
    0: ' ', 1: 'e', 2: 't', 3: 'a', 4: 'o', 5: 'i', 6: 'n', 7: 's',
    8: 'r', 9: 'h', 10: 'l', 11: '.', 12: 'd', 13: 'u', 14: 'm', 15: 'c',
    16: 'g', 17: 'y', 18: 'w', 19: 'f', 20: 'p', 21: 'b', 22: 'k', 23: '!',
    24: 'A', 25: 'v', 26: 'I', 27: "'", 28: 'T', 29: 'S', 30: 'M', 31: ',',
    32: 'D', 33: 'O', 34: 'W', 35: 'H', 36: 'Y', 37: 'E', 38: 'R', 39: '<',
    40: '>', 41: 'G', 42: 'L', 43: 'C', 44: 'N', 45: 'B', 46: '?', 47: 'P',
    48: '-', 49: 'F', 50: 'z', 51: 'K', 52: 'j', 53: 'U', 54: 'x', 55: 'q',
    56: '0', 57: 'V', 58: '2', 59: 'J', 60: '#', 61: '1', 62: 'Q', 63: 'Z',
    65: '3', 66: '5', 67: '&', 68: '/', 69: '7', 70: 'X', 72: ':', 74: '4',
    75: ')', 76: '(', 78: '6', 80: '*', 81: '>', 84: '<', 85: '@', 86: '+',
    87: '8', 89: '9',
}


def card_name(d, cid):
    """Best-effort name decode; only used for readable output."""
    o = int.from_bytes(d[NAME_OFF + 2 * cid:NAME_OFF + 2 * cid + 2], 'little')
    p = NAME_TXT + o
    s = ''
    for i in range(40):
        b = d[p + i]
        if b == 0xFF:
            break
        if b == 0xF8:
            i += 2
            continue
        s += GLYPH.get(b, '?')
    return s


def installed(d):
    return all(d[a:a + len(b)] == b for a, b in HOOKS)


def read_lists(d):
    """Exactly what the routine reads: scan until an entry with bit15 set."""
    eff, exc = [], []
    for i in range(EFF_N):
        v = int.from_bytes(d[DATA + 2 * i:DATA + 2 * i + 2], 'little')
        if v & 0x8000:
            break
        eff.append((v >> 4, v & 0xF))
    for i in range(EXC_N):
        v = int.from_bytes(d[EXC + 2 * i:EXC + 2 * i + 2], 'little')
        if v & 0x8000:
            break
        exc.append(v)
    return eff, exc


def write_lists(d, eff, exc):
    if len(eff) > EFF_N:
        sys.exit('at most %d effect cards' % EFF_N)
    if len(exc) > EXC_N:
        sys.exit('at most %d exceptions' % EXC_N)
    for cid, e in eff:
        if not 1 <= cid <= 722 or e not in EFFECTS:
            sys.exit('bad effect entry %r' % ((cid, e),))
    for cid in exc:
        if not 1 <= cid <= 722:
            sys.exit('bad exception card id %d' % cid)
    for i in range(EFF_N):
        v = (eff[i][0] << 4 | eff[i][1]) if i < len(eff) else 0xFFFF
        d[DATA + 2 * i:DATA + 2 * i + 2] = v.to_bytes(2, 'little')
    d[DATA + 32:DATA + 36] = b'\xFF\xFF\xFF\xFF'
    for i in range(EXC_N):
        v = exc[i] if i < len(exc) else 0xFFFF
        d[EXC + 2 * i:EXC + 2 * i + 2] = v.to_bytes(2, 'little')
    d[EXC + 28:EXC + 32] = b'\xFF\xFF\xFF\xFF'


def write_code(d):
    for a, b in HOOKS + CODE:
        d[a:a + len(b)] = b


def check(args):
    d = open(args.slus, 'rb').read()
    ok = installed(d)
    print('process installed:', ok)
    lo, hi = 0x1C57D0, 0x1C5A50
    base = 0x1C558E                         # file offset of gCard_asNameSortKey
    print('clobbered gCard_asNameSortKey entries: card ids %d..%d'
          % ((lo - base) // 2 + 1, (hi - 1 - base) // 2 + 1))
    if not ok:
        return
    eff, exc = read_lists(d)
    print('effect cards (%d/%d):' % (len(eff), EFF_N))
    for cid, e in eff:
        print('  %3d %-26s -> %s' % (cid, card_name(d, cid), EFFECTS.get(e, '?%d' % e)))
    print('Exploder exceptions (%d/%d):' % (len(exc), EXC_N))
    for cid in exc:
        print('  %3d %s' % (cid, card_name(d, cid)))


def install(args):
    d = bytearray(open(args.slus, 'rb').read())
    eff, exc = read_lists(d) if installed(d) else ([], [])
    write_code(d)
    write_lists(d, eff, exc)
    out = args.out or args.slus
    open(out, 'wb').write(d)
    print('installed into %s; kept %d effects, %d exceptions' % (out, len(eff), len(exc)))


def parse_effect(s):
    cid, _, e = s.partition(':')
    if not e:
        sys.exit('--effect wants ID:EFFECT')
    k = e.strip().lower().replace(' ', '').replace('.', '')
    e = int(e) if e.strip().isdigit() else ALIAS.get(k)
    if e is None:
        sys.exit('unknown effect %r (0/1/2, marshmallon, exploder, ddwl)' % s)
    return int(cid), e


def setcmd(args):
    d = bytearray(open(args.slus, 'rb').read())
    if not installed(d):
        write_code(d)
    eff = [parse_effect(s) for s in (args.effect or [])]
    exc = [int(x) for x in (args.exception or [])]
    write_lists(d, eff, exc)
    out = args.out or args.slus
    open(out, 'wb').write(d)
    print('wrote %s: %d effects, %d exceptions' % (out, len(eff), len(exc)))


def restore(args):
    d = bytearray(open(args.slus, 'rb').read())
    s = open(args.stock, 'rb').read()
    if len(s) != len(d):
        sys.exit('stock file has a different size')
    for a, b in HOOKS + CODE:
        d[a:a + len(b)] = s[a:a + len(b)]
    d[DATA:DATA + DATA_LEN] = s[DATA:DATA + DATA_LEN]
    out = args.out or args.slus
    open(out, 'wb').write(d)
    print('restored', out)


def names(args):
    d = open(args.slus, 'rb').read()
    for i in args.ids:
        print('%3d %s' % (i, card_name(d, int(i))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('check'); p.add_argument('slus'); p.set_defaults(f=check)
    p = sp.add_parser('install'); p.add_argument('slus'); p.add_argument('-o', '--out'); p.set_defaults(f=install)
    p = sp.add_parser('set'); p.add_argument('slus'); p.add_argument('-o', '--out')
    p.add_argument('--effect', action='append', metavar='ID:EFFECT',
                   help='0|1|2 or marshmallon|exploder|ddwl')
    p.add_argument('--exception', action='append', metavar='ID',
                   help='card id immune to Exploder Dragon')
    p.set_defaults(f=setcmd)
    p = sp.add_parser('restore'); p.add_argument('slus'); p.add_argument('stock')
    p.add_argument('-o', '--out'); p.set_defaults(f=restore)
    p = sp.add_parser('names'); p.add_argument('slus'); p.add_argument('ids', nargs='+', type=int)
    p.set_defaults(f=names)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
