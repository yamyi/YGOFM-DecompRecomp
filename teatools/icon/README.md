# ICON tool

Route: `extend/tools/icon` (UI version `V.220513`). Input: **SLUS_014.11** (`accepted: ".11"`,
1,902,591..2,097,152 bytes). Optional second input: an image for the icon art (`image/*`, up to
20 MB) which the site draws into a **48x16** canvas and quantises to 16 colours — so an image of any
other size is stretched. (A second, unused `image/bmp` reader with `minsize 246, maxsize 250` is a
leftover single-frame 16x16 4bpp BMP path.)
It edits the **PS1 memory-card save icon** — the 16x16 4bpp, 16-colour, 3-frame animated icon in the
save's title frame — plus the save's Shift-JIS **title** and the **game code** inside the memory-card
file name. All client-side; the patched SLUS is downloaded back.
Script: `scripts/save_icon.py` (dump / import / restore / check). Notes: `NOTES-raw.md`.

Status: fully decoded, all offsets verified against `~/ygofm-decomp/SLUS_014.11`; the icon renders
(three frames of Yugi's face), PNG round-trips pixel-identically, restore is byte-exact; the
consuming code found in the decomp.

**This is the memory-card save icon, not an in-game UI icon sheet.** The 4bpp UI icon sheet the
game draws attribute/type icons and "FIELD"/"MEADOW" labels from lives at WA_MRG `0xB50000`
(256x160, part of the 54-sector boot block loaded by `func_80043960`) and is documented in
[`../image-gamefont/README.md`](../image-gamefont/README.md); nothing in this tool touches it.

## 1. The save title frame

The 0x200-byte block at SLUS file offset `0x1C4800` = RAM `0x801D4000` (decomp `D_801D4000`) is a
verbatim Sony "title frame" (the first block of a PS1 save file). Verified stock bytes:

| offset (file / RAM) | size | field | stock |
|---|---|---|---|
| `0x1C4800` / `0x801D4000` | 2 | magic | `53 43` = `"SC"` |
| `0x1C4802` / `0x801D4002` | 1 | icon flag | `13` = 3 animation frames (`0x11`/`0x12`/`0x13` = 1/2/3) |
| `0x1C4803` / `0x801D4003` | 1 | blocks used | `01` |
| `0x1C4804` / `0x801D4004` | 64 | title, 32 full-width Shift-JIS chars | `82 78 82 95 81 7C ...` = `Ｙｕ−Ｇｉ−Ｏｈ！　Ｆｏｒｂｉｄｄｅｎ　Ｍｅｍｏｒｉｅｓ　　　　` |
| `0x1C4844` / `0x801D4044` | 28 | reserved | all zero |
| `0x1C4860` / `0x801D4060` | 32 | CLUT, 16 x u16 BGR555 LE | `2548 67BF 29F5 14ED 0046 03FF 0235 016E 00A8 0018 082F 1466 1000 11A5 7FFF 0C85` |
| `0x1C4880` / `0x801D4080` | 3 x 128 | icon frames, 16x16 4bpp | frame 0 starts `bb 9a a9 5b b5 a9 bb 6b ...` |

The site's own decimal constants: `1853444` (`0x1C4804`, title), `1853536` (`0x1C4860`, CLUT),
`1853568` (`0x1C4880`, frames), `2950` (`0xB86`, game code).

Pixel format: **4bpp, 8 bytes per row, low nibble = LEFT pixel** (the site's chunk table reads the
three frames as data rows 0..15 / 16..31 / 32..47 of an 8-byte-wide image and paints them into a
48x16 canvas). CLUT: u16 LE BGR555, bit 15 = STP; only `0x0000` is transparent. **Not one stock
entry has STP set** (they are all `0x0xxx`/`0x1xxx`/`0x2xxx`/`0x6xxx`/`0x7FFF`).

The three stock frames are Yugi's face with the eyes changing — a blink loop.

## 2. The memory-card file name

| offset (file / RAM) | size | stock |
|---|---|---|
| `0xB84` / `0x80010384` | 20 | `"BASLUS-01411-YUGIOH\0"` (decomp `D_80010384`) |
| `0xB86` / `0x80010386` | 10 | `"SLUS-01411"` — the only part the site rewrites |

The site's `code` computed property forces the shape: the first four characters are
`("SLUS" + code1).slice(-4)` and the last five are `("00000" + |code2| % 100000).slice(-5)`, joined
with `-`. So it can only ever write `????-#####`, and it does not touch the leading `BA` or the
trailing `-YUGIOH`.

## 3. What the tool writes, and what it does not

`salvar()` -> `setNewGameCode()` (10 bytes at `0xB86`), `setNewGameName()` (64 bytes at `0x1C4804`),
then `download()`. Loading an image goes through `replace()` -> `setNewHeader16` (CLUT) +
`setNewBody16` (three frames).

* `setNewHeader16` writes BGR555 with **STP set on every non-black entry**, and bumps a pure-black
  entry to (1,1,1) first so it becomes `0x8000` (opaque black) rather than `0x0000` (transparent).
  Round-tripping the *stock* icon through the tool therefore changes all 16 CLUT entries
  (`2548` -> `A548`, ...), even though the colours are the same. Harmless for the BIOS card browser,
  which ignores STP, but it means "import the icon you just exported" is not a byte-identical
  operation. `save_icon.py` reproduces this exactly.
* The **icon flag at `0x1C4802` is never written**. A 16x16 (1-frame) PNG is expanded to three
  identical frames instead. `save_icon.py import --frames N` can set the flag if you want a real
  1- or 2-frame icon.
* The character table is ASCII-only (`a-z A-Z 0-9 + - * / & $ % ! ? . :` and space); anything else
  becomes a full-width space `0x8140`. It reproduces the stock title exactly (`-` is `0x817C`,
  `!` is `0x8149`, space `0x8140`).
* The title is always padded/truncated to exactly 32 characters = 64 bytes; the reserved 28 bytes at
  `+0x44` are never touched.
* The site stretches whatever image you give it into 48x16. `save_icon.py import` instead demands a
  16x16 / 32x16 / 48x16 PNG and repeats the last frame when fewer than three are supplied — the only
  deliberate behavioural difference from the web tool.

## 4. What the game does with it

`D_801D4000` is the **save-file header template**, copied verbatim into the save staging buffer just
before the card write. In `func_8003E1D4` (the "create the save file" phase; `$gp` = 0x8009B000):

```
8003E20C  lui   $v0, %hi(D_80010384)
8003E210  addiu $s0, $v0, %lo(D_80010384)     ; s0 = "BASLUS-01411-YUGIOH"
8003E214  jal   func_80044CD4                 ; (a0 = s0)  look the file up on the card
8003E218  addu  $a0, $s0, $zero
...
8003E23C  lui   $a0, 0x8030                   ; a0 = 0x80300000  (save staging buffer)
8003E240  lui   $a1, %hi(D_801D4000)
8003E244  addiu $a1, $a1, %lo(D_801D4000)
8003E248  jal   backward_word_copy_with_tail_dispatch  ; = memcpy, 0x800356A0
8003E24C  addiu $a2, $zero, 0x200             ;   0x200 bytes  <-- the whole title frame
8003E250  lui   $a0, 0x8030
8003E254  ori   $a0, $a0, 0x0200              ; 0x80300200
8003E258  addiu $a1, $zero, 0x86
8003E25C  jal   func_80035748                 ; = word-fill memset
8003E260  addiu $a2, $zero, 0x800             ;   0x800 bytes of 0x86 = "empty save" filler
8003E264  addu  $a0, $s5, $zero               ; port
8003E268  addu  $a1, $s0, $zero               ; name
8003E26C  lui   $a2, 0x8030                   ; source = 0x80300000
8003E270  addu  $a3, $zero, $zero
8003E274  addiu $v0, $zero, 0xA00             ; length = 0xA00
8003E278  jal   func_800442E4
8003E27C  sw    $v0, 0x10($sp)
```

`func_800442E4` builds the card path with `sprintf(D_800F2B00, "bu%02X:%s", port, name)` — the
format string is `D_80010538` (file `0xD38`) — and hands it to the BIOS card API
(`_card_info` / `MemCard*` at 0x8008B7B0..0x8008CF00). So the whole 0x200-byte block, icon and title
and all, is written to the memory card unchanged.

`D_801D4000` is used a second time as an in-RAM template: `func_8003D03C` (`src/func_8003D03C.c`,
matched C) does `backward_word_copy_with_tail_dispatch(arg0, D_801D4000, 0x200)` (the same 0x800356A0 memcpy) to seed the head of
a fresh save/duel-side record before filling in the turn counter and the sub-objects. Nothing reads
the icon pixels back, and nothing validates the magic or the flag inside the game — only the
console's BIOS card browser does.

**Consequences**

* Card-browser only: the icon and title are invisible during play. The game never re-reads them.
* Changing the file name changes the save slot identity: an EXE patched to `BASLUS-99999-YUGIOH`
  cannot see saves made by the stock EXE, and vice versa. `func_80044CD4` looks up the name
  verbatim, so this is a hard save-incompatibility switch (useful for a mod that wants its own slot).
* The strings `"Make File\n"` (`0xB98` / `0x80010398`) and `"Fail File\n"` (`0xBA4` /
  `0x800103A4`) sit just after the name and are the debug prints of the same routine.

## 5. Recomp options

* **Data patch, once at startup.** All of it is base-EXE data, never re-streamed from disc, so a
  single `PSX_MOD_CONSTRUCTOR` that writes the title frame (`0x801D4000`, 0x200 bytes) and the file
  name (`0x80010384`, 20 bytes) is enough. Use `psx_mod_write_byte`; no frame hook needed.
* **Icon art from a host file.** Convert a 48x16 (or 16x16) RGBA PNG at build time with
  `scripts/save_icon.py`, or at runtime: quantise to 16 colours, write 16 u16 BGR555 at
  `0x801D4060` and 3 x 128 bytes at `0x801D4080`. Remember the nibble order (low nibble = left).
* **Set the frame count too** (`0x801D4002` = `0x10 | frames`), which the web tool never does — a
  static icon should be `0x11`, not three copies of the same frame.
* **Save-slot namespacing.** If the recomp ever ships mod-specific saves, patching
  `0x80010384` (and only the 10 bytes at `0x80010386`, to keep the `BA`/`-YUGIOH` shape the BIOS
  expects) is the whole mechanism; `func_800442E4`'s `"bu%02X:%s"` does the rest.
* A native replacement is not worth it: there is no drawing code to replace, just bytes.

## 6. Decomp findings (proposed)

- `0x801D4000` (file `0x1C4800`, 0x200 B) | PS1 memory-card **save title frame** template: `"SC"`, icon flag `0x13` (3 frames), 1 block, 64-byte full-width Shift-JIS title `Ｙｕ−Ｇｉ−Ｏｈ！　Ｆｏｒｂｉｄｄｅｎ　Ｍｅｍｏｒｉｅｓ`, 28 reserved zeros, 16 x u16 BGR555 CLUT at `+0x60`, 3 x 128-byte 16x16 4bpp icon frames at `+0x80`; copied to the save staging buffer at `0x80300000` by `func_8003E1D4` and used as a record template by `func_8003D03C` | `gSave_sTitleFrame` (currently `D_801D4000`)
- `0x8003E1D4` | memory-card save-file creation phase: looks the file up by name, `memcpy(0x80300000, D_801D4000, 0x200)`, `memset(0x80300200, 0x86, 0x800)`, then writes `0xA00` bytes via `func_800442E4`; drives the `0x4C7($gp)` / `0x4C4($gp)` state and status bits | `MemCard_CreateSaveFile`
- `0x800442E4` | `sprintf(D_800F2B00, D_80010538 /* "bu%02X:%s" */, port, name)` then `func_80043D48` + `_card_info` | `MemCard_OpenPath`
- `0x80044CD4` | called with `a0 = D_80010384` before the write; returns < 0 on failure (`0x4C7($gp)` = 0xA) | `MemCard_FindFile`
- `0x80010384` (file `0xB84`, 20 B) | memory-card file name `"BASLUS-01411-YUGIOH"`; `0x80010398` `"Make File\n"`, `0x800103A4` `"Fail File\n"`, `0x80010538` `"bu%02X:%s"` | `gMemCard_szFileName`, `gMemCard_szPathFmt`
- `0x800356A0` `backward_word_copy_with_tail_dispatch` / `0x80035748` `func_80035748` | already-named `memcpy` / word-fill `memset`; the save path uses both | (facts, confirms the existing names)

## 7. Open questions

* The 0x800 bytes of `0x86` written after the header, and the `0xA00` total length, imply the save
  payload is `0x800` bytes plus a `0x200` header; the actual save layout (what overwrites the `0x86`
  filler) was not chased — that belongs to whichever routine fills `0x80300200` before a real save.
* `func_8003D03C`'s use of the same 0x200 bytes as a *record* template is odd (it seeds a duel-side
  object with the icon bytes, then overwrites most of it). Whether any of those bytes survive into
  gameplay state was not checked; if they do, editing the icon could in principle perturb it.
* The site does nothing server-side beyond the shared `api/v2/tools` usage counter and the comments
  box; the whole edit is in the browser.
