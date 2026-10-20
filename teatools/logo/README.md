# MAIN LOGO tool

Route: `extend/tools/logo` (page title "TEA Online - Main Logo", UI version `V.240323`).
Inputs: **SU.MRG** (1,572,864..5,242,880 bytes) *or* **WA_MRG.MRG** (37,748,736..45,088,768 bytes) —
one at a time, picked from a fake disc tree; plus one or two PNG/JPG images (`image/*`, up to 20 MB).
The tool replaces the "Yu-Gi-Oh! Forbidden Memories" title picture (a 320x168 foreground) and the
hieroglyph wallpaper behind it (256x256), rewrites both CLUTs, and additionally rewrites a 46-byte
sprite-geometry record so the replacement image is not cropped. Everything is client-side; the file
comes back as a download with the original name. The analytics POST `api/v2/tools` is optional.
Script: `scripts/logo_image.py` (dump / import / restore / check / sprites). Notes: `NOTES-raw.md`.

Status: fully decoded and disc-verified against `/DATA/SU.MRG` (LBA 954) and `/DATA/WA_MRG.MRG`
(LBA 10102) extracted from the real disc; both images render correctly, dump->import round-trips
pixel-identically, restore is byte-exact; loaders, VRAM coordinates, CLUT coordinates and the
sprite-record format all found in the decomp.

## 1. Where the picture lives

The same picture exists twice, and the tool calls them "Main image" (SU.MRG, the boot/title screen)
and "Prologue image" (WA_MRG.MRG, the screen shown after the prologue).

| | Main image (SU.MRG) | Prologue image (WA_MRG.MRG) |
|---|---|---|
| foreground pixels | `0x10000`, 0x10000 B | `0xFD3800`, 0x10000 B |
| foreground CLUT | `0x30200`, 256 x u16 | `0xFEB800`, 256 x u16 |
| background pixels | `0x28000`, 0x8000 B | `0xFE3800`, 0x8000 B |
| background CLUT | `0x30800`, 16 x u16 | `0xFEBA00`, 16 x u16 |
| sprite descriptor block | `0x39000` (1 sector) | `0xFEC000` (1 sector) and `0xFD3000` (1 sector) |
| logo sprite group | `0x3923A` -> RAM `0x801AFA3A` | `0xFEC12A` -> RAM `0x801AF12A`; `0xFD312E` -> RAM `0x801AF12E` |
| in-file sector / disc LBA (front, fCLUT, back, bCLUT, block) | 32/986, 96/1050, 80/1034, 97/1051, 114/1068 | 8103/18205, 8151/18253, 8135/18237, 8151/18253, 8152/18254 (+ 8102/18204) |

The site's own constants (chunk `logo.2201f92e.js`, array `Xe`): `front.body 0x10000`,
`front.pallete 197120` (= `0x30200`), `back.body 0x28000`, `back.pallete 198656` (= `0x30800`),
`fix.address 234042` (= `0x3923A`); and `16594944` (`0xFD3800`), `16693248` (`0xFEB800`),
`0xFE3800`, `16693760` (`0xFEBA00`), `fix.address 16593198` (`0xFD312E`) and `16695594` (`0xFEC12A`).

**The two copies are not identical.** Verified byte-for-byte: the backgrounds and the background
CLUTs are the same; the foreground CLUTs differ only in bit 15 (STP) — SU has it set on 255 of 256
entries, WA on none — and the foreground pixels differ in exactly 3,099 bytes, all in rows 208..239,
where the "© 1996 KAZUKI TAKAHASHI" line is laid out one character differently.

## 2. Pixel formats

**Foreground** — an 8bpp 256x256 texture stored as **two 128-byte-wide column strips**:

    file rows   0..255  =  texture x   0..127
    file rows 256..511  =  texture x 128..255
    file offset = base + 0x8000*(u >= 128) + 128*v + (u & 127)

(the split is a consequence of the loader: it uploads one 0x8000-byte column at a time, see §4).
The site models this as a flat 128x512 image and cuts six rectangles out of it to build a 320x168
canvas — `logo_image.py dump` writes both views:

| data rect (128x512 view) | canvas rect (320x168) |
|---|---|
| (0,0) 128x168 | (0,0) |
| (0,168) 128x40 | (128,128) |
| (0,256) 128x128 | (128,0) |
| (0,432) 64x80 | (256,56) |
| (64,424) 64x56 | (256,0) |
| (64,480) 64x32 | (256,136) |

The remaining texture is **not** part of the tool's canvas and is never touched: the copyright line
(texture x 0..127, y 208..239) and "PUSH START BUTTON" (texture x 128..255, y 128..175).

**Background** — 4bpp, 128 bytes per row, 256 rows = 256x256, **low nibble = left pixel**.

**CLUT** — u16 little-endian BGR555: bits 0-4 R, 5-9 G, 10-14 B, bit 15 = STP (semi-transparency).
Only an all-zero u16 is transparent. Stock background CLUT (identical in both files):

    7FFF 1CE7 2D6B 39CE 4210 4631 4E73 56B5 5AD6 6318 6739 6B5A 6F7B 739C 7BDE 0001

Stock foreground CLUT, first 16 entries (SU / WA):

    SU 0x30200: 0000 8001 8001 8001 8001 8421 8022 8820 8003 8842 9040 8025 8443 8008 8009 8C42
    WA 0xFEB800: 0000 0001 0001 0001 0001 0421 0022 0820 0003 0842 1040 0025 0443 0008 0009 0C42

How the site writes a CLUT entry (`setNewHeader` / `setNewHeaderBG`): channels truncated to 5 bits,
**STP set on every non-black entry**, and for the *background* only, pure black is first bumped to
(1,1,1) so it becomes `0x8000` (opaque black) instead of `0x0000` (transparent). Consequence: a
background image imported through this tool can never contain a transparent colour. For the
foreground, clicking a pixel in the preview ("makeTransparent") zeroes the matching CLUT entries and
bumps any existing black entry to (8,8,8).

The image converter itself (`ImageConverter`, shared with the icon/font tools) truncates every
channel to 5 bits, maps opaque black to (8,8,8) (`keep_black: true`), keeps the `num_colors` most
frequent colours, sorts the palette by RGB value ascending, and maps each pixel to the nearest
remaining colour (transparent pixels to the first transparent entry). `scripts/logo_image.py`
reproduces all of this.

## 3. The 46-byte "fix"

`addCode()` runs on **every** save (`download()` calls it before `saveAs`), unconditionally and
regardless of whether you replaced any image, and writes 46 bytes — one whole sprite group — to every
address in `option.fix`. So simply loading a file and pressing Save patches the geometry. Verified
stock bytes at SU `0x3923A`, WA `0xFD312E` and WA `0xFEC12A` (all three are identical):

    stock  07 10 00 00  00 80 00 02 e0 09  00 18 18 43 e0 06  00 88 98 43 e0 06
                        00 38 d0 42 c0 12  80 80 a0 02 e0 09  80 00 10 00 e0 1f  00 00 00 00 e0 1f
    tool   07 10 00 00  00 80 00 02 e0 09  00 00 b8 42 e0 0c  00 88 98 43 e0 06
                        00 38 d0 42 e0 12  80 80 a0 02 e0 09  80 00 10 00 e0 1f  00 00 00 00 e0 1f

Only two of the seven quads change (decoded with the format in §4):

| # | stock | tool | meaning |
|---|---|---|---|
| 1 | screen (256,24) 64x32 from uv(192,192) | screen (256,0) **64x56** from uv(192,168) | the top-right corner of the canvas was simply not drawn |
| 3 | screen (256,56) **56**x80 from uv(128,176) | screen (256,56) **64**x80 | the right-most 8 pixel column was not drawn |

With the fix the seven quads tile exactly 320x168:

    (  0,  0) 128x128   (128,  0) 128x128   (256,  0) 64x56
    (  0,128) 128x40    (128,128) 128x40    (256, 56) 64x80
                                            (256,136) 64x32

So the "fix" is not a hack on game code — it is a geometry correction that makes the whole
320x168 canvas visible, which the stock art did not need because those areas were transparent.
`logo_image.py import --no-fix` skips it (the web tool has no such option).

## 4. What the game does with it

### 4.1 The loaders

Everything goes through the generic disc streamer `func_80014E1C(fileIdx, dbgName, sector, nSectors,
cb, a5, a6)` (`src/func_80014E1C.c` -> `func_80013998` -> `func_80013940`, LBA from
`gFile_anLba` 0x800E9EA8; `fileIdx 0` = WA_MRG.MRG, `1` = SU.MRG, sectors are file-relative). The
per-frame pump `func_80013C28` uploads a sector as a **64 x 16 halfword tile**, advancing y by 16
inside a 256-row band, then x by 64 — so one "column" is 64 halfwords x 256 rows = 16 sectors =
0x8000 bytes. That is exactly why the 8bpp picture is stored as two 128-byte-per-row strips.

**Main image** — `func_8005B85C` (0x8005B85C, currently filed as `src/register_handler.c`) does
`func_80014E1C(1, "M:/mrgSU/SU.mrg", 0, 115, cb=0x8005B64C, 0, 0)` = SU.MRG `0x00000..0x39800`.
The callback `0x8005B64C` (currently misnamed `select_reverb_preset`) is a 5-stage chunk dispatcher:

| stage | SU.MRG bytes | destination |
|---|---|---|
| 0 | `0x00000..0x20000` | VRAM (512,256), 4 columns -> x 512..768, y 256..512 |
| 1 | `0x20000..0x30000` | VRAM (896,0), 2 columns -> x 896..1024, y 0..256 |
| 2 | `0x30000..0x31000` | RAM `D_801DD000` |
| 3 | — | `LoadImage2(rect x=0 y=240 w=256 h=8, D_801DD000)`, then `0x31000..0x39000` -> `0x80180000` (the title/menu module) |
| 4 | `0x39000..0x39800` | RAM **`D_801AF800`** |

so **front pixels 0x10000 -> VRAM (640,256)-(768,512), tpage 0x1A**; **background 0x28000 -> VRAM
(960,0)-(1024,256), tpage 0x0F**; **front CLUT 0x30200 -> VRAM (0,241)**; **background CLUT 0x30800
-> VRAM (0,244)**. Callers: `Main_Init` (0x80012B50), `func_80043960` (boot), `Main_RunMenu`
(0x8002D588, the title screen).

**Prologue image** — `func_8002F630` (`src/func_8002F630.c`) is **story-script opcode 17**
(`gScript_apfnCommand` 0x80090C50, entry 17). It calls
`func_80014E1C(0, 0, 0x1FA7, 0x32, func_8002F4C0, 0, 0)` = WA_MRG sector 8103, 50 sectors =
`0xFD3800..0xFEC800`, then blocks on `func_800137E4()`. The callback `func_8002F4C0` has 3 stages:

| stage | WA_MRG bytes | destination |
|---|---|---|
| 0 | `0xFD3800..0xFEB800` | VRAM (448,256), 3 columns -> x 448..640, y 256..512 |
| 1 | `0xFEB800..0xFEC000` | RAM staging `D_8009B118` |
| 2 | — | `LoadImage2(rect x=0 y=0xF4 w=0x100 h=2)`, then `0xFEC000..0xFEC800` -> **`D_801AF000`** |

so **front 0xFD3800 -> VRAM (448,256), tpage 0x17 (8bpp)**; **background 0xFE3800 -> VRAM (576,256),
tpage 0x19 (4bpp)**; **front CLUT 0xFEB800 -> VRAM (0,244)**; **background CLUT 0xFEBA00 ->
VRAM (0,245)**. The same function then builds the objects and confirms every coordinate:

```c
call_800404CC_store54(slot, 0,0, 0, 0,0, /*tpage*/ 0x17, /*clut*/ 4, D_801AF000);
*(s32 *)(slot + 4) |= 0x1000000;                   /* 8-bit CLUT mode */
func_80040510(slot2, 0,     0, 0x140, 0xF0, 0, 0, 0x19, 0, 0xF5);   /* background */
func_80040510(slot3, 0x100, 0, 0x40,  0xF0, 0, 0, 0x19, 0, 0xF5);
```
`init_obj_id_pos_flags` (0x80040468) turns `p6 = 4` into CLUT x = `4 & 0x3F0` = 0, CLUT y =
`(4 & 0xF) + 0xF0` = 0xF4 = 244.

**The third block, WA `0xFD3000`** is *not* the prologue image's. It is the last sector of the boot
block loaded by `func_80043960` -> `func_80014E1C(0, 0, 0x1F85, 0x22, func_800434F4, 0, 0)` =
WA `0xFC2800..0xFD3800`; `func_800434F4` uploads `0xFC2800..0xFD2800` to VRAM (0,256) (tpage 0x10),
`LoadImage2(rect 256,240,256,4)` for its CLUT block at `0xFD2800`, and puts `0xFD3000..0xFD3800`
into `D_801AF000`. That picture is the **Konami / Shueisha legal screen**, not the logo (rendered and
checked). Its descriptor block happens to contain the same 46-byte 7-quad group at `+0x12E`, which
the tool rewrites too — see "Open questions".

### 4.2 The sprite/animation descriptor format

Three functions in the object system read the blob at `D_801AF000` / `D_801AF800`:

* `func_80041D60` (0x80041D60, matched C) — on an object's first tick it walks a **3-level LE-u16
  offset chain** through `obj->f54` (blob base) indexed by `obj->f67 / f68 / f69`, and stores the
  resulting **animation byte-stream** pointer in `obj->f50` (PC in `f58`, frame countdown in `f5A`).
  Same walk standalone: `func_8003A198`.
* `func_80041C8C` (0x80041C8C) — the stepper. A stream byte `< 0xF0` is a frame:
  `[u8 duration][u16 LE offset-to-sprite-group]`, and `obj->f4C = base + offset`. Bytes `0xF9..0xFF`
  are opcodes dispatched through `D_80090FEC` (index = `op ^ 0xFF`):
  `0xFF` stop (`func_8004141C`), `0xFE` loop to start (`func_80041428`), `0xFD` nop (`func_80041434`),
  `0xFC` jump to another stream (`accum_add_le16`, 0x8004143C), `0xFB` jump + toggle `f4 ^= 0x800000`
  (0x80041464), `0xFA` random jump among N (0x8004149C), `0xF9` set rotate/scale (0x80041534).
* **`func_8004158C` (0x8004158C..0x80041C8C, 0x700 bytes)** — the renderer, called from
  `run_active_rec_chain` (0x80040814) right after `func_80041D60`. It builds a `GsSPRITE` in the
  scratchpad at `0x1F800320` per quad and emits it through `func_80042188` (GsSortSprite family).

**Group header (4 bytes)** — `rec[0]` = sprite count, `rec[1]` = flags (`0x10` = 10-bit screen
coordinates, `0xE0` = enable the per-sprite tpage/CLUT override fields), `rec[2]` = tpage offset
added to `obj->f66` (doubled in 8bpp mode), `rec[3]` = CLUT nibble offset (`lo << 4` on x, `hi` on
y), applied only when `obj->f8 & 0x20`. The logo group's header is `07 10 00 00`.

**Sprite record (6 bytes)**:

    byte 0 : screen X low 8 bits          (signed 8-bit, or low 8 of a signed 10-bit if rec[1]&0x10)
    byte 1 : screen Y low 8 bits
    u16 A  = bytes 2..3 LE
               bits  0.. 4  U / 8      -> GsSPRITE.u = bits*8 + obj->f5E
               bits  5.. 9  V / 8      -> GsSPRITE.v = bits*8 + obj->f5F
               bits 10..12  tpage delta (only when rec[1] & 0xE0)
               bits 14..15  screen X bits 8..9
    u16 B  = bytes 4..5 LE
               bits  0.. 3  CLUT index  (only when rec[1] & 0xE0)
               bits  5.. 8  (W/8) - 1  -> w = ((B>>5)&0xF)*8 + 8      (8..128)
               bits  9..12  (H/8) - 1  -> h = ((B>>9)&0xF)*8 + 8      (8..128)
               bits 14..15  screen Y bits 8..9

Final position = object screen position + (x,y), clipped to 320x240 (0x140 x 0xF0). Decoding the
stock logo group with this gives exactly the six chunks the site's UI uses (plus the two
half-covered ones of §3), which is the independent proof that both the format and the
two-column-strip file layout above are right. `logo_image.py sprites` prints it.

### Consequences / limits

* Quad width and height are limited to 8..128 in steps of 8, and u/v to 0..248 in steps of 8, so the
  picture can never be larger than 256x256 of texture, and the seven quads cannot cover more than
  320x168 without adding an eighth record (which would move every following group in the block).
* 256 colours for the foreground and 16 for the background are hard limits (VRAM CLUT rows).
* Colour index 0 is not special — transparency is "CLUT entry == 0x0000".
* Changing the sprite group changes it for **every** object that references that group in the same
  blob, and the blob is one 2048-byte sector, so records cannot be resized.

## 5. Recomp options

* **Data-only, easiest**: patch the four regions in the disc image the recomp streams (SU.MRG
  `0x10000` / `0x30200` / `0x28000` / `0x30800`, WA_MRG `0xFD3800` / `0xFEB800` / `0xFE3800` /
  `0xFEBA00`). Nothing in the EXE has to change. `scripts/logo_image.py import` already does it.
* **Runtime swap**: both pictures land in VRAM through the pump's `f46 == 2` path
  (`func_80013C28` at 0x80013E6C..0x80013EFC) which calls `LoadImage2` once per sector out of the
  streaming buffer. A `LoadImage`/`LoadImage2` source-swap stub keyed on the destination rect
  (448,256) / (640,256) — the same trick `psx_card_skins.c` uses — lets a host-supplied 256x256
  RGBA image be quantised and uploaded instead, without touching the disc. Boot/one-shot loads, so
  no per-frame re-assert is needed; just re-run on each load.
* **The geometry "fix"**: the 46 bytes live in a disc-loaded sector (`D_801AF000` /
  `D_801AF800`), so a base-EXE `PSX_MOD_CONSTRUCTOR` patch would be wiped. Use the standard
  frame-hook + stock-word check idiom against RAM `0x801AF12A` / `0x801AF12E` / `0x801AFA3A`
  (compare the stock 46 bytes, write the fixed ones), or better: skip it entirely and instead give
  `func_8004158C` a native path — it already reads w/h per quad, so a mod that supplies its own
  group in reclaimed RAM and points `obj->f4C` at it is cleaner than editing the disc sector.
* **Native replacement**: because the seven quads are just a tiling of one texture page, a recomp
  mod can ignore them and draw a single full-resolution 320x168 (or higher) host texture in the
  title screen's draw pass; the only game-side requirement is that the stock quads stop being
  emitted (set `rec[0] = 0`, or skip the object).

## 6. Decomp findings (proposed)

- `0x8005B85C` | calls `func_80014E1C(1, "M:/mrgSU/SU.mrg", 0, 115, 0x8005B64C, 0, 0)`; called from `Main_Init`, `func_80043960` and `Main_RunMenu` | `Title_LoadSuMrg` (currently mis-filed as `src/register_handler.c`)
- `0x8005B64C` | 5-stage SU.MRG chunk dispatcher: `0x00000..0x20000` -> VRAM (512,256); `0x20000..0x30000` -> VRAM (896,0); `0x30000..0x31000` -> `D_801DD000` then `LoadImage2(0,240,256,8)`; `0x31000..0x39000` -> module at `0x80180000`; `0x39000..0x39800` -> `D_801AF800` | `Title_LoadSuMrgStage` — **currently named `select_reverb_preset`, which is wrong** (same class of error as F145's `select_sound_preset`)
- `0x8002F630` | story-script opcode 17 (`gScript_apfnCommand[17]`): `func_80014E1C(0, 0, 0x1FA7, 0x32, func_8002F4C0)` = WA_MRG `0xFD3800` + 50 sectors, then `func_800137E4()` | `Script_ShowLogoPicture`
- `0x8002F4C0` | 3-stage callback: `0xFD3800..0xFEB800` -> VRAM (448,256) tpage 0x17 8bpp; CLUT sector -> `LoadImage2(0,244,256,2)` (256-colour CLUT at VRAM (0,244), 16-colour at (0,245)); `0xFEC000..0xFEC800` -> `D_801AF000`; then spawns the logo object (tpage 0x17, CLUT (0,244)) and two background quads (tpage 0x19, CLUT (0,245)) | `Logo_LoadPictureStage`
- `0x800434F4` | boot-block callback for `func_80014E1C(0,0,0x1F85,0x22,...)`: WA `0xFC2800..0xFD2800` -> VRAM (0,256) tpage 0x10 (the Konami/Shueisha legal screen), CLUT block -> `LoadImage2(256,240,256,4)`, `0xFD3000..0xFD3800` -> `D_801AF000` | `Boot_LoadLegalScreenStage`
- `0x801AF000`, `0x801AF800` | the two one-sector sprite/animation descriptor blobs (`obj->f54`) | `gSprite_aDescBlobA` / `gSprite_aDescBlobB`
- `0x8004158C` (extent `0x8004158C..0x80041C8C`, `config/function_ranges.txt` currently shatters it into ~20 bogus entries) | the sprite-group renderer: 4-byte group header (count, flags, tpage delta, CLUT nibbles) + N 6-byte quads (see §4.2 for the full bit layout), emits `GsSPRITE` from scratchpad `0x1F800320` via `func_80042188` | `Sprite_DrawGroup`
- `0x80041C8C` | animation-stream stepper: `[u8 duration][u16 group offset]`, opcodes `0xF9..0xFF` via `D_80090FEC` | `Sprite_StepAnim`
- `0x80041D60` | 3-level u16 offset-chain walk (`f67/f68/f69`) resolving a stream in the descriptor blob | `Sprite_ResolveAnim`
- `0x8004143C` / `0x80041464` / `0x8004149C` / `0x80041534` / `0x8004141C` / `0x80041428` / `0x80041434` | animation-stream opcodes `0xFC` (jump), `0xFB` (jump + flag toggle), `0xFA` (random jump), `0xF9` (rotate/scale), `0xFF` (stop), `0xFE` (loop), `0xFD` (nop) — **`accum_add_le16` / `accum_add_le16_xor_flag` are misnomers, they are not accumulators** | `Sprite_AnimOpJump` etc.
- SU.MRG `0x10000` / `0x30200` / `0x28000` / `0x30800`; WA_MRG `0xFD3800` / `0xFEB800` / `0xFE3800` / `0xFEBA00` | the title picture: 8bpp 256x256 stored as two 128-byte-wide column strips + 256-colour BGR555 CLUT, and a 4bpp 256x256 wallpaper + 16-colour CLUT; the 320x168 logo is 7 quads of the 8bpp page | (facts)

## 7. Open questions

* The header of a descriptor blob is a nest of u16 offset tables whose *lengths* are not derivable
  from the table itself; `func_80041D60` only ever indexes it with `f67/f68/f69`, so the number of
  animations / sequences per blob is not statically recoverable without the callers' index values.
  `logo_image.py sprites` therefore decodes a group at a known address instead of walking the header.
* The tool rewrites the 7-quad group in **both** WA_MRG descriptor blobs, but `0xFD3000` belongs to
  the boot legal screen (texture WA `0xFC2800`), whose art is *not* replaced. Applying the geometry
  fix there widens two quads over texture areas the legal screen leaves blank; whether that is
  visible in game was not tested (it should only ever un-hide transparent pixels of that texture).
* Bits 10..13 of `A` and bits 0..4 / 13 of `B` are inert for this group (`rec[1] & 0xE0 == 0`);
  their behaviour under the per-sprite override flag is read from the disassembly, not observed.
* SU.MRG `0x30400` and `0x30600` are two more 256-entry CLUTs uploaded to VRAM rows 242 and 243 by
  the same `LoadImage2`; which assets use them was not chased.
* The site does nothing server-side: `api/v2/tools` is a usage counter, `api/v2/pops` /
  `api/v2/comment` are the news and comment boxes.
