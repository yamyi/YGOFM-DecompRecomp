#!/usr/bin/env python3
"""Offline clone of TEA-Online's "Special Ban List" process tool (extend/tools/process/specialbanlist).

  banlist.py inspect SLUS_014.11
  banlist.py apply   SLUS_014.11 out.11 [--colors] [--reset] [--limit CARD=GROUP ...] [--color GROUP=#RRGGBB ...] [--csv f]
  banlist.py restore SLUS_014.11 out.11

GROUP: 0 = Forbidden (never addable), 1..14 = "Limited N" (at most N cards of that whole group in the
deck), 15 = unrestricted.  CSV rows: card,group.  --colors also installs the deck-editor colour
script (trunk-list names turn the group colour when the group is full / forbidden).  --reset puts every
card at 15 and restores the tool's default colour table.

Layout (see ../README.md): code at 0x800955B8 (file 0x85DB8) hooked from 0x8003387C (add-card path of
the deck editor), validator at 0x801DB040 (file 0x1CB840), limit nibbles 0x801DB130 (file 0x1CB930,
361 bytes, high nibble = odd card id, low nibble = even card id), colour words 0x80012978 (file 0x3178)
and colour hook 0x80012580 (file 0x2D80) jumped to from 0x80031C5C.
"""
import argparse, base64, csv, sys

B = lambda s: base64.b64decode(s)
H = lambda s: bytes.fromhex(s.replace(' ', ''))

OFF_W, OFF_J, OFF_Y, OFF_V, OFF_K, OFF_G, OFF_Z, OFF_Q, OFF_X = \
    0x2D80, 0x3178, 0x2245C, 0x2407C, 0x85DB8, 0x85E00, 0x1CB840, 0x1CB930, 0x1CB940

PATCH = {
    OFF_V: H('6e550208 00000000'),                                   # j 0x800955B8 ; nop
    OFF_K: H('0980023c 20564224 000041ac 106c070c 0980023c 09800 13c 20562124 0000218c 05004010 00000000'
             'b8ff000c 07000424 21ce0008 00000000 32ce0008 00000000'),
    OFF_G: bytes(48),
    OFF_Z: H('00564224 000041ac 040043ac 080044ac 0c0045ac 100046ac 140047ac 180048ac 1e80013c 30b12124'
             'ffff0326 43200300 21202400 00008490 01006330 02006010 02290400 0f008530 0f00a42c 1d008010'
             '01000224 1b00a010 00000224 1080043c 502d8424 00000324 28000824 0d008690 00000000 1200c010'
             '00000000 04008694 00000000 ffffc624 42380600 2138e100 0000e790 0100c630 0200c010 02310700'
             '0f00e630 0400c514 ffff0825 01006324 04006510 00000000 ecff0015 10008424 01000224 0980083c'
             '00560825 0000018d 0400038d 0800048d 0c00058d 1000068d 1400078d 1800088d 0800e003 00000000'),
}
PATCH_COLOR = {
    OFF_Y: H('60490008 0980023c'),                                   # j 0x80012580 ; lui v0,0x8009
    OFF_W: H('20564224 000041ac 040043ac 080044ac 8000013c 80802134 1400038e 00000000 17002314 00000426'
             '00005026 106c070c 0980023c 00009024 11004014 ffff4326 1e80013c 30b12124 42100300 21102200'
             '00004290 01006330 02006010 02190200 0f004330 0180013c 78292124 80180300 21082300 0000218c'
             '00000000 140001ae 0980023c 20564224 0000418c 0400438c 0800448c 2201e226 fad5000c 040002a6'
             '19c70008 00000000'),
}
DEFAULT_COLORS = H('ff660000 40bf4000 0066ff00 ff00cc00 ffcc0000 00803300 0000ff00 ad004500 ccff0000 00ffcc00'
              '7340bf00 ff000000 66ff0000 00ccff00 cc00ff00')        # RR GG BB 00 per group 0..14
OLD_JUMP = H('106c0708 00000624')                                   # v1 layout: j 0x801DB040 ; li a2,0

STOCK = {
    OFF_V: H('b8ff000c 07000424'),                                   # jal SD_SEPlayFull ; li a0,7
    OFF_Y: H('fad5000c 040002a6'),                                   # jal int_to_digits ; sh v0,4(s0)
    OFF_W: B('ZC4gOiBmaWxlIGFscmVhZHkgb3Blbi4KAAAAAEFjY2VzcyBEZW5pZWQuIDogZmlsZSBub3Qgb3Blbi4KAAAAAEFjY2VzcyBEZW5pZWQuIDogaW52YWxpZCBkYXRhIHNpemUgYWxpZ24KAAAAQWNjZXNzIERlbmllZC4gOiBpbnZhbGlkIG9mZnNldCB2YWx1ZSBhbGlnbgoAAAAAQWNjZXNzIERlbmll'),
    OFF_J: B('PE5VTEw+AAAAAAAAAAAAAE1ERUNfcmVzdDpiYWQgb3B0aW9uKCVkKQoAAABNREVDX2luX3N5bmMAAAAA'),
    OFF_K: B('RXJyb3I6IENhbid0IHB1c2ggbWF0cml4LHN0YWNrKG1heCAyMCkgaXMgZnVsbCEKAEVycm9yOiBDYW4ndCBwbw=='),
    OFF_G: B('LHN0YWNrIGlzIGVtcHR5IQoAVGhpcyBmdW5jdGlvbiBpcyBub3QgaW1wbGVtZW50'),
}
GROUPS = {0: 'Forbidden', 15: 'unrestricted'}


def load(p):
    d = bytearray(open(p, 'rb').read())
    if not (1782579 <= len(d) <= 2097152) or d[:8] != b'PS-X EXE':
        sys.exit('not a SLUS_014.11-sized PS-X EXE')
    return d


def has(d, table):
    return all(bytes(d[o:o + len(v)]) == v for o, v in table.items() if v)


def get_group(d, base, cid):            # cid 1..722
    b = d[base + (cid - 1) // 2]
    return b >> 4 if cid % 2 else b & 15


def set_group(d, base, cid, g):
    i = base + (cid - 1) // 2; b = d[i]
    d[i] = (g << 4) | (b & 15) if cid % 2 else (b & 0xF0) | g


def inspect(d):
    main = has(d, {k: v for k, v in PATCH.items() if k != OFF_G}); old = bytes(d[OFF_V:OFF_V + 8]) == OLD_JUMP
    color = has(d, PATCH_COLOR)
    print('main script  :', 'installed' if main else ('OLD layout (data at 0x1CB940)' if old else
          ('stock' if bytes(d[OFF_V:OFF_V + 8]) == STOCK[OFF_V] else 'unknown bytes at 0x2407C')))
    print('colour script:', 'installed' if color else ('stock' if bytes(d[OFF_Y:OFF_Y + 8]) == STOCK[OFF_Y] else 'unknown'))
    if not (main or old):
        return
    base = OFF_X if old and not main else OFF_Q
    groups = {}
    for cid in range(1, 723):
        g = get_group(d, base, cid)
        if g != 15:
            groups.setdefault(g, []).append(cid)
    for g in sorted(groups):
        print(f'  group {g:2d} ({GROUPS.get(g, "Limited " + str(g))}): {len(groups[g])} cards: {groups[g]}')
    if not groups:
        print('  no card limited')
    if color:
        cols = ' '.join('#%02x%02x%02x' % tuple(d[OFF_J + 4 * g:OFF_J + 4 * g + 3]) for g in range(15))
        print('  colours 0..14:', cols)


def apply(d, a):
    main = has(d, {k: v for k, v in PATCH.items() if k != OFF_G}); old = bytes(d[OFF_V:OFF_V + 8]) == OLD_JUMP
    fresh = not main
    if fresh and old:                                   # migrate old data zone -> new one
        nib = bytes(d[OFF_X:OFF_X + 361]); d[OFF_X:OFF_X + 361] = bytes(361); d[OFF_Q:OFF_Q + 361] = nib
    for o, v in PATCH.items():
        d[o:o + len(v)] = v
    if (fresh and not old) or a.reset:
        d[OFF_Q:OFF_Q + 361] = b'\xff' * 361
        d[OFF_J:OFF_J + 60] = DEFAULT_COLORS
    if a.colors or has(d, PATCH_COLOR):
        for o, v in PATCH_COLOR.items():
            d[o:o + len(v)] = v
        if not any(d[OFF_J:OFF_J + 60]):
            d[OFF_J:OFF_J + 60] = DEFAULT_COLORS
    for s in a.limit or []:
        c, g = (int(x, 0) for x in s.split('='))
        if not (1 <= c <= 722 and 0 <= g <= 15):
            sys.exit(f'bad --limit {s}')
        set_group(d, OFF_Q, c, g)
    if a.csv:
        for row in csv.reader(open(a.csv)):
            if row and row[0].strip().isdigit():
                set_group(d, OFF_Q, int(row[0]), int(row[1], 0) & 15)
    for s in a.color or []:
        g, rgb = s.split('='); g = int(g, 0); rgb = rgb.lstrip('#')
        d[OFF_J + 4 * g:OFF_J + 4 * g + 4] = bytes.fromhex(rgb) + b'\0'


def restore(d):
    for o, v in STOCK.items():
        d[o:o + len(v)] = v
    d[OFF_Z:OFF_X + 361] = bytes(OFF_X + 361 - OFF_Z)      # validator + both data zones were zero


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['inspect', 'apply', 'restore'])
    ap.add_argument('slus'); ap.add_argument('out', nargs='?')
    ap.add_argument('--colors', action='store_true'); ap.add_argument('--reset', action='store_true')
    ap.add_argument('--limit', action='append'); ap.add_argument('--color', action='append'); ap.add_argument('--csv')
    a = ap.parse_args(); d = load(a.slus)
    if a.cmd == 'inspect':
        inspect(d)
    else:
        if not a.out:
            sys.exit('need an output path')
        apply(d, a) if a.cmd == 'apply' else restore(d)
        open(a.out, 'wb').write(d); print('wrote', a.out)
