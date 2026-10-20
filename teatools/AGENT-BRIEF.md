# Brief for documenting a TEA-Online tool folder (~/teatools/<tool>/)

You are documenting reverse-engineered modding tools for the PS1 game Yu-Gi-Oh! Forbidden
Memories (US, SLUS-01411) so their capabilities can be rebuilt as mods in a static recomp.
The site's tool code is already mirrored in `<tool>/site/`. Work ONLY inside the tool
folders assigned to you. Do not modify anything under ~/ygofm-decomp or
~/YuGiOhForbiddenMemoriesRecomp, do not git commit anywhere, do not log in to anything,
and do not call the site's `api/v2/...` endpoints (they need a signed session). Plain GETs of
static files from https://www.basededatostea.xyz/ (e.g. `/Assets/files/*.xlsx`, images the tool
references) are fine and should be saved into `<tool>/site/`.

## Read first
- `~/teatools/README.md` (conventions), `~/teatools/MIRROR-RECIPE.md` (how the JS is shaped)
- exemplars to match in structure and depth: `~/teatools/duel-result/README.md`,
  `~/teatools/initial-deck/README.md`

## Where the logic is
`<tool>/site/js/extend/tools/.../<name>.<hash>.js` is the tool's own webpack chunk (Vue 2 SPA).
`chunk-common`, `chunk-vendors`, `Assets/js/m2.js` (Materialize), `h.js`, `saver.js` (FileSaver)
are framework, ignore unless the tool imports a helper from chunk-common. Pretty-print with
`sed 's/},{/},\n{/g; s/;/;\n/g' x.js > pretty.js` and grep for `getUint8|getUint16|setUint8|
setUint16|DataView|accepted:|minsize|maxsize|saveAs|api/v2`. Every tool follows one shape: a
`*Reader` component (props `accepted`, `minsize`, `maxsize` tell you the input file: `.11` =
SLUS_014.11 ~1.9 MB, `.mrg` = WA_MRG.MRG 30-42 MB, `.mcr/.mcd` = memory card, images = PNG)
emits a DataView; `get*()` reads fixed offsets to fill the UI; `set*()`/`setBytes()` write back;
`saveAs()` downloads. Some tools instead download a template (xlsx) or generate files.

## Mapping bytes to the game
- SLUS_014.11 file offset -> RAM: `RAM = 0x80010000 + (off - 0x800)`. Stock copy for verifying
  bytes: `~/ygofm-decomp/SLUS_014.11` (read-only; copy to your scratch dir to test patches).
- WA_MRG.MRG = disc LBA 10102, 0x2400000 bytes. Raw disc image (MODE2/2352, data at +24 in
  each 2352-byte sector): `/home/codyj/YuGiOhForbiddenMemoriesRecomp/disc/Yu-Gi-Oh! Forbidden Memories (USA).bin`
  (read-only). Helpers: `sys.path.insert(0,'/home/codyj/ygofm-decomp/tools'); import extract_overlay as eo`
  -> `eo.walk_iso(disc)` lists files (path, lba, size), `eo.sector(disc, lba)` returns 2048 data bytes.
  Screen modules load at 0x80168000 (free duel 0x1E88+0x57, name entry 0x1EDF+0x50 with the
  code module starting at in-file sector 0x1F20, password 0x1F2F+0x56 -> module at 0x1F76);
  the duel overlay is 7 x 235-sector copies at in-file LBA 0.. (see decomp config/duel_overlay.yaml).
- Decomp: `~/ygofm-decomp` (branch tangos/work). Names: `config/symbol_addrs.txt`,
  per-module names `config/modules/*.txt`, evidence: `notes/research/findings.md` (rows F1..F135),
  descriptions: `notes/research/descriptions.md`, matched C in `src/`, disassembly in `asm/`
  (`grep -rn "/\* .* 8002ABCD " asm/` finds the instruction at an address; `glabel` lines above
  give the function). Old IDB names: `reference/idb_raymond_2018/idb_names.txt`.
- Disassembler: `mips-linux-gnu-objdump -D -b binary -m mips:3000 -EL --adjust-vma=0x800XXXXX file.bin`.
- Card ids are 1..722; tables index id-1. Text bank: `gText_aBank` 0x801B0000 with u16 offsets
  at 0x801C0000 (string N starts at bank + offsets[N]); `FC 5A 12` = insert player name.
- Python has PIL 12 and numpy 2 available for image converters (PNG <-> TIM/raw 4bpp/8bpp/15bpp).

## What to produce per tool: `<tool>/README.md`
1. Title, route, input file(s) (type + size limits), one-paragraph purpose, status line.
2. One section per feature/patch with a table: file offset(s), RAM address (or WA_MRG offset +
   in-file sector + disc LBA), stock bytes, patched bytes and their meaning (decode MIPS words).
   Verify the stock bytes against the real file before stating them.
3. "What the game does with it": the consuming function(s), decomp names, a short disassembly
   or C excerpt, and the consequences (limits, quirks).
4. "Recomp options": concrete ways to rebuild the capability in the recomp (patch once at
   startup for base-EXE bytes; frame-hook + stock-word check for module/overlay bytes; native
   replacement where the site's patch is a hack). Idiom: `PSX_MOD_CONSTRUCTOR`, `psx_mod_read_word`,
   `psx_mod_write_code_word` (see ~/YuGiOhForbiddenMemoriesRecomp/src/psx_free_duel_rows.c).
5. "Decomp findings (proposed)": bullet list `address | what was proved | proposed name`. Do NOT
   edit findings.md yourself; the coordinator merges these.
6. "Open questions" and anything the tool does server-side that you could not see.
Also: `<tool>/scripts/<name>.py` — an offline clone (inspect / apply / restore, or convert)
whenever the tool is a byte patcher or a format converter; test it on a COPY in your scratch
dir (never on the decomp's SLUS or the disc); restore must reproduce the stock file
byte-for-byte. Keep the raw working notes in `<tool>/NOTES-raw.md` if they are long.

## Report back
For each tool, 3-6 lines: what it edits, the key addresses/offsets, quirks, and blockers.
