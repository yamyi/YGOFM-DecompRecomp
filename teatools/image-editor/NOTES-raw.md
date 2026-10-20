# image/editor — raw notes

Session: 2026-09-04.

## The chunk is a shell

`site/js/extend/tools/image/editor.79555abd.js` is 10,450 bytes and contains no offsets, no
`DataView`, no `getUint8`/`setUint8`, no `saveAs` of a game file:

    grep -c "getUint8\|setUint8\|setUint16\|DataView\|accepted:\|minsize" pretty.js   -> 0

Its whole component is:

    O = {name:"ImageEditor",
         components:{ToolEditorLayout, FullLoader, ToolPresentation, Modal, TextureIndexer},
         data:{dataviewWa:null, isLoading:false}, methods:{}}

`dataviewWa` is declared and only ever `console.log`ged by a watcher — dead code copied from the
byte-patching tools' boilerplate. The template mounts

    <Modal mode="full" title="Image Editor & Indexer">
        <TextureIndexer @save="$emit('create', true)"/>
    </Modal>

and the page-level `saveChange()` does `POST api/v2/tools {version, tipo:46, data:<ts+rand>}`.
`validateUser()` -> `POST api/v2/toolcontrol/validate`; on 401 the browser is sent to
`/extend/info/join`, and a 3 s interval destroys the editor and clears `<body>` until it passes.

Presentation text (verbatim):

> With this tool you will be able to edit and index images for PSX Forbidden Memories. It allows you
> to resize, crop, apply effects, and index colors perfectly suited for the game. You can easily load
> your images by clicking the button, dragging and dropping them into the workspace, or most
> importantly, by simply pasting them using Ctrl + V.

## TextureIndexer lives in chunk-common, module "5191"

    grep -rl 'n("5191")\|a("5191")' */site/js/extend
      image-builder/site/js/extend/tools/image/builder.cf5d5334.js
      image-editor/site/js/extend/tools/image/editor.79555abd.js
      image-specsmix/site/js/extend/tools/image/cards.0ad4f385.js

Usages:

    image/builder  : <TextureIndexer showDownload=false
                        outputWidth=selSettings.width outputHeight=selSettings.height
                        paletteColors=selSettings.colors @confirm=...>
    image/specsmix : <TextureIndexer showDownload=false
                        outputWidth=images[i].width||102 outputHeight=images[i].height||96
                        paletteColors=images[i].colors||256 @confirm=...>
    image/editor   : <TextureIndexer @save=...>          (all three props null => unlocked)

Component data (defaults): `widthLocal 64, heightLocal 64, colorsLocal 16, resizeAlgo "auto",
edgeSmoothing 0, ditherMode "none", bgRemovalMode "color", bgTolerance 15, eraserSize 3,
eraserHardness 60`.

    sizePresets   : 8x8, 40x32, 102x96, 320x168, 256x256
    colour presets: 16 (2ppb), 72 (1ppb), 256 (8bpp)
    zoomSteps     : 1, 1.5, 2, 3, 4, 6, 8

## Algorithms, as read out of the chunk

Resize kernels (`j`):

    box       k(t)=|t|<=.5           radius .5
    triangle  O(t)=1-|t|  (|t|<1)    radius 1
    catmullrom M(t) cubic            radius 2
    mitchell  D(t) B=C=1/3           radius 2
    lanczos2  L(t)=sinc(t)sinc(t/2)  radius 2
    lanczos3  S(t)=sinc(t)sinc(t/3)  radius 3
    gaussian  I(t)=exp(-t^2/(2*.8^2))radius 2.5
    "auto"    -> lanczos3 shrinking, nearest enlarging

`T()` resamples in premultiplied alpha, horizontally then vertically, unpremultiplying at the end
(alpha <= 1e-4 collapses to (0,0,0,0)).

Edge smoothing sigmas: `N = [0, .4, .8, 1.3]` -> separable Gaussian `U(sigma, radius)`.

Quantiser:

    F(rgba, n)  histogram: alpha < 128 => hasTransparency, pixel excluded.
                opaque pixels counted at full 8-bit RGB, key = r<<16|g<<8|b, Map insertion order.
                >20000 distinct => uniform subsample to exactly 20000.
    $(items,e)  median cut: pick the box with the MOST items (len>1), split on the widest of
                R/G/B, sort by that channel, cut at the count-weighted median (clamped to
                [1, len-1]); box colour = count-weighted mean, rounded.
    B(items,pal,5)  5 rounds of k-means (nearest by squared RGB, recentre on count-weighted mean),
                only applied when items.length > pal.length.
    q(...)      l = hasTransparency ? max(1, colors-1) : colors
                palette = hasTransparency ? [[255,0,255], ...boxes] : boxes
                transparentIndex = hasTransparency ? 0 : null      <-- index 0, magenta
                offset h = hasTransparency ? 1 : 0

Nearest lookup `W(r,g,b,pal,off)` uses `<` so the FIRST minimum wins.

Dither:

    none    W() directly
    ordered g = 255 / cbrt(max(2, pal.length));  bias = (H[row&3][col&3]/16 - .5) * g
            H = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
    floyd   7/16 right, 3/16 down-left, 5/16 down, 1/16 down-right; skipped for transparent pixels

Background removal (post-quantisation, on the index buffer):

    G()  re-index to free a palette slot when the palette is already 256 entries
    (colour fill) 4-connected flood from the clicked pixel, tolerance = pct * maxRGBdistance
    J()  (eraser) round brush, radius c, hardness l%; feathered through the same Bayer matrix.
         If there is no transparent slot yet: palette = [...palette, [255,0,255]] and
         transparentIndex = palette.length-1   <-- APPENDED here, unlike q() which PREPENDS.

PNG writer: hand-rolled. CRC32 table `f`, chunk builder `b(type, data)`, `y()` deflates with
`new CompressionStream("deflate")`. `x(n)` picks bit depth: `<=2 -> 1, <=4 -> 2, <=16 -> 4, else 8`.
Emits `IHDR` (colour type 3), `PLTE`, `tRNS` (`Uint8Array(i+1).fill(255)` with `[i]=0`) when there is
a transparent index, `IDAT` (filter byte 0 per row, sub-byte depths packed MSB-first), `IEND`.

## Script testing

    index_texture.py <card1 art as RGB> out.png --size 102x96 --colors 256 --dither none|ordered|floyd
        -> P mode, 102x96, 151 colours (the source only has 151 distinct after BGR555 expansion)
    index_texture.py ... --size 40x32 --colors 64 --resize lanczos3 --smooth 2
        -> P mode, 40x32, 64 colours
    index_texture.py <same art with a 20x20 alpha hole> out.png --size 102x96 --colors 256
        -> transparent index=0, palette[0] = [255,0,255], tRNS = 0, pixel (0,0) index 0
    card_art.py import --palette exact  accepts the resulting PNGs unchanged.

## Open

* `72 (1ppb)` — no format on the disc uses 72 colours.
* `320x168` and `8x8` presets: not matched to a texture in this session.
