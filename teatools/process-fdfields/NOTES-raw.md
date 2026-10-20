# FREE DUEL FIELDS — working notes (2026-09-04)

Source: https://www.basededatostea.xyz/extend/tools/process/fdfields (login-gated; mirror in `site/`
taken with a session cookie). Tool chunk `site/js/extend/tools/process/fdfields.05b8d55f.js`,
component `FreeDuelFields`, banner "V.240601".

## Blobs in the chunk

    tt (validation_type_1) [{address:87564, data:[28,128,17,60]}]        // 0x80024E0C == lui s1,0x801c
    at (validation_type_2) [{address:87572, data:[28,128,17,60]}]        // 0x80024E14 == lui s1,0x801c
    st (validation_free_1) [{address:87560, data:[100,179,32,160, 10,128,1,60, 105,179,32,160, 10,128,1,60]}]
    ot (validation_free_2) [{address:87560, data:[112,179,38,164, 114,179,39,164, 100,179,32,160, 105,179,32,160]}]
    nt = 87560   it = 87568                                              // where the j lives, per type
    rt (jump_1)  [{address:87560, data:[152,255,6,8, 28,128,17,60]}]     // j 0x801BFE60 ; lui s1,0x801c
    ct (jump_2)  [{address:87568, data:[152,255,6,8, 28,128,17,60]}]
    lt (mainScript_1) [{address:1771104, data:[...96 bytes...]}]
    ut (mainScript_2) [{address:1771104, data:[...97 entries, one of them a HOLE...]}]
    dt (field_names)  ["-","FOREST","WASTELAND","MOUNTAIN","MEADOW","SEA","DARK"]
    pt (bonusData)    the guardianstars table, copy-pasted and never used

File -> RAM: 87560 = 0x15608 -> 0x80024E08; 87564 = 0x1560C -> 0x80024E0C; 87568 = 0x15610 ->
0x80024E10; 87572 = 0x15614 -> 0x80024E14; 1771104 = 0x1B0660 -> 0x801BFE60.
`[152,255,6,8]` LE = 0x0806FF98 -> j target 0x06FF98<<2 = 0x1BFE60 -> `j 0x801BFE60`.

`extractData()` recovers where the code went straight out of the jump word:

    t = 4 * (getUint32(nt|it) & 0x03FFFFFF) - 63488     // 63488 = 0xF800 = the RAM->file bias

## The two hook sites

Stock (`asm/matchings/init_800eb26c_fields_from_args/`):

    80024DC8 li v0,0x7270 ; lui at,0x800a ; sh v0,B36A(at)
    80024DD4 li v0,0x7280 ; lui at,0x800a ; sh v0,B374(at)
    80024DE0 li v0,3
    80024DE4 lui at,0x800a ; sb a0,B360(at)
    80024DEC lui at,0x800a ; sb a1,B361(at)     <- gDuel_bOpponentID
    80024DF4 lui at,0x800a ; sh a2,B370(at)
    80024DFC lui at,0x800a ; sh a3,B372(at)
    80024E04 lui at,0x800a
    80024E08   sb zero,B364(at)                 <- gDuel_bTerrain = 0   *** type-1 hook ***
    80024E0C lui at,0x800a
    80024E10   sb zero,B369(at)                                          *** type-2 hook ***
    80024E14 lui at,0x800a
    80024E18   sb v0,B26C(at)                   <- D_8009B26C = 3, "start the duel"
    80024E1C jr ra

After `process-freedueltheme` the same function is compacted (it drops the repeated `lui at`s and
inserts a theme lookup at the top), and the two stores move to 0x80024E10 / 0x80024E14 — that is
exactly `validation_free_2`, and why the tool needs two variants and warns about ordering.

Stock bytes confirmed with a direct read of `~/ygofm-decomp/SLUS_014.11`:
`0x15608: 64 b3 20 a0 0a 80 01 3c 69 b3 20 a0 0a 80 01 3c`.

`a1` = opponent id: finding F82 records the module call as
`init_800eb26c_fields_from_args(-1, row*5+col, 0x6000, 0x6000)`.

## The 96-byte body

Disassembles cleanly (see `patch/mainScript_type1_801BFE60.dis`); the interesting parts are:

- `addiu s1,s1,-320` after the delay-slot `lui s1,0x801C` -> the table is code+96 = 0x801BFEC0.
- `sb zero, 0xB369(at)` re-does the store that the type-2 hook displaced. `at` still holds
  0x800A0000, which is only true because the hook site is downstream of a `lui at,0x800a`.
- `lhu s5, 0(0x801D071C + 4*a1)` -> the win counter, compared with the record's u16 `limit`.
- `bnez s2, +3` with `move s5,zero` in the delay slot; the branch picks `lbu 2(s1)` (fieldid1) vs
  `lbu 3(s1)` (fieldid2), then `sb s3, 0xB364(at)` writes `gDuel_bTerrain`.
- the tail zeroes s1,s2,s3(,s4) and `j 0x80024E10` (type 2: `j 0x80024E18`).

## Pinning 0x801D071C

Nothing in the EXE references it (scanned every instruction with immediate 0x0714/0718/071C/0720 —
one false hit, in data). It is touched only from the free-duel screen module, which lives in
WA_MRG.MRG sectors 0x1E88..0x1EDE (`func_80014E1C(0,0,0x1E88,0x57,...)`). Scanning that block for the
same immediates found two sites:

    in-file 0xF6D15C   ... lui v0,0x8017 ; addiu v0,-0x6FD0   -> 0x80169030 = gFreeDuel_abGridAvailable
                       lbu the availability byte for row*5+col, and if set:
                       v1 = 0x801D0000 + 4*(row*5+col)
                       lh a0, 0x71C(v1) ; sw a0, 0x801D5608
                       lh v1, 0x71E(v1) ; sw v1, 0x801D560C
                       => this is FreeDuel_PlaceCursor (0x80168090, finding F80) refreshing the W/L pair

    in-file 0xF6D2A8   v1 = (row*5+col) << 2
                       a0 = 0x801D071C + v1
                       if (lbu 0x8009B362 == 1) a0 += 2      ; 0 = win, 1 = loss
                       *(u16*)a0 += 1
                       if (*(s16*)a0 >= 1000) *(u16*)a0 = 999
                       then sh zero, 0x8009B148 / 0x8009B146 and a dialog
                       => the per-duelist W/L increment, the site findings F25/F73 call "unlocated"

So `gFreeDuel_aDuelistRecords` = 0x801D071C, 40 x {u16 wins, u16 losses}, index `row*5+col`, cap 999,
running up to `gDuel_awRecentCardDrops` at 0x801D07BC. The absolute `jal` targets inside the same
block (e.g. `jal 0x80035BE4` = TextBox_Create, `jal 0x80168004`/`0x80168090`) confirm this is the
module that runs in the 0x8016xxxx window.

## Free space at 0x801BFE60

`gText_aBank` starts at 0x801B0000; the last non-zero byte before `gText_aBankOffsets` (0x801C0000)
is at 0x801BFB4D, so 0x801BFB4E..0x801BFFFF (1202 bytes) is zero padding in the loaded image. The
tool uses 0x801BFE60..0x801BFF5F. Verified by scanning the stock file.

## The hole in mainScript_2

Verbatim from the minified chunk (`grep -o 'ut=\[{address:1771104...'`):

    ...,134,147,0,8,,33,160,0,0]
                    ^^ two commas in a row

That is a genuine JS array hole at index 92; `forEach` never visits it, so `setUint8` is never called
for that byte. Result at 0x801BFEBC: `00 21 a0 00` = 0x00A02100, an SLL with `rs = a1`, which objdump
prints as `.word` (reserved encoding) and which the R3000 executes as `sll a0, zero, 4`. Intended was
`0x0000A021` = `move s4, zero`. `patch/mainScript_type2_801BFE60_asShipped.dis` shows it.

## Opponent names

`oppList = getCardInfo(dv, {desde:808, hasta:847})`. The name pointer table is at file 1859584 =
0x1C5C00, entries are u16 biased by 22528 (0x5800), strings are the game's own charset (extracted the
`l<code>` map out of the chunk). Decoded 808..847:

    808 Build Deck        818 Weevil Underwood   828 Teana 2nd            838 High Mage Kepura
    809 Simon Muran       819 Mai Valentine      829 Ocean Mage           839 Labyrinth Mage
    810 Teana             820 Bandit Keith       830 High Mage Secmeton   840 Seto 2nd
    811 Jono              821 Shadi              831 Forest Mage          841 Guardian Sebek
    812 Villager1         822 Yami Bakura        832 High Mage Anubisius  842 Guardian Neku
    813 Villager2         823 Pegasus            833 Mountain Mage        843 Heishin 2nd
    814 Villager3         824 Isis               834 High Mage Atenza     844 Seto 3rd
    815 Seto              825 Kaiba              835 Desert Mage          845 DarkNite
    816 Heishin           826 Mage Soldier       836 High Mage Martis     846 Nitemare
    817 Rex Raptor        827 Jono 2nd           837 Meadow Mage          847 Duel Master K

index = string - 808, so 0 is the Build Deck tile and 1..39 the duelists — matching `row*5+col`.

## Round-trip test

    fd_fields.py apply / set / restore  -> restore reproduces the stock SLUS_014.11 byte for byte
    fd_fields.py MAIN1 == the site's lt array; MAIN2_SITE == the shipped (buggy) type-2 bytes
