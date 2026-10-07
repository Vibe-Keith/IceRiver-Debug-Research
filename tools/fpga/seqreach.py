# Sequential reachability on a site-pin graph: slice inputs->outputs within slice; BRAM in->out.
import sys,pickle,collections,heapq
nets=pickle.load(open(sys.argv[1],'rb'))
cells,drv,loads=pickle.load(open(sys.argv[2],'rb'))
fwd=collections.defaultdict(set)
for d,s in nets:
    if s[2] in('CLK','WRCLK','RDCLK','CLKARDCLK','CLKBWRCLK'): continue
    fwd[(d[0],d[2])].add((s[0],s[2]))
def intra(I,pin):
    """slice input pin -> list of (output pin, is_seq)"""
    c=cells.get(I)
    if I.startswith('RAMB'): return [((I,'DO*'),1)]
    if not c: return []
    L=pin[0]; res=[]
    if pin in('CE','SR'): return []
    if pin[1:].isdigit() or pin in ('AX','BX','CX','DX','CIN'):
        Ls=[L] if pin!='CIN' else list('ABCD')
        for l in Ls:
            res.append(((I,l),0)); res.append(((I,l+'MUX'),0)); res.append(((I,l+'Q'),1)); res.append(((I,'COUT'),0))
            if c['ff5'].get(l): res.append(((I,l+'MUX'),1))
        if pin=='AX' or pin=='CIN':
            for l in 'BCD': res+= [((I,l+'Q'),1),((I,l+'MUX'),0)]
    return res
ramouts=[('RAMB18_X0Y20','DO%d'%i) for i in range(32)]+[('RAMB18_X0Y20','DOP%d'%i) for i in range(4)]
def run(src):
    dist={src:0};pq=[(0,src)]
    while pq:
        dd,u=heapq.heappop(pq)
        if dd>dist.get(u,1e9): continue
        for v in fwd.get(u,()):
            # v is a sink pin; propagate inside
            if dist.get(v,1e9)>dd: dist[v]=dd; heapq.heappush(pq,(dd,v))
            if v[0].startswith('RAMB'):
                for o in ramouts:
                    if dist.get(o,1e9)>dd+1: dist[o]=dd+1; heapq.heappush(pq,(dd+1,o))
            for (o,seq) in intra(*v):
                if dist.get(o,1e9)>dd+seq: dist[o]=dd+seq; heapq.heappush(pq,(dd+seq,o))
    return dist
for a in sys.argv[4:]:
    s,p=a.split(':'); dist=run((s,p))
    hits={k:v for k,v in dist.items() if k[0].startswith(('OLOGIC','PS7')) and k[1] in('D1','T1') or (k[0]=='PS7_X0Y0' and k[1].startswith('EMIO') and k!=(s,p))}
    tgt=sys.argv[3].split(',')
    print('==',a,'reaches', len(dist),'pins; BRAM:', min([dist[o] for o in ramouts if o in dist],default=None))
    for k,v in sorted(hits.items(),key=lambda x:x[1]):
        if any(t in k[0] or t in k[1] for t in tgt): print('   ',k,'FF-depth',v)
