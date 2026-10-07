# Kaspa ASIC physical/test access and cross-family comparison

Scope: **public documentation, photographs, repair docs, patents, package/protocol references, and
the already-decoded firmware.** No device interaction. Egress note: in this environment only GitHub
and the web-search tool were reachable; repair hosts (zeusbtc, d-central, lys-sz, thanosmining,
eevblog, serhack, arxiv, Google Patents) were **egress-blocked**, so facts from them are from
**search-result snippets** and tagged `[snippet]`. Directly fetched primary sources are tagged `[fetched]`.
Binary facts are `[ARM]`.

Confidence: **Confirmed**, **Strongly supported**, **Plausible**, **Speculative**.

---

## A. IceRiver ASIC identification (carried + refined)

Custom, unlabeled IceRiver silicon; package house-codes `P2…/P3…` + date code (`P2SG48 2329`,
`P37P57 2342`, `P38C03/39`, `P3AS24`, `P3GY31`, `P2SM88`, `P49K68`). `[snippet] Strongly supported.`
No public datasheet, decap, die-shot, or X-ray of an IceRiver ASIC was found (searched; none exist
publicly). `[snippet] Strongly supported (absence).` KS3 = 112 chips / 28 groups of 4; KS3L = 56.
Power-up order negative→positive→**data cable** confirms the controller↔hashboard serial link is a
separate ribbon/ZIF, not a wide bus. `[snippet] Strongly supported.`

## B. Package analysis

No datasheet or high-resolution package photo obtained, so pin count/ballout is **Unknown**. From
rework method (per-chip stencil, M705 paste, ~400 °C hot air) the package is a fine-pitch leadless
QFN/LGA/BGA-class part. `[snippet] Plausible.` Whether dedicated test pins (TCK/TMS/TDI/TDO/TRST,
TEST, scan I/O) are brought to the package is **Unknown** — cannot be determined without a datasheet
or clear die/package image.

## C. PCB photograph analysis

**Not achievable in this pass**: every repair/teardown host with high-res hashboard photos was
egress-blocked, and no die/boardview surfaced via search. So no primary pad-level table could be
built. Indirect, text-confirmed structure only: daisy-chain enumeration with per-position addressing
(single dead chip truncates the chain), ribbon/ZIF controller link. `[snippet] Strongly supported.`
This section remains the principal gap and is the clearest target for a follow-up with a reachable
image source.

## D. Factory / test-fixture analysis

A **"KS universal hash board tester for IceRiver"** exists and its **stated purpose is to detect dead
ASIC chips and dead temperature sensors** on a hashboard. `[snippet] Confirmed (existence + purpose).`
That purpose is exactly what the normal `7F 55` enumeration + telemetry path already does, so the
most-supported reading is that the tester **drives the normal controller↔hashboard serial bus** (plus
supplies power rails) to enumerate and poll chips — **not** a deeper debug interface. `Strongly
supported (function); Plausible (bus).` Whether the fixture also contacts per-chip test points cannot
be confirmed without a fixture photo (blocked). A fixture that merely reproduces the normal bus gives
no access beyond what we already mapped.

## E. ASIC test / scan architecture — what is generic vs what is evidenced

Generic engineering fact: custom BGA/leadless ASICs of this complexity almost always contain on-die
manufacturing-test infrastructure (scan chains for ATPG, MBIST for SRAM, often IEEE-1149.1). `Confirmed
(industry norm).` The **BM1397** register map (fetched) shows what a well-documented mining ASIC
actually exposes as a *functional* self-test: a **Frequency Sweep Control (0x90)** + **Golden Nonce
Return (0x94)** + **Pattern Status Registers (0x98–0xA0)** — a BIST-style "inject known pattern, sweep
PLL, check returned nonce pattern" feature. `[fetched] Confirmed (for BM1397).`

Crucial separations (kept explicit per the brief):
- On-die scan/BIST **exists internally** (norm) ≠ it is **exposed on the package** (unknown for any Kaspa ASIC) ≠ it is **routed to accessible board pads** (no evidence for any Kaspa ASIC).
- A BIST/pattern self-test like BM1397's returns **pass/fail + nonce patterns**, not matrix/SRAM contents. `[fetched] Confirmed.`

## F. Matrix-engine architecture (what the silicon must minimally contain)

kHeavyHash = cSHAKE256 → xoShiRo256++ (matrix generation) → **64×64 GF(16) matrix × 64-element
vector** → cSHAKE256 finalize. `[snippet + ARM] Confirmed (algorithm).` Minimal ASIC internal state
for the heavy step:
- **Matrix storage:** 64×64 × 4-bit = 4096 nibbles = **2048 bytes** per job (regenerated per
  prePowHash). `Strongly supported (from algorithm).`
- **Vector:** 64 × 4-bit, derived on-chip from the hashed header.
- **Multiplier:** a 4-bit integer multiply-accumulate array (GF(16)/integer); output 64 values →
  reduced and fed to the final cSHAKE. `Strongly supported.`
- The ARM's `singular::Svd<64,64>` double-precision code is a **host-side rank-check/verification
  artifact**, not the ASIC's representation (hardware uses 4-bit integer MAC, not float SVD). `[ARM]
  Strongly supported.`

Observability consequence: the matrix is **internally generated** (not loaded), the vector is
**internally derived**, and only the **final nonce/telemetry** leaves the die. None of the three
(load matrix / load vector / read raw product) is in any exposed interface. `Confirmed (IceRiver), Strongly supported (class).`

## G. Bitmain comparison

Bitmain Kaspa ASIC = **BM2380 / BM2380AA** — a conventional BM-family part number (contrast
IceRiver's house codes). `[snippet] Confirmed.` Controller = **CVITEK CV1835** running **`godminer`**
(cgminer fork). BM daisy-chain carries **CK + RST + CI/CO (data) + BO (status), with RI/RO return**;
preamble **0x55 0xAA**; TYPE 1 job / TYPE 2 chip-command (address, register R/W) / TYPE 3 chain-inactive.
`[snippet, from BM1397-family RE] Strongly supported.` The BM register interface (BM1397, fetched) is
**richer** than IceRiver's — it has an explicit register read/write and per-core register control —
yet **every register is config/control/telemetry** (chip addr, PLL, ticket mask, core enable, temp,
error/overflow counters, golden-nonce/pattern self-test). **No register exposes hash intermediates,
SRAM, or matrix state.** `[fetched] Confirmed (BM1397).` BM2380's own map is not public `[snippet]`.

This is the single most useful comparative result: the best-documented mining ASIC on the market, with
a full register bus and a BIST pattern mode, **still exposes no computational intermediate** — strong
evidence the same holds for the Kaspa ASICs.

## H. Goldshell comparison

Goldshell KA-BOX / KA-BOX Pro / E-KA1M exist for kHeavyHash; **no teardown, chip marking, controller
detail, test-pad, or fixture information surfaced** (searched; thin public record). `[snippet] Lowest
accessibility.`

## I. Other Kaspa ASICs

Per-family summary (research accessibility, not hashrate):

| Family | ASIC id | Controller | ASIC bus | Register R/W iface | Public ASIC RE | Test-pad/fixture evidence |
|---|---|---|---|---|---|---|
| IceRiver KS0–KS3M | house codes `P2/P3…` (custom) | Zynq-7010 + PL SPI↔UART bridge | SPI0→PL→UART, `7F 55` | no generic reg-read in FW | full FW+bitstream in hand | tester detects dead chips (normal bus) |
| Bitmain KS3/KS5 | **BM2380AA** | CVITEK CV1835 + godminer | `0x55 0xAA` TYPE 1/2/3 | **yes** (config/telemetry only) | BM-family maps public (BM1397) | Bitmain test-fixture culture documented |
| Goldshell KA-BOX | unknown custom | unknown | unknown | unknown | none found | none found |

## J. Best candidate for deeper research

For *documentation depth and a real register interface*: **Bitmain** (BM-family maps, `godminer`,
CV1835 root-access culture). But its register interface is config/telemetry only, so depth ≠ matrix
access. For *material already in hand*: **IceRiver** (full firmware + decoded bitstream + protocol),
now exhausted at the protocol layer. No family shows evidence of matrix observability.

## K. Evidence for/against physical ASIC test access

- **For (generic):** scan/BIST almost certainly on-die for any of these custom ASICs; BM1397 proves a
  functional pattern/sweep self-test is exposed via registers on at least one mining-ASIC family. `Confirmed (BM1397), Plausible (Kaspa ASICs by analogy).`
- **Against (specific):** no PCB photo, schematic, fixture pinout, datasheet, or decap for any Kaspa
  ASIC shows test pads/JTAG routed to accessible points. The one fixture whose purpose is known uses
  the normal bus. `Confirmed (absence in available evidence).`

## L. Evidence for/against matrix observability

**Against (strong, converging):** (1) IceRiver returns only telemetry + nonce/address `[ARM]`; (2) the
richest documented mining-ASIC register bus (BM1397) exposes no compute state `[fetched]`; (3) the
matrix is internally generated and the product never leaves the die in any known interface; (4) even a
BIST/scan interface returns structural/pass-fail data, not labelled matrix arrays. **For:** none.
No source reviewed shows matrix / matrix×vector / pre-cSHAKE data leaving any Kaspa ASIC. `Confirmed-absent in available evidence.`

## M. What is realistically discoverable from public information

Already done: full IceRiver protocol + response maps across 6 models; chip house-codes and board
population; controller architectures across vendors; the BM register taxonomy as a proxy for what
mining ASICs expose. Still discoverable from *reachable* public sources (blocked here): high-res
IceRiver hashboard photos / boardview, the KS tester pinout, the BM2380 register map, and the
HeavyHash/Optical-PoW origin paper (arXiv 1911.05193) for the matrix-engine design intent.

## N. Remaining unknowns
1. IceRiver ASIC package ballout and whether any test pin is exposed (needs datasheet/die image).
2. Whether any hashboard test pad routes to an ASIC test/scan pin (needs boardview/photo).
3. BM2380's register map (needs Bitmain-specific RE).
4. Goldshell KA internals (no public record found).

## O. Recommended research direction
Two tracks, both non-destructive:
1. **Fully offline, no hardware, highest certainty:** compute the 64×64 matrix in software from the
   prePowHash the ARM already places in the `0x0C` packet. Deterministic; needs no ASIC. This *gets the
   matrix* for any job without any silicon access.
2. **Documentation-only, to resolve the physical question:** obtain reachable high-res IceRiver
   hashboard images + the KS tester pinout (and, comparatively, the BM2380 map) to test whether any
   ASIC test pad is externally routed — a static reading step, prerequisite to any (out-of-scope)
   physical probing.

---

## Task 19 — the AI-repurposing question, made specific

kHeavyHash's heavy step is a 64×64 × 4-bit matrix-vector multiply; HeavyHash was explicitly conceived
with matrix/optical hardware (Optical Proof of Work lineage) and the "repurposable for AI" framing
comes from that design intent. `[snippet] Plausible (design intent).` But reuse of a *mining ASIC's*
matrix engine for arbitrary compute faces concrete, enumerable obstacles — not a vague "ASICs aren't
for AI":

- **Possible with the normal protocol:** nothing compute-general — you can only submit a header and
  get a nonce/telemetry back. The matrix is chosen by the hash, not by you.
- **Possible only with undocumented ASIC functionality:** loading an **arbitrary** matrix (the engine
  generates it internally from prePowHash; there is no "load matrix" command), supplying an
  **arbitrary** vector, and reading the **raw product** before cSHAKE. None exists in any mapped interface.
- **Possible only with manufacturing/test access:** if a scan/BIST path could both inject matrix/vector
  state and observe the multiplier output, the engine could in principle be driven — but there is no
  evidence such a path is exposed, and scan access is structural, not a clean MAC datapath.
- **Possible only with silicon-level investigation:** decap + microprobing / FIB to reach the
  multiplier datapath — out of scope and destructive.

The specific architectural obstacle: the matrix engine is **not addressable** — its operands are
hash-derived on-chip and its output is consumed on-chip by cSHAKE; only the final nonce is emitted. To
repurpose it you would need an operand-load path and a pre-cSHAKE readout path, neither of which is
exposed by the mining interface. That is the thing that would have to be discovered (or added in a
custom silicon), and no public evidence shows it exists.

---

## Required direct answers

**1. Which ASIC is the most promising target now?**
For *deeper ASIC documentation*, **Bitmain KS3/KS5 (BM2380)** — real part number, BM-family register
protocol, active controller RE (CV1835/godminer). For *work already in hand*, **IceRiver** (fully
decoded, but protocol-exhausted). Neither shows matrix observability; Bitmain is the better *research*
target only because more of its silicon interface is documented. **Strongly supported.**

**2. What physical interface is the most promising?**
A manufacturing **scan/BIST / pattern-self-test interface** (the category BM1397 proves exists and is
even register-exposed on one family). It is the only interface class with any chance of sub-protocol
visibility — but on all evidence it yields structural/pass-fail/nonce data, not matrix state. **Plausible as an interface; unsupported as a matrix path.**

**3. Credible evidence an ASIC test interface could expose matrix-engine state?**
**No.** The best-documented example (BM1397) exposes only config/telemetry and a nonce-pattern
self-test; nothing reads the multiplier or matrix SRAM. No Kaspa ASIC shows otherwise. **Confirmed-absent.**

**4. Which current assumption about Kaspa ASICs is most likely wrong?**
The implicit assumption that **"no exposed debug interface" means "no register interface at all."**
Bitmain's family *does* have a rich register read/write bus — so a Kaspa ASIC plausibly has internal
config/BIST registers too. The correction: such registers, where they exist, carry **config and
pass/fail telemetry, not computation** — so finding one would *not* get the matrix. **Strongly supported.**

**5. What single piece of evidence would most change the assessment?**
A **boardview/schematic or high-resolution hashboard photo showing an ASIC test/scan pad routed to an
accessible point**, OR a datasheet/decap revealing an ASIC pin that injects/observes the matrix
datapath. Absent that, the matrix stays a deterministic software computation (track 1), not a silicon
readout.
