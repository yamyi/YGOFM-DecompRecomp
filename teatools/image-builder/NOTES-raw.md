# Image Builder — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/image/builder.cf5d5334.js (81 KB), component AdvancedImage; helpers PresetsLoaded,
PopUp, ImageSelector, PalleteEditor, ColorHexEditor, ColorToneEditor, TextureIndexer (chunk-common 5191), Modal.
FileReader accepted ".11,.mrg" minsize 1048576 maxsize 42991616; image "image/*" <= 20971520; also a raw reader ("openRaw").

Classes: q{x,y}; W{ci:q}; V{width,height,data:W,canvas:W} (chunk); R{aditionalPalletes[],aditionalBodies[]};
G{width=128,height=128,colors=256,data_width=128,body_offset=0,pallete_offset=0,bpp=1}; J{chunks,settings,advancedOptions};
X preset {id,userid,username,toolname,filename,thumb,data:J,created,edited}. presets=[new X] (id 0 "custom").
selSettings = preset.id==0 ? settings : preset.data.settings. activePallete = header_offser_selected or settings.pallete_offset.
setNewHeader: for each palette offset in [pallete_offset, ...aditionalPalletes]: lo = g[2:5]+r[0:5], hi = (a>0)+b[0:5]+g[0:2].
setNewBody: for each body in [body_offset, ...aditionalBodies], each chunk, i in [data.ci.x, data.ci.x + width/bpp), n in [data.ci.y, +height):
  bpp1: v = canvas[(i-dx) + cx + (n-dy+cy)*width]; bpp2: v = hi(canvas[2(i-dx)+1+cx+...])<<4 | lo(canvas[2(i-dx)+cx+...]); file[body + i + n*data_width] = v.
ImagePanel config for preview: {width,height,num_colors:colors,bytes_width:data_width,bytes_height:300,body_offset,pallete_offset:activePallete.offset,ppb: bpp==2?2:1}.
validateFile: file must be >= body + w*h/bpp and >= palette + 2*colors.
movePallete(back): palette offset +-2*colors (and the additional ones). settings.body_offset watcher parses 0x.., hex, decimal.
Drafts in localStorage "builddraft". Server: GET api/v2/tools/images?version=, POST api/v2/tools/saveimage {toolname,data,filename},
DELETE api/v2/tools/deleteimage?version=&id= (all need the signed session; not fetched). Thumbs: /Assets/img/tools/images/<thumb>.
TextureIndexer: client-side crop/resize/quantise (algos auto/nearest/lanczos3/lanczos2/mitchell/catmullrom/triangle/box/gaussian,
dither none/ordered/floyd, bg removal, size presets 8x8 40x32 102x96 320x168 256x256) -> data URL -> loadImage.
Page text: "With this tool you will have the ability to modify many images in the game." Version V.260705.

Verification of the generic script against the specific tools: raw_image.py export of the font == game_font.py export (cmp);
card frame assembled from presets/card_frame_monster.json matches the site's ot[3] map; imports/restores on copies -> cmp identical.
