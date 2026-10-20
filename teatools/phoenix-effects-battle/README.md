# PHOENIX > EFFECTS > BATTLE tool ("Battlefield Demolisher")

Route: `extend/tools/phoenix/effects/battle` (page title "TEA Online - Phoenix tools - Battlefield
Demolisher Tool", UI version `V.240321 [BETA]`). Input: **SLUS_014.11** (`.11`, the shared disc-tree
reader; max 44,040,192 bytes). The tool injects a ~600-byte MIPS routine ("the process") into the
EXE, hooks it into the duel's battle-aftermath phase, and then lets you attach one of three
hard-coded battle effects to up to **16 cards**, with a **14-card** exception list:

| effect id | site name | behaviour |
|---|---|---|
| 0 | Marshmallon | the card is never destroyed in battle |
| 1 | Exploder Dragon | both cards are destroyed, unless the other card is in the exception list |
| 2 | D.D. Warrior Lady | both cards are destroyed, no exceptions |

Everything is client-side; the patched SLUS is downloaded back. `Check` verifies the two hook sites
byte-for-byte before reading the lists; `Patch` writes hooks + routine + a wiped data block.
Script: `scripts/phoenix_battle.py` (check / install / set / restore / names). Notes: `NOTES-raw.md`.

Status: fully decoded. Every patch byte verified against `~/ygofm-decomp/SLUS_014.11`, the injected
routine disassembled instruction by instruction, the hooked function and both hooked stock
instructions identified in the decomp, the clobbered stock symbol identified. Not tested in-game.

## 1. The five patched regions

`RAM = 0x80010000 + (file_off - 0x800)`. Site arrays: `Ve` = validation/hooks, `We` = code,
`Ye` = the wiped data block.

| # | file offset | RAM | size | role |
|---|---|---|---|---|
| A | `0x10E30` | `0x80020630` | 16 B | hook A, 4 words |
| B | `0x10EB0` | `0x800206B0` | 8 B | hook B, 2 words |
| C | `0x1C57D0` | `0x801D4FD0` | 552 B (0x228) | the routine |
| D | `0x1C59F8` | `0x801D51F8` | 68 B (0x44) | the effect + exception tables |
| E | `0x1C5A3C` | `0x801D523C` | 20 B (0x14) | the routine's tail |

C + D + E are contiguous: `0x801D4FD0 .. 0x801D5250`.

### Hook A — `0x80020630`, 4 words

| addr | stock | patched | meaning |
|---|---|---|---|
| `0x80020630` | `26119EF0` `addiu s1, s0, -0x6110` | `0C0753F5` **`jal 0x801D4FD4`** | call the routine |
| `0x80020634` | `8E230008` `lw v1, 8(s1)` | `26119EF0` `addiu s1, s0, -0x6110` | the stock word, moved into the delay slot |
| `0x80020638` | `34820080` `ori v0, a0, 0x80` | `0C075468` **`jal 0x801D51A0`** | call the "override v1" stub |
| `0x8002063C` | `A382026C` `sb v0, 0x26C(gp)` | `34820080` `ori v0, a0, 0x80` | the stock word, moved into the delay slot |

The two displaced instructions (`lw v1, 8(s1)` and `sb v0, 0x26C(gp)`) are re-executed inside the
stub at `0x801D51A0`, so nothing is lost. `s1` = `&D_800E9EF0[0]` = `0x800E9EF0` and is computed in
the first delay slot, i.e. *before* the routine runs, which is why the routine can use it.

### Hook B — `0x800206B0`, 2 words

| addr | stock | patched | meaning |
|---|---|---|---|
| `0x800206B0` | `8E22000C` `lw v0, 0xC(s1)` | `0C075474` **`jal 0x801D51D0`** | call the second stub |
| `0x800206B4` | `00000000` `nop` | `3C07801D` `lui a3, 0x801D` | the stub's `a3` base, put in the free delay slot |

### Region C/D/E — what it costs

`0x801D4FD0..0x801D5250` is stock **`gCard_asNameSortKey`** (`s16[722]` at `0x801D4D8E`, ending
exactly where `gDuel_abCardLevelAttr` = `0x801D5332` begins). The injected code therefore **destroys
the alphabetical sort keys of card ids 290..609** (320 cards). That table is only read by
`compare_rec_two_level` / `compare_rec_two_level_std` / `BuildDeck_CompareCard` (0x80032B60), so the
damage is cosmetic — Build Deck / Trunk / Library "sort by name" is scrambled for that id range —
but it is real and permanent for a patched EXE. `phoenix_battle.py check` prints the range.

### Region D — the two tables

    0x801D51F8  16 x u16  effect entries, little-endian:  (card_id << 4) | effect_id
    0x801D5238   1 x u32  0xFFFFFFFF terminator
    0x801D521C  14 x u16  exception card ids                          (= 0x801D51F8 + 36)
    0x801D5238   1 x u32  0xFFFFFFFF terminator                       (= 0x801D521C + 28)

Both lists are scanned with signed `lh` and `bgez`, so **the first entry with bit 15 set ends the
list** — an empty slot in the middle truncates it. The site's UI compacts the arrays before writing
(`sortCardEffect` / `sortCardException` push the nulls to the end), so this never happens through the
web page; `phoenix_battle.py` compacts too. `card_id << 4` caps the id at 4095, which is fine for
1..722. The site clamps `effect` to 0..2 and `card_id` to 1..722 on read.

## 2. The injected routine, decoded

Disassembled from the site's own bytes with
`mips-linux-gnu-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x801D4FD0`.

Two u16 result slots are used throughout: **`0x801D4FD0` = side 0, `0x801D4FD2` = side 1**, with
`+1` = "force survive", `-1` = "force destroyed", `0` = "leave the stock outcome alone".

```
801D4FD4  lw   v0, 4(s1)           ; D_800E9EF0[1]  = the side-1 card object
801D4FD8  lui  a3, 0x801D
801D4FDC  bnez v0, 0x801D4FEC
801D4FE0   sw  zero, 0x4FD0(a3)    ; (delay, always) clear BOTH result slots
801D4FE4  jr   ra                  ; no side-1 object -> nothing to do

; --- per-side lookup, run twice: pass 0 = side 1, pass 1 = side 0 ---
801D4FEC  move v1, zero            ; pass counter
801D4FF0  li   t2, -1              ; side-1 card id
801D4FF4  li   t3, -1              ; side-1 effect
801D4FF8  lbu  a2, 0x6A(v0)        ; obj->f6A = field-slot index
801D5000  a1 = a2*28
801D500C  a2 = 0x801A7AD8          ; D_801A7AD8, the cards-in-play table, stride 0x1C
801D5018  lhu  v0, 0xC(a1+a2)      ; row->+0x0C = 1-based card id
801D501C  j    0x801D523C          ; --> the card-690 guard (region E)
   801D523C  li  a1, 690
   801D5240  bne a1, v0, 0x801D5024   ; card 690 "Fake Trap" -> abort the whole routine
   801D5248  jr  ra

801D5024  a2 = 0x801D51F8          ; the effect table
801D5028  lh   a1, 0(a2)           ; entry
801D5030  srl  t0, a1, 4           ; card id
801D5034  beq  t0, v0, found
801D5038   andi t1, a1, 0xF        ; effect
801D503C  bgez a1, 0x801D5028      ; keep scanning while the entry is >= 0
801D5040   addiu a2, a2, 2
          ... not found: pass 0 -> t2 = card id, t3 stays -1, load D_800E9EF0[0], pass 1
          ... not found on pass 1 and t3 < 0 -> jr ra (neither card has an effect)
found:    pass 0 -> t2 = card id, t3 = effect, load D_800E9EF0[0], pass 1
          pass 1 -> fall through with t0 = side-0 card id, t1 = side-0 effect
```

After both passes: `t0/t1` = side 0's card id / effect, `t2/t3` = side 1's (`-1` = no effect).

```
801D5088  if (t1 == 0) result[0] = +1        ; Marshmallon on side 0
801D5094  if (t3 == 0) result[1] = +1        ; Marshmallon on side 1
801D50A0  v1 = max(t1, t3) ; v0 = -1
801D50BC  if (v1 > 1) { *(u32*)0x801D4FD0 = -1; return; }   ; D.D. Warrior Lady: both die

801D50C4  a2 = 0x801D521C                     ; exception list
801D50CC  if (t1 == 1) {                      ; Exploder Dragon on side 0
801D50D4     *(u32*)0x801D4FD0 = -1;          ;   both die
801D50DC     if (t0 == 660) {                 ;   card 660 "Stain Storm" special case
                result[0] = 0;                ;     ... does not destroy itself
                if (gDuel_abCardLevelAttr[t2] >> 4 == 1)   /* side 1 is DARK */
                   { result[1] = 0; goto side1; }          ;   ... and spares DARK cards
             }
             for (e = *a2++; e >= 0; e = *a2++)            /* exception scan */
                if (e == t2) result[1] = 0;
          }
side1:    if (t3 == 1) { ... exactly the same with the roles swapped ... }
801D518C  jr ra
```

Stub A (replaces `lw v1, 8(s1)`):

```
801D51A0  sb   v0, 0x26C(gp)       ; the displaced stock store (D_8009B26C = mode | 0x80)
801D51A4  lui  a3, 0x801D
801D51A8  lh   a3, 0x4FD0(a3)      ; result[0]
801D51AC  lw   v1, 8(s1)           ; the displaced stock load: D_800E9EF0[2]
801D51B0  if (a3 == 0) return v1   ; no override
801D51B8  v1 = 1                   ; result > 0 -> "survivor object present"
801D51BC  if (a3 > 0) return v1
801D51C4  v1 = 0                   ; result < 0 -> destroyed
```

Stub B (replaces `lw v0, 0xC(s1)`) is the same against `0x801D4FD2` / `D_800E9EF0[3]` and returns in
`v0`; its `a3` comes from the `lui a3, 0x801D` the hook left in the delay slot.

## 3. What the game does with it

### The hooked function

`0x8002061C` is a splat split-label inside **`func_8001F560`** (`config/function_ranges.txt`:
`R 8001F560 1374`, i.e. `0x8001F560..0x800208D4`; asm in `asm/asm_FD5C.s`, no matched C). It is the
**duel battle presentation / aftermath mode handler**, driven by the mode byte `D_8009B26C`
(`0x26C($gp)`, `$gp` = 0x8009B000), whose bit `0x80` is the "this phase already ran" one-shot. The
"who wins" arithmetic itself lives in `func_8001EFD4` (`src/func_8001EFD4.c`, matched); the block at
`0x8002061C` is the *apply the outcome and tear the battle down* phase.

Stock flow of the block the tool hooks:

```c
a0 = D_8009B26C;
if (a0 & 0x80) goto already_done;
s1 = &D_800E9EF0[0];                      /* 0x800E9EF0 */
v1 = D_800E9EF0[2];                       /* <-- hook A overrides this */
D_8009B26C = a0 | 0x80;
if (v1) {                                 /* side 0 survived: put its card back on the field */
    o   = D_800E9EF0[0];
    opponent_field_record_fill(o->f6A, o->f6B);
    row = &D_801A7AD8[o->f6A];
    row->f16 |= (D_8009B270 & 0x0A00) | 0x4000;   /* 0x4000 = darkened "already attacked" tint */
    row->f12  =  D_8009B268;
    func_80018080(row->f0);
}
v0 = D_800E9EF0[3];                       /* <-- hook B overrides this */
if (v0) { ... the same for side 1, plus the D_8009B322 gate ... }
__builtin_delete(D_800E9EF0[0]);
__builtin_delete(D_800E9EF0[1]);
/* then the two HUD panels slide back in */
```

So `D_800E9EF0[2]` / `[3]` are the **"this side's card survives"** gates: non-null means the card is
re-registered into the field table `D_801A7AD8` and re-tinted; null means it is simply not put back,
i.e. destroyed. Forcing that pointer to 1 or 0 is exactly how the tool forces the outcome, and it
does it *after* the battle maths has already run — the damage step, the animation and the LP change
are untouched, only the destruction is.

### Data the routine reads

| address | decomp name | what |
|---|---|---|
| `0x800E9EF0` | `D_800E9EF0` | `Obj *[4]`: `[0]`/`[1]` = the two battling card objects, `[2]`/`[3]` = the per-side survivor gates (indexed as `[D_8009B2B1 + 2]`, so 2 = player, 3 = opponent) |
| `Obj + 0x6A` | — | field-slot index into `D_801A7AD8` |
| `0x801A7AD8` | `D_801A7AD8` | cards-in-play table, stride **0x1C**, 30 rows (15 slots per player); `+0x00` `Obj *`, `+0x0C` **1-based card id**, `+0x0E`/`+0x10` DEF/ATK terms, `+0x12`/`+0x14` modifiers, `+0x16` flags (`0x8000` occupied, `0x800` face-down/defence, `0x4000` darkened) |
| `0x801D5332` | `gDuel_abCardLevelAttr` | `u8[723]`, **indexed by card id, no -1** (see RECOMP-ISSUES #1); `attribute << 4 \| level`, attribute `0` Light, `1` Dark, `2` Earth, ... `5` Wind, `6` Magic, `7` Trap (verified: card 1 Blue-Eyes `0x08`, card 3 Hitotsu-me Giant `0x24`, card 58 Kuriboh `0x11`, card 660 Stain Storm `0x60`, card 690 Fake Trap `0x70`) |
| `0x801D4D8E` | `gCard_asNameSortKey` | the table the routine is written on top of |

### Quirks and limits

* **Exploder beats Marshmallon.** The Marshmallon branch writes a `sh` (+1) first, then the Exploder
  branch writes a `sw` (-1) over *both* halves. So Marshmallon + Exploder in the same battle kills
  both cards; the exception list is the only way to protect a card from Exploder.
* **Two hard-coded card ids.**
  * **690 (`Fake Trap`)** — if *either* combatant resolves to card 690, the routine returns before
    doing anything and the stock outcome stands. Presumably a guard for a non-monster slot; the tool
    exposes no way to change it.
  * **660 (`Stain Storm`, "Acid rain destroys an opponent's Machine monsters.")** — when card 660 is
    the Exploder card it does *not* destroy itself, and it does not destroy an opponent whose
    **attribute nibble is 1 (DARK)**. That does not match the card's own text (Machine is a *type*,
    from `gDuel_adwCardStats` bits 26-30, not the attribute nibble), so this is either a bug in the
    tool or a deliberately different custom effect.
* Effects act after damage, so a Marshmallon card still takes/deals the normal LP damage; only the
  destruction is suppressed.
* The routine is called once per battle (behind the `0x80` one-shot), and it clears both result slots
  on entry, so no state leaks between battles.
* Register safety: the routine clobbers `v0`, `v1`, `a1`, `a2`, `a3`, `t0`-`t5` but leaves `a0`
  (the mode byte, needed by the following `ori`), `s0` and `s1` alone.
* 16 effect cards and 14 exceptions are hard array limits; the terminators (`0xFFFFFFFF` after each
  list) are what stops the scan.

## 4. Recomp options

* **Do not port the byte patch.** It is a code-injection hack that overwrites a live data table
  (`gCard_asNameSortKey[289..608]`). A recomp mod should reproduce the *capability*, not the bytes.
* **Native, minimal.** The whole feature is "decide `D_800E9EF0[2]` / `[3]`". A `PSX_MOD_CONSTRUCTOR`
  can install a frame hook that watches `D_8009B26C`, or — cleaner — patch the two loads:
  `psx_mod_write_code_word(0x80020634, ...)` / `psx_mod_write_code_word(0x800206B0, ...)` to jump to
  a stub in reclaimed RAM that reads the card ids from `D_801A7AD8[obj->f6A].f0C` and consults a
  host-side table. All of it is base-EXE code, so a one-shot startup patch is enough (no per-frame
  re-assert, unlike the 0x80168000 screen modules).
* **Where to put the stub.** *Not* `0x801D4FD0`. The reclaimed-RAM map already has candidates;
  note `psx_card_shop.c` claims `0x801BFF80` and the drop tool's patch wants `0x801BFFD0`
  (see `RECOMP-ISSUES.md` #4) — pick a free arena and record it.
* **Better than the site's design.** With a native table you can key on card *type* / attribute
  instead of a 16-entry id list (e.g. "all Machine monsters" for a real Stain Storm), you get more
  than 3 effects, you can run before the damage step to also suppress LP loss, and you avoid
  destroying the sort keys.
* If the byte patch is ever applied to a disc for compatibility with existing TEA mods, remember to
  restore `gCard_asNameSortKey[289..608]` from the stock EXE afterwards, or Build Deck sorting will
  stay broken.

## 5. Decomp findings (proposed)

- `0x8001F560` (extent `0x8001F560..0x800208D4`, 0x1374; splat splits it into `func_8001F710` … `func_8002061C`) | duel battle presentation + aftermath mode handler, driven by `D_8009B26C` bits `0x80`/`0x40`; calls `func_8001EFD4` (the ATK/DEF comparator), `Duel_CalcGuardianStarBonus`, `opponent_field_record_fill`, `counter_tween_start`, `SD_SEPlayFull`, `Fade_StartOut` | `Duel_RunBattleSequence`
- `0x800E9EF0` | `Obj *[4]`: `[0]`/`[1]` the two battling card objects, `[2]`/`[3]` the per-side "card survives" gates (indexed `[D_8009B2B1 + 2]`); a non-null gate makes the block at `0x80020630` re-register the card into `D_801A7AD8` with flag `0x4000` (darkened) instead of leaving it destroyed | `gDuel_apBattleObjs`
- `0x801A7AD8` `D_801A7AD8` | cards-in-play table, stride 0x1C, 30 rows (15 per player, `D_8009B1D5 * 15 + row`); `+0x00` Obj\*, `+0x04` attached Obj\*, `+0x0C` s16 1-based card id, `+0x0E` DEF term, `+0x10` ATK term, `+0x12`/`+0x14` modifiers, `+0x16` u16 flags (`0x8000` occupied, `0x800` face-down/defence, `0x4000` darkened) | `gDuel_aFieldSlots`
- `Obj + 0x6A` / `+0x6B` | field-slot index / secondary index, set by `opponent_field_record_fill`; `D_801A7AD8[obj->f6A]` is the row | (facts)
- `0x801D5332` `gDuel_abCardLevelAttr` | confirms F146 from a second direction: the injected code does `(gDuel_abCardLevelAttr[card_id] >> 4) == 1` as a "is DARK" test, indexed by id with **no -1** | (facts)
- `0x801D4D8E` `gCard_asNameSortKey` | `s16[722]`, `0x801D4D8E..0x801D5331`, read only by `compare_rec_two_level` / `compare_rec_two_level_std` / `BuildDeck_CompareCard` (0x80032B60) | (facts; the TEA "Phoenix battle" patch overwrites entries 289..608)

## 6. Open questions

* Why **card 690 (Fake Trap)** aborts the routine. The likeliest explanation is that `D_801A7AD8`
  row `+0x0C` holds 690 for some non-monster / placeholder slot, but that was not observed; nothing
  in the decomp special-cases 690.
* Which side is "side 0". `D_800E9EF0[2]`/`[3]` are indexed `[D_8009B2B1 + 2]` where `D_8009B2B1` is
  the acting-player index, so slot 2 is the *player* and slot 3 the *opponent* — but the routine
  reads `[1]` first and `[0]` second, and the mapping of `[0]`/`[1]` to attacker/defender was not
  confirmed. It matters for asymmetric effects (Marshmallon on the attacker vs the defender).
* Whether an effect card in the *opponent's* hand/deck can ever reach this code path (the routine
  only ever sees the two cards actually in the battle, so probably not).
* The site's `Check` only validates the two hook sites; it does not verify regions C/D/E, so an EXE
  with the hooks but a corrupted routine would be reported as "process enabled".
* Nothing happens server-side beyond the shared `api/v2/tools` usage counter and the comments box.
