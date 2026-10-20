# Image Builder tool

Route: `extend/tools/image/builder` (V.260705). Inputs: SLUS_014.11 or WA_MRG.MRG (`.11,.mrg`,
1,048,576..42,991,616 bytes) and an image (`image/*`, up to 20 MB). A generic "any paletted texture at any
offset" editor: you (or a shared preset) describe where an image lives — body offset, palette offset, width,
height, colours, bytes-per-row, 4/8 bpp — plus optional rectangles that map pieces of a texture onto a
canvas, and the tool renders it, lets you replace it with a quantised PNG, and downloads the file. Presets
are shared through the server (`GET api/v2/tools/images?version=`, `POST api/v2/tools/saveimage`,
`DELETE api/v2/tools/deleteimage`; signed session required, **not mirrored**), so the only built-in preset is
the empty "custom" one. There are no game-specific offsets in the chunk; the value of this folder is the
exact texture model, which the other three image tools instantiate.
Script: `scripts/raw_image.py` (export / import / restore / preset) with `scripts/presets/*.json`.
Status: model decoded, script verified against the thumbnail, font, card-art, card-thumb and card-frame images.

## 1. The texture model (`AdvancedImage` component)

`settings` (class `G`): `width`, `height` (canvas, px), `colors` (CLUT entries), `data_width` (bytes per
texture row; default 128), `body_offset` (accepts `0x..`, bare hex, or decimal), `pallete_offset` (decimal),
`bpp` (1 = one byte per pixel, 2 = two pixels per byte — the site's "bpp" is really pixels-per-byte).

`chunks` (class `V`): `{width, height, data:{ci:{x,y}}, canvas:{ci:{x,y}}}` — copy a `width x height` pixel
block whose top-left is at texture pixel column `data.ci.x` (for 4bpp images the site indexes **bytes**, so
`x` is `pixel/2`) and row `data.ci.y` to canvas position `canvas.ci`. Reading:
`byte = file[body + data_width*(data.ci.y + row) + data.ci.x + col]`; with `ppb 2` the low nibble is the
left pixel. Writing (`setNewBody`) is the inverse; `setNewHeader` writes the palette as
`lo = (G>>3 & 7)<<5 | R>>3`, `hi = (a>0)<<7 | (B>>3)<<2 | G>>6` — i.e. PSX 15-bit BGR555 with STP set on
every opaque entry, `0x0000` for transparent. `advancedOptions.aditionalPalletes` / `aditionalBodies` are
extra offsets that receive the same palette / pixels (for images that exist in several copies — see the card
frame's 7 duel-overlay copies in `../image-specsmix/README.md`). `movePallete` steps the palette offset by
`2*colors`, `toglePalleteHeader` previews the texture through another CLUT ("Choose a palette to edit
individually"), and `PalleteEditor` / `ColorHexEditor` / `ColorToneEditor` edit CLUT entries directly
(hex, HSL ramps, per-palette or global tuning).

Image input goes through `ImageConverter` (5-bit rounding, top-N histogram palette, nearest colour, no
dither, `keep_black` -> (8,8,8)) or the newer `TextureIndexer` modal (crop/resize with Lanczos/Mitchell/
bicubic/box, optional Bayer or Floyd-Steinberg dithering, background removal, size presets 8x8, 40x32,
102x96, 320x168, 256x256). `validateFile` refuses a preset whose `body + w*h/bpp` or `palette + 2*colors`
exceeds the file. Hints on the page: "Images that can already be edited in any #teaonline tool will not be
accepted" (for sharing), "Incomplete images will not be accepted", "Multiple images that share the same
palette must be built into the same image".

## 2. Known images expressed in this model (all verified on the disc)

| image | body | CLUT | w x h | ppb | colours | stride | notes |
|---|---|---|---|---|---|---|---|
| dialog portrait n | `0xF35000 + 2432*(n-1)` | body + 2304 | 48x48 | 1 | 64 | 48 | `image-thumbnail` |
| card art (id) | `0x169000 + 14336*(id-1)` | body + 9792 | 102x96 | 1 | 256 | 102 | `image-specsmix` |
| card title (id) | art + 10304 | (game ramp, not on disc) | 96x14 | 2 | 8 | 48 | 4bpp |
| card thumb (id) | art + 10976, copy at `0x800*(id-1)` | +1280 | 40x32 | 1 | 64 | 40 | two copies |
| text font | `0xB48000` | `0xB60800` | 256x168 | 2 | 16 | 128 | `image-gamefont` |
| UI icon sheet | `0xB50000` | `0xB60100 + 32*i` (i=24, 48 real) | 256x160 | 2 | 16 | 128 | boot block |
| card frame | `0xB63000` (+`0x75800*k`, k=0..6) | `0xB83A80 + 512*p` | 144x200 | 1 | 256 | 128 | chunked, `presets/card_frame_*.json` |
| `ImagePanel` default | `0x10FB000` | `0x110B000` | 320x160 shown as 128-wide | 1 | 256 | 128 | an 8bpp background (night temple scene) — the component's placeholder config |

`raw_image.py preset` prints the command lines; `raw_image.py export WA rb.png <params>` reproduced the
`image-gamefont` export byte-for-byte and the assembled card frame matches the site's chunk map.

## 3. What the game does with it

Depends on the image; each row above is loaded differently: the boot UI block (`func_80043960` ->
`func_80014E1C(0,0,0x1690,0x36,func_80043328)` -> `LoadImage2`), the card record (CD DMA to 0x801DC000 +
`LoadImage` rects, F125), the duel overlay copy for the terrain (`func_800179F4`, 235 sectors at
`0x16C6 + 235*terrain`), module-specific loads for the rest. Common facts: everything is PSX 4/8bpp with
BGR555 CLUTs, `0x0000` = transparent, opaque entries carry STP (bit 15), 4bpp packs the left pixel in the
low nibble, textures are stored with their VRAM row pitch (128 bytes = 64 VRAM words) rather than the
sprite width, which is why the site needs `data_width` and chunks.

## 4. Recomp options

- A generic asset layer for the recomp = this model: a manifest of `{file, body, clut, w, h, ppb, colours,
  stride, chunks[], copies[]}` entries (the JSON shape the site's presets already use) plus a PNG per entry,
  applied either by patching the streamed disc image at load time or by the `LoadImage`/`LoadImage2` source
  swap the card-skin mod uses (match on the rect, point `a1` at a host buffer). The three specific tools are
  then just manifest entries.
- If the community's shared presets matter, they have to be fetched with a logged-in session
  (`api/v2/tools/images`), which this pass did not do.

## 5. Decomp findings (proposed)

- (none beyond the entries in the three sibling folders; the builder itself carries no addresses)

## 6. Open questions

- The shared preset list (server-side) — probably contains offsets for backgrounds, the field textures, deck
  screens etc. that would be worth mirroring with an account.
- `0x10FB000` (sector 0x21F6) background: which screen uses it (it is the `ImagePanel` default, likely a
  leftover from the "background" tool).
