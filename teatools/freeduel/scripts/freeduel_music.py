#!/usr/bin/env python3
"""Offline clone of TEA-Online "Free Duel Music" (route extend/tools/freeduel, page V.220724).

One u16 in SLUS_014.11: the default duel BGM code that init_800eb26c_fields_from_args
(0x80024DC8) stores into D_8009B36A at the start of every duel that is not given its own
theme by a campaign script -- i.e. every free duel.

  file 0x155C8  RAM 0x80024DC8   addiu v0, zero, 0x7270     (stock = FREEDUEL THEME)

BGM codes are 0x7000 | (track << 4); the low byte is the site's "p1", the high byte "p2".

Usage:
  freeduel_music.py list
  freeduel_music.py inspect SLUS
  freeduel_music.py apply   SLUS (TRACK_ID | "NAME") [-o OUT]
  freeduel_music.py restore SLUS [-o OUT]
"""
import argparse
import struct
import sys

OFF = 0x155C8
STOCK = 0x7270
SIZE_MIN, SIZE_MAX = 1902591, 2097152

# track id -> name.  Merged from the site's two lists (module 1929 of chunk-common and
# the freeduel/hextext music menus).  Names are the site's.
TRACKS = {
    0x00: "Main Menu", 0x01: "Input Name Menu", 0x02: "Introduction Title Screen",
    0x03: "Tournament Announcement", 0x04: "Modern Times", 0x05: "Inside the Puzzle",
    0x06: "Preliminary Face-Off", 0x07: "Finals Face-Off", 0x08: "Seto Kaiba Face-Off",
    0x09: "Card Shop", 0x0A: "Metropolis I", 0x0B: "Metropolis II", 0x0C: "Simon Muran",
    0x0D: "Egypt in Ruins", 0x0E: "Build Deck", 0x0F: "Hidden Card Shop", 0x10: "Valley of the Kings",
    0x11: "Sea Shrine", 0x12: "Forest Shrine", 0x13: "Desert Shrine", 0x14: "Meadow Shrine",
    0x15: "Mountain Shrine", 0x16: "Vast Shrine", 0x17: "Dark Shrine", 0x18: "Seto's Betrayal",
    0x19: "Forbidden Ruins", 0x1A: "Heishin Millennium Puzzle", 0x1B: "Heishin Invasion",
    0x1C: "DarkNite's Arrival", 0x1D: "Preliminary Match Theme", 0x1E: "Finals Match Theme",
    0x1F: "Seto Kaiba Theme", 0x20: "Egyptian Duel Theme", 0x21: "Mage Duel Theme",
    0x22: "High Mage Duel Theme", 0x23: "Heishin Theme", 0x24: "Priest Seto Theme",
    0x25: "DarkNite & Nitemare Theme (1)", 0x26: "DarkNite & Nitemare Theme (2)",
    0x27: "Freeduel Theme", 0x28: "3D Battle Theme", 0x29: "Seto Kaiba 3D Battle Theme",
    0x2A: "3D Battle Egypt Theme", 0x2B: "DarkNite 3D Battle Theme", 0x2C: "Freeduel Select Theme",
    0x2D: "Library Menu", 0x2E: "You Win", 0x2F: "You Lose", 0x30: "Game Over", 0x31: "Exodia",
    0x32: "Epilogue", 0x33: "Ending Credits Theme", 0x34: "Town Plaza Festival",
    0x35: "Password Menu", 0x36: "Millennium Item Found", 0x37: "Forbidden Ruins (2)",
    0x38: "Simon Muran (2)",
}


def code_of(track):
    return 0x7000 | (track << 4)


def track_of(code):
    return (code - 0x7000) >> 4 if 0x7000 <= code < 0x7400 and code & 0xF == 0 else None


def describe(code):
    t = track_of(code)
    name = TRACKS.get(t, "?") if t is not None else "not a BGM code"
    return f"0x{code:04X} (p1={code & 0xFF}, p2={code >> 8}) track 0x{t:02X} {name}" if t is not None else f"0x{code:04X} {name}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("inspect"); p.add_argument("slus")
    p = sub.add_parser("apply"); p.add_argument("slus"); p.add_argument("track"); p.add_argument("-o", "--out")
    p = sub.add_parser("restore"); p.add_argument("slus"); p.add_argument("-o", "--out")
    a = ap.parse_args()

    if a.cmd == "list":
        for t, n in sorted(TRACKS.items()):
            print(f"0x{t:02X}  code 0x{code_of(t):04X}  {n}{'   (stock free duel)' if t == 0x27 else ''}")
        return

    data = bytearray(open(a.slus, "rb").read())
    if not SIZE_MIN <= len(data) <= SIZE_MAX:
        sys.exit(f"{a.slus}: size {len(data)} outside the tool's accepted range")
    word = struct.unpack_from("<I", data, OFF)[0]
    if word >> 16 != 0x2402:
        sys.exit(f"0x{OFF:X} is not 'addiu v0,zero,imm' (found {word:08X}); the site refuses such files too "
                 "(its 'special duel theme process' check)")
    cur = word & 0xFFFF
    print(f"current: {describe(cur)}")
    if a.cmd == "inspect":
        return
    if a.cmd == "restore":
        new = STOCK
    else:
        s = a.track
        try:
            new = code_of(int(s, 0))
        except ValueError:
            hits = [t for t, n in TRACKS.items() if n.lower() == s.lower()]
            if not hits:
                sys.exit(f"unknown track {s!r}; see 'list'")
            new = code_of(hits[0])
    struct.pack_into("<H", data, OFF, new)
    out = a.out or a.slus
    open(out, "wb").write(data)
    print(f"written: {describe(new)} -> {out}")


if __name__ == "__main__":
    main()
