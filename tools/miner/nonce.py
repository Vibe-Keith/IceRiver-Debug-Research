import sys,pickle,re
ins,x,plt=pickle.load(open(sys.argv[1],'rb')); dispa=int(sys.argv[2],16); typeoff=int(sys.argv[3],16)
idx={a:k for k,(a,_,_) in enumerate(ins)}
# find the bpl just before dispatch (bit-7-clear branch) -> nonce handler
k=idx[dispa]; nonce=None
for a,mn,op in reversed(ins[max(0,k-12):k]):
    if mn.startswith('bpl'):
        try: nonce=int(op.strip('#'),16)
        except: pass
        break
reads=[]
if nonce:
    kk=idx.get(nonce)
    for a,mn,op in ins[kk:kk+120]:
        if mn.startswith('push'): break
        m=re.match(r'\S+, \[sp, #(0x[0-9a-f]+)\]',op)
        if m and mn.startswith(('ldrb','ldrh','ldr')):
            off=int(m.group(1),16); b=off-(typeoff-11)
            if 0<=b<=12:
                w=4 if mn.startswith('ldr') and not mn.startswith(('ldrb','ldrh')) else (2 if mn.startswith('ldrh') else 1)
                for i in range(w): reads.append(b+i)
print('nonce@',hex(nonce) if nonce else None,'payload-bytes-read',sorted(set(b for b in reads if 2<=b<=10)))
