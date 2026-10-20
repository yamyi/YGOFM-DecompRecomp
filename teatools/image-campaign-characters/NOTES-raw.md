# Campaign Characters -- raw working notes (2026-09-04)

Tool chunk: `site/js/extend/tools/image/campaign/characters.55dd3bc1.js` (component `LogoEditor`,
data `lista` (64 ids/names), `temlist` (6 templates: name, com[], chunks, id, width, height, da[], url)).

## Constants
    FileReader wa: ".mrg" minsize 37748735 maxsize 39845888 ; image "image/*" <= 31457280
    ImagePanel: width/height = template, num_colors 256, bytes_width 128, bytes_height 256,
        body_offset = 0x1DC0000 + 102400*(id-1), pallete_offset = 31293440 + 102400*(id-1) (= body + 0x18000)
    salvarEnImagen(header, body, bodyOff, palOff):
        setNewHeader(palOff, header, "0","1")  -> STP bit 0   (CLUT A, block+0x18000)
        setNewHeader(palOff+512, header)       -> STP bit 1   (CLUT B, block+0x18200)
        setNewBody(bodyOff, body): for each chunk: setUint8(off + x + 128*y, body[(x-dx+cx) + (y-dy+cy)*width])
        setNewCommand(palOff + 2048, tempsel.com)  -> block+0x18800
    makeTrasparent(pixel): clicked colour -> transparent: palette entries equal to it dropped (first one kept as
        transparent slot? -- first match becomes the transparent entry, later duplicates removed), indices above
        the removed ones shift by -1, body pixels of that colour -> 0 ; then rewrite CLUT A/B, body, cleanBody(da), com
    cleanBody: zero the template's da rectangles (x0..x1, y0..y1) at off + x + 128*y
    getImageTemplate: downloads /Assets/img/templates/0N.png (302 without session; not mirrored)
    searchNewTemplates: GET api/v2/tools/newtemplates (needs session) appends to temlist
    templates: 1 Simon z 368x160 com 200 B da [(0,168)-(64,192),(0,424)-(64,448)]
               2 Anubisius H 232x232 com 200 B da [(0,128)-(32,152),(104,256)-(120,280)]
               3 Atem q 184x200 com 200 B da [(16,32)-(80,64),(56,64)-(72,80)]
               4 Bakura R 416x168 com 496 B da [(24,160)-(88,184),(48,184)-(64,200),(24,288)-(88,312),(48,312)-(64,336)]
               5 Rex L 320x176 com 480 B da [(40,160)-(104,184),(64,184)-(80,200),(40,408)-(104,440),(56,440)-(88,456)]
               6 Pegasus U 496x192 com 400 B da [8 rects]
    chunk tables z/H/q/R/L/U: see scripts/templates.json (data_x, data_y, canvas_x, canvas_y, w, h)

## Disc facts (char_1.bin = 50 sectors from LBA 25334)
    image rows 0..511 non-zero, 512..767 zero ; 0x17000..0x17FFF zero
    0x18000: 0000 ff5b df53 bb7f be53 ...   (CLUT A, bit15 clear)
    0x18200: 0000 ffdb dfd3 bbff bed3 ...   (CLUT B = A | 0x8000)
    0x18400..0x187FF zero ; 0x18800: 10 00 16 00 00.. (== template-1 com) ; 0x18900..0x18FFF: FF
    Simon com bytes: 16,0,22,0,0x0*12,28,0,30,0,0,0,34,0,36,0,0,0,40,0,43,0,46,0,62,0,65,0,68,0,
        0,84,0, 0,112,0, 3,112,0,3,122,0,3,132,0,3,122,0,3,112,0,255, 0,142,0, 0,170,0, 3,170,0,3,180,0,3,190,0,3,180,0,3,170,0,255,
        4,16,0,0,208,128,13,192,32,198,168,160,136,192,192,214,216,96,0,192,32,199,224,128,0,194,224,223, 1,0,0,0,224,168,0,193,224,196, ...
        (second state: same with 29/152/16/... = +16)

## Code trace
    func_8003A560 (asm_2A998.s): s2 = *(0x80010000) + 0x63040 ; loop a0 = 4..0 over D_8015C410[a0] (lb):
        if entry < 0: gp+0x41E = a0 (first free slot) ; if entry == obj+0x30 (id): cache hit:
            wait func_80042324?(0xA) ; rect@block+0x18C00 = (0x340 - 0xC0*obj+0x3C, 0x100, 0xC0, 0x100) ; LoadImage(rect, block)
            rect@block+0x18C08 = (0x200, 0xF0 + 2*side, 0x100, 2) ; LoadImage(rect, block+0x18000)
            memcpy(side ? 0x801AF800 : 0x801AF000, block+0x18400, 0x800) ; obj+0x33 |= 0x40 ; return
        s2 -= 0x18C10 per slot
      miss: if loader busy (D_8009B0F4 & 0x2000030 | D_8009B134) -> obj+0x33 &= 0x7F, retry
            a2 = ((id*3<<3)+id)<<1 = id*50 ; += 0x3B4E ; func_80014E1C(0,0,a2,0x32,func_8003A01C,0,0)
            v1 = returned loader obj ; v1+0x38 = 0x801AF000 (0x801AF800 if side) ; v1+0x3C = side ; D_8009B0F4 |= 0x10
    func_8003A01C(obj, stage): 0: f1C=0x18000, y=0x100, w=0x40, h=0x10, mode 2, x = 0x340 - 0xC0*obj+0x3C, f8=staging
                               1: f1C=0x800, dest staging, mode 1
                               2: rect(obj) = (0x200, 0xF0 + 2*obj+0x3C, 0x100, 2) ; LoadImage2(obj, staging) ; f1C=0x800 ; dest = obj+0x38 ; mode 1
    pump order for mode 2 (func_80013C28): y += 16 ; at y&0xFF == 0: y back to page top, x += 64  -> 3 pages side by side
