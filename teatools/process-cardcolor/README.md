# CARD COLOR tool

Route: `extend/tools/process/cardcolor`. UI "V.260709", component `ProcessCardColor`.
Inputs: **SLUS_014.11** (`.11`, 1,782,579..2,097,152 bytes) **and WA_MRG.MRG** (`.mrg`,
36,700,160..45,088,768 bytes); both are edited and both can be downloaded. Optional
`site/Assets/files/CardColorTemplate.xlsx` for bulk import (column A = card id 1..722, column B =
colour slot). Analytics POST `api/v2/tools` `tipo` 23 (comments box `guia` 33).
Script: `scripts/card_color.py` (inspect / apply / restore on a SLUS copy, plus palette
export / import / copy-default on a WA copy). Patch blobs + disassembly: `patch/`.
Raw notes: `NOTES-raw.md`.

Purpose: in stock the colour of a card's frame is derived from its **card type** (monster / magic /
trap / ritual). This tool adds a per-card "colour slot" table so any card can use any of 7 frame
colours, and lets you repaint the 7 palettes in WA_MRG.MRG.

Status: both the current ("v2") and the previous ("v1") code layouts are decoded and verified against
the stock EXE; the default table the tool generates is proven to reproduce stock rendering exactly at
all three consumers; `card_color.py` round-trips byte-for-byte. Not yet built as a recomp mod.

## 1. What it writes — SLUS_014.11 (current layout)

| file offset | RAM | size | contents |
|---|---|---|---|
| 0x2950 | 0x80012150 | 361 | the colour table: one **nibble pair per two cards** |
| 0x2AC0 | 0x800122C0 | 176 | two code stubs (44 words) |
| 0x73BC | 0x80016BBC | 8 | `j 0x80012300` + `nop` |
| 0x19C0C | 0x8002940C | 8 | `j 0x800122C0` + `addiu s3, a0, -1` |
| 0x1CA90 | 0x8002C290 | 112 | rewritten inner loop (28 words) |

Table encoding (`getInfo` / `setInfo`): byte `n` at 0x80012150 holds card `2n+1` in the **high**
nibble and card `2n+2` in the low nibble, n = 0..360 (722 cards). Slot values 0..7 are what the UI
offers ("COLOR DEFAULT" .. "COLOR 7"); the xlsx importer accepts 0..15 and the packing allows it,
but only 7 palettes exist.

**Where the new bytes go: on top of PsyQ debug strings.** 0x80012150..0x800122B8 (table) and
0x800122C0..0x8001236F (code) both land in the libgpu string block. The stock 544 bytes at file
0x2950 are the libgpu RCS id and its printf templates:

    ".c,v 1.140 1998/01/12 07:52:27 noda Exp yos $"  "ResetGraph:jtb=%08x,env=%08x\n"
    "ResetGraph(%d)...\n"  "SetGraphDebug:level:%d,type:%d reverse:%d\n"  "SetGrapQue(%d)...\n"
    "DrawSyncCallback(%08x)...\n"  "SetDispMask(%d)...\n"  "DrawSync(%d)...\n"
    "%s:bad RECT"  "(%d,%d)-(%d,%d)\n"  "%s:"  "ClearImage"  "ClearImage2"  "LoadImage"
    "StoreImage"  "MoveImage"  "ClearOTag(%08x,%d)...\n"  "ClearOTagR(%08x,%d)...\n"
    "DrawOTag(%08x)...\n"  "PutDrawEnv(%08x)...\n"  "DrawOTagEnv(%08x,&08x)...\n"
    "PutDispEnv(%08x)...\n"  "GPU timeout:que=%d,stat=%08x,chcr=%08x,madr=%08x\n"  "LoadImage2"

None of these are printed by the retail build. `checkSuitableArea()` only validates the 160 stock
bytes at 0x2AC0 (plus the three other hook sites) before allowing a patch — the 361 table bytes at
0x2950 are overwritten with no check at all. Cute detail: the code stub deliberately leaves the eight
bytes at 0x800122F8 (`"OTagEnv("`) intact because they fall in a gap between the two stubs.

## 2. What it writes — WA_MRG.MRG (the palettes)

    palette k (k = 0..6, "COLOR 1".."COLOR 7")   WA 0xB84000 + 512*k
    mirrored to 10 copies at + 0, 481280, 962560, 1443840, 1925120, 2406400, 2887680,
                                3684352, 4409344, 5658624

The editor (`ColorToneEditor`) reads/writes the **first 72 entries** (144 bytes) of each block as
15-bit BGR555 with the top bit as the semi-transparency/mask flag, applies HSL tone shifts, and
writes the result into all 10 copies. "RESET PALETTE" restores the 144 bytes it backed up on load;
"COPY DEFAULT" copies the whole 512-byte block of colour 1 into colour 7 in all 10 copies.

Stock facts, measured on the US disc:

- colours 1..6 are populated (~427-469 non-zero bytes each); **colour 7 is entirely zero** — that is
  why the tool ships the "COPY DEFAULT" button, and why the code special-cases slot 6 (§4);
- colours 1, 3, 4, 5, 6 and 7 are identical across all 10 copies; **colour 2 is not** (the magic /
  equip frame differs per package).

## 3. The three consumers and the stock rule they replace

All three derive a 0..3 "slot" from the card type in stock, using the same numbering the tool then
generalises to 0..7. Card type = bits 26-31 of `gDuel_adwCardStats[id-1]` (0x801D4244); the stock
code masks it with 0x1F, i.e. it only reads 5 of the 6 bits. Types: 20 Magic, 21 Trap, 22 Ritual,
23 Equip, everything below 20 is a monster family.

| consumer | field | stock values | patched |
|---|---|---|---|
| `init_container_entry_objs` 0x800291E0 (big card) | `s3`, later used as sprite id `s3 + 8` | 0x100 monster, 0x101 magic/equip, 0x102 trap, 0x103 ritual | `0x100 + slot` |
| `func_80016784` 0x80016784 (in-duel small card) | scratchpad packet 0x1F800320 `+0x12` | 241 + 0/1/2/3 (same order) | `241 + slot` |
| `func_8002BFCC` 0x8002BFCC (library card grid) | per-card u16 at `a0 + 0x54`, stride 4 | 0x160 / 0x170 / 0x180 / 0x190 | `0x160 + 16*slot` |

So `slot = 0` monster, `1` magic, `2` trap, `3` ritual, `1` equip is exactly stock — and that is what
`generateData()` seeds on a fresh apply (`{20:1, 21:2, 22:3, 23:1}`, everything else 0). Verified:
`card_color.py apply` on the stock EXE produces 621 slot-0 cards, 67 slot-1 (magic + equip), 10
slot-2 (traps, ids 681-690) and 24 slot-3 (rituals).

### 3a. `init_container_entry_objs` (big card), hook at 0x8002940C

Stock:

    800292D4  sra v0, v0, 26 ; andi s0, v0, 0x1F      ; card type -> s0, also stored at obj+0x68
    800292E0  beq s0, 0x15 -> .L80029348   s3 = 0x102, s0 = 1        (trap)
    800292EC  if (s0 <  0x16):  beq s0,0x14 -> .L8002933C s3 = 0x101 (magic)
    80029304  if (s0 >= 0x16):  beq s0,0x16 -> .L80029320 s3 = 0x103 (ritual)
                                beq s0,0x17 -> .L8002932C obj[0x5F] += 0x20, then s3 = 0x101 (equip)
    800293FC  .. default path (monsters): s3 = 0x100 ; s0 = 0
    8002940C  lui v1, %hi(gDuel_abCardLevelAttr)     <-- HOOK (stock `1d 80 03 3c` `32 53 63 24`)
    80029410  addiu v1, v1, %lo(...)
    80029414  addu v1, a0, v1 ; lbu -> obj+0x3B = attribute, obj+0x3A = level
    ...
    8002947C  addiu v0, s3, 8 ; sw v0, 0x1C(sp)      ; the sprite id actually used

Patched: `j 0x800122C0` with `addiu s3, a0, -1` in the delay slot, and the stub at 0x800122C0 is

    800122C0  srl   s3, s3, 1                ; (id-1) / 2
    800122C4  lui   v0, 0x8001
    800122C8  addiu v0, v0, 0x2150           ; the nibble table
    800122CC  addu  v0, v0, s3
    800122D0  lb    v0, 0(v0)
    800122D4  andi  s3, a0, 1                ; odd id -> high nibble
    800122D8  andi  v0, v0, 0xFF
    800122DC  beqz  s3, 800122E8
    800122E0   andi s3, v0, 0xF
    800122E4  srl   s3, v0, 4
    800122E8  addiu s3, s3, 0x100            ; frame id = 0x100 + slot
    800122EC  lui   v1, 0x801D
    800122F0  j     0x80029414               ; rejoin, with
    800122F4   addiu v1, v1, 0x5332          ; the displaced %lo of gDuel_abCardLevelAttr

Because the hook is at the **shared tail** (0x8002940C), every card reaches it and the per-type side
effects (the `obj+0x5F` bump for equip, the layout fields on the default path) still follow the real
card type — only the frame id is redirected.

### 3b. `func_80016784` (in-duel small card), hook at 0x80016BBC

`s1` is the scratchpad GPU packet at 0x1F800320. It is seeded at 0x800168D8 with
`sw 0x00F10100, 0x10(s1)` — i.e. `+0x10 = 0x0100`, `+0x12 = 0x00F1` (241) — and the type dispatch at
0x800169E4 (`lbu v1, 0x68(s6)`, the card type stored by `init_container_entry_objs`) then adds to
`+0x12` after drawing:

    type 0x14 magic  -> .L80016A28                    +0x12 += 1
    type 0x15 trap   -> .L80016A54 (obj+0xE = 0x40)   +0x12 += 2
    type 0x16 ritual -> .L80016A88 (obj+0xE = 0x60)   +0x12 += 3
    type 0x17 equip  -> obj+0xE = 0x20, then A28      +0x12 += 1
    monsters         -> .L80016AC0 / .L80016ABC       (no change, stays 241)
    all paths merge at .L80016BBC                     <-- HOOK

Stock at 0x80016BBC is `lui a0, 0x6666` / `li v0, 0xE` (the start of a divide-by-10 magic constant
used a few instructions later). The tool replaces both with `j 0x80012300` + `nop`, and the stub at
0x80012300 re-issues them before jumping back to 0x80016BC4:

    80012300  lw   v0, 0x28(sp)   ; the D_801A7AD8 record
    80012308  lhu  v0, 0xC(v0)    ; its card id
    80012304/0C  v1 = 0x80012150 + (id-1)/2 ; lbu ; nibble select -> v0 = slot
    80012334  slti a0, v0, 6 ; bnez a0, 80012354          ; slot < 6 -> normal
    80012340  lui  v0, 0xF1 ; ori v0, 0x180
    80012348  sw   v0, 0x10(s1)   ; slot >= 6: force the pair to (0x0180, 0x00F1)
    80012350  li   v0, 0
    80012354  li   a0, 241 ; addu v1, v0, a0 ; sh v1, 0x12(s1)   ; = 241 + slot
    80012360  lui  a0, 0x6666     ; the two displaced stock instructions
    80012364  li   v0, 0xE
    80012368  j    0x80016BC4 ; nop

The `slot >= 6` branch is why colour 7 is special: its palette is blank in stock, so the tool falls
back to CLUT row 241 with a different `+0x10` half (0x180 instead of 0x100).

### 3c. `func_8002BFCC` (library card grid), 0x8002C290 rewritten in place

Stock is a 723-iteration loop that reads each card's stats, masks the type with 0x1F and writes
`a0 + 0x54` (u16, stride 4) with 0x160 / 0x170 / 0x180 / 0x190. The patch keeps the loop skeleton and
replaces the type decode with a nibble-table lookup:

    8002C290  lui v0, 0x8001 ; addiu v0, v0, 0x2150      ; once, before the loop
    8002C298 .loop:  sb zero, 0x56(a0) ; sh zero, 0x54(s5)
              s1 = tbl[(s3-1)/2] ; s2 = nibble(s3)       ; s3 = card id, 1..722
              slti s1, s2, 6 ; bnez s1, +2 ; nop ; nop   ; (dead check: both paths converge)
    8002C2D0  sll s2, s2, 4 ; li s1, 0x160 ; addu s1, s1, s2
    8002C2DC  sh  s1, 0x54(a0)                           ; = 0x160 + 16*slot
    8002C2E0  addiu a0,a0,4 ; addiu s3,s3,1 ; slti s1,s3,723 ; bnez s1,.loop ; addiu a1,a1,4

The loop-back target moved from 0x8002C290 to 0x8002C298 so the pointer setup runs once. The trailing
three words of the 112-byte blob are zeros (`nop`), overwriting the stock loop tail. `a1` is still
advanced although nothing reads it any more.

## 4. The previous layout ("v1") and the migration

Older patched files carry a different arrangement, which the tool detects (`checkForOldCode`) and
migrates (`generateData` when `itsNeedMigrate`, then the `Ke` byte set):

| | v1 | v2 |
|---|---|---|
| table | 0x1CB624 -> RAM 0x801DAE24 | 0x2950 -> 0x80012150 |
| big-card hook | 0x19BFC -> **0x800293FC**, `j 0x801DADE0` + `addiu s3,a0,-1` | 0x19C0C -> 0x8002940C |
| big-card stub | 0x1CB5E0 -> 0x801DADE0, 68 bytes | inside 0x800122C0 |
| small-card hook | 0x73AC -> **0x80016BAC**, `j 0x801DAF90` (no delay-slot fix-up) | 0x73BC -> 0x80016BBC |
| small-card stub | 0x1CB790 -> 0x801DAF90, 124 bytes | 0x80012300 |
| library grid | not patched at all | 0x8002C290 |

The v1 stubs lived at 0x801DADE0/0x801DAF90, another zero-filled hole in the EXE image (verified
all-zero in stock). **v1 had a real bug that v2 fixes**: its big-card hook sat at 0x800293FC, which is
only on the *default* (monster) path — the four special card types jump straight to 0x8002940C and
never reach it — so under v1 you could only recolour cards whose real type was a monster type.
Migration moves the 361 table bytes to the new home, zeroes the old table and both old stubs, and
restores the two displaced stock instructions (`addiu v1,v1,-8` at 0x80016BAC; `li s3,0x100` /
`move s0,zero` at 0x800293FC).

## 5. Recomp options

1. **Native, no code patch.** All three consumers read a value derived from the card type. Hook the
   three sites (0x8002940C, the `.L80016BBC` merge, and the `func_8002BFCC` loop) — or better,
   reimplement the three tiny computations natively — and read a mod-owned `u8 slot[722]` array. Base
   EXE code, so `PSX_MOD_CONSTRUCTOR` + one-shot `psx_mod_write_code_word`; no frame hook needed.
2. **Byte-for-byte port.** 44 + 2 + 2 + 28 code words plus 361 table bytes. Only worth it to stay
   file-compatible with the site's output; note that writing over the libgpu string block is safe in
   the recomp only if the recompiled libgpu shims do not print them.
3. **Beyond 7 colours.** The nibble packing (0..15) and `0x160 + 16*slot` already allow 16 slots; what
   stops you is VRAM/palette data, not the code. In a recomp the palettes can come from a mod asset
   instead of the 10 mirrored copies in WA_MRG.MRG, which also removes the "colour 2 differs per
   package" wrinkle.
4. **Palette side.** The 7 x 512-byte blocks are plain BGR555; a recomp mod can load them from a PNG
   at boot (`card_color.py palette-export/import` is the offline equivalent) and skip the 10-copy
   mirroring entirely.
5. **Interaction.** Anything else that wants the libgpu string block (process-guardianstars puts its
   16-entry table at 0x80011A80) must not overlap 0x80012150..0x8001236F. In the recomp keep both in
   mod-owned memory.

## 6. Decomp findings (proposed)

- `0x800291E0 init_container_entry_objs` | `s3` on the shared tail is the **card frame sprite id**: 0x100 monster, 0x101 magic/equip, 0x102 trap, 0x103 ritual, and the id actually used is `s3 + 8` (0x108..0x10B) at 0x8002947C. Proven by the site replacing it with `0x100 + slot` and its default slot map reproducing stock | document `s3` as `frameId`
- `0x80016784` | `s1` = scratchpad packet 0x1F800320; `+0x10/+0x12` is seeded to 0x00F10100 at 0x800168D8 and the type dispatch at 0x800169E4 adds 1/2/3 to `+0x12` for card types 0x14/0x15/0x16 (0x17 shares the +1 path). So `+0x12` is the **small-card frame CLUT row**, base 241 | name the packet field `clutRow`
- `0x8002BFCC` | the 723-iteration loop at 0x8002C290 fills a u16-per-card table at `s5+0x58 + 4*i` (written as `0x54(a0)` with `a0 = s5+4`) with the card frame value 0x160/0x170/0x180/0x190 by type — the library card-grid frame table | `gLibrary_awCardFrame` (or document the field)
- `0x801D4244 gDuel_adwCardStats` | bits 26-31 are the card type but **both** stock consumers mask with 0x1F, so type 32+ would alias | note the 5-bit mask as a stock quirk
- `0x80012150..0x8001236F` and `0x80011A80..0x80011A9F` | live PsyQ libgpu/libetc/libspu debug strings that the retail build never prints; used as free space by TEA's cardcolor and guardianstars tools. The libgpu block at file 0x2950 is 544 bytes of RCS id + printf templates | free-space note
- `0x801DADE0` / `0x801DAF90` | zero fill in the loaded EXE image (the old cardcolor stub homes) | free-space note

## 7. Open questions

- The exact VRAM meaning of the small-card `+0x10/+0x12` pair: 241 also appears in `func_80057544` as
  the `y` of a `LoadImage2` rect at (512, 241) 256x1, which suggests a 256-entry CLUT row, but the
  `+0x10` half is 0x100/0x180, not 512.
- Why colour 2's WA palette block differs between the 10 mirrored copies while the others do not.
- What the 512-byte blocks are beyond the first 72 entries the editor touches.
- The site never validates the 361 stock bytes it overwrites at 0x2950, so a file already patched by a
  *different* tool that used that area would be silently corrupted.
- Nothing is done server-side beyond the analytics POST.
