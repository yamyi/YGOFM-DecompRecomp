# Initial Deck tool

Route: `extend/tools/data/initialdeck`. Input: WA_MRG.MRG (30..42 MB, `.mrg`) plus an .xlsx
made from `site/Assets/files/InitialTemplate.xlsx`. Client-side only.
Script: `scripts/starter_sets.py` (dump / verify / export CSV / import CSV, works on WA_MRG.MRG
or directly on a MODE2/2352 .bin disc image). Module dump + disassembly: `module/`.
Raw session notes: `NOTES-raw.md`.

## The data: 7 starter "sets"

    WA_MRG.MRG offset 0xF92BD4 (copy A)  and  0xFBDBD4 (copy B, = A + 0x2B000)
    7 rows x 1464 bytes:  u16 cardsToDraw, u16 weight[722] (index = card id - 1), 18 bytes pad
    followed by 7 pointers 0x8016ABD4 + 0x5B8*k, then 0   (RAM addresses, see below)

Rules the game imposes (see generator): counts should total 40, each row's weights should
total 2048. Stock values, verified on the US disc:

    set  draws  distinct  heaviest cards
    1     16      42      558 563 635 644 (56 each), 9 (48)
    2     16      84      604 606 609 611 (32 each)
    3      4      97      139 142 143 144 155 (24 each)
    4      1      86      3 10 23 25 30 (24 each)
    5      1       2      336 or 337 (1024 each)
    6      1       6      330..333 (344), 334 (336)
    7      1      28      315 652 654 659 (80 each)

## Where it lives in RAM

The table is data inside the **text-entry screen module**, which is loaded to 0x80168000 by
two different disc loads: name entry (`func_80014E1C(0,0,0x1EDF,0x50,...)`) and password
(`...0x1F2F,0x56...`). Each load = graphics prefix + module; the module starts at in-file
sector 0x1F20 (name entry) / 0x1F76 (password). Both modules are byte-identical for their
first 0x7326 bytes (all code, the table, the pointer list) and differ only in later data.
That is why the site mirrors every write to +0x2B000: copy B is the password screen's copy.

    0x8016ABD4  gNameEntry_aStarterSets    7 x 1464 B (proposed name, decomp F132)
    0x8016D3DC  gNameEntry_apStarterSets   7 pointers + NULL

## The generator: 0x8016A930  (module code, proposed `NameEntry_BuildStarterDeck`)

    copies[722] = 0
    dst = gDuel_awPlayerDeck (0x801D0200, u16 ids)
    for each set p (pointer list until NULL):
        n = *(u16*)p; w = (u16*)(p + 2)
        while n--:
            threshold = (rand() & 0x7FF) + 1           # 1..2048
            sum = 0
            for i in 0..719:                           # 720, NOT 722
                rand()                                 # one extra pull per step
                sum += w[i]
                if sum >= threshold:
                    if copies[i] < 3: copies[i]++; *dst++ = i+1; Library_UpdateCardUsedFlag(i+289)
                    else:             n++              # 4th copy refused -> redraw
                    break

Consequences:
- max 3 copies of a card; a refused draw is re-rolled, not skipped;
- card ids 721 and 722 can never be drawn (any weight there is dead);
- a row summing to less than 2048 can miss and the deck comes out short of 40;
- RNG consumption depends on how far each walk goes.

Called from the module entry 0x8016AA6C (proposed `NameEntry_Main`): wipe save block
(0x801D0000, 0x3000 bytes) -> NameEntry_Init -> loop {update; rand()} until the screen returns
non-zero -> build deck -> store `(rand()<<8) | XOR(12 name bytes @0x801D060C)` (non-zero) at 0x801D0534.

## Recomp options

1. **Data patch on load.** Frame hook: when `psx_mod_read_word(0x8016D3DC) == 0x8016ABD4` the
   module is resident; overwrite the 7 rows at 0x8016ABD4 from a player file (CSV from
   `starter_sets.py export`). Re-check every frame because the module is reloaded per visit.
   Both screens carry the table, but only the name-entry path calls the generator.
2. **Replace the generator.** Hook 0x8016A930 to a native function: same pointer list, but you
   can lift the 720 bound, the 3-copy cap, or add more than 7 sets (the list is NULL-terminated
   and the loop has no fixed set count, so extra pointers into reclaimed RAM just work).
3. **Deterministic starter decks** for a "duelist pack" style mod: write the 40 ids to
   0x801D0200 directly after the generator (hook at the `jal 0x8016a930` return, 0x8016AAD8).
