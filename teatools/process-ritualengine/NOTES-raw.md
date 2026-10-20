# RITUAL ENGINE — working notes (2026-09-04)

Source: https://www.basededatostea.xyz/extend/tools/process/ritualengine (login-gated route; the
mirror in `site/` was taken with a session cookie). Tool chunk
`site/js/extend/tools/process/ritualengine.c236c68f.js`, component `RitualConstructor`; the patch
blobs are NOT in that chunk but in **chunk-common module `8481`**
(`site/js/chunk-common.9cc62f95.js`), which exports:

    a("8481")["a"] = 12154880 = 0xB97800          // addresData, WA offset of the ritual table
    a("8481")["b"] = { jumps: [...], buffer: [...], script: [...] }

Verbatim from the chunk:

    jumps:  {address:118772, data:[210,230,5,8,0,0,0,0]}
            {address:118960, data:[250,230,5,8,0,0,0,0]}
            {address:118992, data:[210,230,5,8,10,0,140,37]}
    buffer: {address:12155136, size:112}
    script: {address:12155248, data:[...560 bytes...]}

`injectCodeOnSlus()` writes `jumps` into the SLUS DataView at those FILE offsets;
`injectCodeOnWa()` writes `script` and zeroes `buffer` through `multiSetByte`, which repeats every
write at `+481280*k` for k = 0..6. `writeWa()` writes 24 records (10 bytes each) + a zero record at
+240 through `multiSetWord`, same 7 copies.

File offset -> RAM: 118772 = 0x1CFF4 -> 0x8002C7F4, 118960 = 0x1D0B0 -> 0x8002C8B0,
118992 = 0x1D0D0 -> 0x8002C8D0. WA 12155248 = 0xB97970 = table + 0x170 -> RAM 0x80179B48;
12155136 = 0xB97900 = table + 0x100 -> 0x80179AD8.

Decoding the jump words: `[210,230,5,8]` LE = 0x0805E6D2, j target 0x05E6D2 << 2 = 0x179B48 ->
`j 0x80179B48`. `[250,230,5,8]` = 0x0805E6FA -> `j 0x80179BE8`. `[10,0,140,37]` = 0x258C000A =
`addiu t4, t4, 10`.

Stock verification (against `~/ygofm-decomp/SLUS_014.11` and WA_MRG.MRG extracted from
`~/YuGiOhForbiddenMemoriesRecomp/disc/*.bin`, md5 971c16ea21635b45351e5ae959c53503):

    0x1CFF4  00 00 82 95 00 00 00 00   lhu v0,0(t4) ; nop
    0x1D0B0  00 00 22 95 00 00 00 00   lhu v0,0(t1) ; nop
    0x1D0D0  4c b2 00 08 21 10 00 00   j .L8002C930 ; move v0,zero
    WA +0x170, all 7 copies: 560 bytes of 0xFF
    WA +0x100, all 7 copies: 112 bytes of 0xFF

## The victim function

`table801a7ad8_recipe_lookup` 0x8002C7E8 — matched C already in the decomp
(`src/table801a7ad8_recipe_lookup.c`), asm in `asm/matchings/table801a7ad8_recipe_lookup/`.
Everything the patch does hangs off three facts in that asm:

1. 0x8002C7F4 is the top of the key-scan loop and the load is a full u16 compare — masking it with
   0x3FF is what makes the `type<<10` bits usable at all.
2. 0x8002C87C does `addiu t4, t4, 0x2` once, before the material loop. Every later reference to the
   record (`lhu v0, 0x6(t4)` for the result) is relative to record+2. This is what makes the HOOK 3
   `addiu t4,t4,10` land on next-record+2 instead of next-record — see README §5A.
3. `.L8002C8D0` is reachable from two places in stock (end of table, and no candidate matched); after
   HOOK 1 only the second path survives, so re-purposing it as "try the next record" is safe apart
   from the +2.

## Tables the injected code reads

`lui 0x801d / addiu 0x4240` + `sll id,2` -> `0x801D4240 + 4*id`. `gDuel_adwCardStats` in
symbol_addrs is 0x801D4244, so this is `stats[id-1]` with a 1-based id. Bit layout confirmed by
dumping the first cards out of the stock EXE:

    id 1 Blue-Eyes  0x0205F52C  atk 3000 def 2500 gs2 1 gs1 8 type 0 (Dragon)
    id 2 Mystical Elf 0x06099050 atk 800 def 2000 gs2 2 gs1 8 type 1
    -> bits 0-8 ATK/10, 9-17 DEF/10, 18-21 star2, 22-25 star1, 26-31 type

`lui 0x801d / addiu 0x5332` + `addu id` -> `0x801D5332 + id`, `lbu`, `>> 4`. The decomp already
carries this as `gDuel_abCardLevelAttr` (asm/data/overlay_arena.data.s, byte 0 is 0x00 and byte 1 is
0x08 for Blue-Eyes = level 8 / attribute 0 = Light) and `init_container_entry_objs` reads exactly the
same nibble pair (`f3B = >>4`, `f3A = &0xF`). Attribute order comes from the site store:
`atributes: ["Light","Dark","Earth","Water","Fire","Wind","Magic","Trap"]`; checked against ids 1-6
(Light, Light, Earth, Wind, Dark, Dark) — matches.

## Site-side details worth keeping

- `Ritual.fromBytes` masks every field with 0x3FF, so the UI cannot express a requirement > 1023 even
  though types 1/2 only use 6 and 4 bits.
- The spell picker is cards with `type == 22`, result/material pickers are `type < 20` — pure UI
  filters, the engine checks neither.
- The "Ritual types that don't require specific cards..." note in the UI is literally the ATK gate:
  types 1, 2 and 3 all require material ATK < result ATK; type 0 does not.
- The download panel only offers the SLUS *and* the WA; the SLUS is described as "you'll usually only
  need to download it the first time", i.e. the EXE patch is idempotent and the WA carries the data.
- Analytics: POST api/v2/tools, tipo 44; comments box guia 54. No other network use.

## Round-trip test

    scripts/ritual_engine.py apply-slus / restore-slus  -> byte-identical to the stock EXE
    scripts/ritual_engine.py apply-wa   / restore-wa    -> byte-identical to the stock WA_MRG.MRG
    scripts/ritual_engine.py apply-wa reproduces the exact 7-copy byte pattern the site writes
    (250 record bytes, 112 zero bytes at +0x100, 560 script bytes at +0x170, 0xFF elsewhere).
