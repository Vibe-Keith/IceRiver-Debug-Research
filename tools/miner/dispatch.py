# Locate the 13-byte response dispatcher in a miner binary and map per-handler byte reads.
import sys,pickle,re,struct
pkl=sys.argv[1]; binf=sys.argv[2]
ins,xref,plt=pickle.load(open(pkl,'rb'))
d=open(binf,'rb').read()
idx={a:k for k,(a,_,_) in enumerate(ins)}
addrs=[a for a,_,_ in ins]
def S(va):  # string at vaddr (file base 0x10000)
    o=va-0x10000
    if 0<=o<len(d):
        b=d[o:o+48].split(b'\0')[0]
        if b and all(9<=c<127 for c in b): return b.decode(errors='replace')
    return None
# find 'unknown command' string va and its xref -> dispatcher
unk=None
for m in re.finditer(rb'unknown command',d):
    unk=m.start()+0x10000; break
disp=xref.get(unk,[])
# Find the dispatch cmp chain: search whole text for a run of cmp #0x80/#0x81/#0x8e/#0x82 within 60 insns
def find_dispatch():
    want={0x80,0x81,0x8e,0x82}
    for k,(a,mn,op) in enumerate(ins):
        if mn.startswith('cmp') and op.endswith('#0x80'):
            seen={0x80}; tgt={}
            for a2,m2,o2 in ins[k:k+40]:
                mm=re.search(r'#0x(8[0-9a-f])$',o2)
                if mm and m2.startswith('cmp'): cur=int(mm.group(1),16)
                if m2.startswith('beq') and 'cur' in dir():
                    t=o2.strip('#')
                    try: tgt[cur]=int(t,16)
                    except: pass
                mm2=re.search(r'#0x(8[0-9a-f])$',o2)
                if mm2: seen.add(int(mm2.group(1),16))
            if want.issubset(seen): return a,tgt
    return None,{}
dispa,tgt=find_dispatch()
# find frame-base: scan backward from dispa for the ldrb that reads the type byte [Rn,#imm]; base = that reg, typeoff=imm
basereg=None; typeoff=None
if dispa:
    k=idx[dispa]
    for a,mn,op in reversed(ins[max(0,k-12):k]):
        m=re.match(r'(r\d+|sb|sl|fp|ip|sp), \[(r\d+|sb|sl|fp|ip|sp), #(0x[0-9a-f]+)\]',op)
        if mn.startswith('ldrb') and m:
            basereg=m.group(2); typeoff=int(m.group(3),16); break
print('BIN',binf.split('/')[-1])
print(' dispatch@',hex(dispa) if dispa else None,'type-byte base=%s off=%s'%(basereg,hex(typeoff) if typeoff else None),'handlers',{hex(k):hex(v) for k,v in tgt.items()})
# For each handler, collect ldrb/ldrh/ldr [base, #off] reads until function boundary (push/next handler)
def reads(start,limit=160):
    if not start: return {}
    k=idx.get(start)
    if k is None: return {}
    offs={}
    base=basereg
    for a,mn,op in ins[k:k+limit]:
        if mn.startswith('push') or (a!=start and a in tgt.values()): break
        m=re.match(r'\S+, \[(r\d+|sb|sl|fp|ip|sp), #(0x[0-9a-f]+)\]',op)
        if m and (mn.startswith('ldrb') or mn.startswith('ldrh') or mn.startswith('ldr')):
            reg=m.group(1); off=int(m.group(2),16)
            if typeoff is not None and (off>=typeoff-11 and off<=typeoff+1):
                b=off-(typeoff-11)  # frame byte index (0..12) with type at 11
                offs[b]=mn[:4]
    return offs
if typeoff is not None:
    for ty in (0x80,0x81,0x82,0x8e):
        r=reads(tgt.get(ty))
        print('  %02X payload-bytes-read %s'%(ty,sorted(b for b in r if 2<=b<=10)))
