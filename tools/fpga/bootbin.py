import struct,sys,os
d=open(sys.argv[1],'rb').read(); out=sys.argv[2]
w=lambda o:struct.unpack_from('<I',d,o)[0]
print('width det %08x id %08x'%(w(0x20),w(0x24)))
print('fsbl src off %x len %x load %x exec %x total %x'%(w(0x30),w(0x34),w(0x38),w(0x3c),w(0x40)))
pht=w(0x9c); iht=w(0x98)
print('img hdr tbl %x part hdr tbl %x'%(iht,pht))
o=pht
i=0
while True:
    f=struct.unpack_from('<16I',d,o)
    if f[0]==0 and f[1]==0 and f[4]==0: break
    enc,unenc,tot,dl,ex,doff,attr,sc,cs,ihoff,acoff=f[:11]
    print(i,'enclen %x unenc %x tot %x load %x exec %x dataoff %x attr %x ih %x'%(enc*4,unenc*4,tot*4,dl,ex,doff*4,attr,ihoff*4))
    # image name
    if ihoff:
        nm=d[ihoff*4+16:ihoff*4+16+64]
        # name stored as big-endian words
        s=b''.join(nm[j:j+4][::-1] for j in range(0,64,4)).split(b'\0')[0]
        print('   name',s)
    else: s=b'p%d'%i
    open(os.path.join(out,'part%d_%s'%(i,s.decode(errors='replace').replace('/','_'))),'wb').write(d[doff*4:doff*4+tot*4])
    o+=64;i+=1
# register init
print('reg init:')
for k in range(0xa0,0x8a0,8):
    a,v=struct.unpack_from('<II',d,k)
    if a==0xffffffff: break
    print(' %08x <= %08x'%(a,v))
