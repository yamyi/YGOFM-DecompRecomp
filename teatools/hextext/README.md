# hextext -- "Campaign Editor Studio" (text bank + story script editor)

Route: `extend/tools/hextext`. Inputs: SLUS_014.11 (`.11`, 1,048,576..3,145,728 bytes) and,
optionally, WA_MRG.MRG (`.mrg`, 36,700,160..45,088,768 bytes). Page version V.230825. A hex
editor over the EXE's text bank with a live decoder of the game's text control codes, a pointer
editor for the campaign string table, and (with the WA) a "Campaign Router" that edits the story
bytecode and previews backgrounds/portraits from the WA. Everything is client-side; SAVE SLUS /
SAVE WA download the edited files.
Scripts: `scripts/fmtext.py` (importable codec: charset, encoder, control-code decoder, bank
dump/patch/find), `scripts/campaign_script.py` (story script dumper from WA or disc image).
Raw session notes: `NOTES-raw.md`.

Status: charset extracted from the EXE (not from the site) and cross-verified; control-code
grammar taken from the site and corrected against the EXE's handler tables; script bank located
and parsed; not a mod in itself (it is the toolkit other text mods need).

## 1. What the page edits

| thing | file offset | RAM | notes |
|---|---|---|---|
| text bank | 0x1A0800 + off | `gText_aBank` 0x801B0000 + off | default view 0x1A1A60 = bank +0x1260, 256-byte pages; `move()` lets you page anywhere in 0..0x1D07F0 |
| campaign string pointers | 0x1B1000 + 2*id (250 ids) | 0x801C0800 = `gText_aBankOffsets` + 0x800, i.e. **string ids 1024..1273** | u16 bank offsets; the "R. id" index; 259 entries are non-zero |
| story script (WA) | WA 0xF34000, 4096 B | loaded to 0x801A8000 (F111/F115) | 199 u16 offsets + 3698 B bytecode |
| campaign portraits (WA, preview) | 0xF35000 + (n-1)*2432, CLUT at +2304 | -- | 48x48 8bpp, n = 1..25 = `F6 (0x40+n)` thumbnails; the array ends at 0xF43D80, right before the free-duel portrait file at sector 0x1E88 (F122) |
| backgrounds (WA, preview) | static 0x10FB000 (+CLUT 0x110B000, 67,584 B each); compound 0x1423800/0x144B800 (165,888 B); animated 0x1AC8800/0x1B00800 (231,424 B) | -- | 320x160 8bpp assembled from 128-wide strips |

All writes are plain byte stores into the DataView: letters via the charset, control sequences
via the context menu, pointer edits (`setUint16` at 0x1B1000 + 2*id), WA script rewrite
(`salvarWa`: 199 pointers then the op bytes back to 0xF34000 + 398). When an op is inserted or
resized the page shifts every later pointer/jump by the delta (`fixData`, `fixPointers`), which
is the only "smart" thing it does; text moves (`MOVE BYTES`) shift bytes up to the next FF.

## 2. The charset (from the EXE, `gText_adwGlyphCodeTable` 0x801D9000)

One u32 per glyph index; low 16 bits = the Shift-JIS code the glyph draws (`Text_SjisToGlyphCodes`
0x8003BC40 scans it to encode dynamic text such as the player name). 92 entries, 0x00..0x5B;
0x5C..0xEF unassigned; the order is letter frequency. `fmtext.CHARSET` / `fmtext.SJIS`; the
site's `J` object matches it entry for entry (plus two non-glyph slots 226/239 shown as space).

    00 ' '  01 e  02 t  03 a  04 o  05 i  06 n  07 s  08 r  09 h  0A l  0B .  0C d  0D u  0E m  0F c
    10 g    11 y  12 w  13 f  14 p  15 b  16 k  17 !  18 A  19 v  1A I  1B '  1C T  1D S  1E M  1F ,
    20 D    21 O  22 W  23 H  24 Y  25 E  26 R  27 <<  28 >>  29 G  2A L  2B C  2C N  2D B  2E ?  2F P
    30 -    31 F  32 z  33 K  34 j  35 U  36 x  37 q  38 0  39 V  3A 2  3B J  3C #  3D 1  3E Q  3F Z
    40 "    41 3  42 5  43 &  44 /  45 7  46 X  47 .(mid)  48 :  49 female  4A 4  4B )  4C (  4D male  4E 6
    4F $    50 *  51 >  52 subset  53 superset  54 <  55 alpha  56 +  57 8  58 <-  59 9  5A ->  5B %

Upper 16 bits of each word: `(sheet cell << 4) | attr` -- 0xA0+n for A..Z, 0xC0+n for a..z,
0xE0+n for digits, 0xBA..0xBF for the symbol row, 0 for glyphs drawn straight from the font; not
needed for encoding. Text colour slots: `F8 0A n` or a raw byte 0x80..0x8F -> `D_801D5708[n]`
(F130): 0 white, 1 yellow, 2 blue, 3 green, 4 grey, 5 orange, 6 red, 7 purple (the page's menu
swaps 3/7 relative to the site's own chunk-common table; the duel-result tool's list agrees with
chunk-common).

## 3. Control codes -- what the EXE does

The typewriter `TextBox_BuildStep` (0x800393B0) treats bytes < 0xF0 as glyph indices and jumps
through the 16-entry table at 0x80090F18 for 0xF0..0xFF; `F8` has its own 32-entry table at
0x80090EAC. Stream bytes are read through the record's cursor (`func_80036D3C` = next u16 LE).

| bytes | handler | meaning (verified in the EXE unless marked *site*) |
|---|---|---|
| `F0..F5 xx` | func_80037D2C | 2-byte glyph escape: index `(c-0xF0)<<8 \| xx` (matches `Text_SjisToGlyphCodes`' `0xF0xx` output). Same stub serves `F8 1B..1F`. |
| `F6 id anim` | func_80038EB0 | character/portrait: id < 64 story character (list in `campaign_script.py`), 0x41..0x59 = thumbnail n = id-64; anim *site*: 00/01 slide in L/R, 08/09 appear L/R, 14/15 slide in state 3, 20/21 (de)freeze, 40/41 show state 1/2, 80 slide out, 81/82 out 1/2 |
| `F7 ..` | func_80037D6C | sub-ops *site*: `05 01 id type[ y xlo xhi]` background (type 0 static 1 compound 2 animated, +0x80 = with position), `0F lo hi` text delay in frames (0 = softlock), `0A` wait for background, `0B x x y y d d` background move, `10 hi lo` background effect (2800 earthquake) |
| `F8 sub ..` | func_80038B4C -> table | see below |
| `F9 lo hi [lo hi]` | func_80038D2C | `v = u16`. bit 0x4000: `Library_UpdateCardUsedFlag(v & 0xBFFF)`, 3 bytes (site: "SET/UNSET condition" 0x40xx/0xC0xx). Else `t = u16`; `if Campaign_TestStoryFlag(v)` (bit 0x8000 inverts, F120) jump to bank offset `t`; 5 bytes |
| `FA` | func_80038D14 | page break: wait for X (spawns the press-X cursor, F113) |
| `FB f [b] [ptrs]` | func_80038BF0 | `f` bit 0x08: one extra byte follows; bit 0x80: a u16 list follows and entry `gDialog_bChoice` (0x8009B34D) is taken -> the choice branch (F116: `FA FB 02 <a> FE <b> FE FB 80 u16 u16`); low bits = choice count (`FB 02`) or box style (`FB 53`, F103) |
| `FC lo hi` | append_stream_word_and_advance_field88 | insert (call) the string at bank offset u16, return at its FF. `FC 5A 12` = 0x125A = the 6-byte slot the name-entry screen types the name into (F96/F131) |
| `FD lo hi` | func_80038BA8 | goto bank offset |
| `FE` | func_80038E1C | newline |
| `FF` | func_80038E7C | end (or return from an `FC` insert) |

`F8` sub-ops (table 0x80090EAC; sizes from the site's decoder unless marked):

| sub | bytes | handler | meaning |
|---|---|---|---|
| 00 xx | 3 | 0x80037DA4 | card data field xx (library page) |
| 01 xx | 3 | 0x800380D4 | CR + signed top padding |
| 02 xx | 3 | 0x80038110 | left padding |
| 03 a a a a f | 7 | 0x80038148 | print the value at RAM address (u32 LE) with `f&0xF` digits, `f&0xC0` alignment |
| 04 xx | 3 | 0x800382A8 | font size |
| 06 lo hi | 4 | 0x80038388 | signed left padding |
| 09 | 2 | 0x800383DC | opponent name |
| 0A n | 3 | 0x80038498 | colour slot n (F130) |
| 0B n | 3 | 0x80038094 | icon n |
| 0D 01 opp win lose field mlo mhi | 9 (+FF) | 0x80038530 | **duel**: matched C reads opponent (s8), two u16 (win/lose exit ids), a byte, and derives `D_8009B36A` from the music halfword; ends the string |
| 0E lo hi | 4 | 0x80038690 | play BGM code (see freeduel README for the 57 codes) |
| 10 hi lo [d d] | 4/6 | 0x80038798 | sound effect (big-endian id as the site writes it); if `lo & 0x80` two delay bytes follow |
| 11 xx | 3 | 0x80038800 | stop music (00 fast, 82 medium, 83 slow) |
| 15 xx | 3 | 0x800388D8 | screen effect (91 light in, 90 light out, A1 dark in, A0 dark out) |
| 16 | **2** | 0x800389C4 | clears bit 8 of the box flags (no argument; the site's "F8 16 FF = automatic end" is this op followed by the normal FF) |
| 17 p p ... | 2+2k | 0x800389D8 | jump to `ptr[byte 0x8009B34E]` -- the pointer count is not encoded (string 62 "YOU" uses two: 1P/2P labels, campaign uses four); the site always shows four |
| 18 p p ... | 2+2k | 0x80038A44 | same, indexed by byte 0x8009B355 |
| 19 n | 3 | 0x80038AB0 | unlock duelist n: `Library_UpdateCardUsedFlag(n+0x1F)` and `(n+0x6E0)` -- the free-duel "met" flag `Campaign_TestStoryFlag(0x6E0+id)` (F121) |
| 1A | **2** | 0x80038B08 | delete the choice cursor object, box state 2 (the site does not know it and mis-decodes the next letter) |
| 05 07 08 0C 0F 12 13 14 | ? | 0x80038334 0x800383B0 0x80038070 0x800384E4 0x800386B8 0x80038888/90/98 | exist in the table, not decoded by the site |
| 1B..1F | 2 | stub | consume one byte |

`fmtext.py decode` shows the corrected forms, e.g. string 62 `[JUMP BY 8009B34E 0514 0518]YOU`,
string 245 `[BOX STYLE 53]Your NAME is [COLOUR yellow][INSERT 125A][COLOUR white]-[NL]YES[NL]NO[NL]
[CHOICE TARGETS 1191 118E][CLEAR BOX FLAG 8]`.

## 4. The story script (WA 0xF34000, RAM 0x801A8000)

199 sequences; sequence k starts at `bank + u16[k]` (first = 0x18E, i.e. right after the
table). `Script_RunTick` (0x8002FA54, F111) dispatches the ops; `gScript_pStream` 0x8009B290 is
the cursor and `gScript_wState` 0x8009B2A4 the state. Op shapes as the site parses/edits them:

| op | bytes | meaning (site names) |
|---|---|---|
| `03 flag type lo hi` | 5 | Condition: jump to bank offset if story flag matches |
| `0D 00 00 seq 00` | 5 | Menu: go to sequence `seq` |
| `01 id type` | 3 | Background (type 0/1/2 = static/compound/animated) |
| `0A 00 lo hi` | 4 | Theme: BGM code |
| `0A 40 ..` | 8 | unknown |
| `09 id side` | 3 | Character id at side 00 left / 80 right |
| `02 id type` | 3 | Text: campaign string `id` (index into the 0x801C0800 table -> `gText_aBank`) |
| `0B 00` | 2 | Nothing (padding the editor inserts) |
| `12` / `13` | 1 | Game Over / End |
| `08 xx` | 2 | Exit point |
| `0C lo hi` | 3 | Jump |
| `15 ..` | 3 | unknown |
| `10 82 ..` / `10 81` / `10 xx` | 8 / 2 / 2 | Prologue scene / slow fade-out / unknown |

`campaign_script.py dump disc.bin --slus SLUS_014.11` prints every sequence with the text ids
resolved through the bank. The EXE's 0x801A8000 region is all zero: the bank is disc-loaded, so
an edit must go to WA_MRG.MRG (or be re-applied after the load in the recomp).

## 5. Other reads the page makes (useful offsets)

From chunk-common's `getCardInfo` mixin: card names via `gText_aGlobalOffsets` 0x801D5800 (file
0x1C6000, u16 `off`, string at 0x801D0000 + off, i.e. file 0x1C6000 + off - 0x5800); card
descriptions via the u16 table at 0x801C0200 (file 0x1B0A00; string at 0x801C0000 + off -- note
the different base); duelist names = global ids 808..847; card stats 4 bytes/card at
0x801D4240 (atk/def/gs/type packed) and level/attribute byte at 0x801D5333.

## Recomp options

1. Text edits: the bank is part of the EXE image, so any string edit is a startup byte patch
   (`fmtext.py patch` shows the bytes). Longer strings: move them into free EXE space
   (0x801CB000..0x801D0000 is zero in retail) and repoint the u16 at 0x801C0000 + 2*id.
2. Native replacement is easy because the engine is table-driven: a mod can install its own
   handler in the 0xF0..0xFF table (0x80090F18) or the F8 table (0x80090EAC) -- e.g. a proper
   "insert player name" op, variable-width text, or new colours -- with `psx_mod_write_code_word`
   on the table entries (base EXE data, apply once).
3. Story script: re-write the 4 KiB bank at 0x801A8000 after the campaign loads it (frame hook,
   stock-word check on the first pointer 0x018E), or patch WA_MRG.MRG on disc.
4. A recomp-side name slot that is longer than 5 glyphs needs the `FC 5A 12` inserts to point at
   a bigger buffer (see the memory-card README).

## Decomp findings (proposed)

- `0x80090F18` (16 u32) | control-byte handler table for 0xF0..0xFF used by `TextBox_BuildStep`; `0x80090EAC` (32 u32) = the `F8` sub-op table | `gText_apControlHandlers` / `gText_apF8Handlers`
- `0x80037D2C` | F0..F5 (and F8 1B..1F) handler: 2-byte glyph escape `(c-0xF0)<<8 \| next` | `Text_OpGlyphEscape`
- `0x800389C4` / `0x800389D8` / `0x80038A44` / `0x80038AB0` / `0x80038B08` | F8 16 clear box flag 8 / F8 17 jump by 0x8009B34E / F8 18 jump by 0x8009B355 / F8 19 set story flags 0x1F+n and 0x6E0+n (unlock duelist) / F8 1A close choice cursor | `Text_OpClearFlag8` / `Text_OpJumpBy34E` / `Text_OpJumpBy355` / `Text_OpUnlockDuelist` / `Text_OpCloseChoice`
- `0x80038D2C` | F9: story-flag conditional jump (u16 flag, u16 target) or card-flag flip when bit 0x4000 | `Text_OpIfFlag`
- `0x80038BF0` | FB: box attribute byte, optional value byte (bit 8), choice-target list (bit 0x80) | `Text_OpBoxAttr`
- `append_stream_word_and_advance_field88` | FC = insert sub-string by bank offset | `Text_OpInsert`
- `0x80038BA8` / `0x80038D14` / `0x80038E1C` / `0x80038E7C` | FD goto / FA page wait / FE newline / FF end | `Text_OpGoto` / `Text_OpPageWait` / `Text_OpNewline` / `Text_OpEnd`
- `0x801C0800` | u16 offset table of the campaign strings (= ids 1024..1273 of `gText_aBankOffsets`) | (fact)
- `WA 0xF34000` (sector 0x1E68) | the story script bank loaded to 0x801A8000; 199 u16 + 3698 B | `WA_SECTOR_STORY_SCRIPT`
- `WA 0xF35000` | 25 campaign portraits x 2432 B (48x48 8bpp + 64-entry CLUT), the `F6 0x41+n` thumbnails | (fact)
- `gText_adwGlyphCodeTable` upper halves | `(sheet cell << 4) \| attr` | (fact)

## Open questions

- ~~Byte counts of the F7 sub-ops and of F8 05/07/08/0C/0F/12/13/14 were not read from the handlers.~~
  Read 2026-09-05: F7 xx stores xx to rec+0x51 and the deferred handler (table 0x80090E64) reads
  the operands on the next step: F7 05 = u16 (+ byte and u16 when the u16 has bit 0x8000),
  F7 0A none, F7 0B three u16, F7 0F u16, F7 10 u16 (the site's shapes hold). F8: 05 two bytes,
  07 u16, 08 none, 0C one byte, 0D four bytes + u16 (music id -> D_8009B36A) then mode 3 (duel),
  0F a flag byte + u16 when flags & 0x3F, 12/13 empty stubs, **14 one byte = the map location
  the scene returns to** (func_80038898 -> D_8009B363, mode 5; the overworld overlay's banner
  id is 0x8350 + location, global ids 0x8350..0x835F are the 16 location names). Stock uses
  F8 14 at 0x3F77 / 0x426D (0A Town Plaza) and 0xA3BD (0F Hiding).
- F8 17/18: the real pointer count is whatever the author laid out; the decoder uses a
  proximity heuristic (offsets within +0x400 of the op).
- The site's "SET/UNSET condition" (F9 with 0x40xx/0xC0xx) calls `Library_UpdateCardUsedFlag`;
  what ids < 289 mean there (card flags start at 289) is not established.
- Server side: analytics POST only (`api/v2/tools`, tipo 10).
