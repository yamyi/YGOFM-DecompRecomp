# CARDS DATA — raw working notes (2026-09-04)

Chunk: site/js/extend/tools/cardsdata.355ee958.js, component `DropTable` (name reused), mixin `xe`
(same code as chunk-common 5e6c). Constants: names table 1859584 (0x1C6000), name segment = table
- 22528 (0x1C0800), stats 1854016 (0x1C4A40; +4*id), level 1858355 (0x1C5B33; + id - 1),
descriptions table 1772032 (0x1B0A00 = 0x1C0000+0x200 RAM 0x801C0200; +2*id), description text
= table + off - 512 (RAM 0x801C0000 + off), blob writer base 1861632 (0x1C6800).
readValues: c=atk9=b0+256*(b1&1); l=def9=(b1&254)/2+128*(b2&3); u=st2=(b2&60)/4;
            d=st1=(b2&192)/64+4*(b3&3); p=type=(b3&252)/4; m=level byte: attr=m>>4, level=m&15
writeValues(n,c,l,d,u,p,m,h): [c%256, l%128*2+floor(c/256), d%4*64+4*u+floor(l/128), 4*p+floor(d/4)], level=16*h+m
createExcelData: columns A id, B name, C atk, D def, E st1, F st2, G type, H level, I attr, J colour;
  c=floor(c/10) etc; validity n 1..722, c,l 0..511, d,u 0..15, p 0..63, m,h 0..15; unticked -> current value
watch dataviewSlus: cardList=getCardInfo(1..722), typeList=getCardInfo(768..791), starList 792..801,
  oppList 808..847
writeAllNamesOnSlus: see README section 2 (holes 35533/35534 = 0x8ACD/0x8ACE, 36250/37376 = 0x8D9A/0x9200,
  limit 0xA004, entries 723..767 -> 24576, 864..1023 -> d[768].p, colour prefix 248,10,colour)
readDescription: 0xFE = line break, 0xF8 skips 2 operand bytes; writeDescriptionParsed exists in the
  mixin (table entry 0x100 = 0x9F4 empty, texts from 0x9F5, limit 0xFFFF) but the UI never calls it.
saveChange: tipo 18; PostBox guia 28. getImageTemplate -> /Assets/files/PlantillaData.xlsx (mirrored).

Verification on stock SLUS:
  0x1C4A44: 2c f5 05 02 | 50 90 09 06 | 78 c8 44 12 | 78 8c 20 01
  0x1C5B30: 7c 01 00 [08 04 24 53 13 ...]   -> card1 at 0x1C5B33 (0x08 Light/8), card3 0x24 (Earth/4)
  0x1C6000: 00 60 01 60 18 60 25 60 ...       name offsets
  decoded strings 0x8300..: Dragon .. Equip (24); 0x8318..: Mars Jupiter Saturn Uranus Pluto Neptune
  Mercury Sun Moon Venus (padded to 7); 0x8322..0x8327 = Dragon x6
  sample words: 1 0x0205F52C (3000/2500, b22=8 Sun, b18=1 Mars, type 0, lvl 8, attr 0);
  3 0x1244C878 (Moon/Mars, Beast-Warrior, Earth 4); 58 0x1DCC281E; 380 0x022AF9C2 (Sun/Venus, lvl 12);
  695 0x58000000 (type 22, attr 6 Magic)
  descriptions: entry 0x101 = 0x9F5 -> 0x801C09F5 "An extremely ..." (0x801B09F5 holds junk, so the
  bank for these is 0x801C0000 = Text_LookupString's >0xCFFF branch); max end 0x801CD59E; entries
  0x3D3.. = 0x9F4
  name blob extents: cards 0x6001..0x8ACC, 723..767 -> 0x6000, types/stars 0x8ACE..0x8BCF,
  duelists 0x8BD0..0x8D99, locations 0x8D9A..0x8EA5, non-zero 0x9004..0x916E, 0x3BF/0x3C0/864..1023 = 0x8ACE
  no F8 escapes in any stock card name
  WA_MRG.MRG byte search for the stats/name/level tables: no copies

Consumers (decomp): D_801D5332 only at 0x80029410 (init_container_entry_objs);
  gDuel_adwCardStats viewer text 0x80037E64..0x80037F18 (`ori v0,zero,0x8300`);
  Text_LookupString in src/bank_table_lookup.c.

Script tests (scratch): dump -> cards.csv; apply cards.csv (values only) == stock byte-for-byte;
apply --names --colors with unchanged text: 937 bytes differ, verify says 0 cards differ;
first diff 0x1C65A4 (entry 722: 0x8AB5 -> 0x8ACE), stars lose trailing spaces;
xlsx template applied == stock; modified row (BEWD 3500, renamed, colour 1) -> F8 0A 01 prefix at
0x1C6801; restore --stock == stock.
