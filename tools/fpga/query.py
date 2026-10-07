import sys,pickle,collections,re,csv,json
edges,redges,sitepin=pickle.load(open(sys.argv[1],'rb')); fasmf=sys.argv[2]; D=sys.argv[3]
grid=json.load(open(D+'/xc7z010/tilegrid.json'))
pk={r['site']:r for r in csv.DictReader(open(D+'/xc7z010clg400-1/package_pins.csv'))}
feats=[l.strip() for l in open(fasmf) if l.strip()]
used=collections.defaultdict(set)
for f in feats:
    m=re.match(r'(R|L)IOB33(_SING)?_(X\d+Y\d+)\.IOB_Y(\d)\.(.*)',f)
    if m: used[(f.split('.')[0],int(m.group(4)))].add(m.group(5))
STOP_T=('IOB','ILOGIC','OLOGIC','IDELAY','ODELAY')
def walk(start,E,maxn=20000):
    seen={start};q=collections.deque([start]);hits=set()
    while q and len(seen)<maxn:
        n=q.popleft()
        for sp in sitepin.get(n,[]):
            if n!=start and not sp[1].startswith(STOP_T): hits.add(sp)
        if any(n!=start and not sp[1].startswith(STOP_T) for sp in sitepin.get(n,[])): continue
        for m in E.get(n,()):
            if m not in seen: seen.add(m);q.append(m)
    return hits
# find pad site pin nodes
padnodes={}
for n,lst in sitepin.items():
    for (iname,ty,pin,t) in lst:
        if ty.startswith('IOB33') and pin in ('I','O','T'): padnodes[(iname,pin)]=n
rows=[]
for (tile,y),fs in sorted(used.items(),key=lambda x:(int(re.search(r'Y(\d+)$',x[0][0]).group(1)),x[0][1])):
    sites=sorted(grid[tile]['sites'], key=lambda s:int(re.search(r'Y(\d+)$',s).group(1)))
    site=sites[1-y] if len(sites)>1 else sites[0]  # prjxray IOB_Y0 = upper (M) site
    pin=pk.get(site,{}); 
    direction='IN' if any('.IN' in f or 'IN_ONLY' in f for f in fs) else ''
    if any('DRIVE' in f for f in fs): direction+='OUT'
    pull=[f.split('.')[-1] for f in fs if f.startswith('PULLTYPE')]
    res={}
    for p,E in (('I',edges),('O',redges),('T',redges)):
        n=padnodes.get((site,p))
        if n is None: continue
        h=walk(n,E)
        if h: res[p]=sorted('%s.%s'%(i,pp) for i,ty,pp,t in h)
    print('%-5s %-12s %-22s %-6s %-9s'%(pin.get('pin'),site,pin.get('pin_function'),direction,','.join(pull)),json.dumps(res))
