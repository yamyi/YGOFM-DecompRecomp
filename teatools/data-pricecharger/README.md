# Price Charger tool

Route: `extend/tools/data/pricecharger` (V.221220). Inputs: SLUS_014.11 (`.11`, only to
read card names/ATK/DEF/level for the UI and formulas) and WA_MRG.MRG (`.mrg`), plus an
optional `.xlsx` made from `site/Assets/files/PriceTemplate.xlsx`. Client-side only; only
the WA file is written back.

Purpose: edits the PASSWORD-screen table: each card's starchip price and its 8-digit
password. Bulk tools: random price in a range, price from a formula over card stats,
random/correlative passwords, remove all passwords, "disable password system", xlsx
import, and a `CardList.txt` export of the result.

Status: decoded, disc-verified (Blue-eyes 89631139 / 999999, Mystical Elf 15025844 / 160
= decomp F31), password module disassembled. Script: `scripts/price_table.py` (dump /
export / import CSV / set / nopass / disable / kill / restore, on WA_MRG.MRG or a raw
disc image).

## 1. The data

    WA_MRG.MRG offset 0xFB9800   in-file sector 0x1F73   disc LBA 18153   3 sectors
    723 entries x 8 bytes, index = card id (entry 0 unused, zeros):
        u32 price      starchips, little-endian (stock 10..999999)
        u32 password   the 8 digits as BCD nibbles: 0x89631139 <-> "89631139"
                       0xFFFFFFFE = card has no password
    entries 723.. are 0xFF filler (price 0xFFFFFFFF = list terminator)

Loaded to RAM 0x801A8000 when the PASSWORD screen is entered (sector 0x44 of the
`func_80014E1C(0,0,0x1F2F,0x56,...)` load whose module part lands at 0x80168000 from
sector 0x1F76); decomp name `gLibrary_aPasswordCardData` = 0x801A8008 = entry 1. The EXE
image is zero there (that arena doubles as the story-script buffer, F111/F123).

Stock facts: 122 cards priced 999999 (effectively unbuyable), 24 cards without a
password (356 360 364 365 374 380 701-706 708-710 713 715-722), no duplicate passwords.

Site operations (`extractPriceAndPasswords` / `writePriceAndPasswords`):

| button | effect on the table |
|---|---|
| price range | `price = floor((max-min)*rand) + min`, clamped 0..999999 |
| formula | `math.evaluate` over `[NUMBER] [ATK] [DFD] [LVL]`, floored, clamped 0..999999 |
| random password | 8 random digits, unique across the list; after 9 collisions falls back to the card id zero-padded |
| correlative | password = card id as 8 digits (00000001 ...) |
| remove all passwords | every password -> `FFFFFFFE` |
| disable password system | entry 0 -> `FF FF FF FF FF FF FF FF` (see quirk below) |
| xlsx | template columns A = id (1..722), B = price (< 1e6), C = password parsed as HEX text (so "02010506" -> 0x02010506); only rows with all three cells are applied |

Every write goes through `price % 1e6` and `password % 0xFFFFFFFF`, so the UI can never
produce the 0xFFFFFFFF terminator itself. The download also produces `CardList.txt`
("001. Blue-eyes white dragon 89631139 | 999999").

## 2. What the game does with it (password module, RAM 0x80168000 = WA 0xFBB000)

Lookup, `0x8016A304` (proposed `Password_LookupCard`):

    8016A308  lui   v0, 0x801B ; addiu a1, v0, -0x7FF8   ; a1 = 0x801A8008 (entry 1)
    8016A31C  a0 = (a0 << 4) | gPassword_abDigits[i]     ; i = 0..7 -> 8 BCD digits (0x8016D410, F25)
    8016A33C  v1 = 1
    8016A344  lw v0, 0(a1)  ; beq v0, -1 -> return 0     ; PRICE == 0xFFFFFFFF ends the list
    8016A354  lw v0, 4(a1)  ; beq a0, v0 -> return v1    ; password match -> card id
    8016A360  a1 += 8 ; v1 += 1 ; loop

Purchase path (`0x8016A68C..`): with the found id in 0x8016D4DC it loads
`price = *(u32*)(0x801A8000 + 8*id)` into the text argument `D_801D5608` (+4 = id),
calls `Campaign_TestStoryFlag(0x400 + id)` - the one-time-use flag (F31/F35: bit 0x400+id
of `gCampaign_abStoryFlags` 0x801D0618, i.e. byte 0x801D0698 for card 2) - and shows
message 229 if already used; else compares `gLibrary_dwStarchips` (0x801D07E0) with the
price: message 227 (can't afford) or 228 (confirm). On confirm (0x8016A75C):
`Library_UpdateCardUsedFlag(0x400 + id)`, `ring_buffer_insert_801d0200(id)` (trunk + 1,
recent list), and the starchips are deducted. The price is re-read at 0x8016A7B8 for the
digit display (`int_to_digits`, F28).

Consequences and quirks:

- A password of `FFFFFFFE` can never equal a BCD value, so it means "no password" but
  keeps the walk going. A PRICE of 0xFFFFFFFF stops the walk; the stock terminator is the
  FF filler after card 722.
- The site's "disable password system" writes entry 0, but the game's walk starts at
  entry 1 (0x801A8008) and never reads entry 0 - as far as the module code shows, that
  button does nothing. What actually disables the system is price 0xFFFFFFFF in entry 1
  (`price_table.py kill`), which the UI cannot produce because of its `% 0xFFFFFFFF`.
- Prices are u32 but the UI clamps to 999999; the compare is unsigned so larger values
  simply make a card unbuyable.
- The one-time-use flag is per card id, so changing a card's password does not reset it
  on an existing save.

## 3. Recomp options

1. Data patch on load (mirror of the site): frame hook; the module is resident when
   `psx_mod_read_word(0x8016A308) == 0x3C02801B && psx_mod_read_word(0x8016A30C) == 0x24458008`
   (the lookup's `lui/addiu`), then compare `0x801A8008` with the stock BEWD entry
   (`0x000F423F`, `0x89631139`) and overwrite 0x801A8008..0x801A9698 (722 x 8) with the
   player's table (CSV from `price_table.py export`). Re-check every frame; the arena is
   re-streamed on every PASSWORD visit and also reused by the story scripts.
2. Native replacement: hook the module lookup (0x8016A304 entry, check the signature
   first) and answer from a host-side map; frees you from BCD, lets several passwords map
   to one card, per-save prices, etc. The price shown/deducted is read separately at
   0x8016A6CC / 0x8016A7CC, so patch both or keep prices in the table.
3. The recomp's `src/psx_card_shop.c` is a separate native shop; a price mod there does
   not need this table at all.

## 4. Decomp findings (proposed)

- WA 0xFB9800 (sector 0x1F73) -> 0x801A8000 | password/price table, 723 x {u32 price, u32 BCD password}, 0xFF terminated, entry = card id | `gLibrary_aPasswordCardData` (0x801A8008) confirmed = entry 1; whole table starts 0x801A8000
- 0x8016A304 (password module) | builds the 8-digit BCD from `gPassword_abDigits`, walks entries from id 1 until price == -1, returns matching id or 0 | `Password_LookupCard`
- 0x8016A68C.. (module) | purchase state machine: `Campaign_TestStoryFlag(0x400+id)` = "password already used", starchips compare vs price, `Library_UpdateCardUsedFlag(0x400+id)` + `ring_buffer_insert_801d0200(id)` on buy | flag namespace 0x400+id = used passwords (explains F35's 0x801D0698 for card 2)
- 0x80021894 | called with the drop id (0x80021F14) and with the bought card id (module 0x8016A770): adds one copy to the trunk and pushes the recent-acquisitions ring | rename `ring_buffer_insert_801d0200` -> `Library_AcquireCard`

## 5. Open questions

- Which loader step scatters sector 0x44 of the 0x1F2F load to 0x801A8000 (the
  `func_80014E1C` callback or a sector->arena rule) was not traced; the destination is
  fixed by the module code and the F31 purchase.
- Whether entry 0 is read anywhere outside the module (the EXE's `Main_RunPasswordMenu`
  references to 0x801A8000 are all script-related), i.e. whether "disable system" ever
  worked.
- Server side: only the `api/v2/tools` download log.
