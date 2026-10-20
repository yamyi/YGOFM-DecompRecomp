# Special Ban List (process tool)

Route: `extend/tools/process/specialbanlist`. Input: SLUS_014.11 only (`.11`, 1,782,579..2,097,152 bytes).
Purpose: a Duel-Links-style limit list for the deck editor. Each card gets a 4-bit group:
0 = Forbidden, 1..14 = "Limited N", 15 = unrestricted. When you press X on a trunk card the game's
normal checks run (deck < 40, copies in trunk, < 3 copies in deck) and then a validator refuses the
card if its group is 0 or if the deck already holds N cards of group N. An optional second script
recolours the trunk-list names with the group colour once the card would be refused. Three panels:
"Create" (install main / colour script, reset), "Banlist" (per-group card lists), "Colors" (15 colour
pickers). Client-side only.
Status: decoded, stock bytes verified, script round-trips byte-exact, not yet built as a recomp mod.
Script: `scripts/banlist.py`. Patch dumps + disassembly: `patch/` (W J Y V K G Z H = the JS names).
Raw notes: `NOTES-raw.md`.

## 1. Main script: validator hooked into the deck editor's add-card path

| block (JS) | file offset | RAM | stock bytes | patched bytes |
|---|---|---|---|---|
| V `jumpMainCode` | 0x2407C (8) | 0x8003387C in `func_800336F0` | `0C00FFB8 24040007` = `jal SD_SEPlayFull; li a0,7` | `0802556E 00000000` = `j 0x800955B8; nop` |
| K `mainScript` | 0x85DB8 (64) | 0x800955B8 (over the libgte debug string "Error: Can't push matrix,stack(max 20) is full!...") | ASCII | trampoline, below |
| G `temporalZones` | 0x85E00 (48) | 0x80095600 (over "...,stack is empty!\nThis function is not implement") | ASCII | zeros = two register save areas (0x80095600 for Z, 0x80095620 for K/W) |
| Z `validationScript` | 0x1CB840 (240) | 0x801DB040 (EXE tail, zero in stock) | 0 | validator, below |
| Q `limitData` | 0x1CB930 (361) | 0x801DB130 | 0 | nibble table: byte (id-1)/2, high nibble = odd id, low nibble = even id; 0xFF = both unrestricted |
| H `oldJumps` (v1, detect only) | 0x2407C | | | `08076C10 24060000` = `j 0x801DB040; li a2,0` with data at X = 0x1CB940 (0x801DB140); the tool migrates X -> Q |

Stock context (`asm/matchings/type_record_transition_dispatch/func_800336F0.s`): s1 = `*(gp+0x3F4)`
= 0x80100000 (the load arena the deck editor uses as state), s0 = card id.

    80033844  lw   v0,0x5AA0(s1)      ; deck count
    8003384C  slti v0,v0,0x28         ; < 40
    80033858  lbu  v0,0x5D97(s1+s0)   ; copies in trunk (byte per card, id 1 at +0x5D98)
    80033868  lbu  v0,0x5AC4(s1+s0)   ; copies already in deck (id 1 at +0x5AC5)
    80033870  sltiu v0,v0,3
    8003387C  jal  SD_SEPlayFull(7)   ; <-- hook: "ok" sound
    80033884  jal  func_800320BC(s1,s0)  ; add the card to the 40-row deck list
    ...
    800338C8  jal  SD_SEPlayFull(9)   ; refusal sound

K (0x800955B8): `v0=0x80095620; sw at,0(v0); jal 0x801DB040; lui v0,0x8009` (delay slot) ...
`lw at,0x80095620; beqz v0 -> 0x800955F0; jal SD_SEPlayFull(7); j 0x80033884` / `0x800955F0: j 0x800338C8`.
So v0 = 1 from the validator continues the stock add path, v0 = 0 jumps straight to the refusal beep.

Z, the validator (input s0 = 1-based card id, clobbers nothing: saves at,v1,a0..a3,t0 at 0x80095600):

    g = nibble(0x801DB130, s0)              ; group of the card
    if g >= 15: return 1                    ; unrestricted
    if g == 0:  return 0                    ; forbidden
    count = 0; row = 0x80102D50             ; 40 x 16-byte deck-list rows (arena + 0x2D50)
    for 40 rows:
        if row[13] == 0: return 1           ; empty row = end of the list
        c = *(u16*)(row+4)                  ; card id in that row
        if nibble(c) == g:
            count++
            if count == g: return 0         ; the group already holds g cards
        row += 16
    return 1

Deck-list rows (filled by `func_800320BC`): +4 u16 id, +6 u16 ATK, +8 u16 DEF, +10 u8 type, +13 u8
occupied. Consequence: "Limited 2" means **two cards of that whole group combined**, not two copies
of each card (a semi-limited list, as the site's help text says). The stock 3-copies cap still
applies first.

## 2. Colour script (optional)

| block (JS) | file offset | RAM | stock bytes | patched bytes |
|---|---|---|---|---|
| Y `jumpColorCode` | 0x2245C (8) | 0x80031C5C in `func_80031874` | `0C00D5FA A6020004` = `jal int_to_digits; sh v0,4(s0)` | `08004960 3C028009` = `j 0x80012580; lui v0,0x8009` |
| W `colorsScript` | 0x2D80 (168) | 0x80012580 (over libcd "Access Denied. : file already open." strings) | ASCII | below |
| J `colorData` | 0x3178 (60) | 0x80012978 (over "<NULL>", "MDEC_rest:bad option(%d)", "MDEC_in_sync") | ASCII | 15 x u32 colour, bytes `RR GG BB 00` (PSX sprite r,g,b order); defaults group 0 = #ff6600, 1 = #40bf40, 2 = #0066ff, 3 = #ff00cc, 4 = #ffcc00, 5 = #008033, 6 = #0000ff, 7 = #ad0045, 8 = #ccff00, 9 = #00ffcc, 10 = #7340bf, 11 = #ff0000, 12 = #66ff00, 13 = #00ccff, 14 = #cc00ff |

`func_80031874` draws one trunk-list row: s0 = the name text object (a GsSPRITE-like record whose
+0x14 is the RGB word; 0x808080 = normal, and the stock code sets 0x2020FF = red at 0x80031C4C when
the card already has 3 copies in the deck or for ids 0x11..0x15), s2 = card id, s7+0x122 = the
count column. W: `if *(s0+0x14) == 0x808080` (still the normal colour) call the validator with
s0 = s2; if it returns 0, `*(s0+0x14) = colorData[group(s2)]`. Then it re-executes the two hooked
instructions (`addiu v0,s7,0x122` was the instruction before the hook, so it is repeated too) and
returns to 0x80031C64. Note the site's colour panel is hidden until the colour script is present,
and `inserCode` with "insert colors" ticked installs it; a stock file gets `insertColors = true`
by default.

## Recomp options

1. **Byte patch at startup** (base EXE, all sites resident): write V, K, Z, Q, G (+ Y, W, J if
   colours wanted) with `psx_mod_write_code_word`; keep the nibble table in the same place so the
   site's `.11` files and the recomp agree.
2. **Native validator (preferred).** Replace only the hook at 0x8003387C with a call into a native
   `banlist_allow(card)` reading a mod-owned table; implement the count over the deck-list rows
   (0x80102D50, or better the per-card counter at `arena+0x5AC5`) and return to 0x80033884 /
   0x800338C8. This drops the register save areas and the debug-string overwrites. Colour: set the
   RGB word from the same native function via a hook at 0x80031C5C.
3. **Semantics upgrade.** A per-card limit (max copies of *this* card) instead of the shared group
   budget is a one-line change in the native version.

## Decomp findings (proposed)

- 0x800336F0 | deck-editor "add trunk card" confirm: deck<40 (+0x5AA0), trunk copies (+0x5D98[id-1]), deck copies < 3 (+0x5AC5[id-1]), SE 7 + func_800320BC on success, SE 9 on refusal; state = *(gp+0x3F4) = 0x80100000 | `BuildDeck_TryAddCard`
- 0x80100000+0x2D50 | 40 x 16 B deck rows {+4 id, +6 atk, +8 def, +10 type, +13 occupied}, appended by func_800320BC, scanned by find_free_slot_gp3f4 | `gBuildDeck_aDeckRows`
- 0x80100000+0x5AA0 / +0x5AC5 / +0x5D98 | deck count u32 / per-card copies in deck u8[722] / per-card trunk count u8[722] | `gBuildDeck_wDeckCount`, `gBuildDeck_abDeckCopies`, `gBuildDeck_abTrunkCopies`
- 0x80031874 | trunk-list row renderer; text RGB 0x808080 normal, 0x2020FF (red) when the deck already holds 3 or for ids 0x11..0x15 | `BuildDeck_DrawTrunkRow`
- 0x80095600..0x80095630, 0x80012580..0x80012628, 0x80012978..0x800129B4 | libgte / libcd / libmdec debug strings, safe to overwrite (used by TEA as scratch) | (note)

## Open questions

- The old (v1) layout is only detected via H; its validator code location was not recovered (the
  tool does not remove it, it just re-installs the new one and migrates the nibbles).
- Whether the 0x808080 test in W misses rows whose stock colour differs (e.g. after a sort mode).
- Server side: nothing besides analytics.
