# The Edge Negotiator — Live 2-Junction Demo Guide

A run-it-in-the-meeting guide for showing two traffic-light junctions (**A0** and
**A1**) coordinating with each other, with every decision visible live. Written
so a non-expert can drive it. No prior SUMO knowledge needed.

---

## 1. The one-line command to launch the demo

Open a terminal **in the project folder** and run:

```
cd 03-implementation/edge-negotiator
.venv/Scripts/python src/demo_2node.py
```

That is it. A SUMO map window opens, cars start driving, and the terminal prints
a plain-English line every time A0 or A1 makes a decision.

- This is the **safe demo**: it uses a built-in deterministic agent (`stub`).
  No external AI service is needed; it always works.
- To run the **real-AI variant** (local Phi-4-mini), see Section 6.

> If the window opens but cars do not move, press the green **Play** (▶) button
> in the SUMO toolbar. (We pass `--start` so it usually auto-plays.)

---

## 2. What you are looking at on screen

- A small **2×2 grid** of four traffic-light junctions: **A0, A1, B0, B1**.
- **A0 and A1 are the coordinating pair.** They are next-door neighbours
  (a road runs directly between them). They send each other **signed messages**
  announcing how many cars they are about to release toward the other, and they
  use that to coordinate which green light to show next.
- **B0 and B1 are ordinary junctions.** They run the classic MaxPressure
  algorithm on their own and do not coordinate. They are there for contrast.
- Cars queue at red lights and flow on green, exactly like real traffic.

Each green-light decision at A0 / A1 is the result of three things working
together:

1. **MaxPressure** (the safe fallback) computes which phase has the longest queue.
2. **The AI agent** proposes a phase.
3. A **safety + security check** decides what is actually executed, using the
   verified message from the neighbour.

---

## 3. The click steps: open a junction's live decision panel

This is the centrepiece. In the SUMO window:

1. **Right-click directly on the A0 junction** (the traffic light in the grid).
2. In the pop-up menu, choose **"Show Parameter"** (you may see it as
   *Show Junction Parameter* / *Parameters*).
3. A small panel opens listing **numbered fields, 1 through 8**.
4. These fields **update live** as the simulation runs — watch them change each
   time A0 makes a decision.
5. Repeat the right-click on **A1** to open its panel too. You can have both
   open side by side and watch the two junctions react to each other.

> Tip: the fields are numbered (`1_…`, `2_…`, …) so they always appear in
> reading order. SUMO sorts them alphabetically, and the numbers keep the story
> in sequence.

---

## 4. What each field / log word means (plain words)

The **GUI panel fields** (right-click → Show Parameter):

| Field | Plain meaning |
| --- | --- |
| `1_maxpressure_proposed` | What the safe classic algorithm wanted (longest queue). |
| `2_AI_agent_proposed`    | What the AI agent suggested this round. |
| `3_EXECUTED`             | The phase the light **actually showed**. |
| `4_who_decided`          | Who won: **AI** (its suggestion was used) or **shield (MaxPressure)** (the safe fallback decided). |
| `5_incoming_from_neighbour` | How many cars the neighbour announced are heading this way. |
| `6_neighbour_msg`        | The actual signed message received (who from, how many cars, message tick). |
| `7_security_check`       | Did the neighbour's message pass authentication? `VERIFIED OK` = genuine signed message accepted. Any blocked attack message is called out. |
| `8_conservation`         | The physics check: do the **claimed** released cars match the **observed** arriving cars? `OK` = consistent; `FLAGGED` = a mismatch worth noting. |

The **terminal live log** prints the same story as one line per decision, e.g.:

```
[t=120s | Junction A0] MaxPressure wanted: phase 0  |  AI proposed: phase 1  |  EXECUTED: phase 1 (AI)  |  heard from A1: ~5 cars heading my way  |  message: VERIFIED OK (1)  |  conservation: OK
```

Read it left to right: the time, which junction, what each part proposed, what
ran, what the neighbour said, and the two safety checks.

**Security lines** are called out separately and indented, so they stand out:

- `[SECURITY] REJECTED attack message …` — a forged / unauthorised message was
  blocked. (You will not see these in the normal demo; they appear in attack
  scenarios.)
- `[SECURITY] CONSERVATION FLAG …` — the cars one junction *claims* it sent do
  not match what the other *observed*. In this benign demo this is normal lag
  (cars are still in transit, or the simple placeholder count over/under-reads).
  The point is the check is **live and watching**, not that an attack is
  happening.

---

## 5. What to say while it runs (3 sentences)

> "These two junctions, A0 and A1, are coordinating: each sends the other a
> cryptographically **signed** message saying how many cars it is about to send
> their way, and you can watch those messages arrive in the panel."
>
> "For every green light I can show you exactly what the classic algorithm
> wanted, what the AI proposed, and what actually ran — so the AI never operates
> without a safety net."
>
> "Every message is **authenticated** before it is trusted, and a physics
> **conservation check** continuously compares what's claimed against what's
> actually observed, so a junction can't quietly lie about the traffic it's
> sending."

---

## 6. The real-AI variant (local Phi-4-mini)

Same demo, but the AI proposals come from a real small language model
(Phi-4-mini) served locally by Microsoft Foundry Local instead of the built-in
stub.

**Before the meeting**, start Foundry and load the model:

```
foundry service start
foundry model run phi-4-mini
```

Then launch the demo with the `slm` agent:

```
.venv/Scripts/python src/demo_2node.py --agent slm
```

Everything on screen and in the log is identical; only the source of the
`2_AI_agent_proposed` field changes.

**If Foundry is not running**, the demo **does not crash cryptically** — it
stops immediately with a clear message:

```
ERROR: cannot reach Foundry Local (the local Phi-4-mini service).
       Start it with `foundry service start` and load phi-4-mini,
       or run the safe demo with --agent stub.
```

If anything goes wrong with the model mid-meeting, just fall back to the safe
stub demo (Section 1) — it is fully deterministic and needs nothing external.

---

## 7. Useful flags (optional)

| Flag | Effect |
| --- | --- |
| *(none)* | GUI on, stub agent, 0.2s pause per step — the default demo. |
| `--no-gui` | Run headless (no window). Used for testing / CI. |
| `--agent slm` | Use the real Phi-4-mini via Foundry Local. |
| `--agent stub` | Use the built-in deterministic agent (default, always works). |
| `--delay 0.4` | Slow it down so the room can follow (bigger = slower). |
| `--delay 0` | No pause — fastest run (for headless testing). |
| `--steps 600` | Run a shorter/longer simulation (default 1000). |
| `--quiet` | Hide the per-decision terminal log (panel still updates). |

Example, a slower, easy-to-narrate GUI run:

```
.venv/Scripts/python src/demo_2node.py --delay 0.4
```

---

## 8. Quick sanity check before the meeting

Run this once to confirm everything works without opening a window
(takes a few seconds):

```
.venv/Scripts/python src/demo_2node.py --no-gui --delay 0 --steps 300
```

You should see a stream of `[t=… | Junction A0/A1]` lines and a final
`=== demo finished ===` summary reporting the number of decisions, verified
messages, and conservation checks. If you see that, the live GUI demo will work.
