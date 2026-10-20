# Price Charger - raw working notes (2026-09-04)

## Chunk facts (pricecharger.4174a326.js)
- PriceCharger component (module b8f5). t=16488448 (0xFB9800); read: price = getUint32(t+8*id),
  password = hex string of bytes [7][6][5][4] (i.e. the LE u32 printed as 8 hex digits).
  write: setUint32(t+8*id, price % 1e6), setUint32(t+8*id+4, parseInt(pw,16) % 4294967295).
- removeAllpasswords -> "FFFFFFFE"; disableSystem -> setUint32(t, FFFFFFFF), setUint32(t+4, FFFFFFFF)
  (entry 0 only).
- xlsx: rows 2..last, A id (1..722), B price (>0, <1e6), C parseInt(v,16) (>0, <0xFFFFFFFF).
  Template rows: 1/5000/"02010506", 25/1000/"45151426", 30/999999/"FFFFFFFFE" (sic, 9 chars).
- getTemplate downloads /Assets/files/PriceTemplate.xlsx but names it "FusionTemplate.xlsx"
  (copy-paste from the fusion tool).

## Disc verification (WA_MRG.MRG extracted from the .bin, LBA 10102)
    0xFB9800: 00000000 00000000 | 3F420F00 39116389 | A0000000 44580215 | 46000000 92461876 ...
    card 1 999999 / 89631139   card 2 160 / 15025844   card 3 70 / 76184692
    card 4 999999 / 88819587   card 5 30 / 15303296    card 722 999999 / FFFFFFFE
    after entry 722: FF x (rest of the 3 sectors)
- price histogram: 999999 x122, 30 x58, 120 x36, 800 x35, 55 x34, 60 x29, 25 x27, 100 x27 ...
- SLUS file 0x198800 (RAM 0x801A8000) is zero: the table exists only in WA_MRG.

## Password module (WA 0xFBB000 -> 0x80168000, dumped 0x8000 bytes, objdump -EL mips:3000)
References to the 0x801A8000 arena (all three, nothing reads entry 0):
    8016a308  lui v0,0x801b ; addiu a1,v0,-32760        -> 0x801A8008, lookup walk
    8016a6b4  lui v0,0x801b ; addiu s0,v0,-32768        -> 0x801A8000 + 8*id : price for the prompt
    8016a7b8  lui v1,0x801b ; addiu v1,v1,-32768        -> 0x801A8000 + 8*id : price for the digits
Lookup 0x8016a304..0x8016a378:
    move a0,zero; a1=0x801A8008; v1=a0(0); a2=0x8016D410 (digits)
    loop8: a0 = (a0<<4) | lbu a2[v1]; v1++            ; BCD of the 8 digits
    v1=1; a2=-1
    L: lw v0,0(a1); beq v0,a2 -> ret0                  ; price == -1 terminates
       lw v0,4(a1); beq a0,v0 -> ret v1                ; password match
       a1+=8; v1++; j L
Purchase state machine 0x8016a68c..0x8016a790 (state half at 0x8016D424, found id at 0x8016D4DC):
    price -> 0x801D5608, id -> 0x801D560C; jal 0x8002CCA8 Campaign_TestStoryFlag(0x400+id)
      nonzero -> msg 229 (already used)
    lw 0x801D07E0 (starchips) < price -> msg 227 else msg 228
    confirm branch: jal 0x8002CCE4 Library_UpdateCardUsedFlag(0x400+id); jal 0x80021894 (id)
Text-bank ids used by the module: 0x801B125A/0x801B1245 (lui 0x801b + small addiu) are strings.

## Decomp cross-refs
- findings F25 (digits), F27-F35 (password purchase, used flags), F111/F123 (0x801A8000 arena)
- asm/matchings/func_8002CCA8: story flag test, base gCampaign_abStoryFlags 0x801D0618,
  byte (a0&0x7FF)>>3, bit 0x80>>(a0&7)  -> 0x400+2 -> byte 0x801D0698 bit 0x20 (= F35)
