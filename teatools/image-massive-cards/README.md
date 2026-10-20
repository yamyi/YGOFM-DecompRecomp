# MASSIVE LOADER — Big image Card (bulk card art)

Route: `extend/tools/image/massive/cards` (chunk `cards.4171f7dd.js`, **V.240303 [BETA] [Early
access for donors]**, login-gated — see MIRROR-RECIPE.md). Inputs: **WA_MRG.MRG** (`.mrg`,
31,457,280..44,040,192 bytes) plus a **.zip** of images (0..44,040,192 bytes, unzipped in the browser
with JSZip 3.10.1, mirrored as `site/Assets/js/z.js`). Output: the whole edited WA_MRG.MRG,
`saveAs()`-d under its original filename.

This is the bulk half of the per-card art replacer documented in
[`../image-specsmix/README.md`](../image-specsmix/README.md) §1 — **read that first**, the record
layout is identical and is not repeated here. What this tool adds is a two-tab batch loop: one zip of
`<id>.png` files for the 102x96 library art, one zip for the 40x32 thumbnail, and a Save panel.
What it *removes* is everything else: no SLUS input, no title/name rendering, no price/password, no
card-frame editing, no preview, no per-card palette UI.

Script: `scripts/card_art.py` (info / export / import / restore / roundtrip).
Status: decoded; layout re-verified on all 722 cards from the real disc; script round-trips
byte-for-byte and `restore` reproduces the stock file exactly.

## 1. What the two tabs write

Both tabs run the same loop: `createZipObject()` → `Object.entries(zip.files)` → for each entry
`formatID(name)` → decode blob as an `<img>` → draw on a `<canvas>` of exactly the target size →
`ImageConverter` quantises → `vt(dataviewWa, chunks, {header, body})` writes bytes → next entry.

`REC = 0x169000 + 14336*(id-1)` (in-file sector `722 + 7*(id-1)`, disc LBA `10817 + 7*id`).

### Tab 1 "Big Image" — 102x96 library art

| what | tool config | WA_MRG offset | size |
|---|---|---|---|
| art indices | `offset.body` `parseInt("169000",16)`, `+14336` per card | `REC + 0` | 9792 B, 8bpp, 102-byte rows |
| art CLUT | `offset.header` `1488448` = 0x16B640, `+14336` per card | `REC + 9792` | 512 B, 256 x u16 BGR555 LE |

`config: {width:102, height:96, num_colors:256, keep_black:true, clear_before_render:true}`;
`chunks: [{width:102, height:96, data:(0,0)-(102,96), canvas:(0,0)-(102,96)}]`, `data_width 102`.
**Nothing else in the record is touched** — the baked title at `REC+10304`, the thumbnail at
`REC+10976` and the `REC+12384..14336` zero pad all keep their stock bytes.

### Tab 2 "Small Image" — 40x32 thumbnail, **both copies**

| what | tool config | WA_MRG offset | size |
|---|---|---|---|
| thumb indices, copy A | `offset.body_lil` `0`, `+2048` per card | `0x800*(id-1)` | 1280 B, 8bpp, 40-byte rows |
| thumb CLUT, copy A | `offset.header_lil` `1280`, `+2048` per card | `0x800*(id-1) + 1280` | 128 B, 64 x u16 |
| thumb indices, copy B | `aditionals: [14336*(id-1) + 0x16BAE0]` | `REC + 10976` | 1280 B |
| thumb CLUT, copy B | `aditionals: [14336*(id-1) + 1490912]` (0x16BFE0) | `REC + 12256` | 128 B |

`config: {width:40, height:32, num_colors:64, keep_black:true}`, `bpp:1`, `data_width 40`.
The site derives copy B's address from copy A's: `14336*Math.floor((off - base)/2048) + 0x16BAE0`.
So unlike the per-card tool, **the bulk tool keeps the two thumbnail copies in sync automatically**.
The 640 bytes of `FF` padding after copy A (`0x800*(id-1)+1408 .. +2048`) are left alone.

Verified on the real disc: the two copies are byte-identical for all 722 cards
(`card_art.py info --wa WA_MRG.MRG --ids 1-722` → *0 mini-copy mismatch(es), 0 dirty pad(s)*).

### Tab 3 "Save Panel"

`saveEditedFile()` → `new Blob([dataviewWa.buffer])` → `saveAs(blob, filenameWa)`. The whole
37,748,736-byte file comes back; you then have to rebuild the ISO yourself. A `POST api/v2/tools`
with `tipo: 36` is fired at the same time — analytics only, no image data leaves the browser.

## 2. Which files go in the zip (`formatID`)

    formatID(name):
        name contains "\" or "/"  -> reject     (so: no folders, root-level entries only,
                                                 and JSZip's directory entries are dropped)
        n = parseInt(name.toLowerCase())        (leading integer; "0523.png" -> 523)
        return 1 <= n <= 722 ? n : false

Consequences, all real:

* Extension is **never checked**. `5.txt` passes `formatID`, gets handed to `<img>`, `onload` never
  fires and `onerror` is not handled — **the batch stalls at that entry forever** (the "Processing
  n/N" counter only advances from the converter's `update:image` event). Same for a corrupt PNG.
* `1x.png`, `1 (copy).png` and `1.png` all map to card 1; the last entry in zip order wins.
* Names that don't start with a digit (`mini_1.png`, `card1.png`) are silently skipped.
* Ids outside 1..722 are skipped, so nothing can scribble outside the card tables.

## 3. Image handling — sizing and quantisation

**No resizing.** `paintCanvas()` does `putImageData(<cleared>)` then `ctx.drawImage(img, 0, 0)` on a
canvas that is exactly `width x height`. An oversized PNG is **cropped to its top-left 102x96 (or
40x32)**; an undersized one leaves the rest fully transparent. The page's own instructions ("all the
files should be indexed to 255 colors with a size of 102px x 96px") are advisory — nothing enforces
them.

**Quantiser** (`ImageConverter.createHeader` / `createBody`, identical to the per-card tool's):

1. every pixel truncated to 5 bits per channel (`8*floor(c/8)`), alpha flattened to 0 or 255;
2. `keep_black`: an *opaque* (0,0,0) becomes (8,8,8) — for the histogram only, not for the lookup;
3. popularity histogram keyed on the truncated RGB (alpha taken from the first sighting), sorted by
   count descending, top `num_colors` kept, short palettes padded by repeating the **most frequent**
   entry, then the palette is re-sorted by `r<<16 | g<<8 | b`;
4. each pixel maps to the nearest **opaque** palette entry by Euclidean RGB distance, `<=` so ties go
   to the *last* match; transparent pixels take the first slot whose alpha is 0. No dithering.

Quirk worth knowing: if the image has transparent pixels but no alpha-0 colour survived into the
palette, the JS leaves its running index `n` at the **previous pixel's** value — a smear rather than
a defined colour. `card_art.py` reproduces this.

**CLUT writer** (`bt`, the shared `vt` header path):

    r,g,b,a  ->  u16 = (a > 0 ? 1 : 0)<<15 | (b>>3)<<10 | (g>>3)<<5 | (r>>3)
    opaque (0,0,0) is bumped to (8,8,8) again here

**This sets STP=1 on every opaque entry**, and that is *not* what the stock disc looks like. Measured
over all 722 cards: 675 art CLUTs have exactly one STP-set entry, 36 have two, and entry 0 is `8000`
(opaque black) on 719 of 722; every other entry has STP=0. Same for the thumbnail CLUTs (696 with
exactly one). So a card imported with this tool has 255 semi-transparency-flagged entries where stock
has none. Harmless as long as the card sprite is drawn without ABE — which is how the library page
draws it — but it is a real deviation, and it means a tool-edited card is never byte-identical to a
re-encode of its own stock art.

(This also corrects `image-specsmix/README.md` §1, which says "stock data has STP set on all opaque
entries" — it does not.)

## 4. What the game does with it

Unchanged from the per-card tool; see `image-specsmix/README.md` §5 and findings **F125** / **F136**:

* the 7-sector record is CD-DMA'd whole into `gLibrary_aCardArtRecord` (0x801DC000) and
  `LoadImage` (0x8007F978) uploads art → VRAM (256,256,51,96), CLUT → (512,240,256,1),
  title → (256,352,24,14), thumbnail bytes → (312,256,8,88);
* the single-sector thumbnail at `0x800*(id-1)` is what the deck/trunk lists and the duel hand
  fetch (one sector per card, no need to touch the 7-sector record); its reader is a computed
  `id-1` seek and is still unidentified.

Limits the format imposes: 256 colours for the art, 64 for the thumbnail, 15-bit BGR555 with one
semi-transparency bit, fixed 102x96 / 40x32 geometry, and 722 ids.

## 5. Recomp options

* **Art + title** are already replaced natively by `src/psx_card_skins.c`, which jumps `LoadImage`
  (0x8007F978) through a stub in reclaimed RAM and substitutes a PNG-derived source. A bulk zip
  importer is therefore a *content* problem, not a patch problem: point the skin loader at a
  directory of `<id>.png` and let it median-cut them at load time, which beats the site's popularity
  quantiser on quality for free.
* **Thumbnails** have no native path yet. Two options: (a) once the deck-screen thumbnail
  `LoadImage` rect/caller is measured, extend `psx_card_skins.c` the same way; (b) until then, patch
  the disc image offline — `scripts/card_art.py import --what mini` writes both copies, which is
  exactly what the bulk tool does and what a hand-patch usually forgets.
* Nothing here is a code patch, so there is no `PSX_MOD_CONSTRUCTOR` / `psx_mod_write_code_word`
  work: every byte this tool touches is disc data, re-read from CD on every library/deck screen.
  A frame hook is the wrong shape; a load-time source swap or an offline `WA_MRG.MRG` rewrite is
  the right one.

## 6. Decomp findings (proposed)

* WA_MRG `REC+9792` (256 entries) and `REC+12256` (64 entries) | stock card CLUTs carry STP=1 on
  **entry 0 only** (`0x8000`, opaque black) — 675/722 art CLUTs have exactly 1 STP entry, 36 have 2,
  3 have 0, and entry 0 is `0x8000` on 719/722; the site's importers set STP=1 on every opaque entry
  | (amends the "STP set on all opaque entries" note attached to F125/F136)
* WA_MRG sectors 0..721 vs `REC+10976` | re-verified byte-identical for **all 722** cards (F136
  checked 5) | strengthens F136
* WA_MRG `REC+12384..14336` | zero on all 722 cards; no tool writes it | `WA_CardRecordPad`

## 7. Open questions

* The reader of thumbnail sector `id-1` and its VRAM rect (shared with `image-specsmix`).
* Whether the STP flood the tool writes is visible anywhere — needs a card drawn with ABE set
  (fusion/effect overlays?) to tell.
* Server side: only `POST api/v2/tools` (`tipo: 36`) and `POST api/v2/toolcontrol/validate`
  (the donor gate, which just redirects to `/extend/info/join` on 401). No image data is uploaded
  and nothing is downloaded — the whole conversion is client-side.
