# Minimal 7-series bitstream -> prjxray .bits converter (frame-autoincrement aware)
import struct,sys,yaml
bitf,party,outf=sys.argv[1:4]
class L(yaml.SafeLoader): pass
L.add_multi_constructor('xilinx',lambda l,s,n: l.construct_mapping(n,deep=True) if isinstance(n,yaml.MappingNode) else l.construct_scalar(n))
part=yaml.load(open(party),Loader=L)
BT={'CLB_IO_CLK':0,'BLOCK_RAM':1,'CFG_CLB':2}
# build ordered list of valid frame addresses; mark row ends
order=[]
for bus_name,bt in sorted(BT.items(),key=lambda x:x[1]):
    for half,tb in (('top',0),('bottom',1)):
        hr=part['global_clock_regions'].get(half)
        if not hr: continue
        for r in sorted(hr['rows']):
            buses=hr['rows'][r]['configuration_buses']
            if bus_name not in buses: continue
            cols=buses[bus_name]['configuration_columns']
            for c in sorted(cols):
                for m in range(cols[c]['frame_count']):
                    order.append(((bt<<23)|(tb<<22)|(r<<17)|(c<<7)|m,False))
            order.append((None,True)); order.append((None,True))  # 2 pad frames per row
d=open(bitf,'rb').read()
sync=d.find(bytes.fromhex('665599aa'))
end='<' if sync>=0 else '>'
if sync<0: sync=d.find(bytes.fromhex('aa995566'))
w=[struct.unpack_from(end+'I',d,o)[0] for o in range(sync+4,len(d)-3,4)]
REG={0:'CRC',1:'FAR',2:'FDRI',3:'FDRO',4:'CMD',5:'CTL0',6:'MASK',7:'STAT',8:'LOUT',9:'COR0',10:'MFWR',11:'CBC',12:'IDCODE',13:'AXSS',14:'COR1',16:'WBSTAR',17:'TIMER',22:'BOOTSTS',24:'CTL1',31:'BSPI'}
i=0;far=0;last=None;frames={}
log=[]
def write_fdri(data,far):
    idx=[k for k,(a,p) in enumerate(order) if a==far]
    assert idx,hex(far)
    k=idx[0]; n=len(data)//101
    log.append('FDRI %d words (%d frames) from FAR %08x'%(len(data),n,far))
    for f in range(n):
        if k>=len(order): log.append(' overflow at frame %d'%f); break
        a,p=order[k]; fr=data[f*101:(f+1)*101]
        if a is not None and any(fr): frames[a]=fr
        k+=1
while i<len(w):
    h=w[i]; t=h>>29
    if t==1:
        op=(h>>27)&3; reg=(h>>13)&0x3fff; cnt=h&0x7ff; last=reg
        data=w[i+1:i+1+cnt]
        if op==2:
            if reg==1 and cnt: far=data[0]
            if reg!=2 or cnt: log.append('W %s %s'%(REG.get(reg,reg),' '.join('%08x'%x for x in data[:4])))
            if reg==2 and cnt: write_fdri(data,far)
        i+=1+cnt
    elif t==2:
        op=(h>>27)&3; cnt=h&0x7ffffff
        data=w[i+1:i+1+cnt]
        if op==2 and last==2: write_fdri(data,far)
        else: log.append('T2 reg %s cnt %d'%(last,cnt))
        i+=1+cnt
    else: i+=1
print('\n'.join(l for l in log if not l.startswith('W CRC')))
print('frames with data:',len(frames))
with open(outf,'w') as o:
    for a in sorted(frames):
        fr=frames[a]
        for wi,v in enumerate(fr):
            if wi==50: v&=~0x1fff  # strip ECC bits in HCLK word
            for b in range(32):
                if v>>b&1: o.write('bit_%08x_%03d_%02d\n'%(a,wi,b))
