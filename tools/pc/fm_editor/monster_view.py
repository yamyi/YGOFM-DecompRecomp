"""Read the battle models from MODEL.MRG, as mods/3d-monsters does.

The viewer uses the HMD's stored pose (not the game's animation interpreter).
Coordinates, shared vertices and texture relocation follow the native model
loader, libgs_unit.c and model_polygon_drivers.c. No game data is modified.
"""
from __future__ import annotations

import math
import struct
from array import array
from pathlib import Path

from . import disc, map_view, pngio

SECTOR = 2048
RECORD_SIZE = 0x114 * SECTOR


class ModelError(ValueError):
    pass


def record_index(card_id):
    model = card_id - 1
    if not 0 <= model < 0x2D2 or 0x12C <= model < 0x15E or 0x28A <= model < 0x2BC or model == 0x2D0:
        return None
    return model - (model >= 0x2D1) - 50 * (model >= 0x2BC) - 50 * (model >= 0x15E)


def model_card(project, cid):
    """Cards_ModelId: an explicit disc model, or the copied base's model."""
    added = project.added.get(cid)
    extra = added.extra if added else project.card_extra.get(cid, {})
    if "model" in extra:
        resolved = project.resolve(extra["model"])
        if resolved in project.retail.cards and record_index(resolved) is not None:
            return resolved
    return model_card(project, added.base) if added else cid


def read_record(source, cid):
    index = record_index(cid)
    if index is None:
        raise ModelError("This card has no in-game 3D model.")
    source = Path(source)
    offset = index * RECORD_SIZE
    if source.is_dir():
        archive = source / "DATA" / "MODEL.MRG"
        if archive.is_file():
            with archive.open("rb") as stream:
                stream.seek(offset)
                data = stream.read(RECORD_SIZE)
            if len(data) != RECORD_SIZE:
                raise ModelError("MODEL.MRG is truncated.")
            return data
        # An extracted editor folder may contain just SLUS and WA, with the
        # complete disc beside them (the source tree's game/ layout).
        images = sorted(p for p in source.iterdir() if p.suffix.lower() in (".bin", ".iso"))
        for image in images:
            try:
                return read_record(image, cid)
            except disc.GameFilesError:
                continue
        raise ModelError("MODEL.MRG was not found. Open a complete game disc, or add DATA/MODEL.MRG to the game folder.")
    if not source.is_file():
        raise ModelError("The game source is unavailable. Open a complete game disc to view its 3D models.")
    with disc.DiscImage(source) as image:
        entry = image.find("DATA/MODEL.MRG")
        if entry is None:
            raise disc.GameFilesError("This disc has no DATA/MODEL.MRG.")
        lba, size = entry
        if offset + RECORD_SIZE > size:
            raise ModelError("MODEL.MRG is truncated.")
        return image.read(lba + offset // SECTOR, RECORD_SIZE)


IDENTITY = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))


def transform(matrix, vector):
    return tuple(sum(matrix[i][j] * vector[j] for j in range(3)) for i in range(3))


class MonsterModel:
    def __init__(self, record):
        if len(record) != RECORD_SIZE:
            raise ModelError("Incomplete MODEL.MRG record.")
        self.blob = record[:96 * SECTOR]
        self.vram = array("H", [0]) * (1024 * 512)
        self.polygons = []  # (world vertices, UV words, clut, tpage)
        self._coords = {}
        try:
            self._textures(record)
            self._parse()
        except (struct.error, IndexError, KeyError, RecursionError) as error:
            raise ModelError("The disc model contains invalid geometry or texture data.") from error
        points = [v for vertices, *_ in self.polygons for v in vertices]
        if not points:
            raise ModelError("This card has no viewable model geometry.")
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        self.centre = tuple((a + b) / 2 for a, b in zip(low, high))
        self.radius = max(math.dist(p, self.centre) for p in points) or 1

    def word(self, n):
        if n < 0 or n * 4 + 4 > len(self.blob):
            raise ModelError("Invalid HMD offset.")
        return struct.unpack_from("<I", self.blob, n * 4)[0]

    def _upload(self, x, y, width, height, data):
        if not (0 <= x <= 1024 - width and 0 <= y <= 512 - height):
            raise ModelError("Invalid model texture rectangle.")
        words = struct.unpack(f"<{width * height}H", data)
        for row in range(height):
            start = (y + row) * 1024 + x
            self.vram[start:start + width] = array("H", words[row * width:(row + 1) * width])

    def _textures(self, record):
        # run_record_slot's texture uploads, in the slot-0 VRAM bank.
        for i in range(48):
            at = (96 + i) * SECTOR
            self._upload(i // 16 * 64, 256 + i % 16 * 16, 64, 16, record[at:at + SECTOR])
        self._upload(0, 240, 256, 8, record[144 * SECTOR:146 * SECTOR])
        self._upload(512, 242, 256, 1, record[146 * SECTOR:146 * SECTOR + 512])
        for i in range(16):
            at = (147 + i) * SECTOR
            self._upload(192, 256 + i * 16, 64, 16, record[at:at + SECTOR])

    def _coordinate(self, at, visiting=()):
        if at in self._coords:
            return self._coords[at]
        if at in visiting or len(visiting) > 64:
            raise ModelError("Cyclic model coordinates.")
        values = struct.unpack_from("<9h", self.blob, at * 4 + 4)
        matrix = tuple(tuple(values[i * 3 + j] / 4096 for j in range(3)) for i in range(3))
        position = struct.unpack_from("<3i", self.blob, at * 4 + 24)
        parent = self.word(at + 19)
        if parent:
            pm, pp = self._coordinate(parent, visiting + (at,))
            matrix = tuple(tuple(sum(pm[i][k] * matrix[k][j] for k in range(3)) for j in range(3)) for i in range(3))
            position = tuple(a + b for a, b in zip(transform(pm, position), pp))
        self._coords[at] = matrix, position
        return matrix, position

    def _vertex(self, section, index, coord):
        v = struct.unpack_from("<3h", self.blob, section * 4 + index * 8)
        matrix, position = coord
        return tuple(a + b for a, b in zip(transform(matrix, v), position))

    def _parse(self):
        word = self.word
        if not 0 < word(3) <= 64:
            raise ModelError("Invalid HMD unit count.")
        cursor = word(2)
        count = word(cursor)
        if count > 64:
            raise ModelError("Invalid HMD section count.")
        headers = {}
        cursor += 1
        for _ in range(count):
            n = word(cursor)
            if n > 16:
                raise ModelError("Invalid HMD header.")
            headers[cursor] = [word(cursor + i + 1) & 0x7fffffff for i in range(n)]
            cursor += n + 1
        records = []
        coords = None
        for unit in range(word(3)):
            block = word(4 + unit)
            seen = set()
            while block and block != 0xffffffff:
                if block in seen:
                    raise ModelError("Cyclic HMD blocks.")
                seen.add(block)
                sections = headers[word(block + 1)]
                cursor = block + 3
                for _ in range(word(block + 2) & 65535):
                    kind, head = word(cursor), word(cursor + 1)
                    size, items = head & 65535, (head >> 16) & 32767
                    if size < 1:
                        raise ModelError("Invalid HMD primitive size.")
                    if kind & 0x800000:
                        coords = sections[-1]
                    records.append((unit, kind & ~0x800000, cursor, items, sections))
                    cursor += size + 1
                block = word(block)
        if coords is None:
            raise ModelError("The model has no coordinate table.")
        def coordinate(unit):
            if 1 <= unit < word(3) - 1:
                return self._coordinate(coords + 1 + (unit - 1) * 20)
            return IDENTITY, (0, 0, 0)
        shared = {}
        # Shared polygons join vertices owned by different bones. The game's
        # pre-pass projects them into a common buffer; keep world positions.
        for unit, kind, cursor, _, sections in records:
            if kind == 0x1000000:
                count, source, destination = (word(cursor + i) for i in (2, 3, 4))
                if count > 8192:
                    raise ModelError("Invalid shared vertex count.")
                for i in range(count):
                    shared[(sections[2], destination + i)] = self._vertex(sections[1], source + i, coordinate(unit))
        for unit, kind, cursor, items, sections in records:
            shape = kind & 0xffff
            if shape not in (9, 13, 17, 21, 0x209, 0x20d, 0x211, 0x215):
                continue
            quad, gouraud, window = bool(shape & 16), bool(shape & 4), bool(shape & 512)
            corners = 4 if quad else 3
            stride = (14 if gouraud else 12) if quad else (12 if gouraud else 10)
            at = (sections[0] + word(cursor + 2)) * 4
            for i in range(items):
                start = at + i * (stride * 2 + (4 if window else 0)) + (4 if window else 0)
                r = struct.unpack_from(f"<{stride}H", self.blob, start)
                indices = [r[7 + j * 2] if gouraud else r[(8 if quad else 7) + j] for j in range(corners)]
                if kind & 0x1000000:
                    vertices = [shared[(sections[2], index)] for index in indices]
                else:
                    vertices = [self._vertex(sections[1], index, coordinate(unit)) for index in indices]
                uvs = [r[0], r[2], r[4]] + ([r[6]] if quad else [])
                # func_8004D134 relocates the authored pages/palettes to slot 0.
                page = (r[3] - 10) & 65535
                if (r[3] >> 7) & 3 == 3:
                    page &= 0xff7f
                clut = r[1]
                if (r[3] >> 7) & 3 < 2:
                    clut = (clut + 0x3bd8) & 65535
                    if r[1] >> 6 >= 16:
                        clut = ((clut & 63) + 16) | (((r[1] >> 6) % 16) << 6)
                self.polygons.append((vertices, uvs, clut, page))


def render(model, yaw=30, pitch=-10, zoom=1., size=(320, 320)):
    """An orbit view of the stored pose, with PS1 affine textures and depth."""
    matrix = map_view.rotation_yxz(pitch * 4096 / 360, yaw * 4096 / 360, 0)
    width, height = size
    scale = min(size) * .42 * zoom / model.radius
    faces = []
    for vertices, uvs, clut, page in model.polygons:
        points = []
        for v, uv in zip(vertices, uvs):
            x, y, z = transform(matrix, tuple(v[i] - model.centre[i] for i in range(3)))
            points.append((width / 2 + x * scale, height / 2 + y * scale, z, uv & 255, uv >> 8, 1.))
        for tri in ((0, 1, 2),) if len(points) == 3 else ((0, 1, 2), (1, 3, 2)):
            faces.append(([points[i] for i in tri], page, clut, None))
    out = bytearray(bytes((16, 26, 42, 255)) * (width * height))
    map_view._rasterize(size, faces, model.vram, out, [float("inf")] * (width * height))
    return pngio.Image(width, height, bytes(out))
