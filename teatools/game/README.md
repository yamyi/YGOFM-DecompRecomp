# Other Fixes tool (site name "OtherFixes"; the route is `extend/tools/game`)

Route: `extend/tools/game`. Input: SLUS_014.11 (accepts `.11`, 1,902,591..2,097,152 bytes).
Page version V.220214. Three visible toggles plus one hidden value, all client-side, file
downloaded back. Not the "game" editor the route name suggests: the component is called
`OtherFixes` and the page title is "small modifications to the game".
Script: `scripts/other_fixes.py` (inspect / apply / restore on a SLUS copy; restore is byte-exact).
Raw session notes: `NOTES-raw.md`.

Status: decoded, every stock byte verified against the retail SLUS, consumers located in the
decomp, DMK/Simon pool identity verified on the disc; not yet built as a recomp mod.

## 1. "Enabled cards 721 and 722" -- CPU deck generator draws the last two ids

| | |
|---|---|
| file offset | 0x14CCC (2 bytes) |
| RAM | 0x800244CC, inside `Duel_ShuffleDeck` (0x800243F4) |
| stock word | `2A2202D0` = `slti v0, s1, 0x2D0` (loop while index < 720) |
| patched word | `2A2202D2` = `slti v0, s1, 0x2D2` (index < 722) |

`Duel_ShuffleDeck(src, dst, perm)`: when `src == NULL` it *generates* the CPU deck from
`gDuel_awOpponentDeckPool` (0x801781D8, 722 u16 weights) with the same weighted walk as the
starter-deck generator (initial-deck README): 40 draws, threshold `(rand() & 0x7FF) + 1`, walk
`weight[0..719]`, max 3 copies (a 4th copy re-rolls), then 160 random swaps. Ids 721/722 sit at
indices 720/721 and are never reached, whatever weight a mod gives them. The copies array on the
stack is 722 bytes, so the bound can be raised to 722 without any other change.

    800244C8  addiu s1, s1, 1
    800244CC  slti  v0, s1, 0x2D0      ; <-- patch: 0x2D2
    800244D0  bnez  v0, .L80024474     ; next weight
    800244D4   addiu v1, v1, 2

The player-side starter generator (`0x8016A930`, name-entry module) has the same 720 bound and
is **not** touched by this tool.

## 2. "DMK with his own deck" -- stop copying the player's deck for opponent 39

| | |
|---|---|
| file offset | 0x8585 (1 byte: high byte of the immediate) |
| RAM | 0x80017D84, inside `func_800179F4` (duel bootstrap) |
| stock word | `28620027` = `slti v0, v1, 0x27` (opponent id < 39) |
| patched word | `28620127` = `slti v0, v1, 0x127` (opponent id < 295: always true) |

Context (stock). `v1` = `gDuel_bOpponentID` (s8), `a0` = `gDuel_awPlayerDeck` 0x801D0200:

    80017D7C  addiu a0, v0, 0x0200          ; player deck (save block)
    80017D80  sw    a0, 0x2D0(gp)           ; player record pointer
    80017D84  slti  v0, v1, 0x27            ; <-- patch
    80017D88  bnez  v0, .L80017D94
    80017D8C   addu a1, zero, zero          ; opp < 39 : CPU source = NULL -> generate from pool
    80017D90  addu  a1, a0, zero            ; opp >= 39: CPU source = player's own deck -> copy
    80017D94  jal   Duel_ShuffleBothDecks   ; (a0 = player deck, a1 = CPU source or NULL)

`Duel_ShuffleBothDecks` calls `Duel_ShuffleDeck(a0, gDuel_awPlayerShuffledDeck, ...)` for the
player and `Duel_ShuffleDeck(a1, +0x50, ...)` for the CPU; a non-NULL `a1` means "copy these 40
ids" instead of "draw from the pool". Duel Master K is the only 1P opponent with id >= 39, so the
stock game hands him your deck. With the patch he draws from his own pool like everyone else.

Where the pool comes from (same function, 0x80017AC4): `func_80014E1C(0, 0, 0x1D33 + 3*id, 3,
0, 0, gDuel_awOpponentDeckPool)` -- a 3-sector CD read of WA_MRG.MRG in-file sector
`0x1D33 + 3*id` (WA offset `0xE99800 + id*0x1800`, disc LBA `17569 + 3*id`). Each record is
4 x 1444-byte weight tables (deck pool, then the three drop pools), each summing to 2048.
Verified on the US disc: DMK's deck pool (sector 0x1DA8, WA 0xED4000) is byte-identical to
Simon's (sector 0x1D36, WA 0xE9B000) -- which is why the site says "by default DMK's deck is equal
to Simon's, modify it in the WA file". The 2P path (`gDuel_bOpponentID < 0`) is unaffected: it
passes both players' save decks (0x801D1200 / 0x801D2200).

## 3. "EXODIA STEC" -- Exodia win scores -127 instead of +40

| site | file offset | RAM / function | stock | patched |
|---|---|---|---|---|
| a | 0x9BDC | 0x800193DC `func_80018FEC` | `240328` `addiu v1, zero, 0x28` | `2403FF81` = `li v1, -127` |
| b | 0x11DF4 | 0x800215F4 `Duel_CalcRankScore` | `24020028` `addiu v0, zero, 0x28` | `2402FF81` |
| c | 0x8BD0 | 0x800183D0 `func_8001825C` | `24020028` `addiu v0, zero, 0x28` | `2402FF81` |

The three sites share one constant, the per-player **outcome byte** `D_800E9FF0[player].b0`
(records are 0x20 bytes, player index at `gp+0x2CD`):

- (a) is the Exodia-victory handler: stores 40 into the outcome byte, plays BGM 0x7310 (track
  0x31 "Exodia"), sets the end-of-duel mode (`D_8009B369 = 1`, `D_8009B269 = 3`, `D_8009B26C = 1`).

        800193DC  addiu v1, zero, 0x28      ; <-- (a)
        800193F0  sb    v1, 0x0(v0)         ; D_800E9FF0[player].b0 = 40
        800193F8  addiu a0, zero, 0x7310    ; Exodia theme

- (b) `Duel_CalcRankScore` seeds the score with 50, **adds the outcome byte** (`lb`, signed), then
  the per-statistic deltas from `gDuel_awRankScoreChange` via `Duel_CalcRankScoreChange`. Before
  that it compares the byte with 40 -> result-type code 0x42 into duel object +0x35 (0x40 default,
  0x41 when the byte is -40, i.e. the CPU's Exodia).
- (c) `func_8001825C` (duel-screen setup) compares the byte with 40 to pick the Exodia
  win presentation (`gp+0x332 |= 0x2000`, table lookup by player).

Patching all three keeps the game's own equality tests consistent (the win is still recognised
as Exodia at (b) and (c)) but the `lb` at 0x800215F0 now adds -127 instead of +40, so the total
falls far below the S-TEC boundary. Community rank table (not re-derived here): S-TEC <= 9,
A-TEC 10-19, B-TEC 20-39, C 40-59, B-POW 60-79, A-POW 80-89, S-POW >= 90; base 50; Exodia +40.
The -40 compare at 0x80021618 (opponent's Exodia) is not patched. The tool reports the toggle as
active only when all three sites read `81 FF`.

## 4. Hidden: guardian-star bonus amount (`bonus_t`, no UI)

| file offset | RAM / function | stock | meaning |
|---|---|---|---|
| 0x10770 | 0x8001FF70 `func_8001FDB4` | `slti v0, v0, 0x1F4` | count-up cap of the "+500" popup |
| 0x10784 | 0x8001FF84 `func_8001FDB4` | `addiu v0, zero, 0x1F4` | value stored when the cap is reached |
| 0x1D3D0 | 0x8002CBD0 `Duel_CalcGuardianStarMatchup` | `addiu v0, zero, 0x1F4` | the +500 return |

`Duel_CalcGuardianStarMatchup(a, b)` returns +500 / -500 / 0 (the -500 at 0x8002CBE4 is **not**
patched). `func_8001FDB4` spawns the star icon (`(stats >> 22) & 0xF` / `(stats >> 18) & 0xF`
from `gDuel_adwCardStats`) and counts `gp+0x2C8` up by 16 per frame until 500, writing it into
the widget's 0x36/0x38 fields. The page reads the three u16s; if they agree it keeps the value,
else it falls back to 500, clamps 0..5000 and writes all three back on every SAVE. With a stock
file that is a no-op; the only user-visible effect is that an inconsistent file gets normalised
to 500. `other_fixes.py apply --gs-bonus N` exposes it.

## Recomp options

1. Base-EXE code, so all of it can be applied once at startup with `psx_mod_write_code_word`:
   `0x800244CC <- 0x2A2202D2`, `0x80017D84 <- 0x28620127`, `0x800193DC <- 0x2403FF81`,
   `0x800215F4 <- 0x2402FF81`, `0x800183D0 <- 0x2402FF81`.
2. Nicer DMK: instead of widening the compare, give id 39 a real pool -- the sector formula
   `0x1D33 + 3*id` already yields a distinct record for 39 (it is just a copy of Simon's on the
   retail disc), so a disc-side or CD-hook replacement of that 3-sector record is the clean fix
   and needs no code patch at all.
3. Nicer Exodia: a hook at the `lb` in `Duel_CalcRankScore` (0x800215F0) can substitute any
   score contribution without disturbing the three equality checks (leave the constants at 40,
   change only the added value).
4. Guardian star: patch both branches of `Duel_CalcGuardianStarMatchup` (+N at 0x8002CBD0, -N at
   0x8002CBE4) and the popup cap/step (0x8001FF60 `addiu v0, v0, 0x10` is the step) if the
   count-up should still end on the new value.

## Decomp findings (proposed)

- `0x800244CC` | `Duel_ShuffleDeck` generate path bound is 720 (`slti 0x2D0`), same 720-not-722
  limit as the starter generator F134; copies array is 722 bytes | (fact for the F134 family)
- `0x80017D84` | `func_800179F4`: `gDuel_bOpponentID < 39 ? generate : copy player deck` chooses
  `Duel_ShuffleBothDecks`' second argument; DMK (39) is the only copy case in 1P | `Duel_InitDecks`? (function name)
- `0x80017AC4` | CPU pool CD read: WA in-file sector `0x1D33 + 3*id`, 3 sectors, into
  `gDuel_awOpponentDeckPool`; record = 4 x 722 u16 weight tables (deck, drops) each summing 2048;
  DMK's deck table == Simon's on the retail disc | `WA_SECTOR_OPPONENT_RECORD = 0x1D33`
- `D_800E9FF0[p].b0` | signed outcome score term added to the rank score base 50; 40 = Exodia win
  (written at 0x800193F0), -40 = Exodia loss (compare 0x80021618) | `gDuel_aPlayerRecords[].bOutcomeBonus`
- `0x80018FEC` @0x800193BC..0x8001943C | Exodia victory handler (outcome 40, BGM 0x7310, end mode) | part of `Duel_UpdateEndOfDuel`?
- `0x8001FDB4` | guardian-star bonus popup: star icon from card stats bits 22..25 / 18..21, counter
  `gp+0x2C8` += 16/frame to 500 | `Duel_ShowGuardianStarBonus`
- duel object `+0x34..+0x36` | result-type codes 0x44/0x40/0x45, +0x35 := 0x42 (Exodia win) / 0x41 (Exodia loss) | (facts)

## Open questions

- What (besides Exodia) writes `D_800E9FF0[p].b0`: the other writers (func_80018608, func_800208D4,
  func_80025F3C, asm_13944/7DA0/DE70/918C sites) were not read; normal wins presumably leave 0.
- Exact rank thresholds: `gDuel_awRankScoreChange` (0x801798A8) lives in the disc-loaded 0x80168000
  region, not in the EXE, and the grade cut-offs were not located; the table above is the community one.
- Server side: only the analytics POST to `api/v2/tools` (tipo 4); nothing else leaves the browser.
