import sys,struct
d=open(sys.argv[1],'rb').read(); tgt=int(sys.argv[2],16)
base=0x10000
for o in range(0x2c30,0x2c30+0x11fe10,2):
    h1,h2=struct.unpack_from('<HH',d,o)
    if (h1>>11)==0x1e and ((h2>>14)==3 or ((h2>>14)==2 and (h2>>12)&1)):
        S=(h1>>10)&1; imm10=h1&0x3ff; J1=(h2>>13)&1; J2=(h2>>11)&1; imm11=h2&0x7ff
        I1=1^(J1^S); I2=1^(J2^S)
        off=(S<<24)|(I1<<23)|(I2<<22)|(imm10<<12)|(imm11<<1)
        if S: off-=1<<25
        pc=base+o+4
        blx=(h2>>14)==3 and not (h2>>12)&1
        t=(pc&~3 if blx else pc)+off
        if t==tgt: print(hex(base+o),'blx' if blx else 'bl')
