# DISASSEMBLER tool

Route: `extend/tools/data/disassembler` (login-gated; tool id `tipo: 22`, comment board `guia: 32`).
Input: SLUS_014.11 — the file picker declares `accepted: ".11,.mrg"`, `minsize 0`, `maxsize 41,000,000`
(42,991,616), so WA_MRG.MRG loads too but the RAM column is then meaningless.
Second input: a `.tad` draft (`accepted: ".tad"`, `maxsize 5,242,880`).
Client-side except for the *signed* patch export and the licence heartbeat (see "Server side").
Script: `scripts/tea_disasm.py` — offline clone: listing, `functions.bin` dump, assembler,
word poke, `.tad` read/make/apply/revert, opcode-coverage report.
Raw session notes: `NOTES-raw.md`.

This is **not a byte patcher with a fixed patch list**. It is a generic MIPS R3000 viewer /
one-word assembler over the uploaded EXE, plus a portable patch file. So the sections below
document what it can do, exactly how faithful it is, and what breaks.

## 1. What it is

| | |
|---|---|
| component | `Parser` in `site/js/extend/tools/data/disassembler.3b67ed93.js` |
| address model | `RAM = 2147547136 + file_offset` = `0x8000F800 + off` (= `0x80010000 + (off - 0x800)`) |
| default offset | `29184` = `0x7200` → RAM `0x80016A00`, mid-`func_80016784`; an arbitrary leftover, not a landmark |
| window | `numCodes` instructions from `offset`, 1..3000, default 100 |
| columns | RAM (toggle) · ADDRESS FILE (decimal) · HEX · OPCODE · ATTR · DESCRIPTION |
| reads | `dataviewSlus.getUint32(offset + 4*i, /*LE*/ true)` |
| writes | `dataviewSlus.setUint32(offset, word, true)` (the **WRITE** button), one word at a time |
| download | `saveAs(new Blob([dataviewSlus.buffer]), filenameSlus)` — the whole edited EXE |

Everything is one flat DataView over the uploaded file; there is no section model, no relocation
awareness, and no notion of the disc-loaded modules or the duel overlay.

Verified against `~/ygofm-decomp/SLUS_014.11` at the default offset — output matches
`asm/nonmatchings/func_80016784/func_80016784.s` line for line:

    RAM       file   hex        tool                            decomp
    80016A00  29184  3C020010   LUI   $2,16                     lui   $v0, (0x100008 >> 16)
    80016A04  29188  08005AB0   J     function 29376            j     .L80016AC0
    80016A08  29192  34420008   ORI   $2,$2,8                   ori   $v0, $v0, 0x8
    80016A0C  29196  24020016   ADDIU $2,$0,22                  addiu $v0, $zero, 0x16
    80016A10  29200  1062001D   BEQ   $3,$2, 29                 beq   $v1, $v0, .L80016A88
    80016A18  29208  14620028   BNE   $3,$2, 40                 bne   $v1, $v0, .L80016ABC
    80016A24  29220  A222000E   SB    $2 $17(14)                sb    $v0, 0xE($s1)

Two conveniences worth stealing: `J`/`JAL` render their target as **`function <file offset>`**
(`4*target - 0xF800`), and clicking the DESCRIPTION cell of a branch highlights the target row
(`offsetLight = address + 4 + 4*simm`). `scripts/tea_disasm.py dis --targets` prints both.

## 2. Instruction coverage

Decoder (`parseCode` + table `x`), keyed `op = w >> 26`, then `funct` for op 0, `rt` for op 1,
`rs` for op 16:

| group | mnemonics |
|---|---|
| SPECIAL (op 0), 28 | ADD ADDU AND NOR OR SLT SLTU SUB SUBU XOR SLL SLLV SRA SRAV SRL SRLV DIV DIVU MFHI MFLO MTHI MTLO MULT MULTU BREAK JALR JR SYSCALL |
| REGIMM (op 1), 4 | BGEZ BGEZAL BLTZ BLTZAL |
| COP0 (op 16), 2 | MFC0 MTC0 |
| other, 22 | ADDI ADDIU ANDI LUI ORI SLTI SLTIU XORI BEQ BGTZ BLEZ BNE J JAL LB LBU LH LHU LW SB SH SW |
| special-cased | word `0x00000000` → `NOP` |

**Not decoded at all** (rendered as `NONE`, no operands): the unaligned loads/stores
LWL/LWR/SWL/SWR (op 0x22/0x26/0x2A/0x2E), every COP2/GTE instruction (op 0x12) and
LWC2/SWC2 (op 0x32/0x3A), COP0's RFE, LWC0-3/SWC0-3 in general, and the COP1/COP3 space.

Measured on the real EXE with `scripts/tea_disasm.py coverage`, over the code segment
`0x800..0x803E0` (130,808 words):

    3126 undecodable (2.39%)
       op 18 (0x12) COP2/GTE  956
       op 50 (0x32) LWC2      632
       op 58 (0x3A) SWC2      420
       op 38 (0x26) LWR       157
       op 34 (0x22) LWL       143
       op 42 (0x2A) SWL       141
       op 46 (0x2E) SWR       141
       op  0        bad funct 107   (mostly jump tables / rodata inside .text)
       rest                   ~350

So any function that touches the GTE (all the 3D/model code) or does unaligned string work
reads as a wall of `NONE`. For real work `mips-linux-gnu-objdump -D -b binary -m mips:3000 -EL
--adjust-vma=0x8000F800` is strictly better; the site tool's value is the in-browser edit +
`.tad` round trip, not the disassembly.

Other fidelity notes:
- registers are printed as `$0..$31` — **no ABI names**, no symbol names, no `gp`-relative resolution.
- the ATTR column prints immediates **unsigned** (`addiu $2,$0,65528` for `addiu v0, zero, -8`);
  only the DESCRIPTION column sign-extends. Load/store ATTR is `$rt $rs(imm)` with an unsigned imm too.
- branches print the raw halfword displacement, not a target address.
- `JR`/`JALR`/`BREAK`/`SYSCALL` use inline formatters; `BREAK`/`SYSCALL` print no operand at all.

## 3. Assembler ("GEN" + "WRITE")

`codeList` ships **55 mnemonics** — the decoder's set minus `nop`, plus a `syscall` entry:
add addi addiu addu and andi lui nor or ori slt slti sltiu sltu sub subu xor xori sll sllv sra
srav srl srlv div divu mfhi mflo mthi mtlo mult multu beq bgez bgezal bgtz blez bltz bltzal bne
break j jal jalr jr mfc0 mtc0 syscall lb lbu lh lhu lw sb sh sw.

You pick a mnemonic from a dropdown, type `rs`/`rt`/`rd`/`sa`/`imm`/`tgt` as **decimal register
numbers**, press GEN to get the hex word, then WRITE to poke it at the current offset. Selecting
an existing row's OPCODE cell (`editOpCode`) pre-fills the fields from that word and sets the
offset to that row, so "edit this instruction in place" is a two-click flow.

Two helper toggles next to the fields (`newOPModifier`):

| field | states |
|---|---|
| `imm` | raw · "Signed To UnSigned" (`x < 0 → 0x10000 + x`) · "Hex value" (`parseInt(x,16)`) |
| `tgt` | raw · "Auto Positive Value" (`abs`) · "Ram Address" (`int(hex[-6:],16)/4`) · "Slus Address" (`(off + 0xF800)/4`) |

The "Ram Address" trick works only because every FM code address is `0x800xxxxx`, so the last six
hex digits are exactly the 28-bit region. `scripts/tea_disasm.py` exposes both as
`tgt_from_ram()` / `tgt_from_slus()`.

### Bugs in the shipped tool (reproduced by the script unless you pass `--fix`)

1. **`mtlo` assembles to `mflo`.** Its generator emits funct `010010` (0x12 = MFLO) instead of
   `010011` (0x13 = MTLO): `mtlo $3` → `00600012`, which is `MFLO $0`. Writing that into the EXE
   silently drops the intended `LO = rs`. `tea_disasm.py asm mtlo --rs 3 --fix` emits `00600013`.
   The *decoder* has MTLO (funct 19) correct, so a hand-typed hex word is fine.
2. **`mthi` and `mtlo` are both labelled `mflo`** in the dropdown (`name: "mflo"` on all three
   entries), so the list shows "mflo rd=LO", "mflo HI=rs", "mflo LO=rs".
3. **`break`/`syscall` take their 20-bit code from the `imm` box**, not a code box: the field
   packer `C()` builds `code` out of `e.imm`.
4. `getOpcodes()` **appends** to `nameCodes` instead of replacing it; only the "number of opcodes"
   input clears the list first, so re-reading at a new offset without touching that box stacks
   listings.
5. `createAllOpcodes()` — the "dump every function to `functions.bin`" routine — **is never
   called from the template.** It is complete, working, dead code. `tea_disasm.py functions`
   reproduces its exact output format:

       FUNCTION 29184
       (blank)
       80016A00 29184 LUI $2,16 $2 = 0010 << 16
       ...

   It starts a new `FUNCTION <fileoff> <RAMHEX>` header on the instruction after a delay slot
   that followed `0x03E00008` (`jr $ra`, the literal `65011720` in the source). Run over the whole
   code segment that yields **1932** "functions" against the decomp's **2503** `type:func`
   symbols — the split is naive (multi-return functions get cut, and any data word that happens
   to equal `03E00008` starts a bogus one).

## 4. The `.tad` patch format

Both variants are **base64 of a JSON object, stored raw in the file** (no header, no compression;
the file's bytes are the base64 text). `scripts/tea_disasm.py tad show|make|apply|revert` handles both.

**v1** — "CREATE PATCH" / "LOAD DRAFT", produced entirely client-side:

```json
{"v":1,"title":"","locked":false,
 "notes":[{"id":0,"text":"free-form note","date":"2026-09-04 12:00:00"}],
 "bytes":{"c29184":1006764048, "c29188":134240944}}
```

`bytes` keys are `"c" + decimal file offset`; values are the instruction word as a JS number,
written back with `setUint32(off, v, /*LE*/ true)`. `applyPatch()` pokes every entry into the
loaded DataView and alerts the offsets that threw (i.e. past EOF). Loading a draft **merges** it
over the current `patchSystem` and applies immediately. `locked` is carried but never read here.

**v2** — "EXPORT V2", produced by the `PatchV2` component, and this is the format the
`behavior-patchloader` / `behavior-patchcreator` tools consume:

```json
{"v":2,"title":"NoName from Disassembler","notes":[...],"locked":false,
 "dZones":{}, "bytes":[],
 "areas":[{"address":29184,"data":"10 00 02 3C B0 5A 00 08","isHex":false}],
 "sign":"<server-issued signature>"}
```

`generateJson()` sorts the recorded offsets and **coalesces adjacent words into runs**
(`prev.address + prev.data.length < next` starts a new area), emitting each word as four
space-separated hex bytes in **little-endian file order**. The title is hard-coded to
"NoName from Disassembler" — whatever you typed in the title box is discarded on the v2 path.

## 5. Server side (what you cannot do offline)

| call | when | effect |
|---|---|---|
| `POST api/v2/toolcontrol/validate` | every 3 s from `created()` | a `setInterval` **destroys the editor, blanks `document.body` and redirects to `/extend`** unless this returns `{ok:true}` first. 401 → `/extend/info/join`. |
| `POST api/v2/tools` `{version, tipo:22, data}` | "SAVE SLUS" | analytics ping; **the EXE download only happens in its `.then()`**, so an offline/failed POST means no file |
| `POST api/v2/toolcontrol/genhash` `{hash: md5(json)}` | "EXPORT V2" | returns `{ok, sign}`; `sign` is stitched into the `.tad` before download. **v2 drafts are server-signed and cannot be produced offline.** |
| `GET api/v2/pops?v=` | mount | site-wide announcement popups, nothing to do with the EXE |
| `POST api/v2/users/login`, `GET api/v2/users/validate` | login modal | account |

The signature is over `md5(JSON.stringify(generateJson()))` of the patch *before* `sign` is added.
Nothing is uploaded except that hash — the patch bytes themselves never leave the browser.

## 6. Symbol / address map: there is none

The brief asked whether anything here is worth importing into the decomp. Checked and **no**:

- the whole 107 KB chunk contains exactly two magic addresses — `2147547136` (`0x8000F800`, the
  RAM base) and `65011720` (`0x03E00008`, `jr $ra`) — plus the default offset `29184`. A grep for
  `0x8?????` / six-to-eight-digit constants over the raw file finds no address table.
- `api/v2/pops` returns site announcements, not symbols.
- registers print as `$N`; there is no label, name, or comment store anywhere in the tool, and the
  `.tad` format has no symbol field either (only free-text `notes`).

So no `symbols/` directory is created here. For reference, `~/ygofm-decomp/config/symbol_addrs.txt`
carries 3183 lines / 2503 `type:func` entries, 1185 of them already hand-named — strictly more
than anything this tool knows. The one thing the site tool *does* produce that the decomp does not
have a direct analogue for is the `functions.bin` naive `jr $ra` split (1932 boundaries), and the
decomp's `config/function_ranges.txt` (6135 lines) is a strictly better version of that.

## 7. What the game does with it

Nothing specific — the tool edits arbitrary words of the base EXE, which maps to RAM
`0x80010000..0x801D0000` at load. Two consequences worth writing down for anyone rebuilding this:

- **The default offset is not special.** `0x7200` → `0x80016A00` sits inside `func_80016784`
  (a screen/mode dispatcher; the `j .L80016AC0` at `+4` is one arm of its switch). Nothing in the
  tool depends on it.
- **Anything the disc streams in is invisible here.** The 0x80168000 screen modules, the duel
  overlay at 0x80146000, and the WA_MRG data tables (see `data-dropUI`) are *not* in SLUS_014.11,
  so a `.tad` cannot reach them. Loading WA_MRG.MRG into the same reader is allowed by the size
  cap but the RAM column and `J`/`JAL` target arithmetic are then wrong (they assume the EXE map),
  which is why the RAM checkbox is labelled "only slus file".

## 8. Recomp options

The disassembler is a *workbench*, not a feature, so "rebuild it" splits three ways:

1. **`.tad` v1 as a mod input format.** It is trivially parseable (base64 → JSON → offset/word
   pairs) and offset-based, so a `PSX_MOD_CONSTRUCTOR` can read a `.tad` from the player-data
   directory and, for every entry, `psx_mod_write_code_word(0x8000F800 + off, word)` once at
   startup. Guard each write with `psx_mod_read_word(addr) == stock` so a draft cut against a
   different EXE fails loudly instead of corrupting. `scripts/tea_disasm.py tad show` prints the
   decoded instruction for each entry so a mod author can eyeball a draft before shipping it.
   v2 areas are the same thing with byte runs, and `sign` can simply be ignored offline.
2. **A live disassembler view.** The recomp already has `tools/live_disasm.py` and
   `tools/exe_dis.py`; those are better than this tool in every way (full R3000+GTE, symbol
   names from `symbol_addrs.txt`). The only thing worth porting is the UX: "click a branch,
   highlight the target" and "J/JAL show the destination as an address you can jump to".
3. **Don't port the assembler.** 55 mnemonics, no pseudo-ops, no labels, no expression parser,
   decimal register numbers only, and the `mtlo` encoding is wrong. Anything that needs to emit
   code in the recomp should use real assembly or the existing `psx_mod_write_code_word` helpers.

## 9. Decomp findings (proposed)

Nothing here is game behaviour, so there is little to merge. Two small confirmations:

- `0x80016A00` (file 0x7200) | the site tool's default landing offset; confirmed to be inside
  `func_80016784`, a mode dispatcher whose arm at `+0x4` jumps to `.L80016AC0` | *(no name change proposed)*
- `0x8000F800` | the site independently uses the same file→RAM base the repo's convention uses
  (`RAM = 0x80010000 + (off - 0x800)`), i.e. a third-party corroboration of the load map | *(convention, no symbol)*

## 10. Open questions

- `api/v2/toolcontrol/genhash` signing: unknown what the server checks besides producing a
  signature — whether the sign is verified by `behavior-patchloader`, or only decorative.
  (Not probed: signed-session endpoints are out of scope per the brief.)
- The `.tad` `locked` flag is written but never read in this tool; presumably
  `behavior-patchcreator`/`patchloader` honour it. Cross-check with those folders.
- `registers` (r0..r31, HI, LO, PC) and the `exec(registers, values)` path are present in the
  component but nothing in the template calls them — there was evidently a step-through
  interpreter planned. Only `lightCode` (branch-target highlight) survives.
- `pops` payload not fetched (needs a session).
