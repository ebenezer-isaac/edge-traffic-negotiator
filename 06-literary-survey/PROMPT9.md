# Prompt 9 — Verified-source identity/registry and physical-consistency detection anchors for the pivoted dissertation

## Context (do not skip — this constrains the answer)

This is the ninth prompt in the dissertation literature survey. **Note (2026-07-21): the project has since re-pivoted again; the current single source of truth is [`../specs/001-edge-negotiator/MASTER-SPEC.md`](../specs/001-edge-negotiator/MASTER-SPEC.md) (the `PROJECT-DECISION-BRIEF.md` this prompt originally cited has been deleted).** Prompt 9 was run on **2026-05-31**, under the then-current "Verified-Source Cross-Junction Coordination" framing, to fill the two literature gaps that pivot opened; both pillars below remain directly useful background under the current thesis (external identity root + registry, and the conservation/CUSUM + corroboration gate):

- **Pillar A — Identity / registry / revocation.** Anchors for a single-administrative-domain agent-identity registry (a permissioned membership registry: register, validate, revoke verified sources) without committing to the full DID/VC cross-domain machinery. The selected analogues deliberately bracket the design space — from a minimal membership-proof registry to full ledger-anchored DID/VC mutual authentication — and several supply explicit *evidence against* over-engineering for a 3-month build.
- **Pillar B — Physical-consistency / spoofing-&-fault detection.** Anchors for a conservation/plausibility invariant that cross-checks neighbour reports, plus the key adversarial bound (physically-consistent FDI evades residual checks) that motivates pairing the invariant with the Pillar-A authentication layer.

Twenty-eight papers were gathered: **15 in Pillar A** (14 cached, 1 dropped) and **14 in Pillar B** (all cached). A file `papers/<key>.pdf` existing in the survey folder counts as **CACHED**; this was confirmed by directory listing against `prompt9-identity-urls.txt` and `prompt9-detection-urls.txt`.

`status` values below: **CACHED** = PDF present in `papers/`; **DROPPED** = deliberately excluded, no copy fetched.

---

## Pillar A — Identity / registry / revocation

| key | title | authors | year | venue | status | relevance |
|---|---|---|---|---|---|---|
| proofmember23 | Combining Decentralized IDentifiers with Proof of Membership to Enable Trust in IoT Networks | A. Pino, D. Margaria, A. Vesco | 2023 | IEEE ITNAC 2023 | CACHED | Closest analogue to a single-domain permissioned membership registry; mutual auth via DID key-ownership + proof a DID belongs to an evolving trusted set; deliberately drops VCs for the same-administrative-domain case. |
| pkchain25 | PKChain: Compromise-Tolerant and Verifiable Public Key Management System | J. Y. Mosakheil, K. Yang | 2025 | IEEE Internet of Things Journal 12(3) | CACHED (IEEE version of record; eprint mirror also cached) | On-chain public-key register/update/query/validate/revoke via threshold validation; on-chain status removes need for CRL/OCSP. |
| dcsm24 | Decentralized Credential Status Management: A Paradigm Shift in Digital Trust | P. Herbke et al. | 2024 | arXiv:2406.11511 (also IEEE) | CACHED | Frames centralized-PKI → DPKI transition (DigiNotar/Symantec), blockchain credential-status/revocation; argues a root authority is still needed. |
| didlink24 | DID Link: Authentication in TLS with Decentralized Identifiers and Verifiable Credentials | S. Rodriguez Garzon, D. Natusch, A. Philipp, A. Küpper, H. J. Einsiedler, D. Schneider | 2024 | arXiv:2405.07533 (also IEEE) | CACHED | Mutual auth in the TLS handshake using DID-bound self-signed X.509 + verifiable presentations; reports DID resolution 3–42× slower than CA X.509 (overhead caveat). |
| didvcsurvey24 | A Survey on Decentralized Identifiers and Verifiable Credentials | C. Mazzocca, A. Acar, A. S. Uluagac, R. Montanari, P. Bellavista, M. Conti | 2024 | arXiv:2402.02455 (also IEEE COMST 2025) | CACHED | DID/VC survey: verifiable data registries, revocation (Revocation List 2020), threats, edge/IoT applicability. |
| slvcdida25 | SLVC-DIDA: Signature-less Verifiable Credential-based Issuer-hiding and Multi-party Authentication for Decentralized Identity | T. Xie, K. Gai, J. Yu, L. Zhu, B. Xiao | 2025 | arXiv:2501.11052 | CACHED | DID/VC multi-party auth with Merkle-tree VC list + accumulator revocation; motivated by issuer-hiding/privacy (cross-domain features the project does NOT need). |
| aiagents25 | AI Agents with Decentralized Identifiers and Verifiable Credentials | S. Rodriguez Garzon, A. Vaziry, E. M. Kuzu, D. E. Gehrmann, B. Varkan, A. Gaballa, A. Küpper | 2025 | arXiv:2511.02841 (accepted ICAART 2026) | CACHED | Ledger-anchored DID + self-hosted VC for zero-trust mutual auth between AI agents; its OWN prototype reports brittleness (4–36% completion) and an LLM silently skipping a security step — evidence AGAINST full DID/VC for a 3-month build. |
| endorse25 | Endorsement-Driven Blockchain SSI Framework for Dynamic IoT Ecosystems | (authors unconfirmed) | 2025 | arXiv:2507.09859 | CACHED | Layered blockchain SSI for IoT: issuer onboarding, endorsement-based trust, distributed credential revocation. |
| dpkidrone24 | Decentralized PKI Framework for Data Integrity in Spatial Crowdsourcing Drone Services (D2XChain) | J. Akram, A. Anaissi | 2024 | IEEE ICWS 2024; arXiv:2407.00876 | CACHED | X.509-compatible multi-CA blockchain DPKI with node key registration/revocation, contrasted vs CA-based PKI. |
| sovchain26 | Sovchain: mutual authentication scheme for SSI management using blockchain for open banking | (authors unconfirmed) | 2026 | Financial Innovation (Springer, open access) | CACHED | SSI mutual-auth via Hyperledger smart contracts (open-banking-framed; mechanism transfers to fixed nodes). |
| ssiiiot22 | A Decentralized IIoT Identity Framework based on Self-Sovereign Identity using Blockchain | A. Dixit, M. Smith-Creasey, M. Rajarajan | 2022 | IEEE LCN 2022 | CACHED (OA author version) | On-chain DID/VC identity registry (Ethereum + Hyperledger Indy) for IIoT replacing centralized CAs. |
| sdida25 | SDIdA-IoT: self-sovereign digital identification and authentication framework for IoT devices using blockchain | (authors unconfirmed) | 2025 | Cluster Computing (Springer) | CACHED (UCL access) | Decentralized SSI for IoT devices to manage/prove on-chain identities. |
| pkicompare23 | A comparative study on blockchain-based distributed public key infrastructure for IoT applications | (authors unconfirmed) | 2023 | Multimedia Tools and Applications (Springer) | CACHED (UCL access) | Blockchain DPKI vs centralized CA-based PKI for IoT on trust, cert-signing cost, single-point-of-failure. |
| capvc22 | Capabilities-based access control for IoT devices using Verifiable Credentials | N. Fotiou, V. A. Siris, G. C. Polyzos, Y. Kortesniemi, D. Lagutin | 2022 | IEEE SPW/SafeThings 2022 | CACHED (UCL access) | Access rights as VCs with proof-of-possession + VC revocation for constrained devices. |
| ssiframe25 | A Blockchain-Based Self-Sovereign Identity Management Framework for Internet of Things | (authors unconfirmed) | 2025 | Springer chapter (IIWCS 2024) | DROPPED | Redundant with sdida25 + ssiiiot22; no open/UCL copy available. |

---

## Pillar B — Physical-consistency / spoofing-&-fault detection

| key | title | authors | year | venue | status | relevance |
|---|---|---|---|---|---|---|
| Amanullah2026CoopMD | Coop-IntelliMD: Toward Collaborative Detection of Data Integrity Attacks in Cooperative ITS | M. A. Amanullah, M. Baruwal Chhetri, S. W. Loke, R. Doss | 2026 | IEEE Access 14 | CACHED | Closest analogue to neighbour-report cross-checking: each node monitors closest neighbours in real-time to detect FDI/replay; escalates to collaborative check only when local checks fail (event-gating precedent). |
| Derhab2020FlowConserv | Two-Hop Monitoring Based on Relaxed Flow Conservation Constraints against Selective Routing Attacks in WSNs | A. Derhab, M. Bouras, M. Belaoued, L. Maglaras, F. A. Khan | 2020 | Sensors 20(21):6106 | CACHED | The single best precedent: relaxed flow-conservation-constraint intrusion detection with two-hop neighbour monitoring; the project's invariant is the traffic analogue. |
| Keijzer2021Intersection | Detection of Cyber-Attacks in Collaborative Intersection Control | T. Keijzer, … R. Ferrari | 2021 | arXiv:2104.03801 | CACHED | Sliding-mode-observer FDI detection for signage-less intersection control; reports detection latency vs crash time; "any control law can be chosen without affecting detection" (proposer/detector decoupling). |
| Ghosh2025Switching | Detecting Switching Attacks On Traffic Flow Regulation For Changing Driving Patterns | S. Ghosh, T. Roy | 2025 | arXiv:2505.23033 (preprint) | CACHED | Model-based detector bank for a multimodal macroscopic traffic model; conservation/fundamental-diagram template; sets threshold to a target false-alarm rate. |
| Xiao2026Residual | Limits of Residual-Based Detection for Physically Consistent False Data Injection | C. Xiao, Y. Weng | 2026 | arXiv:2602.10162 (preprint) | CACHED | KEY CAVEAT: physically-consistent (conservation-respecting) FDI provably evades residual/consistency checks — bounds what the conservation check can claim; motivates the auth layer as complement. |
| Abshari2025CPSReview | Cyber-Physical Systems Security: A Comprehensive Review of Anomaly Detection Techniques | D. Abshari, M. Sridhar | 2025 | arXiv:2502.13256 | CACHED | Survey taxonomising model/invariant-based vs learned anomaly detection; framing citation for choosing an invariant-based detector; unifies fault-vs-attack. |
| Huisman2025Hybrid | Hybrid Control as a Proxy for Detection and Mitigation of Sensor Attacks in Cooperative Driving | M. Huisman, C. Murguia, E. Lefeber, N. van de Wouw | 2025 | arXiv:2504.05958 | CACHED | Sensor redundancy / equivalent controller realizations whose outputs must agree absent attack — consistency-invariant detection, transferable to cross-validating reports. |
| Huisman2024Realizations | Optimal Controller Realizations against False Data Injections in Cooperative Driving | M. Huisman, C. Murguia, E. Lefeber, N. van de Wouw | 2024 | arXiv:2404.05361 | CACHED | Invariance of input-output behaviour under coordinate transform to harden cooperative control vs FDI. |
| Shahariar2025Trust | A Survey of Security Threats and Trust Management in Vehicular Ad Hoc Networks | R. Shahariar, C. Phillips | 2025 | Trans. on Engineering and Computing Sciences 13(3) | CACHED | Up-to-date survey of trust/reputation models for isolating malicious insiders / false messages. |
| IntelliMD2024 | IntelliMD: A Hybrid Approach for Local Misbehaviour Detection in Cooperative ITS | M. A. Amanullah, M. Baruwal Chhetri, S. W. Loke, R. Doss | 2024 | ACM CPSIoTSec'24 | CACHED (Deakin OA copy) | Rule-based plausibility/consistency checks + unsupervised ML for FDI/replay (supports the plausibility-check component). |
| Obata2023FDIState | Detection of False Data Injection Attacks in Distributed State Estimation of Power Networks | S. Obata, K. Kobayashi, Y. Yamashita | 2023 | IEICE Trans. Fundamentals E106-A(5) | CACHED | Residual-based FDI detection in distributed (ADMM) state estimation across networked agents; transferable methodology. |
| Liu2022Blockchain | On a Blockchain-Based Security Scheme for Defense against Malicious Nodes in VANETs | G. Liu, N. Fan, C. Q. Wu, X. Zou | 2022 | Sensors 22(14):5361 | CACHED | Identifies malicious nodes/forged messages via reputation + time/distance plausibility (space-time checks parallel the travel-time-window invariant). |
| Balaram2023Sybil | Highly accurate Sybil attack detection in VANET using extreme learning machine with preserved location | A. Balaram, S. A. Nabi, K. S. Rao, N. Koppula | 2023 | Wireless Networks (Springer) | CACHED (UCL access) | VANET Sybil detection using location-preserving features. |
| Azam2022Sybil | Collaborative Learning Based Sybil Attack Detection in VANETs | S. Azam, M. Bibi, R. Riaz, S. S. Rizvi, S. J. Kwon | 2022 | Sensors 22(18):6934 | CACHED | Supporting VANET Sybil-detection paper. |

---

## Staged registry block

The JSON array below uses the same shape as entries in `registry.json` (`tag`/short-tag, `title`, `year`, `url`, `category`, `relevance`). **These entries are NOT yet merged into `registry.json`** — they are staged here for the user to review and merge later. `category` follows the Pillar split: `"A-identity"` for Pillar A, `"B-detection"` for Pillar B. The dropped paper (`ssiframe25`) is excluded from the staged block. URLs are taken verbatim from `prompt9-identity-urls.txt` / `prompt9-detection-urls.txt`; where a URL field was not present in those files, a DOI/identifier note is given in the value instead of a fabricated URL (see Caveats).

```json
[
  {
    "tag": "proofmember23",
    "title": "Combining Decentralized IDentifiers with Proof of Membership to Enable Trust in IoT Networks",
    "year": 2023,
    "url": "https://arxiv.org/pdf/2310.08163",
    "category": "A-identity",
    "relevance": "Closest analogue to a single-domain permissioned membership registry; mutual auth via DID key-ownership + proof a DID belongs to an evolving trusted set; deliberately drops VCs for the same-administrative-domain case."
  },
  {
    "tag": "pkchain25",
    "title": "PKChain: Compromise-Tolerant and Verifiable Public Key Management System",
    "year": 2025,
    "url": "https://eprint.iacr.org/2023/1791.pdf",
    "doi": "10.1109/JIOT.2024.3478754",
    "category": "A-identity",
    "relevance": "On-chain public-key register/update/query/validate/revoke via threshold validation; on-chain status removes need for CRL/OCSP."
  },
  {
    "tag": "dcsm24",
    "title": "Decentralized Credential Status Management: A Paradigm Shift in Digital Trust",
    "year": 2024,
    "url": "https://arxiv.org/pdf/2406.11511",
    "category": "A-identity",
    "relevance": "Frames centralized-PKI to DPKI transition (DigiNotar/Symantec), blockchain credential-status/revocation; argues a root authority is still needed."
  },
  {
    "tag": "didlink24",
    "title": "DID Link: Authentication in TLS with Decentralized Identifiers and Verifiable Credentials",
    "year": 2024,
    "url": "https://arxiv.org/pdf/2405.07533",
    "category": "A-identity",
    "relevance": "Mutual auth in the TLS handshake using DID-bound self-signed X.509 + verifiable presentations; reports DID resolution 3-42x slower than CA X.509 (overhead caveat)."
  },
  {
    "tag": "didvcsurvey24",
    "title": "A Survey on Decentralized Identifiers and Verifiable Credentials",
    "year": 2024,
    "url": "https://arxiv.org/pdf/2402.02455",
    "category": "A-identity",
    "relevance": "DID/VC survey: verifiable data registries, revocation (Revocation List 2020), threats, edge/IoT applicability."
  },
  {
    "tag": "slvcdida25",
    "title": "SLVC-DIDA: Signature-less Verifiable Credential-based Issuer-hiding and Multi-party Authentication for Decentralized Identity",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2501.11052",
    "category": "A-identity",
    "relevance": "DID/VC multi-party auth with Merkle-tree VC list + accumulator revocation; motivated by issuer-hiding/privacy (cross-domain features the project does NOT need)."
  },
  {
    "tag": "aiagents25",
    "title": "AI Agents with Decentralized Identifiers and Verifiable Credentials",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2511.02841",
    "category": "A-identity",
    "relevance": "Ledger-anchored DID + self-hosted VC for zero-trust mutual auth between AI agents; its OWN prototype reports brittleness (4-36% completion) and an LLM silently skipping a security step - evidence AGAINST full DID/VC for a 3-month build."
  },
  {
    "tag": "endorse25",
    "title": "Endorsement-Driven Blockchain SSI Framework for Dynamic IoT Ecosystems",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2507.09859",
    "category": "A-identity",
    "relevance": "Layered blockchain SSI for IoT: issuer onboarding, endorsement-based trust, distributed credential revocation."
  },
  {
    "tag": "dpkidrone24",
    "title": "Decentralized PKI Framework for Data Integrity in Spatial Crowdsourcing Drone Services (D2XChain)",
    "year": 2024,
    "url": "https://arxiv.org/pdf/2407.00876",
    "category": "A-identity",
    "relevance": "X.509-compatible multi-CA blockchain DPKI with node key registration/revocation, contrasted vs CA-based PKI."
  },
  {
    "tag": "sovchain26",
    "title": "Sovchain: mutual authentication scheme for SSI management using blockchain for open banking",
    "year": 2026,
    "url": "https://link.springer.com/content/pdf/10.1186/s40854-026-00921-0.pdf",
    "doi": "10.1186/s40854-026-00921-0",
    "category": "A-identity",
    "relevance": "SSI mutual-auth via Hyperledger smart contracts (open-banking-framed; mechanism transfers to fixed nodes)."
  },
  {
    "tag": "ssiiiot22",
    "title": "A Decentralized IIoT Identity Framework based on Self-Sovereign Identity using Blockchain",
    "year": 2022,
    "url": "https://openaccess.city.ac.uk/id/eprint/29418/1/SSI_for_IIoT_4_Pages-2.pdf",
    "category": "A-identity",
    "relevance": "On-chain DID/VC identity registry (Ethereum + Hyperledger Indy) for IIoT replacing centralized CAs."
  },
  {
    "tag": "sdida25",
    "title": "SDIdA-IoT: self-sovereign digital identification and authentication framework for IoT devices using blockchain",
    "year": 2025,
    "url": "DOI 10.1007/s10586-025-05120-7 (no direct PDF URL in url-list; Cluster Computing, Springer; UCL access)",
    "category": "A-identity",
    "relevance": "Decentralized SSI for IoT devices to manage/prove on-chain identities."
  },
  {
    "tag": "pkicompare23",
    "title": "A comparative study on blockchain-based distributed public key infrastructure for IoT applications",
    "year": 2023,
    "url": "DOI 10.1007/s11042-023-16970-x (no direct PDF URL in url-list; Multimedia Tools and Applications, Springer; UCL access)",
    "category": "A-identity",
    "relevance": "Blockchain DPKI vs centralized CA-based PKI for IoT on trust, cert-signing cost, single-point-of-failure."
  },
  {
    "tag": "capvc22",
    "title": "Capabilities-based access control for IoT devices using Verifiable Credentials",
    "year": 2022,
    "url": "DOI 10.1109/SPW54247.2022.9833873 (no direct PDF URL in url-list; IEEE SPW/SafeThings 2022; UCL access)",
    "category": "A-identity",
    "relevance": "Access rights as VCs with proof-of-possession + VC revocation for constrained devices."
  },
  {
    "tag": "Amanullah2026CoopMD",
    "title": "Coop-IntelliMD: Toward Collaborative Detection of Data Integrity Attacks in Cooperative ITS",
    "year": 2026,
    "url": "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=11271755",
    "doi": "10.1109/ACCESS.2025.3638793",
    "category": "B-detection",
    "relevance": "Closest analogue to neighbour-report cross-checking: each node monitors closest neighbours in real-time to detect FDI/replay; escalates to collaborative check only when local checks fail (event-gating precedent)."
  },
  {
    "tag": "Derhab2020FlowConserv",
    "title": "Two-Hop Monitoring Based on Relaxed Flow Conservation Constraints against Selective Routing Attacks in WSNs",
    "year": 2020,
    "url": "https://www.mdpi.com/1424-8220/20/21/6106/pdf",
    "doi": "10.3390/s20216106",
    "category": "B-detection",
    "relevance": "The single best precedent: relaxed flow-conservation-constraint intrusion detection with two-hop neighbour monitoring; the project's invariant is the traffic analogue."
  },
  {
    "tag": "Keijzer2021Intersection",
    "title": "Detection of Cyber-Attacks in Collaborative Intersection Control",
    "year": 2021,
    "url": "https://arxiv.org/pdf/2104.03801",
    "category": "B-detection",
    "relevance": "Sliding-mode-observer FDI detection for signage-less intersection control; reports detection latency vs crash time; 'any control law can be chosen without affecting detection' (proposer/detector decoupling)."
  },
  {
    "tag": "Ghosh2025Switching",
    "title": "Detecting Switching Attacks On Traffic Flow Regulation For Changing Driving Patterns",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2505.23033",
    "category": "B-detection",
    "relevance": "Model-based detector bank for a multimodal macroscopic traffic model; conservation/fundamental-diagram template; sets threshold to a target false-alarm rate."
  },
  {
    "tag": "Xiao2026Residual",
    "title": "Limits of Residual-Based Detection for Physically Consistent False Data Injection",
    "year": 2026,
    "url": "https://arxiv.org/pdf/2602.10162",
    "category": "B-detection",
    "relevance": "KEY CAVEAT: physically-consistent (conservation-respecting) FDI provably evades residual/consistency checks - bounds what the conservation check can claim; motivates the auth layer as complement."
  },
  {
    "tag": "Abshari2025CPSReview",
    "title": "Cyber-Physical Systems Security: A Comprehensive Review of Anomaly Detection Techniques",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2502.13256",
    "category": "B-detection",
    "relevance": "Survey taxonomising model/invariant-based vs learned anomaly detection; framing citation for choosing an invariant-based detector; unifies fault-vs-attack."
  },
  {
    "tag": "Huisman2025Hybrid",
    "title": "Hybrid Control as a Proxy for Detection and Mitigation of Sensor Attacks in Cooperative Driving",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2504.05958",
    "category": "B-detection",
    "relevance": "Sensor redundancy / equivalent controller realizations whose outputs must agree absent attack - consistency-invariant detection, transferable to cross-validating reports."
  },
  {
    "tag": "Huisman2024Realizations",
    "title": "Optimal Controller Realizations against False Data Injections in Cooperative Driving",
    "year": 2024,
    "url": "https://arxiv.org/pdf/2404.05361",
    "category": "B-detection",
    "relevance": "Invariance of input-output behaviour under coordinate transform to harden cooperative control vs FDI."
  },
  {
    "tag": "Shahariar2025Trust",
    "title": "A Survey of Security Threats and Trust Management in Vehicular Ad Hoc Networks",
    "year": 2025,
    "url": "https://arxiv.org/pdf/2602.06608",
    "doi": "10.14738/tmlai.1303.18943",
    "category": "B-detection",
    "relevance": "Up-to-date survey of trust/reputation models for isolating malicious insiders / false messages."
  },
  {
    "tag": "IntelliMD2024",
    "title": "IntelliMD: A Hybrid Approach for Local Misbehaviour Detection in Cooperative ITS",
    "year": 2024,
    "url": "DOI 10.1145/3690134.3694817 (no direct PDF URL in url-list; ACM CPSIoTSec'24; Deakin OA copy)",
    "category": "B-detection",
    "relevance": "Rule-based plausibility/consistency checks + unsupervised ML for FDI/replay (supports the plausibility-check component)."
  },
  {
    "tag": "Obata2023FDIState",
    "title": "Detection of False Data Injection Attacks in Distributed State Estimation of Power Networks",
    "year": 2023,
    "url": "https://www.jstage.jst.go.jp/article/transfun/E106.A/5/E106.A_2022MAP0010/_pdf",
    "doi": "10.1587/transfun.2022MAP0010",
    "category": "B-detection",
    "relevance": "Residual-based FDI detection in distributed (ADMM) state estimation across networked agents; transferable methodology."
  },
  {
    "tag": "Liu2022Blockchain",
    "title": "On a Blockchain-Based Security Scheme for Defense against Malicious Nodes in VANETs",
    "year": 2022,
    "url": "https://www.mdpi.com/1424-8220/22/14/5361/pdf",
    "doi": "10.3390/s22145361",
    "category": "B-detection",
    "relevance": "Identifies malicious nodes/forged messages via reputation + time/distance plausibility (space-time checks parallel the travel-time-window invariant)."
  },
  {
    "tag": "Balaram2023Sybil",
    "title": "Highly accurate Sybil attack detection in VANET using extreme learning machine with preserved location",
    "year": 2023,
    "url": "DOI 10.1007/s11276-023-03399-1 (no direct PDF URL in url-list; Wireless Networks, Springer; UCL access)",
    "category": "B-detection",
    "relevance": "VANET Sybil detection using location-preserving features."
  },
  {
    "tag": "Azam2022Sybil",
    "title": "Collaborative Learning Based Sybil Attack Detection in VANETs",
    "year": 2022,
    "url": "https://www.mdpi.com/1424-8220/22/18/6934/pdf",
    "doi": "10.3390/s22186934",
    "category": "B-detection",
    "relevance": "Supporting VANET Sybil-detection paper."
  }
]
```

---

## Caveats

- **NOT yet merged.** The JSON above is staged only; nothing has been written to `registry.json`. Merge after review.
- **Dropped paper.** `ssiframe25` ("A Blockchain-Based Self-Sovereign Identity Management Framework for Internet of Things", Springer chapter / IIWCS 2024, DOI 10.1007/978-981-96-4741-5_26) was dropped as redundant with `sdida25` + `ssiiiot22` and has no open/UCL copy available. No PDF was fetched; it is excluded from the staged registry block.
- **Preprints (not yet peer-reviewed / version may change):** `Ghosh2025Switching` (arXiv:2505.23033), `Xiao2026Residual` (arXiv:2602.10162). Treat conclusions as provisional and re-check for published versions before final citation.
- **Preprint/published version mismatch — `Shahariar2025Trust`.** `prompt9-detection-urls.txt` records the cached PDF as `https://arxiv.org/pdf/2602.06608` (an arXiv preprint), while the gathered metadata gives the venue as *Trans. on Engineering and Computing Sciences* 13(3) with DOI 10.14738/tmlai.1303.18943. The cached PDF may be the preprint rather than the journal version of record — verify which version is in hand before citing page numbers.
- **Paywalled / institutional-access items (cached via UCL or OA author copy, no public PDF URL guaranteed):** `sdida25` (Cluster Computing), `pkicompare23` (Multimedia Tools and Applications), `capvc22` (IEEE SPW/SafeThings), `Balaram2023Sybil` (Wireless Networks), `IntelliMD2024` (ACM; Deakin OA copy). These have a DOI but no direct PDF URL in the url-lists, so the staged `url` field carries the DOI plus an access note rather than a fabricated link.
- **`pkchain25` two artifacts.** Both the IEEE version of record (`pkchain25.pdf`) and an IACR eprint mirror (`pkchain25_eprint.pdf`, listed in `prompt9-identity-urls.txt` as `https://eprint.iacr.org/2023/1791.pdf`) are cached. The staged entry points to the eprint PDF and carries the IEEE DOI (10.1109/JIOT.2024.3478754) for the version of record.
- **`Amanullah2026CoopMD` URL.** The url-list gives an IEEE `stamp.jsp` viewer link (session-dependent, may not resolve directly); the DOI 10.1109/ACCESS.2025.3638793 is the stable identifier.
- **Unconfirmed authors.** Author lists could not be confirmed for `endorse25`, `sovchain26`, `sdida25`, `pkicompare23`, `ssiframe25`. These are marked "(authors unconfirmed)" in the tables and the `authors` field is omitted from the staged JSON to avoid inventing names. Confirm before final citation.
- **`category` field.** The staged entries use `"A-identity"` / `"B-detection"`, which differ from the single-letter `category` codes (`"a"`, `"b"`, …) used by existing `registry.json` rows. Reconcile to the registry's category scheme during merge.
- **Cached-status confirmation.** All 14 Pillar-A papers and all 14 Pillar-B papers were confirmed present as `papers/<key>.pdf` by directory listing on 2026-05-31. Only `ssiframe25` (dropped) has no cached file.
