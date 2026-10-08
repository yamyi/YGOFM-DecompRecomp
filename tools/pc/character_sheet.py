#!/usr/bin/env python3
"""The campaign's characters as PNGs, assembled the way the game draws them.

    python3 tools/pc/character_sheet.py --out tmp/pc/characters
    python3 tools/pc/character_sheet.py --character 7 --frames --sheet
    python3 tools/pc/character_sheet.py --check

A character -- the speaker a dialogue draws, 64 of them -- is 50 sectors of
WA_MRG.MRG: three 128x256 pages, two palettes, and a script. Nothing in
there is a picture of the character: the script cuts pieces out of the pages
and places them, so the trader's face has a hole in it until the eye and
mouth layers are drawn over it.

This walks that script and puts the pieces back together:

  <out>/08-egyptian-card-trader/pose0.png     as the game draws it
  <out>/08-egyptian-card-trader/sheet.png     the three pages, with --sheet
  <out>/08-egyptian-card-trader/pose0-body-0.png   each frame, with --frames
  <out>/08-egyptian-card-trader/pose0-eyes-1.png
  <out>/08-egyptian-card-trader/pose0-mouth-2.png

Where the format comes from, all of it this project's own code:

  block(id) = 0x1DC0000 + 0x19000 * (id - 1), and func_8003A560
    (src/game/display_effect_resource_setup.c) streams 48 sectors to VRAM at
    (832 - 192 * side, 256), the palettes to (512, 240 + 2 * side) and the
    last sector to 0x801AF000 as the script.
  DisplayObject_UpdateCommandStream walks three levels of u16 offsets into
    that script, indexed by the pose and the layer.
  DisplayObjectStream_ReadNextCommand reads the stream it reaches: 3-byte
    (delay, u16 sheet offset) records, opcodes 0xF0 and up being flow
    control.
  SpriteSheetHeader and SpriteSheetPart
    (src/game/display_object_render_sprite_sheet.h) are the sheet a record
    points at: a four-byte header and `count` six-byte parts.
  DisplayEffect_BuildResourceObjects makes up to three objects for one
    character, at (pose, 0, 0), (pose, 1, 0) and (pose, 2, 0) -- the body and
    the two layers that animate over it.

Nothing is written into the repository: the art is the player's disc's.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from fm_editor import disc                                  # noqa: E402

FIRST_BLOCK = 0x1DC0000
BLOCK_BYTES = 0x19000
PIXEL_BYTES = 0x18000           # three 128x256 pages
SCRIPT_AT = 0x18800
SCRIPT_BYTES = 0x800
PAGE_WIDTH, PAGE_ROWS, PAGES = 128, 256, 3
SHEET_WIDTH = PAGE_WIDTH * PAGES
CHARACTERS = 64
LAYERS = ("body", "eyes", "mouth")
POSE_LIMIT = 8
FRAME_LIMIT = 64

# A texture page is 64 halfwords, 128 pixels at 8 bits a pixel, and the
# header's tpage is "doubled when wide" -- these sheets are 8-bit, so a step
# is the 256-pixel window. A part's own page bits step the same window.
PAGE_STEP = 256

# The names the TEA-Online character tool lists, which are the ones the
# community knows them by. An id with no name still has art.
NAMES = {
    1: "Simon Muran", 2: "Jono", 3: "Teana", 4: "Seto", 6: "Dark Shrine Guardian",
    7: "Heishin", 8: "Egyptian card trader", 9: "Lady of the Palace", 10: "beaten Simon",
    12: "Pharaoh Atem", 13: "Joey", 14: "Kaiba", 15: "Shadi", 16: "Rex", 17: "Weevil",
    18: "Mai", 19: "Keith", 20: "Bakura", 21: "Pegasus", 22: "Tea card trader",
    23: "Catacomb Keeper", 24: "Mage Soldier", 25: "Ocean Mage", 26: "Secmeton",
    27: "Forest Mage", 28: "Anubisius", 29: "Mountain Mage", 30: "Atenza",
    31: "Desert Mage", 32: "Martis", 33: "Meadow Mage", 34: "Kepura", 35: "Sebek",
    36: "Neku", 37: "DarkNite", 38: "Nitemare", 42: "Tournament Host", 43: "Villager 1",
    44: "Villager 2", 45: "Villager 3", 46: "Labyrinth Mage", 47: "Isis",
}


def slug(character: int) -> str:
    name = NAMES.get(character)
    if not name:
        return "%02d" % character
    return "%02d-%s" % (character, re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))


# --- the block ----------------------------------------------------------

class Character:
    def __init__(self, wa: bytes, character: int):
        at = FIRST_BLOCK + BLOCK_BYTES * (character - 1)
        self.id = character
        self.pixels = wa[at:at + PIXEL_BYTES]
        self.script = wa[at + SCRIPT_AT:at + SCRIPT_AT + SCRIPT_BYTES]
        palette_at = at + PIXEL_BYTES
        self.palette = []
        for i in range(256):
            value = wa[palette_at + i * 2] | wa[palette_at + i * 2 + 1] << 8
            self.palette.append((((value >> 0) & 31) << 3, ((value >> 5) & 31) << 3,
                                 ((value >> 10) & 31) << 3, 0 if i == 0 else 255))

    def u16(self, at: int) -> int:
        return self.script[at] | self.script[at + 1] << 8

    def texel(self, x: int, v: int) -> int:
        """The sheet is 384 pixels wide: three 128-wide columns, each a run of
        128-byte rows."""
        if not 0 <= x < SHEET_WIDTH or not 0 <= v < PAGE_ROWS:
            return 0
        return self.pixels[(x // PAGE_WIDTH) * 0x8000 + v * PAGE_WIDTH + (x % PAGE_WIDTH)]

    def poses(self) -> int:
        count = 0
        for pose in range(POSE_LIMIT):
            offset = self.u16(pose * 2)
            if not offset or offset >= SCRIPT_BYTES:
                break
            count += 1
        return count

    def table_starts(self):
        """Every offset a level-2 table points at. The level-3 tables sit one
        after another, so a table runs until the next one begins -- there is
        no count anywhere, and the game never needs one because it asks for a
        single entry at a time."""
        out = set()
        for pose in range(self.poses()):
            first = self.u16(pose * 2)
            for layer in range(len(LAYERS)):
                second = self.u16(first + layer * 2)
                if second and second < SCRIPT_BYTES:
                    out.add(second)
        return sorted(out)

    def variants(self, pose: int, layer: int):
        """The level-3 entries of one layer: a body has one, the eyes and the
        mouth have several, and the third index picks between them -- which
        is how the mouth changes with the text and the eyes blink.
        DisplayEffect_BuildResourceObjects always asks for the first."""
        first = self.u16(pose * 2)
        if not first:
            return []
        second = self.u16(first + layer * 2)
        if not second or second >= SCRIPT_BYTES:
            return []
        starts = self.table_starts()
        stop = next((v for v in starts if v > second), SCRIPT_BYTES)
        out = []
        for at in range(second, min(stop, SCRIPT_BYTES - 1), 2):
            value = self.u16(at)
            if not value or value >= SCRIPT_BYTES:
                break
            out.append(value)
        return out

    def frames(self, pose: int, layer: int, variant: int = 0):
        """The (delay, sheet offset) records the stream for one layer walks.
        A zero at any level of the chain means there is no such layer, which
        is what DisplayEffect_HasResourceEntry tests."""
        entries = self.variants(pose, layer)
        if variant >= len(entries):
            return []
        third = entries[variant]
        out, at = [], third
        for _ in range(FRAME_LIMIT):
            if at + 2 >= SCRIPT_BYTES:
                break
            delay = self.script[at]
            if delay >= 0xF0:               # flow control ends the strip
                break
            offset = self.u16(at + 1)
            if not self.is_sheet(offset):
                # Not every strip ends in flow control: a few characters
                # have one that simply stops, and reading on walks into the
                # sheets themselves. A record that does not point at a sheet
                # this script could hold is where the strip ended.
                break
            out.append((delay, offset))
            at += 3
        return out

    def is_sheet(self, offset: int) -> bool:
        """Whether `offset` could be a sheet: a count of at least one part,
        and that many parts inside the script."""
        if not 0 < offset or offset + 4 > SCRIPT_BYTES:
            return False
        count = self.script[offset]
        return 0 < count <= 32 and offset + 4 + count * 6 <= SCRIPT_BYTES

    def shapes(self, pose: int, layer: int):
        """The distinct sheets a layer draws, in the order they first appear.

        A layer's variants are not different pictures: they are the same
        cycle entered at different points, which is how the mouth is put in
        step with the text and the eyes with their own timer. Heishin's four
        mouth variants all walk the same three sheets. So the shapes are the
        sheets themselves, not the variants."""
        out = []
        for variant in range(len(self.variants(pose, layer))):
            for _, offset in self.frames(pose, layer, variant):
                if offset not in out:
                    out.append(offset)
        return out

    def parts(self, offset: int):
        """A sheet: the four-byte header, then `count` six-byte parts."""
        if offset + 4 > SCRIPT_BYTES:
            return []
        count, flags, tpage = self.script[offset], self.script[offset + 1], self.script[offset + 2]
        out = []
        for i in range(count):
            at = offset + 4 + i * 6
            if at + 6 > SCRIPT_BYTES:
                break
            dx, dy = struct.unpack_from("<bb", self.script, at)
            cell = self.u16(at + 2)
            size = self.u16(at + 4)
            if flags & 0x10:                # ten-bit offsets, the high bits in the two words
                dx = ((cell >> 14) & 3) << 8 | (dx & 0xFF)
                dy = ((size >> 14) & 3) << 8 | (dy & 0xFF)
                dx -= 1024 if dx >= 512 else 0
                dy -= 1024 if dy >= 512 else 0
            out.append({
                "dx": dx, "dy": dy,
                "x": (tpage + ((cell >> 10) & 7)) * PAGE_STEP + (cell & 0x1F) * 8,
                "v": ((cell >> 5) & 0x1F) * 8,
                "w": (((size >> 5) & 0xF) + 1) * 8,
                "h": (((size >> 9) & 0xF) + 1) * 8,
                "mirror": bool(cell & 0x2000),
            })
        return out


# --- drawing ------------------------------------------------------------

def draw(character: Character, sheets, scale: int = 1):
    """The parts of every sheet, in order, onto one canvas."""
    every = [p for sheet in sheets for p in sheet]
    if not every:
        return None, None
    x0 = min(p["dx"] for p in every)
    y0 = min(p["dy"] for p in every)
    width = max(p["dx"] + p["w"] for p in every) - x0
    height = max(p["dy"] + p["h"] for p in every) - y0
    canvas = [[(0, 0, 0, 0)] * width for _ in range(height)]
    for part in every:
        for y in range(part["h"]):
            for x in range(part["w"]):
                index = character.texel(part["x"] + (part["w"] - 1 - x if part["mirror"] else x),
                                        part["v"] + y)
                if not index:
                    continue
                canvas[part["dy"] - y0 + y][part["dx"] - x0 + x] = character.palette[index]
    rows = []
    for y in range(height * scale):
        row = bytearray()
        for x in range(width * scale):
            row += bytes(canvas[y // scale][x // scale])
        rows.append(bytes(row))
    return rows, (x0, y0, width, height)


def sheet_rows(character: Character):
    """The three pages side by side, as they are stored."""
    rows = []
    for y in range(PAGE_ROWS):
        row = bytearray()
        for page in range(PAGES):
            at = (page * PAGE_ROWS + y) * PAGE_WIDTH
            for index in character.pixels[at:at + PAGE_WIDTH]:
                row += bytes(character.palette[index])
        rows.append(bytes(row))
    return rows


def write_png(path: pathlib.Path, rows) -> None:
    if not rows:
        return
    height, width = len(rows), len(rows[0]) // 4
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(kind: bytes, body: bytes) -> bytes:
        block = kind + body
        return struct.pack(">I", len(body)) + block + struct.pack(">I", zlib.crc32(block) & 0xFFFFFFFF)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))


# --- checking -----------------------------------------------------------

def check(wa: bytes) -> int:
    """Every character, pose, layer and frame: each part has to lie inside the
    sheet and find something there. A part that samples an empty region is how
    a decoding mistake shows -- it is what a missing `tpage` looked like."""
    problems = 0
    parts = frames = 0
    for cid in range(1, CHARACTERS + 1):
        one = Character(wa, cid)
        for pose in range(one.poses()):
            for layer in range(len(LAYERS)):
                for index, (_, offset) in enumerate(one.frames(pose, layer)):
                    frames += 1
                    for part in one.parts(offset):
                        parts += 1
                        if part["x"] < 0 or part["x"] + part["w"] > SHEET_WIDTH or \
                           part["v"] < 0 or part["v"] + part["h"] > PAGE_ROWS:
                            print("character %d pose %d %s frame %d: a %dx%d part at (%d, %d) "
                                  "falls outside the sheet" % (cid, pose, LAYERS[layer], index,
                                                               part["w"], part["h"], part["x"], part["v"]))
                            problems += 1
                            continue
                        if not any(one.texel(part["x"] + x, part["v"] + y)
                                   for y in range(part["h"]) for x in range(part["w"])):
                            print("character %d pose %d %s frame %d: a %dx%d part at (%d, %d) "
                                  "reads nothing but transparency" % (cid, pose, LAYERS[layer], index,
                                                                      part["w"], part["h"], part["x"], part["v"]))
                            problems += 1
    print("check: %d characters, %d frames, %d parts, %d problems" %
          (CHARACTERS, frames, parts, problems))
    return 1 if problems else 0


# --- the tool -----------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--game", type=pathlib.Path, help="a disc image or folder (default: game/)")
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("tmp/pc/characters"))
    parser.add_argument("--character", type=int, help="just this one, 1 to 64")
    parser.add_argument("--frames", action="store_true", help="every frame of every layer too")
    parser.add_argument("--sheet", action="store_true", help="the three pages as they are stored too")
    parser.add_argument("--scale", type=int, default=1, help="draw at this many times the console's size")
    parser.add_argument("--check", action="store_true", help="walk every part and report, writing nothing")
    options = parser.parse_args()

    files = disc.load(options.game) if options.game else disc.find_game()
    if not files:
        return int(bool(print("no game files found; name a disc image or folder with --game")))
    if options.check:
        return check(files.wa)

    wanted = [options.character] if options.character else range(1, CHARACTERS + 1)
    written = 0
    for cid in wanted:
        if not 1 <= cid <= CHARACTERS:
            return int(bool(print("a character is 1 to %d" % CHARACTERS)))
        one = Character(files.wa, cid)
        folder = options.out / slug(cid)
        if options.sheet:
            write_png(folder / "sheet.png", sheet_rows(one))
            written += 1
        for pose in range(one.poses()):
            body = one.frames(pose, 0)
            eyes = one.shapes(pose, 1)
            mouths = one.shapes(pose, 2)
            body_sheet = [one.parts(body[0][1])] if body else []

            def put(name, eye, mouth):
                layers = list(body_sheet)
                if eye is not None:
                    layers.append(one.parts(eye))
                if mouth is not None:
                    layers.append(one.parts(mouth))
                rows, _ = draw(one, layers, options.scale)
                if rows:
                    write_png(folder / name, rows)
                    return 1
                return 0

            resting_eye = eyes[0] if eyes else None
            resting_mouth = mouths[0] if mouths else None
            written += put("pose%d.png" % pose, resting_eye, resting_mouth)
            # Each shape the layer has, the other layer left at rest.
            for index in range(1, len(eyes)):
                written += put("pose%d-eyes%d.png" % (pose, index), eyes[index], resting_mouth)
            for index in range(1, len(mouths)):
                written += put("pose%d-mouth%d.png" % (pose, index), resting_eye, mouths[index])
            if not options.frames:
                continue
            for layer, strip in enumerate(layers):
                for index, (_, offset) in enumerate(strip):
                    rows, _ = draw(one, [one.parts(offset)], options.scale)
                    if rows:
                        write_png(folder / ("pose%d-%s-%d.png" % (pose, LAYERS[layer], index)), rows)
                        written += 1
        shapes = [(len(one.shapes(pose, 1)), len(one.shapes(pose, 2))) for pose in range(one.poses())]
        print("%-28s %d pose(s), %s%s" % (
            slug(cid), one.poses(),
            ", ".join("%d eye / %d mouth" % (e, m) for e, m in shapes) or "nothing",
            "" if one.poses() else "  (nothing the script reaches)"))
    print("%d images under %s" % (written, options.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
