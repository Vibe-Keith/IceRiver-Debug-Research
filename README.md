# IceRiver Debug Research

Reverse-engineering IceRiver Kaspa miners (KS0-KS3M) to find a path below "work in, nonce out" to the ASIC's kHeavyHash internals.

- `docs/fpga_bitstream_analysis.md`: PL bitstream decode. The ASIC bus is SPI0 -> PL SPI-to-UART bridge, not ttyPS1.
- `tools/fpga/`: BOOT.BIN / bitstream / Project X-Ray netlist tooling
- `tools/miner/`: Thumb-2 xref helpers for `iceriverminer`
- `data/ks3l_fpga/`: derived pad map, PS7 connections, FSBL MIO table, FASM
