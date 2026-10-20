#!/usr/bin/env python3
"""Offline clone of TEA-Online's FREE DUEL FIELDS tool (extend/tools/process/fdfields).

Gives every Free Duel opponent its own terrain, switched by your win count
against that opponent.  Installs 24 instructions of new code plus a 40 x u32
table in the unused tail of the text bank (default 0x801BFE60), and redirects
one instruction inside the duel-parameter setter at 0x80024DC8.

  fd_fields.py inspect SLUS_014.11
  fd_fields.py apply   SLUS_014.11 out.11 [--code-addr 0x801BFE60]
  fd_fields.py set     SLUS_014.11 out.11 --opp 2:MOUNTAIN:SEA:5 [--opp ...]
  fd_fields.py restore SLUS_014.11 out.11

--opp ID:FIELD_BEFORE:FIELD_AFTER:LIMIT
    while duelistRecords[ID].wins <  LIMIT -> FIELD_BEFORE
    once  duelistRecords[ID].wins >= LIMIT -> FIELD_AFTER
    ID 1..39, LIMIT 0..65535, FIELD one of - FOREST WASTELAND MOUNTAIN MEADOW SEA DARK
    (LIMIT 0 therefore means "always FIELD_AFTER".)
"""
import argparse, struct, sys

RAM_CODE_DEFAULT = 0x801BFE60
HOOK1 = 0x80024E08       # stock: sb zero, gDuel_bTerrain(at)
HOOK2 = 0x80024E10       # same store, one slot later, in a freedueltheme'd EXE
FIELDS = ["-", "FOREST", "WASTELAND", "MOUNTAIN", "MEADOW", "SEA", "DARK"]
OPPONENTS = [               # SLUS name strings 808..847, index = row*5+col
    "Build Deck", "Simon Muran", "Teana", "Jono", "Villager1", "Villager2",
    "Villager3", "Seto", "Heishin", "Rex Raptor", "Weevil Underwood",
    "Mai Valentine", "Bandit Keith", "Shadi", "Yami Bakura", "Pegasus", "Isis",
    "Kaiba", "Mage Soldier", "Jono 2nd", "Teana 2nd", "Ocean Mage",
    "High Mage Secmeton", "Forest Mage", "High Mage Anubisius", "Mountain Mage",
    "High Mage Atenza", "Desert Mage", "High Mage Martis", "Meadow Mage",
    "High Mage Kepura", "Labyrinth Mage", "Seto 2nd", "Guardian Sebek",
    "Guardian Neku", "Heishin 2nd", "Seto 3rd", "DarkNite", "Nitemare",
    "Duel Master K"]

# 24 instruction words.  The first word's -320 displacement makes the table
# start at code+96, so both variants are position independent apart from the
# `lui s1` that the jump patch puts in its delay slot.
MAIN1 = bytes.fromhex(
    "c0fe3126" "80900500" "21883202" "1d80143c"
    "00003396" "69b320a0" "1c079426" "21a09202"
    "00009596" "00000000" "2a90b302" "00000000"
    "02003392" "00000000" "03004016" "21a80000"
    "03003392" "00000000" "64b333a0" "21880000"
    "21900000" "21980000" "84930008" "21a00000")
# Identical except the trailing `j` target (0x80024E18 instead of 0x80024E10).
# NOTE: the site's own array for this variant has a JavaScript array HOLE at index
# 92 (`...,134,147,0,8,,33,160,0,0`).  Array.forEach skips holes, so the site leaves
# byte 92 unwritten and shifts the last four bytes up one, turning the delay slot
# `move s4,zero` into the reserved word 0x00A02100 (an SLL with rs != 0, which the
# R3000 executes as `sll a0,zero,4`, i.e. it zeroes a0 and leaves s4 dirty).
# MAIN2 is the corrected form; MAIN2_SITE reproduces the shipped bytes.
MAIN2 = MAIN1[:88] + bytes.fromhex("86930008") + MAIN1[92:]
MAIN2_SITE = MAIN1[:88] + bytes.fromhex("86930008") + b"\x00" + MAIN1[92:95]

STOCK_HOOK1 = bytes.fromhex("64b320a0" "0a80013c")   # sb zero,B364(at) ; lui at,0x800a
STOCK_HOOK2 = bytes.fromhex("69b320a0" "0a80013c")   # sb zero,B369(at) ; lui at,0x800a
# what the freedueltheme tool leaves at 0x80024E08 (four packed stores)
THEME_SIG = bytes.fromhex("70b326a4" "72b327a4" "64b320a0" "69b320a0")


def load(p):
    d = bytearray(open(p, "rb").read())
    if not (1782579 <= len(d) <= 8388608) or d[:8] != b"PS-X EXE":
        sys.exit("not a SLUS_014.11-sized PS-X EXE")
    return d


def slusoff(ram):
    return ram - 0x80010000 + 0x800


def jword(ram):
    return 0x08000000 | ((ram >> 2) & 0x03FFFFFF)


def code_type(d):
    """1 = plain EXE hook site, 2 = freedueltheme-shifted hook site, None = neither."""
    at1 = bytes(d[slusoff(HOOK1):slusoff(HOOK1) + 16])
    if at1[4:8] == bytes.fromhex("1c80113c"):        # lui s1,0x801c after our j
        return 1
    if bytes(d[slusoff(HOOK2):slusoff(HOOK2) + 8])[4:8] == bytes.fromhex("1c80113c"):
        return 2
    return None


def stock_kind(d):
    at1 = bytes(d[slusoff(HOOK1):slusoff(HOOK1) + 16])
    if at1 == STOCK_HOOK1 + STOCK_HOOK2:
        return 1
    if at1 == THEME_SIG:
        return 2
    return None


def code_addr(d, ct):
    hook = HOOK1 if ct == 1 else HOOK2
    w = struct.unpack_from("<I", d, slusoff(hook))[0]
    return 0x80000000 | ((w & 0x03FFFFFF) << 2)


def read_rows(d, ram):
    base = slusoff(ram) + 96
    rows = []
    for i in range(1, 40):
        v = struct.unpack_from("<I", d, base + 4 * i)[0]
        rows.append((i, v & 0xFFFF, (v >> 16) & 0xF, (v >> 24) & 0xF))
    return rows


def write_row(d, ram, i, limit, f1, f2):
    v = (limit & 0xFFFF) | ((f1 & 0xF) << 16) | ((f2 & 0xF) << 24)
    struct.pack_into("<I", d, slusoff(ram) + 96 + 4 * i, v)


def inspect(d):
    ct = code_type(d)
    if ct is None:
        k = stock_kind(d)
        print("fdfields patch : NOT installed  "
              + {1: "(stock EXE)", 2: "(freedueltheme patch present)",
                 None: "(hook site is neither stock nor freedueltheme!)"}[k])
        return
    ram = code_addr(d, ct)
    print(f"fdfields patch : installed, type {ct}, code+table at {ram:#010x} "
          f"(file {slusoff(ram):#x})")
    print("  id  opponent               wins <  limit      wins >= limit")
    for i, limit, f1, f2 in read_rows(d, ram):
        if limit == 0 and f1 == 0 and f2 == 0:
            continue
        print(f"  {i:2d}  {OPPONENTS[i]:<21}  {FIELDS[f1] if f1 < 7 else f1:<9} (<{limit})  "
              f"{FIELDS[f2] if f2 < 7 else f2}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["inspect", "apply", "set", "restore"])
    ap.add_argument("slus")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--code-addr", default=hex(RAM_CODE_DEFAULT),
                    help="RAM address for the 256-byte code+table block")
    ap.add_argument("--opp", action="append", metavar="ID:BEFORE:AFTER:LIMIT")
    ap.add_argument("--site-bug", action="store_true",
                    help="reproduce the site's byte-for-byte (broken) type-2 delay slot")
    a = ap.parse_args()
    d = load(a.slus)

    if a.cmd == "inspect":
        inspect(d)
        return
    if not a.out or a.out == a.slus:
        sys.exit("give an output path different from the input")

    if a.cmd == "apply":
        ct = stock_kind(d)
        if ct is None:
            sys.exit("hook site at 0x80024E08 is neither stock nor freedueltheme-patched")
        ram = int(a.code_addr, 0)
        hook = HOOK1 if ct == 1 else HOOK2
        struct.pack_into("<I", d, slusoff(hook), jword(ram))
        struct.pack_into("<I", d, slusoff(hook) + 4, 0x3C11801C)   # lui s1,0x801c
        if ct == 1:
            body = MAIN1
        else:
            body = MAIN2_SITE if a.site_bug else MAIN2
        d[slusoff(ram):slusoff(ram) + 96] = body
        d[slusoff(ram) + 96:slusoff(ram) + 96 + 160] = bytes(160)
        if ram != RAM_CODE_DEFAULT:
            # the code reaches its table as 0x801C0000-320; re-point that pair
            struct.pack_into("<I", d, slusoff(ram),
                             0x26310000 | ((ram + 96 - 0x801C0000) & 0xFFFF))
    elif a.cmd == "set":
        ct = code_type(d)
        if ct is None:
            sys.exit("file is not patched yet -- run `apply` first")
        ram = code_addr(d, ct)
        for spec in a.opp or []:
            parts = spec.split(":")
            if len(parts) != 4:
                sys.exit(f"bad --opp {spec!r}: want ID:BEFORE:AFTER:LIMIT")
            i = int(parts[0], 0)
            if not 1 <= i <= 39:
                sys.exit(f"opponent id {i} out of range 1..39")
            try:
                f1 = FIELDS.index(parts[1].upper())
                f2 = FIELDS.index(parts[2].upper())
            except ValueError:
                sys.exit(f"field must be one of {' '.join(FIELDS)}")
            write_row(d, ram, i, int(parts[3], 0), f1, f2)
    else:                                              # restore
        ct = code_type(d)
        if ct is None:
            sys.exit("file does not carry the fdfields patch")
        ram = code_addr(d, ct)
        hook = HOOK1 if ct == 1 else HOOK2
        if ct == 1:                                     # plain EXE: two lui/sb pairs
            d[slusoff(HOOK1):slusoff(HOOK1) + 8] = STOCK_HOOK1
        else:                                           # freedueltheme layout: packed stores
            d[slusoff(HOOK2):slusoff(HOOK2) + 8] = bytes.fromhex("64b320a0" "69b320a0")
        d[slusoff(ram):slusoff(ram) + 256] = bytes(256)

    open(a.out, "wb").write(d)
    print("wrote", a.out)
    inspect(load(a.out))


if __name__ == "__main__":
    main()
