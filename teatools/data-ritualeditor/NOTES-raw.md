# Ritual Editor — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/data/ritualeditor.41addce6.js. Helpers imported from chunk-common:
  8481 -> addresData = 12154880 (0xB97800), plus `b` = {jumps,buffer,script} for the ritual-engine tool
  15a2 -> Ritual class: fromBytes([w0..w4]) type=w0>>10&3, ritual_id=w0&1023, req1..3, card_result
          isRegNull = all five zero
  5e6c -> card mixin getCardInfo/readValues/readName/readDescription (same as cardsdata)
  f68d -> Card class; 5a50 attribute list; 4993/cc01 ImagePanel (card art from WA)
readWa: loop e<24 until isRegNull, 10-byte records at addresData + 10*e (LE u16 x5)
writeWa: 24 slots ((type<<10)+ritual_id, req1, req2, req3, card_result) or zeros, then zeros at 240..248
multiSetWord: setUint16 at addresData+e + k*481280 for k=0..6
addNewRitual default: {id:695,type:0,ritual_id:695,req1:1,req2:1,req3:1,card_result:380}
ritualRitualSpellList = type==22; ritualMonsterList = type<20
saveChange: POST api/v2/tools {version, tipo:43, data} then download WA; PostBox guia 53
ImagePanel config: body_offset 0x169000+14336*(id-1), pallete_offset 1488448+14336*(id-1), 102x96, 256 colours

Disc verification (MODE2/2352, WA at LBA 10102):
  copies at 0xB97800 + 481280*k identical for k=0..6 (first 256 bytes compared)
  raw row 0: 9e 02 1b 00 26 00 3a 00 6c 01  -> 670, 27, 38, 58, 364
  bytes before 0xB97800 and after +0x100: 0xFF fill; FF run starts at 0xB975E9
  WA search for row 0 bytes: 0xB97800, 0xC0D000, 0xC82800, 0xCF8000, 0xD6D800, 0xDE3000, 0xE58800
  package boundaries: sectors 5830..6032 identical across the 7 copies, 6033.. differ

Decomp:
  gDuel_awRitualData = 0x801799D8 (symbol_addrs); SLUS bytes there are zero (file 0x16A1D8)
  refs: 0x80017300 (select_sound_preset, dest+size 0x800), 0x80021954 (asm_120F0, stores the
  pointer to gp+0x2E0 on duel start), 0x8002C7EC (recipe lookup), 0x80020F54 (func_80020F4C)
  func_8001798C: a2 = terrain*235 + 0x16C6, a3 = 0xEB, callback select_sound_preset
  func_80024E58: a2 = terrain*235 + 0x1791, a3 = 0x10
  extract_overlay.py SIG (18000000 00100000 x3) found at sectors 5970,6205,6440,6675,6910,7145,7380
  callers of table801a7ad8_recipe_lookup: 0x80026248 (func_8002622C), 0x800262F8
  (obj_lifecycle_state_dispatch), 0x80072600 (AiScript_CheckRitual)
  0x8002622C: lh a1,0x2CA(gp); jal lookup(0,a1); sh v0,0x298(gp); beqz -> fail;
              func_8002C68C(0x12); SD_SEPlayFull; func_80029164(1, gp+0x298)

Script tests (scratch copies only): verify stock -> 7x stock; apply CSV (row 0 -> 1,2,3 -> 380,
row 23 -> 695/58,58,58 -> 58) -> 7 copies MODIFIED, 77 bytes changed; restore -> cmp clean;
--terrain 3 -> exactly one copy modified; verify works on the .bin disc image directly.
