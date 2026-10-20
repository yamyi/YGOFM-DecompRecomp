# TEA-Online "DUEL RESULT" tool — what it actually patches (2026-09-03)

Source: https://www.basededatostea.xyz/extend/tools/duel (Vue SPA, no login needed
for the page itself). Mirror of every asset is in this directory; the logic is
`js/extend/tools/duel.eb4e3cfe.js`, component `DuelEditor`. The tool is 100%
client-side: it reads SLUS_014.11 into a DataView, pokes bytes at three file
offsets, and calls saveAs(). The only network call is an analytics POST.

File offset -> RAM: SLUS load address 0x80010000, header 0x800, so
RAM = 0x80010000 + (file_off - 0x800).

## 1. "Aditional Starchips per Duel"  (file 0x126DC -> RAM 0x80021EDC)

Inside `Duel_MaybeEndOfDuel` (0x800218F0, idb2018 `u_maybe_endOfDuel`):

    80021ECC  lw   v0, 0x2E0(gp)      ; D_8009B1E8 = duel-state object
    80021ED0  lw   a0, 0x2D0(gp)      ; 0x8009B1D8 = current player's record
    80021ED4  lbu  v1, 0x3A(v0)       ; starchip prize for this duel (u8)
    80021ED8  lw   v0, 0x5E0(a0)      ; player starchips (u32)
    80021EDC  nop                     ; <-- tool writes: addiu v1, v1, N   (0..10000)
    80021EE0  addu v0, v0, v1
    80021EE4  sw   v0, 0x5E0(a0)
    ...       clamp to 0xF423F (999,999)

Encoding written: [N & 0xFF, N >> 8, 0x63, 0x24] = 0x2463NNNN = addiu v1,v1,N.
Restoring 0 writes four zero bytes (the original nop).

Facts for the symbol library:
- player record + 0x5E0 : u32 starchips, hard cap 999,999.
- duel object   + 0x3A  : u8 starchip prize awarded at end of duel.
- duel object   + 0x3C  : u16 card-drop id (stored just before the colour site,
  also mirrored to gDuel_wSelectedCardID and gDuel_CardDropID2).

## 2. "Result color"  (file 0x1247C -> RAM 0x80021C7C, 8 bytes)

    80021C68  lw   a0, 0x2E0(gp)
    80021C6C  lui  v1, 0x801D
    80021C70  lui  at, 0x800A
    80021C74  sh   v0, gDuel_wSelectedCardID
    80021C78  sh   v0, 0x3C(a0)
    80021C7C  sll  v0, v0, 16        ; <-- replaced by  addiu a1, zero, (COM<<8)|YOU
    80021C80  sra  v0, v0, 16        ; <-- replaced by  sw    a1, 0x5708(v1)  = D_801D5708
    80021C84  sw   v0, gDuel_CardDropID2

So the tool stores the 32-bit word {YOU, COM, 0, 0} into D_801D5708[0..3] at
end of duel (dropping a sign-extension it considers harmless). Default bytes
are the original sll/sra pair.

Colour ids the site exposes: 0 White (default), 1 Yellow, 2 Blue, 3 Green,
4 Grey, 5 Orange, 6 Red.

What this tells us about D_801D5708 (currently a placeholder name; the decomp
comments call it a "state-bar"/"nibble table"):
- It is a 16-byte TEXT COLOUR SLOT table. `func_80038498` (matched C) maps a
  text-stream byte with bit 0x80 set through `D_801D5708[byte & 0xF]`, and
  `func_8003C4E0` seeds five slots to 4 (grey), the active slot to 0 (white)
  and the other to 2 (blue) — exactly the palette above.
- The duel result screen draws the YOU / COM numbers through slots 0 and 1.
- Proposed name: `gText_abColorSlots` (u8[16]); slot values are font CLUT rows.

## 3. "Replace You with @username"  (file 0x1A0D14 -> RAM 0x801B0514, 3 bytes)

This is data, not code: gText_aBank (0x801B0000) + 0x514, i.e. inside string
index 62 of the bank (offset table gText_aBankOffsets at 0x801C0000).

    string 62 @0x50E: f8 17 14 05 18 05 | 24 21 35 ff | 00 3d 2f ff      "YOU"
    string 63 @0x51C: f8 17 22 05 26 05 | 2b 21 1e ff | 00 3a 2f ff      "COM"

Tool writes FC 5A 12 over 24 21 35 (Y O U). FC 5A 12 is the "insert player
name" control sequence: it occurs ~100 times across the dialogue bank, and
string 2 (0x12) is `2c 18 1e 25 48 FC 5A 12 f8 16 ff` = "NAME:" + <player>.
Restoring writes 24 21 35 back.

Charset facts (frequency-ordered, upper case): Y=0x24 O=0x21 U=0x35 C=0x2B
M=0x1E N=0x2C A=0x18 E=0x25, ':'=0x48. Lower case starts near 0x01 (space=0x00,
'.'=0x0B, 0xFE newline-ish, 0xFF terminator, F6..FD control prefixes).

## Other tools on the same site

The page loads chunks chunk-2d0be2d7 / 2d0ccb5f / 2d20ec33 (language files);
other tools are separate routes under /extend/tools/<name> and can be mirrored
the same way: `curl` the route, pull every /js/ and /css/ link from the HTML.
