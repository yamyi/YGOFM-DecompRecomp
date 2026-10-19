"""A community mod's modified game files, turned into a port mod.

The mods of the PS1 scene (Mod 13, FM 2023, Shin...) ship patched copies of
SLUS_014.11 and WA_MRG.MRG, or a patched disc. This compares them with the
player's retail files and writes what differs in the port's terms:

* cards, fusions, equips, rituals, deck and drop pools: the editor's own
  diff (manifest.build), so the result opens in the editor like any mod;
* other text (dialogue, menus, types, duelists, places): a partial text
  listing (text_listing.py's format), "text" in mod.json;
* other changed bytes of WA_MRG.MRG (images, passwords and costs, starter
  decks...): "data" patches, or sector replacements for long runs; the port
  reads WA_MRG.MRG through its override layer, so they apply;
* what the port cannot take from a data file (code and tables in the
  executable, such as the AI's parameters or the field bonuses; other disc
  files) is listed in the report instead.
"""
from __future__ import annotations

import bisect
import json
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from . import art, duelist_rules, gamedata as g, guardian_stars, kit, manifest, pngio, starter_pools, tea_import, teatools_import, ui_assets, values
from .fixed_decks import set_deck as set_fixed_deck
from .model import Project, StarterDeck, duelist_named
from .pools import normalize

# ``extract_images`` lives beside the editor package.  The editor is also
# imported as the top-level ``fm_editor`` package by its test suite, so use
# both valid import paths rather than making the importer depend on one launch
# convention.
try:
    from tools.pc import extract_images as image_extract
except ImportError:  # pragma: no cover - exercised by PYTHONPATH=tools/pc
    import extract_images as image_extract

WA_FILE = "\\DATA\\WA_MRG.MRG;1"
SECTOR = 2048
MERGE_GAP = 32              # changed runs closer than this are one patch
PATCH_LIMIT = 4096          # longer runs become sector replacements
# The port holds 65536 patched runs and 4096 replaced regions for all the mods
# together (src/pc/mods/mods.c PATCHES_MAX, REGIONS_MAX); a quarter of each is
# this mod's own share, leaving the rest for whatever else is active. Past
# these a mod replaces the whole file instead of a patch list.
WA_PATCHES_MOST = 16384
WA_REGIONS_MOST = 1024
# A common rebuilt-disc enable patch: it changes the boot compliance branch,
# rather than any game feature a generated mod should reproduce.
IGNORED_WA_IMPORT_RANGES = ((0xB61902, 0xB61903),)

# Executable regions the port has no data key for, by RAM address.
SLUS_REGIONS = [
    (0x800909D4, 0x80090A4C, "field (terrain) bonus table"),
    (0x80090A4C, 0x80090AD4, "destroy-by-type/ATK effect table"),
    (0x80090AD4, 0x80090B39, "magic effect classes"),
    (0x800917F0, 0x80091958, "opponents' AI parameters (9 bytes each)"),
    (0x8009AF24, 0x8009AF40, "trap ceilings / heal and burn amounts"),
    (0x8001A7F8, 0x8001A7FC, "equip bonus (+500)"),
    (0x8001A820, 0x8001A824, "Megamorph bonus (+1000)"),
    (0x801D9000, 0x801D9170, "the font's glyph table"),
    (0x801D5EC0, 0x801D6000, "the names table's entries 0x8360-0x83FF (past the ones the text listing reads)"),
]
# Executable regions the editor turns into cards[]; the text banks' bytes
# the text listing reads are added per file (text_spans).
SLUS_HANDLED = [
    (g.STATS_ADDRESS, g.STATS_ADDRESS + 4 * g.CARD_COUNT),
    (g.LEVEL_ATTR_ADDRESS, g.LEVEL_ATTR_ADDRESS + g.CARD_COUNT + 1),
]
TEXT_BANKS = [(0x801B0000, 0x801C0000, "the dialog bank"), (0x801C0000, 0x801D0000, "the card texts' bank"),
              (0x801D0000, 0x801E0000, "the names bank")]
PLACES_SHOWN = 12           # changed places listed one by one in the report

# The drop draw (Duel_SelectCardDrop) adds each card's weight at this
# instruction. The TeaOnline drop tool's mods write every drop weight as
# bias + 8*weight + noise and replace it with a jump to code that undoes it.
DRAW_ADD = 0x80021860
TEAONLINE_ENCODING = (2512, 3)      # (bias, shift) that tool writes
DROP_POOLS = ("pow", "bcd", "tec")  # the deck pools are never encoded


def slug(text: str) -> str:
    """A mod id out of a file name (File > Import and the command line)."""
    text = re.sub(r"[^A-Za-z0-9_-]+", "-", Path(text).stem).strip("-").lower()
    return (text or "imported-mod")[:63]


@dataclass(frozen=True)
class ImportFinding:
    """One source feature's import outcome, suitable for a detailed summary."""

    feature: str
    workspace: str
    status: str                 # recovered, partial, raw, unsupported, unchanged
    source_file: str
    details: str


@dataclass
class ImportResult:
    project: Project
    report: list = field(default_factory=list)       # lines for the user
    unhandled: int = 0                               # count of things the port cannot take
    findings: list[ImportFinding] = field(default_factory=list)
    handled_ranges: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    analysis: object | None = None
    analysis_status: dict[str, str] = field(default_factory=dict)

    def finding(self, feature: str, workspace: str, status: str, source_file: str, details: str,
                ranges: list[tuple[int, int]] | None = None) -> None:
        """Record a structured outcome without making reporting all-or-nothing."""
        self.findings.append(ImportFinding(feature, workspace, status, source_file, details))
        if ranges:
            self.handled_ranges.setdefault(source_file, []).extend(ranges)


def _starter_analysis_matches_project(project: Project, records: list) -> bool:
    """Whether the ordinary starter importer already expressed decoded pools."""
    pools = project.other.get("starter_pools")
    if not isinstance(pools, list) or len(pools) != len(records):
        return False
    for pool, record in zip(pools, records):
        if not isinstance(pool, dict) or pool.get("draws") != record.get("draws"):
            return False
        cards = pool.get("cards")
        expected = {str(card): weight for card, weight in record.get("weights", {}).items()}
        if cards != expected:
            return False
    return True


def _tea_analysis_status(result: ImportResult) -> None:
    """Describe analysis/import relation without letting analysis mutate Project."""
    analysis = result.analysis
    if analysis is None:
        return
    for feature in analysis.features:
        if feature.feature_id == "initial_deck" and _starter_analysis_matches_project(result.project,
                                                                                        feature.data.get("records", [])):
            result.analysis_status[feature.feature_id] = "already_imported"
        elif feature.compatibility.value == "supported":
            result.analysis_status[feature.feature_id] = "ready_for_conversion"
        else:
            result.analysis_status[feature.feature_id] = "needs_engine_support"


def _runs(a: bytes, b: bytes, start: int, end: int, gap: int = MERGE_GAP):
    """[start, end) runs where a and b differ, merged across small gaps."""
    runs = []
    at = start
    end = min(end, len(a), len(b))
    step = 4096
    while at < end:
        stop = min(at + step, end)
        if a[at:stop] == b[at:stop]:
            at = stop
            continue
        for i in range(at, stop):
            if a[i] != b[i]:
                if runs and i - runs[-1][1] <= gap:
                    runs[-1][1] = i + 1
                else:
                    runs.append([i, i + 1])
        at = stop
    return [tuple(r) for r in runs]


def _trim(a: bytes, b: bytes, runs):
    """Each run cut down to its first and last differing byte; runs where
    nothing differs (a gap between two regions, left by _subtract) dropped."""
    out = []
    for start, end in runs:
        while start < end and a[start] == b[start]:
            start += 1
        while end > start and a[end - 1] == b[end - 1]:
            end -= 1
        if start < end:
            out.append((start, end))
    return out


def _merge(runs, gap: int):
    out = []
    for start, end in sorted(runs):
        if out and start - out[-1][1] <= gap:
            out[-1] = (out[-1][0], max(end, out[-1][1]))
        else:
            out.append((start, end))
    return out


def _subtract(runs, regions):
    """The parts of runs outside every region.

    Walked rather than cut: the regions are merged and sorted once, and each
    run only meets the few it overlaps. Cutting every run by every region
    was fine for the handful of structured tables, but the pictures a mod
    changes are hundreds more, and it went quadratic."""
    merged = _merge(regions, 0)
    starts = [low for low, _high in merged]
    out = []
    for start, end in runs:
        at = start
        index = max(0, bisect.bisect_right(starts, at) - 1)
        while index < len(merged) and at < end:
            low, high = merged[index]
            if high <= at:
                index += 1
                continue
            if low >= end:
                break
            if at < low:
                out.append((at, low))
            at = high
            index += 1
        if at < end:
            out.append((at, end))
    return out


def wa_structured_regions():
    regions = []
    for k in range(g.TERRAIN_COPIES):
        base = g.TERRAIN_BASE + k * g.TERRAIN_STRIDE
        regions += [(base + g.EQUIP_OFFSET, base + g.EQUIP_OFFSET + g.EQUIP_LENGTH),
                    (base + g.FUSION_OFFSET, base + g.FUSION_OFFSET + g.FUSION_LENGTH),
                    (base + g.RITUAL_OFFSET, base + g.RITUAL_OFFSET + g.RITUAL_LENGTH)]
    for d in range(g.DUELIST_COUNT):
        for offset in g.POOL_OFFSETS.values():
            start = g.DUELIST_BASE + d * g.DUELIST_STRIDE + offset
            regions.append((start, start + 2 * g.CARD_COUNT))
    # Passwords and starchip costs: read into project.passwords/starchips
    # above and written back as the manifest's "passwords" key, which the
    # port reads natively -- the raw table stays retail's like the other
    # structured regions above.
    regions.append((g.PASSWORD_TABLE, g.PASSWORD_TABLE + 8 * (g.CARD_COUNT + 1)))
    return regions


def describe_wa(offset: int) -> str:
    if 0x169000 <= offset < 0x169000 + 0x3800 * g.CARD_COUNT:
        return "the cards' pictures and name plates"
    if offset < 0x800 * g.CARD_COUNT:
        return "the cards' small pictures"
    if 0xFB9800 <= offset < 0xFB9800 + 8 * 723:
        return "the cards' passwords and starchip costs"
    if g.STARTER_BASE <= offset < g.STARTER_BASE + g.STARTER_LENGTH:
        return "the starter deck pools"
    if 0xF55000 <= offset < 0xF55000 + 40 * 2432:
        return "the duelists' portraits"
    if g.DUELIST_BASE <= offset < g.DUELIST_BASE + g.DUELIST_COUNT * g.DUELIST_STRIDE:
        inside = (offset - g.DUELIST_BASE) % g.DUELIST_STRIDE
        return "the opponents' records (between their pools)" if inside < 4 * 0x5B4 else \
            "the opponents' records (rank tables)"
    if g.TERRAIN_BASE <= offset < g.TERRAIN_BASE + g.TERRAIN_COPIES * g.TERRAIN_STRIDE:
        return f"the duel package (terrain copy {(offset - g.TERRAIN_BASE) // g.TERRAIN_STRIDE})"
    return "WA_MRG.MRG"


# --- the executable's code ------------------------------------------------------------

def _word(slus: bytes, address: int):
    at = g.slus_offset(address)
    return struct.unpack_from("<I", slus, at)[0] if 0 <= at <= len(slus) - 4 else None


def _jump_target(word: int, address: int) -> int:
    return ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


def jumps_into(retail_slus: bytes, slus: bytes, places) -> dict:
    """{(start, end): ["j at 0x80021860 (patched)", ...]}: the j and jal
    instructions of the executable that land in each [start, end) RAM range;
    "patched" when that instruction is not retail's."""
    found = {place: [] for place in places}
    ranges = sorted(places)
    starts = [start for start, _ in ranges]
    header = g.slus_offset(0x80010000)
    for index, (word,) in enumerate(struct.iter_unpack("<I", slus[header:header + (len(slus) - header) // 4 * 4])):
        if word >> 26 not in (2, 3):
            continue
        address = 0x80010000 + 4 * index
        target = _jump_target(word, address)
        k = bisect.bisect_right(starts, target) - 1
        if k >= 0 and target < ranges[k][1]:
            patched = " (patched)" if _word(retail_slus, address) != word else ""
            found[ranges[k]].append(f"{'j' if word >> 26 == 2 else 'jal'} at 0x{address:08X}{patched}")
    return found


def draw_code_encoding(retail_slus: bytes, slus: bytes):
    """(bias, shift, code address) when the drop draw's add (DRAW_ADD) is a
    jump to code that turns the weight into (weight - bias) >> shift with an
    addiu and an sra before anything else branches, else None."""
    word = _word(slus, DRAW_ADD)
    if word is None or word == _word(retail_slus, DRAW_ADD) or word >> 26 != 2:
        return None
    code = _jump_target(word, DRAW_ADD)
    bias = register = None
    for i in range(8):
        w = _word(slus, code + 4 * i)
        if w is None:
            return None
        op, rs, rt, rd = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        if op == 9 and bias is None and rs == rt:                       # addiu r, r, -bias
            imm = w & 0xFFFF
            bias, register = -(imm - 0x10000 if imm & 0x8000 else imm), rt
        elif op == 0 and w & 63 == 3 and bias is not None and rt == rd == register:     # sra r, r, shift
            return bias, (w >> 6) & 31, code
        elif 1 <= op <= 7 or (op == 0 and w & 63 in (8, 9)):             # a branch or a jump first
            return None
    return None


def _raw_pool(wa: bytes, duelist: int, pool: str):
    at = g.DUELIST_BASE + duelist * g.DUELIST_STRIDE + g.POOL_OFFSETS[pool]
    return struct.unpack_from("<%dH" % g.CARD_COUNT, wa, at)


def decode_weights(raw, bias: int, shift: int) -> dict:
    weights = {cid: max(0, (x - bias) >> shift) for cid, x in enumerate(raw, 1)}
    return {cid: w for cid, w in weights.items() if w}


def guess_encoding(raws):
    """(bias, shift) that makes every one of `raws` (pools not adding up to
    2048) add up to exactly 2048 once decoded: the TeaOnline tool's own
    values first, then biases just under the smallest weight. None if none."""
    if not raws:
        return None
    low = min(min(raw) for raw in raws)
    candidates = [TEAONLINE_ENCODING] + [(low - k, shift) for shift in (3, 1, 2, 4) for k in range(1 << shift)]
    for bias, shift in candidates:
        if bias >= 0 and all(sum(max(0, (x - bias) >> shift) for x in raw) == g.POOL_TOTAL for raw in raws):
            return bias, shift
    return None


def text_spans(slus: bytes):
    """[start, end) RAM ranges of the text banks that the text listing reads
    (the two offset tables and every string's bytes), or None when the
    listing cannot follow the file's text."""
    from .gamedata import _tl
    image = g._image(slus)
    spans = [(_tl.STRING_TABLE, _tl.STRING_TABLE + 2 * 0x4FA), (_tl.NAME_TABLE, _tl.NAME_TABLE + 2 * 0x360)]
    try:
        glyphs = _tl.glyph_characters(image)
        for bank in _tl.banks(image):
            ops, _ = _tl.decode_bank(image, bank, glyphs)
            spans += [(bank.base + op.offset, bank.base + op.offset + op.length) for op in ops.values()]
    except Exception:
        return None
    return _merge(spans, 0)


def _where(address: int) -> str:
    if address < 0x80010000:
        return f", in the executable's header (file offset 0x{address - kit.HEADER_ADDRESS:X})"
    for low, high, name in TEXT_BANKS:
        if low <= address < high:
            return f", in {name}"
    return ""


def describe_places(retail_slus: bytes, slus: bytes, pieces) -> list:
    """Report lines for changed file-offset pieces of the executable, grouped
    when close: RAM addresses, bytes, and the jumps that reach them."""
    groups = []
    for start, end in sorted(pieces):
        if groups and start - groups[-1][1] <= MERGE_GAP:
            groups[-1][1:] = [end, groups[-1][2] + end - start]
        else:
            groups.append([start, end, end - start])
    # The header's bytes are where the BIOS leaves them (the kit runs code there).
    places = [(start + (kit.HEADER_ADDRESS if start < 0x800 else g.EXE_DELTA),
               end + (kit.HEADER_ADDRESS if start < 0x800 else g.EXE_DELTA), count) for start, end, count in groups]
    callers = jumps_into(retail_slus, slus, [(start, end) for start, end, _ in places])
    lines = []
    for start, end, count in places[:PLACES_SHOWN]:
        reached = callers[(start, end)]
        more = f" and {len(reached) - 4} more" if len(reached) > 4 else ""
        lines.append(f"  0x{start:08X}-0x{end:08X} ({count} bytes{_where(start)}"
                     f"{'; reached by ' + ', '.join(reached[:4]) + more if reached else ''})")
    if len(places) > PLACES_SHOWN:
        lines.append(f"  ... and {len(places) - PLACES_SHOWN} more places")
    return lines


# --- text ---------------------------------------------------------------------------

USES_LABELS = re.compile(r"\{:L|\{(jump|call|if|choose|f8 1[78]|f8 2[78])\b")
_items = manifest.listing_items
CARD_BANKS = {"names": (0x8000, "name"), "descriptions": (0xD100, "description")}
# The name entry's own strings (the password overlay's box, three lines):
# a mod that turns them into its own menus (a starter deck
# chooser after YES) needs its code, and a menu taller than the box stops
# the retail text engine for good (TextBox_BuildStep waits on a page in a
# loop, func_80039794). They stay retail's.
NAME_ENTRY_IDS = range(0xF0, 0x100)


def _card_ids(bank: str, key: str) -> list:
    """The card ids an item of the names or descriptions bank is for."""
    if bank not in CARD_BANKS:
        return []
    first = CARD_BANKS[bank][0]
    return [i - first for i in manifest.item_ids(key) if 1 <= i - first <= g.CARD_COUNT]


def _card_item(bank: str, key: str) -> bool:
    """A card's name or text, which cards[] carries unless the text file must."""
    if bank == "descriptions":
        return True
    return bank == "names" and bool(manifest.item_ids(key)) and \
        len(_card_ids(bank, key)) == len(manifest.item_ids(key))


class _PackedTexts:
    """An executable whose descriptions bank holds packed card texts."""

    def __init__(self, image, memory: bytes):
        self.image, self.memory, self.data = image, memory, image.data

    def bytes(self, address: int, count: int) -> bytes:
        if address == g.DESCRIPTION_BANK and count == 0x10000:
            return self.memory
        return self.image.bytes(address, count)

    def __getattr__(self, name):
        return getattr(self.image, name)


def wa_description_listing(image, texts: dict, names: dict) -> str:
    """The descriptions a mod keeps in WA_MRG.MRG as listing items: packed
    into banks of under 64 KB (they are plain strings, no jumps), each
    listed as the executable's own bank would be."""
    from .gamedata import _tl
    out, group, size = [], [], 0
    groups = []
    for cid in sorted(texts):
        if size + len(texts[cid]) > 0xF000:
            groups.append(group)
            group, size = [], 0
        group.append(cid)
        size += len(texts[cid])
    groups.append(group)
    for group in groups:
        memory = bytearray(0x10000)
        bank = _tl.Bank("descriptions", g.DESCRIPTION_BANK)
        at = 0x10                                    # offset 0 means "no string"
        for cid in group:
            memory[at:at + len(texts[cid])] = texts[cid]
            bank.ids[0xD100 + cid] = at
            at += len(texts[cid])
        out.append(_tl.write_listing(_PackedTexts(image, bytes(memory)), [bank], names))
    return "\n".join(out)


def modded_listing(modded_slus: bytes, modded_wa: bytes, report: list) -> str:
    """The modified executable's text, bank by bank: a bank the listing
    cannot follow (its bytes are the mod's code) is left out and reported;
    card texts a mod keeps in WA_MRG.MRG are listed from there."""
    from .gamedata import _tl
    image = g._image(modded_slus)
    names = g.plain_names(image, _tl.glyph_characters(image))
    parts = []
    for bank in _tl.banks(image):
        if bank.name == "descriptions" and modded_wa and g.wa_descriptions(modded_slus, modded_wa):
            parts.append(wa_description_listing(image, g.description_bytes(modded_slus, modded_wa), names))
            report.append("text: the card texts are in WA_MRG.MRG (256 bytes a card from 0x2400000, sector "
                          f"{g.WA_TEXT_BASE // 2048}), where the mod's code loads them; read from there")
            continue
        try:
            parts.append(_tl.write_listing(image, [bank], names))
        except Exception as problem:      # a text bank the listing cannot follow
            report.append(f"text: the modified {bank.name} bank could not be read ({problem}); its strings are not "
                          "imported")
    return "\n".join(parts)


def text_changes(retail_slus: bytes, modded_slus: bytes, report: list, modded_wa: bytes = b"",
                 card_fields: dict = None):
    """(A partial listing of the text that differs, {(card id, field): its
    item}), the listing None when nothing differs. Card names and texts are
    left to cards[], except the `card_fields` ({field: card ids}) the text
    file must carry. A bank whose changed strings jump anywhere is written
    whole, so every place they name is in the file."""
    from .gamedata import _tl
    card_fields = card_fields or {}
    before = _items(_tl.write_listing(g._image(retail_slus)))
    after = _items(modded_listing(modded_slus, modded_wa, report))
    out, carried = [], {}

    def wanted(bank, key):
        if not _card_item(bank, key):
            return True
        field = CARD_BANKS.get(bank, (0, ""))[1]
        return any(cid in card_fields.get(field, ()) for cid in _card_ids(bank, key))

    for bank in ("dialog", "names", "descriptions"):
        old, new = before.get(bank, {}), after.get(bank, {})
        if not new:
            continue
        changed = [k for k in new if old.get(k) != new[k] and wanted(bank, k)]
        gone = [k for k in old if k not in new and not _card_item(bank, k)]
        if not changed and not gone:
            continue
        whole = bool(gone) or any(not k.startswith("[") or USES_LABELS.search(new[k]) for k in changed)
        keys = [k for k in new if wanted(bank, k)] if whole else changed
        if bank == "dialog":
            kept = [k for k in keys if any(i in NAME_ENTRY_IDS for i in manifest.item_ids(k))
                    and old.get(k) != new[k] and "{:L" not in new[k].split("\n")[0]]
            if kept:
                keys = [k for k in keys if k not in kept]
                report.append(f"text: the name entry's strings {', '.join(k for k in kept)} stay retail's: the mod "
                              "makes them its own menus (a starter deck chooser after the name), which need its "
                              "code, and a menu taller than the name box's three lines stops the game")
        out.append(f"@bank {bank}\n")
        # No blank line after an item that runs on: a game from before the
        # listing passed over it reads it as a line break of the string's.
        out += [new[k] + ("" if new[k].endswith("{cont}") else "\n") for k in keys]
        for k in keys:
            for cid in _card_ids(bank, k):
                # What the editor shows for the card: the item with its jumps
                # and calls followed, since a mod that shares a name between
                # two cards leaves the card's own item a jump and nothing else.
                carried[(cid, CARD_BANKS[bank][1])] = manifest.followed(new, new[k])
        report.append(f"text: {len(changed)} strings of the {bank} bank differ" +
                      ("; the bank is written whole (its strings jump)" if whole else ""))
    if not out:
        return None, carried
    head = ("# Text of a modified game that differs from retail, written by the FM Editor's importer\n"
            "# (notes/translation.md). Card names and texts are in mod.json, except those with color\n"
            "# or icon codes and those the mod left empty, which only this file can carry.\n\n")
    return head + "\n".join(out), carried


# --- the import ------------------------------------------------------------------------

def _line_ends(text: str) -> str:
    return "\n".join(line.rstrip(" ") for line in text.split("\n"))


def _has_codes(text: bytes) -> bool:
    return any(0xF6 <= b < 0xFE for b in text)


def coded_card_texts(retail_files, modded_files) -> dict:
    """{field: card ids} of the names and texts that only a text listing can
    carry: changed ones with a color or icon code in them, and texts the
    mod left empty (cards.c reads "" as "not set")."""
    from .gamedata import _tl
    image, retail_image = g._image(modded_files.slus), g._image(retail_files.slus)
    out = {"name": set(), "description": set()}
    for cid in range(1, g.CARD_COUNT + 1):
        name = g.text_bytes(image, g.NAME_BANK + image.u16(g.NAME_TABLE + cid * 2), 128)
        old = g.text_bytes(retail_image, g.NAME_BANK + retail_image.u16(g.NAME_TABLE + cid * 2), 128)
        if name != old and _has_codes(name):
            out["name"].add(cid)
    texts, old_texts = g.description_bytes(modded_files.slus, modded_files.wa), g.description_bytes(retail_files.slus)
    for cid, text in texts.items():
        if text != old_texts[cid] and (_has_codes(text) or text == b"\xFF"):
            out["description"].add(cid)
    return out


def decode_drop_pools(retail, modded, retail_files, modded_files) -> list:
    """Decode the modded drop pools in place when the mod stores them
    encoded (DRAW_ADD); report lines saying which reading was used."""
    changed = [(d, p) for d in range(len(modded.pools)) for p in DROP_POOLS
               if modded.pools[d][p] != retail.pools[d][p]]
    if not changed:
        return []
    found = draw_code_encoding(retail_files.slus, modded_files.slus)
    where = f"the draw at 0x{DRAW_ADD:08X} jumps to the mod's code at 0x{found[2]:08X}" if found else ""
    extra = kit.extra_draws(retail_files.slus, modded_files.slus)
    if not found and extra and extra.encoding:
        found = extra.encoding
        where = (f"the prize draw at 0x{kit.RESULT_DRAW:08X} jumps to the mod's code at 0x{extra.code:08X}, which "
                 f"calls 0x{found[2]:08X}")
    notes = []
    if found:
        bias, shift, code = found
        decode = changed
        notes.append(f"pools: the drop pools are encoded: {where}, which reads each weight as max(0, (raw - {bias}) >> "
                     f"{shift}); the {len(decode)} changed drop pools were decoded that way (the deck pools are not "
                     "encoded)")
        kept = [f"{g.DUELIST_NAMES[d]} {p}" for d in range(len(modded.pools)) for p in DROP_POOLS
                if (d, p) not in changed]
        if kept:
            notes.append(f"pools: {len(kept)} drop pools are as retail wrote them (for example {'; '.join(kept[:3])})"
                         "; kept as retail, although the mod's draw would read them encoded")
    else:
        decode = [(d, p) for d, p in changed if sum(modded.pools[d][p].values()) != g.POOL_TOTAL]
        guess = guess_encoding([_raw_pool(modded_files.wa, d, p) for d, p in decode])
        if not guess:
            return []
        bias, shift = guess
        notes.append(f"pools: {len(decode)} changed drop pools do not add up to 2048 but do once each weight is read "
                     f"as max(0, (raw - {bias}) >> {shift}), the way the TeaOnline drop tool encodes them; the "
                     f"mod's draw code at 0x{DRAW_ADD:08X} was not recognized, so they were decoded that way")
    for d, p in decode:
        modded.pools[d][p] = decode_weights(_raw_pool(modded_files.wa, d, p), bias, shift)
    return notes


def _names(project: Project, ids, most: int = 8) -> str:
    ids = sorted(ids)
    shown = ", ".join(project.card_label(i) if i in project.cards else str(i) for i in ids[:most])
    return shown + (f" and {len(ids) - most} more" if len(ids) > most else "")


def read_equip_bitmaps(project: Project, modded, retail_files, modded_files) -> list:
    """The equips when the mod's Duel_CheckEquip reads a bitmap per equip
    (kit.equip_bitmaps): every equip card's monsters as the mod's code
    decides. Records of cards the port's equips cannot take are reported."""
    table = kit.equip_bitmaps(retail_files.slus, modded_files.slus, modded_files.wa)
    if table is None:
        return []
    cards = modded.cards
    monsters = {cid for cid, card in cards.items() if card.is_monster()}
    equips = {cid for cid, card in cards.items() if card.type == g.TYPE_EQUIP}
    project.equips = {e: table.allowed(e) & monsters for e in equips}
    project.equips = {e: m for e, m in project.equips.items() if m or e in project.retail.equips}
    for e, m in project.retail.equips.items():
        if e not in equips:         # no longer an equip card in the mod: nothing to say about it
            project.equips[e] = set(m)
    notes = [f"equips: the mod's {table.where} reads its table as bitmaps of {kit.EQUIP_RECORD} bytes per card "
             f"({len(table.records)} records{'' if table.limit is None else f', {table.limit} read'}); every "
             "equip card's monsters were read that way"]
    others = [key for key, _ in table.records if key not in equips]
    if others:
        notes.append(f"equips: {len(others)} records are for cards that are not equip cards ({_names(project, others)}): "
                     "monsters or magic used as equips (\"Union\"); the port's equips take equip cards only "
                     "(src/pc/cards/tables.c: \"not an equip card\"), so they are not imported")
    if table.by_monster:
        notes.append(f"equips: {len(table.by_monster)} records name a monster and the equips it takes "
                     f"({_names(project, [m for m, _ in table.by_monster])}); those equips' lists include it")
    if table.blocked:
        notes.append(f"equips: no equip equips {_names(project, table.blocked)}, as the mod's code decides")
    return notes


def check_rituals(project: Project, modded) -> list:
    """No rituals when the ritual table holds no recipe the game could
    read: the kit keeps code there and takes the rituals away. A record's
    key is not required to be a Ritual-type card: the stock lookup
    (table801a7ad8_recipe_lookup) matches it against whatever card
    triggered it and never checks that card's type, so a mod is free to
    key a recipe on a monster card instead of a spell."""
    cards = modded.cards
    valid = {r: rec for r, rec in project.rituals.items()
             if r in cards and all(1 <= c <= g.CARD_COUNT for c in rec)}
    bad = len(project.rituals) - len(valid)
    if bad and len(valid) * 2 < len(project.rituals):
        valid = {}      # mostly not recipes: the few that look like one are the code's bytes by chance
    # A retail ritual the mod made another kind of card: nothing to say (the
    # port refuses a rituals entry for a card that is not a ritual).
    other = {r: rec for r, rec in project.retail.rituals.items()
             if r not in valid and cards.get(r) and cards[r].type != g.TYPE_RITUAL}
    project.rituals = {**valid, **other}
    notes = [f"rituals: {len(other)} retail ritual cards are other cards in the mod; no rule names them"] if other else []
    if not bad:
        return notes
    if valid:
        return notes + [f"rituals: {bad} records of the modified ritual table name no ritual card or no card at all; "
                        "left out"]
    return notes + [f"rituals: the modified ritual table holds no recipe ({bad} records naming no ritual card or no "
                    "card: code, or another format); the rituals were imported as removed, as the game finds none there"]


TYPE_NAME_INDEX = 0x300         # the names bank: 0x300 + type id, type 0 (Dragon) is string 0x8300


def type_names_from_slus(slus: bytes) -> dict:
    """{type: name} for the 24 retail type slots, as the names bank has
    them. Past type 23 the bank holds the star strings (cardsdata README:
    "768..791 types, 792..801 stars"), so nothing past 23 is read -- a card
    wearing one of those ids has no name of its own to recover here."""
    from .gamedata import _tl
    try:
        image = g._image(slus)
        glyphs = _tl.glyph_characters(image)
    except Exception:
        return {}
    out = {}
    for type_ in range(len(g.TYPE_NAMES)):
        at = g.NAME_BANK + image.u16(_tl.NAME_TABLE + (TYPE_NAME_INDEX + type_) * 2)
        text, jumps = "", 0
        try:
            while len(text) < 24:
                code = image.bytes(at, 1)[0]
                # As community mods write them (gamedata.plain_names): a
                # colour/icon escape (F8 0A/0B NN) is skipped rather than
                # read as a glyph or mistaken for the 0xF0+ terminator.
                if code == 0xF8:
                    at += 3 if image.bytes(at + 1, 1)[0] in (0x0A, 0x0B) else 2
                    continue
                if code == 0xFD and jumps < 8:
                    at = g.NAME_BANK + int.from_bytes(image.bytes(at + 1, 2), "little")
                    jumps += 1
                    continue
                if code >= 0xF0:
                    break
                text += glyphs.get(code, "?")
                at += 1
        except Exception:
            return {}
        out[type_] = text.strip()
    return out


def import_card_types(project: Project, retail_slus: bytes, modded_slus: bytes, modded_wa: bytes,
                      report: list) -> list:
    """A retail type the executable renamed becomes a new custom declaration
    rather than a rewrite of the retail slot.

    The disc has one name per id: it cannot keep "Sea Serpent" for anyone who
    still expects retail's 13 to mean that and also show a mod's "Psychic"
    there. In the modded game every card at that id now reads "Psychic", so
    that is what they are; retail's 13 is left alone (unused by this mod)
    and the mod's name gets an id of its own, with the cards that wore the
    retail id moved to it. TeaTools' own tools (cardsdata) only repack the
    24 retail type-name strings -- there is no registry for a name past
    those 24, so nothing here is invented for an id with no string of its
    own (cardsdata's accepted 0-63 just writes the raw id).

    The new declaration's icon, where one can be read, is the retail slot's
    own card-text glyph (card_text.RetailFont): cardsdata only ever rewrites
    the name string, never that glyph bitmap, so the picture at "Sea
    Serpent"'s old position is still exactly what it was -- a real starting
    icon for "Psychic" to keep or replace, not a guess from its numeric id."""
    was, now = type_names_from_slus(retail_slus), type_names_from_slus(modded_slus)
    if not was or not now:
        report.append("card_types: the executable's type names could not be read; any renamed type is left out")
        return []
    renamed = {type_: now[type_] for type_ in sorted(now) if now[type_] and now[type_] != was.get(type_)}
    if not renamed:
        return []
    from . import card_text
    try:
        font = card_text.RetailFont(modded_wa)
    except (ValueError, OSError, struct.error):
        font = None
    mapping, entries, skipped, icons_found = {}, [], [], 0
    next_id = len(g.TYPE_NAMES)
    for old in sorted(renamed):
        new_name = renamed[old]
        while next_id < g.TYPE_LIMIT and project.type_names[next_id]:
            next_id += 1
        if next_id >= g.TYPE_LIMIT:
            skipped.append(new_name)
            continue
        declaration = {"id": next_id, "name": new_name}
        icon_path = None
        if font is not None:
            try:
                found = font.icon(card_text.ICON_NAMES.index(g.TYPE_NAMES[old]))
            except ValueError:
                found = None
            if found is not None:
                icon_path = f"icons/type-{next_id}.png"
                project.files[icon_path] = pngio.encode(pngio.Image(*found))
                declaration["icon"] = icon_path
        messages = []
        manifest.read_card_types(project, {"types": [declaration]}, messages)
        if messages:
            skipped.append(new_name)
            if icon_path:
                project.files.pop(icon_path, None)
            continue
        mapping[old] = next_id
        if icon_path:
            icons_found += 1
        entries.append(f'{was.get(old, old)} (id {old}) → "{new_name}" (new id {next_id})')
        next_id += 1
    if mapping:
        moved = sum(1 for card in project.cards.values() if card.type in mapping)
        for card in project.cards.values():
            if card.type in mapping:
                card.type = mapping[card.type]
        shown = ", ".join(entries[:3])
        report.append(f"card_types: {len(mapping)} retail type(s) renamed in the executable "
                      f"({shown}{', ...' if len(entries) > 3 else ''}) became new custom types rather than "
                      f"replacing the retail one, since the disc has no room for both names at the same id; "
                      f"{moved} card(s) using the old id moved to the new one"
                      + (f"; {icons_found} kept the retail slot's own icon" if icons_found else ""))
    if skipped:
        report.append(f"card_types: {len(skipped)} renamed type(s) could not be declared as new custom types "
                      f"({', '.join(skipped[:3])}); left as retail")
    return []


def report_unresolved_type_and_attribute_ids(project: Project, report: list):
    """Cards wearing a custom type or attribute id the import could not name
    -- past the 24 types and 6 attributes the disc's own names bank covers,
    TeaTools' cardsdata writes the raw id (0-63 for type, 0-15 for
    attribute) with nothing recoverable past it; this just says so, rather
    than inventing a name import_card_types had no string to base one on."""
    custom_types = sorted({card.type for card in project.cards.values()
                           if len(g.TYPE_NAMES) <= card.type < g.TYPE_LIMIT and not project.type_names[card.type]})
    if custom_types:
        report.append(f"card_types: {len(custom_types)} custom type id(s) in use with no name of their own "
                      f"({', '.join(str(t) for t in custom_types[:6])}{', ...' if len(custom_types) > 6 else ''}); "
                      "name them on the Types & Attributes page. TeaTools' own cardsdata tool accepts ids up to 63, "
                      "but the original game masks a card's type to 5 bits in places, so an id of 32 or more may not "
                      "play consistently on the original disc even though this port reads it exactly")
    custom_attributes = sorted({card.attribute for card in project.cards.values() if 8 <= card.attribute <= 255})
    if custom_attributes:
        report.append(f"attributes: {len(custom_attributes)} custom attribute id(s) in use with no name of their "
                      f"own ({', '.join(str(a) for a in custom_attributes[:6])}"
                      f"{', ...' if len(custom_attributes) > 6 else ''}); TeaTools has no attribute-naming tool to "
                      "recover one from, so name them on the Types & Attributes page")


DUELIST_NAME_INDEX = 0x328      # the names bank: 0x328 + id (translation.c TEXT_DUELIST_NAMES)


def duelist_names(slus: bytes) -> dict:
    """{id: name} as the executable's names bank has them, or {} when it
    cannot be read. The port keeps its own table of these (tables.c
    Tables_DuelistNames) and never reads the disc's, so a modified name
    reaches the game only as a "duelists" entry."""
    from .gamedata import _tl
    try:
        image = g._image(slus)
        glyphs = _tl.glyph_characters(image)
    except Exception:
        return {}
    out = {}
    for duelist in range(1, g.DUELIST_COUNT):
        at = 0x801D0000 + image.u16(_tl.NAME_TABLE + (DUELIST_NAME_INDEX + duelist) * 2)
        text = ""
        try:
            while len(text) < 32:
                code = image.bytes(at, 1)[0]
                if code >= 0xF0:
                    break
                text += glyphs.get(code, "?")
                at += 1
        except Exception:
            return {}
        out[duelist] = text.strip()
    return out


def renamed_duelists(project: Project, retail_slus: bytes, modded_slus: bytes, report: list) -> list:
    """A "duelists" entry for each of the disc's own the mod renamed."""
    was, now = duelist_names(retail_slus), duelist_names(modded_slus)
    if not was or not now:
        report.append("duelists: the executable's names could not be read; any renamed duelist is left out")
        return []
    entries = []
    for duelist, name in sorted(now.items()):
        if not name or name == was.get(duelist):
            continue
        entries.append({"id": slug(name) or f"duelist-{duelist}",
                        "replace": g.DUELIST_NAMES[duelist], "name": name})
    if entries:
        project.other["duelists"] = entries
        shown = ", ".join(f"{e['replace']} \u2192 {e['name']}" for e in entries[:3])
        report.append(f"duelists: {len(entries)} renamed ({shown}{', ...' if len(entries) > 3 else ''}); the port "
                      "keeps its own names (tables.c Tables_DuelistNames) and never reads the disc's, so they are "
                      "carried as \"duelists\" entries rather than as bytes of the executable")
    return entries


def art_regions(cid: int) -> dict:
    """Where each of a card's three pictures is stored in WA_MRG.MRG."""
    base = art.record_base(cid)
    small = (cid - 1) * art.SECTOR
    return {"art": (base, base + art.TITLE_PIXELS),
            "title": (base + art.TITLE_PIXELS, base + art.ART_SECTORS * art.SECTOR),
            "thumbnail": (small, small + art.THUMB_CLUT + 2 * 64)}


def recognisable_card_art(retail_wa: bytes, modded_wa: bytes, cid: int, part: str) -> bool:
    """Whether a changed picture looks like a picture replacement.

    Every byte in an indexed picture can be decoded, including a normal code
    or data patch that happens to fall in its sectors.  Preserve small edits
    and large, nearly uniform runs as archive data: a real replacement has a
    substantial range of palette indices, while those changes are otherwise
    indistinguishable from a PNG to ``disc_image``.
    """
    start, _ = art_regions(cid)[part]
    if part == "title":
        length = 48 * art.SIZES[part][1]
        changed = [new for old, new in zip(retail_wa[start:start + length], modded_wa[start:start + length])
                   if old != new]
        # Plates have two four-bit inks per byte; values above 7 cannot be
        # drawn by the game as a plate.
        return len(changed) >= 64 and all((byte & 0x0F) < 8 and byte >> 4 < 8 for byte in changed)

    width, height = art.SIZES[part]
    length = width * height
    changed = [new for old, new in zip(retail_wa[start:start + length], modded_wa[start:start + length])
               if old != new]
    return len(changed) >= 128 and len(set(changed)) > 2


def recognisable_portrait(retail_wa: bytes, modded_wa: bytes, duelist: int) -> bool:
    """Whether a changed portrait record looks like a replaced face.

    The same question ``recognisable_card_art`` asks: every byte of an
    indexed picture decodes, a patch that happens to land in the portraits
    included, so a real replacement is told by how much of it changed and
    how many palette indices it uses."""
    at = art.portrait_at(duelist)
    changed = [new for old, new in zip(retail_wa[at:at + art.PORTRAIT_PIXELS],
                                       modded_wa[at:at + art.PORTRAIT_PIXELS]) if old != new]
    if len(changed) >= 128 and len(set(changed)) > 2:
        return True
    # A face recoloured rather than redrawn keeps the disc's pixels and gives
    # them its own colours; a patch that lands in the palette touches one or
    # two words of it, not a good part of it.
    clut = at + art.PORTRAIT_PIXELS
    colours = sum(1 for i in range(art.PORTRAIT_COLOURS)
                  if retail_wa[clut + 2 * i:clut + 2 * i + 2] != modded_wa[clut + 2 * i:clut + 2 * i + 2])
    return colours >= 8


def import_duelist_portraits(project: Project, retail_wa: bytes, modded_wa: bytes, report: list) -> list:
    """The Free Duel faces a mod changed, as PNGs on its duelists' entries.

    The port never reads the disc's record for a duelist a mod gave a face
    (free_duel/duelists.c): a "duelists" entry's "portrait" names a PNG, which
    it reduces to the console's 48x48 slot and also draws whole for the scaled
    picture. Carried that way the picture is the mod's own -- the editor shows
    it on the duelist's tile and it can be replaced again -- rather than bytes
    of the archive nothing but the game can read.

    Returns the byte ranges now carried as PNGs, for the caller to keep out of
    the "data" diff."""
    entries = project.other.get("duelists")
    entries = list(entries) if isinstance(entries, list) else []
    by_slot = {}
    for entry in entries:
        if isinstance(entry, dict) and "replace" in entry:
            found = duelist_named(entry["replace"])
            if 0 < found < art.PORTRAIT_COUNT:
                by_slot[found] = entry
    kept, written, unreadable, deck_build = [], [], [], False
    # Deck Build's own record (0) is no opponent's face: there is no entry to
    # put it on, so it stays as bytes.
    for duelist in range(art.PORTRAIT_COUNT):
        at = art.portrait_at(duelist)
        end = at + art.PORTRAIT_STRIDE
        if end > len(modded_wa) or retail_wa[at:end] == modded_wa[at:end]:
            continue
        if not recognisable_portrait(retail_wa, modded_wa, duelist):
            continue
        if duelist == 0:
            deck_build = True
            continue
        name = g.DUELIST_NAMES[duelist]
        try:
            picture = pngio.encode(art.portrait_image(modded_wa, duelist))
        except (ValueError, OSError, IndexError, pngio.PngError) as problem:
            unreadable.append(f"{name} ({problem})")
            continue
        entry = by_slot.get(duelist)
        if entry is None:
            entry = {"id": slug(name) or f"duelist-{duelist}", "replace": name}
            entries.append(entry)
            by_slot[duelist] = entry
        relative = f"portraits/{entry.get('id') or f'duelist-{duelist}'}.png"
        project.files[relative] = picture
        entry["portrait"] = relative
        written.append(name)
        kept.append((at, end))
    if written:
        project.other["duelists"] = entries
        shown = ", ".join(written[:3])
        report.append(f"portraits: {len(written)} Free Duel portrait(s) read out of WA_MRG.MRG as the mod's own PNGs "
                      f"({shown}{', ...' if len(written) > 3 else ''}), so the editor shows them and they can be "
                      "replaced again")
    if unreadable:
        report.append(f"portraits: {len(unreadable)} could not be read and stay as bytes of WA_MRG.MRG "
                      f"({'; '.join(unreadable[:3])}{', ...' if len(unreadable) > 3 else ''})")
    if deck_build:
        report.append("portraits: the Free Duel screen's Deck Build picture changed; it belongs to no duelist, so it "
                      "stays as bytes of WA_MRG.MRG")
    return kept


def import_card_art(project: Project, retail_wa: bytes, modded_wa: bytes, report: list, say=None) -> list:
    """The pictures a mod changed, as PNGs of its own rather than as bytes.

    A picture carried as a "data" patch reaches the game but nothing else: it
    is seven sectors against a budget of sixteen runs, the editor draws the
    disc's instead of it, and it cannot be edited again. Read out as a PNG it
    is the mod's own art, which the editor shows and the port draws through
    the same path as any other replacement.

    Returns the byte ranges now carried as PNGs, for the caller to keep out of
    the "data" diff."""
    kept, counted = [], {part: 0 for part in art.PARTS}
    unreadable = []
    for cid in range(1, g.CARD_COUNT + 1):
        if say is not None and not cid % 50:
            say(f"Pictures ({cid} of {g.CARD_COUNT})")
        where = art_regions(cid)
        for part in art.PARTS:
            start, end = where[part]
            if end > len(modded_wa) or retail_wa[start:end] == modded_wa[start:end]:
                continue
            if not recognisable_card_art(retail_wa, modded_wa, cid, part):
                continue
            try:
                image = art.disc_image(modded_wa, cid, part)
                art.set_image(project, cid, part, image)
            except (ValueError, OSError, IndexError, pngio.PngError) as problem:
                unreadable.append(f"{project.card_label(cid)} {art.LABELS[part].lower()} ({problem})")
                continue
            counted[part] += 1
            kept.append((start, end))
    said = ", ".join(f"{counted[part]} {art.LABELS[part].lower()}" for part in art.PARTS if counted[part])
    if said:
        report.append(f"art: {said} read out of WA_MRG.MRG as the mod's own PNGs, so the editor shows them and "
                      "they can be edited again")
    if unreadable:
        report.append(f"art: {len(unreadable)} pictures could not be read and stay as bytes of WA_MRG.MRG "
                      f"({'; '.join(unreadable[:3])}{', ...' if len(unreadable) > 3 else ''})")
    return kept


STAR_NAME_INDEX = 0x317         # the names bank: Mars (star 1) is 0x318, Venus (10) is 0x321
GUARDIAN_MATCHUP = 0x8002CB80


def guardian_star_masks(slus: bytes):
    """The 16-star routine used by TeaOnline-style community patches.

    It replaces ``Duel_CalcGuardianStarMatchup`` with two directional tests
    against sixteen u16 masks.  The table address is deliberately read from
    the patch rather than fixed: authors commonly put its data in a nearby
    free area of the executable.  Unknown code remains unknown; importing
    arbitrary replacement routines as a matchup table would invent rules.
    """
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
    if any(expected is not None and word != expected for word, expected in zip(words, fixed)) or \
            words[2] >> 16 != 0x3C02 or words[3] >> 16 != 0x2442:
        return None
    base = ((words[2] & 0xFFFF) << 16) + struct.unpack("<h", struct.pack("<H", words[3] & 0xFFFF))[0]
    table = g.slus_offset(base)
    if table < 0 or table + 32 > len(slus):
        return None
    return list(struct.unpack_from("<16H", slus, table)), [(at, at + 116), (table, table + 32)]


def star_names(slus: bytes) -> dict:
    """{star: name} as the names bank has them.

    Past Venus the disc keeps its own strings at those places, so a name
    there is only a name when it differs from retail's -- which is how a mod
    that adds stars writes them (TLM's eleventh, twelfth and thirteenth are
    Fortuna, Transpluto and Ceres where the disc has "Dragon")."""
    from .gamedata import _tl
    try:
        image = g._image(slus)
        glyphs = _tl.glyph_characters(image)
    except Exception:
        return {}
    out = {}
    for star in range(1, guardian_stars.MAX_STARS + 1):
        at = 0x801D0000 + image.u16(_tl.NAME_TABLE + (STAR_NAME_INDEX + star) * 2)
        text = ""
        try:
            while len(text) < 24:
                code = image.bytes(at, 1)[0]
                if code >= 0xF0:
                    break
                text += glyphs.get(code, "?")
                at += 1
        except Exception:
            return {}
        out[star] = text.strip()
    return out


def import_guardian_stars(project: Project, retail, modded, retail_slus: bytes, modded_slus: bytes,
                          modded_wa: bytes, report: list) -> list:
    """The stars the modified game has: the disc's ten where it renamed them,
    and any past them its cards use.

    A star past the disc's ten has nowhere to live on the disc -- the names
    bank holds the disc's own strings at those places (stars.c: "a new star
    with no name: its number, not the disc's Dragon that the names bank has at
    its place") -- so the only sure sign of one is a card wearing it: the stat
    word keeps each star in four bits, and the port takes ids up to 15."""
    was, now = star_names(retail_slus), star_names(modded_slus)
    named = {star: now[star] for star in sorted(now) if now[star] and now[star] != was.get(star)}
    worn = sorted({value for card in modded.cards.values() for value in (card.star1, card.star2)
                   if value > guardian_stars.RETAIL_COUNT})
    entries, renamed, bare = [], [], []
    for star in sorted(set(named) | set(worn)):
        entry = {"id": star}
        if star in named:
            entry["name"] = named[star]
            if star <= guardian_stars.RETAIL_COUNT:
                renamed.append(f"{was.get(star, star)} \u2192 {named[star]}")
        elif star > guardian_stars.RETAIL_COUNT:
            bare.append(star)
        entries.append(entry)
    masks = guardian_star_masks(modded_slus)
    if not entries and masks is None:
        return []
    section = project.other.get("guardian_stars")
    section = dict(section) if isinstance(section, dict) else {}
    section["stars"] = entries
    if masks is not None:
        table, handled = masks
        matchups = []
        for attacker in range(1, guardian_stars.MAX_STARS + 1):
            for defender in range(1, guardian_stars.MAX_STARS + 1):
                if attacker == defender or table[defender - 1] & (1 << (attacker - 1)):
                    bonus = -guardian_stars.RETAIL_BONUS
                elif table[attacker - 1] & (1 << (defender - 1)):
                    bonus = guardian_stars.RETAIL_BONUS
                else:
                    bonus = 0
                if bonus != guardian_stars.retail_matchup(attacker, defender):
                    matchups.append({"attacker": attacker, "defender": defender, "bonus": bonus})
        section["matchups"] = matchups
        for entry in entries:
            if entry["id"] <= guardian_stars.RETAIL_COUNT:
                continue
            found = guardian_stars.imported_icon(modded_wa, entry["id"])
            if found is None:
                continue
            path = f"icons/star-{entry['id']}.png"
            project.files[path] = pngio.encode(pngio.Image(*found))
            entry["icon"] = path
        report.append(f"guardian stars: imported the 16-star matchup table ({len(matchups)} changed pairs)"
                      + (" and custom icons" if any("icon" in entry for entry in entries) else ""))
    else:
        handled = []
    project.other["guardian_stars"] = section
    if renamed:
        report.append(f"guardian stars: {len(renamed)} renamed ({', '.join(renamed[:3])}"
                      f"{', ...' if len(renamed) > 3 else ''})")
    past = [e for e in entries if e["id"] > guardian_stars.RETAIL_COUNT]
    if past:
        said = ", ".join(f"{e['id']} {e.get('name', '(unnamed)')}" for e in past)
        report.append(f"guardian stars: {len(past)} past the disc's ten ({said}), found by the names the mod "
                      "wrote past Venus and by the cards wearing them. "
                      + ("Their matchups were read from the mod's 16-star table." if masks is not None else
                         "What each beats is in the mod's own code, which the port runs none of, so every battle "
                         "with one is neutral until the Guardian Stars page says otherwise"))
    if bare:
        report.append(f"guardian stars: {len(bare)} of them have no name of their own "
                      f"({', '.join(str(s) for s in bare)}); the editor calls them \"Star n\"")
    return handled


def _starter_rows(wa: bytes) -> list:
    """The disc's seven starter rows as (draws, {card: weight})."""
    stride = g.STARTER_LENGTH // 7
    rows = []
    for index in range(7):
        at = g.STARTER_BASE + index * stride
        draws = struct.unpack_from("<H", wa, at)[0]
        weights = struct.unpack_from(f"<{starter_pools.RETAIL_SCAN}H", wa, at + 2)
        rows.append((draws, {cid: weight for cid, weight in enumerate(weights, 1) if weight}))
    return rows


def import_starter_table(project: Project, retail_wa: bytes, modded_wa: bytes, report: list) -> list:
    """Carry the disc's starter table in the port's equivalent form.

    Retail's seven rows are weighted pools. Community mods sometimes replace
    every row with forty card counts instead; the editor's written starter
    decks represent that form directly.
    """
    start, end = g.STARTER_BASE, g.STARTER_BASE + g.STARTER_LENGTH
    if end > len(modded_wa) or retail_wa[start:end] == modded_wa[start:end]:
        return []
    rows = _starter_rows(modded_wa)
    totals = [sum(cards.values()) for _, cards in rows]
    draws = [count for count, _ in rows]
    if sum(draws) == starter_pools.DRAWS and all(total == g.POOL_TOTAL for total in totals):
        project.other["starter_pools"] = [
            {"name": starter_pools.RETAIL_NAMES[index], "draws": count,
             "cards": {str(cid): weight for cid, weight in cards.items()}}
            for index, (count, cards) in enumerate(rows)]
        project.starter_pool_state = None
        report.append("starter decks: imported seven weighted starter pools")
        return [(start, end)]
    if all(total == starter_pools.DRAWS for total in totals):
        project.starter = [StarterDeck(name=f"Deck {index + 1}", cards=cards)
                           for index, (_, cards) in enumerate(rows)]
        report.append("starter decks: imported seven written 40-card decks")
        return [(start, end)]
    return []


def _starter_counts(wa: bytes) -> list:
    """Each of the seven starter rows as (weight, {card id: copies}), or
    None when its own total is not a plausible deck (0 to forty, no single
    card past forty): a kit's counted-deck table in place of the disc's
    weighted pools (the "starter" manifest key, notes/starter-deck.md)."""
    stride = g.STARTER_LENGTH // 7
    out = []
    for k in range(7):
        base = g.STARTER_BASE + k * stride
        weight = struct.unpack_from("<H", wa, base)[0]
        values = struct.unpack_from("<%dH" % g.CARD_COUNT, wa, base + 2)
        total = sum(values)
        if not 0 < total <= kit.DECK_SIZE or any(v > kit.DECK_SIZE for v in values):
            out.append(None)
            continue
        out.append((weight, {cid: count for cid, count in enumerate(values, 1) if count}))
    return out


def port_wa(retail_wa: bytes, modded_wa: bytes, keep_retail) -> bytes:
    """The modified archive with `keep_retail` ([start, end) regions: the
    tables mod.json carries, and what the port cannot read the mod's way)
    put back to the retail bytes."""
    out = bytearray(modded_wa)
    for start, end in keep_retail:
        end = min(end, len(retail_wa), len(out))
        if start < end:
            out[start:end] = retail_wa[start:end]
    return bytes(out)


def preview_archive(project: Project, retail_wa: bytes, wa_lba: int) -> bytes:
    """Return the archive as an imported mod makes the game read it.

    An imported BIN keeps unstructured graphics as ``data`` patches and raw
    sector replacements.  The game applies those entries at load time, but a
    newly opened editor project otherwise only has the retail ``WA_MRG.MRG``
    in memory.  Replaying the entries here makes editor previews show the
    same card frames, UI sheets, and other imported graphics after Save and
    Open as they did immediately after the BIN import.

    This is deliberately preview-only: structured tables remain represented
    by the normal Project model and are not copied back into the archive.
    Invalid or unrelated ``data`` entries are ignored just as the preview
    ignores assets it cannot render.
    """
    data = project.other.get("data")
    if not isinstance(data, list) or not retail_wa:
        return retail_wa

    def blob(path):
        if not isinstance(path, str):
            return None
        value = project.files.get(path)
        if isinstance(value, bytes):
            return value
        folder = getattr(project, "source_dir", None)
        if folder is None:
            return None
        try:
            target = art.safe_target(Path(folder), path)
            return target.read_bytes() if target is not None and target.is_file() else None
        except OSError:
            return None

    def number(value):
        try:
            return int(value, 0) if isinstance(value, str) else int(value)
        except (TypeError, ValueError):
            return None

    def is_archive(value):
        return isinstance(value, str) and value.replace("/", "\\").upper().lstrip("\\") in \
            ("DATA\\WA_MRG.MRG;1", "DATA\\WA_MRG.MRG")

    out = bytearray(retail_wa)
    for entry in data:
        if not isinstance(entry, dict):
            continue
        replacement = blob(entry.get("replace"))
        if replacement is not None and is_archive(entry.get("file")):
            # A named full-file replacement.  Keep the retail tail where a
            # malformed replacement is short, matching the port's sector
            # fallback rather than making the preview unreadable.
            out[:min(len(out), len(replacement))] = replacement[:len(out)]
        lba, sectors = number(entry.get("lba")), number(entry.get("sectors"))
        if replacement is not None and lba is not None and sectors and sectors > 0:
            start = (lba - wa_lba) * SECTOR
            size = sectors * SECTOR
            if start < len(out) and start + size > 0:
                source_start = max(0, -start)
                target_start = max(0, start)
                count = min(size - source_start, len(replacement) - source_start, len(out) - target_start)
                if count > 0:
                    out[target_start:target_start + count] = replacement[source_start:source_start + count]
        if not is_archive(entry.get("file")) or not isinstance(entry.get("patch"), list):
            continue
        for patch in entry["patch"]:
            if not isinstance(patch, dict):
                continue
            at = number(patch.get("at"))
            text = patch.get("bytes")
            if at is None or not isinstance(text, str):
                continue
            try:
                changed = bytes.fromhex("".join(text.split()))
            except ValueError:
                continue
            if at < len(out) and at + len(changed) > 0:
                source_start = max(0, -at)
                target_start = max(0, at)
                count = min(len(changed) - source_start, len(out) - target_start)
                if count > 0:
                    out[target_start:target_start + count] = changed[source_start:source_start + count]
    return bytes(out)


def wa_data(project: Project, retail_files, modded_files, report: list, carried=()) -> list:
    """The "data" entries that carry the rest of WA_MRG.MRG: patches and
    sector replacements at the retail disc's sectors when they are few, the
    whole file otherwise. Either way the structured tables (mod.json's
    fusions, equips, rituals and pools) stay retail's, so the port's rules
    apply over the disc's own tables."""
    wa_old, wa_new = retail_files.wa, modded_files.wa
    # The structured tables mod.json carries, and the pictures its PNGs do.
    keep = wa_structured_regions() + list(carried) + list(IGNORED_WA_IMPORT_RANGES)
    starters = [sum(cards.values()) for _, cards in _starter_rows(wa_new)] \
        if len(wa_new) >= g.STARTER_BASE + g.STARTER_LENGTH else []
    starter_range = (g.STARTER_BASE, g.STARTER_BASE + g.STARTER_LENGTH)
    if starter_range not in keep and starters and min(starters) < g.POOL_TOTAL // 2 and wa_new[g.STARTER_BASE:g.STARTER_BASE + g.STARTER_LENGTH] != \
            wa_old[g.STARTER_BASE:g.STARTER_BASE + g.STARTER_LENGTH]:
        keep.append((g.STARTER_BASE, g.STARTER_BASE + g.STARTER_LENGTH))
        rows, unreadable, added = _starter_counts(wa_new), 0, []
        for row in rows:
            if row is None:
                unreadable += 1
                continue
            weight, cards = row
            deck = StarterDeck(weight=weight, cards=cards)
            project.starter.append(deck)
            added.append(deck)
        complete = sum(1 for d in added if d.complete())
        report.append(f"WA_MRG.MRG: the starter decks are counts of cards (they add up to {', '.join(map(str, starters))}"
                      f"), not weights of 2048; written as {len(added)} starter decks ({complete} of forty cards "
                      "each)" + (f", {unreadable} unreadable" if unreadable else ""))
    for sector, sectors, what in g.PROGRAMS:
        start, end = sector * 2048, (sector + sectors) * 2048
        changed = sum(1 for a, b in zip(wa_old[start:end], wa_new[start:end]) if a != b)
        if changed:
            keep.append((start, end))
            report.append(f"WA_MRG.MRG: {what} (sector {sector}) differs in {changed} bytes: the mod's own code and "
                          "data there; the port runs its own code for that program over its data, so it stays "
                          "retail's")
    runs = _trim(wa_old, wa_new, _subtract(_runs(wa_old, wa_new, 0, min(len(wa_old), len(wa_new))), keep))
    patches, regions, places = [], [], {}
    for start, end in runs:
        count, runs_there = places.get(describe_wa(start), (0, 0))
        places[describe_wa(start)] = (count + end - start, runs_there + 1)
        if end - start <= PATCH_LIMIT:
            patches.append((start, end))
            continue
        first, last = start // 2048, (end + 2047) // 2048
        if regions and first <= regions[-1][1]:
            regions[-1][1] = max(last, regions[-1][1])
        else:
            regions.append([first, last])
    whole = None
    if len(wa_new) != len(wa_old):
        whole = f"its size differs ({len(wa_new)} bytes, retail {len(wa_old)})"
    elif len(patches) > WA_PATCHES_MOST or len(regions) > WA_REGIONS_MOST:
        whole = (f"{len(patches)} patches and {len(regions)} sector runs would be more than this mod's share of what "
                 f"the port holds for every mod together ({WA_PATCHES_MOST} and {WA_REGIONS_MOST} of 65536 and 4096, "
                 "src/pc/mods/mods.c PATCHES_MAX and REGIONS_MAX)")
    if whole:
        project.files["WA_MRG.MRG"] = port_wa(wa_old, wa_new, keep)
        report.append(f"WA_MRG.MRG: {whole}; the whole file is replaced, with the tables mod.json carries kept as "
                      "retail's")
        data = [{"file": WA_FILE, "replace": "WA_MRG.MRG"}]
    else:
        data = [{"file": WA_FILE, "patch": [{"at": f"0x{s:X}", "bytes": wa_new[s:e].hex(" ").upper()}
                                            for s, e in patches]}] if patches else []
        clean = None
        for first, last in regions:
            path = f"data/wa_{first:05X}.bin"
            if any(s < last * 2048 and e > first * 2048 for s, e in keep):
                clean = clean or port_wa(wa_old, wa_new, keep)
                project.files[path] = clean[first * 2048:last * 2048]
            else:
                project.files[path] = wa_new[first * 2048:last * 2048]
            # "lba" is a sector of the disc the port runs, the retail one.
            data.append({"lba": retail_files.wa_lba + first, "sectors": last - first, "replace": path})
    for place, (count, runs_there) in sorted(places.items()):
        report.append(f"WA_MRG.MRG: {place}: {count} bytes in {runs_there} places changed, carried as data")
    return data


def fixed_decks(project: Project, retail, modded, retail_files, modded_files) -> list:
    """Fixed decks when the mod's shuffle deals counts of copies (A4): each
    opponent's deck is the forty cards that shuffle deals from its pool,
    and its weighted pool stays retail's."""
    if not kit.deals_by_count(retail_files.slus, modded_files.slus):
        return []
    short, walked = [], []
    for d in range(len(modded.pools)):
        pool = modded.pools[d]["deck"]
        deck = kit.dealt_by_count(pool)
        if sum(deck.values()) < kit.DECK_SIZE:
            short.append(g.DUELIST_NAMES[d])
            project.pools[d]["deck"] = dict(retail.pools[d]["deck"])
            modded.pools[d]["deck"] = dict(retail.pools[d]["deck"])
            continue
        if sum(pool.values()) != kit.DECK_SIZE:
            walked.append(g.DUELIST_NAMES[d])
        set_fixed_deck(project, d, deck)      # the port deals this; the weighted pool stays retail's
        project.pools[d]["deck"] = dict(retail.pools[d]["deck"])
        modded.pools[d]["deck"] = dict(retail.pools[d]["deck"])       # nothing left to scale
    notes = [f"decks: the mod's Duel_ShuffleDeck deals each deck pool as counts of copies, in card order up to "
             f"{kit.DECK_SIZE}, with no limit of three (signature A4); {len(project.fixed)} decks written as "
             "fixed decks"]
    if walked:
        notes.append(f"decks: {len(walked)} pools do not add up to {kit.DECK_SIZE} ({', '.join(walked[:4])}"
                     f"{'...' if len(walked) > 4 else ''}): the fixed deck is what that shuffle deals from them, "
                     "the first cards by id")
    if short:
        notes.append(f"decks: {len(short)} pools hold fewer than {kit.DECK_SIZE} cards ({', '.join(short[:4])}); "
                     "the mod's shuffle would never finish; left as retail's")
    return notes


AI_COMMANDS = 0x800916E0, 0x800916E0 + 4 * 72    # gAiScript_apfnCommand
STAT_CAP_SITES = (0x800170E0, 0x80017200)       # Duel_CalcCardStats
OPPONENT_FIELD = 0x80024E08                     # func_80024DC8: the opponent's home field
CARD_FRAME = 0x8002C290                         # func_8002BFCC: the card's frame
# The card-colour patch's older ("v1") layout, before it also redirected the
# Library setup loop: init_container_entry_objs's and func_80016784's own
# redirects are the only trace of it, and its table lived here instead of
# alongside CARD_FRAME's. teatools/process-cardcolor/README.md #4 and
# scripts/card_color.py's OLD/OLD_DATA document and verify these bytes.
CARD_FRAME_OLD_BIG = 0x800293FC                 # init_container_entry_objs's redirect
CARD_FRAME_OLD_SMALL = 0x80016BAC               # func_80016784's redirect
CARD_FRAME_OLD_TABLE = 0x801DAE24               # the table, at its pre-migration home

# The card viewer's two 128px-wide atlas pages and the palette rows used by
# its four frame kinds.  These are the same sources the Frames page decodes
# for its retail fallback (qt.common._card_frame_background), kept here so an
# imported BIN produces ordinary, editable PNG frame styles instead of a
# preview-only raw WA patch.
CARD_FRAME_LEFT = 0xEE6800
CARD_FRAME_RIGHT = CARD_FRAME_LEFT + 16 * SECTOR
CARD_FRAME_PALETTES = 0xF06800
CARD_FRAME_KINDS = (("monster", 0, "gold"), ("magic", 1, "green"),
                    ("trap", 2, "pink"), ("ritual", 3, "blue"))

# Direct immediate values in the retail card-view renderer.  These are safe
# to import only when the modified instruction keeps the retail opcode and
# changes its 16-bit literal; arbitrary replacement code remains reported as
# code, rather than being guessed at as a layout.
CARD_LAYOUT_IMMEDIATES = {
    "art_y": 0x80028C4C,
    "title_x": 0x80028CC8,
    "atk_x": 0x80028EB0,
    "atk_y": 0x80028EC4,
    "def_x": 0x80028F3C,
    "def_y": 0x80028F50,
    "attribute_x": 0x80029084,
    "attribute_y": 0x80029098,
}


def card_frame_table(slus: bytes):
    """The TeaOnline card-colour patch's packed frame table, if present, in
    either layout the tool has written.

    The current layout replaces the Library setup loop with a lookup of one
    4-bit frame number for each card; its first two instructions name the
    table, and the remaining instructions are checked exactly so unrelated
    library changes are never mistaken for card colours. The older layout
    never touched the Library loop at all -- only the two other consumers --
    so it is detected by its own pair of redirects instead, with the table
    at a fixed, different address (card_frame_table_old).
    """
    at = g.slus_offset(CARD_FRAME)
    if at < 0 or at + 100 > len(slus):
        return card_frame_table_old(slus)
    words = struct.unpack_from("<25I", slus, at)
    # Word 15 sits right after the "slti s2,6 / bnez +2" bnez's delay slot:
    # process-cardcolor/README.md #3c calls the two paths through here a
    # "dead check: both paths converge", so this word (a plain nop in one
    # build, "li s2,0" in another -- both seen in real files, the other 23
    # words agreeing exactly) is not load-bearing and is not checked.
    fixed = (None, None, 0xA0800056, 0xA6A00054, 0x2671FFFF, 0x00118842, 0x00518821,
             0x92310000, 0x32720001, 0x12400002, 0x3232000F, 0x00119102,
             0x2A510006, 0x16200002, 0, None, 0x00129100, 0x24110160,
             0x02328821, 0xA4910054, 0x24840004, 0x26730001, 0x2A7102D3,
             0x1620FFEA, 0x24A50004)
    if any(expected is not None and word != expected for word, expected in zip(words, fixed)) or \
            words[0] >> 16 != 0x3C02 or words[1] >> 16 != 0x2442:
        return card_frame_table_old(slus)
    address = ((words[0] & 0xFFFF) << 16) + struct.unpack("<h", struct.pack("<H", words[1] & 0xFFFF))[0]
    table = g.slus_offset(address)
    size = (g.CARD_COUNT + 1) // 2       # cards 1 through 722, two nibbles per byte (361 for 722)
    if table < 0 or table + size > len(slus):
        return card_frame_table_old(slus)
    raw = slus[table:table + size]
    values = [((raw[(cid - 1) // 2] >> (4 * (cid & 1))) & 15) for cid in range(g.CARD_COUNT + 1)]
    return values, [(at, at + 100), (table, table + size)]


def card_frame_table_old(slus: bytes):
    """card_frame_table's fallback for the card-colour patch's older layout
    (process-cardcolor/README.md #4): its two redirects, verified exactly,
    name no table address of their own, so the table's fixed old home is
    read directly instead."""
    big, small = g.slus_offset(CARD_FRAME_OLD_BIG), g.slus_offset(CARD_FRAME_OLD_SMALL)
    table = g.slus_offset(CARD_FRAME_OLD_TABLE)
    size = (g.CARD_COUNT + 1) // 2
    if big < 0 or big + 8 > len(slus) or small < 0 or small + 4 > len(slus) or \
            table < 0 or table + size > len(slus):
        return None
    if slus[big:big + 8] != bytes.fromhex("786b0708ffff9324") or \
            slus[small:small + 4] != bytes.fromhex("e46b0708"):
        return None
    raw = slus[table:table + size]
    values = [((raw[(cid - 1) // 2] >> (4 * (cid & 1))) & 15) for cid in range(g.CARD_COUNT + 1)]
    return values, [(big, big + 8), (small, small + 4), (table, table + size)]


def _transparent_rect(image: pngio.Image, left: int, top: int, width: int, height: int) -> pngio.Image:
    """Clear an artwork window in an otherwise opaque PS1 frame atlas."""
    out = bytearray(image.rgba)
    for y in range(max(0, top), min(image.height, top + height)):
        start = (y * image.width + max(0, left)) * 4
        end = (y * image.width + min(image.width, left + width)) * 4
        out[start:end] = b"\0" * (end - start)
    return pngio.Image(image.width, image.height, bytes(out))


def _frame_atlas(wa: bytes, frame: int, monster: bool, art_rect=(19, 50, 102, 96)) -> pngio.Image | None:
    """Decode one 140×196 card-view plate from WA_MRG.MRG.

    The image is composed from the exact two VRAM atlas pages the original
    renderer uses.  It deliberately contains no card-specific artwork or
    text; transparent texels remain transparent so a full-bleed style can be
    drawn behind the normal card art, title, and stat sprites.
    """
    palette_at = CARD_FRAME_PALETTES + (8 + frame) * 0x200
    minimum = max(CARD_FRAME_RIGHT + 16 * SECTOR, palette_at + 0x200)
    if len(wa) < minimum:
        return None
    try:
        palette = image_extract.read_palette(wa, palette_at, 256)
        left_w, left_h, left_rgba = image_extract.decode(wa, CARD_FRAME_LEFT, 64, 256, 8, palette)
        right_w, right_h, right_rgba = image_extract.decode(wa, CARD_FRAME_RIGHT, 64, 256, 8, palette)
    except (IndexError, struct.error):
        return None
    left = pngio.Image(left_w, left_h, left_rgba)
    right = pngio.Image(right_w, right_h, right_rgba)
    # See func_80029EC4's Library atlas packing, mirrored in the existing Qt
    # preview helper.  The lower 4px edge is split into two 62px pieces and
    # stretched to the 64px output halves by the game's primitive layout.
    out = pngio.Image(140, 196, b"\0" * (140 * 196 * 4))
    out = pngio.paste(out, pngio.crop(left, 0, 0, 128, 192), 0, 0)
    out = pngio.paste(out, pngio.crop(right, 4, 0, 12, 128), 128, 0)
    out = pngio.paste(out, pngio.crop(right, 36, 0, 12, 68), 128, 128)
    if not monster:
        out = pngio.paste(out, pngio.crop(left, 0, 208, 128, 48), 0, 144)
    bottom = pngio.crop(left, 0, 0, 128, 4)
    # The original vertical-flips the source edge before placing it.
    rows = [bottom.rgba[(bottom.height - 1 - y) * bottom.width * 4:
                        (bottom.height - y) * bottom.width * 4]
            for y in range(bottom.height)]
    bottom = pngio.Image(bottom.width, bottom.height, b"".join(rows))
    out = pngio.paste(out, pngio.resample(pngio.crop(bottom, 0, 0, 62, 4), 64, 4), 0, 192)
    out = pngio.paste(out, pngio.resample(pngio.crop(bottom, 62, 0, 62, 4), 64, 4), 64, 192)
    # The PS1 submits the artwork after this opaque plate.  A card_layout
    # frame draws after the artwork instead, so its picture needs a real
    # transparent aperture or it would paint over the card art in-game.
    return _transparent_rect(out, *art_rect)


def _changed_immediate(retail_slus: bytes, modded_slus: bytes, address: int) -> int | None:
    """A changed same-opcode signed immediate at a RAM ``address``, if any."""
    at = g.slus_offset(address)
    if at < 0 or at + 4 > len(retail_slus) or at + 4 > len(modded_slus):
        return None
    old, new = struct.unpack_from("<I", retail_slus, at)[0], struct.unpack_from("<I", modded_slus, at)[0]
    if old == new or old >> 16 != new >> 16:
        return None
    value = new & 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


def _label_sprites_hidden(retail_slus: bytes, modded_slus: bytes) -> bool:
    """Recognise TLM's label-suppression patch without accepting arbitrary code.

    TLM replaces both ``lhu`` loads that provide the label Y coordinate with
    loads into ``$zero``.  The labels consequently draw at screen origin and
    are intentionally absent from the card.  Representing that as explicit
    ``hide`` state is both editable and faithful in the port.
    """
    locations = (0x80028D44, 0x80028D48)
    expected = (0x96420032, 0x96630032)
    replacement = (0x96000032, 0x96000032)
    words = []
    for address in locations:
        at = g.slus_offset(address)
        if at < 0 or at + 4 > len(retail_slus) or at + 4 > len(modded_slus):
            return False
        words.append((struct.unpack_from("<I", retail_slus, at)[0], struct.unpack_from("<I", modded_slus, at)[0]))
    return tuple(old for old, _ in words) == expected and tuple(new for _, new in words) == replacement


def import_card_layout(project: Project, retail_files, modded_files, report: list) -> list:
    """Import a modified card-frame atlas and recognised layout immediates.

    Raw WA replacements still preserve every unrecognised pixel and program
    patch.  This conversion adds the useful editor representation alongside
    them: each source frame becomes a PNG under ``frames/`` and known card
    renderer positions become the selected style's editable fields.
    """
    retail_wa, modded_wa = retail_files.wa, modded_files.wa
    atlas_ranges = ((CARD_FRAME_LEFT, CARD_FRAME_RIGHT + 16 * SECTOR),
                    (CARD_FRAME_PALETTES, CARD_FRAME_PALETTES + 12 * 0x200))
    atlas_changed = any(end <= len(retail_wa) and end <= len(modded_wa) and
                        retail_wa[start:end] != modded_wa[start:end]
                        for start, end in atlas_ranges)
    positions = {key: value for key, address in CARD_LAYOUT_IMMEDIATES.items()
                 if (value := _changed_immediate(retail_files.slus, modded_files.slus, address)) is not None}
    labels_hidden = _label_sprites_hidden(retail_files.slus, modded_files.slus)
    if not atlas_changed and not positions and not labels_hidden:
        return []

    styles = {}
    for kind, index, color in CARD_FRAME_KINDS:
        # A full-bleed style must opt back into the localized card-title
        # sprite.  The PS1 source always draws it over the frame plate.
        style = {"hand_color": color, "title": {"x": 12, "y": 14}}
        if atlas_changed:
            art_rect = (19, positions.get("art_y", 50), 102, 96) if kind == "monster" else (19, 50, 102, 96)
            image = _frame_atlas(modded_wa, index, kind == "monster", art_rect)
            if image is not None:
                path = f"frames/imported-{kind}.png"
                project.files[path] = pngio.encode(image)
                style["image"] = path
        styles[f"imported-{kind}"] = style

    # ``digits`` owns the positions in a full-bleed style.  The source
    # renderer's literals are top-left positions for a 4×6px, 13px-high run;
    # the current mod API stores that run's centre.
    if {"atk_x", "atk_y"} <= positions.keys():
        styles["imported-monster"].setdefault("digits", {})["atk"] = {
            "x": positions["atk_x"] + 12, "y": positions["atk_y"] + 6}
    if {"def_x", "def_y"} <= positions.keys():
        styles["imported-monster"].setdefault("digits", {})["def"] = {
            "x": positions["def_x"] + 12, "y": positions["def_y"] + 6}
    if "art_y" in positions:
        styles["imported-monster"]["art"] = {"x": 19, "y": positions["art_y"], "width": 102, "height": 96}
    if "title_x" in positions:
        styles["imported-monster"]["title"] = {"x": positions["title_x"], "y": 14}
    if {"attribute_x", "attribute_y"} <= positions.keys():
        styles["imported-monster"]["attribute"] = {
            "x": positions["attribute_x"], "y": positions["attribute_y"], "width": 16, "height": 16}
    if labels_hidden:
        styles["imported-monster"]["atk_label"] = {"hide": True}
        styles["imported-monster"]["dfd_label"] = {"hide": True}

    layout = project.other.get("card_layout")
    if not isinstance(layout, dict):
        project.other["card_layout"] = layout = {}
    existing = layout.get("frame_styles")
    if not isinstance(existing, dict):
        layout["frame_styles"] = existing = {}
    style_names = {}
    for name, style in styles.items():
        # An importer owns its generated names.  Do not overwrite a previous
        # hand-authored style should this helper ever be used on an existing
        # project in the future.
        candidate = name
        suffix = 2
        while candidate in existing:
            candidate = f"{name}-{suffix}"
            suffix += 1
        existing[candidate] = style
        style_names[name.removeprefix("imported-")] = candidate

    # Keep the four extracted plates selectable and make them the default
    # family when the player enables the generated full-bleed setting.
    names = style_names
    layout["default_styles"] = {"kinds": {
        "monster": names["monster"], "effect_monster": names["monster"],
        "magic": names["magic"], "equip": names["magic"],
        "ritual": names["ritual"], "trap": names["trap"],
    }}
    layout["default_style"] = names["monster"]
    if not any(isinstance(setting, dict) and setting.get("key") == "full_bleed" for setting in project.info.settings):
        project.info.settings.append({
            "key": "full_bleed", "label": "Imported card frame", "type": "bool", "default": 0,
            "description": "Use the card frame, layout and stat placement imported from the source game."})

    imported = ", ".join(kind for kind, _, _ in CARD_FRAME_KINDS if "image" in styles[f"imported-{kind}"])
    summary = f"frames: imported editable card-frame styles ({imported or 'layout only'})"
    if positions:
        changed = ", ".join(key.replace("_", " ") for key in positions)
        summary += f" and renderer positions ({changed})"
    if labels_hidden:
        summary += "; ATK and DEF labels are hidden as in the source game"
    report.append(summary)
    handled = [(g.slus_offset(CARD_LAYOUT_IMMEDIATES[key]),
                g.slus_offset(CARD_LAYOUT_IMMEDIATES[key]) + 4)
               for key in positions]
    if labels_hidden:
        handled += [(g.slus_offset(address), g.slus_offset(address) + 4)
                    for address in (0x80028D44, 0x80028D48)]
    return handled


def import_card_frames(project: Project, modded, slus: bytes, report: list) -> list:
    """Turn a recognised game's per-card frame colours into ``cards[]``."""
    found = card_frame_table(slus)
    if found is None:
        return []
    values, handled = found
    changed = []
    for cid in range(1, g.CARD_COUNT + 1):
        card = project.cards[cid]
        # The table's zero through five are the port's Monster through Orange
        # palette rows.  A type-coloured card needs no explicit mod entry.
        frame = values[cid] if values[cid] < len(g.FRAME_NAMES) else 0
        frame = -1 if frame == g.type_frame(card.type) else frame
        if card.frame != frame:
            card.frame = frame
            changed.append(cid)
    report.append(f"cards: {len(changed)} frame colours imported from the mod's per-card frame table")
    return handled


# Title/menu assets live in SU.MRG rather than WA_MRG.MRG.  The ordinary
# raw-WA fallback cannot preserve that archive, so decode the same sprites as
# the UI workspace and turn only changed visual layers into ordinary mod PNGs.
# These names are the port's built-in menu entries, in the same order as
# ui_assets.ENTRY_SPRITES.
TITLE_MENU_ENTRIES = ("new_game", "load", "duel", "trade", "options", "campaign", "free_duel",
                      "build_deck", "library", "password", "save")


def _same_image(one: pngio.Image, other: pngio.Image) -> bool:
    return one.width == other.width and one.height == other.height and one.rgba == other.rgba


def import_title_and_menu_assets(project: Project, retail_files, modded_files, report: list) -> tuple[list[str], list[str], str | None]:
    """Recover modified SU.MRG title and retail-menu images as editable PNGs.

    TeaTools' Main Logo writer operates on the title package's texture pages,
    palettes and sprite geometry.  ``TitleArt`` already reconstructs those
    pages with the game's sprite layout, so it is the single source of truth
    for import as well as preview.  A full canvas is used for the wallpaper:
    it preserves the game's tiled 256x240 background in the title API's
    320x240 picture field.
    """
    retail_su = ui_assets.read_su(retail_files)
    modded_su = ui_assets.read_su(modded_files)
    retail, modded = ui_assets.TitleArt(retail_su), ui_assets.TitleArt(modded_su)
    if not retail.ok or not modded.ok:
        # An ordinary SLUS/WA pair has no supplementary title archive on
        # either side.  That is not evidence of a title modification and must
        # not make a no-change import look partial.  One readable archive is
        # different: comparison is impossible and needs a visible diagnostic.
        if retail_su is None and modded_su is None:
            return [], [], None
        report.append("title: DATA/SU.MRG is missing from one source; title and menu graphics were not imported")
        return [], [], "DATA/SU.MRG"

    title, menu = {}, {}
    changed_title = []
    retail_wall, modded_wall = retail.wall(), modded.wall()
    if not _same_image(retail_wall, modded_wall):
        path = "ui/title-background.png"
        project.files[path] = pngio.encode(modded_wall)
        title["background"] = {"image": path, "picture": True}
        changed_title.append("background")
    for layer in ("logo", "copyright", "prompt"):
        old, _, _ = retail.layer(layer)
        image, _, _ = modded.layer(layer)
        if not _same_image(old, image):
            path = f"ui/title-{layer}.png"
            project.files[path] = pngio.encode(image)
            title[layer] = {"image": path}
            changed_title.append(layer)

    changed_menu = []
    entries = {}
    for index, name in enumerate(TITLE_MENU_ENTRIES):
        entry = {}
        for selected, key, suffix in ((False, "image", ""), (True, "selected_image", "-selected")):
            old, _, _ = retail.entry(index, selected)
            image, _, _ = modded.entry(index, selected)
            if _same_image(old, image):
                continue
            path = f"ui/menu-{name}{suffix}.png"
            project.files[path] = pngio.encode(image)
            entry[key] = path
        if entry:
            entries[name] = entry
            changed_menu.append(name)
    if entries:
        menu["entries"] = entries

    if title:
        project.other["title"] = title
    if menu:
        project.other["menu"] = menu
    if changed_title:
        report.append("title: imported " + ", ".join(changed_title) + " image"
                      + ("s" if len(changed_title) != 1 else "") + " from SU.MRG")
    if changed_menu:
        report.append(f"menus: imported {len(changed_menu)} changed retail menu entr"
                      f"{'y' if len(changed_menu) == 1 else 'ies'} from SU.MRG")
    return changed_title, changed_menu, None


def kit_rules(project: Project, modded, retail_files, modded_files) -> tuple:
    """(report lines, README lines): the rules the kit's code sets that
    mod.json has keys for, read from the code and its tables, and what it
    changes that no key carries, in the game's terms."""
    retail_slus, slus = retail_files.slus, modded_files.slus
    notes, readme, missing, explained = [], [], [], []
    memory, retail = kit.Memory(slus), kit.Memory(retail_slus)
    cards = modded.cards

    chest = kit.chest_overflow(retail_slus, slus)
    if chest:
        limit, pay = chest
        project.other["chest_overflow"] = {"limit": limit, "starchips": pay}
        notes.append(f"rules: the mod's Duel_AwardCard keeps {limit} copies of a card in the chest and pays {pay} "
                     f"starchips for each card past them (A3): \"chest_overflow\"")
        readme.append(f"- The chest keeps {limit} copies of a card; each card won past them is worth {pay} starchips.")
    terrain = kit.terrain_bonus(retail_slus, slus)
    if terrain:
        table = {kit.TERRAIN_NAMES[t - 1]: {g.TYPE_NAMES[k]: v for k, v in sorted(values.items())}
                 for t, values in terrain.table.items() if values}
        table["replace"] = True
        project.other["terrain_bonus"] = table
        notes.append(f"rules: the terrain bonuses are the mod's, from {terrain.where} (A9): \"terrain_bonus\", every "
                     "pair, and no bonus for the others")
        readme.append("- Each field card's terrain gives the monster types the mod's bonuses (in steps of 10, "
                      "not the disc's +500/-500).")
        if terrain.more_terrains > 0:
            missing.append(f"{terrain.more_terrains} terrains of the mod's own past the six (7 and up, some opponents' "
                           "home fields): the port has six")
        if terrain.by_attribute:
            missing.append(f"terrains from {terrain.by_attribute} up that favour a monster's attribute, not its type")
        explained.append((kit.TERRAIN_BOOST, kit.TERRAIN_BOOST + 120))
    traps = kit.trap_thresholds(retail_slus, slus)
    if traps:
        project.other["trap_thresholds"] = traps
        notes.append(f"rules: the attack traps' thresholds are the mod's (A8): \"trap_thresholds\" "
                     f"({', '.join(f'{k} {v}' for k, v in traps.items())})")
        readme.append("- Attack traps spring up to the mod's attack thresholds.")
        missing.append("which cards act as which attack trap (the mod's lists, in its rewritten "
                       "Duel_SelectAttackTrap): the disc's six traps keep their places")
        explained.append((kit.TRAP_THRESHOLDS, kit.TRAP_THRESHOLDS + 12))
    bonus = kit.equip_bonus(retail_slus, slus)
    if bonus:
        equips = {cid: v for cid, v in bonus.fixed.items() if cid in cards and cards[cid].type == g.TYPE_EQUIP}
        others = [cid for cid in bonus.fixed if cid not in equips]
        for cid, points in sorted(equips.items()):     # the Cards tab's Equip bonus
            project.set_equip_bonus(cid, points)
        notes.append(f"rules: the mod's DuelScene_UpdateCardPlacement (code at {bonus.where}) sets {len(equips)} "
                     f"equips' bonuses (A7): \"equips\" \"bonus\"; the rest keep +500")
        if equips:
            readme.append(f"- {len(equips)} equips add the mod's own bonus instead of +500.")
        if others:
            missing.append(f"bonuses the mod gives cards that are not equip cards ({_names(project, others)}): "
                           "monsters used as equips and magic")
        if bonus.conditional:
            missing.append(f"{len(bonus.conditional)} equip bonuses that grow with a count the mod keeps "
                           f"({_names(project, [c for c, _, _ in bonus.conditional])})")
        if bonus.special:
            missing.append(f"{len(bonus.special)} equips (or more) with an effect of their own in the mod's code "
                           f"({_names(project, bonus.special)}): they keep +500 (Megamorph +1000)")
    megamorph = kit.megamorph_bonus(retail_slus, slus)
    if megamorph is not None:
        project.set_equip_bonus(kit.MEGAMORPH_CARD, megamorph)
        notes.append(f"rules: Megamorph's own equip bonus is the mod's (Tables_EquipBoost, 0x{kit.MEGAMORPH_BONUS:08X}): "
                     f"\"equips\" \"bonus\" {megamorph:+d} instead of +1000")
        readme.append(f"- Megamorph adds {megamorph:+d} instead of +1000.")
        explained.append((kit.MEGAMORPH_BONUS, kit.MEGAMORPH_BONUS + 4))
    ai_rows, ai_retail_rows = kit.opponent_ai(slus), kit.opponent_ai(retail_slus)
    ai_changed = []
    if ai_rows and ai_retail_rows:
        for d in range(1, g.DUELIST_COUNT):      # 0 is "Unused" (the player's slot): no disc duelist, no rule for it
            if list(ai_rows[d]) != list(ai_retail_rows[d]):
                duelist_rules.set_rules(project, d, ai=list(ai_rows[d]))
                ai_changed.append(d)
        if ai_changed:
            shown = ", ".join(g.DUELIST_NAMES[d] for d in ai_changed[:8])
            if len(ai_changed) > 8:
                shown += f" and {len(ai_changed) - 8} more"
            notes.append(f"rules: {len(ai_changed)} duelists' way of playing is the mod's, from gDuel_aOpponentData "
                         f"(0x{kit.OPPONENT_DATA:08X}): \"ai\" ({shown})")
            readme.append(f"- {len(ai_changed)} duelists play by the mod's own numbers, not the disc's.")
        explained.append((kit.OPPONENT_DATA + g.AI_FIELDS, kit.OPPONENT_DATA + g.DUELIST_COUNT * g.AI_FIELDS))
    draws = kit.extra_draws(retail_slus, slus)
    if draws and draws.count:
        # "limits" "card_drops" locks the player's Game > Card drops while
        # the mod is applied (1 to 99, the setting's range).
        count = min(max(draws.count, 1), values.CARD_DROPS_MAX)
        limits = project.other.get("limits")
        if not isinstance(limits, dict):
            limits = project.other["limits"] = {}
        limits["card_drops"] = count
        notes.append(f"rules: the mod draws {draws.count} prizes a win (A1: its loop at 0x{draws.code:08X}): "
                     f"\"limits\" \"card_drops\" {count}, which locks Game > Card drops while the mod is applied")
        if count != draws.count:
            missing.append(f"{draws.count} prizes a win: the port deals at most {values.CARD_DROPS_MAX}")
        readme.append(f"- The mod gives {count} cards a win: Game > Card drops shows {count}, set by the mod, "
                      "while it is applied.")
    if any(memory.bytes(a, 0x40) != retail.bytes(a, 0x40) and b"\x31\x75" in memory.bytes(a, 0x120)
           for a in STAT_CAP_SITES):
        missing.append("ATK, DEF and life points up to 30000 (5 digits): the port keeps 9999")
    if memory.word(OPPONENT_FIELD) != retail.word(OPPONENT_FIELD):
        missing.append("each opponent's home field from the mod's table")
    start, end = AI_COMMANDS
    changed = [k for k in range(0, end - start, 4) if memory.word(start + k) != retail.word(start + k)]
    if changed:
        missing.append(f"the opponents' play (AI): {len(changed)} of its script commands are the mod's code, and "
                       "the mod's scripts in WA_MRG.MRG expect them, so they play by the disc's commands")
    if memory.bytes(CARD_FRAME, 16) != retail.bytes(CARD_FRAME, 16) and card_frame_table(slus) is None:
        missing.append("each card's frame colour by its class (Effect, Union...)")
    if any(slus[0x88:0x800]):
        notes.append("rules: the executable's header holds code (0x8000B070 and up): a mod made with the kit "
                     "that patches the duel in MIPS (A16)")
    effects = sum(1 for card in project.cards.values() if "Effect" in card.description)
    if effects:
        missing.append(f"monster effects: {effects} cards say «Effect» in their text, which the mod's code "
                       "carries out in battle and when summoned")
    for line in missing:
        notes.append(f"not imported: {line}")
    return notes, readme, missing, explained


def write_readme(project: Project, readme: list, missing: list):
    if not readme and not missing:
        return
    lines = [f"{project.info.name}", "", "Imported by the FM Editor from a modified game. It plays close to the "
             "mod's own rules; what the mod does in code of its own is not here.", ""]
    if readme:
        lines += ["What the port does the mod's way:", ""] + readme + [""]
    if missing:
        lines += ["What the mod changes that this import cannot bring:", ""] + [f"- {m[0].upper()}{m[1:]}."
                                                                             for m in missing] + [""]
    lines.append("import-report.txt has the details.")
    project.files["README.txt"] = ("\n".join(lines) + "\n").encode("utf-8")


def import_modded(retail_files, modded_files, mod_id: str = "imported-mod", name: str = None,
                  progress=None) -> ImportResult:
    """`progress(what)` is called as each stage starts, for a window that
    would otherwise sit unpainted while a hundred megabytes are read."""
    say = progress if progress is not None else lambda _what: None
    say("Reading the retail tables")
    retail = g.load_game(retail_files)
    report = []
    try:
        modded = g.load_game(modded_files)
    except Exception as problem:
        raise ValueError(f"the modified files could not be read as the game's tables: {problem}")
    project = Project(retail)
    project.info.id = mod_id
    project.info.name = name or mod_id
    project.info.description = "Imported from a modified game by the FM Editor."
    result = ImportResult(project, report)
    # TeaTools recognition is deliberately an analysis pass: it is allowed to
    # report a decoder failure but never to change this import's outcome.
    try:
        result.analysis = tea_import.analyze(retail_files, modded_files)
    except Exception as problem:
        report.append(f"TeaTools analysis: unavailable ({type(problem).__name__}: {problem})")
    for note in modded.notes:
        report.append(f"note: {note}")
        result.unhandled += 1

    # Cards and the rule tables: the editor's own diff.
    say("Cards and the rule tables")
    spaced = 0
    for cid, card in modded.cards.items():
        card = card.copy()
        old = retail.cards.get(cid)
        for name in ("name", "description"):
            if old is not None and getattr(card, name) != getattr(old, name) and \
                    _line_ends(getattr(card, name)) == _line_ends(getattr(old, name)):
                setattr(card, name, getattr(old, name))     # only spaces at line ends differ: the same text
                spaced += 1
        project.cards[cid] = card
    passwords_changed = 0
    for cid, password in modded.passwords.items():
        if password != retail.passwords.get(cid, ""):
            project.set_password(cid, password)
            passwords_changed += 1
    if passwords_changed:
        report.append(f"cards: {passwords_changed} passwords imported")
    starchips_changed = 0
    for cid, price in modded.starchips.items():
        if cid in project.cards and price != retail.starchips.get(cid):
            project.set_starchips(cid, price)
            starchips_changed += 1
    if starchips_changed:
        report.append(f"cards: {starchips_changed} starchip shop prices imported")
    drop_notes = decode_drop_pools(retail, modded, retail_files, modded_files)
    project.fusions = dict(modded.fusions)
    project.equips = {e: set(m) for e, m in modded.equips.items()}
    equip_notes = read_equip_bitmaps(project, modded, retail_files, modded_files)
    project.rituals = dict(modded.rituals)
    ritual_notes = check_rituals(project, modded)
    project.pools = [{p: dict(modded.pools[d][p]) for p in g.POOLS} for d in range(len(modded.pools))]
    # The Password screen table is one of the editor's normal mod.json
    # tables.  Keep it out of raw WA patches when every changed record has a
    # value the port's "passwords" reader can express.
    password_changed = [cid for cid in retail.cards
                        if modded.passwords.get(cid, "") != retail.passwords.get(cid, "")]
    price_changed = [cid for cid in retail.cards
                     if modded.starchips.get(cid, 0) != retail.starchips.get(cid, 0)]
    password_handled = []
    password_start = g.PASSWORD_TABLE
    password_end = password_start + 8 * (g.CARD_COUNT + 1)
    supported_passwords = password_end <= len(modded_files.wa) and \
        retail_files.wa[password_start:password_start + 8] == modded_files.wa[password_start:password_start + 8] and \
        all(modded.starchips.get(cid, 0) <= 999999 for cid in retail.cards)
    if (password_changed or price_changed) and supported_passwords:
        for cid in password_changed:
            project.set_password(cid, modded.passwords[cid])
        for cid in price_changed:
            project.set_starchips(cid, modded.starchips[cid])
        password_handled.append((password_start, password_end))
        report.append(f"passwords: {len(password_changed)} password(s) and {len(price_changed)} starchip price(s) imported")
    changed_cards = sum(1 for cid in retail.cards if project.card_changed(cid))
    report.append(f"cards: {changed_cards} changed")
    if spaced:
        report.append(f"cards: {spaced} names or texts differ from retail only by spaces at the end of a line; "
                      "kept as retail")
    report.append(f"fusions: {sum(1 for p in set(retail.fusions) | set(modded.fusions) if retail.fusions.get(p) != modded.fusions.get(p))} pairs differ")
    report.append(f"equips: {sum(1 for e in set(retail.equips) | set(project.equips) if set(retail.equips.get(e, [])) != set(project.equips.get(e, [])))} equip cards differ")
    report += equip_notes
    report.append(f"rituals: {sum(1 for r in set(retail.rituals) | set(project.rituals) if retail.rituals.get(r) != project.rituals.get(r))} differ")
    report += ritual_notes
    pools_changed = sum(1 for d in range(len(retail.pools)) for p in g.POOLS if retail.pools[d][p] != modded.pools[d][p])
    report.append(f"pools: {pools_changed} of {len(retail.pools) * len(g.POOLS)} differ")
    report += drop_notes
    report += fixed_decks(project, retail, modded, retail_files, modded_files)
    starter_handled = import_starter_table(project, retail_files.wa, modded_files.wa, report)
    off_total = []
    for d in range(len(modded.pools)):
        for p in g.POOLS:
            total = sum(modded.pools[d][p].values())
            if modded.pools[d][p] != retail.pools[d][p] and total != g.POOL_TOTAL:
                off_total.append(f"{g.DUELIST_NAMES[d]} {p}: {total}")
                project.pools[d][p] = normalize(project.pools[d][p])
    if off_total:
        report.append(f"pools: {len(off_total)} pools do not add up to 2048 in the modified game (for example "
                      f"{'; '.join(off_total[:3])}), which the game's draw needs; the mod likely changes the draw "
                      "in its code. They are scaled to 2048, keeping each card's share")

    # Text.
    say("Text")
    card_fields = coded_card_texts(retail_files, modded_files)
    text, carried = text_changes(retail_files.slus, modded_files.slus, report, modded_files.wa, card_fields)
    if text:
        project.files["text.txt"] = text.encode("utf-8")
        project.other["text"] = "text.txt"
    for (cid, field), item in carried.items():
        value = manifest.plain_name(item) if field == "name" else manifest.listing_plain(item)
        setattr(project.cards[cid], field, value)
        project.text_cards.setdefault(cid, {})[field] = value
    for field, label in (("name", "names"), ("description", "texts")):
        ids = [cid for cid in card_fields.get(field, ()) if (cid, field) in carried]
        empty = [cid for cid in ids if field == "description" and not project.cards[cid].description]
        if ids:
            report.append(f"cards: {len(ids)} card {label} carry color or icon codes"
                          + (f" or are empty on purpose ({len(empty)} empty)" if empty else "")
                          + "; text.txt carries them (cards[] cannot)")
    blank = [cid for cid, card in project.cards.items() if cid <= g.CARD_COUNT and not card.name
             and (cid, "name") not in carried]
    for cid in blank:
        project.cards[cid].name = retail.cards[cid].name
    if blank:
        report.append(f"cards: {len(blank)} names could not be read; kept as retail's")

    say("Pictures")
    carried = import_card_art(project, retail_files.wa, modded_files.wa, report, say)
    renamed_duelists(project, retail_files.slus, modded_files.slus, report)
    import_card_types(project, retail_files.slus, modded_files.slus, modded_files.wa, report)
    report_unresolved_type_and_attribute_ids(project, report)
    # After the renames: a renamed duelist's entry takes its portrait too,
    # rather than a second entry being written for the same duelist.
    say("Portraits")
    carried += import_duelist_portraits(project, retail_files.wa, modded_files.wa, report)
    guardian_handled = import_guardian_stars(project, retail, modded, retail_files.slus, modded_files.slus,
                                              modded_files.wa, report)
    frame_handled = import_card_frames(project, modded, modded_files.slus, report)
    layout_handled = import_card_layout(project, retail_files, modded_files, report)
    say("Title screen and menus")
    title_layers, menu_entries, title_missing = import_title_and_menu_assets(project, retail_files, modded_files, report)
    title_format = teatools_import.format_named("logo")
    if title_layers or menu_entries:
        details = []
        if title_layers:
            details.append("title " + ", ".join(title_layers))
        if menu_entries:
            details.append(f"{len(menu_entries)} menu entries")
        result.finding(title_format.identifier, title_format.workspace, "recovered", "DATA/SU.MRG",
                       "; ".join(details))
    elif title_missing:
        result.finding(title_format.identifier, title_format.workspace, "partial", title_missing,
                       "supplementary archive could not be compared")

    # Rules the kit's code sets.
    say("Rules the mod's code sets")
    rule_notes, readme, missing, explained = kit_rules(project, modded, retail_files, modded_files)
    report += rule_notes
    result.unhandled += len(missing)
    write_readme(project, readme, missing)

    # The rest of the executable.
    slus_runs = _runs(retail_files.slus, modded_files.slus, 0, max(len(retail_files.slus), len(modded_files.slus)), 0)
    if len(retail_files.slus) != len(modded_files.slus):
        report.append(f"executable: its size differs ({len(modded_files.slus)} bytes); only the tables were read")
        result.unhandled += 1
    text_read = text_spans(modded_files.slus) or []      # what text.txt carries; nothing when unreadable
    handled = [(g.slus_offset(a), g.slus_offset(b)) for a, b in SLUS_HANDLED + text_read] + guardian_handled + frame_handled + layout_handled
    named = [(g.slus_offset(a), g.slus_offset(b), label) for a, b, label in SLUS_REGIONS]
    # A rule above (terrain_bonus, trap_thresholds, megamorph_bonus, the AI
    # table...) may already have read a named region's bytes as the mod's
    # own values; do not also report that region as "cannot be imported".
    explained_offsets = [(g.slus_offset(a), g.slus_offset(b)) for a, b in explained]
    unexplained_runs = _subtract(slus_runs, explained_offsets)
    for low, high, label in named:
        count = sum(min(e, high) - max(s, low) for s, e in unexplained_runs if s < high and e > low)
        if count:
            report.append(f"executable: {label} changed ({count} bytes); the port reads the executable's code "
                          "and tables natively, so this cannot be imported")
            result.unhandled += 1
    other = _subtract(slus_runs, handled + [(low, high) for low, high, _ in named])
    # Bytes the retail text used that the modified text no longer reads:
    # left-over text of a repacked bank, or the mod's code written over it.
    old_text = [(g.slus_offset(a), g.slus_offset(b)) for a, b in text_spans(retail_files.slus) or []]
    code = _subtract(other, old_text)
    leftover = _subtract(other, code)
    if code:
        report.append(f"executable: {sum(e - s for s, e in code)} other bytes changed: code patches, or the mod's "
                      "own code and data, which the native port cannot take:")
        report += describe_places(retail_files.slus, modded_files.slus, code)
        result.unhandled += 1
    if leftover:
        report.append(f"executable: {sum(e - s for s, e in leftover)} bytes where the retail text was changed, and "
                      "the modified text does not read them (text left over, or code):")
        report += describe_places(retail_files.slus, modded_files.slus, leftover)
        result.unhandled += 1

    # The rest of WA_MRG.MRG.
    say("The rest of WA_MRG.MRG")
    data = wa_data(project, retail_files, modded_files, report,
                   carried + starter_handled + password_handled)
    if data:
        project.other["data"] = data
    if result.unhandled:
        report.append(f"{result.unhandled} kind(s) of change could not be imported (above)")
    _tea_analysis_status(result)
    if result.analysis is not None:
        report.extend(("", *result.analysis.report().rstrip().splitlines()))
        if result.analysis_status:
            report.append("TeaTools conversion status:")
            for feature, status in sorted(result.analysis_status.items()):
                report.append(f"  {feature}: {status.replace('_', ' ')}")
        sidecar = result.analysis.as_dict()
        sidecar["import_status"] = dict(sorted(result.analysis_status.items()))
        project.files["import-analysis.json"] = (json.dumps(sidecar, indent=2, sort_keys=True) + "\n").encode("utf-8")
    project.files["import-report.txt"] = ("\n".join(report) + "\n").encode("utf-8")
    return result


def save(result: ImportResult, folder) -> None:
    """Write the imported mod: mod.json and the files it names."""
    folder = Path(folder)
    manifest.save_mod(result.project, folder)
