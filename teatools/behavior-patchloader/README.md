# PATCH LOADER tool

Route: `extend/tools/behavior/patchloader` (public; page version string `V.230421`, analytics
`tipo: 30`, comment board `guia: 40`).
Inputs: **two** files — the game file to patch (`accepted:".11,.mrg"`, `minsize 0`,
`maxsize 42,991,616`) and a patch (`accepted:".tad"`, `minsize 0`, `maxsize 5,242,880`).
Purpose: apply a site-made `.tad` byte patch to one of the game's internal files and download the
result. It is the *consumer* half of TEA-Online's own patch container; the producer is
[`behavior-patchcreator`](../behavior-patchcreator/README.md) (and, for v1, `data/disassembler`).
Status: format fully decoded, both versions implemented, round-trip verified byte-for-byte against
the real SLUS_014.11 and against a sibling tool's own patched EXE. Reader **and** writer are done.
Script: `scripts/tad.py` (dump / json / hash / verify / apply / create / diff; identical copy in
`behavior-patchcreator/scripts/tad.py`). Raw session notes: `NOTES-raw.md`.

The tool is not a fixed patch list — it is a generic byte poker. So this README documents the
container exactly, the applier's bug-for-bug semantics, and what a `.tad` can and cannot reach.

## 1. The `.tad` container

| | |
|---|---|
| magic | **none** |
| header | **none** |
| length field | **none** |
| checksum / CRC | **none** |
| target-file id | **none** (see §4) |
| version field | `"v"` *inside* the JSON, not in the container |
| whole file | `base64( JSON.stringify(patch) )`, ASCII, no padding stripped, no newline |

Write path (`patchcreator`/`disassembler` `createPatch`):

    Buffer.from(JSON.stringify(patch), 'utf8').toString('base64')  ->  Blob  ->  saveAs('draft.tad')

Read path (`patchloader` `loadDraft`, `site/js/extend/tools/behavior/patchloader.2f7ab5b1.js`):

    txt = new TextDecoder().decode(dataView)          // the raw file bytes as UTF-8
    json = Buffer.from(txt, 'base64').toString()      // 'buffer' npm polyfill, webpack module b639
    patchSystem = { ...resetPatchSystem(), ...JSON.parse(json) }

`JSON.parse` failures are caught and only `console.log`ged, leaving the reset patch
(`{v:1,title:"",notes:[],locked:false,bytes:{}}`) — i.e. a corrupt `.tad` silently applies nothing.
There is no compression, no encryption, and the base64 is not URL-safe.

## 2. The JSON object

Canonical key order, as emitted by both writers (it matters — see the md5 in §5 of the
patchcreator README):

| key | type | v1 | v2 | meaning |
|---|---|---|---|---|
| `v` | int | 1 | 2 | dispatched by `tryApply()`: `1 -> applyPatch()`, `2 -> applyPatch2()`, anything else does nothing |
| `title` | string | yes | yes | shown in the loader header |
| `notes` | array | yes | yes | `{id:"YYYY-MM-DD HH:mm:ss <n>", text, date:"YYYY-MM-DD HH:mm:ss"}` (the disassembler writes `id` as an int) |
| `locked` | bool | yes | yes | **written by every tool, read by none.** Vestigial in patchloader, patchcreator *and* data/disassembler |
| `bytes` | object/array | **payload** | empty `{}` (creator) or `[]` (disassembler) | v1 record set |
| `dZones` | object | — | **required** | user-editable overlay fields |
| `areas` | array | — | **payload** | byte runs |
| `pic` | string | opt | opt | filename under `/Assets/img/tools/patch/`; the loader paints it behind the header (`linear-gradient(...) , url(/Assets/img/tools/patch/<pic>)`) |
| `sign` | object | opt | opt | `{serial, user, athr}`, server-issued. See §5 |

`v2` requires `areas` **and** `dZones` to be present: `applyPatch2()` calls
`this.patchSystem.areas.forEach` and `Object.keys(this.patchSystem.dZones)` with no guard, so a v2
patch missing either key throws and applies nothing (silently — no alert, only a console error).

### v1 records — `bytes`

```json
{"v":1,"title":"","notes":[],"locked":false,
 "bytes":{"b73800":134236010, "b73804":0}}
```

| field | encoding |
|---|---|
| key | one arbitrary prefix character + the **decimal** file offset. Read with `parseInt(key.substring(1))`, so the letter is ignored. `patchcreator`/`patchloader` mint `"b<off>"`; `data/disassembler` mints `"c<off>"`; both load in either tool |
| value | the 32-bit word as a JSON number (or numeric string), applied with `DataView.setUint32(off, parseInt(value), /*littleEndian=*/ true)` |

`134236010` = `0x0800476A` = `j 0x80011DA8` — values are stored little-endian-as-a-word, i.e. the
number is the word you would see in a disassembler, and the four file bytes come out reversed.

### v2 records — `areas`

```json
{"v":2,"title":"More Opponents","notes":[],"locked":false,"bytes":{},
 "dZones":{},
 "areas":[{"address":73800,"data":"6A 47 00 08 00 00 00 00","isHex":false}]}
```

| field | encoding |
|---|---|
| `address` | **decimal** file offset, always a JSON number in the file |
| `data` | hex bytes as one **space-separated** string. `applyPatch2()` does `data.split(" ")` and writes token *i* with `setUint8(address + i, parseInt(token,16) % 256)` |
| `isHex` | editor-only. It means "the Address input box is typed in hex"; `fixAddress()` converts with `parseInt(v,16)` and stores a decimal number, so `isHex` **never** changes how a patch is applied |

The byte count of an area is the **token count**, not `len(data)/2`. Consequences, all reproduced
by `scripts/tad.py`:

| `data` | tokens | bytes written |
|---|---|---|
| `"6A 47 00 08"` | 4 | `6A 47 00 08` |
| `""` | `[""]` (JS `''.split(' ')` is not empty!) | **one** `00` byte |
| `"0102"` | 1 | `02` — `parseInt("0102",16)` is 258, `258 % 256` = 2 |
| `"AA  BB"` (double space) | 3 | `AA 00 BB` — the empty token is `NaN`, `setUint8(NaN)` writes 0 |
| `"ZZ"` | 1 | `00` |

The creator's `fixBytes()` normalises anything typed into upper-case `"HH HH .."`, so real
site-made patches never hit the odd rows — but the loader will happily eat a hand-made file that does.

### v2 dynamic zones — `dZones`

```json
"dZones":{"b73800":{"address":73800,"type":2,"tag":"Bank offset"}}
```

| field | encoding |
|---|---|
| key | `"b" + decimal address` (the address is repeated in the value; the key is only used as a map key) |
| `address` | decimal file offset |
| `type` | byte width: `1`, `2` or `4` |
| `tag` | the label the loader prints next to the numeric input |
| `value` | **not stored by the creator**; the loader always re-derives it (below), so any `value` present in a file is ignored |

`setInitialValues()` seeds each zone's default from whatever the **areas** contain at that address:

    val  = parseInt(tok[k], 16)
    type>1 && tok[k+1] exists: val += 256      * parseInt(tok[k+1],16)
    type>3 && tok[k+3] exists: val += 65536    * parseInt(tok[k+2],16)
                               val += 16777216 * parseInt(tok[k+3],16)

Three quirks, all faithful in `tad.py`:

- containment is tested on the **first** byte only (`area.address <= a <= area.address+len-1`), so a
  zone can straddle the end of an area and read tokens that do not exist;
- the area loop does not `break`, so if several areas cover the address the **last one wins**;
- for `type:4` the byte-2 term is guarded on `tok[k+3]`, so a zone with only three tokens available
  silently drops byte 2 as well as byte 3.

`applyPatch2()` writes **all areas first, then all zones**, so a zone always overrides the area
bytes underneath it: `setUint8` / `setUint16(LE)` / `setUint32(LE)` by `type`, value taken
`% 256**type` (`fixValue()` also does `Math.abs(parseInt(v)||0)` as you type).

## 3. What the applier actually does

`site/js/extend/tools/behavior/patchloader.2f7ab5b1.js`, component `PatchLoader`:

| method | effect |
|---|---|
| game-file `readed` | `dataviewSlus = new DataView(arrayBuffer)`, and **resets** the loaded patch, the log and the patch filename |
| `LOAD PATCH` -> `tryLoad()` | clicks the hidden `.tad` input -> `loadDraft(dataView)` |
| `loadDraft` | reset, base64 -> JSON, **merge** over the reset patchSystem, `setInitialValues()` |
| `APPLY PATCH` -> `tryApply()` | `v==1 -> applyPatch()`, `v==2 -> applyPatch2()`; pushes `{name: title||filename}` onto the on-screen LOG |
| `SAVE <file>` -> `salvar()` | POST `api/v2/tools {version, tipo:30, data}`, and **only in its `.then()`** `download(true)` -> `saveAs(new Blob([dataviewSlus.buffer]), filenameSlus)` |
| `setPrivate()` | a hidden click target (an `&nbsp;` span next to the version string) that flips `isPrivate`; when set, `salvar()` calls `download(true)` **directly**, bypassing the analytics POST. So the download works offline/logged-out |

Error handling: every write is wrapped in `try{}catch{}`. A `DataView.setUintN` past the end of the
buffer throws `RangeError`, which is caught, and after the loop the tool shows
`"Your <file> is not the size indicated for the patch."` — that is the **only** validation of any
kind. Nothing checks the target's size, name, hash, or whether the stock bytes are what the patch
expected. (Cosmetic bug: `applyPatch()` accumulates the offending *offsets*, `applyPatch2()`
accumulates the offending *byte values*, so the v2 message is useless either way — the string is
built and then only tested for emptiness.)

Applying the same patch twice is allowed and is a no-op for areas; there is no undo in the tool —
you re-load the original file. (`tad.py apply --undo` fills that gap, see §6.)

Dead code inherited from `data/disassembler`: `dataviewWa`, `registers` (r0..r31/HI/LO/PC),
`newOp`, `codeOp`, `nameCodes`, `numCodes`, `offsetLight`, `index`, `newcode`, `offset` are all
declared in `data()` and referenced nowhere else in the chunk.

## 4. Which file does a `.tad` target?

**It is not recorded.** The loader's own on-page text says:

> To use this tool you will need your SLUS_014.11, WA_MRG.MRG or SU.MRG (or similar) files [...]

Both game files go into the same `dataviewSlus` and the same code path; `accepted` is only an HTML
`accept=` hint on the `<input type=file>`, so any renamed file is accepted. The only filter is size:

| file (verified on the real disc / decomp copy) | size | `minsize 0 / maxsize 42,991,616` |
|---|---|---|
| `SLUS_014.11` | 1,902,592 (0x1D0800) | loads |
| `/DATA/WA_MRG.MRG` (disc LBA 10102) | 37,748,736 (0x2400000) | loads |
| `/DATA/SU.MRG` (disc LBA 954) | 2,537,472 (0x26B800) | loads |
| `/DATA/MODEL.MRG` (disc LBA 28534) | 351,019,008 (0x14EC2000) | rejected, `alert("Wrong File Size!")` |

So `address` / the `b<off>` keys are **raw file offsets into whatever you dropped in**. For the EXE
the repo convention applies: `RAM = 0x80010000 + (off - 0x800)`; for WA_MRG,
`in-file sector = off / 2048`, `disc LBA = 10102 + sector`.

Verified against the real disc image: WA_MRG offset `0xE9B000` = in-file sector `0x1D36` = disc LBA
**17580**, and the 3 sectors there decode as opponent 1's four `u16 weight[722]` pools, each summing
to exactly 2048 — matching `../process-moreopponets/README.md` §2.
(That sibling README prints the LBA as 17592; 10102 + 0x1D36 = 10102 + 7478 = **17580**.)

Consequence: nothing that the disc streams in later is reachable. The 0x80168000 screen modules,
the duel overlay at 0x80146000, and everything inside `MODEL.MRG` are invisible to a `.tad` unless
the patch targets their bytes *inside WA_MRG.MRG* — which is possible, because the overlay copies
live in WA_MRG, but the tool gives you no help finding them.

## 5. The signature, and why it does not protect anything

The creator asks the server to bless a patch and stores the answer:

    md5  = md5(JSON.stringify(patch_without_sign))        // npm "md5", webpack module 6821f
    POST api/v2/toolcontrol/genhash  {hash}        -> {ok, sign}
    patch.sign = sign                                     // {serial, user, athr}

The loader **never verifies it**. `sign` is used in exactly one place: to print the author name
(`sign.user`) and link `/extend/user/profile?id=<sign.athr>` under the patch title. An unsigned,
hand-made `.tad` (`tad.py create`) applies identically. Only the *creator* refuses to reopen a
patch whose `md5` + `sign.serial` the server rejects (`POST api/v2/toolcontrol/checkhash`,
"This file cannot be edited."). The creator's own on-page text confirms the intent:

> This patch can be uploaded and edited as many times as you want, however it can only be edited
> with your own account. The generated file has a reference to your account.

So `sign` is an authorship/ownership marker for the editor, not an integrity check on the payload.
This answers the open question left in `../data-disassembler/README.md` §10 — and corrects its
guess that `sign` is a bare string: it is an object.

## 6. Worked example, verified against the real files

`scripts/tad.py` rebuilt the eight-site "More Opponents" EXE patch as a v2 `.tad` from
`../process-moreopponets/patch/patch_*.bin` and applied it to a copy of the decomp's stock
`SLUS_014.11` (md5 `dab1b3c9a6b8a56558b5ca8f807339c3`):

| area (file off) | RAM | len | stock bytes (read from the real file) | patch bytes |
|---|---|---|---|---|
| 0x002540 | 0x80011D40 | 144 | `79 6e 63 00 43 44 5f 72 65 61 64 79 ...` = `ync\0CD_ready\0` .. `$Id: bios.c,v 1.86 ...` | 16 zero bytes then three stubs |
| 0x012048 | 0x80021848 | 8 | `ff 07 42 30 01 00 45 24` = `andi v0,v0,0x7FF` / `addiu a1,v0,1` | `6a 47 00 08 00 00 00 00` = `j 0x80011DA8` / `nop` |
| 0x01205B | 0x8002185B | 1 | `96` (`lhu v0,0(s0)`) | `92` (`lbu v0,0(s0)`) |
| 0x01207C | 0x8002187C | 1 | `02` (`addiu s0,s0,2`) | `01` (`addiu s0,s0,1`) |
| 0x014C50 | 0x80024450 | 8 | `21 98 00 00 10 00 b4 27` = `move s3,zero` / `addiu s4,sp,0x10` | `60 47 00 08 00 00 00 00` = `j 0x80011D80` / `nop` |
| 0x014C77 | 0x80024477 | 1 | `94` (`lhu v0,0(v1)`) | `90` (`lbu v0,0(v1)`) |
| 0x014CD4 | 0x800244D4 | 1 | `02` | `01` |
| 0x028D68 | 0x80038568 | 8 | `0a 80 01 3c 61 b3 25 a0` = `lui at,0x800A` / `sb a1,-0x4C9F(at)` | `54 47 00 08 00 00 00 00` = `j 0x80011D50` / `nop` |

Jump-target arithmetic checks out: `0x0800476A -> (0x476A << 2) = 0x11DA8 -> 0x80011DA8`,
`0x08004760 -> 0x80011D80`, `0x08004754 -> 0x80011D50`.

Results:

- `tad.py apply` output is **byte-identical** to `../process-moreopponets/scripts/more_opponents.py apply`
  (md5 `a43b047f4296232c1928625969ce3c59`, 153 bytes changed);
- `tad.py apply --undo undo.tad` then applying `undo.tad` reproduces the stock EXE **byte-for-byte**;
- `tad.py diff stock patched out.tad` -> `apply` reproduces the same patched EXE.

## 7. The PsyQ-debug-string scratch convention

The container itself has no notion of scratch space — but TEA's own patches use one, and a `.tad`
is how they ship it, so it belongs here. Three regions of the base EXE hold **PsyQ library debug
strings that the retail build never prints**, and the site treats them as free RAM for injected
code and variables. All three verified in `~/ygofm-decomp/SLUS_014.11`:

| RAM | file off | stock content | used by |
|---|---|---|---|
| 0x80011D40 | 0x2540 | libcd `bios.c` strings: `CD_ready`, `%s...`, `%s: no param`, `CD_cw`, `$Id: bios.c,v 1.86 1997/03/28 07:42:42 makoto Exp yos $`, `CD_init:`, `addr=%08x`, `CD_datasync` | `process/moreopponets` — a u16 bank offset at 0x80011D40 + three trampolines at 0x80011D50 / 0x80011D80 / 0x80011DA8 |
| 0x80012580 | 0x2D80 | libcd/libmcrd file-access strings: `Access Denied. : file already open.`, `... file not open.`, `... invalid data size align`, `... invalid offset value align`, `... system busy` | `process/specialbanlist` — a colour script at 0x80012580..0x80012628 |
| 0x80095600 | 0x85E00 | libgte matrix-stack strings: `Error: Can't push matrix,stack(max 20) is full!`, `Error: Can't pop matrix,stack is empty!`, `This function is not implemented.` | `process/specialbanlist` — two register save areas at 0x80095600 and 0x80095620 |

`process/specialbanlist` also uses 0x80012978..0x800129B4 (libmdec strings). None of these are
referenced by any reachable code path in the retail EXE, which is why overwriting them is safe;
they are, however, a hard-coded shared resource — two site patches that both claim 0x80011D40 will
silently corrupt each other, and nothing in the `.tad` format detects the collision.

## 8. Recomp options

1. **Read `.tad` directly.** The container is trivial (base64 -> JSON -> offset/byte runs) and
   offset-based, so a `PSX_MOD_CONSTRUCTOR` can load a `.tad` out of the player-data directory and
   replay it. For `bytes`/`areas` that fall inside the base EXE image
   (`0x800 <= off < 0x1D0800`), convert with `addr = 0x80010000 + off - 0x800` and use
   `psx_mod_write_code_word(addr, word)` once at startup. **Guard every write with
   `psx_mod_read_word(addr) == stock`** — the format carries no stock bytes and no target id, so a
   patch cut against a different build would otherwise corrupt silently. `tad.py verify` is the
   offline version of exactly that check and should be run first.
2. **Dynamic zones map onto mod settings.** `dZones` is already "a labelled, typed, bounded number
   the user edits" — the natural recomp shape is one config entry per `tag`, written into the
   patched image at load. Because `applyPatch2` writes zones *after* areas, a recomp can apply the
   areas once at startup and re-write only the zones whenever a setting changes.
3. **Offsets outside the EXE need a different hook.** A `.tad` aimed at WA_MRG.MRG is a *data-file*
   patch. In the recomp there is no WA_MRG on disk to poke, so those records have to be translated
   into the equivalent table writes (see `../cardsdata`, `../drop`, `../process-moreopponets` for
   the table layouts) or applied to the extracted file before the recomp reads it. Detect the case
   by size: an offset >= 0x1D0800 cannot be an EXE offset.
4. **Do not port the scratch-space convention.** 0x80011D40 / 0x80012580 / 0x80095600 exist because
   the site has nowhere else to put code. A recomp mod writes native C and does not need the space,
   so the right move is to reimplement each patch's *behaviour* (`psx_free_duel_rows.c` style) and
   leave the PsyQ strings alone — that also removes the cross-mod collision hazard in §7.
5. **A `tad` export would make the recomp interoperable both ways.** `tad.py diff` already turns
   "stock EXE vs modded EXE" into a v2 patch the site's own loader accepts; a recomp debug command
   that dumps its applied code-word patches in the same shape would let recomp mods be shared with
   emulator users.

## 9. Decomp findings (proposed)

Nothing in this tool is game behaviour; these are the corroborations it produces.

- `0x80011D40..0x80011DD0` (file 0x2540) | libcd `bios.c` debug strings — `CD_ready`, `CD_cw`,
  `$Id: bios.c,v 1.86 1997/03/28 07:42:42 makoto Exp yos $`, `CD_init:`, `addr=%08x`,
  `CD_datasync` — verified byte-for-byte in the stock EXE; unreferenced, used as TEA scratch |
  `gPsyQ_szCdBiosStrings` (data blob, or leave unnamed with a note)
- `0x80012580..0x80012628` (file 0x2D80) | libcd/libmcrd `Access Denied. : ...` message table,
  verified in the stock EXE; unreferenced, used as TEA scratch | `gPsyQ_szFileErrorStrings`
- `0x80095600..0x80095640` (file 0x85E00) | libgte matrix-stack error strings
  (`Can't push matrix,stack(max 20) is full!`, `Can't pop matrix,stack is empty!`,
  `This function is not implemented.`), verified; unreferenced, used as TEA scratch |
  `gPsyQ_szGteErrorStrings`
- `0x80010000 + (off - 0x800)` | a third independent tool (after `data/disassembler` and the
  process tools) uses the repo's EXE load map, and its `j` targets resolve correctly against it |
  *(convention, no symbol)*
- WA_MRG.MRG | disc LBA 10102, 0x2400000 bytes; SU.MRG LBA 954, 0x26B800; MODEL.MRG LBA 28534,
  0x14EC2000 — re-read from the raw disc image while checking the loader's size cap |
  *(no symbol; corrects `process-moreopponets/README.md`'s "disc LBA 17592" to 17580)*

## 10. Open questions

- **What the server does with `serial`.** `genhash`/`checkhash` are signed-session endpoints and
  out of scope per the brief. Unknown whether `serial` encodes the md5 or is just a row id, and
  whether `checkhash` compares the md5 or only checks ownership. Either way the *loader* ignores it.
- **The `pic` whitelist.** `pic` is a bare filename appended to `/Assets/img/tools/patch/`; no
  index of that directory is public, so the set of legal values is unknown. (It is inserted into a
  CSS `url(...)` unescaped — a mild injection surface, not something worth probing.)
- **Published patches.** The tool expects users to obtain `.tad` files from the site/community;
  the listing is behind the session-gated API, so no genuine site-signed `.tad` was available to
  test against. Everything here is derived from the two writers' code plus round-trips through
  `tad.py`, which reproduce the writers exactly.
- **`locked`.** Written by all three tools, read by none of them. Presumably a planned
  "no further edits" flag; there is no server-side behaviour visible from the client.
