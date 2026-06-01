"""Generate the Edge Negotiator proposal + status deck (5 slides) as a .pptx."""
from pptx import Presentation
from pptx.util import Pt

prs = Presentation()
prs.slide_width = Pt(960)
prs.slide_height = Pt(540)


def bullets(title, items, sub_color=False):
    """items: list of (text, level) tuples."""
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    tf = slide.placeholders[1].text_frame
    tf.word_wrap = True
    for i, (text, level) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level
        for r in p.runs:
            r.font.size = Pt(20 if level == 0 else 17)
            if text.endswith(":"):
                r.font.bold = True
    return slide


# Slide 1 — Title
s = prs.slides.add_slide(prs.slide_layouts[0])
s.shapes.title.text = "The Edge Negotiator"
sub = s.placeholders[1].text_frame
sub.text = "Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control"
for line in [
    "UCL MSc Systems Engineering for IoT  —  Project Proposal & Status",
    "Student 25153651  ·  Supervisors: Dr Akin Delibasi (UCL), Lee Stott (Microsoft)",
    "Small language-model agents that coordinate traffic lights, verify who they talk to,",
    "and catch faulty/spoofed data — evaluated in SUMO on a real London corridor.",
]:
    p = sub.add_paragraph()
    p.text = line
    for r in p.runs:
        r.font.size = Pt(16)

# Slide 2 — Proposal
bullets("What we're building & why", [
    ("Problem: traffic signals decide blind to neighbours; multi-agent coordination needs trustworthy data.", 0),
    ("Per-junction SLM agents (Phi-4-mini via Microsoft Foundry Local) coordinate signal timing in Eclipse SUMO.", 0),
    ("Deterministic MaxPressure shield validates / overrides every SLM decision — safety first.", 0),
    ("Cryptographic agent identity (Ed25519 + on-chain permissioned registry) — verify the source.", 0),
    ("Vehicle-conservation check flags spoofed / faulty neighbour reports; tamper-evident audit log.", 0),
    ("Novelty (integrative): authenticated identity + conservation check beneath SLM cross-junction coordination — no published precedent.", 0),
])

# Slide 3 — Status
bullets("Current status — built & validated", [
    ("Scope pivoted & locked (supervisor-approved); single source-of-truth decision brief.", 0),
    ("Literature base: 175 papers (incl. 28 new on agent identity & spoof / fault detection).", 0),
    ("DONE: SUMO 2x2 grid + MaxPressure baseline — beats fixed-time (waiting 52 s vs 66 s).", 0),
    ("DONE: SLM-in-the-loop — Phi-4-mini drives a junction live: 90 decisions, 0 failures, shield + event-gating working.", 0),
    ("Reproducible public repo — code, scenario, docs, all committed.", 0),
])

# Slide 4 — Next steps + confidence
bullets("Next steps  ·  what we're confident about", [
    ("Next steps:", 0),
    ("Cross-junction coordination — share predicted neighbour state (the novel core).", 1),
    ("Identity + audit layer — Ed25519 signatures + Hyperledger Besu allowlist / revoke.", 1),
    ("Spoof / fault detection + adversarial scenarios; then real Lambeth corridor + evaluation sweep.", 1),
    ("Confident about:", 0),
    ("End-to-end pipeline runs — SUMO + TraCI + SLM + shield all validated.", 1),
    ("Phi-4-mini serves on a consumer laptop; MaxPressure shield is provably stable.", 1),
    ("Identity mechanism is literature-backed and buildable within the timeline.", 1),
])

# Slide 5 — Challenges & mitigations
bullets("Challenges & how we tackle them", [
    ("SLM latency (Foundry serial, ~2-8 s/decision)  ->  terse output, pause-sim, event-gating, keep to ~6-8 SLM junctions.", 0),
    ("Consistency check is not truth (a consistent liar evades it)  ->  scope to uncoordinated spoofs / faults; identity layer complements; cite the limit (Xiao 2026).", 0),
    ("Blockchain too slow for the control loop  ->  async audit / registry only, never in the hot path.", 0),
    ("Real-corridor demand data is coarse  ->  DfT traffic counts + SUMO routeSampler calibration.", 0),
    ("SLM decision quality  ->  deterministic shield underneath; explicit-prompt engineering (already validated).", 0),
])

out = __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0] + "/Edge-Negotiator-Proposal-Status.pptx"
prs.save(out)
print("saved:", out)
