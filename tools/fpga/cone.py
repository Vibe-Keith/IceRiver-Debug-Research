import sys,pickle,collections
cells,drv,loads=pickle.load(open(sys.argv[1],'rb'))
CLKN={'BUFHCE_X0Y20':'clkA','BUFHCE_X1Y20':'clkA','BUFHCE_X0Y21':'clkB','BUFHCE_X1Y21':'clkB','BUFHCE_X0Y22':'clkDIV','ILOGIC_X0Y27':'ext27','ILOGIC_X0Y28':'ext28','BUFHCE_X1Y8':'h8'}
def clk(I):
    d=drv.get((I,'CLK'),[])
    return ','.join(CLKN.get(x[0],x[0]) for x in d) or '-'
def desc(I,pin):
    """describe output pin of slice I"""
    c=cells.get(I)
    if not c: return I+'.'+pin,[]
    L=pin[0]
    if pin.endswith('Q') and len(pin)==2:
        mux=c['ff'].get(L,'?'); src={'AX':L+'X','BX':L+'X','CX':L+'X','DX':L+'X','O6':L+'6','O5':L+'5','XOR':'XOR','CY':'CY'}.get(mux,mux)
        ins=[(L+'X')] if mux.endswith('X') else ([L+str(k) for k in range(1,7)] if mux in('O6','O5') else [L+str(k) for k in range(1,7)]+['CIN'])
        return '%s.%sFF[%s,D=%s,CE=%s,SR=%s]'%(I,L,clk(I),mux,fmt(I,'CE'),fmt(I,'SR')),ins
    if pin.endswith('MUX'):
        m=c['outmux'].get(L,'?')
        if m.endswith('Q'): return '%s.%s5FF[%s,D=%s]'%(I,L,clk(I),c['ff5'].get(L,'?')),[L+str(k) for k in range(1,7)]+[L+'X']
        return '%s.%sMUX(%s) LUT%s=%016x'%(I,L,m,L,c['lut'].get(L,0)),[L+str(k) for k in range(1,7)]+(['CIN'] if m in('XOR','CY') else [])
    if pin in('A','B','C','D'):
        return '%s.%sLUT=%016x'%(I,L,c['lut'].get(L,0)),[L+str(k) for k in range(1,7)]
    if pin=='COUT': return I+'.COUT(carry)',['CIN']
    return I+'.'+pin,[]
def fmt(I,p):
    d=drv.get((I,p),[])
    return '/'.join('%s.%s'%x for x in d) if d else '-'
def cone(I,pin,depth,ind='',seen=None):
    seen=seen if seen is not None else set()
    s,ins=desc(I,pin)
    print(ind+s)
    if (I,pin) in seen or depth==0: return
    seen.add((I,pin))
    for p in ins:
        for (dI,dp) in drv.get((I,p),[]):
            print(ind+'  '+p+' <- ',end='')
            if dI.startswith('SLICE'): cone(dI,dp,depth-1,ind+'    ',seen)
            else: print('%s.%s'%(dI,dp))
for a in sys.argv[3:]:
    I,p=a.split(':'); print('=====',a); cone(I,p,int(sys.argv[2]))
