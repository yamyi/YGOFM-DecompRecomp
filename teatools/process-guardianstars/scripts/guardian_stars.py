#!/usr/bin/env python3
"""Offline clone of TEA-Online's GUARDIAN STARS tool (extend/tools/process/guardianstars).

Replaces Duel_CalcGuardianStarMatchup (0x8002CB80) with a table-driven version and
installs a 16 x u16 "who beats whom" bitmask table (default home 0x80011A80).

  guardian_stars.py inspect SLUS_014.11
  guardian_stars.py apply   SLUS_014.11 out.11 [--data-addr 0x80011A80]
  guardian_stars.py set     SLUS_014.11 out.11 --beats 1:2 [--beats ...]
  guardian_stars.py clear   SLUS_014.11 out.11 --beats 1:2
  guardian_stars.py restore SLUS_014.11 out.11

Star ids are 1..15 as the game numbers them (1 Mars .. 10 Venus; 11-15 are spare
slots with no name string).  "--beats A:B" means star A wins (+500 ATK/DEF) over
star B; like the site's UI this also clears the reverse edge.
"""
import argparse, struct, sys

RAM_CODE = 0x8002CB80          # Duel_CalcGuardianStarMatchup
RAM_DATA = 0x80011A80          # default table home (dead libspu debug strings)
OFF_CODE = 0x1D380
OFF_HI   = 0x1D388             # lui   v0, %hi(table)     immediate (u16)
OFF_LO   = 0x1D38C             # addiu v0, v0, %lo(table) immediate (s16)

STAR_NAMES = ["Mars", "Jupiter", "Saturn", "Uranus", "Pluto", "Neptune",
              "Mercury", "Sun", "Moon", "Venus",
              "(11)", "(12)", "(13)", "(14)", "(15)"]

# 24 instruction words, verbatim from the tool's mainScript blob.  The two
# address immediates live at +8 (lui) and +12 (addiu) and are rewritten by
# set_hilo() when a custom data address is used.
PATCH = bytes.fromhex(
    "24 84 ff ff  24 a5 ff ff  3c 02 80 01  24 42 1a 80"
    "00 05 18 40  00 43 18 21  94 63 00 00  00 00 00 00"
    "00 83 18 06  30 63 00 01  14 60 00 0a  24 03 fe 0c"
    "00 04 18 40  00 43 18 21  94 63 00 00  00 00 00 00"
    "00 a3 18 06  30 63 00 01  14 60 00 02  24 03 01 f4"
    "24 03 00 00  00 60 10 21  03 e0 00 08  00 00 00 00".replace(" ", ""))
PATCH = b"".join(PATCH[i:i + 4][::-1] for i in range(0, len(PATCH), 4))  # -> little endian

# The complete stock function (29 instructions, 0x8002CB80..0x8002CBF4).
STOCK_CODE = bytes.fromhex(
    "f9ff84240600800406000324f9ffa5240700a10404000324"
    "0800e00321100000ffffa5242a10a300fbff401021208300"
    "010084242a10830002004014000000002120000003008514"
    "feff84240800e003f4010224020081040000000021208300"
    "020085100cfe0224211000000800e00300000000")

# 32 stock bytes at 0x80011A80: the tail of the PsyQ string "wait (wrdy H -> L)"
# plus the whole of "wait (dmaf clear/W)".
STOCK_DATA = bytes.fromhex(
    "64792048202d3e204c290000776169742028646d616620636c6561722f572900")

# The wheel the tool's default bonusData writes: exactly the stock behaviour.
DEFAULT_TABLE = [0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0001,
                 0x0080, 0x0100, 0x0200, 0x0040, 0, 0, 0, 0, 0, 0]


def load(p):
    d = bytearray(open(p, "rb").read())
    if not (1782579 <= len(d) <= 8388608) or d[:8] != b"PS-X EXE":
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d


def slusoff(ram):
    return ram - 0x80010000 + 0x800


def is_patched(d):
    """The site's own check: every patch byte except the two address immediates."""
    cur = bytes(d[OFF_CODE:OFF_CODE + 96])
    return (cur[0:8] == PATCH[0:8] and cur[10:12] == PATCH[10:12]
            and cur[14:96] == PATCH[14:96])


def data_addr(d):
    hi = struct.unpack_from("<H", d, OFF_HI)[0]
    lo = struct.unpack_from("<h", d, OFF_LO)[0]
    return ((hi << 16) + lo) & 0xFFFFFFFF


def set_hilo(d, ram):
    lo = ram & 0xFFFF
    hi = ((ram >> 16) & 0xFFFF) + (1 if lo > 0x7FFF else 0)
    struct.pack_into("<H", d, OFF_HI, hi & 0xFFFF)
    struct.pack_into("<H", d, OFF_LO, lo)


def read_table(d, ram):
    return list(struct.unpack_from("<16H", d, slusoff(ram)))


def write_table(d, ram, tab):
    struct.pack_into("<16H", d, slusoff(ram), *tab)


def show(tab):
    for i, m in enumerate(tab):
        if not m and i >= 10:
            continue
        wins = [STAR_NAMES[j] for j in range(15) if m >> j & 1]
        print(f"  {i + 1:2d} {STAR_NAMES[i]:<8} mask {m:#06x}  beats: "
              + (", ".join(wins) if wins else "-"))


def inspect(d):
    if not is_patched(d):
        stock = bytes(d[OFF_CODE:OFF_CODE + 116]) == STOCK_CODE
        print("guardian-star patch : NOT installed"
              + ("  (0x8002CB80 is stock)" if stock else "  (and 0x8002CB80 is NOT stock either!)"))
        print("stock wheel         : 1->2->3->4->5->6->1  and  7->8->9->10->7")
        return
    ram = data_addr(d)
    print(f"guardian-star patch : installed, table at {ram:#010x} (file {slusoff(ram):#x})")
    tab = read_table(d, ram)
    print("                      " + ("stock wheel" if tab == DEFAULT_TABLE else "custom wheel"))
    show(tab)


def parse_edges(pairs):
    out = []
    for p in pairs or []:
        a, _, b = p.partition(":")
        a, b = int(a, 0), int(b, 0)
        if not (1 <= a <= 15 and 1 <= b <= 15) or a == b:
            sys.exit(f"bad edge {p!r}: star ids are 1..15 and must differ")
        out.append((a - 1, b - 1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "set", "clear", "restore"])
    ap.add_argument("slus")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--data-addr", default=hex(RAM_DATA),
                    help="RAM address of the 32-byte table (default 0x80011A80)")
    ap.add_argument("--beats", action="append", metavar="A:B",
                    help="star A wins over star B (repeatable)")
    a = ap.parse_args()
    d = load(a.slus)

    if a.cmd == "inspect":
        inspect(d)
        return
    if not a.out or a.out == a.slus:
        sys.exit("give an output path different from the input")

    if a.cmd == "restore":
        ram = data_addr(d) if is_patched(d) else RAM_DATA
        d[OFF_CODE:OFF_CODE + 116] = STOCK_CODE
        d[slusoff(RAM_DATA):slusoff(RAM_DATA) + 32] = STOCK_DATA
        if ram != RAM_DATA:
            print(f"note: table had been moved to {ram:#010x}; those 32 bytes are left as-is")
    elif a.cmd == "apply":
        ram = int(a.data_addr, 0)
        d[OFF_CODE:OFF_CODE + 96] = PATCH
        set_hilo(d, ram)
        write_table(d, ram, DEFAULT_TABLE)
    else:                                             # set / clear
        if not is_patched(d):
            sys.exit("file is not patched yet -- run `apply` first")
        ram = data_addr(d)
        tab = read_table(d, ram)
        for x, y in parse_edges(a.beats):
            if a.cmd == "set":
                tab[x] |= 1 << y
                tab[y] &= ~(1 << x)
            else:
                tab[x] &= ~(1 << y)
        write_table(d, ram, tab)

    open(a.out, "wb").write(d)
    print("wrote", a.out)
    inspect(load(a.out))


if __name__ == "__main__":
    main()
