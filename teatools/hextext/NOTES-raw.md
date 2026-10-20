# hextext (extend/tools/hextext) -- raw notes, 2026-09-04

- Chunk `site/js/extend/tools/hextext.8b4d16ac.js` (107 KB). Components: Hextext (hex table), FloatMenu, PointerEditor, TimeLine
  ("Campaign Router", WA), ImagePanelLayered (WA image preview). Mixin `nt` = the context-menu writers. Mixin Z = chunk-common 5e6c getCardInfo.
- Constants: offset 1710688 (0x1A1A60) default page; 1705984 (0x1A0800) = bank base (pointers are `abs - 1705984`); q=256 page;
  textPointer 4704 = 0x1260; generateIndexList: 250 u16 at 1773568 (0x1B1000) -> indexList (R. id); editPointer writes setUint16 there.
  move() bound: 0 < offset < 1902576. TimeLine: indexOffset 15941632 = 0xF34000 (NOT 0xF34C00 -- first reading was a hex slip),
  199 u16 pointers, parseCode over 3698 bytes from +398, FF ends. salvarWa writes pointers + bytes back.
- Layers: P (compound bg) body 0x1423800+165888, header 0x144B800+165888, size 165888; R (static) body 0x10FB000 header 17870848 (0x110B000) size 67584;
  F (animated) body 0x1AC8800+231424 header 0x1B00800+231424 (+512 for second layer) size 231424; L (thumbnails) body 0xF35000 header 0xF35900 size 2432.
  move_id = image id (body + (id-1)*size). Palette 15bpp, 256 colours (thumbnails: header at +2304 => 64 entries).
- Charset J: l0 ' ' l1 e ... l91 % (+ l239/l226 shown as space in chunk-common's copy). X: 254 newline glyph, 255 end, 250 page, 251 option.
- Context-menu writers (bytes): addName FC 5A 12; addNewLine FE; addNewPage FA; endText FF; endAutomaticText F8 16 FF; editLetter 0x30 ('-');
  addOptions FA FB 02; addAnswers FE FB 80 p p p p (both = here+7); setGoto FD p p (here+3); pastePointer lo hi; putColor F8 0A n;
  unlokOpponent F8 19 n; addDuel FA F8 11 00 F8 0D 01 60 61 00 00 72 FF; putBackground F7 05 01 n; putCharacter F6 01 anim;
  putThumbnail FA F6 41 anim; putPause F7 0F 3C 00; putIf F9 FE 00 p p (here+5); putIfNot F9 FE 80 p p; putCondition F9 FE 40; unsetCondition F9 FE C0;
  setMusicTheme F8 0E lo hi; setSoundEffect F8 10 hi lo (setUint16 big-endian); setScreenEffect F8 15 n; setStopMusic F8 11 n;
  resetUntilFF zero to FF; resetAll rewrites every campaign string as "#<id>" FF; moveUntilFF shifts bytes.
- Decoder (computed `texto`): see README table; F8 0D is recognised only when byte+1==0D and byte+8==FF; F8 0B icon id folded (D-34)%16+34 for D>=34;
  F6 with 64<id<90 = thumbnail (id%64); F7 05 background types 0/1/2/65/128/129/130.
- EXE: gText_adwGlyphCodeTable 0x801D9000 (file 0x1C9800): 92 words; low16 = SJIS; high16 = cell<<4|attr (a..z 0xC0+, A..Z 0xA0+, 0-9 0xE0+, symbols 0xBA..0xBF, 0 for font glyphs).
  TextBox_BuildStep 0x8003968C slti 0xF0; table s1=D_80090F18: F0-F5 -> 80037D2C, F6 80038EB0, F7 80037D6C, F8 80038B4C, F9 80038D2C, FA 80038D14,
  FB 80038BF0, FC append_stream_word_and_advance_field88, FD 80038BA8, FE 80038E1C, FF 80038E7C.
  F8 table D_80090EAC (32): 00 80037DA4 01 800380D4 02 80038110 03 80038148 04 800382A8 05 80038334 06 80038388 07 800383B0 08 80038070 09 800383DC
  0A 80038498 0B 80038094 0C 800384E4 0D 80038530 0E 80038690 0F 800386B8 10 80038798 11 80038800 12 80038888 13 80038890 14 80038898 15 800388D8
  16 800389C4 17 800389D8 18 80038A44 19 80038AB0 1A 80038B08 1B-1F 80037D2C.
  Stub 80037D2C: reads one byte, gp+0x432 = (code-0xF0)<<8 | byte, gp+0x448 = -1 -> BuildStep falls into the glyph path with that code (2-byte glyph escape).
  80038D2C (F9): func_80036D3C -> v; v&0x4000 -> Library_UpdateCardUsedFlag(v&0xBFFF) ; else t=u16; Campaign_TestStoryFlag(v) -> stream lo16 = t.
  80038BF0 (FB): f=byte; f&8 -> extra byte (default 0xF); f&0x80 -> pointer[gp+0x445] ...
  800389D8 (F8 17): stream += 2*gp[0x446]; u16 -> stream lo16.  80038A44 (F8 18): same with gp[0x44D].  gp = 0x8009AF08.
  80038AB0 (F8 19): n=byte; n>0 -> Library_UpdateCardUsedFlag(n+0x1F); (n+0x6E0).  80038B08 (F8 1A): __builtin_delete(rec+0x30), state 2, +0x62=0, gp+0x448=1.
  800389C4 (F8 16): rec+0x34 &= ~8.
- Bank facts: 0x801C0000 table 1100 entries used; entry 62 -> 0x50E, 254 -> 0x125A (name slot 6 bytes), first campaign pointer 0x1260.
  0x801C0800 table: 259 non-zero entries, first 0x1260 (=4704), used by the script's TEXT op ids.
- WA script bank verified on disc: 0xF34000 = [398,398,415,416,...], code head 09 08 80 01 04 00 0a 00 e0 70 0d 01 00 01 00 08.
  EXE 0x801A8000 (file 0x198800) all zero -> loaded from disc.
- api/v2/tools tipo 10 analytics only.
