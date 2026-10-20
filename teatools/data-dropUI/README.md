# DROP EDITOR UI tool  (`dropUI`)

Route: `extend/tools/data/dropUI` (login-gated; tool id `tipo: 48`, comment board `guia: 58`).
Page title "TEA Online - DropUI", in-app title "Drop Editor".
Inputs: **WA_MRG.MRG** (`.mrg`, no size check — the drop-and-drop widget only tests the file
name suffix) and **SLUS_014.11** (`.11`). Both must be loaded before the editor unlocks, but the
SLUS is used only for *names* — every byte the tool writes goes into WA_MRG.MRG.
Output: `saveAs(dataviewWa.buffer, "WA_MRG.MRG")` — the whole 36 MB file back.
Script: `scripts/dropui.py` (verify / show / names / export / apply / unobtainable / randomize / balance).
Sibling folders documenting the same data from other angles: `drop`, `process-uniquedrop`
(different agent — cross-reference only, nothing here overlaps their tools).

Not to be confused with the site's `drop` tool: this one edits **all four** weight lists per
duelist, including the **opponent deck pool**, and it does it in the disc data file rather than
the EXE.

## 1. The data: 40 duelist records in WA_MRG.MRG

    baseOffset = 15,308,800 = 0xE99800   (in-file sector 7475, disc LBA 17577)
    record(char) = baseOffset + char * 6144            char = 0..39, 3 sectors each
    region       = 0xE99800 .. 0xED5800  (245,760 bytes, sectors 7475..7594, LBA 17577..17696)

Inside a record, four 722-entry `u16` weight lists 1460 bytes apart, then 304 more bytes:

| block offset | tool name | bytes | RAM once loaded | decomp symbol |
|---|---|---|---|---|
| `+0x0000` | DECK | 722×u16 + 16 pad | `0x801781D8` | `gDuel_awOpponentDeckPool` |
| `+0x05B4` | SA-POW | 722×u16 + 16 pad | `0x8017878C` | `gDuel_awSaPowCardDrops` |
| `+0x0B68` | BCD-PT | 722×u16 + 16 pad | `0x80178D40` | `gDuel_awBcdCardDrops` |
| `+0x111C` | SA-TEC | 722×u16 + 16 pad | `0x801792F4` | `gDuel_awSaTecCardDrops` |
| `+0x16D0` | *(not touched)* | 304 | `0x801798A8` | `gDuel_awRankScoreChange` |

`getSlotOffset(char, list, cardId) = baseOffset + char*6144 + list*1460 + 2*(cardId-1)`,
read with `getUint16(off, /*LE*/ true)`. Card ids are 1..722; index is `id-1`.
The JS constants are literally `_ = 722, w = 4, y = 2*_+16, k = 6144, x = 40`.

The 1460-byte stride is not a guess: `gDuel_awSaPowCardDrops - gDuel_awOpponentDeckPool` and each
subsequent gap in `~/ygofm-decomp/config/symbol_addrs.txt` is exactly `0x5B4` = 1460, and
`0x801781D8 + 0x1800 = 0x801799D8 = gDuel_awRitualData`, i.e. the whole 6144-byte record lands
contiguously in RAM.

**Verified on the real disc** (`~/YuGiOhForbiddenMemoriesRecomp/disc/…(USA).bin`, WA_MRG.MRG at
LBA 10102) with `scripts/dropui.py verify`:

    checked 160 lists at base 15308800 (0xE99800); 0 anomalies

i.e. all 40 × 4 lists sum to **exactly 2048** and every 16-byte trailer is zero. Sample stock bytes:

| what | file offset | first 16 bytes |
|---|---|---|
| char 0 DECK | `0xE99800` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` (card 9 = `48 00` at +0x10) |
| char 1 (Simon Muran) SA-POW | `0xE9B5B4` | `00 00 1b 00 00 00 00 00 00 00 00 00 00 00 00 00` |
| char 17 (Kaiba) SA-POW | `0xEB35B4` | `00 00 00 00 8c 00 46 00 8c 00 00 00 00 00 00 00` |
| char 38 (Nitemare) SA-TEC | `0xED391C` | `00 00 00 00 00 00 1e 00 00 00 00 00 00 00 00 00` |

Two facts the tool relies on and that hold on the stock disc:
- **record 0 and record 1 are byte-identical.** Record 0 is "Build Deck" — the starter-deck /
  build-deck pool — and is never loaded as an opponent. The tool's "unobtainable" scan therefore
  starts at character **1** (`S = 1, O = 39`).
- the 304-byte tail (`gDuel_awRankScoreChange`) is **identical in all 40 records** — it is not
  per-duelist data, it is just along for the 3-sector ride. It decodes as ten runs of
  `{s16 threshold, s16 value}` pairs with `32767` as the run terminator, then `0xFFFF` fill;
  `Duel_CalcRankScoreChange` (`0x80021558`, matched in `src/func_80021558.c`) indexes it by
  `a0 * 20`. Neither the site tool nor `scripts/dropui.py` writes it.

## 2. Duelist names come from the SLUS text table

`dropUI` never reads the WA_MRG for names. On `dataviewSlus` load it calls the shared
`chunk-common` helper twice:

```js
this.cards     = this.getCardInfo(slus, {includeDescription:true, parseDescription:true}) // ids 1..722
this.opponents = this.getCardInfo(slus, {desde:808, hasta:847})                            // 40 names
```

so the 40 duelist names are **entries 808..847 of the same name-pointer table the cards use**:
table base file offset `1,859,584` = `0x1C6000` (RAM `0x801D5800`), `u16` pointer per entry,
string at `base + ptr - 22528`, `0xFF`-terminated, `0xF8 xx` = colour escape.
Confirmed against `~/ygofm-decomp/SLUS_014.11` (`scripts/dropui.py names SLUS_014.11`):

    0 Build Deck    1 Simon Muran   2 Teana        3 Jono        4..6 Villager1..3
    7 Seto          8 Heishin       9 Rex Raptor  10 Weevil Underwood  11 Mai Valentine
   12 Bandit Keith 13 Shadi        14 Yami Bakura 15 Pegasus    16 Isis      17 Kaiba
   18 Mage Soldier 19 Jono 2nd     20 Teana 2nd   21 Ocean Mage 22 High Mage Secmeton
   23 Forest Mage  24 High Mage Anubisius         25 Mountain Mage      26 High Mage Atenza
   27 Desert Mage  28 High Mage Martis            29 Meadow Mage        30 High Mage Kepura
   31 Labyrinth Mage 32 Seto 2nd   33 Guardian Sebek 34 Guardian Neku   35 Heishin 2nd
   36 Seto 3rd     37 DarkNite     38 Nitemare    39 Duel Master K

That is the exact roster order `~/YuGiOhForbiddenMemoriesRecomp/tools/gen_drop_db.py` already
uses (offset by one, because it skips record 0), so the two agree independently.
Card stats come from the same helper: values at file `1,854,016` = `0x1C4A40`
(4 bytes/card: atk/def packed + type/star), guardian stars at `1,858,355` = `0x1C5B33`
(one byte, hi nibble / lo nibble), descriptions via the pointer table at `1,772,032` = `0x1B0A00`.

## 3. What the tool lets you do

| feature | what it does |
|---|---|
| Characters tab | pick a duelist, pick one of DECK / SA-POW / BCD-PT / SA-TEC, edit any card's weight (0..65535); live sum vs the 2048 target, and a per-list "show only assigned" filter + card-name search |
| Auto balance | `autoBalanceList()` rescales the non-zero entries by `target/sum`, `max(1, round())` each, then dumps the rounding remainder onto the currently heaviest entry so the sum lands exactly on `sumTarget` (default 2048) |
| Randomize | `randomizeList()` picks `20..69` distinct cards, gives each a random weight `1..100`, rescales to `sumTarget` the same way. "Randomize all" runs it over all 40 × 4, skipping lists whose `edit` flag is off |
| Summary tab | per duelist: the four sums, weakest/strongest deck monster by ATK+DEF, average ATK/DEF/level, and a "hard count" = how many cards have a drop weight of 1..4 in any of the three drop lists |
| Unobtainable tab | scans cards 1..722 against **characters 1..39, lists 1..3 only**, and reports cards no duelist can ever drop |
| Advanced panel | `baseOffset` (default 15308800) and `mascara` (default 0) are user-editable; changing either re-reads the whole file |
| `processConfig` | per list: `edit` (include in save/randomize) and `isCrypted`; plus `decryptionKey = 2512`, `decryptionBitShift = 3` |
| Save | rewrites **all** 40 × 4 lists that have `edit` set, then POSTs `api/v2/tools`, then downloads `WA_MRG.MRG` |

`mascara` and `isCrypted` exist for *mods* that store the weights obfuscated, not for the stock
game (both default to the identity):

    read :  isCrypted ? max(0, (v - 2512) >> 3)        : v - mascara
    write:  isCrypted ? (8*v + 2512 + rand(0..6)) & 0xFFFF : v + mascara

Note the write path adds a **random 0..6 jitter** in crypted mode, so a crypted round trip is not
byte-stable (the low 3 bits are noise the reader shifts away). `scripts/dropui.py --crypted`
mirrors this exactly, with `--seed` for reproducibility.

The stock unobtainable list, reproduced offline (`scripts/dropui.py unobtainable WA_MRG.MRG
--slus SLUS_014.11`), is **82 cards** — the Exodia limbs 17/18, the fusion-only monsters
(Summoned Skull, Gaia the Dragon Champion, B. Skull Dragon, Blue-eyes Ultimate Dragon,
Great Moth line, Thousand Dragon, Rabid Horseman, Gate Guardian, Black Luster Soldier…),
every ritual result 701..720, and both `721 Dark Magic Ritual` / `722 Magician of Black Chaos`.

## 4. What the game does with it

### 4.1 The load: 3 sectors per duelist, straight into RAM

`func_800179F4` (duel setup, `asm/asm_81F4.s`) at `0x80017AB0`:

    80017AB0  lui   v0, %hi(gDuel_bOpponentID)
    80017AB4  lb    v0, %lo(gDuel_bOpponentID)(v0)
    80017ABC  bltz  v0, .L80017AF0            ; no opponent -> skip the load
    80017AC0   sllv a2, v0, s0                ; s0 = 1  (set at 0x80017A20)
    80017AC4  addu  a0, zero, zero
    80017AC8  addu  a1, a0, zero
    80017ACC  addu  a2, a2, v0                ; a2 = id*2 + id = 3*id
    80017AD0  addiu a2, a2, 0x1D33            ; a2 = 7475 + 3*id     <-- in-file sector
    80017AD4  addiu a3, zero, 0x3             ; a3 = 3 sectors = 6144 bytes
    80017AD8  lui   v0, %hi(gDuel_awOpponentDeckPool)
    80017ADC  addiu v0, v0, %lo(gDuel_awOpponentDeckPool)
    80017AE0  sw    zero, 0x10(sp)            ; a4 = no completion callback
    80017AE4  sw    zero, 0x14(sp)
    80017AE8  jal   func_80014E1C             ; the CD read request
    80017AEC   sw   v0, 0x18(sp)              ; a6 = destination = 0x801781D8

`0x1D33` = **7475** and the stride is **3 sectors**, which is exactly the tool's
`baseOffset / 2048` and `CHAR_BLOCK_SIZE / 2048`. One duelist's record is resident at a time,
overwriting `0x801781D8..0x801799D8`. (The same `func_80014E1C` two instructions earlier loads
the 235-sector duel overlay from `0x16C6 + terrain*…`.)

### 4.2 The drop roll — `Duel_SelectCardDrop` `0x80021810`

Matched in `~/ygofm-decomp/src/weighted_random_pick.c`:

```c
s32 Duel_SelectCardDrop(s32 a0) {                 /* a0 = 0 SA-POW, 1 BCD-PT, 2 SA-TEC */
    struct Rec *r = &gDuel_awSaPowCardDrops[a0];  /* 1460-byte stride */
    s32 threshold = (rand() & 0x7FF) + 1;         /* 1..2048 */
    s32 sum = 0;
    for (i = 0; i < 722; i++) {                   /* slti $v0, $v1, 0x2D2 */
        sum += r->weights[i];
        if (sum >= threshold) return i + 1;
    }
    return 0;                                     /* nothing */
}
```

Consequences, all of them mod-relevant:
- **the list must total exactly 2048.** Under it, high rolls fall off the end and return 0 —
  "no drop". Over it, every card past the crossing point is unreachable, silently.
- a weight is literally `w/2048` probability; the tool's percentage column is exact.
- the roll only happens on a **won** duel (decomp finding F78; `0x80021810`'s single call site is
  the starchip branch of `Duel_MaybeEndOfDuel`).
- the tier is chosen by your win rank (`func_800218F0` at `0x80021A4C..0x80021C58`:
  `letter < 3 ? 1 : (score < 50 ? 2 : 0)`), i.e. tier 0 = S/A POW, 1 = B/C/D, 2 = S/A TEC —
  matching the tool's list order 1,2,3.

### 4.3 The DECK list — the opponent's deck, not a drop pool

`Duel_ShuffleDeck` `0x800243F4` (`asm/asm_14BF4.s` from `0x80024430`) builds the AI's 40-card deck
from `gDuel_awOpponentDeckPool` with the same weighted walk:

    copies[0..721] = 0                      ; 0x2D1 down to 0 -> 722 bytes cleared
    while (built < 40):                     ; slti $v0, $s3, 0x28
        threshold = (rand() & 0x7FF) + 1
        sum = 0
        for i in 0..719:                    ; slti $v0, $s1, 0x2D0   <-- 720, NOT 722
            sum += pool[i]
            if sum >= threshold:
                if copies[i] < 3: copies[i]++; emit card i+1
                break                       ; else: nothing emitted, outer loop retries

So the DECK list has its own quirks, distinct from the drop lists:
- **cards 721 and 722 can never appear in an opponent's deck** — the walk stops at index 719.
  Any weight the tool lets you put there is dead. (Same bound as the starter-deck generator,
  decomp finding F134.)
- **max 3 copies**; a 4th hit produces nothing for that iteration and the outer loop just rolls
  again, so a pool concentrated on few cards costs extra RNG pulls but still terminates.
- a pool summing under 2048 can miss, which also just re-rolls, so a short-summing DECK list is
  survivable where a short-summing *drop* list is not — but the tool validates both to 2048.

### 4.4 The 304-byte tail

`gDuel_awRankScoreChange` `0x801798A8` — `Duel_CalcRankScoreChange(a0, a1)` walks
`table + a0*20` reading `{s16 threshold, s16 value}` pairs 4 bytes apart while `a1 >= threshold`,
returning the paired value. Stock content begins
`05 00 0c 00 | 09 00 08 00 | 1d 00 00 00 | 21 00 f8 ff | ff 7f f4 ff` = `(5,12) (9,8) (29,0)
(33,-8) (32767,-12)`. Identical in all 40 records; the site tool never writes it, and neither
should a mod that only wants drops.

## 5. Recomp options

The recomp **already implements most of this** — `src/psx_drop_missing.c` + `src/psx_drop_edits.c`
+ `src/psx_drop_viewer.c`, with `tools/gen_drop_db.py` baking the tables off the player's own disc
(its `DROP0 = WA_MRG_BASE + 15310260` is `0xE99800 + 1460`, i.e. tier 0; the deck pool is its
"table 0 at −1460"). The mechanism there is the right one and this tool changes nothing about it:

- one duelist's record is resident at a time, so **you patch RAM, not the disc file**:
  `psx_mod_write_half(0x8017878C + tier*1460 + 2*i, w)` from a throttled tick, keyed on a
  fingerprint over the four resident arrays (drops alone are ambiguous — Heishin/Heishin 2nd and
  Villager3/Duel Master K share drop tables byte for byte, which is exactly why the fingerprint
  includes the DECK list).
- the fingerprint doubles as the re-entry guard: a rewritten table no longer matches stock.

What `dropUI` covers that the recomp does **not** yet:

1. **The DECK list (`gDuel_awOpponentDeckPool`, `0x801781D8`).** `psx_drop_edits.c` addresses
   tiers 1..3 only (`table = tier + 1`, "table 0 is the deck pool"). Editing table 0 with the
   identical `psx_mod_write_half` loop gives you *opponent deck editing* — arguably the bigger
   feature, and it needs no new plumbing: extend `apply_tier()` to `tier = -1` and add a
   `[Duelist] deck` section to `drop_table_edits.ini`. Enforce sum == 2048 and **reject any weight
   on cards 721/722** (unreachable, see 4.3), and keep the ≤3-copies reality in the UI copy.
2. **Duelist 0 (Build Deck).** Never loaded as an opponent, so it cannot be patched in RAM at all;
   its DECK row is the *starter/build-deck* pool consumed by the name-entry module's generator.
   See the `initial-deck` folder — that one lives in the 0x80168000 module, not here.
3. **Whole-file export/import.** For anyone who wants an actual patched WA_MRG.MRG rather than a
   runtime mod, `scripts/dropui.py export` / `apply` is a byte-exact round trip
   (verified: randomize → apply(exported json) reproduces the stock file byte for byte).

A native replacement worth considering instead of table rewriting: hook `Duel_SelectCardDrop`
itself. It is a pure function of `(tier, rand)`, so a native version can lift the 2048 total, the
722 bound and the "0 = nothing" cliff, and read weights straight from the player's ini without
ever touching guest memory. Same for `Duel_ShuffleDeck`'s 720 bound and 3-copy cap.

## 6. Server side

| call | when | effect |
|---|---|---|
| `POST api/v2/toolcontrol/validate` | on mount | must return `{ok:true}` or the page redirects (401 → `/extend/info/join`, else `/extend`) |
| `POST api/v2/tools` `{version, tipo:48, data}` | Save | analytics; **the WA_MRG download only happens in its `.then()`**, so a failed POST silently yields no file |

Nothing else leaves the browser — the 36 MB file is never uploaded.

## 7. Decomp findings (proposed)

- `0x80017AB0..0x80017AEC` (in `func_800179F4`) | the per-duelist drop/deck record load:
  `sector = 0x1D33 + 3*gDuel_bOpponentID`, 3 sectors, dest `gDuel_awOpponentDeckPool`; skipped
  when `gDuel_bOpponentID < 0`. Confirms WA_MRG offset `0xE99800` = in-file sector 7475 = disc
  LBA 17577 and a 6144-byte per-duelist stride, verified against the retail disc (all 160 lists
  sum to 2048, all 16-byte trailers zero) | proposed `Duel_LoadOpponentTables` for the block, or a
  comment on `func_800179F4`
- `0x801798A8` `gDuel_awRankScoreChange` | is **loaded from the disc as bytes `+0x16D0..+0x1800`
  of the same 3-sector duelist record**, not initialised by code, and is byte-identical in all 40
  records — so it is effectively a constant that happens to be re-uploaded every duel. Explains
  why the record stride is 6144 and not 5840 | *(fact for descriptions.md; symbol name unchanged)*
- `0x801781D8` `gDuel_awOpponentDeckPool` | independently confirmed as list 0 of the record and as
  the AI deck-build source; `Duel_ShuffleDeck`'s walk is bounded at **720** (`slti 0x2D0`) with a
  3-copy cap, so cards 721/722 are undeckable — the same bound F134 records for the starter deck |
  *(quirk for descriptions.md)*
- text ids **808..847** of the card-name pointer table (base file `0x1C6000`, RAM `0x801D5800`) are
  the 40 duelist names, in the same order as the WA_MRG records (0 = "Build Deck") | proposed
  `gText_apCardNames` entries 808..847 = duelist names; useful for `notes/research/descriptions.md`
- record **0 == record 1** byte for byte on the retail disc, and record 0 is never loaded as an
  opponent (`bltz` guard on `gDuel_bOpponentID`) — it is the Build Deck / starter pool | *(fact)*

## 8. Open questions

- What consumes `gDuel_awRankScoreChange`'s ten 20-byte rows — `Duel_CalcRankScoreChange(a0, …)`'s
  `a0` is presumably the scoring category (the five duel-rank components), unverified.
- `dropUI` loads SLUS_014.11 purely for names but still *requires* it before unlocking the editor;
  nothing in the editor writes to it. Probably a UX decision, but worth re-checking against a
  future version in case a SLUS-side write appears.
- `mascara` / `isCrypted` target third-party mods that obfuscate their WA_MRG tables. Which mods,
  and whether the `+ rand(0..6)` jitter on write is deliberate anti-diff or just sloppiness, is
  unknown; no such mod was available to test.
- The Summary tab's "hard count" (cards with drop weight 1..4) has no in-game meaning I could
  find — it looks like a heuristic for "rare drops", not a game constant.
