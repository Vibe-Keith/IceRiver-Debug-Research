# IceRiver cross-model RX-parser differential analysis

Scope: **offline static analysis only** — no device interaction, transmission, FPGA
simulation, or fuzzing. Binaries are the `iceriverminer` ELFs extracted from the public
`mcmickburns/iceriverminer_dump`. Web search used read-only for third-party implementations.

Confidence tags: **Confirmed** (static fact in code), **Strongly supported**, **Plausible**, **Unknown**.
A "static fact" is *"handler X reads frame byte N"*; any meaning assigned to byte N is an interpretation.

Method: a dispatcher locator (`scripts/dispatch.py`) finds the `cmp 0x80/0x81/0x8e/0x82`
chain and the type-byte stack offset in each binary, then records the frame-byte offsets each
handler loads (`ldrb`/`ldrh`/`ldr`, with word loads expanded to the bytes they cover).
`scripts/nonce.py` does the same for the bit-7-clear nonce handler. Addresses below are verified
per binary.

## Binaries compared (distinct md5)

| Tag | Model | md5 (12) | size | notes |
|---|---|---|---|---|
| KS0 | KS0 | a70e38474515 | 1518468 | factory 2023-09-16; == KS0 OC First_Release/160GHs |
| KS1 | KS1 | 2c84b128ea36 | 1522576 | factory |
| KS2 | KS2 | 66309b081574 | 1522576 | factory |
| KS3 | KS3 | d45f9db57c7d | 1547392 | factory |
| KS3L_run | KS3L | b02f7eb89811 | 1531000 | **running build on the dumped unit** |
| KS3L_fw | KS3L | 909e955d5737 | 1543296 | shipped KS3L firmware |
| KS3M | KS3M | 7f2447bca693 | 1543296 | == KS3L `var/volatile/test/miner` |
| KS3M_preml | KS3M | f36f8e1de5f5 | 1543292 | pre-model-lock |

Key version fact: on the dumped KS3L the **running** binary (`b02f7eb8`) is an *earlier/thinner*
build than the **shipped** KS3L firmware (`909e9557`) — it reads fewer response fields (§D). **Confirmed.**

---

## A. Cross-model protocol comparison

The inbound frame is identical in all 8 binaries: `55 7F | 9 payload | type@11 | checksum@12`,
13 bytes, additive checksum (SWAR summer), dispatch on byte 11, types `0x80/0x81/0x82/0x8E` +
bit-7-clear nonce, "unknown command: %02X" default. The dispatcher and all five handlers were
located in every binary. **Confirmed.** No model defines any other inbound frame length or type.

The whole 13-byte parser lives inside **`scanhash_kaspa_fpga()`** (string `0x180424`, entered at
`0x1181fa` in KS3L_run — the `0x118xxx` consumer region). A separate **`scanhash_kaspa_cpu()`**
(string `0x17faa4`, ref `0x114a2e`) is the software reference path (§I). **Confirmed.**

---

## B/C. Per-handler byte-usage map (payload bytes 2–10)

"used" = some instruction loads it; "—" = never loaded in that handler in that binary.
Word loads (`ldr`) expand to 4 bytes; so e.g. 0x82's `ldr [base+5]` covers 5,6,7,8.

### 0x80 (status: PLL + counter + chip id)
| byte | KS0 | KS1 | KS2 | KS3 | KS3L_run | KS3L_fw | KS3M | KS3M_preml |
|---|---|---|---|---|---|---|---|---|
| 2,3 | — | — | — | — | — | — | — | — |
| 4,5 | — | — | — | used | used | used | used | used |
| 6,7,8,9 | used | used | used | used | used | used | used | used |
| 10 | used | used | used | used | used | used | used | used |

Interp: 4,5 = PLL readback (format `"…pll : %d"`), present only in KS3-generation. 6–9 = 32-bit
counter (×10, "noncecnt"). 10 = chip index. **Bytes 2,3 are read by NO model.**

### 0x81 (temperature)
All models: use **7,8,9,10**; bytes 2,3,4,5,6 read by no model. Identical. **Confirmed.**
Interp: 7–9 = 12-bit temp raw; 10 = chip index.

### 0x82 (model string)
All models use **5,6,7,8** (word load at 5) **,9,10**; KS3 additionally reads **4**.
Bytes 2,3 (and 4 except KS3) read by no model. Interp: 4-char model/ID string + model code byte 10.

### 0x8E (voltage) — the one field that differs in *interpretation*
| byte | KS0 | KS1 | KS2 | KS3 | KS3L_run | KS3L_fw | KS3M | KS3M_preml |
|---|---|---|---|---|---|---|---|---|
| 2,3 | used | used | used | used | used | used | used | used |
| 7,8 | — | **used** | **used** | **used** | — | **used** | **used** | — |
| 10 | used | used | used | used | used | used | used | used |
| 4,5,6,9 | — | — | — | — | — | — | — | — |

Interp: bytes 2,3 = voltage A `((b2<<8|b3)>>2)` → float. In KS1/KS2/KS3/KS3L_fw/KS3M the handler
also reads bytes 7,8 = a **second voltage** `(((b7&0x3F)<<8)|b8)>>2`, then compares the two and
keeps the **lower** rail (verified: KS3L_fw `0x119830`, `vcmpe.f64 d14,d15` → min; KS3L_run `0x1194a8`
reads only 2,3). **Confirmed (second-voltage read in those builds).**

### bit-7-clear nonce
All models read bytes **2–9** (64-bit nonce + chip index at byte 2); KS0/KS3L_run/KS3M_preml also
touch byte 10. No model extracts any field adjacent to the nonce beyond nonce + chip id. **Confirmed.**

---

## D. Ignored-field investigation — the headline question

> **Does any IceRiver model/version/tool interpret a response byte the KS3L retail miner ignores?**

**Yes — exactly one field, and it is mundane.** The KS3L *running* build (`b02f7eb8`) ignores
0x8E bytes **7,8**. KS1, KS2, KS3, the shipped KS3L firmware (`909e9557`) and KS3M **do** read them,
as a **second supply-voltage rail**, keeping the lower of the two readings.
- Exact byte: 0x8E payload bytes 7,8.
- Meaning: second voltage ADC value, `(((b7&0x3F)<<8)|b8)>>2`, same scale as voltage A.
- Model/version: used by KS1/KS2/KS3/KS3L-fw/KS3M; ignored by KS0/KS3L-run/KS3M-preml.
- Function: 0x8E handler (`0x119830` in KS3L_fw). Confidence: **Confirmed**.

Second difference (PLL): 0x80 bytes **4,5** are read by all KS3-generation builds but not by KS0/KS1/KS2
— a PLL/frequency readback, also mundane. **Confirmed.**

### Bytes read by NO handler in ANY model (truly never interpreted)
| type | never-read payload bytes |
|---|---|
| 0x80 | 2, 3 |
| 0x81 | 2, 3, 4, 5, 6 |
| 0x82 | 2, 3 (4 on non-KS3) |
| 0x8E | 4, 5, 6, 9 |

Their content is **Unknown** from static analysis (no code path reads them). Ranked ordinary
explanations (per request): reserved/padding or chip-id echo most likely (the frame already carries
a chip index in byte 10 and the fields are short); status/error flags possible; **no evidence** of a
computational intermediate. The frame is only 13 bytes — far too small to carry matrix (≈2 KB) or
matrix×vector (64×u16 ≈ 128 B could fit in principle, but no handler assembles such a vector and no
multi-frame accumulation exists).

---

## E. Firmware-version differences

Within a model the parser is stable: KS0 == KS0_first (byte-identical), KS1 ≈ KS1_oc, KS2 ≈ KS2_oc
(OC builds change clock/voltage *setpoints*, not the parser). The only parser evolution found is the
KS3L_run→KS3L_fw delta: the **later** shipped firmware **added** the second-voltage read (0x8E 7,8).
So the ignored field is newer, not vestigial — it was introduced, not dropped. **Confirmed.**

---

## F. Factory/test software findings

- KS3L `var/volatile/test/miner/iceriverminer` is byte-identical to the KS3M shipped binary
  (`7f2447bc`) — a "test" slot, but the *same* miner, no extra parser. **Confirmed.**
- No separate board-test / diagnostic binary with its own 13-byte parser exists in the dump; grep for
  the dispatcher pattern and the `55/7F` header checks finds the parser only inside `iceriverminer`.
- The stock binary already contains a **raw-frame debug path**: at `0x118a7c` it calls the hex dumper
  (`"bf----" %02X`) with length `0xD` over the frame base — i.e. a `-D/-P` protocol-dump flag prints
  the **entire raw 13-byte response**, including the bytes the field handlers ignore. This path only
  *prints* the 13 bytes that already exist; it exposes no additional data. **Confirmed.**

---

## G. Third-party protocol implementations

- `rdugan/iceriver-oc` (the known community modified firmware) layers a web UI / overclocking on top
  of the **stock** `iceriverminer`; it does not reimplement the serial parser. Its "per-board average
  chip voltage/clock" stats are the stock parser's already-decoded 0x8E/0x80 fields. **No new field interpretation.**
- Web search found **no** independent implementation of the IceRiver `7F 55` protocol, and no
  standalone IceRiver hashboard tester that parses extra fields. The active low-level Kaspa-ASIC RE
  work that surfaced targets **Bitmain**'s KS3 (CV183x SoC, `godminer`) — different silicon and
  protocol, not applicable. **No external source interprets fields the stock miner ignores.**

Sources: [rdugan/iceriver-oc](https://github.com/rdugan/iceriver-oc),
[Kryptex IceRiver overview](https://pool.kryptex.com/en/articles/iceriver-ks0-ks1-ks2-ks3-ks3l-en),
[eevblog Bitmain KS3 RE thread](https://www.eevblog.com/forum/beginners/reverse-engineering-bitmain-asic/).

---

## H. Work-packet (0x0C) differences

All models build `7F 55 FF 0C <len> <payload> <cksum>` preceded by a `0x0D` mode byte. The payload
carries a prePow/header-derived block + per-chain nonce-range offsets (KS3L detail in
`docs/asic_rx_protocol.md`). Packet length tracks model but the structure — prePow block in, nonce
range per chain — is common. No model's 0x0C packet contains matrix-sized data (would need ≈2 KB).
**Confirmed (no matrix in the outbound packet).** Exact per-model length byte: **Plausible** targets
for a future focused diff; not yet tabulated field-by-field across all six.

---

## I. kHeavyHash evidence in the binary

- Every model links the **software reference kHeavyHash**: RTTI/assert strings for
  `singular::Svd<M,N> [M=64,N=64]` and paths `./algo/kaspa/matrix-utils/singular/{Svd,Vector,Reflector}.h`.
  This is the 64×64 matrix generation + SVD rank/singularity check (the generator rejects
  rank-deficient matrices). Present in all 8 binaries. **Confirmed.**
- Two scan entry points: `scanhash_kaspa_cpu()` (software path, where the matrix code lives) and
  `scanhash_kaspa_fpga()` (ASIC path, where the 0x0C sender and 13-byte parser live). The matrix code
  is **not** in the ASIC path. **Confirmed.**
- Implication: the 64×64 matrix is a deterministic public function of prePowHash. The ARM already
  holds the prePowHash (it builds the 0x0C packet from it), so the matrix for any job is computable
  **offline in software** — it is not secret and does not need to come from the ASIC. **Strongly supported.**

---

## J. Matrix / intermediate visibility

- **A. Does the 64×64 matrix leave the ASIC?** No evidence. Inbound frames are fixed 13 bytes; no
  handler or pre-dispatch path accumulates matrix-sized data. **Confirmed-absent in software.**
- **B. Does matrix×vector leave the ASIC?** No evidence. No handler assembles a 64-element vector; the
  only multi-byte inbound quantity is the 64-bit nonce. **Confirmed-absent.**
- **C. Does pre-cSHAKE data leave the ASIC?** No evidence. **Confirmed-absent.**
- **D. Any ASIC diagnostic data that could indirectly expose computational state?** Only telemetry:
  PLL readback (0x80 4,5), counter (0x80 6–9), temperature (0x81), model (0x82), one–two voltages
  (0x8E). Plus the truly-unread bytes (§D) whose content is Unknown but which are too few/small to be
  an intermediate. **Strongly supported: telemetry only.**
- **E. Is the remaining uncertainty beyond static software analysis?** Yes. The only open item is the
  content of the never-read bytes (0x80:2,3; 0x81:2–6; 0x82:2,3; 0x8E:4,5,6,9), which the firmware
  never touches, so their values are observable **only** by a passive bus capture — out of scope here.

---

## K. What static analysis has definitively established

1. One inbound frame format (13 bytes) across all models; dispatch on byte 11; additive checksum. **Confirmed.**
2. The complete per-model byte-usage map (§B/C). **Confirmed.**
3. The only cross-model *used-vs-ignored* differences are a second voltage (0x8E 7,8) and a PLL
   readback (0x80 4,5) — both ordinary sensors/telemetry. **Confirmed.**
4. The matrix/SVD code is a CPU reference path, separate from the ASIC path; the ASIC returns only
   telemetry + nonce. **Confirmed.**
5. No third-party or factory software interprets any additional field. **Confirmed (within available corpus).**

## L. What requires hardware evidence
- Actual values/meaning of the never-read bytes (§D,J-E).
- Whether the ASIC would *emit* anything beyond the 13-byte frame to a non-stock request (the stock
  parser could not consume it even if it did). This cannot be resolved statically and is out of scope.

## M. Best remaining static target
Field-by-field diff of the **0x0C work packet across all six models** (§H) to confirm no model injects
an ASIC-specific field — the last outbound structure not yet exhaustively cross-compared. After that,
static analysis of this corpus is effectively exhausted; further progress needs a passive capture.

---

## Required summary answers

**Most interesting newly discovered field:** 0x8E response bytes 7,8 — a *second* supply-voltage
rail that KS1/KS2/KS3/KS3L-firmware/KS3M read (keeping the lower rail) but the KS3L *running* build
and KS0 ignore. Interesting only as proof that "ignored ≠ hidden computation": it is a sensor value.

**Most interesting alternate firmware/tool:** the shipped KS3L firmware `909e9557` vs the running
`b02f7eb8` — same unit, the newer build *added* the second-voltage read, showing the parser grows by
adding telemetry, not by exposing computation. (`rdugan/iceriver-oc` adds nothing at the protocol level.)

**Strongest evidence against matrix visibility:** the inbound frame is a fixed 13 bytes with no
multi-frame accumulation anywhere in any model, and the 64×64 matrix/SVD code is confined to the CPU
reference path, never the ASIC path — the ASIC returns only telemetry and a 64-bit nonce.

**Strongest evidence that more ASIC state may exist:** several payload bytes are never read by any
model (0x80:2,3; 0x81:2–6; 0x82:2,3; 0x8E:4,5,6,9). Their content is genuinely unknown from static
analysis. This is weak evidence (they are few and small), but it is the only unexplained surface.

**Single best next research target:** a *passive* logic-analyzer capture of those never-read bytes on
the owner's own board (out of scope for this static pass) — or, fully offline, computing the 64×64
matrix in software from the prePowHash the ARM already places in the 0x0C packet, which needs no ASIC
access at all because matrix generation is a deterministic public function of prePowHash.
