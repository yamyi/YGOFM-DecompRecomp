# phoenix-effects-battle — raw working notes

## Mirror

`site/js/extend/tools/phoenix/effects/battle.5d3db071.js`, pretty-printed with
`sed 's/},{/},\n{/g; s/;/;\n/g'`. The tool's own state lives in component `Ct`:

    bytes: { mainScript: We, validationScript: Ve, initData: Ye }
    Ve = [{address: 69168,   data: [16 bytes]}, {address: 69296, data: [8 bytes]}]
    We = [{address: 1857488, data: [552 bytes]}, {address: 1858108, data: [20 bytes]}]
    Ye = [{address: 1858040, data: [68 x 0xFF]}]
    wt = [{name:"Marshmallon",id:0}, {name:"Exploder Dragon",id:1}, {name:"D.D. Warrior Lady",id:2}]

    checkSlus()            -> compares every Ve byte; throws "This file does not have the process enabled."
    addCode()              -> writes Ve, then We, then Ye
    readLine(v)            -> {card: cards[(v>>4)-1], effect: wt[v & 15]}, clamped id 1..722, effect 0..2
    readCardWithEffects()  -> 16 x getUint16(Ye[0].address + 2*i, LE)
    readExceptions()       -> 14 x getUint16(Ye[0].address + 36 + 2*i, LE)
    writeCardWithEffects() -> (id << 4) + effect, 0xFFFF for empty, then setUint32(+32, 0xFFFFFFFF)
    writeExceptions()      -> id, 0xFFFF for empty, then setUint32(+36+28, 0xFFFFFFFF)
    addCardEffect()        -> refuses when effectCardListFiltered.length > 15   (so 16 max)
    addCardException()     -> refuses when exceptionListFiltered.length > 13    (so 14 max)

Decimal -> hex:

      69168 = 0x10E30    69296 = 0x10EB0
    1857488 = 0x1C57D0 1858040 = 0x1C59F8 1858108 = 0x1C5A3C

RAM (`0x80010000 + off - 0x800`): `0x80020630`, `0x800206B0`, `0x801D4FD0`, `0x801D51F8`,
`0x801D523C`. C+D+E are contiguous, `0x801D4FD0..0x801D5250`.

## Verified stock bytes (`~/ygofm-decomp/SLUS_014.11`)

    0x10E30  26 11 9e f0 | 8e 23 00 08 | 34 82 00 80 | a3 82 02 6c
             addiu s1,s0,-0x6110 ; lw v1,8(s1) ; ori v0,a0,0x80 ; sb v0,0x26C(gp)
    0x10EB0  8e 22 00 0c | 00 00 00 00
             lw v0,0xC(s1) ; nop
    0x1C57D0 b0 01 ce 00 f3 01 87 01 ...    (gCard_asNameSortKey entries 289+)
    0x1C59F8 cb 02 90 00 18 00 a9 00 ...
    0x1C5A3C 4b 01 62 02 e4 01 bc 00 ...

Patched:

    0x10E30  f5 53 07 0c | f0 9e 11 26 | 68 54 07 0c | 80 00 82 34
             jal 0x801D4FD4 ; addiu s1,s0,-0x6110 ; jal 0x801D51A0 ; ori v0,a0,0x80
    0x10EB0  74 54 07 0c | 1d 80 07 3c
             jal 0x801D51D0 ; lui a3,0x801D

## Disassembling the payload

```
cat patch_main_1C57D0.bin patch_init_1C59F8.bin patch_main_1C5A3C.bin > phx_full.bin
mips-linux-gnu-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x801D4FD0 phx_full.bin
```

Full listing (comments added):

```
801d4fd0  nop                          ; padding, the entry is +4
801d4fd4  lw    v0, 4(s1)              ; D_800E9EF0[1]
801d4fd8  lui   a3, 0x801d
801d4fdc  bnez  v0, 801d4fec
801d4fe0   sw   zero, 0x4fd0(a3)       ; clears BOTH result u16s (delay slot, always runs)
801d4fe4  jr    ra
801d4fec  move  v1, zero               ; pass counter
801d4ff0  li    t2, -1                 ; side-1 card id
801d4ff4  li    t3, -1                 ; side-1 effect
801d4ff8  lbu   a2, 0x6a(v0)           ; LOOKUP: obj->f6A
801d5000  sll   a1, a2, 3
801d5004  subu  a1, a1, a2             ; a1 = a2*7
801d5008  sll   a1, a1, 2              ;      *4  -> *28
801d500c  lui   a2, 0x801a
801d5010  addiu a2, a2, 0x7ad8         ; D_801A7AD8
801d5014  addu  v0, a1, a2
801d5018  lhu   v0, 0xc(v0)            ; row->cardId
801d501c  j     801d523c               ; card-690 guard, region E
801d5020   lui  a2, 0x801d
801d5024  addiu a2, a2, 0x51f8         ; effect table
801d5028  lh    a1, 0(a2)              ; SCAN
801d5030  srl   t0, a1, 4
801d5034  beq   t0, v0, 801d506c       ; hit
801d5038   andi t1, a1, 0xf
801d503c  bgez  a1, 801d5028           ; 0xFFFF terminates
801d5040   addiu a2, a2, 2
801d5044  beqz  v1, 801d505c           ; miss on pass 0
801d5048   move t0, v0
801d504c  bgez  t3, 801d5088           ; miss on pass 1: apply only if side 1 had an effect
801d5050   li   t1, -1
801d5054  jr    ra
801d505c  move  t2, v0                 ; pass 0 miss: remember side-1 id, effect stays -1
801d5060  lw    v0, 0(s1)              ; D_800E9EF0[0]
801d5064  j     801d4ff8
801d5068   addiu v1, v1, 1
801d506c  bnez  v1, 801d5088           ; hit on pass 1 -> apply
801d5074  lw    v0, 0(s1)              ; hit on pass 0
801d5078  move  t2, t0
801d507c  move  t3, t1
801d5080  j     801d4ff8
801d5084   addiu v1, v1, 1
801d5088  bnez  t1, 801d5094           ; APPLY
801d508c   li   v0, 1
801d5090  sh    v0, 0x4fd0(a3)         ; t1 == 0 -> side 0 survives
801d5094  bnez  t3, 801d50a0
801d509c  sh    v0, 0x4fd2(a3)         ; t3 == 0 -> side 1 survives
801d50a0  slt   v0, t1, t3
801d50a4  bnez  v0, 801d50b4
801d50a8   li   v0, -1
801d50ac  j     801d50b8
801d50b0   move v1, t1
801d50b4  move  v1, t3                 ; v1 = max(t1, t3)
801d50b8  addiu a1, v1, -1
801d50bc  bgtz  a1, 801d5194           ; max == 2 -> D.D. Warrior Lady
801d50c0   addiu t1, t1, -1
801d50c4  lui   a2, 0x801d
801d50c8  addiu a2, a2, 0x521c         ; exception list
801d50cc  bnez  t1, 801d512c           ; side-0 effect != Exploder
801d50d0   addiu t3, t3, -1
801d50d4  sw    v0, 0x4fd0(a3)         ; both slots = -1
801d50d8  li    t4, 660
801d50dc  bne   t0, t4, 801d5110       ; card 660 special case
801d50e4  sh    zero, 0x4fd0(a3)       ;   side 0 (the 660 card) keeps stock outcome
801d50e8  lui   t5, 0x801d
801d50ec  addiu t5, t5, 0x5332         ; gDuel_abCardLevelAttr
801d50f0  addu  t5, t5, t2             ;   [side-1 card id]
801d50f4  lbu   t5, 0(t5)
801d50f8  li    t4, 1
801d50fc  srl   t5, t5, 4              ;   attribute nibble
801d5100  bne   t5, t4, 801d5110       ;   != DARK -> exception scan
801d5108  j     801d512c
801d510c   sh   zero, 0x4fd2(a3)       ;   DARK -> side 1 spared, skip the scan
801d5110  lh    a1, 0(a2)              ; exception scan against t2
801d5118  bne   a1, t2, 801d5124
801d5120  sh    zero, 0x4fd2(a3)
801d5124  bgez  a1, 801d5110
801d5128   addiu a2, a2, 2
801d512c  bnez  t3, 801d518c           ; the mirror image for side 1 (660 check on t2, attr on t0)
...
801d518c  jr    ra
801d5194  li    v0, -1                 ; D.D. Warrior Lady
801d5198  jr    ra
801d519c   sw   v0, 0x4fd0(a3)         ; both slots = -1
801d51a0  sb    v0, 0x26c(gp)          ; STUB A: the displaced store
801d51a4  lui   a3, 0x801d
801d51a8  lh    a3, 0x4fd0(a3)
801d51ac  lw    v1, 8(s1)              ;         the displaced load
801d51b0  beqz  a3, 801d51c8
801d51b8  li    v1, 1
801d51bc  bgtz  a3, 801d51c8
801d51c4  li    v1, 0
801d51c8  jr    ra
801d51d0  lh    a3, 0x4fd2(a3)         ; STUB B (a3 base set by the hook's delay slot)
801d51d4  lw    v0, 0xc(s1)
801d51d8  beqz  a3, 801d51f0
801d51e0  li    v0, 1
801d51e4  bgtz  a3, 801d51f0
801d51ec  li    v0, 0
801d51f0  jr    ra
801d51f8  .. 68 bytes of data ..
801d523c  li    a1, 690                ; REGION E: the Fake Trap guard
801d5240  bne   a1, v0, 801d5024
801d5248  jr    ra
```

## Decomp cross-reference

* `0x8002061C` is a splat label inside `func_8001F560` (`config/function_ranges.txt` `R 8001F560 1374`),
  asm in `asm/asm_FD5C.s`, no matched C. Battle presentation / aftermath handler.
* `s1 = s0 - 0x6110` with `s0 = 0x800F0000` gives `0x800E9EF0` = `D_800E9EF0`, an `Obj *[]`
  (`src/func_8002D7CC.c` declares `extern Obj *D_800E9EF0[];`). `[2]`/`[3]` are indexed
  `[D_8009B2B1 + 2]` at 0x800204F4..0x80020510.
* `0x26C($gp)` with `$gp = 0x8009B000` is `D_8009B26C`, the mode byte (F17 / F128).
* Symbol extents from `asm/data/overlay_arena.data.s`:
  `gDuel_adwCardStats` `0x801D4244..0x801D4D8E`, `gCard_asNameSortKey` `0x801D4D8E..0x801D5332`
  (0x5A4 = 722 x 2), `gDuel_abCardLevelAttr` `0x801D5332..0x801D5608`.
  So `0x801D4FD0` = sort key index `(0x801D4FD0-0x801D4D8E)/2` = 289 = card 290, and the last
  clobbered byte `0x801D524F` is index 608 = card 609.
* `gCard_asNameSortKey` readers: `src/compare_rec_two_level.c`, `src/compare_rec_two_level_std.c`,
  `BuildDeck_CompareCard` (0x80032B60).

## Card ids the routine hard-codes

Decoded from the SLUS name tables (offsets `0x1C6000 + 2*id`, text at `0x1C0800 + off`, glyph table
from the site's `Ke`):

    660  Stain Storm       "Acid rain destroys an opponent's Machine monsters."   aux 0x60 (attr 6 = Magic)
    690  Fake Trap         "A trap card for tricking your opponent. Nothing happens when it is attacked."
                                                                                 aux 0x70 (attr 7 = Trap)

Attribute nibble verified against known cards: 1 Blue-eyes `0x08` (Light, lvl 8), 2 Mystical Elf
`0x04`, 3 Hitotsu-me Giant `0x24` (Earth), 5 Ryu-kishin `0x13` (Dark), 58 Kuriboh `0x11` (Dark),
4 Baby Dragon `0x53` (Wind). So `>> 4 == 1` is "is DARK".

## Script tests (scratch copies only)

    phoenix_battle.py check   SLUS_014.11        -> "process installed: False", clobber range 290..609
    phoenix_battle.py set     px.11 -o px_mod.11 --effect 58:marshmallon --effect 660:exploder \
                                                 --effect 1:ddwl --exception 722 --exception 57
    phoenix_battle.py check   px_mod.11          -> lists all three effects and both exceptions
    (all Ve/We/Ye bytes re-verified byte-for-byte against the site arrays)
    phoenix_battle.py restore px_mod.11 SLUS_014.11 -o px_res.11 ; cmp px_res.11 SLUS_014.11 -> identical
