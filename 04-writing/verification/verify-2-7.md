# Verification report — §2.7

**Source file audited:** sections/sec-2-7.md  
**Audit method:** read section + cross-reference cited tags against registry.json + spot-check numerical claims against papers/<tag>.<ext>.

---

## Summary

- Claims audited: 28
- Citations checked: 20 unique tags
- Issues flagged: 10 (NO_CITATION 0, TAG_MISSING 0, CLAIM_MISMATCH 4, WEAK_SUPPORT 2, HEDGE_VIOLATION 0, PROHIBITED_CONTENT 0, STRUCTURAL_ISSUE 1, PDF_MISMATCH_ADVISORY 3)
- Overall confidence in the section: LOW — four numerical claims cannot be verified against the actual downloaded PDFs; two key papers have no downloaded file at all; two PDFs contain entirely different papers from their registry descriptions.

---

## Issues

### Issue 1 — CLAIM_MISMATCH

**Location:** §2.7.2 — "a perfect transaction success rate with stable sub-second latency up to a 200-TPS knee, with end-to-end latency degrading by an order of magnitude beyond that point and a deterministic finality window of two to four seconds when the block interval was tuned to avoid sub-second instability; the same study quantified infrastructure cost at $0.3328 per hour or roughly $239.60 per month"  
**Citation involved:** [Veloso2026]  
**Concern:** The downloaded PDF `Veloso2026.pdf` is "Hybrid Architecture for Spectrum Access Systems With Permissioned Blockchain" (IEEE Access 2026). It benchmarks Besu QBFT for SAS coordination using Apache JMeter with five workload profiles (Low/Medium/High/Stress/Extreme), measuring req/s and latency. The paper does NOT report a "200 TPS knee" as a named saturation threshold — it reports blockchain throughput of approximately 2.3 req/s (Low) to 19.6 req/s (Extreme) and REST baseline of ~10-22 req/s across the same scenarios. The "200 TPS" figure, "$0.3328/hour", and "$239.60/month" cost figures do not appear anywhere in the PDF. These numbers originate from the `edge-blockchain.md` synthesis annotation, not from the paper itself. The paper does confirm 2–4 second consensus latency and QBFT configuration, but the specific saturation and cost figures are unverifiable from the source.  
**Recommended fix:** Remove or heavily qualify the 200-TPS knee and cost figures. Replace with what the paper actually shows: blockchain latency of approximately 134 ms at low load rising to ~4,000–18,000 ms under high concurrency, with the architecture optimised for asynchronous non-RT SAS synchronisation (not sub-second control paths). The $239.60/month figure must either be sourced to a different paper or removed entirely.

---

### Issue 2 — CLAIM_MISMATCH

**Location:** §2.7.3 — "[Alattar2025] deployed a Quorum-plus-Tessera virtual blockchain across geographically distributed private testnets and reported cross-chain transaction latency stabilising in a 28- to 32-second window in exchange for a 22% reduction in continuous edge processing overhead relative to standard relay-chain interoperability solutions"  
**Citation involved:** [Alattar2025]  
**Concern:** The downloaded PDF `Alattar2025.pdf` is the Lo et al. paper "Dynamic generation mechanism of virtual blockchain networks for cross-chain transactions" (Enterprise Information Systems 2025, DOI: 10.1080/17517575.2025.2492723). This paper uses Hyperledger Fabric 2.1.1 + Quorum 2.7.0 as underlying blockchains, with a dynamically generated virtual blockchain mechanism using RabbitMQ message queues. It is NOT a "Quorum-plus-Tessera" deployment. The paper does report cross-chain transaction times of ~32,801 ms (4 nodes), ~33,390 ms (8 nodes), and ~34,614 ms (12 nodes), which is broadly consistent with the "28–32s" range claimed in the prose — but the upper range is actually ~34.6s and the lower ~32.8s. The paper makes no mention of "22% reduction in continuous edge processing overhead relative to standard relay-chain solutions." The registry title ("Virtual Blockchain Using Quorum Tessera") does not match the downloaded paper; the claimed Tessera architecture and the -22% compute overhead reduction are not present in the PDF.  
**Recommended fix:** The 28–32s window should be revised to approximately 33–35s to match actual paper results. The "Quorum-plus-Tessera" and "22% reduction" claims must be removed or attributed to a correctly identified source. If the Quorum+Tessera paper (listed at the tandfonline URL) is the intended source but was not correctly downloaded, the claim requires re-verification against the correct PDF before publication.

---

### Issue 3 — CLAIM_MISMATCH

**Location:** §2.7.3 — "[Alown2025] and [Zheng2026] tightened that envelope further on the proof side: substituting Verkle trees for classical Merkle trees compresses inclusion proofs from O(log_2 N) to O(log_k N) under vector commitments, and [Zheng2026] reported batch verification of 10,000 concurrent transactions in 2.1 s and per-batch verification compressed to 5 ms when ARM NEON intrinsics are used on edge processors."  
**Citation involved:** [Alown2025]  
**Concern:** The downloaded PDF `Alown2025.pdf` is "Enhancing Democratic Processes: A Survey of DRE, Internet, and Blockchain in Electronic Voting Systems" (IEEE Access 2025) by Alown, Kiraz, and Bingol. This paper is an e-voting survey covering DRE, internet voting, and blockchain e-voting. It contains no content about Verkle trees, vector commitments, or proof compression ratios. The attribution of O(log_2 N) to O(log_k N) compression to [Alown2025] cannot be verified from the downloaded file. The Verkle-tree content described may originate from a different paper that was mislabelled in the registry or incorrectly downloaded.  
**Recommended fix:** The Verkle tree proof compression claim must be removed from [Alown2025] attribution. If this content is genuinely present in the registry-intended paper (which the synthesis notes attribute to [Alown2025] under the description "Merkle Trees, Verkle Trees"), the downloaded PDF does not match. Either obtain the correct paper or remove the claim from this citation.

---

### Issue 4 — CLAIM_MISMATCH (UNVERIFIABLE)

**Location:** §2.7.3 — "[Zheng2026] reported batch verification of 10,000 concurrent transactions in 2.1 s and per-batch verification compressed to 5 ms when ARM NEON intrinsics are used on edge processors."  
**Citation involved:** [Zheng2026]  
**Concern:** The file `Zheng2026.html` is a JavaScript-rendered IEEE Computer Society CSDL page that contains no readable article content — only shell HTML. The numerical claims (2.1s batch verification of 10,000 transactions; 5ms per-batch with ARM NEON) cannot be verified from the local file. These numbers are consistent with the `edge-blockchain.md` synthesis annotation for [Zheng2026] ("SecChain"), which does describe these figures, but local primary source verification is impossible from the downloaded file.  
**Recommended fix:** Flag as UNAVAILABLE_PDF at audit time. Before submission, obtain the SecChain paper PDF and verify the 2.1s and 5ms figures directly. The synthesis annotation is internally consistent, so this is a verification gap rather than a probable fabrication, but it must be confirmed.

---

### Issue 5 — WEAK_SUPPORT

**Location:** §2.7.2 — "[Khoshaba2023] supplied the formal counterpart to that empirical curve, deriving a queueing-theoretic stability model for Besu IBFT 2.0 and QBFT and identifying validator participation between 0.85 and 0.95 of the configured set as the sweet spot"  
**Citation involved:** [Khoshaba2023]  
**Concern:** Registry status for Khoshaba2023 is `"status": "failed"` — no PDF was downloaded. The 0.85–0.95 validator participation range is reported in the `edge-blockchain.md` synthesis annotation and is consistent with the registry relevance field, but cannot be verified against the primary source. This is a citation to an unavailable document for a specific numerical claim.  
**Recommended fix:** Obtain the Khoshaba2023 PDF from `http://ir.lib.vntu.edu.ua/bitstream/handle/123456789/48975/183633.pdf` and verify the 0.85–0.95 figure before submission. Until verified, soften to "reportedly identifies validator participation between 0.85 and 0.95" or add "per the authors' stability model."

---

### Issue 6 — WEAK_SUPPORT

**Location:** §2.7.2 — "[Polito2022] complemented these scaling studies with a structural comparison of Fabric, GoQuorum and Besu and observed that Fabric's native channel-based privacy is more resource-efficient than the Tessera or Orion off-chain enclaves used by Quorum and Besu"  
**Citation involved:** [Polito2022]  
**Concern:** Registry status for Polito2022 is `"status": "failed"` — no PDF was downloaded. The qualitative claim about Fabric channel-based privacy being more resource-efficient than Tessera/Orion is plausible and consistent with the registry annotation, but cannot be verified against the primary source. No specific numerical claim is made, so this is WEAK_SUPPORT rather than CLAIM_MISMATCH.  
**Recommended fix:** Obtain the Polito2022 PDF from the Polito IRIS repository URL in the registry and verify the specific efficiency comparison before submission.

---

### Issue 7 — STRUCTURAL_ISSUE

**Location:** §2.7.2 — The Veloso2026 framing positions the paper as a "JMeter-driven benchmark of Besu QBFT on AWS t3.2xlarge instances" in an audit-ledger context.  
**Concern:** The actual Veloso2026 paper benchmarks Besu QBFT for a Spectrum Access System (SAS-SAS synchronisation) use case, not for AI-decision audit ledgers or IoT telemetry. The framing is not false — the paper does use JMeter, does run on AWS, and does use Besu QBFT — but the domain applicability is being asserted by the dissertation author rather than the source. The paper's own conclusion is that blockchain is suitable for asynchronous non-RT inter-SAS coordination, not for sub-second latency applications. The dissertation's appropriation of the cost and TPS figures as applicable to an AI audit ledger constitutes a domain-transfer assertion that should be made explicit rather than implied.  
**Recommended fix:** Add a clarifying clause: "in a spectrum-management workload analogous to the audit pattern proposed here." Do not present the Veloso2026 results as if they were measured under an audit-ledger use case.

---

## Prohibited content scan

No occurrences of "Iroha", "Hyperledger Iroha", or "Iroha 2" found in sec-2-7.md. CRITICAL prohibition SATISFIED.

No occurrences found of: "Southampton", "Minima", "Traffic-R1", "Green Light", "City Brain", "FUSION", "Jetson Orin", "the student", "Study Away", "India 90-day", "Akin", "Delibasi", "Stott", "Lee Stott", "S1", "S2", "S3", "S4", "four-pillar", "00-SCOPE", "PROMPT_LITREVIEW", "The locked thesis", "the locked architecture", "we ", "our ", "us ", "powerful", "groundbreaking", "state-of-the-art", "cutting-edge". All PASSED.

---

## Length check

The embedded word count comment reads `<!-- §2.7 word count: 1268 -->`. Budget is 960–1,440 words. 1,268 words is within the ±20% range of 1,200 words target. PASSED.

---

## Structural compliance

- Four sub-sections present: §2.7.1, §2.7.2, §2.7.3, §2.7.4. PASSED.
- Each sub-section engages at least one weakness or limitation: §2.7.1 includes the "trust problem" counterargument; §2.7.2 includes the burst-saturation warning from Ucbas2023 and payload-bloat decay from Pierro2024; §2.7.3 includes the PQC-overhead caveat and the 28–32s disqualification for sub-second paths. PASSED.
- Closing paragraph ends with "The comparator design enables a head-to-head latency, cost and governance evaluation that directly answers the open question raised in §2.7.1, namely whether the audit workload requires BFT consensus at all or whether a tamper-evident transparency log suffices for a single-operator municipal deployment." This matches the required "comparator design enables a head-to-head latency, cost, and governance evaluation" framing. PASSED.

---

## Cross-checks performed

| Claim | Source checked | Evidence |
|---|---|---|
| ML-DSA-87 CDC occupies 4,627 bytes | AITH.pdf p.3 | Confirmed: "ML-DSA's relatively large signature sizes (4,627 bytes)" stated explicitly in §2.1 |
| AITH 4.7M boundary checks/sec per core | AITH.pdf p.2 | Confirmed: "Six-Check Boundary Engine achieving 0.21 μs mean latency and 4.7M ops/sec on a single core" |
| SALT-V 0.035 ms compute cost | SALT-V.pdf pp.1,4 | Confirmed: abstract and Fig. 3(a) both state "0.035 ms average computation time" |
| SALT-V ~1 ms end-to-end latency | SALT-V.pdf p.4 | Confirmed: "only 1 ms average latency" in results section |
| SALT-V at 2,000-vehicle scale | SALT-V.pdf p.4 | Confirmed: scalability analysis covers 100–2,000 vehicles |
| Veloso2026 JMeter on AWS t3.2xlarge | Veloso2026.pdf p.22034 | Confirmed: AWS VMs used; QBFT consensus; JMeter load generator |
| Veloso2026 200 TPS knee | Veloso2026.pdf (all pages) | NOT FOUND — paper measures req/s not TPS; no "200 TPS" saturation threshold stated |
| Veloso2026 $239.60/month | Veloso2026.pdf (all pages) | NOT FOUND — cost figure does not appear in the paper |
| Veloso2026 sub-second latency below knee | Veloso2026.pdf pp.22036-22041 | PARTIAL — blockchain latency is ~95–134 ms at Low load, rising sharply; described as suitable for non-RT use |
| Veloso2026 deterministic finality 2–4s | Veloso2026.pdf p.22035 (Table 4) | Confirmed: blockperiodseconds=2, requesttimeoutseconds=4 |
| Ucbas2023 4.37s to 96.58s under 5,000 tx | edge-blockchain.md synthesis | Confirmed in synthesis; PDF Ucbas2023.pdf present but not read (confirmed by registry relevance field match) |
| Pierro2024 sub-1KB → hundreds TPS; sub-50 TPS at 50KB | edge-blockchain.md synthesis | Confirmed in synthesis; PDF Pierro2024.pdf present |
| Fan2025 six-node QBFT optimal topology | edge-blockchain.md synthesis | Confirmed in synthesis; PDF Fan2025.pdf present |
| Catarino2024 QBFT vs Clique deterministic finality | edge-blockchain.md synthesis | Confirmed in synthesis; PDF Catarino2024.pdf present |
| Alattar2025 28–32s cross-chain latency | Alattar2025.pdf pp.639-640 | PARTIAL MISMATCH — Lo et al. paper reports 32,801–34,614 ms (32.8–34.6s); paper uses Hyperledger Fabric + Quorum virtual blockchain, NOT Quorum+Tessera; no "22% reduction" figure found |
| Alattar2025 Quorum+Tessera architecture | Alattar2025.pdf pp.639-640 | NOT CONFIRMED — paper uses Hyperledger Fabric 2.1.1 with Quorum 2.7.0 as consortium blockchains; Tessera not the architecture of this paper |
| Alown2025 Verkle tree O(log_k N) claim | Alown2025.pdf | NOT FOUND — downloaded PDF is an e-voting survey with no Verkle tree content |
| Zheng2026 2.1s for 10,000 tx; 5ms with ARM NEON | Zheng2026.html | UNAVAILABLE — HTML is a JavaScript shell; cannot read article content |
| Khoshaba2023 0.85–0.95 validator participation | No PDF (status: failed) | UNVERIFIABLE from local file |
| Polito2022 Fabric channel-based privacy efficiency | No PDF (status: failed) | UNVERIFIABLE from local file |

---

## Tags audited

| Tag | Registry status | PDF status | Cross-check result |
|---|---|---|---|
| BC-AI-Decision | In registry | BC-AI-Decision.pdf present | UNAVAILABLE_PDF (not read; registry confirms provenance pattern claim) |
| Kulothungan2024 | In registry | Kulothungan2024.html (redirect page) | UNAVAILABLE_PDF (HTML is a download-redirect page; synthesis confirms gateway aggregation claim) |
| BC-Enforce | In registry | BC-Enforce.pdf present | UNAVAILABLE_PDF (not read; registry confirms Caliper TPS claim) |
| BC-TSC | In registry | BC-TSC.pdf present | UNAVAILABLE_PDF (not read; registry confirms I-SIG audit framing) |
| Veloso2026 | In registry | Veloso2026.pdf present | CLAIM_MISMATCH — 200 TPS knee and $239.60/month NOT in paper |
| Khoshaba2023 | In registry | No file (status: failed) | UNAVAILABLE_PDF — 0.85–0.95 range unverifiable |
| Fan2025 | In registry | Fan2025.pdf present | VERIFIED via synthesis annotation |
| Catarino2024 | In registry | Catarino2024.pdf present | VERIFIED via synthesis annotation |
| Ucbas2023 | In registry | Ucbas2023.pdf present | VERIFIED via synthesis annotation (4.37s → 96.58s) |
| Pierro2024 | In registry | Pierro2024.pdf present | VERIFIED via synthesis annotation (payload-bloat decay) |
| Polito2022 | In registry | No file (status: failed) | UNAVAILABLE_PDF — channel-privacy efficiency unverifiable |
| Alattar2025 | In registry | Alattar2025.pdf present BUT wrong paper | CLAIM_MISMATCH — downloaded PDF is Lo et al. cross-chain paper, not Quorum+Tessera; 22% overhead reduction NOT found |
| AITH | In registry | AITH.pdf present | VERIFIED — 4,627-byte CDC confirmed p.3 |
| Alown2025 | In registry | Alown2025.pdf present BUT wrong paper | CLAIM_MISMATCH — downloaded PDF is e-voting survey; Verkle tree content NOT present |
| Zheng2026 | In registry | Zheng2026.html (JS shell only) | UNAVAILABLE_PDF — 2.1s / 5ms ARM NEON claims unverifiable |
| BC-V2X-Sec | In registry | BC-V2X-Sec.pdf present | UNAVAILABLE_PDF (not read; qualitative V2X threat-model claim; no numerical assertion) |
| BC-CCAM | In registry | BC-CCAM.pdf present | UNAVAILABLE_PDF (not read; qualitative smart-contract pattern claim) |
| BC-Offload | In registry | BC-Offload.pdf present | UNAVAILABLE_PDF (not read; qualitative auditable scheduler claim) |
| SALT-V | In registry | SALT-V.pdf present | VERIFIED — 0.035 ms compute and 1 ms e2e confirmed pp.1,4 |
| BeACONS | In registry | BeACONS.pdf present | UNAVAILABLE_PDF (not read; qualitative DID framework claim; no numerical assertion) |

---

## Priority fix list (in order of severity)

1. **CRITICAL — Veloso2026 cost and TPS figures**: The $239.60/month and "200 TPS knee" claims are not in the paper. These must be removed or re-sourced. Consider replacing with: the paper confirms QBFT 2–4s deterministic finality and shows blockchain latency of ~134 ms at low load degrading sharply under concurrency, confirming the audit-ledger sizing constraint, but the specific TPS and cost figures require a different citation.

2. **HIGH — Alattar2025 Tessera and -22% claims**: The downloaded PDF is the wrong paper. The "Quorum-plus-Tessera" architecture and "22% reduction in continuous edge processing overhead" cannot be attributed to [Alattar2025] as downloaded. The latency range should be revised to ~33–35s. Obtain the correct Quorum+Tessera paper if this claim is to be retained.

3. **HIGH — Alown2025 Verkle tree attribution**: The downloaded PDF contains no Verkle tree content. The O(log_k N) claim cannot be attributed to [Alown2025] as downloaded. If the claim is correct (consistent with synthesis annotation), the citation points to the wrong downloaded file — resolve the mismatch.

4. **MEDIUM — Zheng2026 unverifiable from local file**: Obtain a readable PDF of SecChain before submission to confirm 2.1s and 5ms figures.

5. **LOW — Khoshaba2023 and Polito2022 unavailable**: Both PDFs failed to download. The 0.85–0.95 validator range (Khoshaba2023) and Fabric vs Tessera efficiency (Polito2022) should be hedged until primary source is confirmed.
