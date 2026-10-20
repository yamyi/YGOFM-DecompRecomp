# x2 — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/data/x2.af4f1144.js (component `SpecialAtkDfd`). Core:

    we=[36868,36892,37048,37072,86732,86784,100488,100520,100724,100756,105396,105460,119884,
        141608,141640,142728,142760,142964,142996,144812,144832,333152,333188]
    checkCode : all dataview.getUint8(off) == 128  -> isCodeComplete (tool refuses)
    insertCode: setUint8(off,128) for each
    modifyValues: base 1854020 (=0x1C4A44), 722 x u32 LE:
        a = (a>>18<<18) | (floor((a&511)/2)) | (floor(((a>>9)&511)/2)<<9)
    trySave: insertCode, modifyValues, saveAs(filename)   (FileReader accepted ".11", 1 MiB..3 MiB)

Stock words at the 23 offsets (python struct over ~/ygofm-decomp/SLUS_014.11): all `sll ..,1`
(0x00021040 / 0x00031840 / 0x00028040 / 0x00052040 / 0x00031040 / 0x00042040), low byte 0x40.

Function membership from `grep -rl "/\* .* 8002CC4C " asm/` + glabel:
func_80018608 (4), card_record_fill 0x800249E0 (2, asm_1517C.s), func_80027DF8 (4),
init_container_entry_objs 0x800291E0 (2), Duel_GetBaseCardStat 0x8002CBF4 (1),
func_800320BC (2), func_800323F8 (4), func_80032C48 (2), func_80060B38 (2, asm_51338.s).

Scan script (idea): for each word with opcode 0x0C (andi) and imm 0x1FF, look ahead 8 words for
`(w & 0xFFE007FF) == 0x40` (sll rd,rt,1). EXE: 23 hits == the tool list. WA_MRG.MRG whole file: 0.
(First attempt used a wrong mask 0xFC00F83F and found nothing — keep the corrected mask.)

Halving loss: 135 cards with atk9 or def9 odd (first: 11,63,78,83,84,85,86,87).

Script test (scratch copies): apply -> inspect shows 150/125 for BEWD (x20 = 3000/2500);
restore --stock == stock (cmp clean); restore without --stock differs from stock in 149 bytes.
apply changes 1517 bytes vs stock (23 code + stats words).

Not found: any `lui 0x801D`+`addiu 0x4244` in WA_MRG (mask `(w&0xFFE0FFFF)==0x3C00801D` for lui),
so the recomp's 0x8018xxxx "library overlay" stats sites are not plain code on disc.
