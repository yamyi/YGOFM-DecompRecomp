# Raw notes — behavior/patchloader (and the shared `.tad` container)

Session 2026-09-04. Mirror already present; nothing re-fetched from the site (no `api/v2` calls,
no login). The two chunks are the whole story:

    site/js/extend/tools/behavior/patchloader.2f7ab5b1.js    65,128 B
    site/js/extend/tools/behavior/patchcreator.6e7f1436.js   71,261 B

`sed 's/},{/},\n{/g; s/;/;\n/g'` was not enough (259 / 235 lines, still unreadable). Wrote a
brace-aware pretty printer instead (string/comment aware, newline+indent on `{[(`/`}])`/`;`/`,`)
-> 7,863 / 9,095 lines. Kept in the scratch dir, not committed.

## Where everything is (loader, pretty-printed line numbers)

| what | line |
|---|---|
| component `data()` (incl. all the dead disassembler fields) | 6620 |
| `loadDraft` (base64 -> JSON) | 6800 |
| `setInitialValues` (dZone defaults from areas) | 6845 |
| `resetPatchSystem` | 6960 |
| `tryApply` (v dispatch) | 6985 |
| `applyPatch` (v1) | 7000 |
| `applyPatch2` (v2 areas then dZones) | 7060 |
| `fixValue` | 7216 |
| `.call(this, a("b639").Buffer)` — proof `e` is the buffer polyfill | 7256 |
| game FileReader `accepted:".11,.mrg" maxsize 42991616` | 2566 |
| `.tad` FileReader `accepted:".tad" maxsize 5242880` | 3092 |
| `pic` -> `/Assets/img/tools/patch/` | 2654 |
| `sign.user` / `sign.athr` render | 2751 |
| `saveChange()` `tipo = 30` | 5384 |
| generic `FileReader` component (emits `new DataView(arrayBuffer)`) | 7412 |

## Container

`.tad` file bytes = ASCII base64 of `JSON.stringify(patch)`. No magic / header / length /
checksum / target id. Confirmed both directions:

- read: `Buffer.from(new TextDecoder().decode(dv), 'base64').toString()` then `JSON.parse`
  (the `TextEncoder`/`TextDecoder` round trip in the middle is a no-op).
- write (creator + disassembler): `Buffer.from(JSON.stringify(p),'utf8').toString('base64')`.

`e` in both is webpack module `b639` = the `buffer` npm polyfill (`.call(this, a("b639").Buffer)`).

## Applier semantics worth writing down

- v1 key: `parseInt(key.substring(1))` — the leading letter is ignored. creator/loader mint `b`,
  disassembler mints `c`. Value: `setUint32(off, parseInt(value), true)`.
- v2 area: `data.split(" ")`, byte i = `parseInt(tok[i],16) % 256`, `setUint8(address+i, ...)`.
  - length = TOKEN count, not `len/2`.
  - JS `"".split(" ")` is `[""]` -> an empty area writes ONE `00`.
  - `"0102"` is one token -> 258 % 256 = `02`.
  - `NaN % 256` is `NaN`; `setUint8(x, NaN)` writes `00`.
- v2 dZone default (`setInitialValues`): byte0 + 256*byte1 (if type>1 and tok[k+1] exists)
  + 65536*byte2 + 16777216*byte3 (if type>3 **and tok[k+3] exists** — so a 3-token tail drops
  byte 2 as well). Containment tested on the first byte only; loop does not break, last area wins.
  Any `value` stored in the file is overwritten by this seeding.
- order: ALL areas, THEN all dZones. Zones override the area bytes under them.
- bounds: only `try/catch` around each `setUintN`. RangeError -> the message
  "Your <file> is not the size indicated for the patch." Nothing else validated.
  `applyPatch` accumulates offsets, `applyPatch2` accumulates byte *values* (cosmetic bug — the
  string is only tested for emptiness anyway).
- v2 with a missing `areas` or `dZones` key throws (unguarded `.forEach` / `Object.keys`) and
  applies nothing, silently.
- no idempotence guard, no undo in the tool.

## Dead code in the loader

`dataviewWa`, `registers{r0..r31,HI,LO,PC}`, `newOp`, `codeOp`, `nameCodes`, `numCodes`,
`offsetLight`, `index`, `newcode`, `offset` — declared in `data()`, referenced nowhere else.
Copy-paste from `data/disassembler`. Component `name:"PatchLoader"` in *both* chunks.

## Server

Loader endpoints: `pops`, `users/login`, `users/validate`, `comment*`, `userGames/getBlockData`,
`tools`. **No `toolcontrol/validate` heartbeat** (unlike data/disassembler, which self-destructs
without it). Only `POST api/v2/tools {version, tipo:30, data}` matters: the file download happens
in its `.then()`. The hidden `setPrivate()` toggle (an `&nbsp;` span next to `V.230421`) makes
`salvar()` call `download(true)` directly, so the download works logged-out.

Creator adds `toolcontrol/genhash` and `toolcontrol/checkhash`. `sign` = `{serial, user, athr}`
(object, not a string — corrects data-disassembler/README §4's guess). The loader NEVER verifies
it; it only renders `sign.user` and links `/extend/user/profile?id=<athr>`.

## md5

Module `6821f` in chunk-vendors = npm `md5` (crypt): constants 1732584193 / -271733879 /
-1732584194 / 271733878. `md5(JSON.stringify(obj))` over UTF-8 == `hashlib.md5(...).hexdigest()`.
Key order matters; both writers produce `v,title,notes,locked,bytes,dZones,areas[,pic][,sign]`.
Checked the disassembler's `generateJson()` (`{...this.patch, dZones:{}, areas, bytes:[], v:2,
title:"NoName from Disassembler"}` with `this.patch = {v,title,notes,locked,bytes}`) — object
spread keeps existing key positions, so its order is the same. Cross-tool reopen is possible.

JS truthiness trap in `loadDraft`'s normalisation: `{}` and `[]` are TRUE in JS, so
`i.bytes || {}` keeps an empty `{}` or `[]` as-is. `tad.py.js_truthy()` reproduces this;
a naive Python `or` would rewrite `{}` to `{}` but `[]` to `{}` and change the md5.

## Target files (measured, not assumed)

    SLUS_014.11              1,902,592   0x1D0800   loads
    /DATA/WA_MRG.MRG   LBA 10102  37,748,736 0x2400000  loads
    /DATA/SU.MRG       LBA   954   2,537,472 0x26B800   loads
    /DATA/MODEL.MRG    LBA 28534 351,019,008 0x14EC2000 rejected (> maxsize 42,991,616)

Disc geometry re-read from `~/YuGiOhForbiddenMemoriesRecomp/disc/...bin` with
`extract_overlay.walk_iso` (needs the image as *bytes*: `mmap` it; `read_range(disc, lba, nbytes)`
takes bytes, not sectors).

WA offset 0xE9B000 -> in-file sector 0x1D36 (7478) -> disc LBA 10102+7478 = **17580**. The 3
sectors there decode as opponent 1's four `u16 weight[722]` pools, sums 2048/2048/2048/2048,
maxima 100/90/98/92 — matches process-moreopponets §2. That README prints 17592; arithmetic slip.

## PsyQ scratch regions — verified in `~/ygofm-decomp/SLUS_014.11`

    0x2540  -> 0x80011D40  b'ync\x00CD_ready\x00\x00\x00\x00%s...\n\x00\x00%s: no param\n\x00\x00\x00CD_cw\x00\x00\x00$Id: bios.c,v 1.86 1997/03/28 07:42:42 makoto Ex'
    0x2D80  -> 0x80012580  b'd. : file already open.\n\x00\x00\x00\x00Access Denied. : file not open.\n\x00\x00\x00\x00Access Denied. : invalid data si'
    0x85E00 -> 0x80095600  b",stack is empty!\n\x00This function is not implemented.\n\x00\x00\x00\x00\x00\x00\x00"

(libcd `bios.c`; libcd/libmcrd file-access messages; libgte matrix-stack errors.) All three are
unreferenced string data, which is why TEA uses them. `process/moreopponets` claims 0x80011D40;
`process/specialbanlist` claims 0x80012580, 0x80095600 and 0x80012978. Nothing in the `.tad`
format detects two patches claiming the same region.

The container itself has NO scratch-space concept — it is a plain offset/bytes poker. The
convention lives in the *payloads* the site ships through it.

## Script tests (all on copies in the scratch dir; the decomp SLUS and the disc were read-only)

stock `SLUS_014.11` md5 `dab1b3c9a6b8a56558b5ca8f807339c3`.

1. Rebuilt the 8-site More Opponents patch from `process-moreopponets/patch/patch_*.bin` via
   `tad.py create` -> v2, 8 areas, 172 bytes.
2. `tad.py verify` printed the stock bytes at all 8 offsets; every one matches
   `process-moreopponets/README.md` §1 exactly (`ff 07 42 30 01 00 45 24`,
   `21 98 00 00 10 00 b4 27`, `0a 80 01 3c 61 b3 25 a0`, `96`/`02`/`94`/`02`, and the libcd strings).
3. `tad.py apply` -> md5 `a43b047f4296232c1928625969ce3c59`, 153 bytes changed;
   `cmp` against `more_opponents.py apply` output: **identical**.
4. `tad.py apply --undo undo.tad`, then apply `undo.tad` to the patched file -> `cmp` against the
   stock EXE: **identical** (restore is byte-for-byte).
5. `tad.py diff stock patched d.tad` -> 9 areas / 164 bytes (splits 0x2540 into 0x2540+12 and
   0x2550+124 because the middle 4 bytes were already zero); `apply d.tad` reproduces the patched
   EXE exactly.
6. v1 path: `create --v1 --area 0x12048:6a47000800000000` -> `{"b73800":134236010,"b73804":0}`;
   `134236010 == 0x0800476A`; apply writes `6a 47 00 08 00 00 00 00` at 0x12048. (7 of 8 bytes
   "changed" because byte 0x1204D was already 0.)
7. Out-of-range: a v2 area at 0xE9B000 (a WA offset) applied to the SLUS changes 0 bytes and
   reports 4 out-of-file writes — the site's "not the size indicated for the patch" case.
8. Quirks, on a 32-byte zero target:
   `"AA BB"` -> `aa bb`; `""` -> one `00`; `"0102 ZZ  41"` -> `02 00 00 41`.
   dZones `u16@16` default 4660 (0x1234), `u32@20` default 305419896 (0x12345678), `u8@30` 7.
   `--set HP=0x0102 --set GOLD=999999 --set LVL=40` -> `02 01` at 16, `3f 42 0f 00` at 20, `28` at 30.
9. Key order: `dumps_js(p) == dumps_js(normalised(p))` for a `tad.py create` output — the writer's
   order matches what the site hashes.

Jump-target check on the injected stubs: `0x0800476A -> 0x80011DA8`, `0x08004760 -> 0x80011D80`,
`0x08004754 -> 0x80011D50`. All three land on the stub entry points documented in
process-moreopponets, which is an independent confirmation of `RAM = 0x80010000 + off - 0x800`.

## Loose ends

- No genuine site-signed `.tad` was obtainable (the patch listing needs a session). Everything is
  derived from the two writers plus round-trips.
- `/Assets/img/tools/patch/` has no public index, so the `pic` value set is unknown.
- `locked` written by all three tools, read by none.
- The scratch pretty-printer output and the test artefacts live under the session scratch dir and
  are not part of this folder.
