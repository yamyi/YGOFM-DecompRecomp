# x2 tool ("Special ATK/DEF": double the stat range)

Route: `extend/tools/data/x2`. Input: SLUS_014.11 (accepts `.11`, 1,048,576..3,145,728 bytes).
UI: "V.230314 [BETA]", one button ("MODIFY PROCESS"), client-side, file downloaded back
(the account only gates the analytics POST to `api/v2/tools`; comments box `guia` 39).
Script: `scripts/x2.py` (inspect / apply / restore on a SLUS copy). Raw notes: `NOTES-raw.md`.

Purpose: the per-card stats word stores ATK/10 and DEF/10 in 9-bit fields, so the game can
never show more than 5110. The tool rewrites the 23 places where the EXE turns a 9-bit field into
a number (`x * 10`) so they compute `x * 20`, then halves every stored ATK/DEF so all 722 cards
keep their printed values. From then on a modder enters half the wanted value in any card editor
("7000 ATK -> register 3500"); the tool detects an already-converted file and refuses to run twice.

Status: decoded, stock bytes verified against `~/ygofm-decomp/SLUS_014.11`, script round-trips
(apply -> restore --stock is byte-identical), not yet built as a recomp mod.

## 1. The 23 code sites: `sll rd,rt,1` -> `sll rd,rt,2`

The tool writes one byte (0x40 -> 0x80, the shamt field) at each file offset. Stock words verified.

| file off | RAM | function | stock word | patched | meaning |
|---|---|---|---|---|---|
| 0x09004 | 0x80018804 | func_80018608 | `00021040` sll v0,v0,1 | `00021080` | sll v0,v0,2 |
| 0x0901C | 0x8001881C | func_80018608 | `00021040` | `00021080` | |
| 0x090B8 | 0x800188B8 | func_80018608 | `00021040` | `00021080` | |
| 0x090D0 | 0x800188D0 | func_80018608 | `00021040` | `00021080` | |
| 0x152CC | 0x80024ACC | card_record_fill (0x800249E0) | `00031840` sll v1,v1,1 | `00031880` | ATK into card record +0xE |
| 0x15300 | 0x80024B00 | card_record_fill | `00031840` | `00031880` | DEF |
| 0x18888 | 0x80028088 | func_80027DF8 | `00021040` | `00021080` | |
| 0x188A8 | 0x800280A8 | func_80027DF8 | `00021040` | `00021080` | |
| 0x18974 | 0x80028174 | func_80027DF8 | `00021040` | `00021080` | |
| 0x18994 | 0x80028194 | func_80027DF8 | `00021040` | `00021080` | |
| 0x19BB4 | 0x800293B4 | init_container_entry_objs (0x800291E0) | `00021040` | `00021080` | card-detail object +0x32 (ATK) |
| 0x19BF4 | 0x800293F4 | init_container_entry_objs | `00021040` | `00021080` | +0x34 (DEF) |
| 0x1D44C | 0x8002CC4C | Duel_GetBaseCardStat (0x8002CBF4) | `00028040` sll s0,v0,1 | `00028080` | the duel's stat getter |
| 0x22928 | 0x80032128 | func_800320BC | `00021040` | `00021080` | |
| 0x22948 | 0x80032148 | func_800320BC | `00021040` | `00021080` | |
| 0x22D88 | 0x80032588 | func_800323F8 | `00021040` | `00021080` | |
| 0x22DA8 | 0x800325A8 | func_800323F8 | `00021040` | `00021080` | |
| 0x22E74 | 0x80032674 | func_800323F8 | `00021040` | `00021080` | |
| 0x22E94 | 0x80032694 | func_800323F8 | `00021040` | `00021080` | |
| 0x235AC | 0x80032DAC | func_80032C48 (deck-builder sort, next to BuildDeck_CompareCard) | `00052040` sll a0,a1,1 | `00052080` | ATK of card A |
| 0x235C0 | 0x80032DC0 | func_80032C48 | `00031040` sll v0,v1,1 | `00031080` | DEF |
| 0x51560 | 0x80060D60 | func_80060B38 | `00042040` sll a0,a0,1 | `00042080` | |
| 0x51584 | 0x80060D84 | func_80060B38 | `00042040` | `00042080` | |

Every site is the tail of the same compiler idiom (`x*10 = ((x<<2)+x)<<1`), e.g. at 0x800187F8:

    andi a0, v1, 0x1FF        ; ATK/10 field
    sll  v0, a0, 2
    addu v0, v0, a0           ; x*5
    sll  v0, v0, 1            ; <-- patched to sll 2  => x*20
    ...
    sra  v1, v1, 9 ; andi v1, v1, 0x1FF ; same for DEF

Completeness check: a scan of the whole EXE for `andi ..,0x1FF` followed within 8 words by an
`sll ..,1` finds exactly these 23 sites and nothing else. The same scan over all of WA_MRG.MRG
(duel overlay, screen modules) finds none, so no disc-loaded code carries its own `x10`.
`mult`-based multiplies are not covered by that scan (none seen).

## 2. The data transform

    for id in 1..722:  w = u32 @ 0x1C4A44 + (id-1)*4          (RAM 0x801D4244, gDuel_adwCardStats)
        atk9 = (w & 0x1FF) >> 1 ;  def9 = ((w >> 9) & 0x1FF) >> 1 ;  bits 18..31 unchanged

Bits 18-21 / 22-25 (Guardian Stars) and 26-30 (type) are untouched. The halving floors: 135 stock
cards have an ATK or DEF that is not a multiple of 20 and come back 10 lower (Sword Arm of Dragon
1750/2030 -> 1740/2020, Kwagar Hercules 1950/2100 -> 1940/2100 ...). The tool never restores; the
script's `restore` doubles back (lossy) unless given `--stock` to copy the 722 words.

## 3. What the game does with it

- `Duel_GetBaseCardStat` (0x8002CBF4, IDB `baseCardStat`): reads `gDuel_adwCardStats[id-1]`, picks
  ATK or DEF, multiplies by 10 (the patched shift), adds `Duel_GetTerrainBoost` (+/-500 by type on a
  terrain) and **clamps to 0..9999**. This is the duel's and the AI's (`AiScript_TestHighStat`,
  `AiScript_EvaluateFusion`) view of a card, so 511*20 = 10220 becomes 9999 there.
- `card_record_fill` (0x800249E0): when a hand/field card record is built, `sh v1, 0xE(s3)` stores
  ATK*10 (and DEF right after) in the record. Equip (+500 etc.) and terrain boosts are added in
  absolute points afterwards, so with x2 they are relatively half as strong.
- The other sites are display/compare paths: card detail object (`init_container_entry_objs`,
  +0x32/+0x34 = ATK/DEF, right before it reads the level/attr byte), deck-builder sorting
  (`func_80032C48` compares two cards' ATK then DEF), and screens the decomp has not named yet
  (`func_80018608`, `func_80027DF8`, `func_800320BC`, `func_800323F8`, `func_80060B38`). None of
  these clamp, hence the site's warning "do not register values greater than 5000 (9999)".
- The "used already" detection is simply "all 23 bytes are 0x80".

## 4. Recomp options

1. Faithful port, one shot at startup (base-EXE code and data): `psx_mod_write_code_word` the 23
   words (`stock | 0x40` -> `| 0x80`), then halve the 722 words in place. Do it before
   `psx_card_extend.c` builds its relocated copy of the table (it copies the stock words), or halve
   both. `psx_card_db_stats()` and `psx_fusion_db` decode `(w & 0x1FF) * 10` and would need a
   multiplier constant too.
2. Better: do not halve anything. Keep stock data and only widen the arithmetic natively: hook
   `Duel_GetBaseCardStat` and the record fill with functions reading from a mod-owned 16-bit
   ATK/DEF table (the relocation machinery in `psx_card_extend.c` already re-points the 64 stats
   sites, so a second table with u16 fields is the natural extension). That gives 0..9999 without the
   "enter half" convention and without the 10-point rounding loss.
3. Display-only variant: leave code alone and post-process the numbers in the text hook
   (`psx_card_name_color.c` shows how the glyph stream can be intercepted).

## 5. Decomp findings (proposed)

- `0x80018804, 0x8001881C, 0x800188B8, 0x800188D0, 0x80024ACC, 0x80024B00, 0x80028088, 0x800280A8, 0x80028174, 0x80028194, 0x800293B4, 0x800293F4, 0x8002CC4C, 0x80032128, 0x80032148, 0x80032588, 0x800325A8, 0x80032674, 0x80032694, 0x80032DAC, 0x80032DC0, 0x80060D60, 0x80060D84` | the complete set of `x*10` shifts applied to the 9-bit ATK/DEF fields of gDuel_adwCardStats (EXE scan; none in disc modules) | annotate as `CardStat_x10` sites
- `0x800249E0 card_record_fill` | stores ATK*10 at card record +0xE (0x80024AD0 `sh v1,0xE(s3)`), DEF*10 right after | confirms the record layout
- `0x80032C48` | compares two cards by ATK*10 then DEF*10 (deck builder, next to BuildDeck_CompareCard 0x80032B60) | `BuildDeck_CompareByStats`
- `0x80029410` | `D_801D5332` is indexed by card id (1-based) and split `>>4` -> object +0x3B (attribute), `&0xF` -> +0x3A (level) | `gCard_abLevelAttr` (see cardsdata README)

## 6. Open questions

- What screens `func_80018608`, `func_80027DF8`, `func_800320BC`, `func_800323F8`, `func_80060B38`
  belong to (only the shift idiom was matched, not the callers).
- The recomp lists stats-table readers in a disc-loaded module at 0x8018xxxx (library). No plain
  `lui 0x801D / addiu 0x4244` pair exists anywhere in WA_MRG.MRG, so either that module is not
  stored as plain code or those addresses come from elsewhere; if it multiplies by 10 itself the
  x2 patch would show halved numbers there. Needs an in-game check.
- Server side: only the analytics POST (`api/v2/tools`, `tipo` not visible in this chunk).
