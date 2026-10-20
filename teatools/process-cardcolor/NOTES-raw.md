# CARD COLOR — working notes (2026-09-04)

Source: https://www.basededatostea.xyz/extend/tools/process/cardcolor (public route). Tool chunk
`site/js/extend/tools/process/cardcolor.bdc27163.js`, component `ProcessCardColor`, banner "V.260709".
Everything is client-side; the only network calls are the analytics POST (`tipo` 23) and the static
download of `Assets/files/CardColorTemplate.xlsx`.

## The five byte sets in the chunk

    Ve  = "suitable area" check   -> the STOCK bytes expected at the 4 v2 sites
    Ye  = the v2 patch            -> {10944:176B, 29628:8B, 105484:8B, 117392:112B}
    Je  = the v1 patch            -> {29612:4B, 105468:8B, 1881568:64B, 1882000:124B}
    Ke  = the v1 UNDO             -> stock bytes at 29612/105468 + zero fill at 1881568/1882000
    Xe  = 10576   (v2 data offset)      Qe = 1881636 (v1 data offset)

File -> RAM (RAM = 0x80010000 + off - 0x800):

    10576   = 0x2950   -> 0x80012150   361-byte nibble table (v2)
    10944   = 0x2AC0   -> 0x800122C0   both v2 stubs
    29612   = 0x73AC   -> 0x80016BAC   v1 small-card hook
    29628   = 0x73BC   -> 0x80016BBC   v2 small-card hook
    105468  = 0x19BFC  -> 0x800293FC   v1 big-card hook
    105484  = 0x19C0C  -> 0x8002940C   v2 big-card hook
    117392  = 0x1CA90  -> 0x8002C290   v2 library-grid loop
    1881568 = 0x1CB5E0 -> 0x801DADE0   v1 big-card stub
    1881636 = 0x1CB624 -> 0x801DAE24   v1 nibble table
    1882000 = 0x1CB790 -> 0x801DAF90   v1 small-card stub

All stock bytes verified against `~/ygofm-decomp/SLUS_014.11`; `Ve` matches the file exactly, and
0x1CB5E0/0x1CB624/0x1CB790 are zero fill.

## Flow of the component

    startTool()   -> setExtraInfo() (read 722 card names/stats) ; backupPalettes()
                     checkSlus()          all Ye bytes present?  -> already patched, getInfo()
                     checkForOldCode()    all Je bytes present?  -> itsNeedMigrate = true
                     checkSuitableArea()  all Ve bytes present?  -> isEnabledToApply
    applyPatch()  -> generateData() ; if migrating write Ke ; write Ye ; getInfo()
    generateData()   migrating: copy 361 bytes 0x1CB624 -> 0x2950 and zero the old
                     fresh:     slot = {20:1, 21:2, 22:3, 23:1}[cardType] else 0, packed as
                                parseInt(`${hi}${lo}`, 16)   (so only 0..9 would survive a
                                two-digit value; irrelevant because slots are 0..3 here)
    setInfo()     -> called on SLUS download: repack cardList[].data.bgColor into the nibble table
    makeRandom()  -> random 0..6 per card
    importExcel() -> column A card id 1..722, column B slot 0..15

## Palettes (WA side)

    palleteConfig1..7 = {offset: 12075008 + 512*k, size: 72}   -> 0xB84000 + 512*k
    cicles = [0,481280,962560,1443840,1925120,2406400,2887680,3684352,4409344,5658624]
    copyDefault(): for each cicle, copy 512 bytes from (0xB84C00 - 3072) = 0xB84000 to 0xB84C00

`ColorToneEditor.getHeader()` reads `size` = 72 u16 entries at `offset` and decodes
BGR555 (`r = (lo & 0x1F) << 3`, `g = ((hi & 3) << 6) | ((lo & 0xE0) >> 2)`, `b = (hi & 0x7C) << 1`,
`a = hi >> 7`); `apply()` re-encodes and writes into every cicle. So the "palette" the tool edits is
144 bytes out of each 512-byte block.

Measured on the stock disc (WA md5 971c16ea21635b45351e5ae959c53503):

    slot 1 @0xB84000  469 non-zero bytes, identical in all 10 copies
    slot 2 @0xB84200  440                 NOT identical across the 10 copies
    slot 3 @0xB84400  427                 identical
    slot 4 @0xB84600  427                 identical
    slot 5 @0xB84800  427                 identical
    slot 6 @0xB84A00  427                 identical
    slot 7 @0xB84C00    0 (all zero)      identical   <- hence "COPY DEFAULT"

## Proving the default slot map is stock-identical

Three consumers, each of which stock-derives a 0..3 index from the card type; the constants line up
one-for-one with the site's `{20:1, 21:2, 22:3, 23:1}`:

    init_container_entry_objs (0x800291E0)
      .L80029348 (type 0x15 trap)   s3 = 0x102
      .L8002933C (type 0x14 magic,
                  and 0x17 equip)   s3 = 0x101
      .L80029320 (type 0x16 ritual) s3 = 0x103
      .L800293FC (default)          s3 = 0x100, s0 = 0
      then 0x8002947C  addiu v0, s3, 8      <- the sprite id actually used

    func_80016784 (0x80016784), packet at 0x1F800320
      0x800168D8  sw 0x00F10100, 0x10(s1)   -> +0x10 = 0x0100, +0x12 = 241
      0x800169E4  lbu v1, 0x68(s6)          -> the card type stored by init_container_entry_objs
        0x15 -> .L80016A54  sb 0x40,0xE(s1) ; draw ; +0x12 += 2
        0x14 -> .L80016A28                    draw ; +0x12 += 1
        0x16 -> .L80016A88  sb 0x60,0xE(s1) ; draw ; +0x12 += 3
        0x17 -> sb 0x20,0xE(s1) then A28    ; draw ; +0x12 += 1
        else -> .L80016AC0/.L80016ABC       ; no change
      all merge at .L80016BBC  <- the v2 hook

    func_8002BFCC (0x8002BFCC), loop 0x8002C290..0x8002C2FC, 723 iterations
      t2 = 0x15 t1 = 0x14 t0 = 0x16 a3 = 0x17 a2 = 0x170   (set at 0x8002C264..0x8002C274)
      type 0x15 -> 0x180   type 0x14 -> a2 = 0x170   type 0x16 -> 0x190
      type 0x17 -> a2 = 0x170   else -> 0x160
      stored as sh v0, 0x54(a0) with a0 = s5+4, stride 4

    -> 0x160 + 16*slot, 0x100 + slot and 241 + slot all reproduce these exactly for slot 0..3.

Round-trip check: `card_color.py apply` on the stock EXE gives 621 slot-0, 67 slot-1
(magic 20 + equip 23), 10 slot-2 (traps, ids 681-690) and 24 slot-3 (rituals) cards.

## The v1 -> v2 move

v1 hooked the big card at 0x800293FC, which is the DEFAULT branch of the type dispatch
(`.L800293FC`, reached only when the card type is not 0x14-0x17). The four special types
`j .L8002940C` past it. So v1 could not recolour magic / trap / ritual / equip cards at all; v2 moved
the hook to 0x8002940C, the shared tail every card reaches. v1 also never touched
`func_8002BFCC`, so the library grid kept the stock colours.

v1's small-card hook was one instruction earlier (0x80016BAC, the `addiu v1,v1,-8` inside the
draw loop) and its stub had to re-issue that instruction; v2 moved it to the merge label.

## Free space used

0x80012150..0x8001236F is inside the libgpu debug-string block. `card_color.py`'s `STOCK[0x2950]`
holds all 544 stock bytes (the RCS id `.c,v 1.140 1998/01/12 07:52:27 noda Exp yos $` plus
"ResetGraph:", "DrawOTag(%08x)...", "GPU timeout:que=%d,...", "LoadImage2", ...). The tool's own
"suitable area" test only checks the 160 bytes at 0x2AC0, not the 361 table bytes.

The v2 blob at 0x2AC0 reproduces the stock bytes at 0x800122F8..0x800122FF ("OTagEnv(") verbatim —
that 8-byte gap sits between the two stubs and is never executed.

## Round-trip test

    card_color.py apply   -> the four written regions are byte-identical to the site's Ye arrays
    card_color.py restore -> byte-identical to the stock SLUS_014.11 (verified with cmp)
