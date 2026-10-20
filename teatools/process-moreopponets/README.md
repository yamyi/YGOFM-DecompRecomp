# More Opponents (process tool)

Route: `extend/tools/process/moreopponets` (sic). Inputs: SLUS_014.11 (`.11`, 1..5 MB) **and**
WA_MRG.MRG (`.mrg`, 35..43 MB), plus optionally an `.xlsx` made from
`site/Assets/files/MoreOpponetsTemplate.xlsx` (100 KB..20 MB).
Purpose: double the opponent count (39 -> 78) without adding data: the per-opponent deck / drop
pools shrink from u16 weights to u8 weights, which frees the second half of every pool for a second
"bank" of opponents. Opponent id bit 6 (0x40) selects the bank. The tool patches the EXE (8 sites),
converts WA_MRG's pool table ("reduce": u16 -> u8 modulo 256, bank 1 = copy of bank 0) or fills it
from the Excel sheet. Version string on the page: V.230503 [BETA]. Client-side; only analytics go to
the server.
Status: decoded, stock bytes verified (the tool itself checks all 8 stock sites before applying),
script round-trips byte-exact (WA restore needs a stock reference, the reduction is lossy), not yet
built as a recomp mod.
Script: `scripts/more_opponents.py` (inspect / apply / reduce / export / import / restore / restore-wa).
Patch dumps + disassembly: `patch/`. Raw notes: `NOTES-raw.md`.

## 1. The SLUS patch (8 sites, JS `we`; stock check `ye`)

| file offset | RAM | function | stock | patched |
|---|---|---|---|---|
| 0x2540 (144) | 0x80011D40 (libcd debug strings "CD_ready", "$Id: bios.c,v 1.86 ...") | new code + a u16 | ASCII | u16 bank offset at 0x80011D40 (0 or 722), three stubs at 0x80011D50 / 0x80011D80 / 0x80011DA8 |
| 0x28D68 (8) | 0x80038568 in `func_80038530` | campaign-script opcode that fetches the opponent byte | `lui at,0x800A; sb a1,gDuel_bOpponentID` | `j 0x80011D50; nop` |
| 0x14C50 (8) | 0x80024450 in `Duel_ShuffleDeck` | AI deck draw | `move s3,zero; addiu s4,sp,0x10` | `j 0x80011D80; nop` |
| 0x14C77 (1) | 0x80024477 | | `94` (`lhu v0,0(v1)`) | `90` (`lbu v0,0(v1)`) |
| 0x14CD4 (1) | 0x800244D4 | | `02` (`addiu v1,v1,2`) | `01` (`addiu v1,v1,1`) |
| 0x12048 (8) | 0x80021848 in `Duel_SelectCardDrop` | card drop roll | `andi v0,v0,0x7FF; addiu a1,v0,1` | `j 0x80011DA8; nop` |
| 0x1205B (1) | 0x8002185B | | `96` (`lhu v0,0(s0)`) | `92` (`lbu v0,0(s0)`) |
| 0x1207C (1) | 0x8002187C | | `02` (`addiu s0,s0,2`) | `01` (`addiu s0,s0,1`) |

The stubs (`patch/patch_00002540.dis`):

    80011d50  at = 0x80011D40
              v1 = (a1 & 0x40) ? 722 : 0        ; bank offset in BYTES (u8 pools)
              a1 &= 0x3F                         ; real opponent 0..63
              *(u16*)0x80011D40 = v1
              sb a1, gDuel_bOpponentID           ; the displaced stock store
              j 0x80038570
    80011d80  s7 += *(u16*)0x80011D40            ; Duel_ShuffleDeck: s7 = deck pool pointer
              s3 = 0; s4 = sp+0x10               ; displaced stock words
              j 0x80024458
    80011da8  s0 += *(u16*)0x80011D40            ; Duel_SelectCardDrop: s0 = drop pool pointer
              v0 &= 0x7FF; a1 = v0 + 1           ; displaced stock words (threshold 1..2048)
              j 0x80021850

## 2. The WA_MRG data: opponent pool table

| | |
|---|---|
| WA_MRG offset | 0xE9B000 = in-file sector 0x1D36, disc LBA 10102 + 0x1D36 = 17580 (id 1). Block for id N at sector 0x1D33 + 3N; sector 0x1D33 (id 0) is a byte-identical copy of Simon's block, unused |
| per opponent | 0x1800 bytes = 3 sectors: 4 pools x 1460 B (deck, SA-POW, BCD, SA-TEC), each stock `u16 weight[722]` + 16 B pad, weights sum to 2048 |
| after the patch | each pool = `u8 bank0[722]` + `u8 bank1[722]` (+16 pad); the site's "reduce" writes `w % 256` into both halves |
| RAM | loaded by `func_800179F4` (0x80017AC4..0x80017AEC: `sector = 0x1D33 + 3*gDuel_bOpponentID`, 3 sectors) to `gDuel_awOpponentDeckPool` 0x801781D8; drop pools follow at `gDuel_awSaPowCardDrops` 0x8017878C + 1460*n |
| xlsx | sheet 1, card rows 6..727, column C onward, 4 columns per opponent (DECK, SAPOW, BCDPT, STEC) for opponents 1..78; row 3 = the 2048 sums, row 4 = reference names |

Stock verified: every pool of every opponent sums to 2048 (u16). Opponent 2 (Teana) has weights up
to 400 and 300; after the site's reduction her deck pool sums to 512 (400 -> 144, 300 -> 44).

## What the game does with it

`Duel_ShuffleDeck(0, ...)` (0x800243F4) builds the CPU deck: for each of 40 slots roll
`rand() & 0x7FF + 1`, walk the 722 weights (`lhu` -> now `lbu`, step 2 -> 1) until the running
sum reaches the threshold, take that card if it has < 3 copies (else re-roll). `Duel_SelectCardDrop(n)`
(0x80021810) does one walk over drop pool n (`s0 = 0x8017878C + 1460*n`) and returns the 1-based
card or 0 when the walk runs out. Consequences of the u8 conversion:

- A pool whose bytes sum to less than 2048 misses with probability (2048 - sum)/2048: the deck
  builder just re-rolls (more RNG pulls, different deck), but `Duel_SelectCardDrop` returns **0 = no
  drop**. Any stock weight >= 256 must be re-spread by hand (the template's 2048 row is the check).
- `gDuel_bOpponentID` is masked to 0..63 at the script opcode only. Portrait, name, AI record
  (`gDuel_aOpponentData`), W/L record slot (0x801D071C, 39 x 4) all come from the masked id, so a
  bank-1 opponent is "the same duelist with another deck and drops".
- The bank word at 0x80011D40 is only written by the script opcode. The free-duel module sets
  `gDuel_bOpponentID` through `init_800eb26c_fields_from_args` and never touches it, so a free duel
  right after a bank-1 campaign duel will still read bank 1 (stale) for that opponent. Bank-1 ids can
  only be requested by a campaign script byte (0x41..0x67) or by other TEA tools that write such ids.
- Third-party drop editors (and the recomp's stock readers) misinterpret the converted table; the
  page warns the operation cannot be reversed.

## Recomp options

1. **Do not convert the disc data.** Keep the stock u16 pools and give extra opponents their own
   pools in mod memory: hook `Duel_ShuffleDeck` / `Duel_SelectCardDrop` (or just swap the pool
   pointer before they run) when the opponent id is >= 40. A native "duelist pack" folder (deck +
   3 drop tiers summing to 2048, u16) is the same idea without the 255 cap.
2. **Site compatibility.** If a player brings a reduced WA_MRG + patched SLUS, detect the 8 patched
   sites and simply let the code run; nothing in the recomp needs to change for that.
3. If the site layout is wanted natively: patch the 8 words once at startup (base EXE), and store the
   bank word in mod state instead of 0x80011D40; reset it to 0 when a free duel starts.

## Decomp findings (proposed)

- 0x80017AC4..0x80017AEC (`func_800179F4`) | opponent block load: WA_MRG sector 0x1D33 + 3*gDuel_bOpponentID, 3 sectors, into 0x801781D8 via func_80014E1C; layout deck u16[722]+pad, then 3 drop pools 1460 B apart (0x8017878C = SA-POW, +0x5B4 BCD, +0xB68 SA-TEC); ids are 1-based (Simon = 1, sector 0x1D36), sector 0x1D33 is a duplicate of Simon's block; all 156 stock pools sum to 2048 | `Duel_LoadOpponentPools`; `gDuel_awOpponentDeckPool` (keep), `gDuel_awSaPowCardDrops` (keep) + `gDuel_awBcdCardDrops` 0x80178D40, `gDuel_awSaTecCardDrops` 0x801792F4
- 0x80038530 | campaign-script opcode: reads one operand byte from the script stream (`*(*(a0 + 4*a0[0x58]))++`), stores it as gDuel_bOpponentID, then the BGM presets D_8009B36A / D_8009B374 from further bytes | `Script_OpStartDuel`
- 0x80011D40..0x80011DD0 | libcd `bios.c` debug strings, safe scratch | (note)

## Open questions

- Which script opcode number `func_80038530` is, and whether any other path writes `gDuel_bOpponentID` with bit 6 set (the free duel roster editor tool might).
- The template also carries per-opponent names in row 4 "not taken into account"; no name/portrait data is added anywhere, so bank-1 duelists are visually clones.
- Server side: nothing besides analytics.
