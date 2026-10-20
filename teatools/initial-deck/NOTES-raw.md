# TEA-Online "Initial Deck" tool — what it patches, and what the game does with it (2026-09-03)

Route: https://www.basededatostea.xyz/extend/tools/data/initialdeck (the "w"
in the link you gave was a typo). Mirror in this directory; logic is
`js/extend/tools/data/initialdeck.6d35ea6b.js`, method `createExcelData`.
Client-side only. Input is WA_MRG.MRG (30-42 MB, `.mrg`) plus an .xlsx filled
from `Assets/files/InitialTemplate.xlsx`.

## What the tool writes

    base   = 16329684 = 0xF92BD4   (byte offset inside WA_MRG.MRG)
    for set r in 0..6:                       # 7 sets, 1464 bytes each
        for u in 0..722:
            off = base + 1464*r + 2*u
            u16 LE value from sheet cell (col C+r, row 4+u)
            written at off AND at off + 176128 (0x2B000)
    u == 0   -> number of cards drawn from this set   (all 7 must total 40)
    u == 1..722 -> weight of card id u                 (each set must total 2048)
    bytes 1446..1463 of each row are never touched (padding)

Template defaults: counts 16, 16, 4, 1, 1, 1, 1.

## Verified on the real disc

WA_MRG.MRG = disc LBA 10102, 0x2400000 bytes. Both copies read back identical:

    copy A: WA offset 0xF92BD4 = in-file sector 0x1F20 + 0x3D4 = disc LBA 18075
    copy B: WA offset 0xFBDBD4 = in-file sector 0x1F76 + 0x3D4 = disc LBA 18161

    set  count  sum   distinct cards   heaviest
    1     16   2048        42          558/563/635/644 @56, 9 @48
    2     16   2048        84          604/606/609/611 @32
    3      4   2048        97          139/142/143/144/155 @24
    4      1   2048        86          3/10/23/25/30 @24
    5      1   2048         2          336, 337 @1024        (one of two)
    6      1   2048         6          330..333 @344, 334 @336
    7      1   2048        28          315/652/654/659 @80

Right after the 7th row sit seven pointers 0x8016ABD4, +0x5B8 each, then 0
(a null-terminated pointer list). That fixes the module load base:
0x8016ABD4 - 0x2BD4 = 0x80168000, so sector 0x1F20 is byte 0 of a module.

## Which module

The EXE's disc-load calls (`func_80014E1C(0,0,sector,count,cb,0,0)`) form a
contiguous chain; the two that cover our sectors are

    0x1EDF + 0x50  name entry  (register_handler_8003BA14, from Main_RunNameEntry)
    0x1F2F + 0x56  password    (register_handler_8003BD14, from Main_RunPasswordMenu)

0x1F20 is 0x41 sectors into the name-entry load, 0x1F76 is 0x47 sectors into
the password load, and NameEntry_Init (0x801683EC) is exactly at offset 0x3EC
of the 0x1F20 sub-module. So each load is [graphics prefix][code+data module
at 0x80168000]; the graphics prefix differs in length. The two modules are
byte-identical for their first 0x7326 bytes (all code, the set table and the
pointer list) and diverge only in later data: name entry and password are one
shared text-entry module with per-screen data, like the 7 duel-overlay copies.
Hence the tool's "+176128" mirror: it keeps the password copy in sync.

## The generator: 0x8016A930  (proposed NameEntry_BuildStarterDeck)

    clear u8 copies[722] on the stack
    dst = gDuel_awPlayerDeck (0x801D0200, u16 card ids)
    for each set pointer p in the list at 0x8016D3DC until NULL:
        n = *(u16*)p; w = (u16*)(p+2)
        while n--:
            threshold = (rand() & 0x7FF) + 1          # 1..2048
            sum = 0
            for i in 0..719:                          # NOTE: 720, not 722
                rand()                                 # extra RNG pull per step
                sum += w[i]
                if sum >= threshold:
                    if copies[i] < 3:
                        copies[i]++; *dst++ = i+1
                        Library_UpdateCardUsedFlag(i + 289)   # marks card i+1 as seen
                    else:
                        n++                            # 4th copy refused: redraw
                    break

Consequences worth knowing for the decomp / modders:
- max 3 copies of any card in the starter deck (redraw, not skip);
- card ids 721 and 722 can never be drawn (loop bound 720) — weight there is
  dead, and a set whose weight is all in the tail yields a short deck;
- if a set's weights sum to less than 2048 a draw can miss entirely and the
  deck comes out short, which is exactly the tool's "must add up to 2048" rule;
- one rand() per weight step, so RNG consumption depends on the walk length.
- Same 2048-threshold walk as Duel_SelectCardDrop in the EXE (drop tables use
  1460-byte rows without the leading count; starter sets use 1464 with it).

## Caller: module entry 0x8016AA6C  (proposed NameEntry_Main)

    memset-like func_80035748(0x801D0000, 0, 0x3000)      # wipe the save block
    printf(fmt@0x80168090, ...)
    NameEntry_Init()
    do { call_four_update_funcs(); rand(); } while (func_80169C08() == 0)   # screen loop
    NameEntry_BuildStarterDeck()
    id = XOR of the 12 name bytes at 0x801D060C
    hi = D_8009B09C; do { v = (hi << 8) | id; hi = rand(); } while (v == 0)
    *(u32*)0x801D0534 = v                                   # save/game identifier

The rand() inside the screen loop is what seeds the deck with how long you
sat on the name screen.
