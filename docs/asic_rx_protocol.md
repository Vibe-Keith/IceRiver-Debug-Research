# IceRiver KS3L — ASIC protocol and RX-parser static reconstruction

Scope: **offline static analysis only** of `iceriverminer` (KS3L, md5 `b02f7eb8…`,
ARM Thumb-2, stripped, cpuminer-multi derived) plus the previously decoded FPGA
bitstream. No live-device interaction, no transmission, no measurement.

Evidence source for every claim: **[ARM]** = this binary's disassembly,
**[BIT]** = bitstream, **[prior]** = carried from earlier sessions.
Confidence: **Confirmed** (static fact in code), **Strongly supported**,
**Plausible**, **Unknown**.

A "static fact" is only *"instruction at 0xADDR reads byte N"*. Any statement
that byte N *means* temperature/PLL/etc. is an interpretation and is tagged.

---

## A. ASIC transport architecture

```
ARM iceriverminer ──write()/read()──> /dev/spidev0.0 ──> Zynq PL (SPI↔UART bridge) ──> 4 ASIC UART chains
```

- The ASIC fd is opened by `spi_open` at **0x116ecc** (`sprintf("/dev/spidev%d.%d",0,0)`,
  `open`, `SPI_IOC` ioctls) and stored in the controller struct at **+0x10**. Both the
  init path (**0x117186**, **0x1188de**) and the RX reader fetch the same fd. **[ARM] Confirmed.**
- Requested SPI params: speed arg `0x2625A00` = 40 MHz, mode `0x0C`, 8 bits. The mode/
  speed ioctl return values are stored but the result of the mode-set is not checked.
  Actual SCLK is a PL/clock-divider matter, not knowable from this binary. **[ARM] Confirmed (requested values); Unknown (effective values).**
- All outbound ASIC frames ultimately reach `write(fd,…)` inside the senders below;
  all inbound ASIC data arrives via `read(fd,8)` in the poll loop (§D). **[ARM] Confirmed.**

---

## B. Outbound frame construction

Three sender entry points, all converging on the raw writer `proto_write`/`0x11c894`:

| Sender | Address | Behaviour |
|---|---|---|
| checksum sender | **0x11c3a0** | hex-ASCII template → bytes, appends 1 additive-checksum byte, `write()` |
| hex sender | **0x11cb88** | hex-ASCII template → bytes (checksum already in template), `write()` |
| raw writer | **0x11c894** | takes an already-built byte buffer + length, `write()` |

Outbound wire layout (**[ARM] Confirmed** from the 97 templates + builders):

```
7F 55 | addr | opcode | len | payload(len bytes) | checksum
```

- `7F 55` literal header, MSB-first on the wire as written.
- `addr` = ASIC address (`FF` = broadcast; specific chip addresses `01,03,05,07,47,49,4B,4D,8D,8F,91,93` seen in the init ramp).
- Checksum = `sum(all preceding bytes) & 0xFF`, computed by the SWAR byte-sum at **0x11c660**
  (classic `0x7f7f7f7f` trick). Verified earlier against `7F 55 FF 81 01 00` → `55`. **[ARM] Confirmed.**

### Opcodes observed in templates/builders

| Opcode | Meaning (interpretation) | Evidence | Confidence |
|---|---|---|---|
| `01` | init / enable step | init sequence `0x11d048…` | Plausible |
| `02` | address assignment (`7F 55 00 02 01 <addr>`) | daisy-chain enumeration `0x11dafe…` | Strongly supported |
| `05` | config write (`…05 03 ce 5c e5`) | single use `0x11d986` | Plausible |
| `07` | core-enable mask (`…07 04 ff ff 24 ff`) | per-chip in ramp | Plausible |
| `08` | per-chip command (`7F 55 %02x 08 01 01`) | `0x119a2c` | Plausible |
| `09` | **frequency/PLL config** (not a register read) | dynamic builder `0x116b60`, §J-note | Strongly supported |
| `0B` | config (`…0b 02 00 19`) | `0x11d99c` | Plausible |
| `0C` | **work packet** | builder `0x1175fe` (§L) | Confirmed (is work) |
| `0D` | mode/select (`7F 55 FF 0D 01 %02X`) | `0x1175a4`, sent before `0C` | Strongly supported |

Note on `0x09`: the dynamic builder at **0x116b60** multiplies a per-chain frequency
integer by `0.16` (`0x116cf8` = 0.16) and packs it into the two variable bytes of
`7F 55 FF 09 08 01 0B 00 00 00 %02x %02x 8a`. Each `0.16` step ≈ 6.25 MHz/LSB; the
static-template ramp `02 00 → 09 80` maps to ~200→~950 MHz. This is a **clock/PLL
configuration write**, superseding the old "indexed register read" guess. **[ARM] Strongly supported.**

---

## C. 7F55 command table (response-producing commands)

The RX parser (§E) dispatches purely on the inbound **type byte (byte 11)**; outbound
opcode and inbound type are *not* the same field. Linkage below is by firmware context.

| Outbound | Context | Inbound type seen in same code region | Confidence |
|---|---|---|---|
| `0C` work | mining loop | `0x80` status, bit7-clear nonce | Strongly supported |
| `09` freq | PLL set | `0x80` (PLL echo in status) | Plausible |
| `81`-prefixed query `7F 55 FF 81 01 00` | temp read (`0x117cce`, `0x11aa02`) | `0x81` | Strongly supported |
| `8E`/`80`/`82` | voltage / model / status polls | `0x8E`,`0x82`,`0x80` | Plausible |

Exact command→response pairing cannot be fully proven statically because the ASIC
responds asynchronously and the parser keys only on the type byte. **[ARM] Confirmed (dispatch is type-keyed).**

---

## D. RX buffer / polling architecture

- Reader body: **0x117ce8** (`algoboard` read path) and the consumer at **0x118834**.
- While `gpio_get(964)` reads 0, the ARM `write()`s the fixed 10-byte SPI poll
  command `5E 58 55 52 59 56 53 57 54 51`, `usleep`s, then `read(fd, 8)`. **[ARM] Confirmed.**
- The 8 bytes are 4 `(status,data)` pairs, one per chain. Loop at **0x117d80/9a/b6/d4**:
  for each pair, if `status == 0x77` → no byte; else append `data` to that chain's
  byte ring buffer. Each chain buffer is bounded at `0x7D0` = 2000 bytes
  (`0x117d8c cmp #0x7d0`). **[ARM] Confirmed.**
- Ring buffer: push `0x11c07c`, pop `0x11c0ec`, free-count `0x11c290`, byte-search
  `0x11c1ec`. The four buffers keep the chains' streams **separate**. **[ARM] Confirmed.**

This means: the FPGA presents four independent RX byte streams to the ARM; the ARM
reassembles frames per chain in software.

---

## E. 13-byte response frame format

Frame re-assembly in the consumer **0x118834–0x1189d8**. For each chain the code:

1. waits until free-count > 12 (`0x11c290`, `cmp #0xc`), **0x118844**.
2. pops 1 byte → `sp+0x160`, requires `== 0x55` (**0x118864**).
3. pops 1 byte → `sp+0x161`, requires `== 0x7F` (**0x11887a**); else counts "not 7f".
4. pops 11 bytes → `sp+0x162…0x16C` (`movs r2,#0xb`, **0x1189b8**).
5. checksum: `cksum(sp+0x160, 0xC)` via **0x11c660**, compared to `sp+0x16C` (byte 12);
   mismatch → "checksum error!" (**0x118a12**), frame dropped.
6. dispatch on `sp+0x16B` (byte 11) (**0x1189e0**).

Confirmed layout (13 bytes, indices 0–12). **Note the header byte order is reversed
vs. outbound**: inbound is `55 7F`, outbound is `7F 55`. **[ARM] Confirmed.**

```
idx 0  : 0x55                (framing)
idx 1  : 0x7F                (framing)
idx 2..10 : 9 payload bytes
idx 11 : response type  (0x80/0x81/0x82/0x8E, or bit7-clear → nonce path)
idx 12 : additive checksum over idx 0..11
```

Only this one inbound length exists: the pop count (11) and checksum length (12) are
the sole inbound size constants in the parser; no other inbound frame format is
decoded anywhere in the binary. **[ARM] Confirmed (single format).**

Handlers (all at `sp+0x160` base): `0x80`→**0x118e88**, `0x81`→**0x118eee**,
`0x8E`→**0x1194a8**, `0x82`→**0x119e80**, bit7-clear→**0x11a1d8**,
unknown type→ "unknown command: %02X" (**0x118a02**).

---

## F. 0x80 response map (type byte 11 = 0x80)

Handler **0x118e88**. Byte reads (static facts) and interpretations:

| Byte(s) | Instr | Reads | Interpretation | Conv | Confidence |
|---|---|---|---|---|---|
| 4,5 | 0x118eb2/ba | `pll = b4<<8 | b5` | PLL/freq readback | none | Strongly supported (label from format string) |
| 6,7,8,9 | 0x118e88-a6 | `cnt = (b6<<24|b7<<16|b8<<8|b9)` | nonce/hash counter | `×10`, then `/1e6`-ish scale stored | Strongly supported |
| 10 | 0x118ea0 | `idx = b10` | chip index (array subscript) | `[base + idx*4]` | Confirmed (used as index) |
| 2,3 | — | **not read** | — | — | Confirmed unused |

Format string: `"%02X noncecnt: %d, pll : %d"` at `0x1808f4`. Result stored to a
per-chip counter array `str [r3, b10<<2]` at **0x118ee8**. **[ARM]**

---

## G. 0x81 response map (temperature)

Handler **0x118eee**. 

| Byte(s) | Reads | Interpretation | Conv | Confidence |
|---|---|---|---|---|
| 7,8,9 | `v = (b7<<16|b8<<8|b9)`, `ubfx 12 bits` | temperature raw | float: `0.5 + v*k` (vmla d10/d12) → stored as f32/f64 | Strongly supported |
| 10 | `idx = b10` | chip index | `base+b10*8` (`vstr d15,[r1]`) | Confirmed (index) |
| 2,3,4,5,6 | not read | — | — | Confirmed unused |

Temperature table write at **0x118f4e** `vstr d15,[r6 + b10*8]`. **[ARM]**

---

## H. 0x82 response map (model string)

Handler **0x119e80**.

| Byte(s) | Reads | Interpretation | Confidence |
|---|---|---|---|
| 5,6,7,8 | `ldr [sp+0x165]` (4 bytes) | 4-char model/ID string | Strongly supported |
| 9 | `[sp+0x169]` | string terminator/5th char | Plausible |
| 10 | `[sp+0x16a]` | model code `%02X` | Strongly supported |
| 2,3,4 | not read | — | Confirmed unused |

Format `"model %02X: %s"` at `0x180b54`, built into a stack string at `sp+0xF0`. **[ARM]**

---

## I. 0x8E response map (voltage)

Handler **0x1194a8**.

| Byte(s) | Reads | Interpretation | Conv | Confidence |
|---|---|---|---|---|
| 2,3 | `v = (b2<<8|b3)`, `asr #2` | voltage raw (14-bit) | float: `((v*? )…)` via vmul d11 → stored | Strongly supported |
| 10 | chip index | — | `base+0xb10` and `base+b10*8` | Confirmed (index) |
| 4,5,6,7,8,9 | not read | — | — | Confirmed unused |

Stored to a per-chip voltage table at **0x119500**. **[ARM]**

---

## J. Bit-7-clear nonce response map

Handler **0x11a1d8** (taken when `type & 0x80 == 0`, `0x1189e4 lsls…#0x18 / bpl`).

Byte reads (static facts): bytes **2,3,4,5,6,7** individually, **8,9** as a halfword
(`ldrh [sp+0x168]`, then `rev16`), and byte **2** reused as chip index
(`strb ip,[sl,#0xfc]`, `[sb + b2<<2]` counter at **0x11a26c**).

Arithmetic (**0x11a1f0–0x11a264**): nibble-swaps bytes 2 and 3
(`lsr#4 | lsl#4`), then assembles a little-endian 64-bit value from bytes
[2,3,4,5,6,7] plus the byte-swapped halfword [8,9] into a 64-bit pair at
`sp+0x68/0x6c`, copied to `sp+0xA8`. **[ARM] Confirmed (assembles a 64-bit integer with nibble/byte swaps).**

Interpretation: this is the **found-nonce result** (64-bit). **Strongly supported.**
In the consumer (**0x1188a0**) the 64-bit value is loaded from `sp+0xA8`, compared
against a stored "last nonce" at `0x198de8+0x100`, and if different it is accepted
(dedup), then handed to the mining/submit path. The chip index (byte 2 nibble-swapped)
increments a per-chip nonce counter at `0x19a550`. **[ARM] Confirmed (dedup+store).**

---

## K. Discarded / unused response bytes

For the 13-byte frame, framing (0,1), type (11), checksum (12) are structural. Of the
**9 payload bytes (2–10)**:

| Type | USED payload bytes | RECEIVED-BUT-UNUSED payload bytes |
|---|---|---|
| 0x80 | 4,5,6,7,8,9,10 | **2,3** |
| 0x81 | 7,8,9,10 | **2,3,4,5,6** |
| 0x82 | 5,6,7,8,9,10 | **2,3,4** |
| 0x8E | 2,3,10 | **4,5,6,7,8,9** |
| nonce | 2,3,4,5,6,7,8,9,(2 as idx) | **10** |

**Static fact:** every handler ignores part of the 9-byte payload; `0x81` ignores 5 of
9, `0x8E` ignores 6 of 9. The parser never scans payloads longer than one 13-byte frame.
**Interpretation of what the unused bytes contain: Unknown** — the firmware never reads
them, so static analysis cannot show their content; this can only be answered by a
passive bus capture, which is out of scope here.

---

## L. 0x0C work packet reconstruction

Live builder **0x1175fe** (preceded by a `0x0D` mode byte at **0x1175a4**,
`7F 55 FF 0D 01 <0x28>`). Wire framing: `7F 55 FF 0C 39 <57-byte payload> <cksum>`
(`0x39 = 57`). **[ARM] Confirmed length.**

Builder behaviour (static facts):
- Parses three hex source regions into three per-chain binary buffers (`r4,r8,r7`),
  so three chains get near-identical packets. **0x1175fe–0x117694.**
- Sets payload byte 4 from a length/addr accumulator, byte 5/6 from a 16-bit field
  `(b6 + b0<<8)`, then `+1`/`+2` for the second/third chain — i.e. a **per-chain nonce-range
  start offset**. **0x11769e–0x1176d6. Strongly supported.**
- Zeroes bytes 7..0x13, then `memcpy`s a data block at offset `+0x14` via **0x11c894**
  path (**0x117704–0x117724**). **Confirmed (block copied from work struct).**

Concrete instance — the firmware's built-in **self-test vector** (template `0x181504`,
used only by the selftest path `0x11d678`, *not* live mining):
```
7F 55 FF 0C 39 | 1B 5A | 00×16 | 01 | <32 bytes: 81 2E 88 …(prePow-sized)… 04 5B> | F5 BE 32 11 76 | 00
```
The 32-byte block is **prePowHash-sized** and the live builder copies a work-derived
block into the same position. **prePowHash = Strongly supported; exact field semantics of
the 2-byte prefix / 16 zeros / 6 trailing bytes = Plausible/Unknown.**

What the ASIC receives before hashing: a compact work packet (≈57 payload bytes)
containing a ~32-byte prePow/header-derived block plus per-chain nonce-range fields.
It does **not** receive a 64×64 matrix (that would be ~2 KB packed). **[ARM] Confirmed (size).**

---

## M. kHeavyHash information flow (ARM-visible boundary)

```
Kaspa work (stratum)  ──ARM──>  0C work packet (prePow block + nonce range)  ──SPI──>  FPGA  ──UART──>  ASIC
ASIC  ──UART──>  FPGA  ──SPI(poll)──>  ARM:  0x80 status | 0x81 temp | 0x82 model | 0x8E volt | bit7-clear 64-bit NONCE
```

- Into the ASIC: header/prePow-derived block + nonce range + freq/core config. **Confirmed.**
- Out of the ASIC (everything the ARM ever reads): the five 13-byte response types above.
  The only *computational* output is the **64-bit winning nonce** (§J). Everything else is
  telemetry (PLL echo, counters, temp, voltage, model). **[ARM] Confirmed.**

---

## N. Evidence regarding matrix visibility

- No ARM code path reads, stores, or transmits a 4096-element / 2048-byte / 512-byte
  structure on the ASIC path. (grep for such sizes finds only the generic buffers.) **[ARM] Confirmed-absent in parser.**
- The ASIC never returns more than a 13-byte frame to the ARM; there is no response type
  whose handler accumulates a large block. **[ARM] Confirmed.**
- Therefore, in the observed firmware path, **no matrix or matrix×vector or pre-cSHAKE
  intermediate exists outside the ASIC.** The matrix is derived per-prePow inside the
  ASIC and consumed internally; only the final nonce crosses back. **Strongly supported.**

---

## O. Remaining unknowns (static analysis cannot resolve)

1. Content of the received-but-unused payload bytes (§K) — needs a passive capture.
2. Whether any outbound opcode not exercised during normal mining (e.g. a diagnostic/
   test opcode) would make the ASIC emit a longer/other frame — the *parser* only
   understands 13-byte frames, so even if such a response existed the stock ARM would
   drop it. No such opcode is present in the 97 templates. **Unknown.**
3. Exact semantics of `0x0C` payload prefix/trailer fields.
4. Effective UART baud / SPI clock (deliberately out of scope).

---

## P. Best next static-analysis target

The `0x82`/`0x8E`/startup command senders in the init thread **0x11cc80 → 0x11d0xx**:
confirm whether any init-only command elicits a response type other than the five
known, and whether the "unknown command: %02X" branch is ever reachable from a real
ASIC reply. This bounds, purely statically, whether the stock firmware is *capable* of
receiving anything beyond nonce+telemetry. (It already appears not to be.)

---

## Three direct answers

**1. Exactly what does the ASIC send back to the ARM?**
Only 13-byte UART frames, reassembled per chain, of five kinds: `0x80` status
(PLL readback, a ×10 nonce/hash counter, chip index), `0x81` temperature (12-bit raw +
chip index), `0x82` model string, `0x8E` voltage (14-bit raw + chip index), and the
bit-7-clear frame carrying a **64-bit nonce** + chip index. Nothing larger, and no
other format is parseable by the firmware. **[ARM] Confirmed.**

**2. Is any returned information currently ignored by the stock software?**
Yes — **structurally**. Every response handler reads only part of the 9 payload bytes:
`0x81` ignores bytes 2–6 (5 of 9), `0x8E` ignores 4–9 (6 of 9), `0x80` ignores 2–3,
`0x82` ignores 2–4. Those bytes are received into the stack frame and never read.
Whether they carry anything useful is **Unknown** from static analysis alone (the code
never touches them); a passive capture would be required to see their values. This is
the single most interesting static finding for follow-up.

**3. Does static evidence reveal any path by which the 64×64 matrix or a pre-cSHAKE
intermediate is already present in returned data?**
**No.** The ARM sends a compact prePow/work packet in, and the ASIC returns only the
five small telemetry/nonce frames. No code path handles matrix-sized data, and the
inbound frame is fixed at 13 bytes. On the evidence, the matrix and all intermediates
exist only inside the ASIC and never cross the UART→SPI boundary in stock firmware.
The only non-telemetry computational output observable today is the final 64-bit nonce.
