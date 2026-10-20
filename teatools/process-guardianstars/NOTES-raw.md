# GUARDIAN STARS — working notes (2026-09-04)

Source: https://www.basededatostea.xyz/extend/tools/process/guardianstars (login-gated; mirror in
`site/` taken with a session cookie). Tool chunk
`site/js/extend/tools/process/guardianstars.cb1f89de.js`, component `GuardianStar`,
banner "V.231003 [BETA] [Early access for donors]".

## The four blobs in the chunk

    lt (validationScript) [{address:119680, data:[255,255,132,36,255,255,165,36]},
                           {address:119690, data:[2,60]},
                           {address:119694, data:[66,36, ...78 more bytes...]}]
    dt (position)         [{address:119688, data:[1,128]}, {address:119692, data:[128,26]}]
    ut (mainScript)       [{address:119680, data:[...96 bytes...]}]
    pt (bonusData)        [{address:8832,   data:[2,0,4,0,8,0,16,0,32,0,1,0,128,0,0,1,0,2,64,0,
                                                  0,0,0,0,0,0,0,0,0,0,0,0]}]

`ut` is the whole 96-byte body; `lt` is the same bytes MINUS the two address immediates (bytes 8-9
and 12-13), which is how `checkSlus()` recognises an already-patched file no matter where the table
was put; `dt` names those two immediates so `applyMinPatch()` can rewrite them.

Addresses (file -> RAM = 0x80010000 + off - 0x800):

    119680 = 0x1D380 -> 0x8002CB80   (Duel_CalcGuardianStarMatchup)
    119688 = 0x1D388 -> 0x8002CB88   lui  v0, imm   <- %hi
    119692 = 0x1D38C -> 0x8002CB8C   addiu v0,v0,imm <- %lo
      8832 = 0x2280  -> 0x80011A80   the 32-byte table

Stock bytes at 0x2280 (verified in `~/ygofm-decomp/SLUS_014.11`):

    64 79 20 48 20 2d 3e 20 4c 29 00 00 77 61 69 74
    20 28 64 6d 61 66 20 63 6c 65 61 72 2f 57 29 00
    = "dy H -> L)" \0 \0 "wait (dmaf clear/W)" \0

PsyQ debug format strings; the whole neighbourhood (0x80010000..0x80012xxx) is libgpu/libetc/libspu
RCS ids and printf templates that the retail build never prints, which is why several TEA tools park
code and data in it (see also process-cardcolor, which uses 0x80012150 and 0x800122C0).

## Stock 0x8002CB80

`symbol_addrs.txt` already calls it `Duel_CalcGuardianStarMatchup`, but `src/calc_wrap_scroll_delta.c`
comments it as a menu-scroll helper ("wraps at -7/+7 with widths 6 or 4"). Reading it as the star
wheel makes every constant obvious:

    -7 splits the two rings (stars 1..6 and 7..10)
    v1 = 6 or 4 is the ring size
    +1 / -2 walk to the next / previous star in the ring
    +500 / -500 is the flat ATK/DEF bonus

That the tool's default `bonusData` reproduces this ring order bit for bit is the proof:

    idx (star-1) : mask -> bit (target-1)
    0 -> 0x0002 -> 1     3 -> 0x0010 -> 4     6 -> 0x0080 -> 7     9 -> 0x0040 -> 6
    1 -> 0x0004 -> 2     4 -> 0x0020 -> 5     7 -> 0x0100 -> 8
    2 -> 0x0008 -> 3     5 -> 0x0001 -> 0     8 -> 0x0200 -> 9

i.e. 1>2>3>4>5>6>1 and 7>8>9>10>7, the well-known FM wheel with
1 Mars 2 Jupiter 3 Saturn 4 Uranus 5 Pluto 6 Neptune 7 Mercury 8 Sun 9 Moon 10 Venus.

Sanity check on real data: card 1 (Blue-Eyes White Dragon) stats word 0x0205F52C -> star1 (bits 22-25)
= 8 = Sun, star2 (bits 18-21) = 1 = Mars, ATK 3000, DEF 2500, type 0 (Dragon). Matches the game.

Callers found by grepping the `jal` encoding `0C00B2E0`:
`Duel_CalcGuardianStarBonus` 0x8001EE44 (call at 0x8001EF04), `AiScript_FindKiller` 0x80071B64
(0x80071C30), `AiScript_FindBestAttack` 0x8007308C (0x80073170).

## The patched body, annotated

    addiu a0,a0,-1 / addiu a1,a1,-1     both star ids -> 0-based
    lui/addiu v0 = 0x80011A80           the relocatable pointer (dt)
    v1 = tbl[a1]; v1 = (v1 >> a0) & 1   defender beats attacker?  -> -500
    v1 = tbl[a0]; v1 = (v1 >> a1) & 1   attacker beats defender?  -> +500
    else 0

Defender first, so a symmetric pair resolves in the defender's favour; the UI's `createBonus()` clears
the reverse edge on every click, so the site never produces that state.

`createDataSet()` reads 15 u16 (`0..14`); the 16th entry of the blob is padding. Each row is stored
in the Vue model as a reversed array of 16 '0'/'1' characters, `parseInt(reverse.join(''), 2)`.

## The custom-address bug

    var t = parseInt(customAddress) - 8832 + 72320 & 16777215,   // 72320 = 0x11A80, so t = RAM & 0xFFFFFF
        a = 65535 & t,
        s = (t >> 16 & 255) + (a > 32767 ? 1 : 0) & 255;
    setUint16(0x1D388, parseInt("80" + hex2(s)), true);          // <-- decimal parseInt!
    setUint16(0x1D38C, a, true);

`parseInt("8001")` is 8001, not 0x8001. So the `lui` immediate is wrong for every custom address.
`extractData()` reads the immediate back as `(getUint8(0x1D388) << 16) + getInt16(0x1D38C) - 63488`
(63488 = 0xF800, the RAM->file bias), which works fine for the default table and breaks after a custom
one. `scripts/guardian_stars.py --data-addr` implements what was intended.

## Round-trip test

    guardian_stars.py apply   -> the 96 code bytes and 32 data bytes are byte-identical to the
                                 site's `ut` / `pt` arrays
    guardian_stars.py restore -> byte-identical to the stock SLUS_014.11
