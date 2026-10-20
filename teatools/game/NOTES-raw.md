# Other Fixes (extend/tools/game) -- raw notes, 2026-09-04

- Chunk `site/js/extend/tools/game.3e0a5f64.js`, component `OtherFixes` (name in code: FreeDuelMusic, copy-paste).
  SlusReader accepted ".11" 1902591..2097152. Methods: getLimit/setLimit (85196), getDMK/setDMK (34181),
  getExodia/setExodia (39900, 73204, 35792), getBonus/setBonus (67440, 67460, 119760; bonus_t has no
  input in the template; computed `bonus` clamps 0..5000; salvar() calls setLimit,setDMK,setBonus,setExodia).
- Stock bytes read from ~/ygofm-decomp/SLUS_014.11:
    0x14CCC d0 02 22 2a  slti v0,s1,0x2D0   (Duel_ShuffleDeck 0x800244CC)
    0x8584  27 00 62 28  slti v0,v1,0x27    (func_800179F4 0x80017D84; tool writes byte 0x8585)
    0x9BDC  28 00 03 24 / 0x11DF4 28 00 02 24 / 0x8BD0 28 00 02 24
    0x10770 f4 01 42 28  slti v0,v0,0x1F4 ; 0x10784 f4 01 02 24 ; 0x1D3D0 f4 01 02 24
- Duel_ShuffleDeck(a0 src, a1 dst, a2 perm): a0==0 -> zero 722 copies (s1=0x2D1 loop), s7=gDuel_awOpponentDeckPool,
  40 draws (slti s3,0x28), threshold rand()&0x7FF+1, walk 720 (slti s1,0x2D0), copies<3 else redraw;
  a0!=0 -> copy 40 u16; then 160 swaps (slti s1,0xA0) with rand()%40 pairs.
- Duel_ShuffleBothDecks(a0,a1): ShuffleDeck(a0, gDuel_awPlayerShuffledDeck 0x80177FE8, -0x54) ; ShuffleDeck(a1, +0x50, -0x2C).
- func_800179F4: s0=1; if D_8009B369==1 skip load; gDuel_bOpponentID>=0 -> func_80014E1C(0,0,opp*3+0x1D33,3,0,0,pool)
  (sllv a2,v0,s0 = opp<<1, + opp). 0x80017D30..: opp<0 -> 2P path (0x801D1200/0x801D2200 -> gp+0x2D0/0x2D4);
  else a0=0x801D0200, a1 = opp<39 ? 0 : a0 ; jal Duel_ShuffleBothDecks.
- Disc check: WA sector 0x1D33+3*id, 3 sectors = 4 x 1444 B u16 tables each summing 2048; id 39 deck table == id 1 (Simon).
- Exodia: func_80018FEC @0x800193BC..: func_800156DC(); sh 0x309 -> D_800EF658; sb 0x28 -> D_800E9FF0[gp+0x2CD].b0;
  sb player -> gp+0x25D; clear +0x12/+0x14 of the other player's record; func_800472A8(0x7310); func_80059C18(0x7310);
  D_8009B369=1, D_8009B269=3, D_8009B26C=1.
  Duel_CalcRankScore: +0x34..36 = 44 40 45; lb rec.b0 == 0x28 -> +0x35=0x42; == -0x28 -> 0x41; +0x2C=+0x30=50; += lb rec.b0;
  then Duel_CalcRankScoreChange(k, stat) for fields +0x17(lb) +0x13(lh) +1 +2 +3 +7 +8 +4 +5 +0 ... for both players (s5<2).
  Duel_CalcRankScoreChange(row a0, stat a1): table gDuel_awRankScoreChange 0x801798A8 (in the disc-loaded region, not in EXE),
  row stride 20, {s16 threshold, s16 value} pairs; returns value of first threshold > stat.
  func_8001825C @0x800183C4: lw v0,0x2C0(gp) (=&D_800E9FF0[player]) lb b0 == 0x28 -> gp+0x332 |= 0x2000, table D_800907D8[player*20+s2] -> D_801A7AD8 records.
- GS bonus: func_8001FDB4 reads gDuel_adwCardStats bits (>>22)&0xF / (>>18)&0xF, func_8002C604(0xE) widget, +0x1A = star-1,
  gp+0x2C8 = 0, flags |= 0x60 in gp+0x26C; then per frame (flag 0x40) counter += 0x10, slti 0x1F4 -> clamp to 0x1F4 and clear 0x40,
  store to D_800EA0E8[gp+0x2B1]+0x36/+0x38. Duel_CalcGuardianStarMatchup returns 0x1F4 (0x8002CBD0) / -0x1F4 (0x8002CBE4) / 0.
- The site posts to api/v2/tools (tipo 4) after every save; nothing else server-side.
