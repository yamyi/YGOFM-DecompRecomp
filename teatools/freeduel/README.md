# Free Duel Music tool

Route: `extend/tools/freeduel`. Input: SLUS_014.11 (accepts `.11`, 1,902,591..2,097,152 bytes).
Page version V.220724. **Not** the free-duel opponent grid: it swaps the BGM played in every
free duel for another of the game's 57 tracks ("music in FM can't be changed for a new one, only
swapped for an existing one"). One u16 patch, client-side.
Script: `scripts/freeduel_music.py` (list / inspect / apply / restore on a SLUS copy).
Raw session notes: `NOTES-raw.md`.

Status: decoded, stock word verified, consumer chain located in matched C; trivial recomp mod.

## 1. The patch

| | |
|---|---|
| file offset | 0x155C8 (2 bytes) |
| RAM | 0x80024DC8, first instruction of `init_800eb26c_fields_from_args` |
| stock word | `24027270` = `addiu v0, zero, 0x7270` -> stored to `D_8009B36A` |
| patched word | `2402CCPP` where `PPCC` = BGM code = `0x7000 \| (track << 4)` |

The site keeps the code as two bytes `p1` (low) / `p2` (high); its default highlight is
"FREEDUEL SELECT THEME" (0x72C0) but the retail value is 0x7270 = track 0x27 **Freeduel Theme**.

Matched C (`src/init_800eb26c_fields_from_args.c`):

    void init_800eb26c_fields_from_args(int a0, int a1, int a2, int a3) {
        D_8009B36A = 0x7270;      /* duel BGM            <-- patched constant  */
        D_8009B374 = 0x7280;      /* 3D battle BGM (track 0x28) -- not exposed */
        D_8009B360 = a0;  D_8009B361 = a1 /* gDuel_bOpponentID */;
        D_8009B370 = a2;  D_8009B372 = a3;
        D_8009B364 = 0;   D_8009B369 = 0;  D_8009B26C = 3;   /* mode: duel start */
    }

Callers: the free-duel confirm (`FreeDuel_UpdateScreen`, module 0x80168F84: `(-1, row*5+col,
0x6000, 0x6000)`, F82/F124), `func_80030F40` (`(-1, 1, 0x8000, 0x8000)`), and
`mask_test_800eb26c_reinit_and_poll` at 0x8002DD3C (`(-1, -1, 0, 0)`, the 2P path). Campaign
duels do **not** go through it: the story-script duel op (`F8 0D`, handler `func_80038530`)
fills the same globals itself and derives `D_8009B36A` from the script's music halfword
(`func_80036D3C`), with `D_8009B374` = 0x72A0, or 0x7280 for opponents 9..16, 0x7290 for 0x11,
0x72B0 for 0x26. So the patch changes free duels (and the two other `init_...` callers) only.

Consumer: `func_8001825C` (duel-screen setup) at 0x8001848C:

    80018478  lh   v0, 0x34(v1)
    80018480  beqz v0, .L80018498
    80018488  lui  a0, %hi(D_8009B36A)
    8001848C  lhu  a0, %lo(D_8009B36A)(a0)
    80018490  jal  call_masked_and_store_orred    ; SD play-by-code (same entry used with 0x7350 elsewhere)

## 2. BGM code table

Code = `0x7000 | (track << 4)`; sound-effect ids are the small numbers passed to the same
entry (SE 0x2F, 0x30 in `FreeDuel_UpdateScreen`), BGM codes are the 0x7xxx range. Track names
are the site's (module `1929` of chunk-common plus the page's list).

| track | code | name | track | code | name |
|---|---|---|---|---|---|
| 00 | 7000 | Main Menu | 1D | 71D0 | Preliminary Match Theme |
| 01 | 7010 | Input Name Menu | 1E | 71E0 | Finals Match Theme |
| 02 | 7020 | Introduction Title Screen | 1F | 71F0 | Seto Kaiba Theme |
| 03 | 7030 | Tournament Announcement | 20 | 7200 | Egyptian Duel Theme |
| 04 | 7040 | Modern Times | 21 | 7210 | Mage Duel Theme |
| 05 | 7050 | Inside the Puzzle | 22 | 7220 | High Mage Duel Theme |
| 06 | 7060 | Preliminary Face-Off | 23 | 7230 | Heishin Theme |
| 07 | 7070 | Finals Face-Off | 24 | 7240 | Priest Seto Theme |
| 08 | 7080 | Seto Kaiba Face-Off | 25 | 7250 | DarkNite & Nitemare (1) |
| 09 | 7090 | Card Shop | 26 | 7260 | DarkNite & Nitemare (2) |
| 0A | 70A0 | Metropolis I | **27** | **7270** | **Freeduel Theme (stock)** |
| 0B | 70B0 | Metropolis II | 28 | 7280 | 3D Battle Theme |
| 0C | 70C0 | Simon Muran | 29 | 7290 | Seto Kaiba 3D Battle |
| 0D | 70D0 | Egypt in Ruins | 2A | 72A0 | 3D Battle Egypt |
| 0E | 70E0 | Build Deck | 2B | 72B0 | DarkNite 3D Battle |
| 0F | 70F0 | Hidden Card Shop | 2C | 72C0 | Freeduel Select Theme |
| 10 | 7100 | Valley of the Kings | 2D | 72D0 | Library Menu |
| 11 | 7110 | Sea Shrine | 2E | 72E0 | You Win |
| 12 | 7120 | Forest Shrine | 2F | 72F0 | You Lose |
| 13 | 7130 | Desert Shrine | 30 | 7300 | Game Over |
| 14 | 7140 | Meadow Shrine | 31 | 7310 | Exodia |
| 15 | 7150 | Mountain Shrine | 32 | 7320 | Epilogue |
| 16 | 7160 | Vast Shrine | 33 | 7330 | Ending Credits |
| 17 | 7170 | Dark Shrine | 34 | 7340 | Town Plaza Festival |
| 18 | 7180 | Seto's Betrayal | 35 | 7350 | Password Menu |
| 19 | 7190 | Forbidden Ruins | 36 | 7360 | Millennium Item Found |
| 1A | 71A0 | Heishin Millennium Puzzle | 37 | 7370 | Forbidden Ruins (2) |
| 1B | 71B0 | Heishin Invasion | 38 | 7380 | Simon Muran (2) |
| 1C | 71C0 | DarkNite's Arrival | | | |

Cross-checks: `FreeDuel_Init` ends with 0x72C0 (F121 calls it "SE 0x72C0" -- it is the select
theme), the Exodia handler plays 0x7310, `func_80030F40` pre-sets 0x71D0 (then overwritten).

## 3. The "special duel theme process" refusal

`getMusic()` first runs `checkCode()`: it compares 84 bytes at file offset 1,882,128 (0x1CB810,
RAM 0x801CB010, a zero region of the EXE: 0x801CB000..0x801D0000 is all zeros in retail) with a
signature from chunk-common module `1929`, and refuses the file if they match. The signature
decodes as a relocated copy of `init_800eb26c_fields_from_args` with a per-opponent lookup:

    lui  v0, 0x801E ; addu v0, v0, a1 ; lb v0, -0x4FF0(v0)   ; table[opponent] at 0x801DB010 (s8)
    sll  v0, v0, 4  ; addiu v0, v0, 0x7000                   ; code = 0x7000 | track<<4
    sh   v0, D_8009B36A ; li v0, 0x7280 ; sh v0, D_8009B374 ; sb a0, D_8009B360 ; sb a1, D_8009B361 ...

That is another site tool (per-opponent duel themes, default track "27") installing a code cave
at 0x801CB010 and a 40-byte track table at 0x801DB010; presumably the original function gets a
`j 0x801CB010`. This tool cannot coexist with it, hence the check. Both addresses are free space
worth remembering for the recomp.

## Recomp options

1. One `psx_mod_write_code_word(0x80024DC8, 0x24020000 | code)` at startup (base EXE).
2. Better: hook the play call in `func_8001825C` (0x80018490) or write `D_8009B36A` from a
   frame hook when the mode byte says a free duel is starting, which allows a per-opponent
   table (the site's other tool) or even per-terrain music without touching code.
3. `D_8009B374` (3D battle theme, stock 0x7280) can be changed the same way; the site leaves it.

## Decomp findings (proposed)

- `D_8009B36A` / `D_8009B374` | duel BGM code / 3D-battle BGM code, `0x7000 | track<<4`; defaults
  0x7270 / 0x7280 from `init_800eb26c_fields_from_args`, campaign overrides in `func_80038530` | `gDuel_wBgmCode` / `gDuel_wBattleBgmCode`
- `0x80024DC8` | `init_800eb26c_fields_from_args(a0, opponent, a2, a3)` = duel-request setup used
  by free duel, `func_80030F40` and the 2P path | `Duel_Request`
- `call_masked_and_store_orred` | SD "play by code": small ids = SE, 0x7000+ = BGM track<<4 | `SD_Play`
- BGM track list above (57 tracks, 0x00..0x38) | `SD_BGM_*` enum
- `0x801CB000..0x801D0000` | zero in the retail EXE (site code-cave area) | (fact)

## Open questions

- `func_80030F40` (`(-1, 1, 0x8000, 0x8000)`, presets 0x71D0 then calls init which overwrites it):
  which screen is it (tutorial duel vs Simon?) -- its caller was not found by `jal` grep.
- Server side: analytics POST only (`api/v2/tools`, tipo 3).
