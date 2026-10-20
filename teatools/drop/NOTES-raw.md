# Drop Editor - raw working notes (2026-09-04)

## Chunk facts (drop.b8afbc11.js, pretty-printed)
- DropTable component; mixin getCardInfo reads card names from the SLUS (offsets 1854016 /
  1858355 / 1772032 / 1859584 are the card-stat, description and name tables, same mixin
  as every other tool).
- createDropData: a=15314944 (0xE9B000), 6144*i + 1460*n + 2*(l-1), i<39, n<4, l=1..722,
  column = numberToletters(4*i+n+1+2), row = l+5. Values parseInt % 65536.
- is2048 computed check; createMissingList over n=1..3 only.
- criptoDrop: checkGhostIso(); for n=1..3 every cell w -> 8*w + 2512 + floor(7*rand).
  then SLUS: non-ghost: at(8 B) @73824 (0x12060), Qe(24 B) @1771472 (0x1B07D0).
  ghost: at @1684660 (0x19B434) + WA at [12328116,12809396,13290676,13771956,14253236,
  14734516,15215796] (= 0xBC1CB4 + k*0x75800), et(24 B) @1771472.
- Ze=1684544 (0x19B3C0) + Xe (144 B) = ghost signature.

## Stub disassembly (objdump, mips:3000, little-endian)
    at  @80021860: 0806fff4 j 0x801bffd0 ; 00000000 nop
    Qe  @801bffd0: 2442f630 addiu v0,v0,-2512 ; 000210c3 sra v0,v0,3 ; 00822021 addu a0,a0,v0
                   0085102a slt v0,a0,a1 ; 0800861a j 0x80021868 ; nop
    et  = Qe with 0806ab2f j 0x801aacbc
    Xe  @801aabc0:
      lui sp,0x1b / addiu sp,sp,-21504    -> sp = 0x001AAC00 (?? kseg0 0x801AAC00 without the
                                             high bit; works because the PS1 mirrors 0x0..)
      sw v0,v1,s0,a0,a1,ra,s6,s7 to 0(sp)..28(sp); sb zero,32(sp)
      lbu s6,32(sp); addiu s6,s6,1; li s7,6; beq s6,s7 -> 801aac74  (loop 1..5)
      sb s6,32(sp); lui s0,0x801b; lw s0,-20912(s0)  -> s0 = *(0x801AAE50) = table pointer
      j 0x801aaea0  (rand call etc., outside the 144-byte signature)
      801aac1c: andi v0,v0,0x7ff / addiu a1,v0,1 / a0=0 / v1=0 / lhu v0,0(s0) / nop
      801aac34: addu a0,a0,v0   <- ghost hook position (SLUS 0x19B434)
      801aac38: slt v0,a0,a1 / beqz v0 -> 801aac58 / addiu v0,v1,1 / addiu v1,v1,1
      801aac48: slti v0,v1,722 / bnez v0 -> 801aac2c
  The ghost stub returns to 0x801aacbc, not 0x801aac3c; unverified whether that is a bug
  or whether the multi-drop routine is laid out differently past the signature.
  The recomp's psx_card_drops.c describes the "community drop mod" as an overlay-space
  patch dealing N cards with 1 + 7N rand() calls; this routine is that patch.

## Disc verification
- WA_MRG.MRG extracted from the .bin (LBA 10102, 2352-byte sectors, +24). md5 of the
  extracted file: 971c16ea21635b45351e5ae959c53503.
- 39 blocks at 0xE9B000: all 156 rows sum 2048, all 16-byte pads zero, all 39 trailers
  identical (05 00 0c 00 09 00 08 00 1d 00 00 00 21 00 f8 ff ...) = gDuel_awRankScoreChange.
- Sector before the block (0xE9A800) is other data (292 non-zero bytes); after it
  (0xEF5800) `77 77 77 ...`.
- SLUS: 0x12060 = 21 20 82 00 2a 10 85 00 (stock); 0x1B07D0..0x1B0800 zero;
  0x19B3C0.. zero (no ghost signature in stock).

## Decomp cross-refs
- asm/matchings/weighted_random_pick/Duel_SelectCardDrop.s, src/weighted_random_pick.c
- asm/asm_81F4.s lines ~78-90: loader call (sector 0x1D33 + 3*id, a3 = 3, dest 0x801781D8)
- asm/asm_14BF4.s: Duel_ShuffleDeck
- asm/asm_120F0.s lines 196-262: tier choice and result stores; line 240 = jal 0x80021810
- findings F73/F78/F129 (end-of-duel path), F19 (save block).
