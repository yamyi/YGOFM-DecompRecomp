# CARDS DATA tool

Route: `extend/tools/cardsdata`. Inputs: SLUS_014.11 (accepts `.11`, 1,572,864..3,145,728 bytes)
and an `.xlsx` (up to 20 MB) filled from the template `site/Assets/files/PlantillaData.xlsx`
(header + 722 stock rows, columns `ID NAME ATTACK DEFENDING STAR_ID 1 STAR_ID 2 TYPE_ID LEVEL
ATTR_ID NAME_COLOR_ID`). UI "V.230913", client-side, analytics POST `api/v2/tools` `tipo` 18
(comments box `guia` 28). Script: `scripts/cards_data.py` (dump / apply CSV or the site's xlsx /
verify / restore). Raw notes: `NOTES-raw.md`.

Purpose: bulk-edit every card's ATK, DEF, both Guardian Stars, type, level, attribute and — with
the "Name" / "Name Color" boxes ticked — its name text and name colour, straight into the SLUS.
Rows can cover any subset of the 722 cards; a row with an out-of-range value is skipped; unticked
fields keep the file's current value. The name printed on the card *image* is a separate asset
("Card Spec Mix" tool). Card descriptions are not touched by this tool (the shared mixin has a
writer, see 5).

Status: all three tables located and verified against `~/ygofm-decomp/SLUS_014.11`; consumers
found in the decomp; script tested (values round-trip byte-exact, restore byte-exact). Not built as
a recomp mod (the recomp already parses two of the three tables in `psx_card_db.c`).

## 1. The three per-card tables (all inside the EXE, none in WA_MRG.MRG)

| table | file offset | RAM | verified stock bytes |
|---|---|---|---|
| stats word | `0x1C4A44 + (id-1)*4`, u32 LE | `0x801D4244` `gDuel_adwCardStats` | card 1 `2C F5 05 02` = 0x0205F52C |
| level / attribute | `0x1C5B33 + (id-1)`, u8 | `0x801D5333` (game indexes `0x801D5332[id]`) | cards 1..3 `08 04 24` |
| name offsets | `0x1C6000 + id*2`, u16 | `0x801D5800` `gText_aGlobalOffsets` (1024 entries) | entry 1 = 0x6001 |
| name text | `0x1C0800 + off` | `0x801D0000 + off` | card 1 `2D 0A 0D 01 30 01 ...` = "Blue-eyes ..." |

Stats word (site `readValues`, agrees with the recomp and with the game's own readers):

    bits  0- 8  ATK / 10           (0..511 -> 0..5110)
    bits  9-17  DEF / 10
    bits 18-21  Guardian Star 2    1 Mars 2 Jupiter 3 Saturn 4 Uranus 5 Pluto
    bits 22-25  Guardian Star 1    6 Neptune 7 Mercury 8 Sun 9 Moon 10 Venus   (strings 0x8318..0x8321)
    bits 26-30  type               0 Dragon 1 Spellcaster 2 Zombie 3 Warrior 4 Beast-Warrior 5 Beast
                                   6 Winged Beast 7 Fiend 8 Fairy 9 Insect 10 Dinosaur 11 Reptile
                                   12 Fish 13 Sea Serpent 14 Machine 15 Thunder 16 Aqua 17 Pyro
                                   18 Rock 19 Plant 20 Magic 21 Trap 22 Ritual 23 Equip  (strings 0x8300..)
    Blue-eyes 0x0205F52C: 3000/2500, Sun / Mars, Dragon.   Kuriboh 0x1DCC281E: 300/200, Mercury / Saturn, Fiend.

"Star 1" (bits 22-25) is the one the card viewer prints first (0x80037EA8 `sra v1,v0,22` before
0x80037EF0 `sra v0,v0,18`); the recomp's `psx_card_extend.c` calls bits 18-21 "GS1", i.e. the
opposite label. Level/attribute byte: `attr<<4 | level`, attribute 0 Light 1 Dark 2 Earth 3 Water
4 Fire 5 Wind 6 Magic 7 Trap (Blue-eyes 0x08 = Light 8, Hitotsu-me 0x24 = Earth 4, Puppet Ritual
0x60 = Magic 0).

Name text is the frequency-coded charset (`0x01`=e, `0x02`=t ... see `RAW_ASCII` in
`psx_card_db.c`), 0xFF-terminated; an optional colour prefix `F8 0A cc` (cc = 0 white 1 yellow
2 blue 3 green 4 grey 5 orange 6 red; the site also offers 7 purple) precedes the letters. Stock
card names carry no prefix.

## 2. What the tool writes

Values (`writeValues`, per accepted row): byte0 = atk9 & 0xFF; byte1 = def9%128*2 + atk9>>8;
byte2 = (star1%4)<<6 | star2<<2 | def9>>7; byte3 = type<<2 | star1>>2; level byte = attr<<4 | level.
Validation: ATK/DEF are divided by 10 and must land in 0..511 (so 0..5119, i.e. 5110 max),
stars 0..15, **type 0..63** (a value above 31 sets bit 31), level 0..15, attribute 0..15, id 1..722.
The whole 0..15 star range is accepted although only 1..10 exist.

Names / colours (`writeAllNamesOnSlus`, only when either box is ticked) rebuild the **entire**
global name table and text blob from the decoded texts of: 722 card names, 24 type names
(string ids 768..791), 10 star names (792..801), 40 duelist names (808..847):

    entry 0 -> 0x6000 (an 0xFF byte); strings packed from 0x6001 in that order, each
    len(text.trim()) + (colour ? 3 : 0) + 1 bytes;
    a string that would straddle offset 0x8ACD is moved to start at 0x8ACE;
    a string that would straddle 0x8D9A is moved to 0x9200   (skips the 16 location names 848..863,
                                                             0x8D9A.., and the data up to 0x916E);
    overflow error if the end reaches 0xA004 (RAM 0x801DA004);
    table: 1..722 cards, 723..767 -> 0x6000 (empty), 768..801 types+stars, 802..807 six copies of
           "Dragon", 808..847 duelists, 848..863 untouched, 864..1023 -> the new "Dragon" offset;
    text: optional F8 0A cc, then one byte per character (unknown characters become 0 = space), 0xFF.

Quirks, measured: even with unchanged text the repack is not the stock layout (937 bytes differ)
because the ten star names lose their padding spaces ("Mars   " -> "Mars"; the game pads them to
7 columns) and the 0x8ACD test is off by one — stock card 722 ends exactly at 0x8ACC, the rule
moves it to 0x8ACE and shifts everything after it. All names still decode identically. The decoder
drops bytes it has no glyph for and renders the Greek alpha of "Kuwagata α" (0x55) as "@", which
re-encodes to 0x55 — harmless. Only 50 bytes of a name are read.

## 3. What the game does with it

- **Stats**: read at 64 `lui 0x801D / addiu 0x4244` sites (list in the recomp's
  `psx_card_extend.c`). Key consumers: `Duel_GetBaseCardStat` (0x8002CBF4: field*10 + terrain
  boost, clamp 0..9999), `card_record_fill` (0x800249E0: ATK/DEF*10 into the hand/field record),
  the card viewer's type/star text at 0x80037E64..0x80037F18 (string id `0x8300 + type`,
  `0x8300 + 0x17 + star`), `Duel_CalcGuardianStarMatchup` (0x8002CB80: two star ids -> +500 / -500
  / 0 on the two rings 1-6 and 7-10), the AI opcodes (`AiScript_TestHighStat`, `AiScript_EvaluateFusion`),
  the deck-builder sort. A type >= 20 is "not a monster" everywhere (`sltiu 0x14` style tests).
- **Level / attribute**: exactly one reader, `init_container_entry_objs` 0x80029410
  (`lbu v0, D_801D5332(a0=id)`; `>>4` -> object +0x3B, `&0xF` -> +0x3A). FM has no level or
  attribute rules, so this is display only (the card viewer's stars/attribute line).
- **Names**: `Text_LookupString` (0x8003B744) resolves ids >= 0x8000 through
  `gText_aGlobalOffsets` (0x801D5800) against segment 0x801D0000; a card's name is string
  `0x8000 + id`, types `0x8300 + t`, stars `0x8318 + (s-1)`, duelists `0x8328 + i`, locations
  `0x8350 + i` (F118); indices 864..1023 are filler (0x8ACE = "Dragon"). The renderer
  (`func_80037DA4` / `func_80036C14`) honours `F8` escapes; `F8 0A cc` sets the glyph colour and
  it is sticky for the rest of the widget (see `psx_card_name_color.c`).
- Layout of the stock blob (offsets from 0x801D0000): card names 0x6001..0x8ACC, one pad byte,
  types+stars 0x8ACE..0x8BCF, duelists 0x8BD0..0x8D99, locations 0x8D9A..0x8EA5, more data
  (unknown, non-zero) 0x9004..0x916E, zero from 0x916F. The site's 0xA004 cap therefore leaves
  the region the recomp uses for new-card names (`NAMES_BASE 0x801D9200`) inside its write range.

## 4. Recomp options

1. Startup data patch, all base-EXE: read a CSV (`cards_data.py dump` format) and write the 722
   stats words and level/attr bytes with `psx_mod_write_word/byte` once the table is resident
   (`psx_card_db` probes Kuriboh's word). Order matters: `psx_card_extend.c` copies the stock words
   into its relocated table, so patch before it builds (or patch both copies); call
   `psx_card_db_invalidate()` afterwards.
2. Names: do not repack. Append changed names at the free end of the blob (0x801D916F..0x801DA000,
   ~3.7 KB — shared with `psx_card_extend`'s `NAMES_BASE 0x801D9200`, so allocate from one place)
   and repoint the u16 entry; stock names keep their bytes. Colours: use the existing glyph hook
   (`psx_card_name_color.c`) rather than `F8 0A` prefixes; if prefixes are wanted anyway, write the
   prefixed copy at the end as above.
3. The values are plain data reads, so a "card database" mod can equally replace the readers
   natively (`psx_card_db_stats`) — that is where a wider ATK/DEF range (see `data-x2`) belongs.
4. Note for `psx_card_extend.c`: `AUX_STOCK + (id-1)` reads the previous card's level/attr byte;
   the game uses `0x801D5332 + id`. Kuriboh's clones currently copy card 57's byte.

## 5. Decomp findings (proposed)

- `0x801D5332 D_801D5332` | per-card level/attribute byte table indexed by card id (1-based, so card 1 is at 0x801D5333): low nibble level, high nibble attribute (0 Light 1 Dark 2 Earth 3 Water 4 Fire 5 Wind 6 Magic 7 Trap); only reader 0x80029410 -> object +0x3A / +0x3B | `gCard_abLevelAttr`
- `0x801D4244 gDuel_adwCardStats` | bit layout 0-8 ATK/10, 9-17 DEF/10, 18-21 second Guardian Star, 22-25 first Guardian Star (drawn first by the viewer at 0x80037EA8), 26-30 type; verified on all of cards 1,2,3,58,380,695 | document; star ids 1..10 = strings 0x8318..0x8321
- `0x801D5800 gText_aGlobalOffsets` | 1024 entries: 1..722 card names, 723..767 = 0x6000 (empty string), 768..791 types, 792..801 stars, 802..807 = "Dragon" x6, 808..847 duelists, 848..863 locations, 864..1023 = 0x8ACE filler | document
- text blob | card names end 0x801D8ACC, types/stars 0x801D8ACE..0x801D8BCF, duelists ..0x801D8D99, locations 0x801D8D9A..0x801D8EA5, unknown non-zero data 0x801D9004..0x801D916E, zero to 0x801DA004 | free space for name mods = 0x801D916F..
- description strings | `Text_LookupString` ids >= 0xD000 resolve relative to 0x801C0000 (the table's own segment); card descriptions are entries 0x101..0x3D2 (id 0xD100 + card), texts 0x801C09F5..0x801CD59E, and entry 0x100 = 0x9F4 (empty string) | `gText_aBankOffsets` doubles as the description table; 0x801CD5A0 (recomp reclaimed region) starts right after the last description

## 6. Open questions

- What the non-zero bytes at 0x801D9004..0x801D916E are (the site protects them with the
  0x9200 skip; the recomp's zero-scan says 0x801D916F.. is free).
- Why the site protects offset 0x8ACD (nothing in the decomp references it; stock just has a pad
  byte there).
- Whether the star-name trimming (7-column padding lost) misaligns the viewer's star line.
- The recomp's claim that these tables are "re-streamed from disc per screen": no copy of the
  stats, level/attr or name tables exists anywhere in WA_MRG.MRG (byte search), and the site's
  SLUS-only patch is what its users run, so the EXE copy is authoritative.
- Server side: only the analytics POST.
