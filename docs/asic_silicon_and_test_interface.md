# Kaspa ASIC silicon, PCB test infrastructure, and cross-vendor accessibility

Scope: **static / documentation research only** — binary analysis of the `iceriverminer`
ELFs, public repair documentation, teardown/marketplace listings, and comparative ASIC
knowledge. No device interaction, no transmission, no hardware control. Many repair domains
(zeusbtc, d-central, eevblog, thanosmining, lys-sz, serhack, Google Patents) were
**egress-blocked** in this environment; facts from them come from search-result summaries and
are tagged accordingly (**[repair-doc/snippet]**). Direct binary facts are **[ARM]**.

Confidence: **Confirmed** (direct static fact or primary listing), **Strongly supported**,
**Plausible**, **Speculative**.

---

## A. IceRiver ASIC identification

Package markings reported by repair suppliers for KS3/KS3L/KS3M hashboards:
`P37P57`, `P38C03`, `P38C39`, `P3AS24`, `P3GY31`, `P2SG48`, `P2SM88`, `P49K68`, each followed by
a 4-digit date code (e.g. `2342` = 2023 week 42; `2339`, `2345`, `2347`, `2329` also seen).
**[repair-doc/snippet] Strongly supported.**

Interpretation:
- The `P2…`/`P3…` + date-code form is an **internal production/house code, not a public commercial
  part number** (exactly the caution in the brief). Multiple distinct codes for the "same" model
  reflect date-code/revision/bin spread, not different chips. **Strongly supported.**
- Therefore the IceRiver Kaspa ASIC is a **custom, unlabeled part** with no public datasheet.
  Confidence that a public datasheet exists: **Speculative→No**.
- Package: reworked with a **stencil/solder-paste** process (M705 paste, ~400 °C hot-air, a
  per-chip stencil tool), i.e. a **fine-pitch QFN/LGA/BGA-class leadless package**, small, 4 chips
  sharing one voltage domain. Exact pin count: **Unknown** (no datasheet; no high-res pinout obtained).
  **[repair-doc/snippet] Plausible.**

Hashboard population (per repair sources): **KS3 = 112 ASICs in 28 groups of 4** (28 voltage
domains); **KS3L = 56 ASICs**; KS0 is a single integrated control+hash board with 4 ASICs.
**[repair-doc/snippet + earlier dmesg] Strongly supported.**

---

## B. ASIC package / pin analysis

No datasheet and no fetched high-res die/pinout photo, so pin functions are inferred from the
firmware + board behaviour, not read from a datasheet:
- Each chip has a **chain data in / data out** (daisy-chain), a **clock**, a **reset**
  (controller GPIO 976–979 per chain, from earlier work), and shares power in groups of 4.
- Chip **address** is assigned by enumeration (`0x02` address-assignment command), returned in the
  nonce response's address field. **[ARM] Confirmed.**
- Whether the package exposes dedicated test pins (TCK/TMS/TDI/TDO/TRST, TEST, BOOT, scan-in/out)
  is **Unknown** — not determinable without a datasheet or a high-resolution package photo.
  **Known-from-datasheet: none. Inferred-from-PCB: insufficient data.**

---

## C. PCB / test-pad analysis

I could not fetch high-resolution hashboard photographs (repair hosts egress-blocked), so no new
pad-level table can be built from primary images in this pass. What is established indirectly:
- Controller↔hashboard link is a **ribbon / ZIF connector**; a partially-seated connector causes
  chain-enumeration failure (0 chips). This connector carries the SPI/bridge link, not a wide bus.
  **[repair-doc/snippet] Strongly supported.**
- Enumeration is a **daisy-chain**: a single dead chip truncates the chain at its position
  (`8/9`, `9/26/52` mismatch patterns), confirming serial in→out chaining with per-position
  addressing. **[repair-doc/snippet] Strongly supported.**
- A board-edge/first-ASIC vs last-ASIC signal diff (chain entry vs chain exit) is architecturally
  expected but **not confirmed from a photo** here. **Plausible.**

This section is the weakest for lack of image access and is the clearest place a follow-up with
reachable high-res teardown images would add value.

---

## D. Factory-fixture analysis

A product named **"KS universal hash board tester for IceRiver"** is sold by a repair-parts vendor.
Its existence is **Confirmed [listing]**; its technical details were **egress-blocked**.
Architectural inference (not confirmed): such a tester typically supplies the hashboard's power
rails and drives the **same controller→hashboard serial link** (the SPI/bridge the stock controller
uses) to enumerate chips and read per-chip telemetry/nonces — i.e. it most likely exercises the
*existing* `7F 55` path, not a hidden one, because that is what the board exposes on its connector.
**Plausible, not Confirmed.** A fixture that contacts extra pads (e.g. per-chip test points) cannot
be ruled out without the fixture's documentation or a board photo.

---

## E. ASIC test / scan possibilities (generic, not IceRiver-specific)

Standard semiconductor manufacturing-test infrastructure (IEEE 1149.1 JTAG: TCK/TMS/TDI/TDO/TRST;
internal scan chains; MBIST/LBIST; ATPG) is common in BGA/leadless ASICs and is used for
**connectivity and structural fault testing**, not functional data readout. **Confirmed (general).**

Critical caveats the brief asked for:
- **JTAG/boundary-scan ≠ internal RAM read.** Boundary scan observes/controls *package-boundary*
  cells (pins), not internal SRAM contents. **Confirmed.**
- **An internal scan chain existing ≠ matrix SRAM externally readable.** ATPG scan shifts flip-flop
  state for test patterns; extracting a specific SRAM array's contents requires that array to be on
  an observable scan path and knowledge of the scan map — vendor-internal, not derivable here.
  **Confirmed (as a general limitation).**
- Whether the IceRiver ASIC exposes *any* of this on the package or board is **Unknown** here.

So: the absence of a documented test interface in Kaspa literature means **"undocumented,"** not
**"absent."** Manufacturing test infrastructure very likely exists on the die (normal for custom
ASICs) but its external accessibility and its connection to the matrix engine are both unestablished.

---

## F. IceRiver vs Bitmain vs Goldshell

| Miner | ASIC marking | Controller | Controller↔ASIC | Preamble | Public RE / FW | Research accessibility |
|---|---|---|---|---|---|---|
| IceRiver KS0–KS3M | `P2…/P3…`+datecode (custom, no datasheet) | Zynq-7010 + PL SPI↔UART bridge | SPI0→PL→UART daisy-chain | `7F 55` out / `55 7F` in | stock FW dumped; `rdugan/iceriver-oc` (UI/OC only) | **Medium** (full FW + bitstream in hand) |
| Bitmain KS3/KS5 | BM-family (Bitmain custom) | **CVITEK CV1835** SoC | cgminer fork **`godminer`** → serial | `0x55 0xAA`-family (BM13xx-style) | active RE (eevblog), root-exploit reported; godminer discussed | **Medium–High** (more RE community activity) |
| Goldshell KA-BOX / Pro | Goldshell custom | Goldshell controller (BraiinsOS/BMMiner-style) | serial | unknown | thin public teardown | **Low** (least public detail found) |

Key cross-vendor facts:
- Bitmain KS3's preamble family (`0x55 0xAA`, BM13xx heritage) is **different** from IceRiver's
  `7F 55` — the two Kaspa ASICs are **unrelated silicon**; do not transfer IceRiver findings to
  Bitmain or vice-versa. **[snippet + ARM] Strongly supported.**
- Bitmain's controller is a different SoC (CV1835) running `godminer`; its hashboard protocol is a
  separate research target with its own (BM-style) register protocol. **[snippet] Confirmed (controller id).**

---

## G. kHeavyHash hardware architecture (what the software reveals)

The `iceriverminer` binary contains a **software kHeavyHash reference** in `scanhash_kaspa_cpu()`,
distinct from the ASIC path `scanhash_kaspa_fpga()`. **[ARM] Confirmed.** Reference-impl internals
recovered from RTTI/symbol strings:
- `./algo/kaspa/matrix-utils/singular/{Svd,Vector,Reflector}.h`
- `singular::Svd<M,N> [M=64,N=64]`, `singular::Matrix<M,M>`, `singular::Vector<const double>`,
  `BidiagonalMatrix`, `doFrancis(...)` (Francis double-shift QR step).

Interpretation:
- The 64×64 matrix rank/non-singularity check is done in **double-precision floating point** via a
  **Golub–Kahan/Francis SVD** — this is the standard Kaspa reference approach (generate matrix from
  prePowHash, reject if not full rank, regenerate). **[ARM] Strongly supported.**
- `keccak` present (kHeavyHash's cSHAKE256 core is Keccak). **[ARM] Confirmed.**
- This is a **CPU/verification artifact**. The ASIC almost certainly does **not** use
  double-precision SVD; hardware would generate the matrix with a PRNG (XoShiRo-class) and do the
  matrix×vector in small-integer/GF arithmetic. So the software reveals the *algorithm boundary*
  (matrix is a deterministic function of prePowHash) but **not the ASIC's internal representation.**
  **Strongly supported.**

The practically useful consequence (unchanged from prior phase): the 64×64 matrix for any job is a
**deterministic public function of prePowHash**, and the ARM already holds the prePowHash, so the
matrix is **computable offline in software without any ASIC access.** **Strongly supported.**

---

## H. Matrix-engine observability possibilities

- Normal `7F 55` protocol returns **only** telemetry (PLL/temp/voltage/model) and a **nonce + chip/core
  address** (the "core" is the address high-nibble, not an internal-state field). No intermediate
  crosses the interface. **[ARM] Confirmed.**
- For an ASIC test interface to expose matrix/matrix×vector/pre-cSHAKE state, **all** of the following
  would have to hold, none of which is established: (1) the package exposes scan/JTAG externally;
  (2) the matrix SRAM / multiplier registers lie on an observable scan path; (3) the scan map is known;
  (4) the board routes those pins to reachable pads. Each is vendor-internal. **Unknown; no evidence for
  or against.**
- Even a confirmed scan chain would, by default, give **structural test access**, not a labelled dump
  of the matrix array. **Confirmed (general limitation).**

---

## I. Evidence hierarchy (research ladder — best current candidate per level)

| Level | Capability | Best candidate / evidence | Status |
|---|---|---|---|
| 1 Normal protocol | work in / nonce+telemetry out | IceRiver (fully mapped) | **Confirmed** |
| 2 Undocumented telemetry | extra sensor fields | IceRiver 0x8E 2nd-voltage, 0x80 PLL (newer FW) | **Confirmed, mundane** |
| 3 Engineering/test commands | vendor diag opcodes | none found in any IceRiver FW; Bitmain `godminer` worth checking | **Plausible (Bitmain)** |
| 4 ASIC test interface (JTAG/scan pads) | package/board test access | generic to BGA ASICs; IceRiver specifics unknown | **Unknown** |
| 5 Internal scan/BIST visibility | shift internal FF/SRAM state | no public evidence for any Kaspa ASIC | **Speculative** |
| 6 Direct matrix/intermediate read | dump matrix engine | no evidence on any candidate | **Speculative** |

---

## J. Best remaining hardware candidate
**Bitmain KS3/KS5** for *community RE depth* (CV1835 controller, `godminer`, an active eevblog RE
thread and a reported root exploit) — more public low-level activity than IceRiver, though its ASIC
is unrelated silicon. For *information already in hand*, IceRiver remains richest (full firmware +
bitstream), but its protocol surface is now exhausted.

## K. Best remaining software/documentation lead
A **reachable high-resolution IceRiver hashboard teardown / repair guide with photos**, and the
**"KS universal hash board tester" documentation**, to resolve Section C/D (test pads, first/last-ASIC
differences, what the fixture contacts). These were egress-blocked here; a mirror or archived copy
would directly advance the only open physical question.

## L. Biggest dead ends (do not revisit)
- Searching the ARM binary for a hidden matrix opcode — the ASIC path is fully mapped: telemetry + nonce only.
- Treating `P3…` markings as a commercial part number — they are house codes.
- Assuming Bitmain KS3 findings transfer to IceRiver — different silicon and preamble.
- The CPU SVD code as an ASIC-internals oracle — it is a float verification artifact.

## M. Single most promising research direction
Offline, no hardware: **compute the 64×64 matrix in software from the prePowHash in the 0x0C packet**
(deterministic, needs no ASIC). For *deeper* ASIC observability the only credible, non-destructive
next step is **documentation-level**: obtain reachable high-res hashboard photos + the IceRiver
tester's pinout to determine whether any test pads/JTAG are routed to accessible points — a
passive, static step before any (out-of-scope) physical probing.

---

## Required direct answers

**1. What exact ASIC silicon are we dealing with?**
A **custom, unlabeled IceRiver Kaspa ASIC** marked with internal house codes `P2…/P3…` + date code
(e.g. `P37P57 2342`), 4 chips per voltage domain (KS3L 56 chips, KS3 112 chips in 28 groups), in a
fine-pitch leadless package. **No public datasheet or commercial part number exists.** It is **not**
a Bitmain BM-family or Goldshell part (different controller, different `7F 55` vs `0x55 0xAA`
preamble). **Strongly supported.**

**2. Does the ASIC show evidence of a manufacturing/debug/test interface?**
No **direct** evidence either way from the material reachable here. Standard JTAG/scan/BIST is
*typical* for this class of custom BGA ASIC (so it very likely exists **on-die**), but whether it is
**exposed on the package or routed to board pads** is **Unknown** — it needs a datasheet or high-res
board photo, neither obtained. The firmware exposes **no** engineering/test command beyond the mapped
telemetry/config set. **Confirmed (firmware); Unknown (silicon pads).**

**3. Which Kaspa miner has the strongest evidence for such an interface?**
**Bitmain KS3/KS5** — most public low-level RE activity (CV1835 + `godminer`, eevblog thread, reported
root access), though that evidence is about the **controller**, not a proven ASIC matrix interface.
No Kaspa miner has public evidence of an ASIC interface exposing computation. **Strongly supported.**

**4. Credible evidence that such an interface could expose matrix-engine state?**
**None.** No firmware, bitstream, repair doc, or teardown reviewed shows matrix / matrix×vector /
pre-cSHAKE data leaving any Kaspa ASIC. Even if scan/JTAG exists, it would give structural test
access, not a labelled matrix dump, absent vendor scan maps. **Confirmed-absent in available evidence.**

**5. What can be learned without physically modifying a board?**
Everything already established statically: the full `7F 55` command set and 13-byte response map
across six models; that the ASIC returns only telemetry + nonce/address; that the matrix/SVD lives
only in the CPU reference path; the chip house-codes and hashboard population; and the comparative
controller architectures (IceRiver Zynq bridge vs Bitmain CV1835). The **one** physically-observable
unknown that still needs no board modification is **reading reachable high-res teardown photos and the
repair-tester pinout** to see whether any ASIC test pads are routed out — a documentation task, not a
hardware procedure.
