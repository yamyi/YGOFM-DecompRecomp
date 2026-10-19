"""Known TeaTools input formats and importer diagnostics.

This module is deliberately declarative.  It records the formats the importer
can recognise without importing or depending on a local TeaTools checkout.
The checkout is useful documentation and fixture material, but a shipped FM
Editor must work without it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeaToolsFormat:
    """A TeaTools writer, its inputs, and the PySide workspace it feeds."""

    identifier: str
    workspace: str
    source_files: tuple[str, ...]
    destination: str
    coverage: str


# Keep this inventory close to the importer.  A format only says where its
# documented output lives; ``coverage`` says what the editor can genuinely
# recover today, instead of implying that every changed byte is editable.
FORMATS = (
    TeaToolsFormat("cardsdata", "Cards", ("SLUS_014.11",),
                   "card stats, levels, numeric types and attributes", "tables"),
    TeaToolsFormat("process-cardcolor", "Cards / UI > Frames", ("SLUS_014.11", "DATA/WA_MRG.MRG"),
                   "per-card frame colours and frame palettes", "partial"),
    TeaToolsFormat("image-cardsleeves", "UI > Frames", ("SLUS_014.11", "DATA/WA_MRG.MRG"),
                   "large card frame artwork and recognised layout fields", "partial"),
    TeaToolsFormat("image-minicardsleeves", "UI > Frames", ("DATA/WA_MRG.MRG",),
                   "mini and micro card graphics", "not yet decoded"),
    TeaToolsFormat("logo", "UI > Title screen", ("DATA/SU.MRG",),
                   "title wallpaper, logo and menu sprites", "sprites"),
    TeaToolsFormat("image-field", "UI > Duel board / Game Rules", ("DATA/WA_MRG.MRG", "SLUS_014.11"),
                   "terrain textures, field labels and bonuses", "not yet decoded"),
    TeaToolsFormat("image-gamefont", "UI > Assets", ("DATA/WA_MRG.MRG",),
                   "game font sheet and palette", "not yet decoded"),
    TeaToolsFormat("initial-deck", "Starter decks", ("DATA/WA_MRG.MRG",),
                   "starter-deck tables", "tables"),
)


def formats() -> tuple[TeaToolsFormat, ...]:
    """The immutable TeaTools format registry, in UI/importer order."""
    return FORMATS


def format_named(identifier: str) -> TeaToolsFormat | None:
    """Return a known format without making callers know registry storage."""
    return next((item for item in FORMATS if item.identifier == identifier), None)
