"""Bounds-safe readers for executable and archive data."""
from __future__ import annotations

from dataclasses import dataclass

from .. import gamedata


@dataclass(frozen=True)
class BinaryReader:
    """A small little-endian reader that never silently truncates a read."""

    data: memoryview
    source: str = "binary"

    def __init__(self, data: bytes | bytearray | memoryview, source: str = "binary"):
        object.__setattr__(self, "data", memoryview(data).cast("B"))
        object.__setattr__(self, "source", source)

    def __len__(self) -> int:
        return len(self.data)

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0:
            raise ValueError(f"{self.source}: negative offset or length")
        end = offset + length
        if end > len(self.data):
            raise ValueError(f"{self.source}: read 0x{offset:X}-0x{end:X} is outside 0x{len(self.data):X}")
        return self.data[offset:end].tobytes()

    def u8(self, offset: int) -> int:
        return self.read(offset, 1)[0]

    def u16(self, offset: int) -> int:
        return int.from_bytes(self.read(offset, 2), "little")

    def u32(self, offset: int) -> int:
        return int.from_bytes(self.read(offset, 4), "little")

    def changed(self, retail: "BinaryReader", offset: int, length: int) -> bool:
        return self.read(offset, length) != retail.read(offset, length)

    def equals(self, offset: int, expected: bytes) -> bool:
        return self.read(offset, len(expected)) == expected

    def diff_ranges(self, retail: "BinaryReader") -> list[tuple[int, int]]:
        """Return contiguous changed ranges, including a size mismatch tail."""
        shared = min(len(self), len(retail))
        ranges: list[tuple[int, int]] = []
        start = None
        for offset in range(shared):
            differs = self.data[offset] != retail.data[offset]
            if differs and start is None:
                start = offset
            elif not differs and start is not None:
                ranges.append((start, offset))
                start = None
        if start is not None:
            ranges.append((start, shared))
        if len(self) != len(retail):
            ranges.append((shared, max(len(self), len(retail))))
        return ranges


def slus_offset(address: int) -> int:
    """Map a PS1 executable RAM address to a SLUS_014.11 file offset."""
    if address < gamedata.EXE_DELTA:
        raise ValueError(f"0x{address:X} is not a SLUS RAM address")
    return gamedata.slus_offset(address)
