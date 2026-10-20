# Raw notes: FIELD tool, session 2026-09-04

- Page data(): body_offset 0xBC8800, header_offset 12388096 (= 0xBD0700 = body + 0x7F00,
  NOT 0xBD0800 -- a hand conversion error cost one garbage render), move 481280 (0x75800 =
  235 sectors), fieldID 0..6. parts: top rows 0..104, bottom 104..208, middle 208..254
  (canvas 256x104 / 256x104 / 256x46), all 4bpp (ppb 2), bytes_width 128.
  `duplicates`: index 0 -> [0,32], 1 -> [64,96], 2 -> [128] = CLUT slot byte offsets written.
  Composite preview `C`: top at y 0, bottom at y 149, middle (45 rows) at y 104.
- getFieldValues: t = 528852 = 0x811D4, 20 rows x 6 int8, displayed x10; writeFieldValues
  writes value/10. typeList = getCardInfo(desde 768, hasta 791) from the global bank
  (chunk-common "5e6c" mixin: same table at 1859584, same 0x5800 subtraction).
- Decomp: gDuel_aTerrainBoost = 0x800909D4 (asm at asm/asm_1517C.s: addiu a0,0x9D4;
  index type*6-1+terrain; result *10). Duel_GetTerrainBoost guard: gDuel_bTerrain != 0,
  type < 20. Dumped stock table matches the known FM field bonuses, so site offset == decomp.
- Terrain block: func_8001798C: D_8009B364*235 + 0x16C6, count 0xEB, callback
  select_sound_preset (stub). WA 0xB63000 + t*0x75800: sectors 0..202 identical across the
  7 copies; 203..218 (0xBC8800.. for t=0) + 222, 226, 230, 232 differ. Texture rows 0..253
  data, 254..255 = CLUT slots (5 used, all different, no STP, no zero entries).
  Renders: t=0 yellow stone 5x2 zones + centre band, t=1 green forest tiles.
- "Image Name": body 11866112 = 0xB51000, CLUT 11930016 = 0xB609A0 (16 greys: 0000 1400
  2118 8424 4834 c628 0831 6b39 cf45 305e 945a d65e 1867 5a6f bd77 ff7f). Raw region render
  shows duel UI text sprites (MEADOW/WASTELAND/MOUNTAIN/FOREST/SEA/DARK, FIELD, CAUTION!,
  arrows, a warning triangle, a "no" sign). Chunk list `w` (46 pieces, ct2) maps them onto
  a 56x168 canvas; `b` (15 pieces, parts2) is only used by an unreachable index==3 path.
- Assets /Assets/img/field/field-0N.png, 256x45.png, field-repeat.png,
  templates/field02.png, field03.png: all 302 -> login page (not mirrored).
- Tests: terrain 3 export/import/export diff 0; atlas export/import/export diff 0 after
  the transparent-index fix; restore all (7 textures + atlas) -> cmp identical; set-boost
  (Dragon Forest +500, Reptile Yami -50) and restore-boost -> identical SLUS.
