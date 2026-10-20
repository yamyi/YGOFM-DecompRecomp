#!/usr/bin/env python3
"""Offline clone of TEA-Online's "More Opponents" process tool (extend/tools/process/moreopponets).

  more_opponents.py inspect SLUS_014.11 [WA_MRG.MRG]
  more_opponents.py apply   SLUS_014.11 out.11                      install the u8-weight code in the EXE
  more_opponents.py reduce  WA_MRG.MRG out.mrg                      stock u16 pools -> u8 pools, bank 1 = copy of bank 0
  more_opponents.py export  WA_MRG.MRG out.csv [--u16]              dump 78 (or 39 stock) opponents x 4 pools
  more_opponents.py import  WA_MRG.MRG out.mrg in.csv               write u8 pools from CSV (site template layout)
  more_opponents.py restore SLUS_014.11 out.11                      stock EXE bytes
  more_opponents.py restore-wa WA_MRG.MRG out.mrg --stock stock.mrg copy the stock 39 x 0x1800 table back

CSV layout (== the site's MoreOpponetsTemplate.xlsx from column C, row 6): one row per card 1..722,
then 4 columns per opponent: DECK, SAPOW, BCDPT, STEC, for opponents 1..78.  Every pool should sum
to 2048; values are stored modulo 256 (that is what the site does too).

How it works (see ../README.md): opponent id bit 6 (0x40) selects "bank 1": the id is masked to
0..63 before it is stored in gDuel_bOpponentID, and a u16 at 0x80011D40 receives 0 or 722, which
Duel_ShuffleDeck and Duel_SelectCardDrop add to their pool pointer while reading u8 weights (lhu ->
lbu, stride 2 -> 1).  WA_MRG keeps the same 39 x 0x1800 blocks at 0xE9B000 (in-file sector 0x1D36,
disc LBA 11 + 0x1D36), each pool 1460 bytes: bank 0 = u8[722], bank 1 = u8[722] right after it.
"""
import argparse, base64, csv, struct, sys

H = lambda s: bytes.fromhex(s.replace(' ', ''))
WA_TABLE = 0xE9B000; OPP_STRIDE = 0x1800; POOL_STRIDE = 1460; N_OPP = 39; POOLS = ('DECK', 'SAPOW', 'BCDPT', 'STEC')

PATCH = {
    0x2540: bytes(16) + H('0180013c 401d2124 40 00a330 00000000 02006010 00000324 d2020324 3f00a530 000023a4'
                          '0a80013c 5ce10008 61b325a0 0180023c 401d4224 00004394 00000000 21b8e302 00000000'
                          '21980000 1000b427 16910008 00000000 0180043c 401d8424 00008394 00000000 21800302'
                          '00000000 ff074230 01004524 14860008 00000000'),
    0x12048: H('6a470008 00000000'),      # Duel_SelectCardDrop: j 0x80011DA8
    0x1205B: b'\x92',                     # lhu v0,0(s0) -> lbu
    0x1207C: b'\x01',                     # addiu s0,s0,2 -> 1
    0x14C50: H('60470008 00000000'),      # Duel_ShuffleDeck: j 0x80011D80
    0x14C77: b'\x90',                     # lhu v0,0(v1) -> lbu
    0x14CD4: b'\x01',                     # addiu v1,v1,2 -> 1
    0x28D68: H('54470008 00000000'),      # func_80038530 (script opcode): j 0x80011D50
}
STOCK = {
    0x2540: base64.b64decode('eW5jAENEX3JlYWR5AAAAACVzLi4uCgAAJXM6IG5vIHBhcmFtCgAAAENEX2N3AAAAJElkOiBiaW9zLmMsdiAxLjg2IDE5OTcvMDMvMjggMDc6NDI6NDIgbWFrb3RvIEV4cCB5b3MgJABDRF9pbml0OgAAAABhZGRyPSUwOHgKAABDRF9kYXRhc3luYwAAAAAA'),
    0x12048: H('ff074230 01004524'), 0x1205B: b'\x96', 0x1207C: b'\x02',
    0x14C50: H('21980000 1000b427'), 0x14C77: b'\x94', 0x14CD4: b'\x02',
    0x28D68: H('0a80013c 61b325a0'),
}


def load_slus(p):
    d = bytearray(open(p, 'rb').read())
    if not (1048576 <= len(d) <= 5242880) or d[:8] != b'PS-X EXE':
        sys.exit('not a SLUS_014.11-sized PS-X EXE')
    return d


def load_wa(p):
    d = bytearray(open(p, 'rb').read())
    if not (36700160 <= len(d) <= 45088768):
        sys.exit('not a WA_MRG.MRG-sized file')
    return d


def has(d, t):
    return all(bytes(d[o:o + len(v)]) == v for o, v in t.items())


def pool_off(opp, pool):                 # opp 0..77, pool 0..3
    return WA_TABLE + OPP_STRIDE * (opp % N_OPP) + POOL_STRIDE * pool + (722 if opp >= N_OPP else 0)


def inspect(slus, wa):
    d = load_slus(slus)
    print('SLUS:', 'process installed' if has(d, PATCH) else ('stock' if has(d, STOCK) else 'unknown/other patch at the 8 sites'))
    if wa:
        w = load_wa(wa)
        u16 = [sum(struct.unpack('<722H', w[pool_off(o, p):pool_off(o, p) + 1444])) for o in range(3) for p in range(4)]
        print('WA_MRG first 3 opponents, u16 pool sums:', u16, '(2048 each = stock u16 layout)')
        u8 = [sum(w[pool_off(o, p):pool_off(o, p) + 722]) for o in range(3) for p in range(4)]
        print('                           u8 pool sums :', u8, '(2048 each = reduced/u8 layout)')


def reduce(w):
    for o in range(N_OPP):
        for p in range(4):
            b = pool_off(o, p)
            vals = struct.unpack('<722H', w[b:b + 1444])
            u8 = bytes(v % 256 for v in vals)
            w[b:b + 722] = u8; w[b + 722:b + 1444] = u8


def export(w, out, u16):
    with open(out, 'w', newline='') as f:
        c = csv.writer(f)
        n = N_OPP if u16 else 2 * N_OPP
        c.writerow(['card'] + [f'{i + 1}:{p}' for i in range(n) for p in POOLS])
        for card in range(722):
            row = [card + 1]
            for o in range(n):
                for p in range(4):
                    b = pool_off(o, p)
                    row.append(struct.unpack_from('<H', w, b + 2 * card)[0] if u16 else w[b + card])
            c.writerow(row)


def imp(w, csvp):
    rows = [r for r in csv.reader(open(csvp)) if r and r[0].strip().isdigit()]
    if len(rows) != 722:
        sys.exit(f'expected 722 card rows, got {len(rows)}')
    for r in rows:
        card = int(r[0]) - 1
        for i, v in enumerate(r[1:1 + 2 * N_OPP * 4]):
            o, p = divmod(i, 4)
            w[pool_off(o, p) + card] = (int(v or 0)) % 256


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['inspect', 'apply', 'reduce', 'export', 'import', 'restore', 'restore-wa'])
    ap.add_argument('src'); ap.add_argument('out', nargs='?'); ap.add_argument('extra', nargs='?')
    ap.add_argument('--u16', action='store_true'); ap.add_argument('--stock')
    a = ap.parse_args()
    if a.cmd == 'inspect':
        inspect(a.src, a.out); return
    if not a.out:
        sys.exit('need an output path')
    if a.cmd in ('apply', 'restore'):
        d = load_slus(a.src)
        for o, v in (PATCH if a.cmd == 'apply' else STOCK).items():
            d[o:o + len(v)] = v
        open(a.out, 'wb').write(d)
    elif a.cmd == 'export':
        export(load_wa(a.src), a.out, a.u16)
    else:
        w = load_wa(a.src)
        if a.cmd == 'reduce':
            reduce(w)
        elif a.cmd == 'import':
            imp(w, a.extra)
        else:
            if not a.stock:
                sys.exit('restore-wa needs --stock <stock WA_MRG.MRG> (the u16 -> u8 reduction is lossy)')
            s = open(a.stock, 'rb').read()
            w[WA_TABLE:WA_TABLE + N_OPP * OPP_STRIDE] = s[WA_TABLE:WA_TABLE + N_OPP * OPP_STRIDE]
        open(a.out, 'wb').write(w)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
