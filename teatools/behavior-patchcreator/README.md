# PATCH CREATOR tool

Route: `extend/tools/behavior/patchcreator` (public; page version string `V.230422`, analytics
`tipo: 31`, comment board `guia: 41`).
Input: a `.tad` patch to reopen (`accepted:".tad"`, `minsize 0`, `maxsize 5,242,880`). **No game
file is loaded** — the editor never sees SLUS_014.11 or WA_MRG.MRG.
Output: `draft.tad`, a server-signed v2 patch.
Purpose: hand-author the site's own patch container — you type byte runs and their file offsets,
optionally mark some of those bytes as user-editable "dynamic values", add a title, notes and a
header picture, and the site signs and downloads the result. The consumer is
[`behavior-patchloader`](../behavior-patchloader/README.md).
Status: format fully decoded; `scripts/tad.py` writes byte-identical containers (same JSON key
order, same normalisation) and round-trips through apply/undo byte-for-byte against the real
SLUS_014.11. The one thing that cannot be reproduced offline is the server `sign` — which the
loader ignores anyway (see §5).
Script: `scripts/tad.py` (dump / json / hash / verify / apply / create / diff; identical copy in
`behavior-patchloader/scripts/tad.py`). Raw session notes: `NOTES-raw.md`.

**The container format itself is documented in
[`../behavior-patchloader/README.md` §1–§4](../behavior-patchloader/README.md#1-the-tad-container).**
This README covers the *writer*: how the editor's UI maps onto that JSON, the exact bytes it emits,
the signing handshake, and what you can and cannot make offline.

## 1. The editor

`site/js/extend/tools/behavior/patchcreator.6e7f1436.js`, component named `PatchLoader` (copy-paste
from the loader; it is the creator). UI strings, in order down the page:

    V.230422
    With this tool you will be able to create patches for the game's internal files.
    [LOAD]  [+NEW]
    Nombre                                     <- the title box (untranslated Spanish label)
    Section 1
      Address  [x] Write Hex Value    <input>
      Hex bytes                       <textarea>          [X]
    [+ADD SECTION]
    HEX Values                                 <- the 16-byte-per-row hex grid, click a byte
      This Area / Value Name / Number of bytes: 1 Byte | 2 Bytes | 4 Bytes
      [+ADD DYNAMIC VALUE] [DEL]
    Notes  <textarea> [+ADD]   (each note shows with an [x])
    Pic    <textarea>                          <- only visible after clicking the hidden toggle
    [SAVE PATCH]
    This patch can be uploaded and edited as many times as you want, however it can only be
    edited with your own account. The generated file has a reference to your account.

| UI element | `data` field | goes into the `.tad` as |
|---|---|---|
| Nombre | `patchSystem.title` | `title` |
| Section *n* Address | `areas[n].address` | `address` (always a **decimal number**) |
| "Write Hex Value" checkbox | `areas[n].isHex` | `isHex` |
| Hex bytes | `areas[n].data` | `data` |
| a clicked byte + Value Name + width | `dZones["b"+addr]` | `dZones` |
| Notes | `patchSystem.notes[]` | `notes` |
| Pic | `pic` | `pic` (omitted when empty) |
| — | `patchSystem.locked` (always `false`) | `locked` |
| — | `patchSystem.bytes` (always `{}`) | `bytes` |

### `isHex` is about the *input box*, not the file

`fixAddress(i)` runs on every `change` of the address input:

    a = areas[i].isHex ? Math.abs(parseInt(v, 16)) : Math.abs(parseInt(v))
    areas[i].address = isNaN(a) ? 0 : a

so the address stored in the `.tad` is always a plain decimal integer, and `isHex` only records how
the box was typed. **Editor bug:** after conversion the box redisplays the *decimal* value, which
is re-parsed as **hex** on the next edit — typing `2540` with the box checked gives 9536, and
touching the field again turns 9536 into 0x9536 = 38198. Watch for it if you ever drive the real
tool; `tad.py create --area 0x2540:...` has no such trap.

### `fixBytes` — the canonical byte-string form

`fixBytes(i)` runs on every `change` of the hex textarea: strip newlines and spaces, take two
characters at a time, `Math.abs(parseInt(pair,16))`, `NaN -> "00"`, format as two upper-case hex
digits, join with a single space, `.trim()`. So a section's `data` in a site-made `.tad` is always
`"AA BB CC"`. (The applier is looser and splits on spaces — see the loader README's quirks table.)
There is no length limit and no alignment requirement: a 1-byte section is legal, which is how the
site ships single-byte opcode tweaks like `lhu -> lbu`.

### Dynamic values

Click any byte in the HEX Values grid -> `showOptions(addr)`; give it a "Value Name" (`tag`, must
be non-empty) and a width (1/2/4 bytes) -> `addDynamicValue()` stores
`dZones["b"+addr] = {address, type, tag}`. `orangeBytes` highlights `type` bytes starting at
`address`. `deleteDynamicValue()` removes it.

**`resetDZones()` wipes every dynamic value whenever any area's address or byte string changes**
(it is called from `fixBytes`, `fixAddress` and `addSection`). Define the sections first, the
dynamic values last, or you will lose them.

No `value` is stored — the loader always re-derives the default from the area bytes underneath.

## 2. Saving: `genPatchComputed()` -> md5 -> `sign` -> base64

```js
genPatchComputed() {                       // the object that gets hashed
  e = { ...this.patchSystem, dZones: {...this.dZones}, areas: [...this.areas] }
  if (this.pic !== "") e.pic = this.pic
  return e
}
salvar()      -> $emit('create', genPatchComputed())      // isPrivate path: see §4
checkHash(e)  -> POST api/v2/toolcontrol/genhash { hash: md5(JSON.stringify(e)) }
                 .then(r => createPatch(r.data.sign))
createPatch(sign) {
  const a = genPatchComputed(); a.sign = sign
  saveAs(new Blob([Buffer.from(Buffer.from(JSON.stringify(a),'utf8').toString('base64'),'utf8')]),
         'draft.tad')
}
```

`md5` is the npm `md5` package (webpack module `6821f`, the classic `crypt` implementation —
constants 1732584193 / -271733879 confirm it), over the UTF-8 bytes of `JSON.stringify`, hex output.
`hashlib.md5(json.encode('utf-8')).hexdigest()` reproduces it exactly.

### Canonical key order (this is load-bearing)

`{...patchSystem}` spreads `v, title, notes, locked, bytes` in that order, then `dZones` and `areas`
are appended as new keys, then `pic`, then `sign`:

    {"v":2,"title":..,"notes":[..],"locked":false,"bytes":{},"dZones":{..},"areas":[..][,"pic":..][,"sign":..]}

`JSON.stringify` preserves insertion order, so the md5 is order-sensitive. Reordering the keys of a
`.tad` by hand — even with identical content — changes the md5 and makes the creator reject the file.
`tad.py` emits and normalises in exactly this order; `tad.py hash -v` prints the string that is hashed.

**Cross-tool check:** `data/disassembler`'s `PatchV2.generateJson()` returns
`{...this.patch, dZones:{}, areas, bytes:[], v:2, title:"NoName from Disassembler"}` where
`this.patch` is `{v,title,notes,locked,bytes}` — object-spread keeps existing keys in place, so its
order is the **same** `v,title,notes,locked,bytes,dZones,areas`. A disassembler-made v2 `.tad`
therefore hashes the same way and can be reopened in the creator (subject to account ownership).
Note its `bytes` is `[]`, not `{}` — harmless, and `loadDraft`'s `i.bytes || {}` keeps `[]` because
an empty array is truthy in JS.

## 3. Reopening a patch: `LOAD` -> `checkhash`

```js
loadDraft(dataView) {
  o = Buffer.from(new TextDecoder().decode(dataView), 'base64').toString()
  i = JSON.parse(o)                                   // failure swallowed, i = {}
  n = { v: i.v||0, title: i.title||"", notes: i.notes||[], locked: i.locked||false,
        bytes: i.bytes||{} }
  if (n.v != 2) { alert("The file version is not supported by the editor."); return }
  n.dZones = i.dZones ? i.dZones : []
  n.areas  = i.areas  ? i.areas  : []
  if (i.pic) n.pic = i.pic
  $emit('makevalidate', { data: n, sign: i.sign || {} })
}
makevalidate({data, sign}) {
  POST api/v2/toolcontrol/checkhash { hash: md5(JSON.stringify(data)), serial: sign.serial }
    .then(r => r.data.ok && editor.commitDraft(data))     // "File uploaded successfully."
    .catch(()  => editor.showAlert("This file cannot be edited.", 2))
}
```

Three things fall out of this:

- **v1 `.tad` files cannot be opened in the creator** — only the loader applies them. The creator is
  v2-only, both for reading and writing.
- The hashed object is a **normalisation**: `sign` and any unknown key are dropped, falsy fields are
  replaced with their defaults, and the key order is rebuilt as `v,title,notes,locked,bytes,dZones,
  areas[,pic]`. Since both writers emit that same order with the same defaults, a round trip is
  stable. `tad.py hash` implements this normalisation (including JS truthiness — `{}` and `[]` are
  **true** in JS, so an empty `bytes`/`dZones` object survives `||`).
- The server sees only the md5 and the serial. **The patch bytes never leave the browser.**

## 4. What you can and cannot do offline

| | |
|---|---|
| decode any `.tad` | yes — `tad.py dump` / `json` |
| build a v1 or v2 `.tad` | yes — `tad.py create` / `diff` |
| apply either version | yes — `tad.py apply`, bug-for-bug with `applyPatch`/`applyPatch2` |
| get a valid `sign` | **no** — `genhash` is a signed-session endpoint |
| have the *loader* accept your unsigned file | **yes** — it never verifies `sign` |
| have the *creator* reopen your unsigned file | no — `checkhash` rejects it ("This file cannot be edited.") |

The "private" escape hatch that works in the loader does **not** work here. Clicking the hidden
`&nbsp;` span next to the version string toggles `isPrivate`, and `salvar()` then calls
`download(true)` instead of emitting `create`. But `download()` early-returns on
`null != this.dataviewSlus` — and `dataviewSlus` is **never declared or assigned anywhere in the
creator**. So the private path silently produces nothing, and `applyPatch()` (a v1 applier copied
in from the loader, unreachable from the template) is dead for the same reason. The creator
genuinely cannot emit a file without the server.

## 5. Verified example

Rebuilt the eight-site "More Opponents" EXE patch (`../process-moreopponets/patch/patch_*.bin`) as a
v2 `.tad` and exercised the whole pipeline against a copy of the decomp's stock `SLUS_014.11`
(md5 `dab1b3c9a6b8a56558b5ca8f807339c3`). Stock bytes were read out of the real file, not assumed:

| area (file off) | RAM | len | stock (real file) | patch |
|---|---|---|---|---|
| 0x002540 | 0x80011D40 | 144 | `79 6e 63 00 43 44 5f 72 65 61 64 79 00 ...` (`ync\0CD_ready\0`, libcd `bios.c` strings) | 16× `00` then three MIPS stubs |
| 0x012048 | 0x80021848 | 8 | `ff 07 42 30 01 00 45 24` | `6a 47 00 08 00 00 00 00` (`j 0x80011DA8; nop`) |
| 0x01205B | 0x8002185B | 1 | `96` | `92` |
| 0x01207C | 0x8002187C | 1 | `02` | `01` |
| 0x014C50 | 0x80024450 | 8 | `21 98 00 00 10 00 b4 27` | `60 47 00 08 00 00 00 00` (`j 0x80011D80; nop`) |
| 0x014C77 | 0x80024477 | 1 | `94` | `90` |
| 0x014CD4 | 0x800244D4 | 1 | `02` | `01` |
| 0x028D68 | 0x80038568 | 8 | `0a 80 01 3c 61 b3 25 a0` | `54 47 00 08 00 00 00 00` (`j 0x80011D50; nop`) |

- `tad.py apply` == `../process-moreopponets/scripts/more_opponents.py apply`, byte-for-byte
  (md5 `a43b047f4296232c1928625969ce3c59`, 153 bytes changed).
- `tad.py apply --undo` -> apply the undo patch -> stock EXE reproduced **byte-for-byte**.
- `tad.py diff stock patched` -> `apply` -> the same patched EXE.
- `tad.py hash` on a file `tad.py create` wrote is stable across a decode/normalise round trip
  (`dumps_js(p) == dumps_js(normalised(p))`), i.e. the key order matches what the site would hash.

Dynamic zones were exercised on a synthetic 32-byte target: a `u16` zone seeded from
`"34 12 00 00 78 56 34 12"` defaults to 4660 (0x1234), a `u32` zone at +4 to 305419896 (0x12345678),
and `--set` overrides write little-endian at the zone address, after the areas.

## 6. What the game does with it

Nothing directly — the creator never touches the game. What matters for rebuilding the capability
is what a `.tad` can *reach*, and that is covered in
[`../behavior-patchloader/README.md` §4](../behavior-patchloader/README.md#4-which-file-does-a-tad-target)
(SLUS_014.11 / WA_MRG.MRG / SU.MRG by raw file offset, nothing disc-streamed) and
[§7](../behavior-patchloader/README.md#7-the-psyq-debug-string-scratch-convention) (the PsyQ
debug-string regions at 0x80011D40 / 0x80012580 / 0x80095600 that TEA patches use as scratch space,
all three verified in the stock EXE).

The one design fact worth restating here: because the creator has **no game file loaded**, it cannot
show you the stock bytes you are about to overwrite, cannot check that your offsets are in range,
and cannot warn about collisions with another patch's scratch space. Every published TEA patch was
authored blind against a hex dump taken elsewhere. That is the single biggest reason to reimplement
these as recomp mods rather than as `.tad` files.

## 7. Recomp options

1. **Use `tad.py diff` as the export path.** Build a modded EXE with the recomp's own tooling, diff
   it against stock, and you have a v2 `.tad` the site's loader accepts — recomp mods become
   shareable with emulator users at no cost. (`--gap N` controls how aggressively neighbouring
   changes are merged into one area.)
2. **Use `.tad` as a mod *input* format.** A `PSX_MOD_CONSTRUCTOR` can read a `.tad` from the
   player-data directory, convert in-EXE offsets with `addr = 0x80010000 + off - 0x800`, and apply
   with `psx_mod_write_code_word` — always gated on `psx_mod_read_word(addr) == stock`, because the
   container stores no stock bytes and no target identity. `tad.py verify` is that check offline.
3. **`dZones` are mod settings.** `{address, type, tag}` is already "a labelled, typed, width-bounded
   number the user edits". Map each `tag` to a config key; re-apply just the zones (after the areas)
   when a setting changes, mirroring `applyPatch2`'s ordering.
4. **Do not rebuild the editor.** The value here is the container, not the UI: no game file, no
   disassembly, no stock-byte display, no collision detection, and dynamic values silently vanish
   when you edit a section. A recomp equivalent should be a small CLI/JSON, which is what
   `scripts/tad.py` already is.
5. **Drop the signing.** It is an account-ownership marker for the site's own editor, not integrity:
   the loader never checks it, so a recomp reader has nothing to gain by parsing `sign` beyond
   printing `sign.user` as an attribution line.

## 8. Decomp findings (proposed)

See [`../behavior-patchloader/README.md` §9](../behavior-patchloader/README.md#9-decomp-findings-proposed)
— the two tools share one finding set (the three PsyQ debug-string scratch regions, the EXE load-map
corroboration, and the MRG disc geometry). Nothing additional is contributed by the creator, which
never reads a game file.

## 9. Open questions

- **`genhash` semantics.** Signed-session endpoint, not probed per the brief. Unknown whether
  `serial` embeds the md5 or is a database row id, and therefore whether `checkhash` is really
  verifying the payload or only the account.
- **`pic`.** A bare filename appended to `/Assets/img/tools/patch/` and dropped into a CSS
  `url(...)` unescaped. The directory has no public index, so the legal values are unknown; the
  field is also hidden behind an undocumented click (`showPic`, toggled from a static-render
  fragment) so most users never see it.
- **`locked`.** Written as `false` by every writer, read by none (patchcreator, patchloader,
  data/disassembler all checked). Whatever it was meant to gate was never implemented client-side.
- **Whether any published `.tad` uses `dZones` in anger.** No genuine site-signed `.tad` was
  obtainable (the patch listing is behind the session-gated API), so the dynamic-value path is
  verified only against the code and synthetic files.
- **`v` values other than 1 and 2.** `tryApply()` silently does nothing for anything else, and the
  creator refuses to open it. No evidence of a v3 in either chunk.
