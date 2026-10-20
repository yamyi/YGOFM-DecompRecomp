# IMAGE EDITOR & INDEXER

Route: `extend/tools/image/editor` (chunk `editor.79555abd.js`, 10,450 bytes, login-gated).
Input: any raster image the browser can decode (`accept="image/*"`, drag-and-drop, file picker, or
**Ctrl+V paste**). Output: an **indexed PNG** downloaded from the browser.

**This tool never touches a Forbidden Memories file.** It has no `.11` / `.mrg` / `.mcr` reader, no
offsets, no `saveAs` of a game file and no server round-trip. It is the site's shared image
pre-processor: crop, resize, quantise, dither, punch transparency, download. Its output is what you
then feed to the tools that *do* patch the game.

Script: `scripts/index_texture.py` (a port of the same pipeline). Status: decoded; the port produces
indexed PNGs with the same palette/transparency conventions, tested against real card art pulled off
the disc.

## 1. What the page actually is

The whole chunk is a shell:

```
ImageEditor (this chunk)
  └─ Modal(mode:"full")
       └─ TextureIndexer            <-- module "5191" of chunk-common.147d0f81.js
            props: imageData=null, showDownload=true,
                   outputWidth=null, outputHeight=null, paletteColors=null
            @save -> $emit("create") -> POST api/v2/tools {tipo: 46}   (analytics only)
```

`TextureIndexer` is shared, not exclusive to this route. Grepping the mirror, exactly three tools
embed module `5191`:

| tool | how it embeds it |
|---|---|
| `image/editor` (this one) | standalone, `showDownload:true`, size and colour count **unlocked** |
| `image/specsmix` (`image-specsmix/`) | `showDownload:false`, `outputWidth/Height/paletteColors` locked to the slot being edited (102x96/256 for card art), `@confirm` hands the data URL straight to the tool's own `ImageConverter` |
| `image/builder` (`image-builder/`) | same, locked to `selSettings.width/height/colors` |

So the editor route is "TextureIndexer with nothing locked and a download button". The size presets
it offers are the game's own texture sizes — `8x8`, `40x32` (card thumbnail), `102x96` (card library
art), `320x168`, `256x256` — and the palette presets are `16 (2ppb)`, `72 (1ppb)`, `256 (8bpp)`.
(`72` is odd: the real 1-byte-per-pixel consumers on this site are 64-colour thumbnails and
256-colour art. Treat it as a UI typo, not a format.)

## 2. The pipeline (chunk-common module 5191)

Source image → optional crop → resize → optional edge smoothing → quantise → optional dither →
optional background removal → indexed PNG.

**Crop.** Free or ratio-locked to the output size; `x,y,w,h` in source pixels.

**Resize.** Separable filtered resample in premultiplied alpha, kernels (`j` in the chunk):

| option | kernel | radius |
|---|---|---|
| `box` | area / box | 0.5 |
| `triangle` | bilinear | 1 |
| `catmullrom` | bicubic | 2 |
| `mitchell` | Mitchell–Netravali B=C=1/3 | 2 |
| `lanczos2` / `lanczos3` | sinc·sinc | 2 / 3 |
| `gaussian` | σ=0.8 | 2.5 |
| `nearest` | point sample | — |
| `auto` (default) | **lanczos3 when shrinking, nearest when enlarging** | |

**Edge smoothing.** A separable Gaussian applied before quantisation, σ from the fixed table
`N = [0, 0.4, 0.8, 1.3]` (UI: None / Light / Medium / Strong).

**Quantiser** (`F` → `$` → `B` → `q`), and this is where it differs sharply from the byte-patching
tools' `ImageConverter`:

1. `F()` histogram — a pixel with **alpha < 128 counts as transparent** and is excluded; opaque
   pixels are counted at **full 8-bit RGB** (no 5-bit truncation). If more than 20,000 distinct
   colours survive, the list is uniformly subsampled to 20,000.
2. `$()` **median cut** — repeatedly split the box holding the **most entries** (not the largest
   volume) along its longest R/G/B extent, at the count-weighted median; each final box becomes its
   count-weighted average colour.
3. `B()` **5 rounds of k-means** refinement over the histogram, but only when there were more
   distinct colours than palette slots.
4. `q()` assembly — if the image had any transparency, the palette becomes
   `[[255,0,255]] ++ colours` and **index 0 is the transparent slot, magenta**; the real colours get
   `max(1, colors-1)` slots and start at index 1. With no transparency there is no reserved slot.

**Dither.** `none` (nearest by squared RGB distance, first match wins ties), `ordered`
(Bayer 4x4 `H`, amplitude `255 / cbrt(max(2, palette))`, bias `(m/16 - 0.5)`), or `floyd`
(Floyd–Steinberg 7/3/5/1, error not propagated into transparent pixels).

**Background removal.** Two brushes over the *indexed* result: a colour flood fill (4-connected, from
the clicked pixel, tolerance as a % of the max RGB distance) and a soft round eraser (radius +
hardness, feathered through the same Bayer matrix). If the image had no transparent slot, one is
created — and note that here it is **appended at the end** of the palette (`[...palette,[255,0,255]]`),
not prepended, unless the palette is already 256 entries, in which case an unused index is recycled.

**Output.** A PNG built by hand in the chunk (its own CRC32 + chunk writer, deflate via the browser's
`CompressionStream("deflate")`): `IHDR` colour type **3** with bit depth 1/2/4/8 chosen from the
palette size, `PLTE`, `tRNS` (one fully transparent entry) when there is a transparent index, `IDAT`,
`IEND`. Rows are filter type 0 and sub-byte depths are packed MSB-first.

## 3. What consumes the output

Nothing in the game — this is a PNG factory. Its consumers are other tools in this repo:

* **`image/massive/cards`** (`../image-massive-cards/`): zip of `<id>.png`, 102x96 / 256 colours for
  library art, 40x32 / 64 colours for thumbnails.
* **`image/specsmix`** (`../image-specsmix/`) and **`image/builder`**: embed the indexer directly, so
  the "download and re-upload" step disappears.
* Every other `image/*` route on the site takes a plain PNG and runs its own `ImageConverter`.

Important mismatch to keep in mind when chaining: the indexer quantises at **full 8-bit RGB with
median cut + k-means**, but every byte-patching tool then re-quantises the PNG with the crude
5-bit-truncation popularity quantiser and writes BGR555. So the indexer's palette is *advisory* — it
mainly buys you good spatial resampling and a clean transparency slot, and the colour choice is
re-decided downstream. Feeding it exactly `num_colors` colours at exactly the target size makes the
downstream popularity histogram a no-op, which is the point of the "already indexed" advice on the
bulk tool's page.

## 4. Recomp options

Nothing to patch — there is no game byte here. The relevant carry-over into the recomp is the
*algorithm*: `src/psx_card_skins.c` already does its own PNG → palette conversion at load time, and
if you want the site's look reproduced exactly you would use median cut + 5 k-means rounds (this
chunk) rather than a popularity histogram. `scripts/index_texture.py` is the reference
implementation; it takes the same flags as the UI:

    ./index_texture.py in.png out.png --size 102x96 --colors 256
    ./index_texture.py in.png out.png --size 40x32  --colors 64 --dither floyd
    ./index_texture.py in.png out.png --size 64x64  --colors 16 \
        --crop 10,10,200,200 --resize lanczos3 --smooth 2

## 5. Decomp findings (proposed)

None — this tool reads and writes no game data.

## 6. Open questions

* What the `72 (1ppb)` palette preset is for. No format on the disc uses 72 colours; the 1-byte-per-
  pixel formats found so far are 64-colour (thumbnail) and 256-colour (art, frames, backgrounds).
* What `320x168` and `8x8` correspond to — the other size presets map cleanly onto card art and
  thumbnails, these two presumably onto backgrounds/UI sheets documented in `image-background/` and
  `image-builder/`.
* Server side: `POST api/v2/toolcontrol/validate` is the donor gate (401 → redirect to
  `/extend/info/join`); the route also destroys the editor every 3 s unless that call succeeds.
  `POST api/v2/tools {tipo: 46}` is fired on save. Neither carries image data.
