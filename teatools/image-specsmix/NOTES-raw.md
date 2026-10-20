# Cards / specsmix — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/image/cards.0ad4f385.js (96 KB), component CardEditor (+ TextImage/textcanvas,
PalleteEditor, ColorToneEditor, TextEditor, DescriptionEditor, ImageSelectorMenu, TextureIndexer, Modal).
FileReaders: ".mrg" 37748735..39845888 (dataview), ".11" 1782579..2097152 (dataviewSlus), "image/*" <= 20971520.

WA offsets (data block `lt`):
  big_image_offsett_base 0x169000, big_image_header_offsett_base 1488448 (0x16B640)
  tiny_image_offsett_base 0x16BAE0, tiny_image_header_offsett_base 1490912 (0x16BFE0)
  tiny_image_2_offsett_base 0x0, tiny_image_2_header_offsett_base 1280
  name_offsett_base 0x16B840, name_header_offsett_base 12075456 (0xB83C40)
  card_offsett_base 0xB63000, card_header_offsett_base 12075008 (0xB83A80) (+512*moveByType)
  price/password base 16488448 (0xFB9800) + 8*id: getUint32 price, bytes +7..+4 as hex password; write: price %1e6, password parseInt(hex)%0xFFFFFFFF
  icons: body 0xB50000, bytes_width 128, 16x16 per icon, chunk data.ci = (4t, 8e) bytes .. (4t+8, 8e+16); palettes 11928064 (0xB60100) + 32*i
  colorPointers: 0xB60F00 + 32*i (i=0..7), and 0xB83C40 size 16
images[]: 0 art 102x96/256/bw102, 1 thumb 40x32/64/bw40, 2 (title, via TextImage), 3 frame 144x200/128 colours/bw128, 4 thumb2 40x32/64.
getIncrement: idx 0,1 -> 14336*(id-1); 3 -> 0; 4 -> 2048*(id-1).
Chunk maps ot[0..5]: see README section 2 (ot[3] monster frame 5 rects, ot[5] spell frame 6 rects, ot[2] title data 48x14 bytes -> 96x14 canvas).
moveByType = type>19 ? (type-20)%3+1 : 0; bgColor overrides for type<20 when set.
setNewHeader(a="1"): (0,0,0,a!=0) -> (8,8,8); STP = (r||g||b) ? a : 0. setNewHeaderBG: STP = a>0.
setNewBodyBG (title): byte = hi<<4 | lo from two canvas pixels, stride 48 (96*n/2). Name palette never written (r=false).
textcanvas.draw: font 16px, fill rgb(8,8,8), scale(c, 14/16), fillText at baseline int(16/1.25)=12, optional fullWidth squeeze / centre / padding.
textcanvas.createBody: d = 255 - 8*floor((255*(1-a) + c*a)/8) per channel (inverted, alpha-composited on white), nearest in S, clamp <=7.
S = [(0,0,0,0),(184,)*3,(152,)*3,(128,)*3,(104,)*3,(88,)*3,(64,)*3,(32,)*3, then 8 x (8,0,0)].
checkSerial: for id 0..721 renders title with current font and writes REC+10304 (serial "Update Name").

SLUS bits the page touches (for the cardsdata folder):
  names: card.name.offset 1861633 (example for id 1) -> 0x1C6801 -> RAM 0x801D6001; budget A004 bytes (writeAllNamesOnSlus)
  descriptions: budget FFFF (writeDescriptionParsed); Description component reads getUint16(e+512+2*a) offsets
  layout constants read as u8 immediates: image x 103476 (0x19434 -> 0x80028C34: `addiu v0,v0,0x13`), image y 103500 (0x80028C4C: 0x32),
    text x 103624 (0x80028CC8: 0x0C), text y 103676 (0x80028CFC: 0x0E), atk x/y 104112/104132 (0x80028EB0 0x61 / 0x80028EC4 0x9D),
    def x/y 104252/104272 (0x80028F3C 0x61 / 0x80028F50 0xAB), st x/y 104396/104432 (0x80028FCC 0x77 / 0x80028FF0 0x20),
    attr x/y 104580/104600 (0x80029084 0x6E / 0x80029098 0x0D)   -- card-page sprite positions
  card colour patch check (checkCodeBG / pt): ut at 105468 (0x19BFC -> 0x800293FC) = 78 6B 07 08 FF FF 93 24 = `j 0x801DADE0; addiu s3,a0,-1`
    (stock: 24130100 00008021 = li s3,0x100; move s0,zero); dt at 1881568 (0x1CB5E0 -> 0x801DADE0, stock zeros):
      srl s3,s3,1; a2 = 0x801DAE24 + s3; lb a2,0(a2); s3 = a0&1 ? a2>>4 : a2&0xF; addiu s3,s3,0x100; move s0,zero; j 0x80029404
    table 1881636 (0x1CB624 -> 0x801DAE24), 361 bytes, card 2k -> high nibble? (getBGCode: cards[2*(e-t)] = b>>4, cards[2*(e-t)+1] = b&15)
    NB the stub uses a0&1 to pick the nibble and a0-1 >> 1 as the byte, i.e. odd a0 (= card id) -> high nibble... the site displays
    even index -> high nibble; consistent since index = id-1.

Disc verification:
- card 1 art/title/thumb render (Blue-eyes); title nibbles 0..7; CLUT[0] = 0x8000 for ids 1,2,100,722; record bytes 12384..14335 zero.
- thumbnail sector id-1 == REC+10976 (1408 B) for all 722 ids; sector tail 640 x 0xFF.
- 16x88 rendering of REC+10976 is noise; 40x32 + 64-CLUT rendering is the card art crop -> F125 needs amending.
- price: id1 999999 / 0x89631139, id2 160 / 0x15025844, id722 999999 / 0xFFFFFFFE. 0xF91800 block is not a copy.
- 0xB63000: 128-byte-wide 8bpp texture, all 512 first rows non-zero, palettes at +0x20A80 (4 x 512); assembled 144x200 with ot[3] + pal 0
  = the stock monster frame; pal 1 near-identical tint; pal 2/3 garish. Same 0x20C80 bytes at 0xB63000 + 0x75800*k for k=0..6.
- func_800179F4 (asm_81F4.s 80017A2C..): a2 = terrain*235 + 0x16C6, a3 = 0xEB, callback select_sound_preset... -> duel overlay per terrain.
- name palette 0xB83C40: 8000 8001 x15. colorPointers 0xB60F00..0xB60FFF: all zero. icon palettes: 0..23 near-black (0001), 24 real, 48 grey ramp, 49 zero.

Script tests: import art/title/thumb + price on a copy, restore -> cmp identical; title export->import (scale 1) identical for ids 1 and 300.
