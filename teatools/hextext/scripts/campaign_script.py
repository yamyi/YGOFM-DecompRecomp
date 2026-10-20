#!/usr/bin/env python3
"""Dump the campaign ("story") script bank that TEA-Online's hextext page edits in its
"Campaign Router" panel.

Location: WA_MRG.MRG offset 0xF34000 (in-file sector 0x1E68, disc LBA 17886), 4096 bytes:
    199 x u16  offsets, relative to the bank start (first = 398 = 0x18E)
    3698 bytes bytecode (0xF3418E .. 0xF34FFF)
The game loads it to 0x801A8000 (decomp F111/F115: Script_RunTick 0x8002FA54 reads
gScript_pStream inside this bank; the EXE's own bytes there are zero).  Op shapes are the
site's parser (V.230825); the decomp has not named the opcodes yet.

Usage:
  campaign_script.py dump  (WA_MRG.MRG | disc.bin) [--slus SLUS_014.11] [--seq N]
  campaign_script.py raw   (WA_MRG.MRG | disc.bin) --seq N          hex of one sequence
"""
import argparse
import struct
import sys

BANK_OFF = 0xF34000
BANK_LEN = 4096
NPTR = 199
CODE_START = 2 * NPTR           # 398
WA_LBA = 10102
RAW_SECTOR, DATA_OFF, DATA_LEN = 2352, 24, 2048

CHARACTERS = ["Empty 0", "Simon Muran", "Jono", "Teana", "Seto", "Empty 1", "Dark Shrine Guardian",
              "Heishin", "Egyptian card trader", "Lady Palace", "Beaten Simon Muran", "Empty 2",
              "Pharaoh Atem", "Joey Wheeler", "Kaiba", "Shadi", "Rex Raptor", "Weevil Underwood",
              "Mai Valentine", "Bandit Keith", "Bakura", "Pegasus", "Tea Card Trader", "Catacomb Keeper",
              "Mage Soldier", "Ocean Mage", "High Mage Secmeton", "Forest Mage", "High Mage Anubisius",
              "Mountain Mage", "High Mage Atenza", "Desert Mage", "High Mage Martis", "Meadow Mage",
              "High Mage Kepura", "Guardian Sebek", "Guardian Neku", "Darknite", "Nitemare", "Empty 3",
              "Empty 4", "Empty 5", "Tournament Host", "Villager 1", "Villager 2", "Villager 3",
              "Labyrinth Mage", "Isis", "Jono defeated", "Teana defeated", "Seto defeated",
              "Heishin defeated", "Kaiba defeated", "Rex Raptor defeated", "Weevil Underwood defeated",
              "Mai Valentine defeated", "Bandit Keith defeated", "Bakura defeated", "Pegasus defeated",
              "Darknite defeated", "Villager 1 defeated", "Villager 2 defeated", "Villager 3 defeated",
              "Labyrinth Mage defeated"]


def read_bank(path):
    d = open(path, "rb").read()
    if len(d) == 37748736:                       # plain WA_MRG.MRG
        return d[BANK_OFF:BANK_OFF + BANK_LEN]
    if len(d) % RAW_SECTOR == 0:                 # MODE2/2352 disc image
        lba = WA_LBA + BANK_OFF // 2048
        out = b""
        while len(out) < BANK_LEN:
            o = lba * RAW_SECTOR + DATA_OFF
            out += d[o:o + DATA_LEN]
            lba += 1
        return out[:BANK_LEN]
    sys.exit("expected WA_MRG.MRG (37,748,736 bytes) or a 2352-byte-sector .bin")


def text_lookup(slus, tid):
    if slus is None:
        return ""
    try:
        sys.path.insert(0, __file__.rsplit("/", 1)[0])
        import fmtext
        off = struct.unpack_from("<H", slus, fmtext.ram2file(fmtext.OFFSETS2_RAM) + 2 * tid)[0]
        return fmtext.decode(slus, fmtext.BANK_FILE + off)[:70]
    except Exception:
        return ""


def parse(bank, slus=None):
    """Return list of (offset, length, name, detail) over the bytecode (site's grammar)."""
    ops = []
    i = CODE_START
    while i < BANK_LEN:
        op = bank[i]
        n, name, det = 1, f"?? {op:02X}", ""
        if op == 0x03:
            n, name = 5, "Condition"
            det = f"flag {bank[i+1]:02X} type {bank[i+2]:02X} jump {struct.unpack_from('<H', bank, i+3)[0]:04X}"
        elif op == 0x0D:
            n, name, det = 5, "Menu", f"sequence {bank[i+3]:02X}"
        elif op == 0x01:
            n, name, det = 3, "Background", f"id {bank[i+1]:02X} type {bank[i+2]:02X}"
        elif op == 0x0A:
            if bank[i + 1] == 0x00:
                n, name, det = 4, "Theme", f"bgm 0x{struct.unpack_from('<H', bank, i+2)[0]:04X}"
            elif bank[i + 1] == 0x40:
                n, name = 8, "?? 0A 40"
        elif op == 0x09:
            n, name = 3, "Character"
            det = f"{bank[i+1]:02X} {CHARACTERS[bank[i+1]] if bank[i+1] < len(CHARACTERS) else '?'} at {'RIGHT' if bank[i+2] == 0x80 else 'LEFT' if bank[i+2] == 0 else hex(bank[i+2])}"
        elif op == 0x02:
            n, name = 3, "Text"
            det = f"id {bank[i+1]:02X} type {bank[i+2]:02X}  {text_lookup(slus, bank[i+1])}"
        elif op == 0x0B and bank[i + 1] == 0x00:
            n, name = 2, "Nothing"
        elif op == 0x12:
            name = "Game Over"
        elif op == 0x13:
            name = "End"
        elif op == 0x08:
            n, name, det = 2, "Exit Point", f"{bank[i+1]:02X}"
        elif op == 0x0C:
            n, name, det = 3, "Jump", f"{struct.unpack_from('<H', bank, i+1)[0]:04X}"
        elif op == 0x15:
            n, name = 3, "?? 15"
        elif op == 0x10:
            sub = bank[i + 1]
            if sub == 0x82:
                n, name = 8, "Prologue Scene"
            elif sub == 0x81:
                n, name = 2, "Slow FadeOut"
            else:
                n, name = 2, f"?? 10 {sub:02X}"
        elif op == 0xFF:
            ops.append((i, 1, "FF (end of bank)", ""))
            break
        ops.append((i, n, name, det))
        i += n
    return ops


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("dump"); p.add_argument("wa"); p.add_argument("--slus"); p.add_argument("--seq", type=int)
    p = sub.add_parser("raw"); p.add_argument("wa"); p.add_argument("--seq", type=int, required=True)
    a = ap.parse_args()
    bank = read_bank(a.wa)
    ptrs = [struct.unpack_from("<H", bank, 2 * k)[0] for k in range(NPTR)]
    if a.cmd == "raw":
        lo = ptrs[a.seq]; hi = ptrs[a.seq + 1] if a.seq + 1 < NPTR else BANK_LEN
        print(f"seq {a.seq:02X} @{lo:04X}..{hi:04X}: {bank[lo:hi].hex(' ')}")
        return
    slus = open(a.slus, "rb").read() if a.slus else None
    ops = parse(bank, slus)
    for k in range(NPTR):
        if a.seq is not None and k != a.seq:
            continue
        lo = ptrs[k]; hi = ptrs[k + 1] if k + 1 < NPTR else BANK_LEN
        print(f"== sequence {k:02X} (RAM 0x{0x801A8000 + lo:08X}, WA 0x{BANK_OFF + lo:06X}) [{lo:04X}..{hi:04X})")
        for off, n, name, det in ops:
            if lo <= off < hi:
                print(f"   {off:04X}  {bank[off:off+n].hex(' '):24s} {name:14s} {det}")


if __name__ == "__main__":
    main()
