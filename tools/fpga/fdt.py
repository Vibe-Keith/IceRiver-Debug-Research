import struct,sys
d=open(sys.argv[1],'rb').read()
mg,ts,so,ss,_,_,_,_,szs,szst=struct.unpack_from('>10I',d,0)
st=d[ss:ss+szst]
o=so;depth=0
def name(off): return st[off:st.index(b'\0',off)].decode()
while True:
    tok=struct.unpack_from('>I',d,o)[0];o+=4
    if tok==1:
        e=d.index(b'\0',o); print('  '*depth+d[o:e].decode()+' {'); o=(e+4)&~3; depth+=1
    elif tok==2: depth-=1; print('  '*depth+'}')
    elif tok==3:
        ln,no=struct.unpack_from('>II',d,o);o+=8; v=d[o:o+ln]; o=(o+ln+3)&~3
        n=name(no)
        if v and v[-1]==0 and all(32<=c<127 or c==0 for c in v[:-1]): s=repr(v.decode().rstrip('\0'))
        else: s=' '.join('%08x'%x for x in struct.unpack('>%dI'%(ln//4),v[:ln//4*4])) if ln%4==0 else v.hex()
        print('  '*depth+'%s = %s'%(n,s))
    elif tok==4: continue
    elif tok==9: break
