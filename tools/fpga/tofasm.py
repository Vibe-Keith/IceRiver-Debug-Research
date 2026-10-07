import sys
sys.path.insert(0,sys.argv[1])
import fasm, fasm.output
from prjxray import fasm_disassembler, bitstream
from prjxray.db import Database
db=Database(sys.argv[2],'xc7z010clg400-1'); grid=db.grid()
dis=fasm_disassembler.FasmDisassembler(db)
bd=bitstream.load_bitdata(open(sys.argv[3]))
model=fasm.output.merge_and_sort(dis.find_features_in_bitstream(bd,verbose=True),zero_function=dis.is_zero_feature,sort_key=grid.tile_key)
print(fasm.fasm_tuple_to_string(model,canonical=False),end='')
