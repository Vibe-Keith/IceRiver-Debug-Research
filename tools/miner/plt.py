import sys,pickle,capstone,re
from elftools.elf.elffile import ELFFile
fn=sys.argv[1]; e=ELFFile(open(fn,'rb'))
rel=e.get_section_by_name('.rel.plt'); dyn=e.get_section_by_name('.dynsym'); ps=e.get_section_by_name('.plt')
got={r['r_offset']:dyn.get_symbol(r['r_info_sym']).name for r in rel.iter_relocations()}
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM)
pd=ps.data(); pa=ps['sh_addr']; plt={}
ins=list(md.disasm(pd[20:],pa+20))
for k,i in enumerate(ins):
    if i.mnemonic=='add' and i.op_str.startswith('ip, pc'):
        v=i.address+8
        m=re.search(r'#(0x[0-9a-f]+|\d+)',i.op_str); v+=int(m.group(1),0)
        m=re.search(r'#(0x[0-9a-f]+|\d+)',ins[k+1].op_str); v+=int(m.group(1),0)
        m=re.search(r'#(0x[0-9a-f]+|\d+)',ins[k+2].op_str); v+=int(m.group(1),0)
        nm=got.get(v,'?%x'%v); plt[i.address]=nm; plt[i.address-4]=nm
a,x,_=pickle.load(open(sys.argv[2],'rb')); pickle.dump((a,x,plt),open(sys.argv[2],'wb'))
print({hex(k):v for k,v in plt.items() if v in('open','write','read','tcsetattr','cfsetispeed','cfsetospeed','ioctl')})
