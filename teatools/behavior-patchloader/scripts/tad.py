#!/usr/bin/env python3
"""tad.py - offline clone of the TEA-Online ".tad" patch container.

The container is used by three site tools:

    extend/tools/behavior/patchcreator   V.230422   writes .tad (v2)
    extend/tools/behavior/patchloader    V.230421   reads .tad (v1 and v2), applies it
    extend/tools/data/disassembler                  writes .tad (v1 and v2)

Container
---------
A .tad file has NO magic, NO header, NO length field, NO checksum and NO target-file
identification.  The whole file is the ASCII base64 of a UTF-8 JSON object:

    file bytes = base64( JSON.stringify(patch) )      Buffer.from(json,'utf8').toString('base64')

Loading is `Buffer.from(TextDecoder().decode(bytes),'base64').toString()` then `JSON.parse`.
A parse failure is swallowed (`console.log(e.message)`) and leaves an empty patch.

JSON schema (canonical key order as emitted by both writers):

    v      1 | 2            format version, dispatched by patchloader.tryApply()
    title  string           free text shown in the loader header
    notes  [{id,text,date}] free text; id = "YYYY-MM-DD HH:mm:ss <n>", date same stamp
    locked bool             WRITTEN BY EVERY TOOL, READ BY NONE - vestigial
    bytes  {} | []          v1 payload; v2 writers emit an empty {} (creator) or [] (disassembler)
    dZones {}               v2 only: user-editable fields laid over the areas (see below)
    areas  [{address,data,isHex}]   v2 payload
    pic    string           optional; a filename under /Assets/img/tools/patch/ shown as the
                            header background in the loader
    sign   {serial,user,athr}  optional; server-issued, see "Signing"

v1 record  ("bytes" object)
    key    = one arbitrary prefix character + the DECIMAL file offset.
             patchcreator/patchloader mint "b<off>"; the disassembler mints "c<off>".
             Readers do `parseInt(key.substring(1))`, so the letter is ignored.
    value  = the 32-bit word as a JSON number (or numeric string), applied with
             `DataView.setUint32(off, parseInt(value), /*littleEndian=*/true)`.
    A write past EOF throws RangeError, is caught, and the loader shows
    "Your <file> is not the size indicated for the patch."  Nothing else is validated.

v2 record  ("areas" array)
    address = DECIMAL file offset (always a number in the file).
    data    = hex bytes as ONE SPACE-SEPARATED STRING, "1C 00 05 24".  The loader does
              `data.split(" ")` and writes token i with
              `setUint8(address + i, parseInt(token,16) % 256)`.
              Consequences, all reproduced here:
                * the byte count is the TOKEN count, not len(data)/2 - "0102" is ONE byte (0x02,
                  because parseInt("0102",16)=258, 258%256=2);
                * "" split by " " is [""] in JS, so an empty area writes ONE 0x00 byte;
                * a double space yields an empty token -> parseInt -> NaN -> setUint8 writes 0x00.
              The creator's fixBytes() normalises anything you type into upper-case "HH HH ..".
    isHex   = editor-only flag: "the Address box is typed in hex".  fixAddress() converts the
              box with parseInt(value,16) and stores a DECIMAL number, so isHex never changes
              how a .tad is applied.  (Editor quirk: after conversion the box shows the decimal
              value, which is re-parsed as hex on the next edit.)

v2 dynamic zones ("dZones" object)
    key   = "b" + the DECIMAL address (the address is repeated inside the value).
    value = {address:int, type:1|2|4, tag:"label", value:int}
    `type` is a byte width; the loader renders one numeric input per zone labelled `tag`.
    On load, setInitialValues() seeds `value` from whatever the AREAS contain at that address:
        val  = parseInt(tok[k],16)
        type>1 and tok[k+1] exists: val += 256*parseInt(tok[k+1],16)
        type>3 and tok[k+3] exists: val += 65536*parseInt(tok[k+2],16)
                                    val += 16777216*parseInt(tok[k+3],16)
      - the containment test only checks the FIRST byte of the zone (`addr <= a <= addr+len-1`);
      - the loop does not break, so if several areas cover the address the LAST one wins;
      - for type 4 with only three tokens available, byte 2 is skipped as well (guarded on [k+3]).
    applyPatch2() writes the areas FIRST and then every zone, so a zone always overrides the
    area bytes underneath it: setUint8 / setUint16(LE) / setUint32(LE) by `type`.
    The creator wipes all dZones whenever any area address or byte string changes (resetDZones).

Signing
-------
    md5 = md5(JSON.stringify(patch_without_sign))          npm "md5" module, hex
    POST api/v2/toolcontrol/genhash  {hash: md5}   -> {ok, sign}       (creator, on Save)
    POST api/v2/toolcontrol/checkhash {hash: md5, serial: sign.serial} (creator, on Load Draft)
`sign` is then stored in the patch as `{"serial":..,"user":..,"athr":..}`; the loader only uses
it to print the author name and link /extend/user/profile?id=<athr>.  THE LOADER NEVER VERIFIES
IT - an unsigned, hand-made .tad applies exactly the same.  Only the *creator* refuses to open a
patch whose md5+serial the server rejects ("This file cannot be edited.").
`tad.py hash` prints the md5 the server would be asked about, over the same normalised object
the creator rebuilds (v,title,notes,locked,bytes,dZones,areas[,pic]; sign and unknown keys dropped).

Target file
-----------
NOT recorded anywhere in the container.  The loader's game-file picker is
`accepted:".11,.mrg", minsize:0, maxsize:42991616`, so SLUS_014.11 (1,902,592 B) and
WA_MRG.MRG (0x2400000 = 37,748,736 B) both load into the SAME DataView and the SAME code path;
`accepted` is only an HTML `accept=` hint, so any renamed file works.  Offsets are therefore raw
file offsets into "whatever you dropped in".  For the SLUS: RAM = 0x80010000 + (off - 0x800).

Usage
-----
    tad.py dump   patch.tad [--slus]     decode, list every record (--slus adds RAM addresses)
    tad.py json   patch.tad              print the raw JSON
    tad.py hash   patch.tad              md5 the site would send to genhash/checkhash
    tad.py verify patch.tad target.bin   show stock vs patch bytes at every record
    tad.py apply  patch.tad target.bin -o out.bin [--set TAG=VAL] [--undo undo.tad]
    tad.py create out.tad --title T --area ADDR:HEX [--dzone ADDR:TYPE:TAG] [--note N] [--v1]
    tad.py diff   stock.bin modded.bin out.tad --title T
"""
import argparse, base64, hashlib, json, sys, datetime, re

# ---------------------------------------------------------------- JS semantics

_JS_INT_RE = {10: re.compile(r'^[\s ]*([+-]?)(\d+)'),
              16: re.compile(r'^[\s ]*([+-]?)(?:0[xX])?([0-9a-fA-F]+)')}

def js_parse_int(s, radix=10):
    """JS parseInt(): leading whitespace, optional sign, longest valid prefix, else NaN."""
    if isinstance(s, (int, float)):
        return int(s)
    m = _JS_INT_RE[radix].match(str(s))
    if not m:
        return None                       # NaN
    return int(m.group(2), radix) * (-1 if m.group(1) == '-' else 1)

def js_to_uint(v, nbytes):
    """ToUintN(): NaN/undefined -> 0, otherwise wrap."""
    if v is None:
        return 0
    return v % (256 ** nbytes)

def area_tokens(area):
    """The site's `area.data.split(' ')`.  JS ''.split(' ') == [''] -> one NaN token."""
    return str(area.get('data', '')).split(' ')

def area_bytes(area):
    """The bytes applyPatch2() would write for this area."""
    return bytes(js_to_uint(js_parse_int(t, 16), 1) for t in area_tokens(area))

def fmt_data(bs):
    """The creator's fixBytes() canonical form."""
    return ' '.join('%02X' % b for b in bs)

def norm_addr(a):
    return js_to_uint(js_parse_int(a, 10), 8)   # addresses are plain decimal numbers

# ---------------------------------------------------------------- container

def load_tad(path):
    raw = open(path, 'rb').read()
    txt = raw.decode('utf-8', 'replace')
    try:
        js = base64.b64decode(txt + '=' * (-len(txt) % 4), validate=False).decode('utf-8', 'replace')
    except Exception as e:
        sys.exit('not base64: %s' % e)
    try:
        return json.loads(js)
    except Exception as e:
        sys.exit('base64 decoded but JSON.parse failed (the site swallows this and applies '
                 'an empty patch): %s' % e)

def dumps_js(obj):
    """JSON.stringify(): no spaces, non-ASCII left literal, dict order preserved."""
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False)

def save_tad(path, obj):
    open(path, 'wb').write(base64.b64encode(dumps_js(obj).encode('utf-8')))

def js_truthy(v):
    """JS truthiness: {} and [] are TRUE, unlike Python."""
    return v is not None and v is not False and v != 0 and v != ''

def normalised(p):
    """The object the creator rebuilds in loadDraft() and hashes; canonical key order.
       loadDraft():  v:i.v||0, title:i.title||"", notes:i.notes||[], locked:i.locked||!1,
                     bytes:i.bytes||{}, then dZones:i.dZones?i.dZones:[],
                     areas:i.areas?i.areas:[], then pic only when i.pic is truthy.
       `sign` and any unknown key are dropped before hashing."""
    n = {}
    n['v'] = p['v'] if js_truthy(p.get('v')) else 0
    n['title'] = p['title'] if js_truthy(p.get('title')) else ''
    n['notes'] = p['notes'] if js_truthy(p.get('notes')) else []
    n['locked'] = p['locked'] if js_truthy(p.get('locked')) else False
    n['bytes'] = p['bytes'] if js_truthy(p.get('bytes')) else {}
    n['dZones'] = p['dZones'] if js_truthy(p.get('dZones')) else []
    n['areas'] = p['areas'] if js_truthy(p.get('areas')) else []
    if js_truthy(p.get('pic')):
        n['pic'] = p['pic']
    return n

def tad_md5(p):
    return hashlib.md5(dumps_js(normalised(p)).encode('utf-8')).hexdigest()

# ---------------------------------------------------------------- records

def v1_records(p):
    """[(file_offset, u32_value)] in the file's key order."""
    out = []
    for k, val in (p.get('bytes') or {}).items():
        out.append((js_to_uint(js_parse_int(str(k)[1:], 10), 8), js_to_uint(js_parse_int(val, 10), 4)))
    return out

def dzone_default(p, addr, typ):
    """setInitialValues(): seed a zone from the areas, bug-for-bug."""
    val = 0
    for a in p.get('areas') or []:
        base = norm_addr(a.get('address', 0))
        tok = area_tokens(a)
        if not (base <= addr <= base + len(tok) - 1):
            continue
        k = addr - base
        v = js_parse_int(tok[k], 16)
        if v is None:
            val = None
            continue
        if typ > 1 and k + 1 < len(tok):
            v1 = js_parse_int(tok[k + 1], 16)
            v = None if v1 is None else v + 256 * v1
        if typ > 3 and v is not None and k + 3 < len(tok):
            v2, v3 = js_parse_int(tok[k + 2], 16), js_parse_int(tok[k + 3], 16)
            v = None if v2 is None or v3 is None else v + 65536 * v2 + 16777216 * v3
        val = v
    return val

def dzones(p, sets=None):
    """[(addr, type, tag, value)] with defaults seeded and --set overrides applied."""
    out = []
    for k, z in (p.get('dZones') or {}).items():
        addr = norm_addr(z.get('address', js_parse_int(str(k)[1:], 10)))
        typ = int(z.get('type', 1))
        tag = z.get('tag', '')
        if sets and tag in sets:
            val = int(sets[tag], 0)
        else:
            # setInitialValues() always re-seeds `value` from the areas, so any `value`
            # stored in the file is ignored by the loader.
            val = dzone_default(p, addr, typ)
        out.append((addr, typ, tag, val))
    return out

# ---------------------------------------------------------------- apply

def apply_patch(p, data, sets=None):
    """Returns (new_bytes, [out_of_range_offsets], [(off, orig_bytes)] for undo)."""
    buf = bytearray(data)
    skipped, touched = [], {}

    def poke(off, bs):
        for i, b in enumerate(bs):
            o = off + i
            if 0 <= o < len(buf):
                touched.setdefault(o, buf[o])
                buf[o] = b
            else:
                skipped.append(o)

    v = p.get('v')
    if v == 1:
        for off, word in v1_records(p):
            if 0 <= off and off + 4 <= len(buf):        # DataView.setUint32 bounds
                poke(off, word.to_bytes(4, 'little'))
            else:
                skipped.append(off)
    elif v == 2:
        for a in p.get('areas') or []:
            poke(norm_addr(a.get('address', 0)), area_bytes(a))
        for addr, typ, _tag, val in dzones(p, sets):
            if 0 <= addr and addr + typ <= len(buf):    # setUintN bounds
                poke(addr, js_to_uint(val, typ).to_bytes(typ, 'little'))
            else:
                skipped.append(addr)
    else:
        sys.exit('unsupported patch version %r (the loader only dispatches v==1 and v==2)' % v)
    return bytes(buf), skipped, sorted(touched.items())

def undo_patch(touched, title):
    """A v2 patch that puts the original bytes back."""
    areas, run = [], None
    for off, b in touched:
        if run is not None and off == run[0] + len(run[1]):
            run[1].append(b)
        else:
            run = (off, [b])
            areas.append(run)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {'v': 2, 'title': title, 'notes': [{'id': now + ' 0', 'text': 'undo made by tad.py', 'date': now}],
            'locked': False, 'bytes': {}, 'dZones': {},
            'areas': [{'address': o, 'data': fmt_data(bytes(bs)), 'isHex': False} for o, bs in areas]}

# ---------------------------------------------------------------- commands

def ram(off):
    return 0x80010000 + off - 0x800

def cmd_dump(args):
    p = load_tad(args.tad)
    v = p.get('v')
    print('tad v%s | title %r | locked=%r | md5(json)=%s' % (v, p.get('title', ''), p.get('locked'), tad_md5(p)))
    for n in p.get('notes') or []:
        print('  note [%s] %s' % (n.get('date', ''), n.get('text', '')) if isinstance(n, dict) else '  note %s' % n)
    if p.get('pic'):
        print('  pic  /Assets/img/tools/patch/%s' % p['pic'])
    if p.get('sign'):
        s = p['sign']
        print('  sign serial=%s user=%s athr=%s (decorative: patchloader never verifies it)'
              % (s.get('serial'), s.get('user'), s.get('athr')) if isinstance(s, dict) else '  sign %r' % s)
    if v == 1:
        for off, word in v1_records(p):
            print('  word  0x%06X%s = %08X' % (off, ram_s(off, args), word))
        print('  %d words, %d bytes' % (len(v1_records(p)), 4 * len(v1_records(p))))
        return
    tot = 0
    for a in p.get('areas') or []:
        off, bs = norm_addr(a.get('address', 0)), area_bytes(a)
        tot += len(bs)
        print('  area  0x%06X%s len %-4d %s' % (off, ram_s(off, args), len(bs), bs.hex(' ')))
    for addr, typ, tag, val in dzones(p):
        print('  dzone 0x%06X%s u%-3d %-20s default=%s' % (addr, ram_s(addr, args), 8 * typ, repr(tag), val))
    print('  %d areas, %d bytes, %d dynamic zones' % (len(p.get('areas') or []), tot, len(p.get('dZones') or {})))

def ram_s(off, args):
    return ' (%08X)' % ram(off) if getattr(args, 'slus', False) else ''

def cmd_json(args):
    print(json.dumps(load_tad(args.tad), indent=2, ensure_ascii=False))

def cmd_hash(args):
    p = load_tad(args.tad)
    print(tad_md5(p))
    if args.verbose:
        print(dumps_js(normalised(p)))

def cmd_verify(args):
    p = load_tad(args.tad)
    data = open(args.target, 'rb').read()
    print('target %s (%d bytes)' % (args.target, len(data)))
    recs = ([(off, w.to_bytes(4, 'little')) for off, w in v1_records(p)] if p.get('v') == 1
            else [(norm_addr(a.get('address', 0)), area_bytes(a)) for a in p.get('areas') or []])
    bad = 0
    for off, bs in recs:
        cur = data[off:off + len(bs)]
        same = cur == bs
        bad += 0 if same else 1
        print('  0x%06X%s len %-4d %s' % (off, ram_s(off, args), len(bs), 'ALREADY PATCHED' if same else ''))
        print('        file  %s' % cur.hex(' '))
        print('        patch %s' % bs.hex(' '))
    print('%d/%d records differ from the target' % (bad, len(recs)))

def cmd_apply(args):
    p = load_tad(args.tad)
    data = open(args.target, 'rb').read()
    sets = dict(s.split('=', 1) for s in (args.set or []))
    out, skipped, touched = apply_patch(p, data, sets)
    open(args.out, 'wb').write(out)
    print('%s -> %s | %d bytes changed' % (args.tad, args.out, sum(1 for o, b in touched if out[o] != b)))
    if skipped:
        print('%d writes fell outside the file - the site would say "Your %s file is not the '
              'size indicated for the patch."' % (len(skipped), args.target))
    if args.undo:
        save_tad(args.undo, undo_patch(touched, 'undo of ' + (p.get('title') or args.tad)))
        print('undo patch -> %s (apply it to get the stock file back byte-for-byte)' % args.undo)

def cmd_create(args):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    notes = [{'id': '%s %d' % (now, i), 'text': t, 'date': now} for i, t in enumerate(args.note or [])]
    if args.v1:
        p = {'v': 1, 'title': args.title, 'notes': notes, 'locked': False, 'bytes': {}}
        for spec in args.area or []:
            addr, hx = spec.split(':', 1)
            bs = bytes.fromhex(hx.replace(' ', ''))
            if len(bs) % 4:
                sys.exit('v1 records are whole 32-bit words; %s is %d bytes' % (spec, len(bs)))
            base = int(addr, 0)
            for i in range(0, len(bs), 4):
                p['bytes']['b%d' % (base + i)] = int.from_bytes(bs[i:i + 4], 'little')
        save_tad(args.out, p)
        print('wrote %s (v1, %d words)' % (args.out, len(p['bytes'])))
        return
    p = {'v': 2, 'title': args.title, 'notes': notes, 'locked': False, 'bytes': {},
         'dZones': {}, 'areas': []}
    for spec in args.area or []:
        addr, hx = spec.split(':', 1)
        p['areas'].append({'address': int(addr, 0),
                           'data': fmt_data(bytes.fromhex(hx.replace(' ', ''))), 'isHex': False})
    for spec in args.dzone or []:
        addr, typ, tag = spec.split(':', 2)
        addr = int(addr, 0)
        # the creator stores only {address,type,tag}; `value` is re-derived on load
        p['dZones']['b%d' % addr] = {'address': addr, 'type': int(typ), 'tag': tag}
    if args.pic:
        p['pic'] = args.pic
    save_tad(args.out, p)
    print('wrote %s (v2, %d areas, %d zones) md5=%s' % (args.out, len(p['areas']), len(p['dZones']), tad_md5(p)))
    print('unsigned - patchloader applies it as-is; patchcreator will refuse to reopen it')

def cmd_diff(args):
    a = open(args.stock, 'rb').read()
    b = open(args.modded, 'rb').read()
    n = min(len(a), len(b))
    areas, i = [], 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i + 1
        gap = 0
        while j < n and gap < args.gap:
            gap = gap + 1 if a[j] == b[j] else 0
            j += 1
        j -= gap
        areas.append({'address': i, 'data': fmt_data(b[i:j]), 'isHex': False})
        i = j
    if len(b) > n:
        areas.append({'address': n, 'data': fmt_data(b[n:]), 'isHex': False})
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    p = {'v': 2, 'title': args.title,
         'notes': [{'id': now + ' 0', 'text': 'made by tad.py diff', 'date': now}],
         'locked': False, 'bytes': {}, 'dZones': {}, 'areas': areas}
    save_tad(args.out, p)
    print('wrote %s: %d areas, %d bytes' % (args.out, len(areas),
                                            sum(len(area_bytes(x)) for x in areas)))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('dump'); s.add_argument('tad'); s.add_argument('--slus', action='store_true',
        help='also print RAM addresses (0x80010000 + off - 0x800)'); s.set_defaults(f=cmd_dump)
    s = sp.add_parser('json'); s.add_argument('tad'); s.set_defaults(f=cmd_json)
    s = sp.add_parser('hash'); s.add_argument('tad'); s.add_argument('-v', '--verbose', action='store_true')
    s.set_defaults(f=cmd_hash)
    s = sp.add_parser('verify'); s.add_argument('tad'); s.add_argument('target')
    s.add_argument('--slus', action='store_true'); s.set_defaults(f=cmd_verify)
    s = sp.add_parser('apply'); s.add_argument('tad'); s.add_argument('target')
    s.add_argument('-o', '--out', required=True); s.add_argument('--set', action='append',
        metavar='TAG=VALUE', help='override a dynamic zone'); s.add_argument('--undo',
        metavar='UNDO.TAD', help='also write a patch that restores the stock bytes')
    s.set_defaults(f=cmd_apply)
    s = sp.add_parser('create'); s.add_argument('out'); s.add_argument('--title', required=True)
    s.add_argument('--note', action='append'); s.add_argument('--area', action='append', metavar='ADDR:HEX')
    s.add_argument('--dzone', action='append', metavar='ADDR:TYPE:TAG'); s.add_argument('--pic')
    s.add_argument('--v1', action='store_true'); s.set_defaults(f=cmd_create)
    s = sp.add_parser('diff'); s.add_argument('stock'); s.add_argument('modded'); s.add_argument('out')
    s.add_argument('--title', required=True); s.add_argument('--gap', type=int, default=4,
        help='keep runs together across fewer than GAP equal bytes (default 4)')
    s.set_defaults(f=cmd_diff)
    a = ap.parse_args(); a.f(a)

if __name__ == '__main__':
    main()
