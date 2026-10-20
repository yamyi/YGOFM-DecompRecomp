#!/usr/bin/env python3
"""Offline clone of TEA-Online's "Card Color" process tool (extend/tools/process/cardcolor).

  card_color.py inspect SLUS_014.11 [WA_MRG.MRG]
  card_color.py apply   SLUS_014.11 out.11 [--set CARD=SLOT ...] [--csv f] [--random]
  card_color.py restore SLUS_014.11 out.11
  card_color.py palette-export WA_MRG.MRG SLOT out.bin       512-byte CLUT (256 x 15-bit BGR) of colour slot 1..7
  card_color.py palette-import WA_MRG.MRG out.mrg SLOT in.bin  write it into all 10 copies
  card_color.py palette-copy-default WA_MRG.MRG out.mrg        slot 1 -> slot 7 (the site's "copy default")

SLOT 0..6 = the site's "COLOR DEFAULT".."COLOR 7" (0 monster frame, 1 magic/equip, 2 trap,
3 ritual, 4..6 spare).  Slot 6's WA palette block is all zeros in stock, which is why the injected
small-card stub special-cases slot >= 6 and why the site ships a "copy default" button.
CSV rows: card,slot (== the site's CardColorTemplate.xlsx).  A fresh apply seeds the table from the
card types exactly like the site: type 20 -> 1, 21 -> 2, 22 -> 3, 23 -> 1, everything else -> 0,
which reproduces stock rendering at all three consumers byte for byte.

What it does (see ../README.md; disassembly of every region in ../patch/): a 361-byte nibble table at 0x80012150 (file 0x2950; high nibble =
odd card id) is consulted by three redirected card-frame CLUT setups: the library/big-card object id
0x108+slot (init_container_entry_objs 0x8002940C), the in-duel small card CLUT row 0xF1+slot
(func_80016784 0x80016BBC) and the per-card CLUT x 352+16*slot table (func_8002BFCC 0x8002C290).
"""
import argparse, base64, csv, random, sys

H = lambda s: bytes.fromhex(s.replace(' ', ''))
OFF_DATA = 0x2950; OFF_STATS = 0x1C4A40                 # 0x80012150 / gDuel_adwCardStats 0x801D4240
PATCH = {
    0X2AC0: H('42981300 0180023c 50214224 21105300 00004280 01009330 ff004230 02006012 0f005330 02990200'
               '00017326 1d80033c 05a50008 32536324 4f546167 456e7628 2800a28f 0180033c 0c004294 50216324'
               '00004424 ffff4224 42100200 21186200 00006390 01008430 02008010 0f006230 02110300 06004428'
               '06008014 00000000 f100023c 80014234 100022ae 00000000 00000224 f1000424 21184400 120023a6'
               '6666043c 0e000224 f15a0008 00000000'),
    0X73BC: H('c0480008 00000000'),          # func_80016784: j 0x80012300
    0X19C0C: H('b0480008 ffff9324'),         # init_container_entry_objs: j 0x800122C0 ; addiu s3,a0,-1
    0X1CA90: H('0180023c 50214224 560080a0 5400a0a6 ffff7126 42881100 21885100 00003192 01007232 02004012'
               '0f003232 02911100 0600512a 02002016 00000000 00000000 00911200 60011124 21883202 540091a4'
               '04008424 01007326 d302712a eaff2016 0400a524 00000000 00000000 00000000'),
}
OLD = {0x73AC: H('e46b0708'), 0x19BFC: H('786b0708 ffff9324')}          # v1 layout (data at 0x1CB624)
OLD_DATA = 0x1CB624; OLD_ZONES = ((0x1CB5E0, 68), (0x1CB790, 124))
STOCK = {
    0x2950: base64.b64decode('LmMsdiAxLjE0MCAxOTk4LzAxLzEyIDA3OjUyOjI3IG5vZGEgRXhwIHlvcyAkAAAAUmVzZXRHcmFwaDpqdGI9JTA4eCxlbnY9JTA4eAoAAABSZXNldEdyYXBoKCVkKS4uLgoAAFNldEdyYXBoRGVidWc6bGV2ZWw6JWQsdHlwZTolZCByZXZlcnNlOiVkCgAAU2V0R3JhcFF1ZSglZCkuLi4KAABEcmF3U3luY0NhbGxiYWNrKCUwOHgpLi4uCgAAU2V0RGlzcE1hc2soJWQpLi4uCgBEcmF3U3luYyglZCkuLi4KAAAAACVzOmJhZCBSRUNUACglZCwlZCktKCVkLCVkKQoAAAAAJXM6AENsZWFySW1hZ2UAAENsZWFySW1hZ2UyAExvYWRJbWFnZQAAAFN0b3JlSW1hZ2UAAE1vdmVJbWFnZQAAAENsZWFyT1RhZyglMDh4LCVkKS4uLgoAAENsZWFyT1RhZ1IoJTA4eCwlZCkuLi4KAERyYXdPVGFnKCUwOHgpLi4uCgAAUHV0RHJhd0VudiglMDh4KS4uLgoAAAAARHJhd09UYWdFbnYoJTA4eCwmMDh4KS4uLgoAAFB1dERpc3BFbnYoJTA4eCkuLi4KAAAAAEdQVSB0aW1lb3V0OnF1ZT0lZCxzdGF0PSUwOHgsY2hjcj0lMDh4LG1hZHI9JTA4eAoAAABMb2FkSW1hZ2UyAABpZCAgPSUwOA=='),
    0x73AC: H('f8ff6324'), 0x73BC: H('6666043c 0e000224'),
    0x19BFC: H('00011324 21800000'), 0x19C0C: H('1d80033c 32536324'),
    0x1CA90: base64.b64decode('IRCrAFYAgKBUAKCmAABCjAAAAACDFgIAHwBDMA0AahAWAGIoBQBAEAAAAAAHAGkQYAECJLuwAAhUAIKkBgBoEJABAiQEAGcUYAECJLuwAAhUAIakgAECJFQAgqQEAIQkAQBzJtMCYirl/0AUBAClJA=='),
}
PAL_BASE = 0xB84000; PAL_STRIDE = 512
COPIES = (0, 481280, 962560, 1443840, 1925120, 2406400, 2887680, 3684352, 4409344, 5658624)
TYPE_DEFAULT = {20: 1, 21: 2, 22: 3, 23: 1}


def load_slus(p):
    d = bytearray(open(p, 'rb').read())
    if not (1782579 <= len(d) <= 2097152) or d[:8] != b'PS-X EXE':
        sys.exit('not a SLUS_014.11-sized PS-X EXE')
    return d


def load_wa(p):
    d = bytearray(open(p, 'rb').read())
    if not (36700160 <= len(d) <= 45088768):
        sys.exit('not a WA_MRG.MRG-sized file')
    return d


def has(d, t):
    return all(bytes(d[o:o + len(v)]) == v for o, v in t.items())


def get_slot(d, base, cid):
    b = d[base + (cid - 1) // 2]
    return b >> 4 if cid % 2 else b & 15


def set_slot(d, base, cid, s):
    i = base + (cid - 1) // 2; b = d[i]
    d[i] = (s << 4) | (b & 15) if cid % 2 else (b & 0xF0) | s


def card_type(d, cid):
    return d[OFF_STATS + 4 * cid + 3] >> 2


def inspect(slus, wa):
    d = load_slus(slus)
    new = has(d, PATCH); old = has(d, OLD)
    print('SLUS:', 'process installed (current layout)' if new else 'OLD layout installed (data at 0x1CB624)' if old
          else 'stock' if has(d, STOCK) else 'unknown bytes at the hook sites')
    if new or old:
        base = OFF_DATA if new else OLD_DATA
        slots = {}
        for cid in range(1, 723):
            slots.setdefault(get_slot(d, base, cid), []).append(cid)
        for s in sorted(slots):
            print(f'  slot {s} (colour {s + 1}): {len(slots[s])} cards' + (f': {slots[s]}' if len(slots[s]) < 60 else ''))
    if wa:
        w = load_wa(wa)
        for s in range(7):
            b = PAL_BASE + PAL_STRIDE * s
            same = all(w[b + c:b + c + 512] == w[b:b + 512] for c in COPIES)
            print(f'  palette slot {s} @ WA {b:#x}: {sum(1 for x in w[b:b + 512] if x)} non-zero bytes, identical in 10 copies: {same}')


def apply(d, a):
    fresh = not has(d, PATCH)
    if fresh:
        if has(d, OLD):                                   # migrate v1 data, wipe v1 code
            d[OFF_DATA:OFF_DATA + 361] = d[OLD_DATA:OLD_DATA + 361]
            d[OLD_DATA:OLD_DATA + 361] = bytes(361)
            for o, n in OLD_ZONES:
                d[o:o + n] = bytes(n)
            d[0x73AC:0x73B0] = STOCK[0x73AC]; d[0x19BFC:0x19C04] = STOCK[0x19BFC]
        else:
            for cid in range(1, 723):
                set_slot(d, OFF_DATA, cid, TYPE_DEFAULT.get(card_type(d, cid), 0))
            d[OFF_DATA + 361:0x2AC0] = bytes(0x2AC0 - OFF_DATA - 361)
    for o, v in PATCH.items():
        d[o:o + len(v)] = v
    if a.random:
        for cid in range(1, 723):
            set_slot(d, OFF_DATA, cid, random.randrange(7))
    for s in a.set or []:
        c, v = (int(x, 0) for x in s.split('='))
        if not (1 <= c <= 722 and 0 <= v <= 15):
            sys.exit(f'bad --set {s}')
        set_slot(d, OFF_DATA, c, v)
    if a.csv:
        for r in csv.reader(open(a.csv)):
            if r and r[0].strip().isdigit() and 1 <= int(r[0]) <= 722:
                set_slot(d, OFF_DATA, int(r[0]), int(r[1]) & 15)


def restore(d):
    for o, v in STOCK.items():
        d[o:o + len(v)] = v
    for o, n in OLD_ZONES:
        d[o:o + n] = bytes(n)
    d[OLD_DATA:OLD_DATA + 361] = bytes(361)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['inspect', 'apply', 'restore', 'palette-export', 'palette-import', 'palette-copy-default'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--set', action='append'); ap.add_argument('--csv'); ap.add_argument('--random', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'inspect':
        inspect(a.args[0], a.args[1] if len(a.args) > 1 else None)
    elif a.cmd in ('apply', 'restore'):
        d = load_slus(a.args[0]); apply(d, a) if a.cmd == 'apply' else restore(d)
        open(a.args[1], 'wb').write(d); print('wrote', a.args[1])
    elif a.cmd == 'palette-export':
        w = load_wa(a.args[0]); s = int(a.args[1]) - 1
        open(a.args[2], 'wb').write(w[PAL_BASE + PAL_STRIDE * s:PAL_BASE + PAL_STRIDE * (s + 1)]); print('wrote', a.args[2])
    else:
        w = load_wa(a.args[0])
        if a.cmd == 'palette-import':
            s = int(a.args[2]) - 1; pal = open(a.args[3], 'rb').read()[:512].ljust(512, b'\0')
        else:
            s = 6; pal = bytes(w[PAL_BASE:PAL_BASE + 512])
        for c in COPIES:
            b = PAL_BASE + PAL_STRIDE * s + c; w[b:b + 512] = pal
        open(a.args[1], 'wb').write(w); print('wrote', a.args[1])
