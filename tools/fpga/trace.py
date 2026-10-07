# Build node graph for xc7z010 from prjxray DB + active PIPs from FASM; trace IOB nets.
import sys,json,pickle,os,collections,re
sys.path.insert(0,sys.argv[1]); D=sys.argv[2]; fasmf=sys.argv[3]; out=sys.argv[4]
from prjxray.db import Database
db=Database(D,'xc7z010clg400-1'); grid=json.load(open(D+'/xc7z010/tilegrid.json'))
cache=out+'.uf.pkl'
if os.path.exists(cache): parent=pickle.load(open(cache,'rb'))
else:
    parent={}
    def find(x):
        while parent.get(x,x)!=x:
            parent[x]=parent.get(parent[x],parent[x]); x=parent[x]
        return x
    for c in db.connections().get_connections():
        a=(c.wire_a.tile,c.wire_a.wire); b=(c.wire_b.tile,c.wire_b.wire)
        ra,rb=find(a),find(b)
        if ra!=rb: parent[ra]=rb
    for k in list(parent): parent[k]=find(k)
    pickle.dump(parent,open(cache,'wb'))
node=lambda tw: parent.get(tw,tw)
# tile types json
tt={}
def ttype(t):
    ty=grid[t]['type']
    if ty not in tt: tt[ty]=json.load(open(D+'/tile_type_%s.json'%ty))
    return tt[ty]
# active pips
edges=collections.defaultdict(set); redges=collections.defaultdict(set)
def add(t,src,dst):
    a,b=node((t,src)),node((t,dst)); edges[a].add(b); redges[b].add(a)
feats=[l.strip() for l in open(fasmf) if l.strip() and not l.startswith('#')]
pipset={}
for f in feats:
    p=f.split('.')
    if len(p)!=3: continue
    t,dst,src=p
    if t not in grid: continue
    j=ttype(t)
    key=grid[t]['type']
    if key not in pipset: pipset[key]={(v['dst_wire'],v['src_wire']) for v in j['pips'].values()}
    if (dst,src) in pipset[key]: add(t,src,dst)
# always ppips
for t,g in grid.items():
    fn=D+'/ppips_%s.db'%g['type'].lower()
    if not os.path.exists(fn): continue
    for l in open(fn):
        n,kind=l.split()
        if kind=='always' and 'CASC' not in n:
            _,dst,src=n.split('.'); add(t,src,dst)
# site pins
sitepin={}
for t,g in grid.items():
    j=ttype(t)
    names=sorted(g.get('sites',{}).items())
    for s in j['sites']:
        # map type-local site to instance name by prefix/xy order
        inst=[n for n,ty in names if n.startswith(s['prefix']+'_')]
        # choose by relative coords
        xs=sorted({int(re.search(r'X(\d+)Y',n).group(1)) for n in inst}) ; ys=sorted({int(re.search(r'Y(\d+)$',n).group(1)) for n in inst})
        try: iname='%s_X%dY%d'%(s['prefix'],xs[s['x_coord']],ys[s['y_coord']])
        except Exception: iname='%s:%s_X%dY%d'%(t,s['prefix'],s['x_coord'],s['y_coord'])
        for pin,info in s['site_pins'].items():
            if info: sitepin.setdefault(node((t,info['wire'])),[]).append((iname,s['type'],pin,t+'.'+s['prefix']+'_X%d'%s['x_coord']))
# synthetic: ILOGIC bypass D->O, OLOGIC D1->OQ, T1->TQ, IDELAY IDATAIN->DATAOUT
for t,g in grid.items():
    if 'IOI3' not in g['type']: continue
    j=ttype(t)
    for s in j['sites']:
        sp={k:v['wire'] for k,v in s['site_pins'].items() if v}
        for a,b in (('D','O'),('D1','OQ'),('T1','TQ'),('IDATAIN','DATAOUT')):
            if a in sp and b in sp: add(t,sp[a],sp[b])
pickle.dump((dict(edges),dict(redges),sitepin),open(out+'.graph.pkl','wb'))
print('nodes w/ edges',len(edges),'sitepin nodes',len(sitepin))
