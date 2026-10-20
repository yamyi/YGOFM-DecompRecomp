# fusionmaker - raw working notes (2026-09-03/04)

## Site JS (site/js/extend/tools/fusionmaker.1fb421ae.js, pretty-printed)

- component `FusionMaker`: `offset_base: 12089344` (0xB88000), `offset: offset_base + 481280*offset_block`
  (481280 = 0x75800 = 235 sectors), `fields` = All Fields(0), Normal(1), Forest, Watesland(sic),
  Mountain, Meadow, Sea, Dark(7). `originSet` picks the block to extract (default 1 = Normal),
  `setID` picks where to save (0 = blocks 0..6).
- FileReader props: SLUS `.11` min 1572864 max 3145728; WA `.mrg` min 36700160 max 45088768;
  xlsx max 20971520. SLUS only feeds `getCardInfo` (names, atk/def/type/attr/level/color, descriptions
  when `iHaveNasaPc`), types 768..791 and stars 792..801 strings.
- `extractData(block)`: for t = 1..722: i = u16 index[t]; if i: s = byte[i]; n = byte[i+1]; o = s;
  r = 0; if s == 0 { o = 511 - n; r = 1 }; c = ceil(o/2) groups at a+i+1+r+5*d; decode
  v = 256*(u&3)+f, g = 256*(u&12)/4+p, b = 256*(u&48)/16+m, y = 256*(u&192)/64+h; accept
  first half if v,g in 1..722 and t <= v; second half same unless it is the dangling half of an
  odd record (d == c-1 && c > o/2) - that half goes to `dataSetBug` (GLITCH FUSIONS panel) when it
  decodes to valid ids and the pair is not already present.
- `setObjectValues()`: per block: index[0] = 0; a = 1446; for each card i with entries: index = a;
  keys sorted ascending; count byte(s); groups of 5 for pairs of entries; 3 bytes for a trailing odd
  entry; results = `t["c"+k][0]`; then FF fill a..65536.
- `necessarySize` = 1446 + sum(5*floor(n/2) + (n<256?1:2) + (odd?3:0)); `salvar()` refuses if
  65536 - necessarySize < 1 ("MEMORY OVERFLOW").
- BATCH TEMPLATE: `list1 x list2` (filters atk/def range, type, attr, level range, name substring,
  colour, id list, description substring) -> one `cardResult`; pair stored under the smaller id;
  `overwrite` flag decides whether existing pairs are replaced. CHECK = simulateList (count only).
- EXCEL: columns A/B/C rows 2..N -> {c1,c2,f}; ids outside 1..722 dropped; "Replace existing" flag.
- removeFromDataSet(card): removes the card's own record and every entry where it is partner or
  result of the FIRST entry (`a[e][0] !== t`) - quirky but that is what it does.
- Network: only `api/v2/tools` analytics POST via mixin `saveChange` on `create`.

## Disc / file facts

- WA_MRG extracted from the .bin with `extract_overlay.walk_iso/sector` (LBA 10102, 0x2400000 B);
  starter-set sanity check at 0xF92BD4 = 16 ok.
- Pattern search: the 32 bytes at 0xB88000 recur at +k*0x75800 for k = 0..6 only. Same for the
  real table start 0xB87800 and the real equip start 0xB85000.
- Real fusion index found by scanning 0xB86000..0xB88800 for a 723-entry u16 array whose nonzero
  entries are >= 1446, monotonic, and whose records decode with partner >= card and result in 1..722:
  exactly one hit, 0xB87800 (578 cards, 25131 pairs, 65004 B incl. 3-byte last tail => 65002 used).
- 7 block copies (0xB63000 + k*0x75800) differ only in sectors +0x65800..+0x6F800 (20 sectors).
- Block sector map: 0 data(VRAM) .. 36 zero, 37.., 68 (+0x22000) equip `2d 01 3f 00`, 69 (+0x22800)
  `0f 02 10 02` (site's equip base = mid-list), 73 (+0x24800) fusion index, 74 (+0x25000) site's
  fusion base = mid-body, 105 (+0x34800) ritual `9e 02 1b 00 26 00 3a 00 6c 01`, 106..107 zero,
  108 (+0x36000) VRAM, 140 (+0x46000) overlay header `18 00 00 00 00 10 00 00`, 203.. terrain gfx.
- 8 x 32-byte rows at block +0x21E00 (0xB84E00): u16 rows `0, a,b,c,d,e,f,g, 0x98C6/0x9CE7, 0x9084,
  0x3E0 x6` - unknown, sits inside stage 1's 0x2000 buffer (which LoadImage2 uploads to VRAM
  (0x100,0xF0) 256x16, so it is image data).

## Loader (decomp asm)

- `func_800179F4` (asm/asm_81F4.s, nonmatching): a0=0,a1=0,a2 = 235*terrain + 0x16C6, a3 = 0xEB,
  stack: cb = 0x800171A8, 0, 0 -> `func_80014E1C`; then `func_800137E4`; then if opponent >= 0:
  `func_80014E1C(0,0, 0x1D33 + 3*opp, 3, 0, 0, gDuel_awOpponentDeckPool)`.
- `func_8001798C` (match/matched): `func_80014E1C(0,0, D_8009B364*235+0x16C6, 0xEB, 0x800171A8,0,0)`.
  No `jal` (0x0C005E63) in SLUS or in the duel overlay image; no pointer 0x8001798C in SLUS.
- `0x800171A8` (asm/nonmatchings/select_sound_preset): `sltiu v0,a1,0xD`; jump table at
  D_800100A8+0x18 = 0x800100C0: 800171E4 80017250 80017278 800172D0 800172F8 80017320 80017348
  8001739C 800173C8 800173DC 8001741C 80017494 800174D4. Each case stores dest to 8(s1)/0xC(s1),
  length to 0x1C(s1), mode byte 0x46(s1) = 1 (RAM) or 2 (VRAM via 0x800-byte ring at *D_8009B118,
  rect fields at 0x30/0x32 = x,y and 4/6 = w,h), and toggles bits in D_8009B0F4.
  Case 2: LoadImage2(D_800E9D70 rect 0x100,0xF0,0x100,0x10, *D_8009B118); dest gDuel_awEquipTable,
  len 0x2800. Case 3: dest gDuel_aFusionTable, len 0x10000. Case 4: gDuel_awRitualData, 0x800.
  Case 7: len 0x16000, dest *(D_800100A8+0x134) = 0x80146000. Case 8: gAiScript_abHandScript 0x1800.
  Case 9: D_801A9800 0x1800. Case 11: len 0x2800 dest D_80010000_arr[0] = 0x80100000.
  Case 0: 0x20000 VRAM (0x300,0x100,0x40,0x10); case 1: 0x2000 RAM; case 5: 0x1000 RAM; case 6:
  0x10000 VRAM (0x200,0x100); case 10: 0x4000 VRAM (0x340,0); case 12: 0x10000 VRAM (0x280,0x100).
  Sum = 0x75800.
- Arena table at 0x80010000: 80100000 80140000 80180000 8013A000 8017A000 8013B000 8017B000 80135000.

## Lookup semantics checked

- fusion_table_lookup emulated over all 261,003 unordered pairs on the stock table: equals the
  "intended" DataSet except 15 pairs (tail overlap). Card 22: index 0x1BA2, count 1, bytes
  `01 | 00 52 d9 | 1f 48 ...` -> second-half test reads partner 0x1F=31, result 0x48=72.
- 292 odd records are followed by the next record 3 bytes after their last full group (never 5);
  the last record (card 712, count 1) is followed by FF fill. Classification of the 293 trailing
  halves: 30 decode to result 0; 245 decode to a partner id BELOW the record's own card id, which
  the sorted lookup never consults (the pair is asked of the other card's record); 1 partner is
  out of range; 2 partners already appear earlier in the same record so the loop returns first;
  15 are reachable and are the real glitch fusions. A raw "nonzero result, partner in 1..722, not
  already a pair in this record" scan gives 260 - the partner-ordering filter is the whole gap.
  The 15 also fall out of the exhaustive emulation over all 261,003 pairs (identical sets).
- Stock entry order inside a record is ascending by partner except card 338: (338,688),(434,376),
  (343,326). The script keeps CSV order so `export` -> `import --terrain all` reproduces the file.
- 50 pairs (a,a) exist in stock; the template's example rows `1,1,380` / `4,4,444` are just examples.

## Script tests (scratch copy of WA_MRG.MRG)

    fusion_table.py dump                 578 cards, 25131 pairs, 65002 used, 15 glitch, 7 copies identical
    export -> import --terrain all       cmp == stock (byte-for-byte)
    verify stock csv                     OK, 15 glitch (expected)
    import --safe-tails (stock set)      MEMORY OVERFLOW at card 655 (needs 586 B, 534 free) - documented
    custom 3-row csv, terrain 3          verify OK; lookup 2 700 -> 5 on terrain 3, none on terrain 0
    restore                              cmp == stock
    dump --site-offsets                  722 "cards", 54831 pairs, -442 free (garbage, as expected)
    dump on the raw .bin                 same numbers as on the extracted file
