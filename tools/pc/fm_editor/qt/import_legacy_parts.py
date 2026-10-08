"""Structured BIN readers retained from the committed PySide importer.

These readers deliberately live beside the modern-editor compatibility layer:
they make imported assets editable without changing the tracked importer.
"""
from __future__ import annotations

import struct

from .. import art, gamedata as g, guardian_stars, pngio


def _art_regions(card_id: int) -> dict:
    base = art.record_base(card_id)
    thumbnail = (card_id - 1) * art.SECTOR
    return {
        "art": (base, base + art.TITLE_PIXELS),
        "title": (base + art.TITLE_PIXELS, base + art.ART_SECTORS * art.SECTOR),
        "thumbnail": (thumbnail, thumbnail + art.THUMB_CLUT + 2 * 64),
    }


def _recognisable_art(retail_wa: bytes, modded_wa: bytes, card_id: int, part: str) -> bool:
    start, _ = _art_regions(card_id)[part]
    if part == "title":
        length = 48 * art.SIZES[part][1]
        changed = [new for old, new in zip(retail_wa[start:start + length], modded_wa[start:start + length])
                   if old != new]
        return len(changed) >= 64 and all((byte & 0x0F) < 8 and byte >> 4 < 8 for byte in changed)
    width, height = art.SIZES[part]
    changed = [new for old, new in zip(retail_wa[start:start + width * height],
                                       modded_wa[start:start + width * height]) if old != new]
    return len(changed) >= 128 and len(set(changed)) > 2


def import_card_art(project, retail_wa: bytes, modded_wa: bytes, report: list, say=None) -> int:
    """Extract changed retail-card pictures into editable PNG replacements."""
    counted = {part: 0 for part in art.PARTS}
    unreadable = []
    for card_id in range(1, g.CARD_COUNT + 1):
        if say and (card_id == 1 or card_id % 24 == 0 or card_id == g.CARD_COUNT):
            say(f"Importing card art: {card_id}/{g.CARD_COUNT}")
        for part in art.PARTS:
            start, end = _art_regions(card_id)[part]
            if end > len(modded_wa) or retail_wa[start:end] == modded_wa[start:end]:
                continue
            if not _recognisable_art(retail_wa, modded_wa, card_id, part):
                continue
            try:
                art.set_image(project, card_id, part, art.disc_image(modded_wa, card_id, part))
                counted[part] += 1
            except (ValueError, OSError, IndexError, pngio.PngError) as problem:
                unreadable.append(f"{project.card_label(card_id)} {part} ({problem})")
    total = sum(counted.values())
    if total:
        summary = ", ".join(f"{counted[part]} {art.LABELS[part].lower()}"
                            for part in art.PARTS if counted[part])
        report.append(f"art: {summary} extracted as editable PNG replacements")
    if unreadable:
        report.append(f"art: {len(unreadable)} changed parts remain archive data ({'; '.join(unreadable[:3])})")
    return total


STAR_NAME_INDEX = 0x317
GUARDIAN_MATCHUP = 0x8002CB80


def _star_names(slus: bytes) -> dict:
    """Read the named Guardian-Star slots from the game names bank."""
    from ..gamedata import _tl
    try:
        image = g._image(slus)
        glyphs = _tl.glyph_characters(image)
    except Exception:
        return {}
    out = {}
    try:
        for star in range(1, guardian_stars.MAX_STARS + 1):
            at = g.NAME_BANK + image.u16(_tl.NAME_TABLE + (STAR_NAME_INDEX + star) * 2)
            text = ""
            while len(text) < 24:
                code = image.bytes(at, 1)[0]
                if code >= 0xF0:
                    break
                text += glyphs.get(code, "?")
                at += 1
            out[star] = text.strip()
    except (IndexError, KeyError, ValueError, struct.error):
        return {}
    return out


def _guardian_masks(slus: bytes):
    """Return the recognised community 16-star matchup table, if installed."""
    at = g.slus_offset(GUARDIAN_MATCHUP)
    if at < 0 or at + 116 > len(slus):
        return None
    words = struct.unpack_from("<29I", slus, at)
    fixed = (0x2484FFFF, 0x24A5FFFF, None, None, 0x00051840, 0x00431821, 0x94630000,
             0x00000000, 0x00831806, 0x30630001, 0x1460000A, 0x2403FE0C,
             0x00041840, 0x00431821, 0x94630000, 0x00000000, 0x00A31806,
             0x30630001, 0x14600002, 0x240301F4, 0x24030000, 0x00601021,
             0x03E00008, 0x00000000, 0x10850002, 0x2402FE0C, 0x00001021,
             0x03E00008, 0x00000000)
    if (any(expected is not None and word != expected for word, expected in zip(words, fixed))
            or words[2] >> 16 != 0x3C02 or words[3] >> 16 != 0x2442):
        return None
    base = ((words[2] & 0xFFFF) << 16) + struct.unpack("<h", struct.pack("<H", words[3] & 0xFFFF))[0]
    table = g.slus_offset(base)
    if table < 0 or table + 32 > len(slus):
        return None
    return list(struct.unpack_from("<16H", slus, table))


def import_guardian_stars(project, retail, modded, retail_slus: bytes, modded_slus: bytes,
                          modded_wa: bytes, report: list) -> int:
    """Import renamed slots, custom IDs, recognised matchups, and custom icons."""
    old_names, new_names = _star_names(retail_slus), _star_names(modded_slus)
    named = {star: new_names[star] for star in new_names
             if new_names[star] and new_names[star] != old_names.get(star)}
    worn = {value for card in modded.cards.values() for value in (card.star1, card.star2)
            if value > guardian_stars.RETAIL_COUNT}
    entries = [{"id": star, **({"name": named[star]} if star in named else {})}
               for star in sorted(set(named) | worn)]
    masks = _guardian_masks(modded_slus)
    if not entries and masks is None:
        return 0
    section = dict(project.other.get("guardian_stars") or {})
    section["stars"] = entries
    if masks is not None:
        pairs = []
        for attacker in range(1, guardian_stars.MAX_STARS + 1):
            for defender in range(1, guardian_stars.MAX_STARS + 1):
                if attacker == defender or masks[defender - 1] & (1 << (attacker - 1)):
                    bonus = -guardian_stars.RETAIL_BONUS
                elif masks[attacker - 1] & (1 << (defender - 1)):
                    bonus = guardian_stars.RETAIL_BONUS
                else:
                    bonus = 0
                if bonus != guardian_stars.retail_matchup(attacker, defender):
                    pairs.append({"attacker": attacker, "defender": defender, "bonus": bonus})
        section["matchups"] = pairs
        for entry in entries:
            if entry["id"] <= guardian_stars.RETAIL_COUNT:
                continue
            found = guardian_stars.imported_icon(modded_wa, entry["id"])
            if found is not None:
                path = f"icons/star-{entry['id']}.png"
                project.files[path] = pngio.encode(pngio.Image(*found))
                entry["icon"] = path
        report.append(f"guardian stars: imported the 16-star matchup table ({len(pairs)} changed pairs)")
    project.other["guardian_stars"] = section
    report.append(f"guardian stars: imported {len(entries)} renamed or used slot"
                  + ("s" if len(entries) != 1 else ""))
    return len(entries)
