#!/usr/bin/env python3
"""Offline clone of TEA-Online's `extend/tools/data/dropUI` (Drop Editor UI).

The site tool edits the 40 per-duelist blocks inside WA_MRG.MRG.  Each block is
3 sectors (6144 bytes) and holds four 722-entry u16 weight lists plus the
rank-score table the game loads alongside them:

    block(char) = WA_MRG offset 0xE99800 + char * 0x1800        (sector 7475 + 3*char)
      +0x000  DECK    722 x u16 + 16 pad   -> gDuel_awOpponentDeckPool 0x801781D8
      +0x5B4  SA-POW  722 x u16 + 16 pad   -> gDuel_awSaPowCardDrops   0x8017878C
      +0xB68  BCD-PT  722 x u16 + 16 pad   -> gDuel_awBcdCardDrops     0x80178D40
      +0x111C SA-TEC  722 x u16 + 16 pad   -> gDuel_awSaTecCardDrops   0x801792F4
      +0x16D0 304 bytes                    -> gDuel_awRankScoreChange  0x801798A8

Every stock list sums to exactly 2048, which is the roll range of
Duel_SelectCardDrop / the deck builder.  This script never touches the trailing
304 bytes -- neither does the site tool.

Commands:
  verify      check all 160 lists (sum == 2048, padding zero)
  show        one character's lists, with card names if a SLUS is supplied
  names       the 40 duelist names read out of a SLUS_014.11 (text ids 808..847)
  export      all 40x4 lists -> JSON
  apply       JSON -> WA_MRG.MRG (byte-exact inverse of export)
  unobtainable  cards no duelist can ever drop (the tool's third tab)
  randomize   the tool's "Randomize" button, seedable
  balance     the tool's "Auto balance" (rescale a list to sum 2048)
"""
import argparse, json, random, struct, sys

BASE      = 15308800        # 0xE99800, the tool's default baseOffset
CHAR_SIZE = 6144            # k
LIST_SIZE = 2 * 722 + 16    # y = 1460
NCARDS    = 722             # _
NLISTS    = 4               # w
NCHARS    = 40              # x
SUM       = 2048            # defaultSumTarget
LIST_NAMES = ["DECK", "SA-POW", "BCD-PT", "SA-TEC"]
CRYPT_KEY, CRYPT_SHIFT = 2512, 3

WA_LBA = 10102              # /DATA/WA_MRG.MRG on the US disc


def slot_off(base, char, lst, card1):          # getSlotOffset()
    return base + char * CHAR_SIZE + lst * LIST_SIZE + 2 * (card1 - 1)


def read_list(buf, base, char, lst, mask=0, crypted=False):
    o = slot_off(base, char, lst, 1)
    v = list(struct.unpack_from('<%dH' % NCARDS, buf, o))
    if crypted:
        return [max(0, (x - CRYPT_KEY) >> CRYPT_SHIFT) for x in v]
    return [x - mask for x in v]


def write_list(buf, base, char, lst, vals, mask=0, crypted=False, rng=random):
    o = slot_off(base, char, lst, 1)
    out = []
    for v in vals:
        v = min(65535, max(0, round(v + mask)))
        if crypted:
            v = (8 * v + CRYPT_KEY + rng.randrange(7)) & 0xFFFF
        out.append(v)
    struct.pack_into('<%dH' % NCARDS, buf, o, *out)


# ------------------------------------------------- SLUS text (chunk-common) --
CHARMAP = {3:'a',21:'b',15:'c',12:'d',1:'e',19:'f',16:'g',9:'h',5:'i',52:'j',
    22:'k',10:'l',14:'m',6:'n',4:'o',20:'p',55:'q',8:'r',7:'s',2:'t',13:'u',
    25:'v',18:'w',54:'x',17:'y',50:'z',24:'A',45:'B',43:'C',32:'D',37:'E',
    49:'F',41:'G',35:'H',26:'I',59:'J',51:'K',42:'L',30:'M',44:'N',33:'O',
    47:'P',62:'Q',38:'R',29:'S',28:'T',53:'U',57:'V',34:'W',70:'X',36:'Y',
    63:'Z',48:'-',27:"'",64:'"',31:',',67:'&',85:'@',60:'#',68:'/',72:':',
    80:'*',81:'>',84:'<',86:'+',23:'!',0:' ',56:'0',61:'1',58:'2',65:'3',
    74:'4',66:'5',78:'6',69:'7',87:'8',89:'9',11:'.',76:'(',75:')',46:'?',
    39:'[',40:']',239:' ',226:' '}
NAME_TABLE = 1859584        # 0x1C6000 -- getCardInfo()'s `offset`


def slus_name(slus, idx):
    lo = slus[NAME_TABLE + 2 * idx]
    hi = slus[NAME_TABLE + 2 * idx + 1]
    p = NAME_TABLE + lo + 256 * hi - 22528
    s, i = "", 0
    while i < 50:
        b = slus[p + i]
        if b == 255:
            break
        if b in CHARMAP:
            s += CHARMAP[b]
        elif b == 248:                     # colour escape: skip the next byte
            i += 2
        i += 1
    return s


def card_names(slus):
    return [slus_name(slus, i) for i in range(1, NCARDS + 1)]


def opp_names(slus):
    return [slus_name(slus, i) for i in range(808, 848)]


# ------------------------------------------------------------------ commands -
def load(a):
    buf = bytearray(open(a.wa, 'rb').read())
    slus = open(a.slus, 'rb').read() if getattr(a, 'slus', None) else None
    return buf, slus


def names_of(slus):
    return opp_names(slus) if slus else ["Character %d" % i for i in range(NCHARS)]


def cmd_verify(a):
    buf, _ = load(a)
    bad = 0
    for c in range(NCHARS):
        for l in range(NLISTS):
            v = read_list(buf, a.base, c, l)
            s = sum(v)
            o = slot_off(a.base, c, l, 1)
            pad = buf[o + 2 * NCARDS:o + LIST_SIZE]
            if s != SUM or any(pad):
                bad += 1
                print("char %2d %-6s sum=%-6d pad=%s" % (c, LIST_NAMES[l], s, pad.hex()))
    print("checked %d lists at base %d (0x%X); %d anomalies"
          % (NCHARS * NLISTS, a.base, a.base, bad))
    print("in-file sector %d, disc LBA %d, region %d..%d bytes"
          % (a.base // 2048, WA_LBA + a.base // 2048, a.base, a.base + NCHARS * CHAR_SIZE))


def cmd_show(a):
    buf, slus = load(a)
    cn = card_names(slus) if slus else None
    nm = names_of(slus)
    lists = range(NLISTS) if a.list is None else [LIST_NAMES.index(a.list)]
    print("char %d  %s   block @%d (0x%X) sector %d / LBA %d"
          % (a.char, nm[a.char], a.base + a.char * CHAR_SIZE,
             a.base + a.char * CHAR_SIZE,
             (a.base + a.char * CHAR_SIZE) // 2048,
             WA_LBA + (a.base + a.char * CHAR_SIZE) // 2048))
    for l in lists:
        v = read_list(buf, a.base, a.char, l, a.mask, a.crypted)
        nz = [(i + 1, x) for i, x in enumerate(v) if x]
        print("  %-6s sum=%d  entries=%d" % (LIST_NAMES[l], sum(v), len(nz)))
        if not a.quiet:
            for cid, w in nz:
                print("      %3d %5d  %5.2f%%  %s"
                      % (cid, w, 100.0 * w / SUM, cn[cid - 1] if cn else ""))


def cmd_names(a):
    slus = open(a.slus, 'rb').read()
    for i, n in enumerate(opp_names(slus)):
        print("%2d  text id %d  %s" % (i, 808 + i, n))


def cmd_export(a):
    buf, slus = load(a)
    out = dict(base=a.base, mask=a.mask,
               opponents=names_of(slus),
               lists=LIST_NAMES,
               data=[[read_list(buf, a.base, c, l, a.mask, a.crypted)
                      for l in range(NLISTS)] for c in range(NCHARS)])
    json.dump(out, open(a.out, 'w'))
    print("wrote %s (%d chars x %d lists x %d cards)"
          % (a.out, NCHARS, NLISTS, NCARDS))


def cmd_apply(a):
    buf, _ = load(a)
    j = json.load(open(a.json))
    rng = random.Random(a.seed)
    for c in range(NCHARS):
        for l in range(NLISTS):
            if a.only and LIST_NAMES[l] not in a.only:
                continue
            write_list(buf, a.base, c, l, j['data'][c][l], a.mask, a.crypted, rng)
    open(a.out or a.wa, 'wb').write(buf)
    print("wrote %s" % (a.out or a.wa))


def cmd_unobtainable(a):
    """The tool's third tab: chars 1..39, drop lists only (SA-POW/BCD-PT/SA-TEC)."""
    buf, slus = load(a)
    cn = card_names(slus) if slus else None
    miss = []
    for cid in range(1, NCARDS + 1):
        ok = False
        for c in range(1, NCHARS):
            for l in (1, 2, 3):
                if read_list(buf, a.base, c, l, a.mask, a.crypted)[cid - 1] > 0:
                    ok = True
                    break
            if ok:
                break
        if not ok:
            miss.append(cid)
    print("%d card(s) with no drop weight on any duelist 1..39:" % len(miss))
    for cid in miss:
        print("   %3d  %s" % (cid, cn[cid - 1] if cn else ""))


def cmd_randomize(a):
    """randomizeList(): 20..69 random cards, random weights rescaled to sumTarget."""
    buf, _ = load(a)
    rng = random.Random(a.seed)
    chars = range(NCHARS) if a.char is None else [a.char]
    lists = range(NLISTS) if a.list is None else [LIST_NAMES.index(a.list)]
    for c in chars:
        for l in lists:
            v = [0] * NCARDS
            n = min(NCARDS, rng.randrange(50) + 20)
            idx = rng.sample(range(NCARDS), n)
            w = [99 * rng.random() + 1 for _ in idx]
            f = a.target / sum(w)
            tot, best, bi = 0, -1e30, 0
            for k, x in enumerate(w):
                q = max(1, round(x * f))
                v[idx[k]] = q
                tot += q
                if x > best:
                    best, bi = x, k
            v[idx[bi]] = max(0, v[idx[bi]] + (a.target - tot))
            write_list(buf, a.base, c, l, v, a.mask, a.crypted, rng)
    open(a.out or a.wa, 'wb').write(buf)
    print("randomized -> %s" % (a.out or a.wa))


def cmd_balance(a):
    """autoBalanceList(): scale the non-zero entries so the list sums to target."""
    buf, _ = load(a)
    v = read_list(buf, a.base, a.char, LIST_NAMES.index(a.list), a.mask, a.crypted)
    nz = [(i, x) for i, x in enumerate(v) if x > 0]
    tot = sum(x for _, x in nz)
    if not nz or tot == 0:
        sys.exit("list is empty")
    f = a.target / tot
    acc, big = 0, nz[0]
    for i, x in nz:
        q = max(1, round(x * f))
        v[i] = q
        acc += q
        if x > big[1]:
            big = (i, x)
    v[big[0]] = max(0, v[big[0]] + (a.target - acc))
    write_list(buf, a.base, a.char, LIST_NAMES.index(a.list), v, a.mask, a.crypted)
    open(a.out or a.wa, 'wb').write(buf)
    print("balanced char %d %s to %d -> %s" % (a.char, a.list, a.target, a.out or a.wa))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', type=lambda s: int(s, 0), default=BASE,
                   help="WA_MRG offset of char 0's block (default %d / 0x%X)" % (BASE, BASE))
    p.add_argument('--mask', type=int, default=0, help="the tool's 'mascara'")
    p.add_argument('--crypted', action='store_true',
                   help="mod stores weights as 8*v+2512+rand(0..6)")
    sub = p.add_subparsers(dest='cmd', required=True)

    def wa(q, slus=True):
        q.add_argument('wa')
        if slus:
            q.add_argument('--slus', help="SLUS_014.11, for card / duelist names")
        return q

    wa(sub.add_parser('verify'), slus=False).set_defaults(func=cmd_verify)

    q = wa(sub.add_parser('show'))
    q.add_argument('--char', type=int, default=0)
    q.add_argument('--list', choices=LIST_NAMES)
    q.add_argument('--quiet', action='store_true')
    q.set_defaults(func=cmd_show)

    q = sub.add_parser('names')
    q.add_argument('slus')
    q.set_defaults(func=cmd_names)

    q = wa(sub.add_parser('export'))
    q.add_argument('-o', '--out', default='drops.json')
    q.set_defaults(func=cmd_export)

    q = wa(sub.add_parser('apply'), slus=False)
    q.add_argument('json')
    q.add_argument('-o', '--out')
    q.add_argument('--only', nargs='*', choices=LIST_NAMES)
    q.add_argument('--seed', type=int, default=None)
    q.set_defaults(func=cmd_apply)

    wa(sub.add_parser('unobtainable')).set_defaults(func=cmd_unobtainable)

    q = wa(sub.add_parser('randomize'), slus=False)
    q.add_argument('--char', type=int)
    q.add_argument('--list', choices=LIST_NAMES)
    q.add_argument('--target', type=int, default=SUM)
    q.add_argument('--seed', type=int, default=None)
    q.add_argument('-o', '--out')
    q.set_defaults(func=cmd_randomize)

    q = wa(sub.add_parser('balance'), slus=False)
    q.add_argument('--char', type=int, required=True)
    q.add_argument('--list', choices=LIST_NAMES, required=True)
    q.add_argument('--target', type=int, default=SUM)
    q.add_argument('-o', '--out')
    q.set_defaults(func=cmd_balance)

    a = p.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
