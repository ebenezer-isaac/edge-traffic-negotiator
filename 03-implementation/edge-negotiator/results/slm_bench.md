# SLM benchmark — latency de-risk + model-agnostic ablation

**Project:** The Edge Negotiator (MSc dissertation)
**Date:** 2026-06-04
**Host:** Foundry Local service on `http://127.0.0.1:59534`, OpenAI-compatible
endpoint `…/v1`. GPU execution provider (Windows.AI.MachineLearning EP skipped —
host is Windows build 19045, below the 26100 minimum — so models run on the generic
GPU build, not the WinML EP).
**Harness:** `src/bench_slm.py` driving `src/slm_agent.py` `SLMAgent.choose_phase`
unchanged (terse `{"phase":N}` contract, `temperature=0`, `max_tokens=16`, returns
`None` on any failure → deterministic MaxPressure shield).
**Battery:** 54 fixed synthetic junction states (seed `20240604`): 14 hand-picked
(clear-winner, margin-of-1, and edge cases) + 40 seeded-random over 2/3/4-phase
junctions, queues in `[0,20]`, each re-rolled to a **unique argmax** so
"agreement with argmax-queue" is an unambiguous correctness signal. Each model gets
**60 timed calls** (battery cycled deterministically). The known-optimal phase is the
argmax of the per-phase halting queue — the same greedy target the MaxPressure shield
computes.

Raw per-call JSON: `results/_bench_*.json` (every call's latency, chosen phase,
optimal set, parse/agree flags).

---

## 1. Latency distribution — does the brief's "~2-8s per call" hold?

Per-call `choose_phase` wall-clock latency, n=60 each, GPU:

| Model (active id) | median (s) | p95 (s) | max (s) | mean (s) |
|---|---|---|---|---|
| **phi-4-mini** (`Phi-4-mini-instruct-generic-gpu:5`) | **0.482** | 0.553 | 1.541 | 0.502 |
| qwen2.5-1.5b (`qwen2.5-1.5b-instruct-generic-gpu:4`) | 0.127 | 0.151 | 2.379 | 0.167 |
| qwen2.5-0.5b (`qwen2.5-0.5b-instruct-generic-gpu:4`) | 0.097 | 0.129 | 1.440 | 0.123 |
| qwen2.5-coder-0.5b (`qwen2.5-coder-0.5b-instruct-generic-gpu:4`) | 0.096 | 0.154 | 1.690 | 0.129 |
| phi-4-mini-reasoning (`Phi-4-mini-reasoning-generic-gpu:3`) | 0.456 | 0.571 | 7.223 | 0.577 |

**Verdict on the "2-8s" assumption: REFUTED for Phi-4-mini.**
Phi-4-mini's real per-call latency is **median 0.48s, p95 0.55s, max 1.54s** — roughly
**an order of magnitude faster** than the brief's worst-case "2-8s" figure, and even the
single slowest call (1.54s, a cold-path outlier) stays under the bottom of that band.
Against the event-gated **~10s** decision interval this leaves **>18× headroom at the
median and >6× at the worst observed call** — comfortably within budget with room for
the neighbour-coordination prompt and shield fallback on the same tick.

Caveats kept honest:
- Calls here are **serial** (one junction, back-to-back), matching how Foundry Local
  serialises requests. The "2-8s" concern was about *serialisation across many
  junctions per tick*. With ~0.5s/call, a single Foundry Local instance can serve
  **~18-20 junction decisions inside a 10s window serially**; beyond that, fan-out
  needs parallel endpoints or staggered gating — but the per-call cost is not the
  bottleneck the brief feared.
- The only model that even *touches* the "2-8s" band is **phi-4-mini-reasoning**, whose
  max hit **7.2s** — and that is because it tries to emit chain-of-thought (see §3),
  not because the base inference is slow.
- All latencies include the full OpenAI client round-trip (HTTP + tokenise + decode of
  ≤16 tokens), i.e. the real production path, not raw GPU time.

---

## 2. Decision quality — model-agnostic ablation

Can a smaller/different SLM do the terse phase task as well as Phi-4-mini?
Parse-success = a valid `{"phase":N}` was returned (not `None`).
Argmax-agreement = the returned phase equals the known max-queue phase.

| Model | Load OK? | Median latency (s) | Parse-success % | Argmax-agreement % |
|---|---|---|---|---|
| **phi-4-mini** | ✅ (cached) | 0.482 | **100.0** | **100.0** |
| qwen2.5-1.5b | ✅ (downloaded ~1.5 GB) | 0.127 | 100.0 | 48.3 |
| qwen2.5-0.5b | ✅ (downloaded) | 0.097 | 100.0 | 43.3 |
| qwen2.5-coder-0.5b | ✅ (downloaded) | 0.096 | 100.0 | 35.0 |
| phi-4-mini-reasoning | ✅ (downloaded ~3.1 GB) | 0.456 | **1.7** | 1.7 |

Notes on what actually happened (no fabrication):
- The brief listed the Qwens as "cached", but `foundry cache list` at start showed
  **only phi-4-mini** cached. Each Qwen/reasoning model was pulled via
  `foundry model run <alias>` (download + load) before benchmarking — all loaded and
  served fine on GPU; none failed on VRAM or format.
- Foundry Local keeps **every loaded model registered simultaneously** on `/v1/models`;
  `SLMAgent` defaults to `data[0]`. To benchmark a specific model, the harness was
  pointed at it explicitly via `FOUNDRY_LOCAL_MODEL=<id>` (no edit to `slm_agent.py`).
- **qwen2.5-1.5b / 0.5b / coder-0.5b:** all hit **100% parse-success** — they happily
  emit valid `{"phase":N}` — but their **argmax agreement is 35-48%**, i.e. they obey
  the *format* contract while frequently failing the *task*. Inspecting wrong calls
  (e.g. `halting=[12,3]→chose 1`, `[15,1,2,4]→chose 3`, `[14,2,15,16]→chose 2`) shows a
  systematic bias toward the **last / middle index** rather than computing the true
  maximum. The coder-tuned 0.5b is the weakest (35%), consistent with its training
  skew away from short numeric-reasoning prompts.
- **phi-4-mini-reasoning:** technically loads and is fast per token, but under the
  production `max_tokens=16` cap it spends its budget on reasoning preamble and almost
  never emits the terse JSON → **1.7% parse-success** (≈59/60 calls return `None` and
  fall through to the shield). It is **unfit for the terse no-CoT contract** by design;
  raising `max_tokens` to let it finish reasoning would also push it into the multi-
  second latency band (its 7.2s max already hints at this). Correctly excluded.

---

## 3. Honest verdict

**(1) Does the latency assumption hold?**
**No — the "Foundry Local serialises calls ~2-8s each" assumption does not hold for the
production model.** Phi-4-mini answers the terse phase query in **~0.5s median (p95
0.55s, max 1.54s)** on this GPU host. The event-gated ~10s decision interval has
**ample headroom** (>18× at median). Per-call latency is *not* the risk; the only
latency risk is *fan-out* (many junctions per tick on one serialising endpoint), which
at ~0.5s/call still supports ~18-20 serial decisions per 10s window before needing
parallel endpoints.

**(2) Is the terse-phase task model-agnostic? — NO.**
The task is **format-agnostic but not capability-agnostic**. Every model trivially
produces valid `{"phase":N}` (100% parse on all four chat models), so the *parsing*
contract is robust across models. But the **decision quality is strongly
model-dependent**: only **Phi-4-mini reaches 100% argmax agreement**; the smaller Qwens
collapse to **35-48%** — near or below what indexing toward a fixed position would give
on this 2/3/4-phase mix. **A smaller/faster model is *not* a drop-in replacement here.**

**(3) Notable finding for the latency budget.**
The hoped-for "smaller model is as good and faster, so spend the saved latency
elsewhere" outcome **did not materialise**. The faster models (0.1-0.13s) are *cheap but
wrong*; the accurate model (Phi-4-mini) is already fast enough (~0.5s) that there is no
latency pressure to trade quality for speed. The right design choice is therefore
**keep Phi-4-mini** and treat the abundant latency headroom as budget for the
neighbour-coordination prompt and the deterministic shield — not as a reason to
downsize the model. The MaxPressure shield remains essential precisely because *any*
SLM (including Phi-4-mini on harder distributions) can disagree with argmax; the shield
is what makes the smaller models' 35-48% agreement *safe* rather than dangerous, since
their bad picks are vetoed.

---

## Reproduce

```
# phi-4-mini is the default-loaded model; others must be loaded first.
foundry model run phi-4-mini
.venv/Scripts/python src/bench_slm.py --calls 60 --tag phi-4-mini --out results/_bench_phi4mini.json

foundry model run qwen2.5-1.5b
FOUNDRY_LOCAL_MODEL=qwen2.5-1.5b-instruct-generic-gpu:4 \
  .venv/Scripts/python src/bench_slm.py --calls 60 --tag qwen2.5-1.5b --out results/_bench_qwen15.json
# …repeat for qwen2.5-0.5b, qwen2.5-coder-0.5b, phi-4-mini-reasoning (use each id)…

foundry model run phi-4-mini   # restore production model when done
```
