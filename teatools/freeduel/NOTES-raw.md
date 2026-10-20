# Free Duel Music (extend/tools/freeduel) -- raw notes, 2026-09-04

- Chunk `site/js/extend/tools/freeduel.9a92cdd7.js`, component FreeDuelMusic. getMusic(): checkCode() then
  read u8 87496/87497 -> match against list g (44 entries, p1/p2). setMusic(): setBytes([p1,p2], 87496). Default
  highlight FREEDUEL SELECT THEME (192,114) is just the fallback when no entry matches.
- checkCode(): module 1929 (chunk-common.27f80639.js) exports c=87496, a=1882128, b="27", d=84 hex bytes, e = 57 track names.
  Compares d with the file at 1882128 (0x1CB810, RAM 0x801CB010); match -> toast "special duel theme process", tool disabled.
  d decodes (objdump) to: lui v0,0x801E; addu v0,v0,a1; lb v0,-0x4FF0(v0); nop; sll v0,v0,4; addiu v0,v0,0x7000; nops;
  lui at,0x800A; sh v0,-0x4C96(at) [D_8009B36A]; li v0,0x7280; sh v0,-0x4C8C(at) [D_8009B374]; sb a0,D_8009B360;
  sb a1,gDuel_bOpponentID; sh a2,D_8009B370; sh a3,D_8009B372; sb zero,gDuel_bTerrain; sb zero,D_8009B369; sb v0,D_8009B26C(?)
  -> relocated init_800eb26c_fields_from_args with table[opponent] at 0x801DB010. Retail EXE is zero at 0x801CB000..0x801D0000.
- Stock: 0x155C8 = 70 72 02 24 (addiu v0,zero,0x7270) = init_800eb26c_fields_from_args first insn (matched C).
- Music code = 0x7000 | track<<4: list e (00..38) x 16 + 0x7000 reproduces every p1/p2 pair of list g (and the hextext `et` list,
  which adds 2D..38: library, win, lose, game over, exodia 0x7310, epilogue, ending (p1=42?! 0x732A -- typo in the site, real is 0x7330),
  festival, password, item found, ruins 2, simon 2).
- Consumers: func_8001825C 0x8001848C lhu D_8009B36A -> call_masked_and_store_orred (SD play). func_80018608 0x800187AC also reads it.
  D_8009B374 read in asm_FD5C.s 0x8002004C/5C (3D battle start). Writers: init (0x7270/0x7280), func_80030F40 (0x71D0 then init),
  func_80038530 (campaign duel op: func_80036D3C(obj, byte) -> D_8009B36A; D_8009B374 0x72A0 / 0x7280 (opp 9..16) / 0x7290 (0x11) / 0x72B0 (0x26)).
- Callers of init: module 0x80168F84 (free duel confirm, F124), func_80030F40 @0x80030F68 (-1,1,0x8000,0x8000),
  mask_test_800eb26c_reinit_and_poll @0x8002DD3C (-1,-1,0,0) when s0==1.
- api/v2/tools tipo 3 analytics only.
