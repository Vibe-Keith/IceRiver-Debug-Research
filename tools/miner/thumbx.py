import sys,struct,re,pickle
from elftools.elf.elffile import ELFFile
import capstone
fn=sys.argv[1]; e=ELFFile(open(fn,'rb'))
text=e.get_section_by_name('.text'); ta=text['sh_addr']; td=text.data()
plt={}
rel=e.get_section_by_name('.rel.plt'); dyn=e.get_section_by_name('.dynsym'); ps=e.get_section_by_name('.plt')
for i,r in enumerate(rel.iter_relocations()): plt[ps['sh_addr']+20+12*i]=dyn.get_symbol(r['r_info_sym']).name
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB); md.skipdata=True
lo={}; xrefs={}; insns=[]
for i in md.disasm(td,ta):
    insns.append((i.address,i.mnemonic,i.op_str))
    m=re.match(r'(r\d+|ip|lr|sb|sl|fp), #(0x[0-9a-f]+|\d+)$',i.op_str)
    if i.mnemonic=='movw' and m: lo[m.group(1)]=int(m.group(2),0)
    elif i.mnemonic=='movt' and m and m.group(1) in lo:
        t=lo.pop(m.group(1))|(int(m.group(2),0)<<16); xrefs.setdefault(t,[]).append(i.address)
pickle.dump((insns,xrefs,plt),open(sys.argv[2],'wb'))
print(len(insns),len(xrefs))
