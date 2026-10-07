import sys,pickle,collections,re
nets=pickle.load(open(sys.argv[1],'rb'))
iob={}
for l in open(sys.argv[2]):
    p=l.split(); iob[p[1].replace('IOB_','')]=(p[0],p[2])
usedtile=set()
for l in open(sys.argv[3]):
    m=re.match(r'(CLBL[LM]_[LR]_X\d+Y\d+)\.SLICE[LM]_X([01])\.',l)
    if m: usedtile.add('%s.SLICE_X%s'%(m.group(1),m.group(2)))
    m=re.match(r'(BRAM_[LR]_X\d+Y\d+)\.RAMB18_Y([01])\.IN_USE',l)
    if m: usedtile.add('%s.RAMB18_Y%s'%m.groups())
def node(s,t,p,tl):
    if t.startswith(('SLICE')): return s if tl in usedtile else None
    if t.startswith(('ILOGIC','OLOGIC','IOB','IDELAY')):
        if not ((t.startswith('ILOGIC') and p=='O') or (t.startswith('OLOGIC') and p in ('D1','T1'))): return None
        k=re.sub(r'^(ILOGIC|OLOGIC|IOB|IDELAY)_','',s)
        return 'PAD:'+k if k in iob else None
    if t=='PS7': return 'PS7:'+p if p.startswith('EMIO') else None
    if t.startswith('RAMB'): return s if s=='RAMB18_X0Y20' else None
    if t.startswith(('MMCM','BUFG','BUFH','PLL')): return s
    return None
par={}
def f(x):
    while par.get(x,x)!=x: x=par[x]
    return x
def u(a,b):
    a,b=f(a),f(b)
    if a!=b: par[a]=b
allsl=set()
for d,s in nets:
    if d[1].startswith(('BUFG','BUFH','MMCM')) or s[2] in ('SR','CE','CLK','CLKARDCLK','CLKBWRCLK','CLKARDCLKL','CLKBWRCLKL','CLKARDCLKU','CLKBWRCLKU'): continue
    a,b=node(*d),node(*s)
    if a and b: u(a,b); allsl.update([a,b])
groups=collections.defaultdict(set)
for x in allsl: groups[f(x)].add(x)
for m in sorted(groups.values(),key=len,reverse=True):
    sl=[x for x in m if x.startswith('SLICE')]
    ps=sorted(x[4:] for x in m if x.startswith('PS7:'))
    pads=sorted('%s(%s)'%(iob.get(x[4:],('?',))[0],x[4:]) for x in m if x.startswith('PAD:'))
    other=sorted(x for x in m if not x.startswith(('SLICE','PS7:','PAD:')))
    print('slices=%d\n  PS7: %s\n  pads: %s\n  other: %s'%(len(sl),' '.join(ps),' '.join(pads),' '.join(other)))
