# BGMOV tool (moving / panning cutscene pictures)

Route: `extend/tools/image/bgmov` (V.220316). Input: WA_MRG.MRG (`.mrg`,
37,748,736..39,845,888 bytes) plus PNG/BMP images: layer 1 of the picture's own size
(512x160, 320x256, 512x256 or 344x256 -- shown in the page header), layer 2 320x160 (256
colours), "Light Layer" 320x160 (16 colours). Client-side; WA_MRG.MRG downloaded back.
Script: `scripts/bgmov.py` (wrapper over `../../image-background/scripts/cutscene_bg.py`
with `--mode mov`). Raw notes: `../image-background/NOTES-raw.md`.
Status: decoded, disc-verified, PNG round trip (layers 1/2/3) and byte-identical restore
tested on a copy, not yet built as a mod.

These are the pictures the camera pans across (wider or taller than the 320x160 screen). The
site lists 13 as 01..13; the game's picture number is NN = index - 1 (00..12), command
`F7 05 NN 02`. The records after NN 12 (from WA 0x1DA7000) are cutscene character sprite
sheets, not backgrounds.

## 1. The record

One picture = 113 sectors (0x38800 bytes):

    WA offset  = 0x1AC8800 + NN * 0x38800         (NN = 0..12)
    in-file sector = 0x3591 + NN * 0x71           disc LBA = 23815 + NN * 113
    (site: body 0x1AC8800 + 231424*(i-1); palettes 0x1B00800 / +512 / +1024)

| in-record | size | content |
|---|---|---|
| +0x00000 | 0x20000 | layer 1 strip: 1024 rows x 128 B, 8bpp; the picture is cut into 128-px columns 256 rows apart |
| +0x20000 | 0x10000 | layer 2 strip: rows 1024..1535, 8bpp, 320x160 in the static four-chunk layout (rows 1024 / 1280 / 1440) |
| +0x30000 | 0x08000 | layer 3 strip: rows 1536..1791, **4bpp**, 320x160 (as BGCOMP layer 3, rows +1536) |
| +0x38000 | 0x200 | CLUT 1 (256, no STP) |
| +0x38200 | 0x200 | CLUT 2 (256, entry 0 transparent; all-zero when the picture has no layer 2) |
| +0x38400 | 0x20 | CLUT 3 (16, entries 1..15 STP set; all-zero when no light layer) |

Layer 1 column k (k = 0..3) = strip rows 256k .. 256k+h, width min(128, w-128k). Per picture
(verified against the CLUTs on the disc -- `inspect` prints `clut2`/`clut3` counts):

| NN | layer 1 | layer 2 | light layer |
|---|---|---|---|
| 00 | 512x160 | - | yes |
| 01 | 320x256 | yes | - |
| 02 | 512x256 | - | - |
| 03 | 320x256 | yes | - |
| 04 | 512x256 | yes | - |
| 05 | 512x256 | yes | - |
| 06 | 320x256 | yes | yes |
| 07 | 512x256 | yes | yes |
| 08 | 320x256 | yes | yes |
| 09 | 344x256 | - | yes |
| 10 | 512x256 | - | yes |
| 11 | 512x256 | - | yes |
| 12 | 512x256 | - | yes |

(NN 00 is the hieroglyph wall with the hand; NN 01 is a 320x256 scene panned vertically.)

## 2. What the game does with it

Same loader (`func_8002DF2C` mode 2: stride 0x71, base 0x13BC -> sector `0x3591 + NN*0x71`,
callback `func_8002DDFC`). 112 pixel sectors = seven 16-sector columns streamed from VRAM
(0,256): x = 0,64,128,192 layer 1 (up to 512 px wide), x = 256,320 layer 2, x = 384 layer 3
(4bpp). CLUT sector -> (0,240) rows 240/241/242.

The pan itself is a second script command. The site's hint: put `F7 0B C0 00 A0 00 2C 01`
before `F7 05 00 02` -- opcode 0x0B with three u16 parameters (0x00C0, 0x00A0, 0x012C =
192, 160, 300) that set the movement (direction / speed / duration by the site's wording);
its handler (entry 0x0B of `gScript_apfnCommand`, 0x80090C50) was not traced. The site also
notes the picture byte can be `02` or `82`: `Script_OpShowImage` masks the parameter with
0xFFF, so bit 0x8000 changes something else (untraced).

## 3. Site details

- Same converter as BGCOMP (histogram at 5-bit precision, black -> (8,8,8), click-to-key for
  layers 2/3, STP bit set on written colours).
- The per-picture layout tables (`elems`, `elems2`, `elems3B`) are hard-coded in the page;
  they are reproduced in `cutscene_bg.py` (`MOV_L1_SIZE`, `MOV_HAS_L2`, `MOV_HAS_L3`).
- A stale chunk entry (`width:64,height:160` for the last layer-2 piece) is really 64x80
  (its data range is 80 rows); the script uses 80.
- `getPointer` prints the BCD byte of (index-1).

## 4. Recomp options

As for the static pictures: disc patch, or a `LoadImage2` source swap on rects
`(64k, 256+16j, 64, 16)` k = 0..6 / `(0, 240, 256, 4)` keyed on the picture code. A native
mod could also widen the pan range if the 0x0B handler is decoded (open).

## 5. Decomp findings (proposed)

- mode 2 of `func_8002DF2C` | moving pictures: 13 x 113 sectors from WA sector 0x3591; layer-1 size varies per picture (table above); layers 2/3 optional (all-zero CLUTs) | (disc fact)
- WA sector 0x3B52 (0x1DA7000) | after the 13 moving pictures: cutscene character sprite sheets with the same 128-B-row strip packing (different CLUT use) -- the `image-campaign-characters` tool's territory | (disc fact)

## 6. Open questions

- Script opcode 0x0B (pan parameters) and the meaning of bit 0x8000 in the picture code.
- How the game knows a picture's layer-1 extent (512 vs 320 vs 344 wide, 160 vs 256 tall):
  probably from the pan command, since the record itself has no header.
