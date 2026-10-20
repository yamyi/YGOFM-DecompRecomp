# equipmaker - raw working notes (2026-09-03/04)

## Site JS (site/js/extend/tools/equipmaker.e1769d79.js, pretty-printed)

- component `EquipMaker`: `offset_base: 12079104` (0xB85800), `offset_movement: 481280` (0x75800),
  `offset = offset_base + offset_block*offset_movement`; fields list identical to fusionmaker
  (All Fields, Normal, Forest, Watesland, Mountain, Meadow, Sea, Dark); `originSet` = block to
  extract (default Normal), `setID` = where to save (0 = all 7).
- FileReader: SLUS `.11`, WA `.mrg` 36700160..45088768, xlsx. SLUS -> `getCardInfo` for names/types.
  `limitedCardsEquip` = type 23; `limitedCards` (targets) = type < 20; `showLimited` toggle.
- `extractData(block)`: `for (a = 0; a < 8448; a++) { s = u16[i+a]; a += 2; n = u16[i+a]; a += 2;
  if (s,n in 1..722) { if first time key s: collect n u16 members (dedupe), a += 2n-1; } else a = 1e7 }`
  then dataSet[id-1] = list or []. (a++ of the for loop supplies the missing +1.)
- `setObjectValues()`: per block: a = 0; for each card i with list: u16 (i+1), u16 len, members;
  then u16 0; then FF fill to 8448. `necessarySize = sum(4+2n) + 2 + 1`; refuse if 8448 - size < 1.
- add/addReverse keep lists sorted ascending and unique; removeFromDataSet(card) strips the card
  from every list; removeFromDataSetReverse empties the card's own list.
- BATCH: `list1` (filters) -> all added to `cardEquip`'s list. EXCEL: A = EQUIP, B = CARD.
- Network: analytics POST `api/v2/tools` only.

## Disc facts

- Real table start found by walking candidate starts in 0xB80000..0xB88000 for a run of
  (key,count) pairs in range ending in key 0: 0xB85000 gives 34 groups / 4041 members, ends at
  0xB8701C (terminator included), FF to 0xB87800. 0xB85800 (site) is inside equip 303's members.
- Loader stage 2 (0x800171A8 case 2): dest gDuel_awEquipTable 0x8017A1D8, length 0x2800, block
  +0x22000 (sum of stages 0+1 = 0x20000 + 0x2000). Stage 3 (fusion) follows at +0x24800 -> RAM
  0x8017C2D8 = 0x8017A1D8 + 0x2100, hence 8448 live bytes (the site's cap).
- RAM neighbourhood: 0x801781D8 opponent deck pool (3 sectors) | 0x801799D8 ritual (0x800) |
  0x8017A1D8 equip (0x2100) | 0x8017C2D8 fusion (0x10000) | 0x8018C2D8.
- Recomp `psx_fusion_db.c` reports 34 groups / 4041 memberships live in a duel: matches +0x22000,
  not the site's +0x22800 (which walks 16 "groups" / 169,045 "members" before hitting a zero).

## Script tests (scratch copy of WA_MRG.MRG)

    equip_table.py dump                  34 groups, 4041 members, 8220/8448, 7 copies identical
    export -> import --terrain all       cmp == stock (byte-for-byte; FF fill to 0x2800 like stock)
    verify stock csv                     OK
    custom csv (301:1,3; 302:2)          verify OK; lookup 301 3 -> equips, 301 12 -> does not
    restore                              cmp == stock
    dump --site-offsets                  warning: walk passes 0x2100 (garbage)
    dump on the raw .bin                 same numbers
