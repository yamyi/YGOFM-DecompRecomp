#!/usr/bin/env python3
"""Offline clone of TEA-Online's `extend/tools/data/disassembler`.

Reproduces, bug for bug, what the site's Vue tool does with an uploaded
SLUS_014.11 (or WA_MRG.MRG):

  dis        the on-screen table (ADDRESS FILE / RAM / HEX / OPCODE / ATTR / DESCRIPTION)
  functions  the unreachable `createAllOpcodes()` dump ("functions.bin")
  asm        the "GEN" button: mnemonic + fields -> instruction word
  patch      the "WRITE" button: poke one word at a file offset
  tad        read / create / apply / revert the .tad draft files
  coverage   how much of a real SLUS the tool's opcode table can actually name

Everything here mirrors `site/js/extend/tools/data/disassembler.3b67ed93.js`.
Where the site is wrong (see README "Bugs in the shipped tool") this script is
wrong the same way unless you pass --fix.

SLUS file offset -> RAM:  RAM = 0x8000F800 + off   (== 0x80010000 + (off - 0x800))
"""
import argparse, base64, json, struct, sys

RAM_BASE = 0x8000F800          # the tool's literal 2147547136
JR_RA    = 0x03E00008          # the tool's literal 65011720


# ---------------------------------------------------------------- decoding --
# getAttr(): v1=rs(25:21) v2=rt(20:16) v3=rd(15:11) v4=sa(10:6) v5=funct(5:0)
def attrs(w):
    return dict(v1=(w >> 21) & 0x1F, v2=(w >> 16) & 0x1F,
                v3=(w >> 11) & 0x1F, v4=(w >> 6) & 0x1F, v5=w & 0x3F)


def _imm(a):        # v3<<11 | v4<<6 | v5 -- the tool never sign-extends here
    return (a['v3'] << 11) + (a['v4'] << 6) + a['v5']


def _simm(a):
    v = _imm(a)
    return v - 0x10000 if v > 0x7FFF else v


def _tgt(a):
    return ((a['v1'] << 21) + (a['v2'] << 16) + (a['v3'] << 11)
            + (a['v4'] << 6) + a['v5'])


# the site's ATTR column formatters (names kept from the minified source)
F = {
    'l': lambda a: "${v3},${v1},${v2}".format(**a),
    'u': lambda a: "${v2} ${v1}({0})".format(_imm(a), **a),
    'd': lambda a: "function {0}".format(4 * _tgt(a) - 0xF800),
    'p': lambda a: "${v2},${v1},{0}".format(_imm(a), **a),
    'm': lambda a: "${v3},${v2}, {v4}".format(**a),
    'v': lambda a: "${v2},{0}".format(_imm(a), **a),
    'f': lambda a: "${v3},${v2},${v1}".format(**a),
    'h': lambda a: "${v1},${v2}".format(**a),
    'g': lambda a: "${v3}".format(**a),
    'b': lambda a: "${v1}".format(**a),
    'w': lambda a: "${v1},${v2}, {0}".format(_imm(a), **a),
    'y': lambda a: "${v1}, {0}".format(_imm(a), **a),
    'O': lambda a: "${v2},${v3}".format(**a),
    'jr': lambda a: "${v1}".format(**a),
    'jalr': lambda a: "${v3} = PC, PC={v1}".format(**a),
    'nul': lambda a: "",
}

# (name, description, ATTR formatter, DESCRIPTION text, is_branch)
SPECIAL = {                                             # op == 0, keyed by funct
    32: ("ADD",    "Add",                 'l', lambda a: "${v3} = ${v1} + ${v2}".format(**a)),
    33: ("ADDU",   "Add Unsigned",        'l', lambda a: "${v3} = ${v1} + ${v2}".format(**a)),
    36: ("AND",    "And",                 'l', lambda a: "${v3} = ${v1} & ${v2}".format(**a)),
    39: ("NOR",    "Nor",                 'l', lambda a: "${v3} = ~(${v1} | ${v2})".format(**a)),
    37: ("OR",     "Or",                  'l', lambda a: "${v3} = ${v1} | ${v2}".format(**a)),
    42: ("SLT",    "Set On Less Than",    'l', lambda a: "${v3} = ${v1} < ${v2}".format(**a)),
    43: ("SLTU",   "Set On Less Than U",  'l', lambda a: "${v3} = ${v1} < ${v2}".format(**a)),
    34: ("SUB",    "Subtract",            'l', lambda a: "${v3} = ${v1} - ${v2}".format(**a)),
    35: ("SUBU",   "Subtract Unsigned",   'l', lambda a: "${v3} = ${v1} - ${v2}".format(**a)),
    38: ("XOR",    "Xor",                 'l', lambda a: "${v3} = ${v1} ^ ${v2}".format(**a)),
    0:  ("SLL",    "Shift Left Logical",  'm', lambda a: "${v3} = ${v2} << {v4}".format(**a)),
    4:  ("SLLV",   "Shift Left Logical Variable",  'm', lambda a: "${v3} = ${v2} << ${v1}".format(**a)),
    3:  ("SRA",    "Shift Right Arith",   'm', lambda a: "${v3} = ${v2} >> {v4}".format(**a)),
    7:  ("SRAV",   "Shift Right Arith Variable",   'f', lambda a: "${v3} = ${v2} >> ${v1}".format(**a)),
    2:  ("SRL",    "Shift Right Logical", 'm', lambda a: "${v3} = ${v2} >> {v4}".format(**a)),
    6:  ("SRLV",   "Shift Right Logical Variable", 'f', lambda a: "${v3} = ${v2} >> ${v1}".format(**a)),
    26: ("DIV",    "Divide",              'h', lambda a: "LO=${v1}/${v2}; HI=${v1}%${v2}".format(**a)),
    27: ("DIVU",   "Divide Unsigned",     'h', lambda a: "LO=${v1}/${v2}; HI=${v1}%${v2}".format(**a)),
    16: ("MFHI",   "Move From HI",        'g', lambda a: "${v3} = HI".format(**a)),
    18: ("MFLO",   "Move From LO",        'g', lambda a: "${v3} = LO".format(**a)),
    17: ("MTHI",   "Move To HI",          'b', lambda a: "HI = ${v1}".format(**a)),
    19: ("MTLO",   "Move To LO",          'b', lambda a: "LO = ${v1}".format(**a)),
    24: ("MULT",   "Multiply",            'h', lambda a: "HI,LO = ${v1}*${v2}".format(**a)),
    25: ("MULTU",  "Multiply Unsigned",   'h', lambda a: "HI,LO = ${v1}*${v2}".format(**a)),
    13: ("BREAK",  "Breakpoint",          'nul', lambda a: "epc=pc; pc=0x3c"),
    9:  ("JALR",   "Jump And Link Register", 'jalr', lambda a: "${v3} = PC, PC= ${v1}".format(**a)),
    8:  ("JR",     "Jump Register",       'jr', lambda a: "PC= ${v1}".format(**a)),
    12: ("SYSCALL", "System Call",        'nul', lambda a: "epc=pc; pc=0x3c"),
}
REGIMM = {                                              # op == 1, keyed by rt
    1:  ("BGEZ",   "Branch On >= 0",      'y', lambda a: "if(${v1}>=0) pc+={0}*4".format(_simm(a), **a), True),
    17: ("BGEZAL", "Branch On >= 0 And Link", 'y', lambda a: "$31 = PC; if(${v1}>=0) pc+={0}*4".format(_simm(a), **a), True),
    0:  ("BLTZ",   "Branch On < 0",       'y', lambda a: "if(${v1}<0) pc+={0}*4".format(_simm(a), **a), True),
    16: ("BLTZAL", "Branch On < 0 And Link",  'y', lambda a: "$31 = PC; if(${v1}<0) pc+={0}*4".format(_simm(a), **a), True),
}
COP0 = {                                                # op == 16, keyed by rs
    0: ("MFC0", "Move From Coprocessor", 'O', lambda a: "${v2}=CPR[0,${v3}]".format(**a)),
    4: ("MTC0", "Move To Coprocessor",   'O', lambda a: "=CPR[0,${v3}]=${v2}".format(**a)),
}
MAIN = {                                                # every other op
    8:  ("ADDI",  "Add Immediate",          'p', lambda a: "${v2} = ${v1} + {0}".format(_simm(a), **a)),
    9:  ("ADDIU", "Add Immediate Unsigned", 'p', lambda a: "${v2} = ${v1} + {0}".format(_simm(a), **a)),
    12: ("ANDI",  "And Immediate",          'p', lambda a: "${v2} = ${v1} & {0}".format(_imm(a), **a)),
    15: ("LUI",   "Load Upper Immediate",   'v', lambda a: "${v2} = {0:04X} << 16".format(_imm(a), **a)),
    13: ("ORI",   "Or Immediate",           'p', lambda a: "${v2} = ${v1} | {0}".format(_imm(a), **a)),
    10: ("SLTI",  "Set On Less Than Immediate",  'p', lambda a: "${v2} = ${v1} < {0}".format(_simm(a), **a)),
    11: ("SLTIU", "Set On Less Than Immediate U", 'p', lambda a: "${v2} = ${v1} < {0}".format(_imm(a), **a)),
    14: ("XORI",  "Xor Immediate",          'p', lambda a: "${v2} = ${v1} ^ {0}".format(_imm(a), **a)),
    4:  ("BEQ",   "Branch On Equal",        'w', lambda a: "if(${v1} == ${v2}) pc+={0}*4".format(_simm(a), **a), True),
    7:  ("BGTZ",  "Branch On > 0",          'y', lambda a: "if(${v1} > 0) pc+={0}*4".format(_simm(a), **a), True),
    6:  ("BLEZ",  "Branch On",              'y', lambda a: "if(${v1} <= 0) pc+={0}*4".format(_simm(a), **a), True),
    5:  ("BNE",   "Branch On Not Equal",    'w', lambda a: "if(${v1} != ${v2}) pc+={0}*4".format(_simm(a), **a), True),
    2:  ("J",     "Jump",                   'd', lambda a: "pc=pc_upper|({0}<<2)".format(_tgt(a))),
    3:  ("JAL",   "Jump And Link",          'd', lambda a: "$31 = PC; pc={0}<<2".format(_tgt(a))),
    32: ("LB",    "Load Byte",              'u', lambda a: "${v2} <- {0} + ${v1} (*char)".format(_simm(a), **a)),
    36: ("LBU",   "Load Byte Unsigned",     'u', lambda a: "${v2} <- {0} + ${v1} (*Uchar)".format(_simm(a), **a)),
    33: ("LH",    "Load Halfword",          'u', lambda a: "${v2} <- {0} + ${v1} (*short)".format(_simm(a), **a)),
    37: ("LHU",   "Load Halfword Unsigned", 'u', lambda a: "${v2} <- {0} + ${v1} (*Ushort)".format(_simm(a), **a)),
    35: ("LW",    "Load Word",              'u', lambda a: "${v2} <- {0} + ${v1} (*word)".format(_simm(a), **a)),
    40: ("SB",    "Store Byte",             'u', lambda a: "${v2} -> {0} + ${v1} (*char)".format(_simm(a), **a)),
    41: ("SH",    "Store Halfword",         'u', lambda a: "${v2} -> {0} + ${v1} (*short)".format(_simm(a), **a)),
    43: ("SW",    "Store Word",             'u', lambda a: "${v2} -> (${v1}+{0}) (*int)".format(_simm(a), **a)),
}


def decode(w):
    """parseCode(): returns (name, attr_text, description_text, branch_off|None)."""
    a = attrs(w)
    if w == 0:
        return ("NOP", "", "", None)
    op = w >> 26
    ent = None
    if op == 0:
        ent = SPECIAL.get(w & 0x3F)
    elif op == 1:
        ent = REGIMM.get((w >> 16) & 0x1F)
    elif op == 16:
        ent = COP0.get((w >> 21) & 0x1F)
    else:
        ent = MAIN.get(op)
    if ent is None:
        # the site leaves the default object: name NONE, zeroed attrs, no text
        return ("NONE", "", "", None)
    name, _des, form, xpl = ent[0], ent[1], ent[2], ent[3]
    branch = _simm(a) if len(ent) > 4 and ent[4] else None
    return (name, F[form](a), xpl(a), branch)


# ---------------------------------------------------------------- assembler --
def _b(v, n):
    return format(int(v) & ((1 << n) - 1), '0%db' % n)


ASM = {  # mnemonic -> (lambda fields -> bitstring, description, needed fields)
    'add':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100000", "rd=rs+rt"),
    'addi':  (lambda f: "001000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs+imm"),
    'addiu': (lambda f: "001001" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs+imm"),
    'addu':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100001", "rd=rs+rt"),
    'and':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100100", "rd=rs&rt"),
    'andi':  (lambda f: "001100" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs&imm"),
    'lui':   (lambda f: "00111100000" + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=imm<<16"),
    'nor':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100111", "rd=~(rs|rt)"),
    'or':    (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100101", "rd=rs|rt"),
    'ori':   (lambda f: "001101" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs|imm"),
    'slt':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000101010", "rd=rs<rt"),
    'slti':  (lambda f: "001010" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs<imm"),
    'sltiu': (lambda f: "001011" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs<imm"),
    'sltu':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000101011", "rd=rs<rt"),
    'sub':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100010", "rd=rs-rt"),
    'subu':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100011", "rd=rs-rt"),
    'xor':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000100110", "rd=rs^rt"),
    'xori':  (lambda f: "001110" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=rs^imm"),
    'sll':   (lambda f: "00000000000" + _b(f['rt'], 5) + _b(f['rd'], 5) + _b(f['sa'], 5) + "000000", "rd=rt<<sa"),
    'sllv':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000000100", "rd=rt<<rs"),
    'sra':   (lambda f: "00000000000" + _b(f['rt'], 5) + _b(f['rd'], 5) + _b(f['sa'], 5) + "000011", "rd=rt>>sa"),
    'srav':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000000111", "rd=rt>>rs"),
    'srl':   (lambda f: "00000000000" + _b(f['rt'], 5) + _b(f['rd'], 5) + _b(f['sa'], 5) + "000010", "rd=rt>>sa"),
    'srlv':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000000110", "rd=rt>>rs"),
    'div':   (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + "0000000000011010", "HI=rs%rt; LO=rs/rt"),
    'divu':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + "0000000000011011", "HI=rs%rt; LO=rs/rt"),
    'mfhi':  (lambda f: "0000000000000000" + _b(f['rd'], 5) + "00000010000", "rd=HI"),
    'mflo':  (lambda f: "0000000000000000" + _b(f['rd'], 5) + "00000010010", "rd=LO"),
    'mthi':  (lambda f: "000000" + _b(f['rs'], 5) + "000000000000000010001", "HI=rs"),
    # BUG in the shipped tool: funct 010010 is MFLO, MTLO is 010011.  --fix corrects it.
    'mtlo':  (lambda f: "000000" + _b(f['rs'], 5) + "0000000000000000100" + ("11" if f.get('_fix') else "10"), "LO=rs"),
    'mult':  (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + "0000000000011000", "HI,LO=rs*rt"),
    'multu': (lambda f: "000000" + _b(f['rs'], 5) + _b(f['rt'], 5) + "0000000000011001", "HI,LO=rs*rt"),
    'beq':   (lambda f: "000100" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "if(rs==rt) pc+=off*4"),
    'bgez':  (lambda f: "000001" + _b(f['rs'], 5) + "00001" + _b(f['imm'], 16), "if(rs>=0) pc+=off*4"),
    'bgezal': (lambda f: "000001" + _b(f['rs'], 5) + "10001" + _b(f['imm'], 16), "r31=pc; if(rs>=0)"),
    'bgtz':  (lambda f: "000111" + _b(f['rs'], 5) + "00000" + _b(f['imm'], 16), "if(rs>0) pc+=off*4"),
    'blez':  (lambda f: "000110" + _b(f['rs'], 5) + "00000" + _b(f['imm'], 16), "if(rs<=0) pc+=off*4"),
    'bltz':  (lambda f: "000001" + _b(f['rs'], 5) + "00000" + _b(f['imm'], 16), "if(rs<0) pc+=off*4"),
    'bltzal': (lambda f: "000001" + _b(f['rs'], 5) + "10000" + _b(f['imm'], 16), "r31=pc; if(rs<0)"),
    'bne':   (lambda f: "000101" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "if(rs!=rt) pc+=off*4"),
    # the site builds `code` out of the imm INPUT box, not a code box (C() bug)
    'break': (lambda f: "000000" + _b(f['imm'], 20) + "001101", "epc=pc; pc=0x3c"),
    'j':     (lambda f: "000010" + _b(f['tgt'], 26), "pc=pc_upper|(tgt<<2)"),
    'jal':   (lambda f: "000011" + _b(f['tgt'], 26), "r31=pc; pc=tgt<<2"),
    'jalr':  (lambda f: "000000" + _b(f['rs'], 5) + "00000" + _b(f['rd'], 5) + "00000001001", "rd=pc; pc=rs"),
    'jr':    (lambda f: "000000" + _b(f['rs'], 5) + "000000000000000001000", "pc=rs"),
    'mfc0':  (lambda f: "01000000000" + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000000000", "rt=CPR[0,rd]"),
    'mtc0':  (lambda f: "01000000100" + _b(f['rt'], 5) + _b(f['rd'], 5) + "00000000000", "CPR[0,rd]=rt"),
    'syscall': (lambda f: "000000" + _b(f['imm'], 20) + "001100", "epc=pc; pc=0x3c"),
    'lb':    (lambda f: "100000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=*(char*)(off+rs)"),
    'lbu':   (lambda f: "100100" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=*(Uchar*)(off+rs)"),
    'lh':    (lambda f: "100001" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=*(short*)(off+rs)"),
    'lhu':   (lambda f: "100101" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=*(Ushort*)(off+rs)"),
    'lw':    (lambda f: "100011" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "rt=*(int*)(off+rs)"),
    'sb':    (lambda f: "101000" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "*(char*)(off+rs)=rt"),
    'sh':    (lambda f: "101001" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "*(short*)(off+rs)=rt"),
    'sw':    (lambda f: "101011" + _b(f['rs'], 5) + _b(f['rt'], 5) + _b(f['imm'], 16), "*(int*)(off+rs)=rt"),
}


def assemble(mn, fields, fix=False):
    if mn not in ASM:
        sys.exit("unknown mnemonic %r (the tool ships %d: %s)"
                 % (mn, len(ASM), " ".join(sorted(ASM))))
    f = dict(rs=0, rt=0, rd=0, sa=0, imm=0, code=0, tgt=0)
    f.update({k: v for k, v in fields.items() if v is not None})
    f['_fix'] = fix
    return int(ASM[mn][0](f), 2) & 0xFFFFFFFF


# the site's "tgt" helper buttons (P.tgt.f2 / f3)
def tgt_from_ram(ram):     # "Ram Address": last 6 hex chars / 4
    return int(("%08X" % ram)[-6:], 16) // 4


def tgt_from_slus(off):    # "Slus Address": (offset + 0xF800) / 4
    return (off + 0xF800) // 4


# ------------------------------------------------------------------- .tad ----
def tad_load(path):
    raw = open(path, 'rb').read()
    return json.loads(base64.b64decode(raw).decode())


def tad_save(path, obj):
    open(path, 'wb').write(base64.b64encode(json.dumps(obj).encode()))


def tad_words(t):
    """-> [(file_offset, word)] for both v1 (bytes dict) and v2 (areas list)."""
    out = []
    if isinstance(t.get('bytes'), dict) and t['bytes']:
        for k, v in t['bytes'].items():
            out.append((int(str(k).lstrip('c')), int(v) & 0xFFFFFFFF))
    for area in t.get('areas') or []:
        b = bytes(int(x, 16) for x in area['data'].split())
        for i in range(0, len(b) - 3, 4):
            out.append((area['address'] + i,
                        struct.unpack_from('<I', b, i)[0]))
    return sorted(out)


# ------------------------------------------------------------------ output ---
def cmd_dis(a):
    d = open(a.file, 'rb').read()
    off = a.offset
    for i in range(a.count):
        p = off + 4 * i
        if p + 4 > len(d):
            break
        w = struct.unpack_from('<I', d, p)[0]
        name, attr, xpl, br = decode(w)
        ram = "%08X " % (RAM_BASE + p) if a.ram else ""
        tgt = ""
        if br is not None and a.targets:
            tgt = "   -> %d (%08X)" % (p + 4 + 4 * br, RAM_BASE + p + 4 + 4 * br)
        print("%s%-8d %08X  %-8s %-22s %s%s" % (ram, p, w, name, attr, xpl, tgt))


def cmd_functions(a):
    """Byte-exact clone of the unreachable createAllOpcodes() (functions.bin)."""
    d = open(a.file, 'rb').read()
    n = (a.end - a.start) // 4
    txt = "FUNCTION %d\n\n" % a.start
    fresh = True
    for o in range(n):
        p = a.start + 4 * o
        w = struct.unpack_from('<I', d, p)[0]
        name, attr, xpl, _ = decode(w)
        txt += "%s %d %s %s %s\n" % (("%X" % (RAM_BASE + p)), p, name, attr, xpl)
        if not fresh:
            txt += "\n\nFUNCTION %d %s\n\n" % (
                a.start + 4 * (o + 1), "%X" % (RAM_BASE + a.start + 4 * (o + 1)))
            fresh = True
        if w == JR_RA:
            fresh = False
    open(a.out, 'w').write(txt)
    print("wrote %s (%d bytes, %d words)" % (a.out, len(txt), n))


def cmd_asm(a):
    w = assemble(a.mnemonic.lower(),
                 dict(rs=a.rs, rt=a.rt, rd=a.rd, sa=a.sa, imm=a.imm, tgt=a.tgt),
                 fix=a.fix)
    name, attr, xpl, _ = decode(w)
    print("%08X   (%s %s   %s)" % (w, name, attr, xpl))


def cmd_patch(a):
    d = bytearray(open(a.file, 'rb').read())
    old = struct.unpack_from('<I', d, a.offset)[0]
    struct.pack_into('<I', d, a.offset, a.word)
    out = a.out or a.file
    open(out, 'wb').write(d)
    print("%s @%d (RAM %08X): %08X -> %08X" %
          (out, a.offset, RAM_BASE + a.offset, old, a.word))


def cmd_tad(a):
    if a.tadcmd == 'show':
        t = tad_load(a.tad)
        print("v=%s  title=%r  locked=%s  sign=%s"
              % (t.get('v'), t.get('title'), t.get('locked'), t.get('sign', '-')))
        for n in t.get('notes') or []:
            print("  note %s [%s] %s" % (n.get('id'), n.get('date'), n.get('text')))
        for off, w in tad_words(t):
            name, attr, xpl, _ = decode(w)
            print("  %-8d RAM %08X  %08X  %-8s %-20s %s"
                  % (off, RAM_BASE + off, w, name, attr, xpl))
    elif a.tadcmd in ('apply', 'revert'):
        t = tad_load(a.tad)
        d = bytearray(open(a.file, 'rb').read())
        stock = bytearray(open(a.stock, 'rb').read()) if a.stock else None
        for off, w in tad_words(t):
            if a.tadcmd == 'apply':
                struct.pack_into('<I', d, off, w)
            else:
                if stock is None:
                    sys.exit("revert needs --stock <clean SLUS_014.11>")
                d[off:off + 4] = stock[off:off + 4]
        out = a.out or a.file
        open(out, 'wb').write(d)
        print("%s %d word(s) -> %s" % (a.tadcmd, len(tad_words(t)), out))
    elif a.tadcmd == 'make':
        words = {}
        for spec in a.word:
            off, hexw = spec.split('=')
            words["c%d" % int(off, 0)] = int(hexw, 16)
        tad_save(a.out, dict(v=1, title=a.title, notes=[], locked=False, bytes=words))
        print("wrote %s (v1, %d word(s))" % (a.out, len(words)))


def cmd_coverage(a):
    d = open(a.file, 'rb').read()
    end = a.end if a.end else len(d)
    tot = un = 0
    hist = {}
    for p in range(a.start, end - 3, 4):
        w = struct.unpack_from('<I', d, p)[0]
        tot += 1
        if decode(w)[0] == "NONE":
            un += 1
            hist[w >> 26] = hist.get(w >> 26, 0) + 1
    print("%d words in [%d,%d)  %d undecodable (%.2f%%)" % (tot, a.start, end, un, 100.0 * un / tot))
    for op, n in sorted(hist.items(), key=lambda kv: -kv[1])[:12]:
        print("   op %2d (0x%02X): %d" % (op, op, n))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    q = sub.add_parser('dis', help="the tool's on-screen listing")
    q.add_argument('file')
    q.add_argument('--offset', type=lambda s: int(s, 0), default=29184)
    q.add_argument('--count', type=int, default=100)
    q.add_argument('--ram', action='store_true')
    q.add_argument('--targets', action='store_true', help="resolve branch targets (the site only highlights them)")
    q.set_defaults(func=cmd_dis)

    q = sub.add_parser('functions', help="clone of the dead createAllOpcodes() dump")
    q.add_argument('file')
    q.add_argument('--start', type=lambda s: int(s, 0), required=True)
    q.add_argument('--end', type=lambda s: int(s, 0), required=True)
    q.add_argument('-o', '--out', default='functions.bin')
    q.set_defaults(func=cmd_functions)

    q = sub.add_parser('asm', help="the GEN button")
    q.add_argument('mnemonic')
    for f in ('rs', 'rt', 'rd', 'sa', 'imm', 'tgt'):
        q.add_argument('--' + f, type=lambda s: int(s, 0))
    q.add_argument('--fix', action='store_true', help="correct the mtlo funct bug")
    q.set_defaults(func=cmd_asm)

    q = sub.add_parser('patch', help="the WRITE button")
    q.add_argument('file')
    q.add_argument('offset', type=lambda s: int(s, 0))
    q.add_argument('word', type=lambda s: int(s, 16))
    q.add_argument('-o', '--out')
    q.set_defaults(func=cmd_patch)

    q = sub.add_parser('tad', help=".tad drafts")
    q.add_argument('tadcmd', choices=['show', 'apply', 'revert', 'make'])
    q.add_argument('tad', nargs='?')
    q.add_argument('--file', help="SLUS to apply/revert against")
    q.add_argument('--stock', help="clean SLUS_014.11 for revert")
    q.add_argument('--title', default="")
    q.add_argument('--word', action='append', default=[], metavar='OFF=HEXWORD')
    q.add_argument('-o', '--out')
    q.set_defaults(func=cmd_tad)

    q = sub.add_parser('coverage', help="how much of a file the opcode table names")
    q.add_argument('file')
    q.add_argument('--start', type=lambda s: int(s, 0), default=0x800)
    q.add_argument('--end', type=lambda s: int(s, 0), default=0)
    q.set_defaults(func=cmd_coverage)

    a = p.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
