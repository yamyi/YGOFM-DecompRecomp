#!/usr/bin/env python3
"""Offline clone of TEA-Online's "XYZ & Synchro" process tool (extend/tools/process/xyzsynchros).

  xyz_synchro.py inspect SLUS_014.11 WA_MRG.MRG
  xyz_synchro.py apply   SLUS_014.11 WA_MRG.MRG out.11 out.mrg [--xyz L,T=CARD ...] [--synchro S,T=CARD ...]
                         [--tuner CARD ...] [--csv f] [--field N] [--clear]
  xyz_synchro.py export  WA_MRG.MRG out.csv [--field N]
  xyz_synchro.py restore SLUS_014.11 WA_MRG.MRG out.11 out.mrg

L = level 1..15, S = summed level 2..15, T = monster type 0..19, CARD = result card id 1..722.
CSV rows: xyz,L,T,CARD | synchro,S,T,CARD | tuner,CARD.  Without --field the tables are written into
all 7 field copies of the duel data (the site's default "repeat data in all the fields").

What it does (see ../README.md): fusion_table_lookup (0x80019A60) is redirected to a 464-byte routine
living in the last 1728 bytes of the 64 KB fusion-table block (RAM 0x8018BC18, WA_MRG 0xB97140 +
k*0x75800).  XYZ: two monsters of the same level and type -> xyz[L-1][T].  Synchro: exactly one of the
two is a tuner, same type -> synchro[L1+L2-2][T].  Otherwise the stock fusion search runs.
WARNING: on a stock WA_MRG those 1728 bytes hold the fusion records of cards 581..712 (offsets
0xF938..0xFDEC of the block); installing over them corrupts those cards' fusions.  restore puts the
stock bytes back.
"""
import argparse, base64, csv, struct, sys

SLUS_HOOK = 0xA260                                # RAM 0x80019A60
HOOK_PATCH = bytes.fromhex('062f0608 00000000'.replace(' ', ''))   # j 0x8018BC18 ; nop
HOOK_STOCK = bytes.fromhex('1880023c d8c24324'.replace(' ', ''))   # lui v0,0x8018 ; addiu v1,v0,-0x3D28
WA_CODE, WA_XYZ, WA_SYN, WA_TUN = 0xB97140, 0xB97310, 0xB97570, 0xB977A0
FIELD_STRIDE = 0x75800; N_FIELDS = 7
CODE = bytes.fromhex(
    '1d80023c 32534224 21184400 00006390 00000000 0f006330 21304500 0000c690 00000000 0f00c630'
    '5f006010 00000000 5d00c010 00000000 1c006614 00000000 1d80023c 40424224 80400400 21304800'
    '0000c68c 00000000 82360600 80400500 21384800 0000e78c 00000000 823e0700 0e00c714 00000000'
    'ffff6324 80400300 21400301 c0180800 21186600 21186600 1980083c e8bd0825 21400301 00000295'
    '00000000 45004014 00000000 1980023c 78c24224 c2380400 21404700 00000891 07008730 08000324'
    '23386700 0640e800 01000331 c2380500 21404700 00000891 0700a730 08000624 2338c700 0640e800'
    '01000631 21186600 01000624 2a006614 00000000 1d80023c 40424224 80400400 21304800 0000c68c'
    '00000000 82360600 80400500 21384800 0000e78c 00000000 823e0700 1c00c714 00000000 1d80023c'
    '32534224 21184400 00006390 00000000 0f006330 21304500 0000c690 00000000 0f00c630 21186600'
    '01000824 2b400301 0d000011 00000000 feff6324 80400300 21400301 c0180800 21186700 21186700'
    '1980083c 48c00825 21400301 00000295 06004014 00000000 00000224 1880023c d8c24324 9a660008'
    '00000000 0800e003 00000000 00000000 00000000 00000000'.replace(' ', ''))
assert len(CODE) == 464
STOCK_TAIL = base64.b64decode(
    'oMrTCqZL408TqlVzVnNqXHNf46pvE3VzqngTgnMCZlvAYswMqlBGWEaqZEZtRqpuRnFGqnJGdEaqd0Z7RmqBRonvDWZKnVWnZlacW5mmXJxyHmp0g3WcZnudgZ1mgpyJnQbImQ1mTP9N/yZPyFZAJlsmXEBmYd9s/yZvyHVAYoJAg50ChIUHZlnjYONmaONylGZ043fjBnnjFapObFB+YlRjVeemVudYfmpbO1znqmR+bX6qbn5xfqpyfnR+pnXnd36qe36BfqaC54l+Csg7FqpObFB+YlRjVeemVudYfmpbO1znqmR+bX6qbn5xfqpyfnR+pnXnd36qe36BfiaC54Sdqol+yDsUqlATUQaqUhNYE6ZbqmQTqmoTbROqbhNxE6pyE3MTqnQTdxOqexN+EyqBE4T0aokTyKoZqlBGVXOqVnNYRqpZRlxzqmBGZEaqaEZsfqptRm5Gqm8TcUaqckZ0Rqp1c3dGqngTeUaqe0Z9fqqBRoJzBonvBWpTCFvAqm8GfAgGyLsEqls7bxOqeBPIOwJmhNPK0wQqWyFsYyJ9Y8gnFWpYc1njpmDjZHNmaONs56ptc25zqnFzcnOqdHN3c6Z543tzpn3nfnNqgXODp2qEEYinColzFmpYc1njZmDjYstqZHNo46Zs521zqm5zcXOqcnN0c2p3c3njantzfeeqfnOBc6aDp4QRpoiniXMBBlvADCpZRlsKqlxzYEaqaEZsfqpvE3VzqngTeUaqfX6Ccw5mXONf46pkRm1Gqm5GcUaqckZ0RqZ143dGqntGgUZmguOJ7wJmW8BizBhiXB9dwGZewGKpYmMfZ8AqbDttCyZvqnBJInFJdApmeKp6wKZ7Jn07Kn47gQtmg5mGwGaHwIiZIokLzycUZmDjYstqZHNo46Zs521zqm5zcXOqcnN0c2p3c3njantzfeeqfnOBc6aDp4QRpoiniXMBBmLMAQZizAZmYONo42ZylHTjZnfjeeMMqmRGbUaqbkZxRqpyRnRGpnXjd0aqe0aBRmaC44nvAQZ73w1mZM5nzGZrym7KZnTOdctmd8p6zGaCy4bMqsJlx2UKyGUJqmhGbH6qbxN1c6p4E3lGqn1+gnMGie8Lqm1GbkaqcUZyRmp0RnXjqndGe0ZqgUaC4waJ7wKqbxN4EwyqbX5ufqpxfnJ+anR+deeqd357fmqBfoLnqol+yDsHqm8TdXOqeBN5Rqp9foJzAoQPB6pvE3VzqngTeUaqfX6CcwaJ7wqqcRNyE6pzE3QTqncTexOqfhOBE2qJE8iqBap1c3gTqnlGfX4KgnMGqnVzeBOqeUZ9fqqCc4MeAQp4EwWqdXN4E6p5Rn1+CoJzCmp3c3njantzfeeqfnOBc6aDp4QRpoiniXMEqngTeUaqfX6CcwWqexN+E6qBE4kTBsiqBKp7RoFGZoLjie8Eqn1+gnMmg52EhQOmhNOroAbK0wRqgX6C56qJfsg7AqqCc8g7A2qCc4OdAoQPBKaDp4QRpoiniXMCZomdyJkBAokPAQbImQEKkKcCqpKblqkBCpGxAQqysQOqkpmUtwapRQEGk1UBCremAQqxsgEKsJcBAs8n////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////')
assert len(STOCK_TAIL) == 1728


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


def fields(a):
    return [a.field - 1] if getattr(a, 'field', None) else range(N_FIELDS)


def read_tables(w, k):
    o = k * FIELD_STRIDE
    xyz = struct.unpack('<300H', w[WA_XYZ + o:WA_XYZ + o + 600])
    syn = struct.unpack('<280H', w[WA_SYN + o:WA_SYN + o + 560])
    tun = [8 * i + b + 1 for i in range(91) for b in range(8) if w[WA_TUN + o + i] & (0x80 >> b)]
    return xyz, syn, tun


def inspect(slus, wa):
    d = load_slus(slus); w = load_wa(wa)
    hb = bytes(d[SLUS_HOOK:SLUS_HOOK + 8])
    print('SLUS hook :', 'installed' if hb == HOOK_PATCH else 'stock' if hb == HOOK_STOCK else 'unknown ' + hb.hex())
    for k in range(N_FIELDS):
        o = k * FIELD_STRIDE
        blk = bytes(w[WA_CODE + o:WA_CODE + o + 464])
        st = 'code installed' if blk == CODE else 'stock fusion records' if bytes(w[WA_CODE + o:WA_CODE + o + 1728]) == STOCK_TAIL else 'other data'
        xyz, syn, tun = read_tables(w, k)
        print(f'field {k + 1} (WA {WA_CODE + o:#x}): {st}; xyz entries {sum(1 for v in xyz if v)}, '
              f'synchro entries {sum(1 for v in syn if v)}, tuners {len(tun)}')
        if k == 0 or getattr(inspect, 'verbose', False):
            for i, v in enumerate(xyz):
                if v: print(f'   xyz     level {i // 20 + 1:2d} type {i % 20:2d} -> card {v}')
            for i, v in enumerate(syn):
                if v: print(f'   synchro sum   {i // 20 + 2:2d} type {i % 20:2d} -> card {v}')
            if tun: print('   tuners:', tun)


def export(w, out, a):
    k = (a.field or 1) - 1
    xyz, syn, tun = read_tables(w, k)
    with open(out, 'w', newline='') as f:
        c = csv.writer(f)
        for i, v in enumerate(xyz):
            if v: c.writerow(['xyz', i // 20 + 1, i % 20, v])
        for i, v in enumerate(syn):
            if v: c.writerow(['synchro', i // 20 + 2, i % 20, v])
        for t in tun: c.writerow(['tuner', t])


def apply(d, w, a):
    d[SLUS_HOOK:SLUS_HOOK + 8] = HOOK_PATCH
    entries = []
    for s in a.xyz or []:
        lt, c = s.split('='); l, t = (int(x) for x in lt.split(',')); entries.append(('xyz', l, t, int(c)))
    for s in a.synchro or []:
        lt, c = s.split('='); l, t = (int(x) for x in lt.split(',')); entries.append(('synchro', l, t, int(c)))
    for s in a.tuner or []:
        entries.append(('tuner', int(s)))
    if a.csv:
        for r in csv.reader(open(a.csv)):
            if r and r[0] in ('xyz', 'synchro'): entries.append((r[0], int(r[1]), int(r[2]), int(r[3])))
            elif r and r[0] == 'tuner': entries.append(('tuner', int(r[1])))
    for k in fields(a):
        o = k * FIELD_STRIDE
        fresh = bytes(w[WA_CODE + o:WA_CODE + o + 464]) != CODE
        w[WA_CODE + o:WA_CODE + o + 464] = CODE
        if fresh or a.clear:
            w[WA_CODE + o + 464:WA_CODE + o + 1728] = bytes(1728 - 464)
        for e in entries:
            if e[0] == 'tuner':
                c = e[1]; w[WA_TUN + o + (c - 1) // 8] |= 0x80 >> ((c - 1) % 8)
            else:
                _, l, t, c = e
                base, row = (WA_XYZ, l - 1) if e[0] == 'xyz' else (WA_SYN, l - 2)
                if not (0 <= t < 20 and 0 <= row < (15 if e[0] == 'xyz' else 14) and 0 <= c <= 722):
                    sys.exit(f'bad entry {e}')
                struct.pack_into('<H', w, base + o + 2 * (20 * row + t), c)


def restore(d, w):
    d[SLUS_HOOK:SLUS_HOOK + 8] = HOOK_STOCK
    for k in range(N_FIELDS):
        o = k * FIELD_STRIDE
        w[WA_CODE + o:WA_CODE + o + 1728] = STOCK_TAIL


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['inspect', 'apply', 'export', 'restore'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--xyz', action='append'); ap.add_argument('--synchro', action='append'); ap.add_argument('--tuner', action='append')
    ap.add_argument('--csv'); ap.add_argument('--field', type=int); ap.add_argument('--clear', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'inspect':
        inspect(*a.args[:2])
    elif a.cmd == 'export':
        export(load_wa(a.args[0]), a.args[1], a)
    else:
        slus, wa, o1, o2 = a.args[:4]
        d = load_slus(slus); w = load_wa(wa)
        apply(d, w, a) if a.cmd == 'apply' else restore(d, w)
        open(o1, 'wb').write(d); open(o2, 'wb').write(w); print('wrote', o1, o2)
