import sys,pickle
ins,x,plt=pickle.load(open(sys.argv[1],'rb')); d=open(sys.argv[2],'rb').read()
rx={a:t for t,l in x.items() for a in l}
def s(t):
    o=t-0x10000
    if 0<=o<len(d):
        b=d[o:o+60].split(b'\0')[0]
        if len(b)>=2 and all(32<=c<127 for c in b): return repr(b.decode())
    return ''
a0,a1=int(sys.argv[3],16),int(sys.argv[4],16)
for a,m,o in ins:
    if a0<=a<a1:
        ex=''
        if m in('bl','blx','b.w','b'):
            try: ex=plt.get(int(o.strip('#'),16),'')
            except: pass
        if a in rx: ex='-> %x %s'%(rx[a],s(rx[a]))
        print('%x: %-7s %-28s %s'%(a,m,o,ex))
