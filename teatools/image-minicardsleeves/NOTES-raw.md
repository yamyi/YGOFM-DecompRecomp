# Mini Card Sleeves -- raw working notes (2026-09-04)

Tool chunk: `site/js/extend/tools/image/minicardsleeves.f22f6e41.js` (component still named
`BackgrounEdit`, a fork of the cardsleeves page; ImageConverter is inlined, chunk tables inline).

## Constants
    FileReader wa: ".mrg" minsize 36700160 maxsize 39845888 ; images "image/*" <= 20 MB ; no SLUS reader shown
    body_offset 0xB75800 = 12015616 ; header_offset 12071424 = 0xB83200
    cicles = [0,481280,962560,1443840,1925120,2406400,2887680,3684352]   (8: arenas + library)
    ImagePanel mini: 224x64 (cardBg1) and 128x48 (cardTransform3), num_colors 128, bytes_width 128,
        pallete_offset = 12071424 + (colorIndex%6)*512 + (colorIndex==6 ? 256 : 0)
    palleteConfig1: colorIndex==6 ? {offset 12071808 (=0xB83380), size 16} : {offset 12071424+512*k+128, size 16}
    images: [0] dynamic 168x64 16 col move 64 ; [1] static 168x64 16 col move 80 ; [2] sleeve 56x64 16 col move 96
            [3] text 128x48 16 col move 112 ; all body_offset_base 0xB75800 header_offset_base 12071424
            [4] micro 12x16 4 col move 0 ; [5] micro 12x16 4 col move 4 ; [6] micro 12x16 8 col move 8
            micro body_offset_base 0xBC5800 (12343296), header_offset_base 11929792 (0xB60840)
    ImagePanel micro (miniFormation1/2): 12x16 num_colors 16 ppb 2, pallete_offset 15862464 (0xF20BC0) + 32*colorIndex
    palleteConfig2 (micro editor): offset 15862466 + 32*colorIndex, size 2
    chunks: O=cardBg1 [(0,48)-(56,112)=>(0,0) (0,112)-(56,176)=>(56,0) (56,112)-(112,176)=>(112,0) (56,48)-(112,112)=>(168,0)]
            j=cardTransform1 = first three of O ; P=cardTransform2 [(56,48)-(112,112)=>(0,0)]
            B=cardTransform3 [(0,0)-(128,48)=>(0,0)] ; T=[(48,0)-(54,16)=>(0,0)] ; E=[(54,0)-(60,16)=>(0,0)]
    salvarEnImagen: n = 512 (or 32 if index>3) ; writeTransparent = !(index==1 || index==5)
        for each cicle r: setNewHeader(hdr+r + {0,n,2n,3n,4n,5n} and +256, pal, move) ; setNewBody(body+r, idx, pal, wt, move)
        setNewBody ALWAYS uses this.cardTransform1 and images[index].width, writes 8bpp bytes (no nibble packing)
    generateColor7Mini: for each cicle: copy 256 bytes at 12071424+cicle -> +256
    generateColor7Micro: copy 32 bytes at 15862464 -> +192

## Disc facts
    rows 592..768 of the card texture: identical in the 7 arenas + library ; password/0x2189 differ
    mini CLUT rows (0xB83200 + 512*k, k=0..6): md5 f0cf2a23 identical in all 8 copies ;
        colour 64 = 0000, colour 65 = f881 / 8081 / 51b8 / a0cc / ebd8 / 3881 / d65a per row
    0xB60840 (sector 5825 + 0x40): 00 00 1f 80 11 80 0c 80 07 80 18 80 1a 80 1d 80 e0 83 ... (7 x 32 bytes)
        0xB60840 + 0x75800*k (k>=1) = 686603643a5bb142... (pixel data, sector 230 of arena k-1) ; +3684352 = zeros (sector 7624)
    0xF20BC0 .. +224: all zero in stock (library bundle sector 116 + 0x3C0)
    0xBC5800: 4bpp-looking data (66 14 22 63 24 31 54 46 ...), identical in the 7 arena copies; the library-cycle
        copy (0xF49000 = sector 7826, inside the free-duel bundle 7816..7902) differs
    boot block: func_80043960 (from Main_Init) -> func_80014E1C(0,0,0x1690,0x36,func_80043328):
        (640,0) 0x18000 ; staging 0x1000 ; LoadImage2((512,248,256,8)) ; +0x800 ; LoadImage2((640,232,16,8)) ; 0x1800 -> 0x80168000
        => sector 5825 byte 0x40 = CLUT block byte 0x840 = row 4 colour 32 -> VRAM (544, 252)
    duel S10: bundle sectors 190..197 -> (832,0) rows 0..127 ; sector 197 = rows 112..127 ;
        bytes 48..60 -> halfwords 24..30 -> 4bpp texels 96..120

## Renders (scratch): mini_full 168x64 = blank frame | spiral-art frame with ATK/DEF bar | same ; mini_sleeve = spiral back ;
    micro_a/b 12x16 fully opaque, 7 indices each
