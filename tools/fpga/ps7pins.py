import sys,pickle,collections,re
edges,redges,sitepin=pickle.load(open(sys.argv[1],'rb'))
def walk(start,E,maxn=20000):
    seen={start};q=collections.deque([start]);hits=set()
    while q and len(seen)<maxn:
        n=q.popleft()
        sps=[sp for sp in sitepin.get(n,[]) if n!=start]
        if sps:
            hits.update(sps); continue
        for m in E.get(n,()):
            if m not in seen: seen.add(m);q.append(m)
    return hits
res=[]
for n,lst in sitepin.items():
    for (iname,ty,pin,t) in lst:
        if ty!='PS7': continue
        for d,E in (('->',edges),('<-',redges)):
            h=[x for x in walk(n,E) if x[1] not in ('PS7','TIEOFF')]
            if h: res.append((pin,d,sorted('%s.%s'%(a,c) for a,b,c,_ in h)))
for r in sorted(res): print(r[0],r[1],' '.join(r[2]))
