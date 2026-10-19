"""Keep PS1 RAM addresses distinct from offsets in game files."""
from __future__ import annotations

from .binary import slus_offset


def slus_ram(address: int, length: int = 1) -> tuple[int, int]:
    """Return the file range for a SLUS RAM range, validating its size."""
    if length < 0:
        raise ValueError("negative address range length")
    start = slus_offset(address)
    return start, start + length


def archive_range(offset: int, length: int) -> tuple[int, int]:
    """Return a WA_MRG.MRG-relative range without pretending it is SLUS RAM."""
    if offset < 0 or length < 0:
        raise ValueError("negative archive range")
    return offset, offset + length
