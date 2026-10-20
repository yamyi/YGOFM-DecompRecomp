# Card Sleeves -- raw working notes (2026-09-04)

Tool chunk: `site/js/extend/tools/image/cardsleeves.1fee14ee.js` (component `BackgrounEdit`).
Helpers pulled from chunk-common: `5457` (chunk tables cardBg1/2/3, cardTransform1/2),
`1d4b` ImagePanel, `287d` ImageConverter, `93b5` PalleteEditor, `a240` FileReader.

## Constants in the JS

    FileReader slus: accepted ".11"  minsize 1782579.2 maxsize 2097152
    FileReader wa:   accepted ".mrg" minsize 36700160 maxsize 39845888
    FileReader img:  accepted "image/*" maxsize 20971520
    body_offset  = parseInt("B63000",16) = 11939840
    header_offset = 12075008 = 0xB84000 (+512*colorIndex, colorIndex 0..6)
    palleteConfig2 offset 12075456 = 0xB841C0 size 16   (row 8, colours 224..239)
    palleteConfig3 offset 12075488 = 0xB841E0 size 16   (row 8, colours 240..255)
    cicles = [0,481280,962560,1443840,1925120,2406400,2887680,3684352,4409344,5658624]
    images[0] dynamic 144x264 colors 72  move 0
    images[1] static  144x264 colors 72  move 72   (split 40 @72.. + 32 @160..)
    images[2] sleeve  144x200 colors 48  move 112
    ImagePanel(big):  width 144 height 200 num_colors 192 bytes_width 128 bytes_height 928 ppb 1
    ImagePanel(text): width 60 height 80 num_colors 16 pallete_offset 12075488 ppb 2
    cleanImage: 10240 bytes of zero at 0xB80000 + cicle (last cicle -16384)
    last cicle: body gets r = -16384, header does not
    positions (SLUS byte offsets): image 103476/103500 text 103624/103676 atk 104112/104132
      def 104252/104272 st 104396/104432 attr 104580/104600 ; fixPosition clamps x<=140 y<=196
    salvarSlus() calls setPositionValues() then downloads; salvar() downloads WA_MRG

## salvarEnImagen(header, headerBase, body, bodyBase)
    for each cicle n (index o):  r = (o == last) ? -16384 : 0
      index 0 (dynamic): setNewHeader(headerBase+n + {0,512,...,2560} [,3072 if hasExtraColor], header, move=0)
                         setNewBody(bodyBase+n+r, body, header)             # writes all pixels
      index 1 (static):  l = header[0..40) ; d = header[40..72)
                         setNewHeader(rows..., l, 72) ; setNewHeader(rows..., d, 72+40+48 = 160)
                         u = body.map(e => e<40 ? e : e+48)
                         setNewBody(bodyBase+n+r, u, [l, 48 blanks, d], false, 72)  # only opaque
      index 2 (sleeve):  setNewHeader(rows..., header, 112) ; setNewBody(..., body, header, true, 112)
    setNewHeader(off, pal, move): for each colour s: if r=g=b=0 && a!=0 -> 8,8,8
        lo = bits: g[2..4] r[0..4] ; hi = (r||g||b||a>0 ? 1 : 0) b[0..4] g[0..1]
        setUint8(off + 2*(s+move), lo) ; setUint8(off+2*(s+move)+1, hi)
    setNewBody(off, body, pal, writeTransparent=true, move=0):
        chunks = (index==2 ? cardBg3 : cardTransform1)
        for each chunk, for x in data.ci.x..cf.x, y in data.ci.y..cf.y:
            d = body[(x - data.ci.x + canvas.ci.x) + (y - data.ci.y + canvas.ci.y)*width]
            if pal[d].a != 0 || writeTransparent: setUint8(off + x + y*128, d + move)

ImageConverter.createHeader: per pixel r,g,b = 8*floor(c/8), a = 0 or 255; black opaque with
keep_black -> (8,8,8); histogram keyed by colour, sorted by count desc, first num_colors kept
(padded with entry 0), then sorted by order = r<<16|g<<8|b. createBody: transparent pixel ->
first histogram entry with a==0; else nearest by Euclidean RGB among opaque entries.
ImagePanel.paintCanvas: byte = data[body_offset + 128*(data.ci.y + i/w) + i%w + data.ci.x];
ppb 1: colour = header[byte] if byte < num_colors else header[0]; ppb 2: low nibble first.

## chunk tables (module 5457), (data ci -> cf) => (canvas ci)
    cardBg1 (a): (0,0)-(128,192)=>(0,0)  (0,256)-(16,384)=>(128,0)  (32,256)-(48,328)=>(128,128)
                 (64,272)-(128,280)=>(0,192)  (64,280)-(128,288)=>(64,192)
    cardBg2 (b): (0,0)-(128,128)=>(0,0) (0,192)-(128,256)=>(0,128) + the 4 edge/strip chunks of a
    cardBg3 (c): (0,384)-(128,576)=>(0,0) (16,256)-(32,384)=>(128,0) (48,256)-(64,328)=>(128,128)
                 (64,256)-(128,264)=>(0,192) (64,264)-(128,272)=>(64,192)
    cardTransform1 (d): a + (0,192)-(128,256)=>(0,200)
    cardTransform2 (e): (0,928)-(28,944)=>(0,0) (0,944)-(28,960)=>(0,16) (0,960)-(28,976)=>(0,32)
                        (0,976)-(12,992)=>(0,48) (0,992)-(12,1008)=>(0,64)   [width 60 canvas, ppb 2]

## Disc verification (python, eo.walk_iso on the .bin, WA_MRG at LBA 10102)
    ISO: /DATA/WA_MRG.MRG lba 10102 size 37748736 ; SLUS_014.11 lba 24 ; MODEL.MRG 28534 ; SU.MRG 954
    WA_MRG md5 971c16ea21635b45351e5ae959c53503
    bundle copies: tex 0xB63000+c (last -0x4000), clut 0xB83000+c
      rows 0..592 identical in all 10 (md5 1b8ac4232e416745719428b2b1695402)
      copy 8 (0xF97800) differs rows 592..896 & clut rows 0..7, 9 ; copy 9 (0x10C4800) rows 640..896 & clut rows 0, 9
      free-duel bundle (0x1E88) and name-entry (0x1EDF) do NOT contain the texture
    SLUS bytes at the 12 offsets: 19 50 12 14 97 157 97 171 119 32 110 13 (all addiu low bytes)

## Loader trace
    func_80014E1C(a0,a1,sector,count,cb,x,y) -> func_80013998(D_800E9E60, ...) ; func_80013940 sets
      field36 = gFile_anLba[a1&15] + sector, field20 = count<<11
    pump: func_80014A5C -> func_8001455C (DsCommand/DsPacket state machine, gp+0x1F8 state 0..6)
          -> func_80013C28 per sector: mode 1 memcpy to obj+8 ; mode 2 LoadImage2(rect(obj+0x30,obj+0x32,64,16))
             then if D_8009B0F4 & 0x20000: x += 64 else { y += 16; if (y & 0xFF)==0 { y = (y^0x100)&0x100; x += 64 } }
             obj+0x28 -= 0x800 ; when <= 0 -> callback(obj, obj+0x47++) then obj+0x28 = obj+0x1C
    duel cb 0x800171A8 jump table 0x800100C0: 171E4 17250 17278 172D0 172F8 17320 17348 1739C 173C8 173DC 1741C 17494 174D4
      S0 (0x300,0x100) 0x20000 ; S1 staging 0x2000 ; S2 LoadImage2(0x100,0xF0,0x100,0x10) + equipTable 0x2800
      S3 fusionTable 0x10000 ; S4 ritualData 0x800 ; S5 staging 0x1000 ; S6 LoadImage2(0,0xF0,0x100,8) + (0x200,0x100) 0x10000
      S7 *(0x800101DC)=0x80146000 0x16000 ; S8 handAiScript 0x1800 ; S9 D_801A9800 0x1800 ; S10 (0x340,0) 0x4000
      S11 *(0x80010000)=0x80100000 0x2800 ; S12 (0x280,0x100) 0x10000     total 235 sectors
    library cb func_8002BD0C table 0x80010208: BD4C BDB8 BDC8 BED4 BE70 BED4 BF14
    password cb func_8003BD14: (0x300,0x100) 0x20000 ; staging 0x2000 ; LoadImage2(0x100,0xF0,0x100,0x10)+handAiScript 0x1800 ; *(0x800101D8)=0x80168000 0x7800
    0x2189 cb func_80032184: (0x300,0x100) 0x20000 ; (0x340,0) 0x4000 ; staging 0x2000 ; LoadImage2(0x100,0xF0,0x100,0x10)
    boot cb func_80043328 (0x1690 x 0x36): (0x280,0) 0x18000 ; staging 0x1000 ; LoadImage2(0x200,0xF8,0x100,8) + 0x800 ; LoadImage2(0x280,0xE8,0x10,8) + *(0x800101D8) 0x1800
    other func_80014E1C sites: 0x1E88+0x57 free duel ; 0x1EDF+0x50 name entry ; 0x1F2F+0x56 password ;
      0x1FD9(+s0)+0x9E func_8003C0C0 ; 0x2115+0x32 & 0x2147+0x10 func_8003C2B4 ; 0x2157+0x32 ; 0x1F85+0x22 & 0x1690+0x36 func_80043960 ;
      0x1DAB+0x22 & 0x1D33+3 func_80020F4C ; 0x1DCD+0x8A func_8002BFCC ; 0x2189+0x4C call_14e1c_137e4 ; 0x4C7+0x10 (a0=1, other file) duel_phase_transition_dispatch

## Site assets
    /Assets/img/capas.png (INFO tab layers picture) -> 302 to site root without session; not mirrored.
    bigcard.zip: Templates/{big card dynamic part template, big card static part template}.png 144x264 RGBA,
                 sleeve_template.png 144x200 ; examples Modern/Vanilla/Teaonline (P-mode PNGs) + configuration.txt
                 (positions text 10,129 image 30,30 atk 59,152 def 104,152 st 112,7 attr 8,108 ; hue shifts per colour)
