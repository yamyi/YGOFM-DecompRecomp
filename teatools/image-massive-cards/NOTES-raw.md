# image/massive/cards — raw notes

Session: 2026-09-04. Mirror already present; nothing re-fetched from the site.

## Reading the chunk

    sed 's/},{/},\n{/g; s/;/;\n/g; s/,function/,\nfunction/g' \
        site/js/extend/tools/image/massive/cards.4171f7dd.js > pretty.js
    grep -n "offsett\|accepted\|minsize\|maxsize\|saveAs\|num_colors\|JSZip" pretty.js

Relevant literals, verbatim:

    V.240303 [BETA] [Early access for donors]

    FileReader accepted:".mrg" minsize:31457280 maxsize:44040192   id:"wareader"
    FileReader accepted:".zip" minsize:0        maxsize:44040192   id:"zipreader"  (big)
    FileReader accepted:".zip" minsize:0        maxsize:44040192   id:"zipreader2" (small)

    tabs: ["Big Image","Small Image","Save Panel"]

    offset: { body:      parseInt("169000",16),   // 0x169000  art
              header:    1488448,                 // 0x16B640  art CLUT
              body_lil:  parseInt("0",16),        // 0         thumb copy A
              header_lil:1280 }                   // 0x500     thumb copy A CLUT

    chunks:     [{width:102,height:96,data:{ci:{x:0,y:0},cf:{x:102,y:96}},
                                       canvas:{ci:{x:0,y:0},cf:{x:102,y:96}}}]
    chunks_lil: [{width:40, height:32,data:{ci:{x:0,y:0},cf:{x:40,y:32}},
                                       canvas:{ci:{x:0,y:0},cf:{x:40,y:32}}}]

Converter configs:

    big:  {width:102,height:96,num_colors:256,sh:true,color:"white",
           emit_pixel:false,clear_before_render:true,keep_black:true,show:false}
    lil:  {width:40, height:32,num_colors:64, ...same...}

Writers:

    salvarEnImagen(header, body, a, i):
        vt(dataviewWa, chunks, { header:{offset:i, data:header},
                                 body:  {offset:a, data:body,
                                         width:102,height:96,data_width:102} })
        a = offset.body   + 14336*(id-1)
        i = offset.header + 14336*(id-1)

    salvarEnImagenLil(header, body, a, i):
        vt(dataviewWa, chunks_lil, {
            header:{ offset:i, data:header, hasMore:true,
                     aditionals:[ 14336*floor((i-1280)/2048) + 1490912 ] },   // 0x16BFE0
            body:  { offset:a, data:body, width:40,height:32,data_width:40,
                     hasMore:true, bpp:1,
                     aditionals:[ 14336*floor(a/2048) + parseInt("16BAE0",16) ] } })
        a = 0    + 2048*(id-1)
        i = 1280 + 2048*(id-1)

`vt` -> `bt` (CLUT) + `yt` (indices); `hasMore` makes both write to `[offset, ...aditionals]`.
`bt` writes `u16 = (a>0 ? z1 : 0)<<15 | (b>>3)<<10 | (g>>3)<<5 | (r>>3)`, `z1` defaults to `"1"`.

    formatID(t):
        t.indexOf("\\")>-1 -> false
        t.indexOf("/") >-1 -> false
        e = parseInt(t.toLowerCase());  return e>0 && e<723 && e

    proccesImage: zip entry -> blob -> arrayBuffer -> DataView -> Converter.batch
    Converter.paintCanvas: createImageData -> clear() -> putImageData -> img.onload ->
                           ctx.drawImage(img,0,0) -> createHeader() -> createBody() ->
                           emit update:image        <-- the ONLY thing that advances the batch
    (no onerror handler => a non-image entry with a numeric name stalls the run)

    saveEditedFile -> $emit("create","wa") -> download() -> saveAs(Blob(dataviewWa.buffer), filenameWa)
    saveChange: POST api/v2/tools {version, tipo:36, data:<timestamp+rand>}
    validateUser: POST api/v2/toolcontrol/validate; 401 -> location="/extend/info/join"
                  (an interval destroys the editor every 3 s until that call succeeds)

## Disc verification

Extracted WA_MRG.MRG from the raw disc (18432 sectors from LBA 10102, 2048 data bytes at +24 of
each 2352-byte sector) -> 37,748,736 bytes, sha1 `4d85dfc2f2f872ab448de7d55788045ee37e60d4`.

    $ card_art.py info --wa WA_MRG.MRG --ids 1-722
    flat WA_MRG
      mini table  sectors 0..721        bytes 0x0..0x169000
      big records sectors 722..5775     bytes 0x169000..0xB48000
      checked 1-722: 0 mini-copy mismatch(es), 0 dirty pad(s)

So for **all 722** cards: `REC+10976 .. REC+12384` == `0x800*(id-1) .. +1408`, and
`REC+12384 .. REC+14336` is zero. (F136 had checked 5 cards.)

CLUT survey over all 722 art CLUTs (256 entries each):

    STP-set count histogram : {1: 675, 2: 36, 0: 3, 4: 5, 5: 1, 3: 2}
    entry 0 value           : {8000: 719, 0004: 1, 0001: 1, 0400: 1}

Thumbnail CLUTs (64 entries): `{1: 696, 2: 26}`.

Card 1 art CLUT starts `8000 7FFF 7FFF 7FFE 7FDD ...` — entry 0 opaque black, everything else
STP=0. The three zero-STP cards (296, 320, +1) simply have a colour in entry 0 (`0004`, `0001`,
`0400`). **Conclusion: stock card CLUTs do not carry STP on their opaque entries**, contradicting
the parenthetical in `image-specsmix/README.md` §1.

The site's writer sets STP=1 on every alpha>0 entry. Confirmed by importing a test image:

    patched card1 CLUT first 8: 0000 8020 8420 8040 8440 8840 8C40 8060   STP count 255

(entry 0 = `0000` because the test image had transparent pixels, so the transparent slot landed
first after the `r<<16|g<<8|b` sort.)

## Script testing (all on copies in the scratch dir)

    card_art.py roundtrip --wa WA_MRG.MRG --ids 1-6
        -> round-trip over 6 card(s): 0 differing byte(s) -- OK
    card_art.py import --wa copy --dir zipsrc --what big  --palette site   -> only 0x169000..0x170000 touched
    card_art.py import --wa copy --dir zipsrc --what mini --palette site
        -> both thumbnail copies identical, 0xFF pad after copy A intact
    card_art.py restore --wa copy --from WA_MRG.MRG --ids 1-2 && cmp copy WA_MRG.MRG
        -> byte-identical

`mini_1.png` in the same directory is correctly skipped (`parseInt("mini_1.png")` is NaN), matching
the JS.

## Fidelity fix made to the pre-existing script

`site_index()`'s body loop originally memoised every colour key in a dict. The JS keeps a *single*
previous-key cache and, in the branch where a pixel is transparent but **no** palette slot has
alpha 0, leaves its running index `n` at the previous pixel's value. Rewritten to carry `n` across
pixels and to skip memoising that branch.

## Not done / left open

* No live comparison against the real site (login-gated; the analytics/validate POSTs are not called
  per the brief).
* Whether the STP flood is ever visible — needs a card sprite drawn with ABE.
