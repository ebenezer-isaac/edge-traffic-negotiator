# Runbook 01 — oBeaver Installation

**Date:** 2026-04-16
**Goal:** Install oBeaver on the user's Windows 10 machine, configure model directory, verify environment.

---

## Steps Taken

### 1. Clone repo
```bash
cd e:/desktop/assignments/dissertation/02-experiments
git clone https://github.com/microsoft/obeaver.git
```
**Result:** ✓ Cloned to `e:/desktop/assignments/dissertation/02-experiments/obeaver`

### 2. Install via pip (editable mode)
```bash
cd obeaver
pip install -e .
```
**Result:** ✓ Successful. Installed `obeaver-0.1.0` plus dependencies (onnxruntime, onnxruntime-genai, foundry-local-sdk, transformers, fastapi, openai, etc.).

**Note:** The earlier external analysis flagged a broken `torch>=2.10.0` pin in `pyproject.toml`. **This was incorrect** — `pip install -e .` succeeded without the workaround. The `pyproject.toml` does not actually pin torch. If torch had been required, we would have followed the agent's `--no-deps -e .` workaround.

### 3. Initialise model directory
```bash
obeaver init e:/desktop/assignments/dissertation/02-experiments/models
```
**Result:** ✓ Configured. Model save location: `E:\desktop\assignments\dissertation\02-experiments\models`. Sub-folders `ort/`, `foundrylocal/`, `cache_dir/` created. Config saved to `~/.obeaver/config.json`.

**Pitfall:** Running `obeaver init` without a path argument enters an interactive prompt that hangs in non-TTY environments (caught us once). Always pass an explicit path.

### 4. Run environment check
```bash
obeaver check
```
**Result:** Mixed.
- ✓ Foundry Local CLI detected at `C:\Users\Ebenezer\AppData\Local\Microsoft\WindowsApps\foundry.EXE`, version 0.8.119
- ⚠ False negative: `foundry-local-sdk` reported as missing, but `pip show foundry-local-sdk` confirmed it was installed (v1.0.0 at the time)
- ⚠ Hugging Face not authenticated (expected — only required for ORT-engine model downloads)

### 5. Fix `foundry-local-sdk` version mismatch
**Problem identified during smoke test:** When trying `obeaver serve qwen2.5-0.5b`, got an `ImportError: foundry-local-sdk is required for the 'foundry' engine`. The SDK was installed but oBeaver expected `from foundry_local import FoundryLocalManager`, while `foundry-local-sdk==1.0.0` exposes the package as `foundry_local_sdk` (renamed).

**Diagnosis:**
```bash
pip show foundry-local-sdk  # version 1.0.0
python -c "import foundry_local"      # ModuleNotFoundError
python -c "import foundry_local_sdk"  # ModuleNotFoundError (also fails because of __init__ structure)
```

oBeaver's `pyproject.toml` says `"foundry-local-sdk>=0.5.0"` — the `>=` operator pulled in the breaking 1.0.0 release.

**Fix:**
```bash
pip install "foundry-local-sdk==0.5.1"
python -c "from foundry_local import FoundryLocalManager; print('OK')"  # OK
```

**Action item:** Pin `foundry-local-sdk==0.5.1` in any future setup script. Track upstream oBeaver for v0.2 which presumably will support the new SDK module name.

### 6. Verify Foundry catalog access
```bash
foundry model list
```
**Result:** ✓ Catalog accessible. Confirmed available models include phi-4-mini, phi-3.5-mini, qwen2.5-0.5b/1.5b/7b, gpt-oss-20b. **Crucially: no Qwen3 in catalog** — confirms that Qwen3-4B (the primary SLM) requires the ORT engine + HF conversion path.

---

## Final Environment State

| Item | Value |
|------|-------|
| Python | 3.13.0 (`C:\Users\Ebenezer\.virtualenvs\DFLEXLIBS-pomxas47\Scripts\python.exe`) |
| pip | 25.3 |
| oBeaver | 0.1.0 (editable install) |
| Foundry Local | 0.8.119 |
| `foundry-local-sdk` | **0.5.1** (pinned; do not let pip upgrade) |
| Model directory | `e:\desktop\assignments\dissertation\02-experiments\models` |
| HF auth | Not yet configured |

---

## Lessons Learned

1. **The torch pin issue from prior analysis was wrong.** `pip install -e .` works directly.
2. **`foundry-local-sdk>=0.5.0` allows pip to install 1.0.0 which breaks oBeaver.** Pin 0.5.1 explicitly.
3. **`obeaver init` interactive prompt hangs in scripts.** Pass an explicit path argument.
4. **`obeaver check`'s SDK detection has a false negative.** Trust `pip show` instead.
5. **No Qwen3 in Foundry catalog.** Plan two parallel paths: Foundry Local for Phi family, ORT engine for Qwen3-4B and Traffic-R1.
