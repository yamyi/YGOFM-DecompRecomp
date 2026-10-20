# teatools — what the TEA-Online mod tools do to Forbidden Memories, and how to do it in the recomp

Personal knowledge base. Each TEA-Online tool (https://www.basededatostea.xyz/extend/tools/...)
gets one folder here:

    <tool>/README.md      the capability: what it changes, exact addresses/bytes, what the game
                          does with them, and how to reproduce it as a recomp mod
    <tool>/site/          full mirror of the tool's web page + JS/CSS (the source of truth)
    <tool>/scripts/       offline scripts that reproduce the tool (inspect / apply / restore)
    <tool>/NOTES-raw.md   the original working notes from the reverse-engineering session

Conventions used everywhere:

- SLUS_014.11 file offset -> RAM:  `RAM = 0x80010000 + (file_off - 0x800)`
- WA_MRG.MRG lives at disc LBA 10102 (US disc); `in-file sector = off / 2048`,
  `disc LBA = 10102 + in-file sector`.
- Card ids are 1..722 as printed in the game; tables index them as id-1.
- Decomp cross-references use the names from `~/ygofm-decomp/config/symbol_addrs.txt`
  and the evidence rows in `~/ygofm-decomp/notes/research/findings.md` (F-numbers).

Recomp idiom (see `~/YuGiOhForbiddenMemoriesRecomp/src/psx_free_duel_rows.c`):
a `PSX_MOD_CONSTRUCTOR` registers a vblank/frame hook; the hook checks that the
stock word is present with `psx_mod_read_word(addr)` and then patches with
`psx_mod_write_code_word(addr, word)`. Patches inside disc-loaded modules
(0x80168000 screens, the duel overlay) must be re-applied every time the module
is loaded, which is why the hook runs every frame and compares against stock.

Per-tool status: see [site-index/README.md](site-index/README.md). Folder name = route with `/` -> `-`
(`duel-result` and `initial-deck` are the two exceptions). Eight routes are login-gated and need a
session cookie to mirror (see MIRROR-RECIPE.md). `mirror.py` mirrors routes; `AGENT-BRIEF.md` is the
spec every tool README follows.

How to add the next tool: follow [MIRROR-RECIPE.md](MIRROR-RECIPE.md).
