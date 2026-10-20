# icon — raw working notes

## Mirror

`site/js/extend/tools/icon.36256049.js` (plus `chunk-common.eec171ac.js`, shared components).
Pretty-print with `sed 's/},{/},\n{/g; s/;/;\n/g'`.

Identifiers that matter (`tt` = `IconEditor`):

    getIcons()            t = 1853568  -> 0x1C4880, three 128-byte frames, `15 & b` then `b >> 4`
    getHeader()           t = 1853536  -> 0x1C4860, 16 x u16 BGR555
    getName()             2*n + 1853444 -> 0x1C4804, 32 x 2 bytes, reverse-lookup through table X
    getCode()             4 chars at 2950 (0xB86) + 5 chars at 2955 (0xB8B)
    setNewGameCode()      setBytes(this.code, 2950)          // 10 ASCII bytes
    setNewGameName()      setBytesWithTable(this.name, 1853444)
    setNewHeader16(t,e)   black -> (1,1,1); byte0 = (g>>3 & 7)<<5 | r>>3 ; byte1 = stp<<7 | (b>>3)<<2 | g>>6
    setNewBody16(t,e)     chunk table Z, writes dataview[t + n + 8*s], nibble = (hi<<4)|lo
    X                     ASCII -> full-width Shift-JIS table (the site's own)
    Z                     [{data (0,0)-(8,16) -> canvas (0,0)}, {(0,16)-(8,32) -> (16,0)}, {(0,32)-(8,48) -> (32,0)}]

Shared `ImageConverter` (`K` here, identical to the logo/font tools): `createHeader` truncates each
channel to 5 bits, applies `keep_black` (opaque black -> (8,8,8)), counts, keeps the `num_colors`
most frequent, sorts by `order = r<<16|g<<8|b`; `createBody` maps each pixel to the nearest
non-transparent palette entry, or to the first transparent entry when alpha == 0.

## Verified stock bytes (`~/ygofm-decomp/SLUS_014.11`)

    0x1C4800  53 43 13 01                                    "SC", 3 frames, 1 block
    0x1C4804  82 78 82 95 81 7c 82 66 82 89 81 7c 82 6e 82 88 81 49 81 40 ...
              -> shift_jis "Ｙｕ−Ｇｉ−Ｏｈ！　Ｆｏｒｂｉｄｄｅｎ　Ｍｅｍｏｒｉｅｓ　　　　"
    0x1C4844  28 zero bytes
    0x1C4860  2548 67BF 29F5 14ED 0046 03FF 0235 016E 00A8 0018 082F 1466 1000 11A5 7FFF 0C85
    0x1C4880  bb9aa95bb5a9bb6bb7a6566bb5ba7b76...    (frame 0)
    0x1C4900  bb9aa95bb599baabbb9aa95bb5a9bb6a...    (frame 1)
    0x1C4980  bb9a5a6bb5a97b76b7a66675b6ba78b7...    (frame 2)
    0x1C4A00  end of the title frame (0x80 header + 3 x 0x80 frames = exactly 0x200 B);
              what follows is unrelated data, mostly zero for the first 0x40 bytes
    0x0B84    "BASLUS-01411-YUGIOH\0Make Fil..."

String addresses found by searching the SLUS:

    "bu%02X:%s"           file 0x0D38  RAM 0x80010538
    "BASLUS-01411-YUGIOH" file 0x0B84  RAM 0x80010384
    "Make File\n"         file 0x0B98  RAM 0x80010398
    "Fail File\n"         file 0x0BA4  RAM 0x800103A4

The site's table round-trips the stock title exactly, which is the check that the table is the
game's own: `-` = `81 7C`, `!` = `81 49`, space = `81 40`, `Y` = `82 78`, `u` = `82 95`.

## Decomp

    grep -rn "D_801D4000" src/ asm/ include/
      src/func_8003D03C.c        backward_word_copy_with_tail_dispatch(arg0, D_801D4000, 0x200)
      asm/asm_2E41C.s:487        8003E240  lui $a1, %hi(D_801D4000)   <- the save writer
      asm/data/overlay_arena.data.s:89259  dlabel D_801D4000 / .word 0x01134353

`func_8003E1D4` (asm/asm_2E41C.s, `glabel` at line 457) is the save-creation phase; disassembled
with `mips-linux-gnu-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x8003E1D4`. jal targets
decode to `func_80044CD4` (find file), `func_8003D46C`, `backward_word_copy_with_tail_dispatch`
(0x800356A0, already named), `func_80035748` (word-fill memset, see `config/blacklist.txt`), and
`func_800442E4` (which sprintf's `"bu%02X:%s"` and calls `_card_info`).

Symbols already in `config/symbol_addrs.txt`: `D_801D4000`, `D_80010384`, `func_8003E1D4`,
`func_800442E4`, `func_80044CD4`, `backward_word_copy_with_tail_dispatch`, `MemCardOpen`,
`MemCardWriteFile`, `MemCardCreateFile`, `_card_info`, ... — none of them documented as the save
title frame.

## Cross-check against the other image tools

The hint to verify was whether this tool edits the memory-card icon or the in-game UI icon sheet.
It is the memory-card icon: "SC" magic + icon flag + Shift-JIS title + 16-colour CLUT + 3 x 128-byte
16x16 4bpp frames, at SLUS `0x1C4800`. The UI icon sheet (WA_MRG `0xB50000`, 256x160 4bpp, loaded by
`func_80043960` as part of the 54-sector boot block with the game font at `0xB48000`) is a different
asset and belongs to `image-gamefont` / a UI-icons tool.

## Script tests (scratch copies only)

    save_icon.py check   SLUS_014.11
    save_icon.py dump    ic.11 icon1        -> icon1.png, 48x16, Yugi's face x3
    save_icon.py import  ic.11 icon1.png -o ic_mod.11 --title "MY COOL MOD" --code SLUS-99999
    save_icon.py dump    ic_mod.11 icon2    -> icon1 vs icon2: max channel delta 0
    save_icon.py restore ic_mod.11 SLUS_014.11 -o ic_res.11 ; cmp ic_res.11 SLUS_014.11 -> identical

`check` on the re-imported file shows the CLUT as `9000 9000 8C85 ...` — every entry now has STP,
which is what the site does too (see README §3).
