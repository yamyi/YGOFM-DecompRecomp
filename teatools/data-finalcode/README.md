# Custom Final Code tool

Route: `extend/tools/data/finalcode` (V.251103). Input: SLUS_014.11 (`.11`, drag-and-drop
reader, no size check). Client-side only.

Purpose: edits the five 8-digit "SECRET NO." codes the game prints after the credits, one
digit box per position (5 x 8 inputs), and downloads the SLUS back.

Status: decoded, stock bytes verified, consumer disassembled. Script:
`scripts/final_code.py` (inspect / apply / restore; restore is byte-exact).

## 1. The data

| | |
|---|---|
| file offset | 0x81350 (20 B) |
| RAM | 0x80090B50 (`D_80090B50`), just before the mode-handler pointer table `D_80090B64` |
| layout | 5 x { u16 first four digits, u16 last four digits }, little-endian |
| stock words | `FA21 FF15` `B80E DA24` `931C 980E` `4824 1719` `D114 6E1D` |
| stock codes | 86985631, 37689434, 73153736, 92886423, 53297534 |

The site reads `getUint16(addr + 4*i)` / `+2`, shows the two halves zero-padded to four
digits each, and writes back `1000*d0+100*d1+10*d2+d3` and the same for the low half.
A half can be at most 9999, so every 8-digit number is representable.

## 2. What the game does with it

`Main_RunCredits` (0x8002DA1C), state 1 first entry (0x8002DB18..0x8002DBA0):

    8002DB24  lw   v1, D_801D0534        ; save "game id": (rand()<<8) | XOR(name), F135
    8002DB28  multu v1, 0xCCCCCCCD ; ... ; a2 = v1 % 5
    8002DB5C  la   v0, D_80090B50
    8002DB6C  lhu  v0, 0(v0 + 4*a2) ; sw v0, D_801D5608     ; text argument 0
    8002DB78  lhu  v1, 2(...)       ; sw v1, D_801D5608+4   ; text argument 1
    8002DB9C  jal  TextBox_CreateFlagged(0, 0x23, 0x10, 0x70, 0x120, 0x20, 8)

String 0x23 of `gText_aBank` is `SECRET NO. <arg0><arg1>` (bytes
`35 1d 25 2b 26 25 1c 00 2c 21 0b 00 f8 03 08 56 1d 80 c4 f8 03 0c 56 1d 80 c4 ff`), so the
code is chosen per save file (game id mod 5) and printed as two numbers. Nothing else in
the EXE references the table; the code has no in-game consumer (its purpose was outside the game, presumably a
promotional/mail-in number), so any 8-digit values are safe.

Quirk: whether a half below 1000 prints with leading zeros depends on the text engine's
number insert, not on the tool - untested.

## 3. Recomp options

Base-EXE data, so a one-time write at startup is enough:
`psx_mod_write_word(0x80090B50 + 4*i, (lo << 16) | hi)` for i = 0..4, where `hi` = first
four digits and `lo` = last four. A more interesting mod: hook 0x8002DB6C and compute the
two halves from the save (name hash, play time, card count) so every player gets a
distinct, verifiable code; or point the two text arguments at anything you like since
`D_801D5608`/`+4` are plain u32 text parameters.

## 4. Decomp findings (proposed)

- 0x80090B50 | 5 x (u16, u16) "SECRET NO." credit codes, indexed by `D_801D0534 % 5` in `Main_RunCredits`, printed through string 0x23 with `D_801D5608`/`+4` as arguments | `gCredits_awSecretNumbers`
- 0x801D0534 | consumed as the per-save id for the credits code choice (writer: name-entry main, F135) | `gLibrary_dwGameID`
- 0x8002DB18..0x8002DBA0 | credits state 1: pick + show the secret number text box | description for `Main_RunCredits`

## 5. Open questions

- Number-insert formatting (zero padding) of the text engine.
- Server side: `POST api/v2/tools` logs the download and then triggers the save; nothing
  else is remote.
