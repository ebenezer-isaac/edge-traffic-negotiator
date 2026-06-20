# Demo Runbook & Narration Script (for the supervisor video)

Two demos, both verified working headless on 2026-06-20. Record the **exploit-then-defend** demo as the headline; optionally open with the **2-node coordination** demo for context. You record and narrate; this file is the script.

All commands run from `03-implementation/edge-negotiator/` using the project venv:
`./.venv/Scripts/python.exe`. SUMO and `SUMO_HOME` are already configured on this machine.

---

## A. Headline demo — exploit-then-defend (record this)

**What it shows:** multiple junctions coordinate to clear a real ambulance through a 4-junction corridor, each sensing it locally and sharing corroborated advance claims so downstream junctions pre-position green. Then a compromised-but-approved junction sends a *signed* fake-emergency claim to grab green, and the system refuses it because preemption requires physical corroboration, not just a valid signature. The coordination works; the robustness layer makes it deployable.

### Run command (GUI, paced for video)

```
./.venv/Scripts/python.exe src/demo_emergency.py --delay 0.2 --attack-t 30 --ambulance-t 80 --steps 260
```

- `--delay 0.2` paces the sim so a viewer can follow (raise to 0.3 if you want slower).
- `--attack-t 30` fires the spoofed claim early, while no real ambulance is near.
- `--ambulance-t 80` injects the real ambulance after the attack is shown.
- The terminal prints one plain-English line per emergency event; keep the terminal visible beside the SUMO window.

### What to show on screen

1. The SUMO-GUI window with the four junctions J0–J1–J2–J3 along the arterial.
2. The **terminal** beside it (the narration lines print there in real time).
3. The red ambulance moving left→right along the arterial once it appears.

### Narration script (beats keyed to the terminal lines)

**Opening (before/at start):**
> "This is a four-junction corridor. Each junction runs a frozen Phi-4-mini agent on Foundry Local. Under normal conditions MaxPressure runs the show; when an emergency or incident is detected, the junctions coordinate to clear it together. The channel is signed so a compromised junction cannot poison that coordination. Watch the terminal — every emergency decision prints one line."

**At `>>> ATTACK: compromised J1 signs a PHANTOM emergency claim to J2`:**
> "Now a junction has been compromised. J1 still holds a valid key, so anything it signs passes authentication. It's sending J2 a signed message claiming an ambulance is approaching — but there is no ambulance. This is the spoofed-preemption attack: lie to grab green and starve the cross street."

**At the J2 `PREEMPTION WITHHELD` line:**
> "J2 checks the signature — valid, approved member. But it asks for *corroboration*: has any independent junction actually seen this ambulance, or do I see it myself? Nothing. So preemption is withheld. The signal stays on MaxPressure, the cross street is not starved. Signing alone did not stop the insider — the corroboration gate did."

**At `>>> REAL ambulance AMB-1 enters eastbound`:**
> "Now a *real* ambulance enters — the red vehicle. Watch it move down the arterial."

**At each `EMERGENCY sensed LOCALLY ... PREEMPT` line (J0, then J1, J2, J3):**
> "Each junction senses the ambulance on its own approach and preempts — clears it through. You can't spoof a physical vehicle into a junction's own sensor."

**At the `CORROBORATED by independent sighting -> PREEMPT` lines:**
> "And downstream junctions get a heads-up claim that's now *corroborated* by an upstream junction that genuinely saw the ambulance — so they pre-position the green. Real claim, corroborated, granted. Fake claim, uncorroborated, refused. Same gate, no need to guess intent."

**At the end summary:**
> "The summary: the junctions coordinated to clear the ambulance at every hop. The phantom attack was blocked without any special case, the same corroboration gate that enables legitimate advance preemption is what refuses the fake one. Coordination is the contribution; the robustness layer is what makes it safe to deploy."

### Quick verification before recording (headless, ~20 s)

```
./.venv/Scripts/python.exe src/demo_emergency.py --no-gui --delay 0 --steps 300
```
Expect: one `PHANTOM_attack_withheld` = 1, several `local_preemptions`, several `corroborated_claim_preemptions`.

---

## B. Optional opener — 2-node coordination demo (context)

**What it shows:** two junctions coordinating over the signed bus, with every decision's MaxPressure proposal, AI proposal, neighbour message, signature check, and conservation check visible live.

### Run command

```
./.venv/Scripts/python.exe src/demo_2node.py --delay 0.2
```

In SUMO-GUI: right-click junction **A0** or **A1** → **Show Parameter** to watch the live decision story update (MaxPressure proposed / AI proposed / executed / who decided / neighbour message / security check / conservation).

### Narration (30 seconds)

> "Before the attack, here's the normal coordination. Two junctions exchange signed messages about traffic they're releasing toward each other. Right-click a junction and 'Show Parameter' — you can see, every decision, what MaxPressure wanted, what the AI proposed, what executed, the verified neighbour message, and the conservation check reconciling claimed-versus-observed traffic. This is the substrate the attack in the next demo targets."

---

## C. Recording tips

- Use the real SLM if Foundry Local is up (`--agent slm` on the 2-node demo); otherwise the deterministic stub is fine and identical to narrate. The emergency demo uses the stub by design (the corroboration logic is independent of the agent).
- Keep the terminal font large; the per-event lines are the narration.
- If the GUI is awkward to capture, the headless run with the printed lines is itself a clean, recordable artifact.
- Total video target: ~3–4 minutes (30 s coordination opener + ~3 min exploit-then-defend).

---

## D. What is real vs simulated (state this in the video, for honesty)

- The corroboration gate, signing, registry, and conservation logic are the real, tested modules.
- The ambulance and the attack are injected live via TraCI for the demo; the corridor and traffic are SUMO.
- The agent shown is the deterministic stub; the corroboration result is identical with the real Phi-4-mini, because preemption admissibility is decided by the deterministic shield, not the SLM.
