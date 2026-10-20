# FORBIDDEN MEMORIES TRAILER ENCODER (media/video)

Route: `extend/tools/media/video` (chunk `video.0b7c9dee.js`, login-gated). Input: **one `.mp4`**
(drag-and-drop or click; the accept list is literally `.mp4` and is matched on the filename suffix).
Output: a file always named **`MOVIE.STR`** — a raw stream of 2048-byte PSX STR sectors carrying
**MDEC BS v2** video at **320x240, 15 fps, sized for 2x CD**, no audio.

It is not a wrapper around a server encoder and not a WASM ffmpeg: the whole MDEC encoder — forward
DCT, quantiser, the PSX AC VLC table, the bit packer and the STR muxer — is plain JavaScript in the
chunk. That makes it the one tool here that is a *format converter* rather than a byte patcher, and
it is fully portable.

Script: `scripts/str_tool.py` (`info` / `check` / `decode` / **`encode`** / `extract`) — a port of
that encoder plus a matching MDEC decoder used to verify it. Status: decoded and disc-verified;
the port re-encodes the game's own frames at **~51 dB PSNR** and picks the same quantiser scale the
disc uses.

## 1. The target on the disc

| | |
|---|---|
| file | `/DATA/MOVIE.STR` |
| disc LBA | **202734** |
| size | **35,430,400** bytes = **17,300** sectors |
| geometry | 320x240, MDEC BS **v2**, quant scale 1..9 |
| layout | **5 back-to-back copies of the same 346-frame movie**, 3460 sectors each |

Per copy: 3028 Mode2 **Form1** video sectors (subheader `00 01 48 00` — file 0, channel 1, submode
0x48 = Data|RT) and 432 Mode2 **Form2** XA audio sectors (`01 01 64 01` — file 1, channel 1, submode
0x64 = Audio|Form2|RT, coding 0x01 = **stereo, 37.8 kHz, 4-bit XA-ADPCM**). Frames use 9 video
sectors (260 of them) or 8 (86), so 10 sectors per frame on average.

Copies 0–3 are byte-identical; copy 4 differs in **exactly one byte pair** — the last sector's
submode becomes `0xC8` (EOF flag set) instead of `0x48`. 346 frames at 15 fps = **23.07 s**.

### Sector header (the first 32 bytes of every video sector's 2048-byte user data)

| off | type | meaning | disc value |
|---|---|---|---|
| +0 | u16 | chunk magic | `0x0160` |
| +2 | u16 | "video id" / stream id | `0x8001` |
| +4 | u16 | chunk index within this frame | 0.. |
| +6 | u16 | **chunk count** for this frame | 8 or 9 |
| +8 | u32 | frame number, 1-based | 1..346 |
| +12 | u32 | frame's bitstream length in bytes, rounded up to 4 | |
| +16 | u16 | width | 320 |
| +18 | u16 | height | 240 |
| +20 | 8 B | copy of the frame header below | |
| +28 | 4 B | zero | |

The remaining **2016** bytes are the frame's payload; a frame is the concatenation of its `count`
chunks in index order.

### Frame header (first 8 bytes of the reassembled bitstream)

| off | type | meaning |
|---|---|---|
| +0 | u16 | number of 16-bit MDEC words (`(codes+2 rounded up to 64) / 2`) |
| +2 | u16 | `0x3800` magic |
| +4 | u16 | quantiser scale, 1..63 |
| +6 | u16 | version = **2** |

Then the VLC bitstream, packed 16 bits at a time MSB-first and stored **little-endian per 16-bit
word**. Per 8x8 block: a raw 10-bit DC, then (run, level) AC codes from the standard PSX MDEC table
(sign appended as one trailing bit, escape = `000001` + 6-bit run + 10-bit signed level = 22 bits),
then EOB = `10`. Blocks per macroblock are **Cr, Cb, Y00, Y01, Y10, Y11**; macroblocks are
**column-major** (all 15 rows of block-column 0, then column 1, ...). The stream ends with the 10-bit
marker `0111111111` (511).

## 2. What the tool accepts and writes

Everything runs off five component props (`ForbiddenMemoriesTrailerEncoder`), none of which the UI
exposes:

    width 320   height 240   fps 15   cdSpeed 2   maxDuration 22

1. **Frame grab.** The mp4 goes into a hidden `<video>`; the encoder seeks to `t = n/fps` for
   `n < floor(min(duration, 22) * 15)` frames (max **330**), waits for `seeked`, fills a 320x240
   canvas black and `drawImage`s the video **letterboxed, aspect preserved** (`scale = min(320/vw,
   240/vh)`, centred). Audio is never touched — the mp4's soundtrack is discarded.
2. **Colour.** BT.601: `Y = .299R + .587G + .114B` at full resolution; Cb/Cr from the **2x2 box
   average** of the RGB, stored interleaved as `[Cr, Cb]` pairs in a `width x height/2` plane.
3. **Encode.** For each frame: integer forward DCT (the chunk's fixed-point cosine matrix, two
   passes of `(sum + 4095) >> 13` with int16 wrap), then **try quantiser scale 1, 2, 3, ... 63 and
   keep the first that fits the frame's byte budget**. The quant table is the standard MDEC/JPEG-ish
   matrix with `q[0] = 8*2 = 16` and `q[i] = table[i] * scale`; coefficients are rounded half away
   from zero and clamped to [-512, 510].
4. **Mux.** Budget per frame = `2016 * floor(acc / fps)` sectors' worth where `acc += 75 * cdSpeed`
   each frame — i.e. at 15 fps / 2x CD, **exactly 10 sectors (20,160 bytes) per frame, always**.
   Each 2048-byte sector gets the header above with `chunk count = 10`.
5. **Download.** `MOVIE.STR`, always that name regardless of the input file.

Failure mode: if no quant scale 1..63 fits the budget the encoder throws
*"No fue posible codificar un frame dentro del presupuesto…"* and the run aborts.

## 3. How the tool's output differs from the disc's file

| | disc `/DATA/MOVIE.STR` | tool output |
|---|---|---|
| container | Mode2 Form1 video **+ interleaved Form2 XA audio** | video only, 2048 B/sector, no subheaders |
| sectors per frame | 8 or 9 video + XA | **always 10 video** |
| chunk-count field | 8 / 9 | 10 |
| frames | 346 (23.07 s), then 4 more identical copies | up to 330 (22 s), one copy |
| total | 17,300 sectors | ≤ 3,300 sectors |
| audio | stereo 37.8 kHz XA-ADPCM | **none** |

The sector *rate* is the same (10 sectors per frame either way), so timing and the game's frame
budget still work out — but the FMV loses its soundtrack, and the file is a flat payload stream, not
a disc image: putting it back needs an ISO rebuild (mkpsxiso or equivalent) that re-creates Mode2
Form1 subheaders and EDC/ECC. A 2048-byte-per-sector extraction of the stock file (which is what
UltraISO and `str_tool.py extract` give you, because the ISO directory records the size as
17300 x 2048) already **destroys** the XA sectors, since those carry 2324 payload bytes — so you
cannot round-trip audio through a flat `.STR` at all.

## 4. What the game does with it

The FMV player lives in the base EXE and is the standard libpsxav/libmdec pair.

**File LBA lookup.** SLUS holds seven ISO path strings at file 0x80F04..0x80F87 (RAM
0x80090704..0x80090787) with a pointer table at 0x80F8C (RAM 0x8009078C), resolved once into the
16-entry word table **`gFile_anLba` = 0x800E9EA8**:

| idx | RAM | file |
|---|---|---|
| 0 | 0x800E9EA8 | `\DATA\WA_MRG.MRG;1` |
| 1 | 0x800E9EAC | `\DATA\SU.MRG;1` |
| 2 | 0x800E9EB0 | `\DATA\MODEL.MRG;1` |
| **3** | **0x800E9EB4** | **`\DATA\MOVIE.STR;1`** |
| 4 | 0x800E9EB8 | `\DATA\SD_SE.DAT;1` |
| 5 | 0x800E9EBC | `\DATA\SD_BGM.DAT;1` |
| 6 | 0x800E9EC0 | `\DATA\MASTER.XA;1` |

**Stream table.** `D_8009151C`, a `{u16 sectors; u16 frames}` array; only entry 0 is populated.

| | |
|---|---|
| file offset | **0x81D1C** |
| RAM | **0x8009151C** |
| stock bytes | `08 0C 2F 01` = `{ sectors = 0x0C08 = 3080, frames = 0x012F = 303 }` |

`lookup_speed_and_start_read(idx=0, 1, speed=-1, 1, 0)` (0x8005C388) reads that entry, uses its
frame count in place of the caller's `-1`, sums the sizes of all preceding entries (0 here) to get a
byte offset, converts `gFile_anLba[3] + 0` to a `CdlLOC` with `CdIntToPos` (0x8007E600), and calls
`func_8005B8A0` with `t = CdPosToInt(loc) + 3080`:

```c
/* src/lookup_speed_and_start_read.c */
e = &base[idx];
if (e->f2 != 0) speed = e->f2;          /* 303 frames */
...
CdIntToPos_8007E600(D_800E9EB4 + total, buf, total);
t = CdPosToInt_8007E710(buf);
t += t2[idx].f0;                        /* + 3080 sectors */
func_8005B8A0(buf, arg1, speed, t, arg3, arg4);
```

`func_8005B8A0` (0x8005B8A0) then does the libmdec/libpsxav setup — `DecDCTReset(0)`,
`DecDCToutCallback(0x8005C1F4)`, `DecDCTvlcBuild(D_8009B498)`, `StSetRing(D_8009B498 + 0x11000, 0x14)`
(a 20-sector ring), `StClearRing()`, `StSetStream(mode, ring, 303, 0, cb)` — and drives
`str_stream_wait_and_decode_frame`, which pulls frames with `StGetNext` and decodes them with
`DecDCTvlc2` (0x800902A0). `func_8003594C` (0x8003594C) is the caller that arms the pipeline.

**Consequences (this is where the tool's odd UI text comes from):**

* The game only ever reads **3080 sectors** and only ever plays **303 frames** = **20.2 s** at
  15 fps. Everything past that — the last 380 sectors of copy 0 and *all four extra copies*,
  13,840 sectors ≈ 28 MB — is never touched by this code path. That is the "only the first 20s are
  considered, 2s are requested as buffer" note on the page: give it fewer than ~3080 sectors of
  stream and `StGetNext` starves before frame 303 arrives, which is the "infinite loop in the .str"
  the page warns about.
* 303 frames is a hard cap in `D_8009151C[0].f2`, not a property of the file. Changing that one u16
  changes the trailer length; changing `f0` changes how much is read.
* Nothing validates the dimensions — `DecDCTvlc2` decodes whatever macroblock count the VRAM upload
  expects, so 320x240 is fixed by the display code, not by the header.

## 5. Recomp options

* **Longer / shorter trailer:** patch the two u16s at RAM 0x8009151C (file 0x81D1C) once at startup —
  base-EXE data, so a `PSX_MOD_CONSTRUCTOR` plus a single
  `psx_mod_write_code_word(0x8009151C, (frames << 16) | sectors)` is enough (little-endian: low
  half-word is the sector count). Raising `frames` past 346 with the stock disc starves the stream;
  raise `sectors` at the same time and re-author the file.
* **Replacing the movie:** it is disc data, so there is no code patch — rewrite `/DATA/MOVIE.STR` in
  the disc image (`scripts/str_tool.py encode` produces the payload; the ISO rebuild has to add the
  Mode2 subheaders). If you want the audio back you must re-interleave XA sectors yourself; the
  tool cannot.
* **Native replacement (the better mod):** the recomp does not need MDEC at all. `func_8005B8A0` /
  `str_stream_wait_and_decode_frame` are the only entry points; redirecting them to a host-side video
  decoder that blits into the same VRAM rect (and honours the 303-frame / `D_8009B063` abort flag)
  removes the 3080-sector budget, the 20 s cap, the 320x240 limit and the quantiser entirely. The
  frame-hook + stock-word-check idiom from `src/psx_free_duel_rows.c` is not needed here because
  none of these addresses live in a disc-loaded overlay.

## 6. Decomp findings (proposed)

* `gFile_anLba` 0x800E9EA8 | index -> ISO file, from the name pointer table at 0x8009078C:
  0 WA_MRG.MRG, 1 SU.MRG, 2 MODEL.MRG, **3 MOVIE.STR**, 4 SD_SE.DAT, 5 SD_BGM.DAT, 6 MASTER.XA |
  document the indices on `gFile_anLba`
* 0x8009151C (file 0x81D1C), stock `08 0C 2F 01` | the FMV stream table `{u16 sectors; u16 frames}`;
  only entry 0 is used: read 3080 sectors of `/DATA/MOVIE.STR`, play 303 frames (20.2 s at 15 fps) |
  `gMovie_aStreamEntry`
* `func_8005B8A0` 0x8005B8A0 | MDEC/STR playback bring-up: `DecDCTReset` / `DecDCToutCallback` /
  `DecDCTvlcBuild(D_8009B498)` / `StSetRing(D_8009B498+0x11000, 20)` / `StSetStream(..., frames, ...)`
  then `str_stream_wait_and_decode_frame` | `Movie_PlayStream`
* `lookup_speed_and_start_read` 0x8005C388 | resolves `gMovie_aStreamEntry[idx]` to a `CdlLOC` from
  `gFile_anLba[3]` and starts playback | `Movie_StartEntry`
* `/DATA/MOVIE.STR` LBA 202734, 17300 sectors | **five identical 3460-sector copies** of one
  346-frame 320x240 MDEC BS v2 movie (copy 4 differs only by the EOF submode on its last sector);
  each copy is 3028 Form1 video sectors + 432 Form2 XA sectors (stereo 37.8 kHz 4-bit ADPCM, file 1
  channel 1). The game reads only the first 3080 sectors of copy 0, so ~28 MB of the file is dead
  weight | facts for `notes/research/findings.md`

## 7. Open questions

* **Why five copies?** The stream table reads only 3080 sectors from `gFile_anLba[3]`, and nothing
  else in the EXE references the file. Candidates: a mastering artefact, a seek-latency hedge that
  was never wired up, or a second entry point in a screen module that was not searched. Cheap to
  settle by tracing `gFile_anLba[3]` reads at runtime.
* Where the XA channel is switched on — `func_8005B8A0`'s `StSetStream` first argument comes from
  `D_8009B060` (the `clearDisplay` flag in the current decomp naming), which looks mis-named; the
  audio channel/file selection was not traced.
* The exact 22 s vs 20 s discrepancy in the tool: the props say `maxDuration: 22` and the code uses
  22 for both the seek loop and the frame count (330 frames), while the page text says 20 s + 2 s of
  buffer. The game's 303-frame cap makes the extra 27 frames unreachable, so the text describes the
  intent and the code over-delivers.
* Server side: `POST api/v2/toolcontrol/validate` (donor gate; 401 -> `/extend/info/join`) and
  `POST api/v2/tools {tipo: 47}` on download. No video data crosses the network.
