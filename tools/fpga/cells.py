# Build a cell-level model of CLB logic from FASM + directed site netlist.
import sys,pickle,re,collections,json
nets=pickle.load(open(sys.argv[1],'rb')); fasmf=sys.argv[2]; out=sys.argv[3]
feat=collections.defaultdict(dict)
for l in open(fasmf):
    l=l.strip()
    m=re.match(r'(CLBL[LM]_[LR]_X\d+Y\d+)\.SLICE[LM]_X([01])\.(\S+?)(?: = (\S+))?$',l)
    if not m: continue
    t,x,f,v=m.groups(); key='%s.SLICE_X%s'%(t,x)
    if v and "'b" in v:
        bits=v.split("'b")[1]; mm=re.match(r'(.*)\[(\d+):(\d+)\]',f)
        feat[key][mm.group(1)]=int(bits,2)
    else:
        mm=re.match(r'(.*)\[(\d+)\]$',f)
        if mm and 'INIT' in f: feat[key][mm.group(1)]=feat[key].get(mm.group(1),0)|(1<<int(mm.group(2)))
        else: feat[key][f]=True
inst={}  # tile.SLICE_Xk -> instance
drv=collections.defaultdict(list)  # (inst,pin) -> [(src inst,pin)]
loads=collections.defaultdict(list)
for d,s in nets:
    for e in (d,s):
        if e[1].startswith('SLICE'): inst[e[3]]=e[0]
    drv[(s[0],s[2])].append((d[0],d[2]))
    loads[(d[0],d[2])].append((s[0],s[2]))
cells={}
for key,f in feat.items():
    if key not in inst: continue
    I=inst[key]; c={'tile':key,'lut':{},'ff':{},'ff5':{},'outmux':{},'carry':False,'f':sorted(k for k in f if not k.endswith('INIT'))}
    for L in 'ABCD':
        if L+'LUT.INIT' in f: c['lut'][L]=f[L+'LUT.INIT']
        for k in f:
            if k.startswith(L+'FFMUX.'): c['ff'][L]=k.split('.')[1]
            if k.startswith(L+'5FFMUX.'): c['ff5'][L]=k.split('.')[1]
            if k.startswith(L+'OUTMUX.'): c['outmux'][L]=k.split('.')[1]
        if (L+'FF.ZINI' in f or L+'FF.ZRST' in f) and L not in c['ff']: c['ff'][L]='?'
    c['carry']=any(k.startswith(('CARRY4','PRECYINIT')) and k!='PRECYINIT.C0' for k in f) or any(v=='XOR' or v=='CY' for v in list(c['ff'].values())+list(c['outmux'].values()))
    cells[I]=c
pickle.dump((cells,dict(drv),dict(loads)),open(out,'wb'))
print('slices',len(cells),'luts',sum(len(c['lut']) for c in cells.values()),'ffs',sum(len(c['ff']) for c in cells.values()),'ff5',sum(len(c['ff5']) for c in cells.values()),'carry slices',sum(c['carry'] for c in cells.values()))
