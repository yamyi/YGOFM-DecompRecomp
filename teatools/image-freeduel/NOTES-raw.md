# Raw notes: FREE DUEL image tool, session 2026-09-04

- Page: FaceEditor component. SLUS reader (.11, min 1,677,721.6) -> getNames(): table at
  t=1859584 (0x1C6000), for n in 808..848: ptr = u16[t+2n]; c = ptr - 22528 (0x5800);
  name = readName(c+t) => file 0x1C0800 + ptr => RAM 0x801D0000 + ptr; table RAM 0x801D5800
  (gText_aGlobalOffsets, F118). i = ptr[848]-ptr[808]-40 = "available chars".
  Tile i: body_offset = 16076800 + 2432*i (0xF55000), pallete_offset = body + 2304.
- Charset map B in the JS (l<code>: char): 1 e, 2 t, 3 a, 4 o, 5 i, 6 n, 7 s, 8 r, 9 h,
  10 l, 11 ., 12 d, 13 u, 14 m, 15 c, 16 g, 17 y, 18 w, 19 f, 20 p, 21 b, 22 k, 23 !, 24 A,
  25 v, 26 I, 27 ', 28 T, 29 S, 30 M, 31 ,, 32 D, 33 O, 34 W, 35 H, 36 Y, 37 E, 38 R, 39 [,
  40 ], 41 G, 42 L, 43 C, 44 N, 45 B, 46 ?, 47 P, 48 -, 49 F, 50 z, 51 K, 52 j, 53 U, 54 x,
  55 q, 56 0, 57 V, 58 2, 59 J, 60 #, 61 1, 62 Q, 63 Z, 64 ", 65 3, 66 5, 67 &, 68 /, 69 7,
  70 X, 72 :, 74 4, 75 ), 76 (, 78 6, 80 *, 81 >, 84 <, 85 @, 86 +, 87 8, 89 9, 0 space.
- setNames(): for a in 808..847: ptr = 35792 + e (0x8BD0 = stock ptr[808]); writeName at
  t + 35792 + e - 22528; e += len+1. Names NFD-normalised, diacritics stripped, unknown -> 0.
- Stock: ptr[808] = 0x8BD0, ptr[848] = 0x8D9A -> 458 bytes, 418 chars, all used by stock.
  Decoded names match the in-game grid (0 Build Deck ... 39 Duel Master K).
- First render attempt at 0xF44000 (start of the 0x1E88 load) was noise: the tiles start
  34 sectors in (0xF55000); the first 32 sectors are the screen backdrop strip (rendered:
  "FREE DUEL" header, stone tiles), sector 32 its CLUT, 33 -> 0x801AF000.
- Tile CLUTs: 64/64 entries STP set on all 40 tiles; 1..5 entries are 0x8000 (black).
  Max index used 63.
- 0xF54FE0.. = FF bytes (end of the CLUT sector), 0xF6CC00.. = zeros after tile 39.
- Tests: tile 17 export/import/export diff 0; restore tile 17 from WA copy and all 40 from
  the .bin both cmp-identical; rename 1 and 39 then restore-names -> identical SLUS.
