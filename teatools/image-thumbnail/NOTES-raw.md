# Thumbnail tool — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/image/thumbnail.864abd65.js (13.5 KB). Pretty-printed with the recipe sed; the
tool component is `BackgrounEdit` (copy-pasted from the background tool, hence the name).

Template facts:
- FileReader accepted ".mrg", minsize 37748736, maxsize 39845888 -> dataviewWa; image reader "image/*" max 12582912.
- 25 ImagePanel instances, config:
  {width:48,height:48,num_colors:64,bytes_width:48,bytes_height:48,
   body_offset:parseInt("F35000",16)+2432*(t-1), pallete_offset:15948032+2432*(t-1), color:"black"}
  15948032 = 0xF35900 = 0xF35000 + 2304.  2432 = 48*48 + 64*2.
- getPointer(t) = "[F6 " + hex(t+64) + " 00]"  -> [F6 41 00] .. [F6 59 00].
- ImageConverter config {width 48, height 48, num_colors 64, keep_black:true, clear_before_render:true}.
- salvarEnImagen(header, body, bodyOff, palOff): setNewHeader(palOff) then setNewBody(bodyOff).
- setNewHeader: (0,0,0)->(8,8,8); lo = g[2:5]+r[0:5]; hi = (r||g||b ? 1:0) + b[0:5] + g[0:2]  (bit strings, MSB first)
  => lo = ((g>>3)&7)<<5 | r>>3 ; hi = STP<<7 | (b>>3)<<2 | g>>6.  STP set for every non-black colour.
- setNewBody: dataviewWa.setUint8(off + x + 48*y, body[x + 48*y]) over the single chunk 48x48.
- download(): saveAs(blob(dataviewWa.buffer), filename). saveChange(): POST api/v2/tools tipo 12 (analytics).
- `setBytes` references dataviewSlus which does not exist in this tool (dead code from the template).

chunk-common ImagePanel (module 1d4b, name "ImagePatched") decoding:
  pixel byte n = batch.getUint8(body + bytes_width*(ci.y + row) + col + ci.x)
  ppb 1: colour = header[n] if n < num_colors else header[0]
  ppb 2: lo nibble first, then hi nibble
  getHeader: n=lo byte, i=hi byte: r=(n&1F)<<3, g=(i&3)<<6|(n&E0)>>2, b=(i&7C)<<1, a = 0 if (i&80)==0 && rgb==0 else 255
ImageConverter (287d): 5-bit rounding, keep_black -> (8,8,8), histogram sorted by count then RGB, nearest colour, transparent -> first entry with a==0.

Disc verification (scratch, via extract_overlay.read_range on the raw .bin, WA at LBA 10102):
- 0xF35000: rendered tiles 1..25 = Simon, Jono, Teana, Seto, Heishin, ... all valid portraits (thumbs25.png).
- All 64 CLUT entries of every tile have bit 15 set; stock pixel indices 1..63 (0 unused).
- Region 0xF35000 + 25*2432 = 0xF43D80 .. 0xF44000: 640 bytes of 0xFF padding; next load (0x1E88, free-duel) starts at 0xF44000.
- Rendering 0xF44000 as 40 raw tiles gives noise -> the free-duel portrait tiles are not at the start of that 0x57-sector load (F121 says they come from the load arena; offset unknown).

Text machine:
- src/func_800393B0.c dispatch table: 0xF6 -> func_80038EB0.
- func_80038EB0 (asm/asm_296B0.s): reads two bytes after F6 (s3 = idx, s2 = flags); `slti v0,s3,0x41` splits
  portrait (>=0x41) from other face-box commands; records 0x4C bytes in D_800EB010 (also +0x98 stride for the
  first lookup); fields +0x30 idx, +0x31 colour slot ((flags>>1)&3 when flags&0x10), +0x32 bit 0x10, +0x33 = 3/5,
  +0x34 = 0x178 / -0x38 / 0xF0 / 0x400 (flags&8), +0x36 = 0x60, +0x3C side (flags&1 / 2), +0x40..+0x44 = (0x178|-0x38, 0xB2, 0x10);
  calls func_80039F44 (init) / func_80039FD4 (kill), writes gp+0x420 (current face record), s4+0x51 = state 6/7/9/0xE.
- No 0x1E6A / 7786 immediate anywhere in SLUS_014.11 (li/addiu/ori/.word scan + raw u16 scan) -> loader is in a module.

Script tests (copies in scratch): import portrait 3 and 5 from a PNG, restore from the disc image and from a
stock WA copy -> cmp identical both times.
