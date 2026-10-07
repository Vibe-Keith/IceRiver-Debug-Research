import struct,sys
d=open(sys.argv[1],'rb').read()
copies=[]
o=0
while True:
    o=d.find(struct.pack('<II',0x33,0xF8000700),o)
    if o<0: break
    tbl={}
    k=o
    while True:
        op,a,m,v=struct.unpack_from('<IIII',d,k)
        if op!=0x33 or not (0xF8000700<=a<=0xF80007D4): break
        tbl[(a-0xF8000700)//4]=v&m; k+=16
    copies.append((o,tbl)); o=k
L3={0:'GPIO',1:'CAN',2:'I2C',3:'WDT/PJTAG',4:'SDIO',5:'SPI',6:'?',7:'UART'}
def fn(p,v):
    if v&2: return 'L0(QSPI/ENET RGMII)'
    if v&4: return 'L1(USB/QSPI1)'
    l2=(v>>3)&3
    if l2: return 'L2=%d(%s)'%(l2,'NAND/SRAM' if l2==2 or l2==1 else 'SDIO-card/other')
    l3=(v>>5)&7
    s=L3[l3]
    if l3==7:
        u = 'UART1' if p in (8,9,12,13,24,25,36,37,48,49,52,53) else 'UART0'
        s=u+(' TX' if p%2==(1 if u=='UART0' else 0) else ' RX')
    if l3==2: s='I2C%d %s'%(0 if (p//2)%2==1 else 1,'SDA' if p%2 else 'SCL')
    if l3==0: s='GPIO' + (' (tri)' if v&1 else '')
    return s
for o,t in copies:
    print('== table at 0x%x, %d entries'%(o,len(t)))
for o,t in copies[-1:]:
    for p in sorted(t):
        v=t[p]; print('MIO%-2d %04x  %-22s IO=%d pu=%d'%(p,v,fn(p,v),(v>>9)&7,(v>>12)&1))
same=all(c[1]==copies[0][1] for c in copies); print('all copies identical:',same)
