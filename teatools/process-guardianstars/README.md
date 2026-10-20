# GUARDIAN STARS tool

Route: `extend/tools/process/guardianstars` (login-gated). UI "V.231003 [BETA] [Early access for
donors]", component `GuardianStar`. Inputs: **SLUS_014.11** (`.11`, 1,782,579..8,388,608 bytes — the
only file that is edited and downloaded) and optionally **WA_MRG.MRG** (`.mrg`, 31,457,280..44,040,192
bytes, read-only: it supplies the 15 guardian-star icons drawn in the matrix: 16x16 4bpp sprites cut out of
the sheet at WA `0xB50000` (128 bytes per row), CLUT at WA `0xB60500`, +768 for icons 11..15 and
+32 more for 15). Analytics POST `api/v2/tools` `tipo` 35 (comments `guia` 45).
Script: `scripts/guardian_stars.py` (inspect / apply / set / clear / restore on a SLUS copy).
Patch blobs + disassembly: `patch/`. Raw notes: `NOTES-raw.md`.

Purpose: replace the hard-wired guardian-star wheel with a 15x15 "who beats whom" matrix, so a mod can
re-wire the existing relations and use up to five extra stars (the card stats field is 4 bits wide, so
1..15 all fit).

Status: the replacement routine and its data table are fully decoded and verified against the stock
EXE; `guardian_stars.py` round-trips byte-for-byte and its default table reproduces stock behaviour
exactly. One shipped defect (the "custom address" option, §5). Not yet built as a recomp mod.

## 1. What it writes

| file | offset | RAM | size | contents |
|---|---|---|---|---|
| SLUS_014.11 | 0x1D380 | 0x8002CB80 | 96 | new `Duel_CalcGuardianStarMatchup` body (24 instructions) |
| SLUS_014.11 | 0x2280 | 0x80011A80 | 32 | `bonusData`: 16 x u16 LE "beats" bitmask, index = star-1 |

Nothing else. The tool never touches WA_MRG.MRG.

**Where the new data goes.** 0x80011A80 is **PsyQ library debug strings** — the 32 stock bytes are

    64 79 20 48 20 2d 3e 20 4c 29 00 00 77 61 69 74 20 28 64 6d 61 66 20 63 6c 65 61 72 2f 57 29 00
    "dy H -> L)\0\0wait (dmaf clear/W)\0"

i.e. the tail of `"wait (wrdy H -> L)"` plus all of `"wait (dmaf clear/W)"`, format strings that the
retail build never prints. The tool offers a "use a custom address" box to move the table elsewhere
(and rewrites the `lui`/`addiu` pair that reaches it) — but see §5.

The 96 bytes of code go **on top of the function itself**: stock `Duel_CalcGuardianStarMatchup` is 116
bytes (0x8002CB80..0x8002CBF3) and the replacement only needs 96, so the last five stock instructions
(0x8002CBE0..0x8002CBF3) are left in place as unreachable tail.

## 2. The stock function it replaces

`Duel_CalcGuardianStarMatchup` = **0x8002CB80** (already named in
`~/ygofm-decomp/config/symbol_addrs.txt`; the C in `src/calc_wrap_scroll_delta.c` describes it as a
list-scroll helper, which is wrong — this tool proves it is the guardian-star wheel). Stock bytes
verified against `~/ygofm-decomp/SLUS_014.11`; full listing in
`patch/stockFunc_8002CB80.stock.dis`.

    int Duel_CalcGuardianStarMatchup(int attacker, int defender)   // star ids, 1-based
    {
        a0 = attacker - 7;
        if (a0 >= 0) {                       // attacker in the 4-ring (7..10)
            a1 = defender - 7;
            if (a1 < 0) return 0;            // other ring -> no interaction
            v1 = 4;                          // ring size
        } else {
            v1 = 6;                          // attacker in the 6-ring (1..6)
            a1 = defender - 1;
            a0 = a0 + 6;                     // = attacker - 1
            if (a1 >= 6) return 0;
        }
        if (++a0 >= v1) a0 = 0;              // the star attacker beats
        if (a0 == a1) return  500;
        a0 -= 2;  if (a0 < 0) a0 += v1;      // the star that beats attacker
        if (a0 == a1) return -500;
        return 0;
    }

So the stock wheel is two disjoint rings, each star beating the next one round:

    ring A (6): 1 Mars -> 2 Jupiter -> 3 Saturn -> 4 Uranus -> 5 Pluto -> 6 Neptune -> 1
    ring B (4): 7 Mercury -> 8 Sun -> 9 Moon -> 10 Venus -> 7

Callers (all pass a pair of star ids and use the +/-500 as a raw ATK/DEF delta):

- `Duel_CalcGuardianStarBonus` 0x8001EE44 (`jal` at 0x8001EF04) — the battle-math path feeding
  `Duel_CalcBattleAttack`/`Duel_CalcBattleDefense` (findings F76);
- `AiScript_FindKiller` 0x80071B64 (`jal` at 0x80071C30);
- `AiScript_FindBestAttack` 0x8007308C (`jal` at 0x80073170).

## 3. The replacement (`patch/mainScript_8002CB80.dis`)

    8002CB80  addiu a0, a0, -1          ; attacker-1  (0-based star index)
    8002CB84  addiu a1, a1, -1          ; defender-1
    8002CB88  lui   v0, 0x8001          ; <- position[0]: the %hi immediate
    8002CB8C  addiu v0, v0, 0x1A80      ; <- position[1]: the %lo immediate  -> 0x80011A80
    8002CB90  sll   v1, a1, 1
    8002CB94  addu  v1, v0, v1
    8002CB98  lhu   v1, 0(v1)           ; table[defender-1]
    8002CBA0  srlv  v1, v1, a0
    8002CBA4  andi  v1, v1, 1           ; does the DEFENDER beat the attacker?
    8002CBA8  bnez  v1, .ret
    8002CBAC   li   v1, -500
    8002CBB0  sll   v1, a0, 1
    8002CBB4  addu  v1, v0, v1
    8002CBB8  lhu   v1, 0(v1)           ; table[attacker-1]
    8002CBC0  srlv  v1, v1, a1
    8002CBC4  andi  v1, v1, 1           ; does the ATTACKER beat the defender?
    8002CBC8  bnez  v1, .ret
    8002CBCC   li   v1, 500
    8002CBD0  li    v1, 0
    8002CBD4 .ret: move v0, v1
    8002CBD8  jr    ra

`table[x]` is a 16-bit mask: bit `y` set means "star x+1 beats star y+1". Note the **defender's** mask
is tested first, so if a pair is marked as beating each other in both directions the defender wins.
The site's UI (`createBonus`) enforces exclusivity anyway: setting A>B clears B>A.

The default `bonusData` the tool installs is exactly the stock wheel:

    idx 0 Mars    0x0002 -> Jupiter      idx 6 Mercury 0x0080 -> Sun
    idx 1 Jupiter 0x0004 -> Saturn       idx 7 Sun     0x0100 -> Moon
    idx 2 Saturn  0x0008 -> Uranus       idx 8 Moon    0x0200 -> Venus
    idx 3 Uranus  0x0010 -> Pluto        idx 9 Venus   0x0040 -> Mercury
    idx 4 Pluto   0x0020 -> Neptune      idx 10..15    0x0000 (the 5 spare stars + a pad entry)
    idx 5 Neptune 0x0001 -> Mars

Cross-check: Blue-Eyes White Dragon (card 1) has `gDuel_adwCardStats[0] = 0x0205F52C`, bits 22-25 = 8
and bits 18-21 = 1 → Sun / Mars, which is what the card viewer prints (bits 22-25 first).

## 4. Where the star ids come from

Per card, `gDuel_adwCardStats` (0x801D4244, SLUS file 0x1C4A44), one u32 per card indexed by id-1:

    bits  0-8   ATK / 10
    bits  9-17  DEF / 10
    bits 18-21  guardian star 2   (the SECOND star the viewer prints)
    bits 22-25  guardian star 1   (the FIRST star the viewer prints)
    bits 26-31  card type (0..19 monster families, 20 Magic, 21 Trap, 22 Ritual, 23 Equip)

Both star fields are 4 bits, so ids 1..15 are storable; that is exactly the "5 additional guardian
stars" the tool advertises. Changing a card's stars is not this tool's job — that is the
[cardsdata](../cardsdata/README.md) editor — this tool only changes the *relation* between stars.

Consequences of the rewrite:

- `srlv` uses only the low 5 bits of the shift, and the table is indexed `2*(id-1)` with no bound
  check, so a star id of 0 reads `table[-1]` (2 bytes before the table) and an id > 16 walks off the
  end. Stock data never produces either, but a mod that writes a bad star nibble will read garbage.
- Star ids 11..15 have no icon in the game's own UI and no name string; the tool draws them from
  WA sprite rows at y=128, which are blank in stock.
- Ring membership no longer exists: any star can be made to beat any other, including
  cross-"ring" pairs the stock code could never produce.

## 5. Defect in the shipped tool: "use a custom address"

`applyMinPatch()` computes the new %hi/%lo correctly but then writes the `lui` immediate as

    setUint16(0x1D388, parseInt("80" + s.toString(16).padStart(2,'0')), true)

`parseInt` with no radix parses **decimal**, so for the default 0x8001 it would write 8001 (=0x1F41)
instead of 32769. Any custom address therefore installs `lui v0, 0x1F41` and the table pointer is
garbage. The bug is masked inside a single session because `extractData()` short-circuits to
`config.customAddress`, but re-opening the saved file makes `extractData()` read the broken `lui` and
either throw or point at the wrong bytes. `scripts/guardian_stars.py --data-addr` does the same
relocation correctly (`set_hilo()`), which is a good way to see what the tool intended.

## 6. Recomp options

1. **Data-only mod, no code patch.** The cleanest port: leave `Duel_CalcGuardianStarMatchup` alone and
   `PSX_MOD_CONSTRUCTOR`-hook it natively with a 16-entry mask table owned by the mod. Base-EXE code,
   so a one-shot `psx_mod_write_code_word` trampoline or a direct function replacement both work; no
   frame hook is needed (nothing re-streams 0x8002CB80 from disc).
2. **Byte-for-byte port.** 24 `psx_mod_write_code_word` at 0x8002CB80 plus 8 word writes at
   0x80011A80. Only do this if you want the site's exact file layout; prefer (1) otherwise, and note
   that writing the table over live PsyQ strings is only safe because retail never prints them.
3. **Beyond the site.** The 16-bit mask makes the relation a plain directed graph, so a recomp mod can
   go further for free: per-star bonus *amounts* (replace the fixed +/-500 with a second table), star
   ids beyond 15 (widen the card stats field, which the recomp can do because it owns the struct), or
   a "both directions set = double KO" rule.
4. **Careful with mod stacking.** Anything else that wants 0x80011A80 (a generic "spare bytes in the
   PsyQ string block" pool) will collide; the site's own custom-address escape hatch is broken, so in
   a recomp keep the table in mod-owned memory instead of EXE space.

## 7. Decomp findings (proposed)

- `0x8002CB80 Duel_CalcGuardianStarMatchup` | **not** a scroll-delta helper: it is the guardian-star wheel. Two rings (ids 1-6 and 7-10), each star beating the next; returns +500 when the attacker's star beats the defender's, -500 for the reverse, 0 otherwise. Proven by the site replacing it with an explicit 16x16 "beats" bitmask whose default entries reproduce the stock ring order exactly | keep the name, rewrite `src/calc_wrap_scroll_delta.c`'s comment
- guardian-star ids | 1 Mars, 2 Jupiter, 3 Saturn, 4 Uranus, 5 Pluto, 6 Neptune, 7 Mercury, 8 Sun, 9 Moon, 10 Venus; the +/-500 is a flat ATK/DEF delta applied by `Duel_CalcGuardianStarBonus` (0x8001EE44) | evidence for the star enum
- `0x801D4244 gDuel_adwCardStats` | u32 per card (id-1): bits 0-8 ATK/10, 9-17 DEF/10, **18-21 guardian star 2**, **22-25 guardian star 1**, 26-31 card type. Star fields are 4 bits so ids up to 15 are representable | `gCard_adwStats`, document the bitfield
- `0x80011A80` (32 bytes) | dead PsyQ debug strings `"...dy H -> L)"` / `"wait (dmaf clear/W)"`; the whole libspu/libetc string block around it is a known free-space pool used by third-party mods | mark as reclaimable in the free-space notes

## 8. Open questions

- Which VRAM CLUT the 11th..15th star icons would use in the real game; the tool only draws them in
  its own HTML canvas from WA sprite rows that are blank in stock.
- Whether the AI paths (`AiScript_FindKiller`, `AiScript_FindBestAttack`) assume the ring structure
  anywhere else — they only consume the return value here, but they were not read end to end.
- Nothing is done server-side beyond the analytics POST; the route is login-gated so the page itself
  needs a session cookie to mirror.
