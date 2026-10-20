# Memorycard name modifier (service)

Route: `extend/services/memorycard/name` (chunk `js/extend/services/memorycard/name.<hash>.js`).
Input: raw PS1 memory-card image, `.mcr` / `.mem` / `.mcd`, 0..2,097,152 bytes (a real card is
131,072). Rewrites the 6-character player name of a Forbidden Memories save and re-seals the
block with "the CRC bypass method proposed by Yusaku from Neoseeker". The name write is
client-side; the checksum is computed **server-side** (`POST api/v2/tools/crypt`) -- fully
reproduced below from the game's own code, so the script needs no server.
Script: `scripts/mc_name.py` (list / verify / set / seal / restore; validated against a save
written by the game: `verify` reproduces every stored checksum word, `seal` on a stock block is
byte-identical).
Raw session notes: `NOTES-raw.md`.

Status: decoded end to end, including the server part.

## 1. What the page does

1. `FileReader` -> DataView of the card. Directory scan (`ve`): for frames 1..15 at
   `0x80*n + 0x0A` read 19 bytes and look the decimal-concatenated string up in `Knowledge`, a
   table embedded in the page HTML (100 product strings -> mod name/id; e.g.
   `BASLUS-01411-YUGIOH` -> Original, Mod 11/13/15, Wicked, ...; `BASLUS-05511-YUGIOH` -> FM II
   Ultimate; full list in `site/page.html`). Blocks whose string is unknown are shown disabled.
   Icons: 3 frames of 16x16 4bpp at block+0x80 (frame count = `block[2] & 3`), CLUT at +0x60.
2. Name read (`be`): 6 little-endian u16 at `block + 0x60C`; high byte 0x82 -> table 1
   (letters/digits), else table 2 (symbols); 0 -> space.
3. Name write (`Ae`): pad/cut to 6, letters/digits -> `0x8200 | code`, symbols -> `0x8100 | code`,
   space -> 0. That is plain full-width Shift-JIS: `A`=0x8260, `a`=0x8281, `0`=0x824F,
   `+`=0x817B `-`=0x817C `*`=0x8196 `/`=0x815E `&`=0x8195 `$`=0x8190 `%`=0x8193 `!`=0x8149
   `?`=0x8148 `.`=0x8144 `:`=0x8146 -- the same codes as the EXE's glyph table (see hextext).
4. Save: `prepareData` sends 642 bytes from `block + 0x580` (`api/v2/tools/crypt`, tipo 40) and
   the server returns a 16-bit value `c`; `writeData` stores `c` **big-endian** at `block + 0x802`
   and zeroes nine u32 at `block + 0x804..0x827`. Then FileSaver downloads the card.

## 2. The save block and its checksums (from the game)

Block layout (8 KiB; block 1 of the retail save):

    +0x000  PS1 frame header "SC", icon flags, title (SJIS), CLUT +0x60, icon frames +0x80
    +0x200  save struct, 0x680 bytes   (= RAM 0x801D0200; the game keeps the header at 0x801D4000)
    +0x880  byte-for-byte mirror of +0x200..+0x87F (written by the saver, func_8003D03C)

Known fields (block offsets): 0x200 `gDuel_awPlayerDeck` (40 u16), 0x250 `gLibrary_abCardChest`,
0x534 game id (F135), **0x60C player name (6 u16 SJIS)**, 0x618 `gCampaign_abStoryFlags`,
0x698 used-password flags, 0x6F4 `gFreeDuel_dwUnlockedDuelists`, 0x718/0x71A 1P wins/losses,
0x71C per-duelist W/L records (39 x {u16,u16}), 0x7BC `gDuel_awRecentCardDrops`, 0x7DE sound
output type, 0x7E0 `gLibrary_dwStarchips`; 0x600 = 0, 0x604 = save counter, 0x608 = `D_8009B0C4`.

Integrity, all matched C in the decomp: `func_8003CEB8` = CRC-16/XMODEM (poly 0x1021, init 0);
`func_8003CE74` = two-word xorshift PRNG on `D_8009AF64/68`; writer `func_8003CF14` (regions 1-2)
+ `func_8003CFC8` (region 3); verifier `func_8003D174` (called from the load path at 0x8003E694).
Per region: `crc = CRC16(data)`, stored twice as u16, then the PRNG is seeded with
`crc | crc << 16` and its successive outputs are written to the words *below* the slot, highest
address first. Offsets relative to the save struct (block = +0x200):

| region | data | crc u16 x2 | PRNG words (first .. last written) | block offsets |
|---|---|---|---|---|
| 1 | +0x000, 0x340 | +0x37C/+0x37E | +0x378 down to +0x340 (15) | data 0x200..0x53F, words 0x540..0x57B, crc 0x57C |
| 2 | +0x380, 0x06C | +0x3FC/+0x3FE | +0x3F8 down to +0x3EC (4) | data 0x580..0x5EB, words 0x5EC..0x5FB, crc 0x5FC |
| 3 | +0x400, 0x204 | +0x604/+0x606 | +0x624 down to +0x608 (8) | data 0x600..0x803, crc 0x804, words 0x808..0x827 |

The verifier recomputes the CRC of each data window, re-seeds, and compares only the PRNG words
(the stored CRC u16s are not checked). Real save (user's `card1.mcd`): region 1 crc AD75, region 2
crc 0000 (empty data), region 3 crc 3D5B -- `mc_name.py verify` reproduces all 27 words.

PRNG step (`func_8003CE74`), state `a` (D_8009AF64), `b` (D_8009AF68):

    t = ((b << 31) | (a >> 1)) ^ (a << 12);  t ^= t >> 20;  b = b + b + (a & 1);  a = t;  return t;

## 3. Why the "bypass" works

The name is inside region 3's window (0x600..0x803). The site never recomputes anything itself:
the server returns `CRC16(block[0x600..0x801])` and the page writes it big-endian into the
window's last two bytes (0x802..0x803). For CRC-16/XMODEM (zero init, no final xor) appending
the CRC of a message to the message gives a total CRC of 0. So the verifier computes crc = 0,
seeds the PRNG with 0 -- and this xorshift with `a = b = 0` emits zeros forever -- which matches
the eight zeroed words at 0x808..0x827. The zeroed CRC slot 0x804 is never checked. Cost of the
shortcut: bytes 0x802..0x803 (a real field, zero in the retail save) are overwritten, the mirror
at +0x880 goes stale, and region 1/2 must already be valid. `mc_name.py set` does the proper
re-seal by default and offers `--bypass` for site parity.

## 4. Quirks

- The web tool allows 6 characters; the game's name-entry screen stops at 5 (F100: length cap 5,
  and the bank slot the name is typed into, 0x801B125A, is 6 bytes = 5 glyphs + FF). A 6-letter
  name is stored fine, but `Text_SjisToGlyphCodes(0x801B125A, name, 6)` writes 6 glyphs + FF =
  7 bytes into a 6-byte slot, clobbering the first byte of the next string (0x801B1260, the
  campaign script's first text) -- untested in game.
- The game id at 0x534 is derived from the name bytes at name entry (F135:
  `(rand()<<8) | XOR(name[0..11])`); nothing recomputes it later, so the id stays as it was.
- `putQ`/icon decoding and the `caratulas/<id>.jpg` cover art are cosmetic; the images are not
  reachable anonymously (`/Assets/img/*` 302s to `/forbidden_memories`), so none are mirrored.

## Recomp options

1. Not a runtime patch: it is a save editor. For the recomp the equivalent is either an offline
   edit of `card1.mcd` with `mc_name.py`, or a native "rename" hook that writes the six u16 at
   0x801D060C and lets the game's own saver (`func_8003D03C`) seal the block on the next SAVE.
2. If a mod wants a longer name: raise the entry cap in the name-entry module and enlarge the
   6-byte slot at 0x801B125A (move it to reclaimed RAM and point the `FC 5A 12` inserts at it).

## Decomp findings (proposed)

- `0x8003CEB8` | CRC-16/XMODEM over the save regions | `Save_Crc16`
- `0x8003CE74` | xorshift PRNG on `D_8009AF64/68`, seeded with `crc\|crc<<16`, fills/validates the
  integrity words | `Save_NextIntegrityWord`; `D_8009AF64/68` = `gSave_dwRngA/B`
- `0x8003CF14` / `0x8003CFC8` / `0x8003D174` | seal regions 1-2 / region 3 / verify all three
  (windows and word counts as in the table) | `Save_SealMain` / `Save_SealTail` / `Save_Verify`
- `0x8003D03C` | builds the card block: header from 0x801D4000, counter at +0x604, output type at
  +0x7DE, seals, zeroes +0x828..+0x87F, mirrors 0x680 bytes to +0x880 | `Save_BuildBlock`
- `0x801D060C` | player name, 6 x u16 SJIS (game types at most 5) | `gSave_awPlayerName`
- `0x8003E694` | load path calls the verifier; a failed verify is state 4 (`gp+0x4E3`) | (fact)

## Open questions

- Whether the loader falls back to the mirror copy at +0x880 when the primary fails (the verifier
  is called once at 0x8003E694 with `gp+0x4C8`; the retry logic was not traced).
- `Knowledge` keys for some mods are binary garbage (product strings with control bytes) -- the
  site keys by the raw 19 bytes, so those mods' saves are still recognised.
