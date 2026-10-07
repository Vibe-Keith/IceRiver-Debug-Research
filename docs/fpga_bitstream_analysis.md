# IceRiver KS3L FPGA bitstream analysis

Source: `OS/KS3L/var/order/reset/BOOT2_0.BIN` from `mcmickburns/iceriverminer_dump`
(md5 `9856cca1bb9b33a3037fcc9041548ffa`, identical to the KS3M recovery copy).
Tools: Project X-Ray (`f4pga/prjxray` + `prjxray-db/zynq7`, part `xc7z010clg400-1`) plus the
scripts in `tools/fpga/`. Derived data is in `data/ks3l_fpga/`.

## Bottom line

1. **The ASIC bus is not a PS UART.** The `7F 55 ...` frames are written with `write()` to
   **`/dev/spidev0.0`** (PS SPI0, requested 40 MHz, 8-bit, mode 0x0C). SPI0 is routed via EMIO
   into the PL. The PL contains a **SPI-slave to UART bridge** that drives the hashboard serial
   lines.
2. **UART0 / `ttyPS1` is a dead port.** It is enabled in the device tree but is muxed to no MIO
   pin (FSBL), has no EMIO route (bitstream), and the DT `pinctrl` node has no groups. The only
   tty `open()` in the miner (`0x11bd3c`, called only from the "read global temp" path) is
   vestigial.
3. **The FPGA is category B: bridge + buffering + framing**, not a transparent wire. It holds
   about 1,100 LUTs, about 1,450 FFs, 1 MMCM and 1 RAMB18 (dual-clock FIFO), which is far more
   than "sparse". There is no evidence that it parses `7F 55` frames or holds any ASIC compute
   state (not ruled out; see open questions).
4. **The bitstream is unencrypted, fully decodable (0 unknown bits) and the PL is reloadable from
   Linux** (`fpga_manager` and an `fpga-full` region are probed in dmesg). That makes the FPGA the
   best place to put a **raw ASIC-bus tap or replacement controller**.

## Boot image

| Partition | Size | Notes |
|---|---|---|
| `zynq_fsbl.elf` | 0x1C010 | ps7_init tables: 3 identical copies |
| `ebaz4205_wrapper.bit` | 0x1FCBA0 | 5,152 frames written from FAR 0, IDCODE 0x03722093 (7z010) |
| `u-boot.elf` | 0x8C914 | embedded DTB at +0x89194 (`data/ks3l_fpga/uboot.dts`) |

Clocks (FSBL): IO PLL = 33.333 MHz x 30 = 1000 MHz. FCLK0 = IO PLL / 5 / 1 = **200 MHz**.

## PS to PL connections actually used (`ps7_fabric.txt`)

| PS7 port | Destination | Function |
|---|---|---|
| EMIO SPI0 (SCLK, MOSI, SS0, MISO) | ~420-slice logic block | **ASIC bridge** (spidev0.0) |
| EMIO SPI1 (SCLK, MOSI, SS0, MISO) | same block, PWM/tach area | Fan/PSU-style register interface (spidev1.0), likely |
| EMIO ENET0 GMII + MDIO | 5 FFs + pads | EBAZ4205 MII Ethernet PHY glue (external clocks on U14/U15) |
| EMIO GPIO 0-36 | pads and logic | see below |
| FCLK0 | BUFG0 to MMCM | |
| M_AXI_GP0 | ACLK only | **No AXI peripherals in the PL.** |
| EMIO UART0/1, I2C, CAN | none | |

Linux GPIO number = 960 + EMIO n (zynq gpiochip base 906 + 54 MIO).

## Clock domains

| Domain | Source | FFs | Notes |
|---|---|---|---|
| clkA | MMCM CLKOUT0, VCO/36 | ~655 | UART TX engine, PWM counters, FIFO read side |
| clkB | MMCM CLKOUT1, VCO/3 | ~610 | SPI slave (oversamples SCLK), FIFO write side, PWM output regs |
| clkDIV | `SLICE_X22Y46.AQ` to BUFG3 | ~171 | fabric-divided clock, purpose not yet traced |
| ext | pads U14/U15 (SRCC) | 10 | Ethernet MII RX/TX clocks |

The MMCM M/D decode from prjxray is ambiguous (fractional CLKFBOUT). The ratio clkB:clkA = 12:1
is reliable, but absolute frequencies are **unverified**.

## ASIC bridge datapath (what the PL does)

```
PS SPI0 (EMIO) --> SPI slave, clkB             SCLK sampled as data (X15Y69), CE = EMIO GPIO8 (968)
                   shift regs X6Y71/X7Y71
                         |
                   RAMB18_X0Y20 (W: clkB, R: clkA, 4-bit ports)   dual-clock FIFO
                   EMIO GPIO_I4 <- X8Y64 (FIFO status flag, likely)
                         |
                   UART TX shifter X23Y59 (clkA), CE = baud tick X21Y61.B
                   baud counter: carry chain X20Y60-X20Y63
                         |
                   out FF X22Y61 --> demux LUT X20Y74, select = EMIO GPIO5..7 (965-967)
                         |
             TX pads: J19, K14, N17, C20      (one per hashboard chain)

RX pads: G14, F16, J14, N18 --> LUT gates with EMIO GPIO32..35 --> RX logic --> SPI0 MISO (X7Y72.A)
```

Hashboard-side pads (bank 34/35, LVCMOS33):

| Dir | Pad | Pkg pin | Driven by / feeds |
|---|---|---|---|
| TX | IO_L10N_T1_AD11N_35 | J19 | X20Y74.A (O6) |
| TX | IO_L20P_T3_AD6P_35 | K14 | X20Y74.AMUX (O5) |
| TX | IO_L23P_T3_34 | N17 | X20Y74.B |
| TX | IO_L1P_T0_AD0P_35 | C20 | X20Y74.BMUX |
| RX | IO_0_35 | G14 | X6Y81.A3 (gated by GPIO32) |
| RX | IO_L6P_T0_35 | F16 | X6Y81.B4 (gated by GPIO33) |
| RX | IO_L20N_T3_AD6N_35 | J14 | X12Y67.C4 (gated by GPIO35) |
| RX | IO_L13P_T2_MRCC_34 | N18 | X8Y65.D1 (gated by GPIO34) |

J14/K14 are one differential pair (L20N/L20P), which suggests TX/RX pairing per connector. The
other TX/RX pairings are inferred, not traced.

Other PL functions:
- **PWM outputs** (counter compare, output FFs in clkB): U12, F19, V20, T10 (X22Y73.AQ-DQ),
  M20 (X28Y82.AQ). These are reachable from SPI1 MOSI. Most likely fan PWM.
- **Tach-like inputs** sampled into logic: U17, T16, V13.
- **Direct EMIO GPIO pads**: outputs 0-3, 16-19, 28-31; inputs 12-15 (975 = EMIO15 / K16 used
  with a falling-edge IRQ); IOBUFs 20-27 (T gated through LUTs).
- **EMIO GPIO9 (969)** fans out to resets across the bridge logic. The miner drives it low before
  init.

## Miner-side confirmation (`iceriverminer`, KS3L, md5 b02f7eb8...)

Thumb-2 binary. Key call chain:

```
0x117186 "init first"
  gpio_set(969,0)
  fd = spi_open(bus=0, cs=0, speed=0x2625A00 /*40 MHz*/, mode=0x0C, bits=8)   @0x116ecc -> "/dev/spidev%d.%d"
  gpio_set(976..979, 0)                                                        EMIO16-19 -> A20,G20,M19,G17
  init_cmd(fd)                                                                 @0x11cc80 ("init cmd")
     -> proto_send(fd, "7f 55 ...")                                            @0x11c3a0, 112 call sites
           hex->bin, byte-sum checksum, write(fd, buf, n)
```

`spidev1.0` (`0x12a49c`) sends 10-byte obfuscated packets. Consistent with a PSU/fan
controller, not the ASICs.

## Revised answers to the open questions

| # | Question | Answer | Confidence |
|---|---|---|---|
| 1 | What does PL do with UART0/ttyPS1? | Nothing. UART0 is unconnected. | High |
| 2 | Is UART0 on EMIO? | No | High |
| 3 | Which PL pins carry the ASIC bus? | TX J19/K14/N17/C20, RX G14/F16/J14/N18 | High (direction), Medium (pairing) |
| 4 | Transparent or protocol-aware? | Byte-level bridge: SPI slave + FIFO + UART framing + chain select | High |
| 5 | ASIC-specific logic? | Not found. No evidence of `7F 55` parsing or ASIC state. | Medium |
| 10 | Can a modified PL instrument the bus? | Yes. Unencrypted, decodable, reloadable at runtime. | High |

## Implications for the matrix objective

- The PL holds no matrix or hash data. It only moves bytes. Every `0x09` response the ASIC
  produces must pass through the RX pads above, so **a PL tap sees 100% of ASIC traffic**.
- The fastest route to "complete low-level ASIC bus control" (bottom rung of the ladder):
  1. **Passive:** put a logic analyzer on TX/RX pads (or the hashboard connector) and read the
     baud rate and framing directly. This resolves the open baud/MMCM question in minutes.
  2. **Active, low-risk:** a custom bitstream that keeps the existing PWM/fan logic (or forces
     the PWM pads high) and routes **EMIO UART0 (ttyPS1, already in the DT)** to the TX/RX pads,
     with chain select on GPIO. That gives a raw `/dev/ttyPS1` to the ASIC chain, with no SPI
     bridge in the way. Load it through `fpga_manager` without reflashing.
  3. Then run the opcode `0x09` index sweeps from userspace with full visibility of the
     responses.

## Risks

- **Fan control lives in the PL.** Replacing the bitstream without the PWM logic can stop the
  fans while the hashboards are powered. Keep the hashboards unpowered (EMIO16-19 / PSU) or
  force the PWM outputs to 100% duty.
- The PSU/PMIC path (SPI1 and I2C) sets hashboard voltage. Do not exercise it blind.
- The pad-to-connector mapping and TX/RX pairing need continuity checks on real hardware before
  driving any pin.

## Open items

- Exact UART baud. The divisor decode is incomplete; get it by capture or a full gate-level
  sim.
- Purpose of the clkDIV domain (171 FFs) and of the RAMB18 4-bit port configuration.
- Whether the RX path buffers bytes or streams bits to MISO.
- SPI wire protocol between miner and PL (command/length framing, whether MISO returns RX bytes
  on the same transfer). Disassemble the read side (`read()` at 0x117b10/0x117d7c).
- Model differences: run the same pipeline on KS0/KS1/KS2/KS3 firmware if their BOOT images
  are available. Only KS3L/KS3M `BOOT2_0.BIN` exist in the dump.

## Reproduce

```
python3 tools/fpga/bootbin.py BOOT2_0.BIN out/
python3 tools/fpga/bit2bits.py out/part1_ebaz4205_wrapper.bit prjxray-db/zynq7/xc7z010clg400-1/part.yaml design.bits
python3 tools/fpga/tofasm.py prjxray prjxray-db/zynq7 design.bits > design.fasm
python3 tools/fpga/trace.py prjxray prjxray-db/zynq7 design.fasm g      # builds g.graph.pkl, g.uf.pkl
python3 tools/fpga/query.py g.graph.pkl design.fasm prjxray-db/zynq7     # pad map
python3 tools/fpga/ps7pins.py g.graph.pkl                                # PS7<->PL
python3 tools/fpga/netlist.py g.graph.pkl nets.pkl prjxray-db/zynq7
python3 tools/fpga/cells.py nets.pkl design.fasm cells.pkl
python3 tools/fpga/cone.py cells.pkl 3 SLICE_X20Y74:A                    # logic cones
python3 tools/fpga/mio.py out/part0_zynq_fsbl.elf                        # MIO mux
```
Notes: prjxray FASM `IOB_Y0` is the upper (M) site of a pair. Unrouted LUT inputs read as 1.
