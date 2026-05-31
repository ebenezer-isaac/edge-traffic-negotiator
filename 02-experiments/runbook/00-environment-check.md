# Runbook 00 — Environment Check

**Date:** 2026-04-16
**Machine:** Windows 10 Home Single Language 10.0.19045
**Goal:** Capture baseline environment state before installing oBeaver

---

## Tooling

| Tool | Version | Status |
|------|---------|--------|
| Python | 3.13.0 | ✓ Meets oBeaver's 3.12+ requirement |
| pip | 25.3 | ✓ |
| git | 2.48.1.windows.1 | ✓ |
| Foundry Local Model Server | **0.8.119** (winget id `Microsoft.FoundryLocal`) | ✓ **Already installed** |
| `foundry` CLI | 0.8.119 | ✓ Available on PATH |
| Hugging Face CLI (`hf`) | not installed | ✗ Required only for ORT-engine model downloads/conversion |
| Hugging Face login | not logged in | ✗ Required only for HF model downloads |

## Implications

1. **Foundry Local already in place.** oBeaver's Foundry Local engine path (the easy path on Windows) should work immediately for Phi-4-mini and any other Foundry catalog model.
2. **HF auth not yet configured.** Required for the ORT-engine path (Qwen3-4B, Traffic-R1 conversion). Will deal with this separately when we get to ORT.
3. **The strategic plan is unchanged from the synthesis:**
   - Phi-4-mini via Foundry Local engine (works today, no extra setup)
   - Qwen3-4B and Traffic-R1 via ORT engine (needs HF auth + conversion step)

## Decision

Proceed with oBeaver installation. Phi-4-mini smoke test via Foundry Local first (fastest path to "is oBeaver alive on this machine"), then HF setup, then Qwen3 conversion.
