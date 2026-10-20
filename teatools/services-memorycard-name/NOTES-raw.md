# Memorycard name modifier (extend/services/memorycard/name) -- raw notes, 2026-09-04

- Chunk `site/js/extend/services/memorycard/name.c2ca66c3.js`. No chunk-common; `Knowledge` is inlined in page.html
  (`const Knowledge = {...}` 100 keys: decimal-concatenated 19-byte product strings -> [{id,name,dir,reference}]).
  FileReader accepted ".mcr,.mem,.mcd" max 2097152.
- fe = 8192 (block size). ve(): dir frames 1..15, bytes 138+i*128 .. +19 (= frame+0x0A, the product/filename field).
  be(): name = 6 u16 LE at 9740+(block-1)*8192 (block+0x60C); hi byte 0x82 -> letters/digits table, else symbols.
  Ae(): letters/digits code+33280 (0x8200), symbols code+33024 (0x8100), space 0.
  putQ: byte at 8194+(block-1)*8192 & 3 = icon frames. Icons: palette 8288 (+0x60), body 8320 (+0x80), 16x16 4bpp x3.
  prepareData(): ye(dv, block, {start:9600, length:642}) -> bytes block+0x580..0x801 -> POST api/v2/tools/crypt
  {version, tipo:40, data:[...], id:block}; response s.data.data -> download(true,'mc',value):
  writeData(v): setUint16(10242+(block-1)*8192, v, BIG-ENDIAN) [block+0x802]; 9x setUint32(10244+.. +4*t, 0) [0x804..0x827].
- Real save (user's card1.mcd, block 1, "BASLUS-01411-YUGIOH"): name 69 82 69 82 = "JJ"; 0x57C = AD75 AD75 ; 0x5FC = 0000 0000 ;
  0x800..0x803 = 00 00 00 00 ; 0x804 = 5B3D 5B3D ; 0x808.. = 94 2b 77 ac a7 a2 ba 0c ...
- Decomp: func_8003CEB8 CRC16 XMODEM (matched). func_8003CE74 xorshift pair D_8009AF64/68 (gp+0x5C/0x60) (matched).
  func_8003CF14(a0): CRC(a0,0x340) -> a0+0x37C/37E, seed, 15 words from a0+0x378 down; CRC(a0+0x380,0x6C) -> +0x3FC/3FE, 4 words from +0x3F8 down.
  func_8003CFC8(a0): CRC(a0+0x400,0x204) -> +0x604/606, 8 words from +0x624 down.
  func_8003D174(a0): verify = recompute CRC per region, seed, compare the words (not the stored CRC u16). Called from 0x8003E694 (load state machine,
  result 0 -> state 4 in gp+0x4E3).
  func_8003D03C(block): copy 0x200 from 0x801D4000 (header); [0x600]=0; [0x608]=D_8009B0C4; [0x7DE]=gSD_bOutputType; [0x604]=++gp[0x4B0];
  [0xC84]=same; CF14(block+0x200); CFC8(block+0x200); zero 0x828..0x87F; copy 0x680 bytes 0x200 -> 0x880. Called from func_8003F87C.
  func_8003FE14 seals D_801D1880 and +0x1000 with CF14 (other structs).
- mc_name.py verify on card1.mcd: all three regions OK (crc AD75 / 0000 / 3D5B), seal idempotent (byte-identical), mirror matches.
  Bypass mode: region 3 CRC becomes 0000 with the residue at 0x802 and zero words -> verifier passes; mirror stale.
- Images (/Assets/img/cuadro.png, rainbow.gif, vidrio84.png, case.jpg, caratulas/*.jpg) 302 -> /forbidden_memories anonymously; not mirrored.
