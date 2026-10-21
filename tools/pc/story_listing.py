#!/usr/bin/env python3
"""The campaign's scenes as an editable listing, and back (notes/story.md).

    python3 tools/pc/story_listing.py extract [--game <disc, or game/>] [-o campaign.story]
    python3 tools/pc/story_listing.py check   [--game <disc, or game/>] [-i campaign.story]
    python3 tools/pc/story_listing.py patch   [--game <disc, or game/>] -i campaign.story -o WA_MRG.MRG

`extract` writes the 199 scenes of the campaign script the way a story mod
edits them: the dialogue in the words the game says, the duellists and the
flags by the names the game itself carries, and one `names:` section at the
end holding the numbers for the pictures, graphics and songs the game leaves
unnamed. `check` reads a listing, assembles the script bank again and
compares it with the disc's, byte for byte, which is what shows the listing
loses nothing.

`patch` assembles a listing into a new WA_MRG.MRG. It never writes the retail
archive in place: pass an explicit output filename, then import that copy as
a data replacement or use it with an extracted-disc workflow.

The bank is 0x1000 bytes at 0xF34000 of DATA/WA_MRG.MRG: a table of 199
little-endian u16 offsets, the scenes' byte-coded streams, and 0xFF filler.
`src/game/script_run_tick.c` dispatches the 23 commands; the grammar here is
the one `src/pc/story/story.c` compiles.
"""
from __future__ import annotations

import argparse
import bisect
import collections
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/pc"))

import text_listing as tl                                   # noqa: E402
from fm_editor import disc                                  # noqa: E402
import character_sheet                                      # noqa: E402

# Where the campaign script is, and how much room it has. The bank is two
# sectors; Campaign_LoadScenePackageStage transfers it to 0x801A8000
# (notes/mrg-files.md, "Campaign scene package").
CAMPAIGN_SCRIPT_AT = 0xF34000
CAMPAIGN_SCRIPT_SIZE = 0x1000
# What the disc's own bank names. A bank says its own count (scene_count),
# so this is the disc's number rather than a limit; SCENE_LIMIT is the limit,
# because gCampaignSceneIndex is one byte.
SCENE_COUNT = 199
SCENE_LIMIT = 256
FILLER = 0xFF

# The first duellist name in the names bank, and the campaign flag of the
# first duellist beaten (src/pc/free_duel/duelists.c, campaign_flags.h).
DUELIST_NAME_TEXT_BASE = 0x8328
DUELIST_COUNT = 40
FLAG_DUELIST_BEATEN_BASE = 0x1F
FLAG_TOURNAMENT_COMPLETE = 0x47

# A place on the campaign map and the scene the player arrives in: the
# overworld adds 32 (src/overlays/overworld/set_location.c).
PLACE_COUNT = 16
PLACE_SCENE_OFFSET = 32

# gDuel_bTerrain, 1 Forest to 6 Yami (src/pc/cards/tables.h).
TERRAINS = {0: "arena", 1: "forest", 2: "wasteland", 3: "mountain", 4: "sogen", 5: "umi", 6: "yami"}

# The dialogue control that starts a campaign duel: F8, secondary command 13
# (src/game/duel_effect_command_table.c, text_start_campaign_duel.c). Its
# operands are opponent, the scene on winning, the scene on losing, the
# terrain and a u16 song.
DUEL_CONTROL = bytes((0xF8, 0x0D))
DUEL_CONTROL_OPERANDS = 6


class StoryError(Exception):
    """A listing the assembler cannot read, or a bank it cannot decode."""


# --- the commands --------------------------------------------------------
#
# Each entry is the command's name here, and how many operand bytes it takes
# in the stream. A callable length reads the operands it needs to decide, as
# the handlers do. `ends` marks the commands after which the stream does not
# carry on: the halts, the jumps, and the four that hand the frontend to
# another mode without clearing the command word.

def _picture_length(bank: bytes, at: int) -> int:
    return 6 if _u16(bank, at + 1) & 0x8000 else 2


def _flag_length(bank: bytes, at: int) -> int:
    return 2 if _u16(bank, at + 1) & 0x4000 else 4


def _sound_length(bank: bytes, at: int) -> int:
    flags = bank[at + 1]
    return 3 if (flags & 0x3F) == 0 or flags & 2 else 1


COMMANDS = {
    0: ("halt", 0),
    1: ("backdrop", _picture_length),
    2: ("say", 2),
    3: ("flag", _flag_length),
    4: ("stage", _picture_length),
    5: ("show", 0),
    6: ("pan", 6),
    7: ("panning", 0),
    8: ("map", 1),
    9: ("sprite", 2),
    10: ("sound", _sound_length),
    11: ("music_fade", 1),
    12: ("goto", 2),
    13: ("save", 4),
    14: ("unused14", 0),
    15: ("unused15", 0),
    16: ("screen_fade", 1),
    17: ("results", 2),
    18: ("gameover", 0),
    19: ("credits", 0),
    20: ("pause", 2),
    21: ("deck", 2),
    22: ("menu", 0),
}
ENDS = {0, 8, 12, 14, 15, 18, 19, 22}
COMMAND_LIMIT = 0x1F + 1        # Script_RunTick masks the word with 0x1F


def _u16(data: bytes, at: int) -> int:
    return data[at] | data[at + 1] << 8


def command_length(bank: bytes, at: int) -> int:
    """The operand bytes of the command at `at`."""
    opcode = bank[at] & 0x1F
    if opcode not in COMMANDS:
        raise StoryError(f"command {opcode} at {at:#x} is not one of the 23")
    length = COMMANDS[opcode][1]
    return length(bank, at) if callable(length) else length


# --- reading the bank ---------------------------------------------------

def read_bank(wa: bytes) -> bytes:
    """The campaign script out of DATA/WA_MRG.MRG."""
    bank = wa[CAMPAIGN_SCRIPT_AT:CAMPAIGN_SCRIPT_AT + CAMPAIGN_SCRIPT_SIZE]
    if len(bank) != CAMPAIGN_SCRIPT_SIZE:
        raise StoryError(f"WA_MRG.MRG is too short for the campaign script at {CAMPAIGN_SCRIPT_AT:#x}")
    return bank


def scene_count(bank: bytes) -> int:
    """How many scenes the bank's table holds.

    The first entry is where the first scene's bytes start, which is the end
    of the table, so the table says its own length. The disc's is 199; a mod
    that adds scenes has more, and the engine reads the table by index, so a
    longer one works the same way. The count is capped because
    gCampaignSceneIndex is one byte."""
    first = struct.unpack_from("<H", bank)[0]
    if first % 2 or not 0 < first // 2 <= SCENE_LIMIT:
        raise StoryError(f"the offset table's first entry is {first:#x}, which is no table length")
    return first // 2


def scene_offsets(bank: bytes) -> list[int]:
    count = scene_count(bank)
    return list(struct.unpack_from("<%dH" % count, bank))


@dataclass
class Instruction:
    offset: int
    opcode: int
    raw: int                    # the stream byte, flags and all
    operands: bytes

    @property
    def length(self) -> int:
        return 1 + len(self.operands)

    def u16(self, index: int = 0) -> int:
        return self.operands[index] | self.operands[index + 1] << 8


@dataclass
class Block:
    """One run of commands: where it starts, the scenes that enter at it, and
    whether anything jumps to it."""
    offset: int
    scenes: list[int] = field(default_factory=list)
    instructions: list[Instruction] = field(default_factory=list)
    entered: bool = False       # a jump target


def disassemble(bank: bytes) -> tuple[list[Block], list[int]]:
    """Every command reachable from the 199 scenes, as blocks in bank order."""
    offsets = scene_offsets(bank)
    decoded: dict[int, Instruction] = {}
    targets: set[int] = set()
    work = collections.deque(sorted(set(offsets)))
    while work:
        at = work.popleft()
        while at < len(bank) and at not in decoded:
            opcode = bank[at] & 0x1F
            length = command_length(bank, at)
            if at + 1 + length > len(bank):
                raise StoryError(f"the command at {at:#x} runs past the bank")
            instruction = Instruction(at, opcode, bank[at], bank[at + 1:at + 1 + length])
            decoded[at] = instruction
            for target in _targets(instruction):
                if target not in targets:
                    targets.add(target)
                    work.append(target)
            if opcode in ENDS:
                break
            at += instruction.length

    starts = set(offsets) | targets
    blocks: list[Block] = []
    for start in sorted(starts):
        if start not in decoded:
            raise StoryError(f"nothing decodes at {start:#x}, which a scene or a jump reaches")
        block = Block(start, entered=start in targets)
        at = start
        while at in decoded:
            block.instructions.append(decoded[at])
            if decoded[at].opcode in ENDS:
                break
            at += decoded[at].length
            if at in starts:            # the next block owns the rest
                break
        blocks.append(block)
    for scene, offset in enumerate(offsets):
        for block in blocks:
            if block.offset == offset:
                block.scenes.append(scene)
                break
    _check_coverage(bank, decoded)
    return blocks, offsets


def _targets(instruction: Instruction) -> list[int]:
    """Where this command can send the cursor inside the bank."""
    if instruction.opcode in (12, 21):
        return [instruction.u16()]
    if instruction.opcode == 3 and not (instruction.u16() & 0x4000):
        return [instruction.u16(2)]
    return []


def _check_coverage(bank: bytes, decoded: dict[int, Instruction]) -> None:
    """Every byte from the table's end to the last command decodes, and what
    follows is filler. A gap would mean the walk misread a length."""
    covered = set()
    for instruction in decoded.values():
        covered.update(range(instruction.offset, instruction.offset + instruction.length))
    end = max(covered) + 1
    gaps = sorted(set(range(len(scene_offsets(bank)) * 2, end)) - covered)
    if gaps:
        raise StoryError("bytes no command covers, from %#x (%d in all)" % (gaps[0], len(gaps)))
    tail = set(bank[end:])
    if tail - {FILLER}:
        raise StoryError(f"the bytes after the last command at {end:#x} are not {FILLER:#x} filler")


# --- the game's own names ----------------------------------------------

@dataclass
class Duel:
    """A campaign duel, as a dialogue stream starts it."""
    opponent: int
    win: int
    lose: int
    terrain: int
    song: int


class GameText:
    """The strings the listing borrows its names from: the dialogue the
    scenes show, and the duellists' names."""

    def __init__(self, slus: bytes):
        image = tl.Image.__new__(tl.Image)
        image.data = slus
        self.image = image
        self.glyphs = tl.glyph_characters(image)
        self.banks = {bank.name: bank for bank in tl.banks(image)}
        self.ops = {name: tl.decode_bank(image, bank, self.glyphs)[0]
                    for name, bank in self.banks.items()}
        self.duels = self._duels()

    def string(self, bank: str, identifier: int) -> str | None:
        """One string, its glyphs as characters, its line breaks as newlines
        and its page breaks as blank lines. None when the bank has no such
        id, which the script's own ids do reach."""
        start = self.banks[bank].ids.get(identifier)
        if not start:
            return None
        ops = self.ops[bank]
        out: list[str] = []
        at = start
        while at in ops:
            op = ops[at]
            if op.kind == "glyph":
                out.append(op.value if isinstance(op.value, str) else self.glyphs.get(op.value, "?"))
            elif op.kind == "nl":
                out.append("\n")
            elif op.kind == "code" and op.value == "page":
                out.append("\n\n")
            elif op.kind in ("end", "jump"):
                break
            at += op.length
        return "".join(out).strip()

    def duelist(self, identifier: int) -> str:
        return self.string("names", DUELIST_NAME_TEXT_BASE + identifier) or f"duellist {identifier}"

    def _duels(self) -> dict[int, Duel]:
        """Every duel the dialogue starts, by the string it is written in.
        The F8 0D control carries the opponent, the two scenes, the terrain
        and the song; a string that starts more than one duel keeps the
        first, which is the one its scene reaches."""
        bank = self.banks["dialog"]
        memory = self.image.bytes(bank.base, 0x10000)
        starts = sorted((offset, identifier) for identifier, offset in bank.ids.items() if offset)
        positions = [offset for offset, _ in starts]
        duels: dict[int, Duel] = {}
        at = memory.find(DUEL_CONTROL)
        while at >= 0:
            if at + len(DUEL_CONTROL) + DUEL_CONTROL_OPERANDS <= len(memory):
                index = bisect.bisect_right(positions, at) - 1
                if index >= 0:
                    operands = memory[at + 2:at + 2 + DUEL_CONTROL_OPERANDS]
                    duels.setdefault(starts[index][1], Duel(operands[0], operands[1], operands[2],
                                                            operands[3], operands[4] | operands[5] << 8))
            at = memory.find(DUEL_CONTROL, at + 1)
        return duels


# --- names -------------------------------------------------------------

def slug(text: str, words: int = 6) -> str:
    """A name out of a piece of text: its first few words, lower case."""
    cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).split()
    return "-".join(cleaned[:words]) or "unnamed"


class Names:
    """What everything in a listing is called, and the number behind it.

    The duellists, the flags that record beating one, the terrains and the
    dialogue come from the game itself. The pictures, the scene graphics and
    the songs have no name in the game, so they get one here and the number
    stays in the listing's `names:` section, which is the only place a bare
    id appears."""

    KINDS = ("scene", "part", "place", "backdrop", "sprite", "music", "sound", "line", "flag")

    def __init__(self, text: GameText | None = None):
        self.text = text
        self.to_name: dict[tuple[str, int], str] = {}
        self.to_id: dict[tuple[str, str], int] = {}

    # -- binding
    def bind(self, kind: str, identifier: int, name: str) -> str:
        if kind not in self.KINDS:
            raise StoryError(f"{kind} is not something a listing names")
        known = self.to_id.get((kind, name))
        if known is not None and known != identifier:
            raise StoryError(f"{kind} {name} is both {known} and {identifier}")
        self.to_name[(kind, identifier)] = name
        self.to_id[(kind, name)] = identifier
        return name

    def free(self, kind: str, wanted: str) -> str:
        """`wanted`, or it with a number, so that it names one thing only."""
        if (kind, wanted) not in self.to_id:
            return wanted
        for index in range(2, 1000):
            candidate = f"{wanted}-{index}"
            if (kind, candidate) not in self.to_id:
                return candidate
        raise StoryError(f"too many things called {wanted}")

    # -- reading
    def name(self, kind: str, identifier: int) -> str:
        found = self.to_name.get((kind, identifier))
        if found is None:
            raise StoryError(f"{kind} {identifier} has no name")
        return found

    def identifier(self, kind: str, name: str) -> int:
        """The number `name` stands for. A name the `names:` section does not
        bind may still be the raw form it documents (`picture 7`)."""
        found = self.to_id.get((kind, name))
        if found is not None:
            return found
        raw = RAW_FORMS.get(kind)
        if raw:
            match = re.fullmatch(rf"{raw} +(\d+)", name.strip())
            if match:
                return int(match.group(1))
            if kind == "music":
                match = re.fullmatch(r"song +(\d+):(\d+)", name.strip())
                if match:
                    return int(match.group(1)) * 16 + int(match.group(2))
        raise StoryError(f"nothing names the {kind} {name!r}; add it to the names section")

    # -- the flags the game names
    def flag_name(self, flag: int) -> str:
        if flag == FLAG_TOURNAMENT_COMPLETE:
            return "tournament-complete"
        if self.text and FLAG_DUELIST_BEATEN_BASE < flag < FLAG_TOURNAMENT_COMPLETE:
            return "beaten " + slug(self.text.duelist(flag - FLAG_DUELIST_BEATEN_BASE))
        return self.name("flag", flag)

    def flag_id(self, name: str) -> int:
        name = name.strip()
        if name == "tournament-complete":
            return FLAG_TOURNAMENT_COMPLETE
        if name.startswith("beaten "):
            wanted = name[len("beaten "):].strip()
            for duelist in range(1, FLAG_TOURNAMENT_COMPLETE - FLAG_DUELIST_BEATEN_BASE):
                if self.text and slug(self.text.duelist(duelist)) == wanted:
                    return FLAG_DUELIST_BEATEN_BASE + duelist
            raise StoryError(f"no duellist is called {wanted!r}")
        return self.identifier("flag", name)


def name_everything(blocks: list[Block], offsets: list[int], text: GameText) -> Names:
    """Infer scene names from the duel, dialogue, and map flow they contain."""
    names = Names(text)
    backdrop_names: dict[int, str] = {}
    for block in blocks:
        for instruction in block.instructions:
            if instruction.opcode in (1, 4):
                picture = instruction.u16() & 0xFFF
                if picture not in backdrop_names:
                    backdrop_names[picture] = f"backdrop-{len(backdrop_names) + 1}"

    # Scenes a duel sends the player to, won or lost.
    for duel in text.duels.values():
        for scene, prefix in ((duel.win, "beat-"), (duel.lose, "lost-to-")):
            if 0 <= scene < len(offsets) and ("scene", scene) not in names.to_name:
                names.bind("scene", scene, names.free("scene", prefix + slug(text.duelist(duel.opponent))))

    # Scenes whose own dialogue starts a duel.
    for block in blocks:
        for scene in block.scenes:
            if ("scene", scene) in names.to_name:
                continue
            for instruction in block.instructions:
                if instruction.opcode != 2:
                    continue
                duel = text.duels.get(instruction.u16() & 0xFFF)
                if duel:
                    names.bind("scene", scene, names.free("scene", "duel-" + slug(text.duelist(duel.opponent))))
                    break

    # For repeated appearances of the same non-duelling character, keep the
    # latest scene as the canonical `meet-name` and number earlier visits.
    # That makes the final shopkeeper scene 198 `meet-shopkeeper`.
    speaker_scenes: dict[str, list[int]] = {}
    outcome_scenes = {scene for duel in text.duels.values() for scene in (duel.win, duel.lose)}
    for block in blocks:
        sprite = next((instruction for instruction in block.instructions
                       if instruction.opcode == 9), None)
        dialogue_lines = [instruction for instruction in block.instructions
                          if instruction.opcode == 2]
        if not sprite or not dialogue_lines or any(
                text.duels.get(instruction.u16() & 0xFFF) for instruction in dialogue_lines):
            continue
        character_id = sprite.operands[0]
        character = "shopkeeper" if character_id == 8 else character_sheet.NAMES.get(
            character_id, f"character-{character_id:02d}")
        base = "meet-" + slug(character)
        for scene in block.scenes:
            if scene not in outcome_scenes:
                speaker_scenes.setdefault(base, []).append(scene)
    speaker_labels: dict[int, str] = {}
    for base, scene_ids in speaker_scenes.items():
        ordered = sorted(set(scene_ids))
        primary = max(ordered)
        aliases = [scene for scene in ordered if scene != primary]
        for suffix, scene in enumerate(aliases, 1):
            speaker_labels[scene] = f"{base}-{suffix}"
        speaker_labels[primary] = base

    # Name dialogue scenes by the visible character where one is shown. With
    # no sprite, use the backdrop, since the text may only describe an empty
    # location rather than someone the player meets.
    for block in blocks:
        for scene in block.scenes:
            if ("scene", scene) in names.to_name:
                continue
            has_dialogue = any(instruction.opcode == 2 for instruction in block.instructions)
            sprite = next((instruction for instruction in block.instructions
                           if instruction.opcode == 9), None)
            if has_dialogue and sprite:
                character_id = sprite.operands[0]
                character = character_sheet.NAMES.get(character_id, f"character-{character_id:02d}")
                # The campaign calls the Egyptian Card Trader the shopkeeper.
                if character_id == 8:
                    character = "shopkeeper"
                wanted = speaker_labels.get(scene, "meet-" + slug(character))
                names.bind("scene", scene, names.free("scene", wanted))
                continue
            if has_dialogue:
                backdrop = next((instruction for instruction in block.instructions
                                 if instruction.opcode in (1, 4)), None)
                if backdrop:
                    picture = backdrop.u16() & 0xFFF
                    label = backdrop_names.get(picture, "backdrop-unknown")
                    wanted = "dialogue-" + label
                else:
                    wanted = "dialogue-backdrop-unknown"
                names.bind("scene", scene, names.free("scene", wanted))
                continue

            first = block.instructions[0] if block.instructions else None
            if first and first.opcode == 19:
                wanted = "credits"
            elif first and first.opcode == 18:
                wanted = "game-over"
            elif first and first.opcode == 17:
                wanted = "duel-results"
            elif any(instruction.opcode == 13 for instruction in block.instructions):
                # The opening script offers a save before sending the player
                # to the map; describe the scene's role, not just its exit.
                wanted = "campaign-start"
            else:
                map_command = next((instruction for instruction in block.instructions
                                    if instruction.opcode == 8), None)
                if map_command:
                    wanted = f"return-to-place-{map_command.operands[0]}"
                elif any(instruction.opcode == 3 for instruction in block.instructions):
                    # A branch-only scene has no spoken line to use as a name.
                    wanted = f"story-branch-{scene}"
                else:
                    continue
            names.bind("scene", scene, names.free("scene", wanted))

    # A table can contain several scene numbers for one stream. Keep the
    # semantically named entry as the main name, and suffix its aliases in
    # scene-number order (for example, beat-jono-2nd-1 through -4, then the
    # main beat-jono-2nd entry).
    map_arrivals = {place + PLACE_SCENE_OFFSET for place in range(PLACE_COUNT)}
    for block in blocks:
        if len(block.scenes) < 2:
            continue
        scene_ids = sorted(block.scenes)
        mains = [scene for scene in scene_ids
                 if names.name("scene", scene).startswith(("beat-", "lost-to-"))]
        if not mains:
            mains = [scene for scene in scene_ids
                     if names.name("scene", scene) in speaker_labels.values()
                     and names.name("scene", scene) == speaker_labels.get(scene)]
        if not mains:
            mains = [scene for scene in scene_ids if scene in map_arrivals]
        main = mains[0] if mains else scene_ids[0]
        base = names.name("scene", main)
        if not base.startswith(("beat-", "lost-to-", "duel-")) and main != scene_ids[0]:
            # `free` gave the later alias a temporary numeric suffix. Recover
            # the unsuffixed label from the first entry before making the map
            # arrival (or other chosen main entry) canonical.
            base = names.name("scene", scene_ids[0])
        old_names = {scene: names.name("scene", scene) for scene in scene_ids}
        for scene, old_name in old_names.items():
            names.to_name.pop(("scene", scene), None)
            names.to_id.pop(("scene", old_name), None)
        base = names.free("scene", base)
        names.bind("scene", main, base)
        aliases = [scene for scene in scene_ids if scene != main]
        for suffix, scene in enumerate(aliases, 1):
            alias = names.free("scene", f"{base}-{suffix}")
            names.bind("scene", scene, alias)

    for scene in range(len(offsets)):
        if ("scene", scene) not in names.to_name:
            names.bind("scene", scene, names.free("scene", f"scene-{scene}"))

    # A place is named after the scene the player arrives in.
    for place in range(PLACE_COUNT):
        arrival = names.name("scene", place + PLACE_SCENE_OFFSET)
        wanted = arrival[len("duel-"):] if arrival.startswith("duel-") else f"place-{place}"
        names.bind("place", place, names.free("place", wanted))

    # The blocks a jump reaches inside a scene: that scene's name and its
    # place in it, so a diff of one scene stays inside that scene.
    inner = 0
    for block in blocks:
        if block.scenes or not block.entered:
            continue
        owner = _owning_scene(blocks, offsets, block)
        if owner is None:
            inner += 1
            names.bind("part", block.offset, names.free("part", f"part-{inner}"))
        else:
            base = names.name("scene", owner)
            names.bind("part", block.offset, names.free("part", f"{base}.next"))

    # Everything the game does not name, in the order the scenes use it.
    for block in blocks:
        for instruction in block.instructions:
            _name_operands(names, text, instruction)
    return names


def _owning_scene(blocks: list[Block], offsets: list[int], block: Block) -> int | None:
    """The scene whose stream this block continues: the nearest scene start
    before it."""
    best = None
    for scene, offset in enumerate(offsets):
        if offset <= block.offset and (best is None or offset > offsets[best]):
            best = scene
    return best


def _next_name(names: Names, kind: str) -> str:
    """The next free `kind-N`, numbered by how many are named already, so a
    name carries the order the scenes use it in, not an id."""
    return names.free(kind, f"{kind}-{sum(1 for k, _ in names.to_name if k == kind) + 1}")


def _name_line(names: Names, text: GameText, identifier: int) -> None:
    if ("line", identifier) in names.to_name:
        return
    spoken = text.string("dialog", identifier)
    names.bind("line", identifier, names.free("line", slug(spoken)) if spoken else _next_name(names, "line"))


def _name_operands(names: Names, text: GameText, instruction: Instruction) -> None:
    opcode = instruction.opcode
    if opcode in (1, 4):
        picture = instruction.u16() & 0xFFF
        if ("backdrop", picture) not in names.to_name:
            names.bind("backdrop", picture, _next_name(names, "backdrop"))
    elif opcode == 2:
        _name_line(names, text, instruction.u16() & 0xFFF)
    elif opcode == 9:
        graphic = instruction.operands[0]
        if ("sprite", graphic) not in names.to_name:
            names.bind("sprite", graphic, _next_name(names, "sprite"))
    elif opcode == 10:
        flags = instruction.operands[0]
        kind = "sound" if (flags & 0x3F) == 0 and flags & 0x40 else "music"
        if (flags & 0x3F) == 0 or flags & 2:
            identifier = instruction.u16(1)
            if (kind, identifier) not in names.to_name:
                names.bind(kind, identifier, _next_name(names, kind))
    elif opcode == 13:
        _name_line(names, text, instruction.u16())
    elif opcode == 3:
        value = instruction.u16()
        flag = (value & 0x3FFF if value & 0x4000 else value) & 0x7FF
        named = flag == FLAG_TOURNAMENT_COMPLETE or FLAG_DUELIST_BEATEN_BASE < flag < FLAG_TOURNAMENT_COMPLETE
        if not named and ("flag", flag) not in names.to_name:
            names.bind("flag", flag, names.free("flag", f"flag-{flag}"))


# The raw form of each kind, for anything a listing would rather not name.
RAW_FORMS = {"backdrop": "picture", "sprite": "graphic", "music": "song", "sound": "effect",
             "line": "text", "place": "place", "flag": "flag"}


# --- writing a listing --------------------------------------------------

HEADER = """\
# Yu-Gi-Oh! Forbidden Memories story listing (notes/story.md).
# Extracted from the USA disc's campaign script (DATA/WA_MRG.MRG).
#
# The campaign is 199 scenes. A scene's number is the game's own -- saves
# keep it, and the map's places lead to it -- so it stays; everything else
# here is a name, and renaming one renames it everywhere. The `names:`
# section at the end is the only place a bare id appears.
#
# The words under `say` are the lines the game shows. `page` is where the
# player presses to carry on.
"""


def write_listing(bank: bytes, text: GameText) -> str:
    """The whole campaign as a listing."""
    blocks, offsets = disassemble(bank)
    names = name_everything(blocks, offsets, text)
    out = [HEADER, f"scenes {len(offsets)}", ""]
    for block in blocks:
        out.append(_write_block(block, blocks, offsets, names, text))
    out.append(_write_names(blocks, names, text))
    return "\n".join(out)


def _write_block(block: Block, blocks: list[Block], offsets: list[int],
                 names: Names, text: GameText) -> str:
    out = []
    if block.scenes:
        out.append("scene " + ", ".join(f"{names.name('scene', scene)} = {scene}"
                                       for scene in block.scenes) + ":")
    else:
        out.append(f"part {names.name('part', block.offset)}:")
    for instruction in block.instructions:
        out.extend("    " + line for line in _write_instruction(instruction, offsets, names, text))
    last = block.instructions[-1]
    if last.opcode not in ENDS:
        # The stream runs straight on into what follows. Saying so costs no
        # bytes and the assembler checks it, so a block cannot be moved or
        # dropped without the listing complaining.
        carries = last.offset + last.length
        out.append(f"    carry on into {_label(carries, offsets, names)}")
    out.append("")
    return "\n".join(out)


def _label(offset: int, offsets: list[int], names: Names) -> str:
    for scene, at in enumerate(offsets):
        if at == offset:
            return names.name("scene", scene)
    return names.name("part", offset)


def _wait(flags: int, bit: int = 0x80) -> str:
    """Every waiting command spells it the same way."""
    return ", and wait" if flags & bit else ""


def _write_instruction(instruction: Instruction, offsets: list[int],
                       names: Names, text: GameText) -> list[str]:
    opcode = instruction.opcode
    if opcode == 0:
        return ["stop here"]
    if opcode in (1, 4):
        value = instruction.u16()
        word = "backdrop" if opcode == 1 else "stage the backdrop"
        line = f"{word} {names.name('backdrop', value & 0xFFF)}"
        if value & 0x8000:
            line += f" at {instruction.u16(2)}, {instruction.u16(4)}"
        return [line]
    if opcode == 2:
        value = instruction.u16()
        identifier = value & 0xFFF
        line = f"say {names.name('line', identifier)}"
        if value & 0x8000:
            line += ", keeping the box"
        spare = value & 0x7000
        if spare:
            # Bits Script_OpShowDialog masks away. Kept so the bank rebuilds
            # byte for byte; notes/story.md records that nothing reads them.
            line += f", with spare bits {spare >> 12}"
        return [line] + _write_speech(identifier, names, text)
    if opcode == 3:
        value = instruction.u16()
        if value & 0x4000:
            payload = value & 0x3FFF
            word = "forget" if payload & 0x8000 else "remember"
            return [f"{word} {names.flag_name(payload & 0x7FF)}"]
        negated = "not " if value & 0x8000 else ""
        return [f"if {negated}{names.flag_name(value & 0x7FF)}: "
                f"goto {_label(instruction.u16(2), offsets, names)}"]
    if opcode == 5:
        return ["show the backdrop"]
    if opcode == 6:
        return [f"pan to {instruction.u16()}, {instruction.u16(2)} over {instruction.u16(4)} frames"]
    if opcode == 7:
        return ["keep panning"]
    if opcode == 8:
        return [f"go to the map at {names.name('place', instruction.operands[0])}"]
    if opcode == 9:
        flags = instruction.operands[1]
        line = f"sprite {names.name('sprite', instruction.operands[0])}"
        if flags & 0x80:
            line += " in the corner"
        if flags & 15:
            line += f" style {flags & 15}"
        return [line]
    if opcode == 10:
        flags = instruction.operands[0]
        if (flags & 0x3F) == 0:
            kind = "sound" if flags & 0x40 else "music"
            return [f"{kind} {names.name(kind, instruction.u16(1))}{_wait(flags)}"]
        parts = []
        if flags & 1:
            parts.append("play the music that was kept")
        if flags & 2:
            parts.append(f"keep the music {names.name('music', instruction.u16(1))}")
        if flags & 4:
            parts.append("keep the music that is playing")
        return [(" and ".join(parts) or "do nothing") + _wait(flags)]
    if opcode == 11:
        command = instruction.operands[0]
        steps = command & 0x7F
        line = "fade the music out"
        if steps:
            line += f" in {steps} steps"
        return [line + _wait(command)]
    if opcode == 12:
        return [f"goto {_label(instruction.u16(), offsets, names)}"]
    if opcode == 13:
        line = names.name("line", instruction.u16())
        scene = instruction.u16(2)
        continues = names.to_name.get(("scene", scene), str(scene))
        return [f"offer to save, asking {line}, then continue at {continues}"]
    if opcode in (14, 15):
        return [f"unused command {opcode}"]
    if opcode == 16:
        command = instruction.operands[0]
        steps = command & 0x3F
        line = "fade the screen out"
        if steps:
            line += f" in {steps} steps"
        return [line + _wait(command)]
    if opcode == 17:
        return [f"show the duel results, screen {instruction.u16()}"]
    if opcode == 18:
        return ["game over"]
    if opcode == 19:
        return ["roll the credits"]
    if opcode == 20:
        return [f"pause {instruction.u16()} frames"]
    if opcode == 21:
        return [f"if the deck is not ready: goto {_label(instruction.u16(), offsets, names)}"]
    if opcode == 22:
        return ["back to the main menu"]
    raise StoryError(f"no words for command {opcode}")


def _write_speech(identifier: int, names: Names, text: GameText) -> list[str]:
    """The line's words, and the duel it starts, indented under the `say`."""
    out = []
    spoken = text.string("dialog", identifier)
    if spoken:
        for index, page in enumerate(spoken.split("\n\n")):
            if index:
                out.append("    page")
            out.extend('    "%s"' % line.replace('"', '\\"') for line in page.split("\n") if line.strip())
    duel = text.duels.get(identifier)
    if duel:
        song = names.to_name.get(("music", duel.song))
        playing = song or f"song {duel.song >> 4}:{duel.song & 15}"
        terrain = TERRAINS.get(duel.terrain, f"terrain {duel.terrain}")
        out.append(f'    duel "{text.duelist(duel.opponent)}" on {terrain}, playing {playing}')
        for outcome, scene in (("win", duel.win), ("lose", duel.lose)):
            where = names.to_name.get(("scene", scene), str(scene))
            out.append(f"        {outcome}: goto {where}")
    return out


NAME_NOTES = {
    "backdrop": "# The pictures the scenes show. The game gives them no names, so these\n"
                "# are this file's; `picture N` is the id the script carries.",
    "sprite": "# The graphics a scene puts on screen and waits for\n"
              "# (Script_OpShowMenu). Unnamed in the game, named here.",
    "music": "# Songs, as the sound driver numbers them: `song P:T` is package P,\n"
             "# track T (notes/modding.md, \"Audio\").",
    "sound": "# Sound effects, by the sound bank's own number.",
    "line": "# The dialogue each `say` shows, by its place in the text bank. Edit\n"
            "# the words under the `say` itself; this is only which string it is.",
    "place": "# The campaign map's places. The player arrives in the scene 32 past\n"
             "# the place's number.",
    "flag": "# Story flags the scenes read but the game does not name. `beaten <who>`\n"
            "# and `tournament-complete` need no entry here.",
}


def _write_names(blocks: list[Block], names: Names, text: GameText) -> str:
    """The `names:` section: every name this listing invented, and its id."""
    used = collections.defaultdict(list)
    for block in blocks:
        where = (names.name("scene", block.scenes[0]) if block.scenes
                 else names.name("part", block.offset))
        for instruction in block.instructions:
            for kind, identifier in _instruction_names(instruction, names):
                if where not in used[(kind, identifier)]:
                    used[(kind, identifier)].append(where)

    out = ["names:"]
    for kind in ("place", "backdrop", "sprite", "music", "sound", "line", "flag"):
        entries = sorted(((identifier, name) for (k, identifier), name in names.to_name.items()
                          if k == kind), key=lambda pair: pair[0])
        if kind == "flag":
            entries = [(identifier, name) for identifier, name in entries
                       if names.flag_name(identifier) == name]
        if not entries:
            continue
        out.append("")
        out.extend("    " + line for line in NAME_NOTES[kind].split("\n"))
        for identifier, name in entries:
            raw = RAW_FORMS[kind]
            if kind == "music":
                value = f"song {identifier >> 4}:{identifier & 15}"
            elif kind == "place":
                value = str(identifier)
            else:
                value = f"{raw} {identifier}"
            line = f"    {kind} {name} = {value}"
            scenes = used.get((kind, identifier), [])
            if scenes:
                shown = ", ".join(scenes[:3]) + (", ..." if len(scenes) > 3 else "")
                line += f"   # {shown}"
            out.append(line)
    out.append("")
    return "\n".join(out)


def _instruction_names(instruction: Instruction, names: Names) -> list[tuple[str, int]]:
    opcode = instruction.opcode
    if opcode in (1, 4):
        return [("backdrop", instruction.u16() & 0xFFF)]
    if opcode == 2:
        return [("line", instruction.u16() & 0xFFF)]
    if opcode == 9:
        return [("sprite", instruction.operands[0])]
    if opcode == 10:
        flags = instruction.operands[0]
        if (flags & 0x3F) == 0:
            return [("sound" if flags & 0x40 else "music", instruction.u16(1))]
        if flags & 2:
            return [("music", instruction.u16(1))]
        return []
    if opcode == 8:
        return [("place", instruction.operands[0])]
    if opcode == 13:
        return [("line", instruction.u16())]
    if opcode == 3:
        value = instruction.u16()
        flag = (value & 0x3FFF & 0x7FF) if value & 0x4000 else (value & 0x7FF)
        return [("flag", flag)]
    return []


# --- reading a listing --------------------------------------------------

@dataclass
class Statement:
    line: int
    text: str


@dataclass
class SourceBlock:
    line: int
    scenes: list[tuple[str, int]]       # (name, number), empty for a part
    label: str | None                   # a part's name
    statements: list[Statement] = field(default_factory=list)


@dataclass
class Listing:
    scene_count: int
    blocks: list[SourceBlock]
    names: Names


def _strip_comment(line: str) -> str:
    """Everything before an unquoted `#`."""
    quoted = False
    for index, character in enumerate(line):
        if character == '"' and (index == 0 or line[index - 1] != "\\"):
            quoted = not quoted
        elif character == "#" and not quoted:
            return line[:index]
    return line


def parse(source: str, text: GameText | None = None) -> Listing:
    """A listing as blocks of statements, and the names it binds."""
    names = Names(text)
    scene_count = SCENE_COUNT
    blocks: list[SourceBlock] = []
    in_names = False
    for number, raw in enumerate(source.splitlines(), 1):
        body = _strip_comment(raw).rstrip()
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip())
        stripped = body.strip()

        if indent == 0:
            in_names = False
            if stripped.startswith("scenes "):
                scene_count = _number(stripped[len("scenes "):], number)
                continue
            if stripped == "names:":
                in_names = True
                continue
            if stripped.startswith("scene ") and stripped.endswith(":"):
                blocks.append(SourceBlock(number, _parse_scene_header(stripped, number), None))
                continue
            if stripped.startswith("part ") and stripped.endswith(":"):
                blocks.append(SourceBlock(number, [], stripped[len("part "):-1].strip()))
                continue
            raise StoryError(f"line {number}: {stripped!r} is not a scene, a part, or the names section")

        if in_names:
            _parse_name(stripped, names, number)
            continue
        if not blocks:
            raise StoryError(f"line {number}: {stripped!r} comes before any scene")
        if indent <= 4:
            blocks[-1].statements.append(Statement(number, stripped))
        # Deeper lines are a `say`'s own words and its duel, which the text
        # side owns (notes/story.md); the script bank does not carry them.
    for block in blocks:
        for name, scene in block.scenes:
            if not 0 <= scene < scene_count:
                raise StoryError(f"line {block.line}: scene {scene} is past the {scene_count} scenes")
            names.bind("scene", scene, name)
        if block.label:
            names.bind("part", -block.line, block.label)      # parts have no id of their own
    return Listing(scene_count, blocks, names)


def _number(word: str, line: int) -> int:
    word = word.strip()
    if not re.fullmatch(r"\d+", word):
        raise StoryError(f"line {line}: {word!r} is not a whole number")
    return int(word)


def _parse_scene_header(text: str, line: int) -> list[tuple[str, int]]:
    out = []
    for piece in text[len("scene "):-1].split(","):
        if "=" not in piece:
            raise StoryError(f"line {line}: {piece.strip()!r} needs a scene number, as `name = 7`")
        name, value = piece.split("=", 1)
        out.append((name.strip(), _number(value, line)))
    if not out:
        raise StoryError(f"line {line}: a scene needs a name")
    return out


def _parse_name(text: str, names: Names, line: int) -> None:
    match = re.fullmatch(r"(\w+) +(.+?) *= *(.+)", text)
    if not match:
        raise StoryError(f"line {line}: {text!r} is not `kind name = value`")
    kind, name, value = match.group(1), match.group(2).strip(), match.group(3).strip()
    if kind not in RAW_FORMS:
        raise StoryError(f"line {line}: {kind!r} is not something a listing names")
    if kind == "music":
        song = re.fullmatch(r"song +(\d+):(\d+)", value)
        identifier = song and int(song.group(1)) * 16 + int(song.group(2))
        if identifier is None:
            identifier = _number(value.replace(RAW_FORMS[kind], ""), line)
    elif kind == "place":
        identifier = _number(value, line)
    else:
        word = RAW_FORMS[kind]
        if not value.startswith(word):
            raise StoryError(f"line {line}: a {kind} is `{word} <number>`, not {value!r}")
        identifier = _number(value[len(word):], line)
    names.bind(kind, identifier, name)


# --- assembling ---------------------------------------------------------

def assemble(listing: Listing, size: int = CAMPAIGN_SCRIPT_SIZE) -> bytes:
    """The script bank a listing describes."""
    table = listing.scene_count * 2
    encoded: list[tuple[SourceBlock, list[tuple[Statement, bytes, str | None]]]] = []
    at = table
    offsets: dict[str, int] = {}
    for block in listing.blocks:
        for name, _ in block.scenes:
            offsets[name] = at
        if block.label:
            offsets[block.label] = at
        pieces = []
        for statement in block.statements:
            data, target = _encode(statement, listing.names)
            pieces.append((statement, data, target))
            at += len(data)
        encoded.append((block, pieces))
    if at > size:
        raise StoryError(f"the scenes need {at - size} bytes more than the bank's {size}")

    for block, pieces in encoded:
        for statement, data, target in pieces:
            if not statement.text.startswith("carry on into "):
                continue
            wanted = statement.text[len("carry on into "):].strip()
            if wanted not in offsets:
                raise StoryError(f"line {statement.line}: nothing here is called {wanted!r}")
            after = _block_end(encoded, block, table)
            if offsets[wanted] != after:
                raise StoryError(f"line {statement.line}: this carries on into whatever follows it, "
                                 f"which is not {wanted!r}")

    stream = bytearray()
    for block, pieces in encoded:
        for statement, data, target in pieces:
            if target is not None:
                if target not in offsets:
                    raise StoryError(f"line {statement.line}: nothing here is called {target!r}")
                data = data[:-2] + bytes((offsets[target] & 0xFF, offsets[target] >> 8))
            stream += data

    bank = bytearray()
    for scene in range(listing.scene_count):
        name = listing.names.to_name.get(("scene", scene))
        if name is None:
            raise StoryError(f"scene {scene} is not in the listing")
        bank += struct.pack("<H", offsets[name])
    bank += stream
    bank += bytes([FILLER]) * (size - len(bank))
    return bytes(bank)


def _block_end(encoded, block, table: int) -> int:
    """Where the block's bytes stop, which is where the next block starts."""
    at = table
    for candidate, pieces in encoded:
        size = sum(len(data) for _, data, _ in pieces)
        if candidate is block:
            return at + size
        at += size
    raise StoryError("a block vanished while assembling")


def _encode(statement: Statement, names: Names) -> tuple[bytes, str | None]:
    """One statement as bytes. The second value is the label whose offset
    belongs in the last two bytes, once every block's place is known."""
    text = statement.text
    line = statement.line

    def command(opcode: int, *operands: int) -> bytes:
        return bytes((opcode,) + operands)

    def u16(value: int) -> tuple[int, int]:
        return value & 0xFF, (value >> 8) & 0xFF

    def named(kind: str, name: str) -> int:
        try:
            return names.identifier(kind, name)
        except StoryError as error:
            raise StoryError(f"line {line}: {error}") from None

    if text.startswith("carry on into "):
        return b"", None            # checked in assemble(), and no bytes
    if text == "stop here":
        return command(0), None
    if text == "show the backdrop":
        return command(5), None
    if text == "keep panning":
        return command(7), None
    if text == "game over":
        return command(18), None
    if text == "roll the credits":
        return command(19), None
    if text == "back to the main menu":
        return command(22), None
    match = re.fullmatch(r"unused command (14|15)", text)
    if match:
        return command(int(match.group(1))), None

    match = re.fullmatch(r"(backdrop|stage the backdrop) (.+?)(?: at (\d+), *(\d+))?", text)
    if match:
        opcode = 1 if match.group(1) == "backdrop" else 4
        picture = named("backdrop", match.group(2))
        if match.group(3) is None:
            return command(opcode, *u16(picture)), None
        return command(opcode, *u16(picture | 0x8000), *u16(int(match.group(3))),
                       *u16(int(match.group(4)))), None

    match = re.fullmatch(r"say (.+?)(, keeping the box)?(, with spare bits (\d+))?", text)
    if match:
        value = named("line", match.group(1))
        if match.group(2):
            value |= 0x8000
        if match.group(4):
            value |= int(match.group(4)) << 12
        return command(2, *u16(value)), None

    match = re.fullmatch(r"(remember|forget) (.+)", text)
    if match:
        flag = names.flag_id(match.group(2))
        payload = flag | (0x8000 if match.group(1) == "forget" else 0)
        return command(3, *u16((payload & 0x3FFF) | 0x4000)), None

    match = re.fullmatch(r"if (not )?(.+?): *goto (.+)", text)
    if match and not match.group(2).startswith("the deck is not ready"):
        flag = names.flag_id(match.group(2))
        value = flag | (0x8000 if match.group(1) else 0)
        return command(3, *u16(value), 0, 0), match.group(3).strip()

    match = re.fullmatch(r"if the deck is not ready: *goto (.+)", text)
    if match:
        return command(21, 0, 0), match.group(1).strip()

    match = re.fullmatch(r"pan to (\d+), *(\d+) over (\d+) frames", text)
    if match:
        return command(6, *u16(int(match.group(1))), *u16(int(match.group(2))),
                       *u16(int(match.group(3)))), None

    match = re.fullmatch(r"go to the map at (.+)", text)
    if match:
        return command(8, named("place", match.group(1))), None

    match = re.fullmatch(r"sprite (.+?)( in the corner)?( style (\d+))?", text)
    if match:
        flags = (0x80 if match.group(2) else 0) | (int(match.group(4)) if match.group(4) else 0)
        return command(9, named("sprite", match.group(1)), flags), None

    match = re.fullmatch(r"(music|sound) (.+?)(, and wait)?", text)
    if match:
        kind = match.group(1)
        flags = (0x40 if kind == "sound" else 0) | (0x80 if match.group(3) else 0)
        return command(10, flags, *u16(named(kind, match.group(2)))), None

    match = re.fullmatch(r"((?:play the music that was kept|keep the music .+?|"
                         r"keep the music that is playing|do nothing)(?: and .+?)*)(, and wait)?", text)
    if match and ("music" in match.group(1) or match.group(1) == "do nothing"):
        flags = 0x80 if match.group(2) else 0
        kept = None
        for piece in match.group(1).split(" and "):
            piece = piece.strip()
            if piece == "play the music that was kept":
                flags |= 1
            elif piece == "keep the music that is playing":
                flags |= 4
            elif piece.startswith("keep the music "):
                flags |= 2
                kept = named("music", piece[len("keep the music "):])
        if flags & 0x3F:
            if flags & 2:
                return command(10, flags, *u16(kept)), None
            return command(10, flags), None

    match = re.fullmatch(r"fade the (music|screen) out(?: in (\d+) steps)?(, and wait)?", text)
    if match:
        opcode = 11 if match.group(1) == "music" else 16
        steps = int(match.group(2)) if match.group(2) else 0
        limit = 0x7F if opcode == 11 else 0x3F
        if steps > limit:
            raise StoryError(f"line {line}: {steps} steps is more than {limit}")
        return command(opcode, steps | (0x80 if match.group(3) else 0)), None

    match = re.fullmatch(r"goto (.+)", text)
    if match:
        return command(12, 0, 0), match.group(1).strip()

    match = re.fullmatch(r"offer to save, asking (.+?), then continue at (.+)", text)
    if match:
        scene = match.group(2).strip()
        number = int(scene) if re.fullmatch(r"\d+", scene) else named("scene", scene)
        return command(13, *u16(named("line", match.group(1))), *u16(number)), None

    match = re.fullmatch(r"show the duel results, screen (\d+)", text)
    if match:
        return command(17, *u16(int(match.group(1)))), None

    match = re.fullmatch(r"pause (\d+) frames", text)
    if match:
        return command(20, *u16(int(match.group(1)))), None

    raise StoryError(f"line {line}: no command says {text!r}")


# --- the tool -----------------------------------------------------------

def load_game(where: Path | None) -> disc.GameFiles:
    """The disc's two files: the executable for the text, the archive for the
    script bank."""
    if where:
        return disc.load(where)
    found = disc.find_game()
    if not found:
        raise SystemExit("no game files found; name a disc image or a folder with --game")
    return found


def check(files: disc.GameFiles, source: str | None) -> int:
    """Assemble a listing and compare it with the disc's own bank."""
    retail = read_bank(files.wa)
    text = GameText(files.slus)
    if source is None:
        source = write_listing(retail, text)
    listing = parse(source, text)
    built = assemble(listing)
    if built == retail:
        print(f"check: {listing.scene_count} scenes, {len(retail)} bytes, the same as the disc's")
        return 0
    differ = [index for index in range(len(retail)) if built[index] != retail[index]]
    print(f"check: {len(differ)} bytes differ, from {differ[0]:#x}")
    for index in differ[:8]:
        print(f"  {index:#06x}: listing {built[index]:#04x}, disc {retail[index]:#04x}")
    return 1


def patch_archive(archive: bytes, source: str, text: GameText) -> bytes:
    """Return an archive copy with a fully validated campaign listing installed.

    This is deliberately pure: a malformed listing cannot partly overwrite a
    source archive.  ``assemble`` resolves every target and enforces the
    fixed 0x1000-byte bank capacity before this function changes the copy.
    """
    if len(archive) < CAMPAIGN_SCRIPT_AT + CAMPAIGN_SCRIPT_SIZE:
        raise StoryError("WA_MRG.MRG is too short for the campaign script")
    bank = assemble(parse(source, text))
    result = bytearray(archive)
    result[CAMPAIGN_SCRIPT_AT:CAMPAIGN_SCRIPT_AT + CAMPAIGN_SCRIPT_SIZE] = bank
    return bytes(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["extract", "check", "patch"])
    parser.add_argument("--game", type=Path, help="a disc image, or a folder holding SLUS_014.11 "
                                                  "and DATA/WA_MRG.MRG (default: the one in game/)")
    parser.add_argument("-o", "--output", type=Path,
                        help="where to write the listing (or patched WA_MRG.MRG for patch)")
    parser.add_argument("-i", "--input", type=Path,
                        help="the listing to check or patch (default: the disc's own for check)")
    arguments = parser.parse_args(argv)
    files = load_game(arguments.game)
    try:
        if arguments.command == "extract":
            listing = write_listing(read_bank(files.wa), GameText(files.slus))
            if arguments.output:
                arguments.output.write_text(listing, encoding="utf-8")
                print(f"extract: {arguments.output}, {len(listing.splitlines())} lines")
            else:
                sys.stdout.write(listing)
            return 0
        if arguments.command == "patch":
            if arguments.input is None or arguments.output is None:
                raise SystemExit("story patch: -i LISTING and -o NEW_WA_MRG.MRG are required")
            source = arguments.input.read_text(encoding="utf-8")
            result = patch_archive(files.wa, source, GameText(files.slus))
            arguments.output.write_bytes(result)
            print(f"patch: {arguments.output}, {CAMPAIGN_SCRIPT_SIZE} campaign bytes installed")
            return 0
        source = arguments.input.read_text(encoding="utf-8") if arguments.input else None
        return check(files, source)
    except StoryError as error:
        raise SystemExit(f"story: {error}") from None


if __name__ == "__main__":
    sys.exit(main())
