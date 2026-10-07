# Directed netlist: sink site input pin -> driving site output pin(s), through active routing.
import sys,pickle,collections,json,os,glob
edges,redges,sitepin=pickle.load(open(sys.argv[1],'rb')); D=sys.argv[3]
dirs={}
for fn in glob.glob(D+'/site_type_*.json'):
    j=json.load(open(fn)); dirs[j['type']]={k:v['direction'] for k,v in j['site_pins'].items()}
def isout(t,p): return dirs.get(t,{}).get(p)=='OUT'
def isin(t,p): return dirs.get(t,{}).get(p)=='IN'
uf=pickle.load(open(sys.argv[1].replace('.graph.pkl','.uf.pkl'),'rb'))
const={}
for k,root in uf.items():
    if k[1]=='VCC_WIRE': const[root]=('VCC','CONST','1','')
    if k[1]=='GND_WIRE': const[root]=('GND','CONST','0','')
for k in list(uf): pass
def drivers(n,maxn=5000):
    seen={n};q=collections.deque([n]);hits=set()
    while q and len(seen)<maxn:
        x=q.popleft()
        if x in const or x[1] in ('VCC_WIRE','GND_WIRE'):
            hits.add(const.get(x) or (('VCC','CONST','1','') if x[1]=='VCC_WIRE' else ('GND','CONST','0',''))); continue
        outs=[sp for sp in sitepin.get(x,[]) if isout(sp[1],sp[2])]
        if outs: hits.update(outs); continue
        for m in redges.get(x,()):
            if m not in seen: seen.add(m); q.append(m)
    return hits
nets=[]
for n,lst in sitepin.items():
    if n not in redges: continue
    for sp in lst:
        if not isin(sp[1],sp[2]): continue
        for d in drivers(n):
            if d[1]=='TIEOFF': d=('VCC' if 'HARD1' in d[2] or 'VCC' in d[2] else 'GND','CONST','1' if ('HARD1' in d[2] or 'VCC' in d[2]) else '0','')
            nets.append((d,sp))
pickle.dump(nets,open(sys.argv[2],'wb'))
print(len(nets))
