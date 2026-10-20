# Game Font tool — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/image/gamefont.57f85294.js (103 KB; this page bundles its own copies of
FileReader/ImagePanel/etc. instead of chunk-common). Components: FontEditor > LoaderZone (asks for
"SLUS_014.11","WA_MRG.MRG" by default but only the WA is used), PreviewZone (ImagePanel + TextGenerator),
PsxAlphabetEditor (the real logic), GridCharEditor (per-cell character remap UI), CustomFontsEditor (localStorage "cfonts").

Constants (PsxAlphabetEditor): Vt=11829248 (0xB48000) body, Yt=21504 size, Kt=256 W, Zt=168 H, Xt=128 bytes/row,
Qt=11929344 (0xB60800) palette, ea=32 palette bytes.
Grids: ta={cellW:8,cellH:12,cols:16,rows:6,x0:0,y0:0}; aa={cellW:16,cellH:16,cols:16,rows:6,x0:0,y0:72}.
Char tables na (small) / sa (large): see README; large row 3 = Q..Z, " ", "←", "→", "E","N","D".
readPalette: v = lo | hi<<8; r=v&31, g=v>>5&31, b=v>>10&31, stp=v>>15; expand c<<3|c>>2.
unpackIndices: idx[y*256+2x] = b&15, idx[y*256+2x+1] = b>>4. packIndices inverse.
renderGlyphIntoIndex: canvas cellW x cellH black, white text, font = (bold?"bold ":"") + max(4, round(0.92*cellH*scale/100)) + 'px "font"',
  textAlign center, baseline middle, fillText(ch, w/2, h/2+1+yOffset); each pixel -> nearestPaletteIndex (Euclidean RGB);
  empty cell -> nearest to black (index 0 = transparent 0x0000).
drawEndWordSpecial: cell (13,3) of the large grid, 48 px wide: fill nearest-black, render "END" 32 px wide at the right,
  left 8 px = first palette entry with stp==1.
onFileChange: size warning if |MB-36| > 40; requires length >= Vt+Yt and >= Qt+ea; reads palette + indices, emits file-loaded.
downloadModified: copy of the buffer, set(packIndices(workIndex), Vt), download "WA_MRG_modificado.MRG". Only the sheet is written.
Analytics: api/v2/tools (tipo), api/v2/toolcontrol/validate, api/v2/users/validate|login, api/v2/comment, api/v2/pops.
Version strings: "Font Editor | V. 20260729", LoaderZone default footer "Ritual Engine Editor | V. 20251123".
ImagePanel default config in this bundle: body 0x10FB000, palette 17870848 (0x110B000), 320x160 -> a background image.

Disc verification:
- 0xB48000 rendered as 256x168 4bpp with CLUT 0xB60800: two alphabets exactly as the grids describe (font.png).
- CLUT: 0000 DEF7 C631 B18C A529 94A5 8C63 8421 A8A3 D107 A06A A470 99A6 9560 88EC 8010.
- 0xB50000 (256x160 4bpp, CLUT 0xB60400 = palette row 24): UI icon sheet (attribute/type icons, FIELD/MEADOW/... labels, LP/COM/2P, buttons).
- 0xB60000..0xB60800: 64 x 32-byte palettes, all non-zero; 0xB60800.. font palette; 0xB60F00.. zeros.
- Sector math: 0xB48000 >> 11 = 0x1690 (5776), LBA 15878. 0xB60800 -> sector 0x16C1. 0xB63000 -> 0x16C6 (duel overlay copy 0).

Loader: src/func_80043960.c: `func_80014E1C(0, 0, 0x1690, 0x36, &func_80043328, 0, 0)` (also asm 800439B4 `addiu a2,zero,0x1690`).
0x36 sectors = 0x1B000 bytes = 0xB48000..0xB63000 exactly. Callback func_80043328 (asm/matchings/func_80043328):
  a1 = phase. phase 0: rec+0x30=0x280, +4=0x40, +6=0x10, +0x1C=0x18000, src D_8009B118, D_8009B0F4 flags &= 0xFFDDFFFF |= 0x10000, +0x46=2.
  phase 1: +0x1C=0x1000, flags &= 0xFFDCFFFF, src D_8009B118 (+0x18000 implied by later phases? not shown), +0x46=1.
  phase 2: rect (0x200,0xF8,0x100,8) LoadImage2 from D_8009B118 -> the 0x1000 CLUT block at VRAM (512,248) 256x8; then +0x1C=0x800, src+0x1000.
  phase 3: rect (0x280,0xE8,0x10,8) LoadImage2 from D_8009B118+0x1000; then +0x1C=0x1800, src = D_800100A8+0x130.
  => font CLUT (block +0x800 = row 4) is at VRAM (512,252). Pixel block destination not decoded (needs live trace).

Script tests: export -> import of the exported PNG reproduces the stock sheet byte-for-byte; modified PNG changes only
0xB48000..; --palette rewrites 0xB60800; restore from the disc image -> cmp identical.
