# Raw notes: cutscene picture tools (background / bgcomp / bgmov), session 2026-09-04

## Reading the pages
- All three are the same Vue component ("BackgrounEdit"): `FileReader` (.mrg, 36-38 MB min,
  39,845,888 max) -> `ImagePanel` (chunk-common module "1d4b", name ImagePatched) to render
  from the DataView, `ImageConverter` ("287d") to turn an uploaded image into
  {header: palette, body: indices}, then `setNewHeader` / `setNewBody` / `setNewBody16`.
- ImagePanel config: width/height (canvas), num_colors, bytes_width 128, body_offset,
  pallete_offset, ppb (1 = 8bpp, 2 = 4bpp, low nibble first), chunks = list of
  {width,height,data:{ci,cf},canvas:{ci,cf}} where data.x is in BYTES and data rows are
  128 bytes. Read: byte = body_offset + 128*(data.ci.y + s/(width/ppb)) + s%(width/ppb) + data.ci.x.
- CLUT decode: lo,hi bytes; r=(lo&0x1F)<<3; g=((hi&3)<<6)|((lo&0xE0)>>2); b=(hi&0x7C)<<1;
  alpha 0 iff all zero (STP bit ignored for display).
- setNewHeader encode: black -> (8,8,8); lo = g[2:5]+r[0:5]; hi = (nonblack?1:0)+b[0:5]+g[0:2]
  -> STP set on every non-black colour written.
- ImageConverter: histogram at 5-bit precision, most frequent num_colors kept, sorted by
  value; keep_black -> pure black to (8,8,8); index = position of the pixel's colour in the
  sorted histogram (nearest by "<= header" scan).
- makeTrasparent (layers 2/3): the clicked colour is dropped from the palette, palette
  prefixed with (0,0,0,0) if < 256/16 entries, pixel indices remapped: removed colour -> 0,
  indices below it +1.
- Site constants (decimal in the JS, converted with Python -- two hand conversions in this
  session were wrong, do not convert by hand):
  17870848 = 0x110B000, 165888 = 0x28800, 231424 = 0x38800, 16076800 = 0xF55000,
  1859584 = 0x1C6000, 11866112 = 0xB51000, 11930016 = 0xB609A0, 12388096 = 0xBD0700,
  481280 = 0x75800, 528852 = 0x811D4.

## Disc dumps (WA_MRG.MRG = disc LBA 10102, read through eo.read_range on the .bin)
- 0x10FB000 (static NN 1) row 0: 30 30 35 35 35 38 38 38 ...; rows 160..255 zero; rows
  256..495 data; 496..511 zero; rows 512..515 (0x110B000) = CLUT; 528+ = NN 2.
- 0x10FA800 (NN 0 CLUT) = 00 80 00 80 00 80 01 00 20 04 00 80 ... (the default CLUT that all
  blank slots share).
- Non-zero pixel bytes per static slot: NN 0 = 5, 1 = 44653, 2 = 50610, ..., 41 = 48495,
  42..49 = 5 each (blank).
- bgcomp NN 0 CLUT3 raw: 00 00 56 a2 f4 99 b2 95 90 91 4f 91 2d 8d ec 88 ca 88 89 84 67 80
  46 80 23 80 02 80 01 80 00 80 (all STP).
- STP census: static/L1/L2 CLUTs: stp_set = 0 (static NN 45 has 4 x 0x8000 blacks, bgmov 4
  L1 one); every L3 CLUT: 15/15 STP. bgmov L2 all-zero for NN 0, 2, 9..12; L3 all-zero for
  NN 1..5. bgcomp NN 0 L2 has 15 zero entries (keyed sprite).
- bgmov blocks 13/14 (0x1DA7000, 0x1DDF800) render as character sprite sheets (Simon,
  Teana...), 15 has no CLUT: the moving set is 13 records.

## Loader (decomp, matched C)
- src/func_8002E730.c Script_OpShowImage: `func_8002DF2C(D_800EAE98, D_8009B270 & 0xFFF)`;
  quad `func_80040510(rec, 0,0, 0x140,0xA0, 0,0, 0x17, 0, 0xF4)`; MoveImage of the
  320x160 display area to (0x1C0,0x100) when nothing is pending.
- src/func_8002DF2C.c: BCD decode, mode 0/1/2 -> (0x21,0)/(0x51,0x672)/(0x71,0x13BC),
  sector = base + NN*stride + 0x21D5, callback func_8002DDFC, f38 = stride-1.
  Check: 0x21D5+0x21 = 0x21F6 (site static 01), 0x21D5+0x672 = 0x2847 (site comp 01),
  0x21D5+0x13BC = 0x3591 (site mov 01). Static slots: 0x672/0x21 = 50 exactly; comp:
  (0x13BC-0x672)/0x51 = 42 exactly.
- src/func_8002DDFC.c: mode 0: f32=0x100,f30=0,w=0x40,h=0x10,f46=2,f1C=f38<<11,
  f8=D_8009B118,fC=+0x800; mode 1: f1C=0x800,f46=1; mode 2: rect (0,0xF0,0x100,4)
  LoadImage2(obj, D_8009B118).
- src/func_80013998.c: the generic arm (arg7 = x|y<<16) sets f4=0x40,f6=0x10,f46=2 too.
- src/func_80013C28.c header: state 2 = double-buffered read, LoadImage2(stream, buf) at
  (f30,f32), "f32 += 0x10 with an 0x100 wraparound that also bumps f30 += 0x40, unless
  D_8009B0F4&0x20000 just bumps f30 += 0x40". LoadImage2 = 0x80081DE8.
- Free-duel load callback src/func_8003B808.c uses the same arms (0: VRAM (0,256) 0x10000
  bytes; 1: 0x800 to RAM; 2: CLUT rect + 0x800 to D_801AF000; 3: 0x18000 to D_80010000;
  4: 0x2800 to *(D_800100A8+0x130)) -- confirms the (0,256) stream + (0,240) CLUT idiom.

## Renders made to verify (scratch img/)
- bg1.png: temple at night, correct with CLUT at +0x10000.
- bgcomp1_layers.png: L1 temple interior, L2 Simon with sceptre (keyed), L3 brown glow disc.
- bgmov1_L1.png: 512x160 hieroglyph wall with the hand.
- freeduel_bg.png: the FREE DUEL header + stone tiles (sectors 0..31 of the 0x1E88 load).

## Script tests (copies in scratch img/)
- static NN 1 export -> import -> export: max channel diff 0; restore -> cmp identical.
- comp NN 0 all three layers imported in sequence, verify lists NN 0 only, restore identical;
  L3 round trip diff 0 after the exact-palette path (8 before, median cut drift).
- mov NN 1 L2 + NN 9 L1 (344x256) imported, restored one by one -> identical.
- inspect straight from the .bin works (sector reader), 105 records listed.
