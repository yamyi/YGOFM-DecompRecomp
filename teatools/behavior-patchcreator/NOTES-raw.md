# Raw notes — behavior/patchcreator

Session 2026-09-04. Companion to `../behavior-patchloader/NOTES-raw.md`, which holds the shared
container notes (base64/JSON layout, applier semantics, md5, the PsyQ scratch regions, and all the
script test results). This file only records what is specific to the *writer*.

Chunk: `site/js/extend/tools/behavior/patchcreator.6e7f1436.js` (71,261 B). Pretty-printed with the
same brace-aware printer -> 9,095 lines. Component is `name:"PatchLoader"` (copy-paste; it is the
creator). Page version `V.230422`, `tipo: 31`, `guia: 41`.

## Where everything is (pretty-printed line numbers)

| what | line |
|---|---|
| `data()` — `patchSystem{v:2,...}`, `areas`, `dZone`, `dZones`, `pic`, `showPic`, `isPrivate` | 1770 |
| `list` computed (the 16-byte hex grid) | 1815 |
| `orangeBytes` computed (highlights `type` bytes from `address`) | 1905 |
| `salvar` | 1947 |
| `download` — early-returns because `dataviewSlus` is never declared | 1968 |
| `loadDraft` -> `$emit('makevalidate', {data,sign})` | 2003 |
| `commitDraft` | 2100 |
| `createPatch(sign)` — base64 + `saveAs('draft.tad')` | 2168 |
| `applyPatch` (v1, dead — no dataviewSlus) | 2196 |
| `addSection` / `fixBytes` / `fixAddress` / `resetDZones` / `deleteSection` | 2258–2380 |
| `showOptions` / `addDynamicValue` / `deleteDynamicValue` | 2400–2510 |
| `addNote` / `removeNote` | 2513–2570 |
| `genPatchComputed` | 2572 |
| `.call(this, a("b639").Buffer)` | 2610 |
| template: `V.230422`, hidden `setPrivate` span | 4550 |
| template: per-area address input + "Write Hex Value" | 4855 |
| template: `pic` textarea (behind `showPic`) | 5722 |
| `checkHash` -> `toolcontrol/genhash` | 8397 |
| `makevalidate` -> `toolcontrol/checkhash` | 8451 |
| `saveChange()` `tipo = 31` | 8342 |

## Editor -> JSON

`genPatchComputed()`:

    e = {...this.patchSystem, dZones:{...this.dZones}, areas:[...this.areas]}
    if (this.pic !== "") e.pic = this.pic

`patchSystem` is `{v:2,title,notes,locked:false,bytes:{}}`, so the emitted key order is

    v, title, notes, locked, bytes, dZones, areas [, pic] [, sign]

`createPatch(sign)` re-runs `genPatchComputed()`, sets `.sign`, then
`Buffer.from(JSON.stringify(a),'utf8').toString('base64')` -> Blob -> `saveAs(..., 'draft.tad')`.
Filename is always `draft.tad`.

## Field-by-field

- `title` <- the box labelled `Nombre` (untranslated).
- `notes[]`: `addNote()` pushes `{id: "<moment YYYY-MM-DD HH:mm:ss> <index>", text, date: same}`.
  `removeNote` filters by `id`.
- `areas[]`: `addSection()` pushes `{address:0, data:"", isHex:false}`.
  - `fixAddress(i)`: `isHex ? Math.abs(parseInt(v,16)) : Math.abs(parseInt(v))`, `NaN -> 0`,
    stored as a **number**. So `isHex` never affects the file; it is a per-section input-mode flag.
    Editor bug: the box then shows the decimal result, which is re-parsed as hex next edit
    (2540 -> 9536 -> 38198).
  - `fixBytes(i)`: strip `\n` and spaces, take 2 chars at a time, `Math.abs(parseInt(pair,16))`,
    `NaN -> "00"`, upper-case 2 digits, join with one space, trim. Canonical form `"AA BB CC"`.
    (There is a latent `else n = s.length` branch referencing an out-of-scope `s`; unreachable
    because the loop condition already excludes an empty pair.)
  - No alignment or length constraint — single-byte sections are normal.
- `dZones{}`: `showOptions(addr)` opens the panel for a clicked grid byte; `addDynamicValue()`
  requires a non-empty `tag` and stores `dZones["b"+address] = {address, type, tag}`.
  **No `value` field is written** — the loader re-derives it from the areas.
  `resetDZones()` (called from `fixBytes`, `fixAddress`, `addSection`) **wipes every dynamic value**
  whenever any section changes. Sections first, dynamic values last.
- `pic`: a bare filename; the loader does
  `url(/Assets/img/tools/patch/<pic>)`. Only visible after clicking a static-render fragment that
  toggles `showPic` (line 6026) — undocumented in the UI.
- `locked`: always `false`, never read anywhere.
- `bytes`: always `{}` — v2 payload lives in `areas`.

## Reopening (`LOAD`)

`loadDraft` normalises to `{v: i.v||0, title: i.title||"", notes: i.notes||[],
locked: i.locked||false, bytes: i.bytes||{}}`, **rejects `v != 2`** ("The file version is not
supported by the editor." — so v1 files cannot be edited here, only applied in the loader), then
`dZones = i.dZones ? i.dZones : []`, `areas = i.areas ? i.areas : []`, `pic` only if truthy, and
emits `makevalidate {data, sign: i.sign||{}}`.

`makevalidate` POSTs `{hash: md5(JSON.stringify(data)), serial: sign.serial}` to
`api/v2/toolcontrol/checkhash`; on `ok` -> `commitDraft(data)` ("File uploaded successfully."),
on error -> "This file cannot be edited."

So the hash is over the *normalised* object with `sign` and unknown keys removed, in the same key
order both writers emit. JS truthiness matters: `{}` and `[]` are true, so an empty `bytes`
survives `||` unchanged. (`tad.py.js_truthy` reproduces this; naive Python `or` would not.)

## The private path is broken in the creator

`setPrivate()` toggles `isPrivate` from the hidden `&nbsp;` span next to `V.230422`, and `salvar()`
then calls `download(true)` instead of emitting `create`. But `download()` guards on
`null != this.dataviewSlus`, and `dataviewSlus` is **never declared in `data()` nor assigned
anywhere in the creator** — there is no game-file reader in this tool at all. So the private path
silently produces nothing, and the copied-in `applyPatch()` (v1) is dead for the same reason.
Conclusion: unlike the loader, the creator genuinely cannot produce a file offline; `genhash` is
mandatory. Which is fine, because `scripts/tad.py create` produces the same bytes minus `sign`,
and the loader ignores `sign`.

## Cross-tool: data/disassembler

`PatchV2.generateJson()` (in `../data-disassembler/site/js/.../disassembler.3b67ed93.js`,
pretty line 13407):

    {...this.patch, dZones:{}, areas:a, bytes:[], v:2, title:"NoName from Disassembler"}

with `this.patch = {v,title,notes,locked,bytes}`. Object spread keeps existing keys in place, so
the order is the same `v,title,notes,locked,bytes,dZones,areas` -> a disassembler-made v2 file
hashes compatibly and can be reopened here (account permitting). Its `bytes` is `[]` not `{}` and
its v1 keys are `"c<off>"` not `"b<off>"` — both harmless, the readers are prefix- and
type-agnostic. Its area coalescing (`prev.address + prev.data.length < next`) is byte-accurate
because `data` is still an array of tokens at that point.

Answers to `../data-disassembler/README.md` §10:
- `sign` is **not** verified by `behavior-patchloader` (it only renders `sign.user`/`sign.athr`).
  It is an object `{serial,user,athr}`, not a string.
- `locked` is **not** honoured by patchcreator or patchloader either — dead in all three tools.

## Test artefacts

All script tests are recorded in `../behavior-patchloader/NOTES-raw.md` ("Script tests"). The
`scripts/tad.py` in this folder is byte-identical to the one there; both cover create/dump/hash/
verify/apply/diff for v1 and v2. Everything was run on copies in the session scratch dir; the
decomp `SLUS_014.11` and the disc image were opened read-only.
