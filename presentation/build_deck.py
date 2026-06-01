"""Generate the Edge Negotiator project-pitch deck as a .pptx.

Built for a 3-minute pitch (~30s/slide) and the marking rubric:
Problem (25), Literature (35), Methodology + Evaluation (20), Presentation (20).
Glanceable one-line bullets, natural language, no em dashes.
"""
from pptx import Presentation
from pptx.util import Pt, Inches

prs = Presentation()
# Standard PowerPoint 16:9 widescreen
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def bullets(title, items):
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    t = slide.shapes.title
    t.text = title
    t.left, t.top, t.width, t.height = Inches(0.6), Inches(0.4), Inches(12.1), Inches(1.1)
    body = slide.placeholders[1]
    body.left, body.top, body.width, body.height = Inches(0.6), Inches(1.7), Inches(12.1), Inches(5.3)
    tf = body.text_frame
    tf.word_wrap = True
    for i, text in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        for r in p.runs:
            r.font.size = Pt(20)
    return slide


# Slide 1 - Title (clean)
s = prs.slides.add_slide(prs.slide_layouts[0])
st = s.shapes.title
st.text = "The Edge Negotiator"
st.left, st.top, st.width, st.height = Inches(0.8), Inches(2.1), Inches(11.7), Inches(1.3)
subph = s.placeholders[1]
subph.left, subph.top, subph.width, subph.height = Inches(0.8), Inches(3.5), Inches(11.7), Inches(3.4)
sub = subph.text_frame
sub.text = "Verified-Source Cross-Junction Coordination for SLM-Driven Traffic Signal Control"
for line in [
    "UCL MSc Systems Engineering for IoT. Project pitch.",
    "Student 25153651, Ebenezer Veeraraju. Supervisors: Dr Akin Delibasi (UCL) and Lee Stott (Microsoft).",
]:
    p = sub.add_paragraph()
    p.text = line
    for r in p.runs:
        r.font.size = Pt(15)

# Slide 2 - Problem (Rubric I)
bullets("The problem", [
    "Traffic signals act blind to their neighbours, leaving coordination gains unused.",
    "When junctions share data to coordinate, nothing confirms that data is genuine or correct.",
    "Signals are safety-critical infrastructure: AI control is deployable only if inputs are trusted and auditable.",
    "Originality: securing language-model coordination with verifiable identity and a physics-based check has no published precedent.",
])

# Slide 3 - Literature (Rubric II, 35 pts)
bullets("Background and the gap", [
    "Mature but separate strands: language-model traffic control, MaxPressure control, cooperative-ITS spoof and fault detection, decentralized identity and blockchain PKI, and chain-of-thought faithfulness.",
    "Evidence base: 175 peer-reviewed sources, with 28 added for agent identity and spoof or fault detection.",
    "The gap: nobody places authenticated identity and a vehicle-conservation check beneath language-model cross-junction coordination.",
    "Research question: can authenticated, plausibility-checked agents coordinate a corridor while detecting spoofed or faulty inputs?",
    "Honest limit: a consistency-respecting attacker can evade conservation checks (Xiao, 2026), so identity is a separate layer.",
])

# Slide 4 - Methodology (Rubric III, method)
bullets("Methodology", [
    "Per-junction Phi-4-mini agents (Microsoft Foundry Local) coordinate signals in SUMO on a real Lambeth corridor.",
    "A MaxPressure shield validates or overrides every decision: the model proposes, the shield disposes.",
    "Signed messages plus a permissioned Hyperledger Besu registry verify the sender and revoke compromised junctions.",
    "A vehicle-conservation check flags physically impossible reports; every decision is logged tamper-evidently.",
    "The model outputs only a phase number, not reasoning, because chain-of-thought is an unfaithful explanation.",
])

# Slide 5 - Evaluation + progress (Rubric III, evaluation)
bullets("Evaluation and progress so far", [
    "Baselines: fixed-time, MaxPressure, and uncoordinated versus coordinated agents.",
    "Metrics: travel time, queue and throughput; detection precision, recall and latency; trust-layer overhead.",
    "Rigour: pre-registered seeds, bootstrap confidence intervals, multiple-comparison correction.",
    "Already working: MaxPressure beats fixed-time, and a live language-model junction ran 90 decisions with zero failures.",
    "All code, scenario and documentation sit in a reproducible public repository.",
])

# Slide 6 - Roadmap, confidence, risks
bullets("Roadmap, confidence, and risks", [
    "Next: cross-junction coordination, then identity and audit, then adversarial evaluation on the real corridor.",
    "Confident: pipeline runs end to end; Phi-4-mini runs on a laptop; the shield is provably stable; identity is literature-backed.",
    "Latency risk: terse output, pause while thinking, skip quiet junctions, cap model-controlled junctions.",
    "Trust risk: scope claims to clumsy or faulty data; the identity layer covers deliberate attacks.",
    "Data risk: calibrate demand from Department for Transport counts using SUMO routeSampler.",
])

out = __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0] + "/25153651_EbenezerVeeraraju_ADelibasi_COMP0234_SysIoT_Pitch_2324.pptx"
prs.save(out)
print("saved:", out, "| slides:", len(prs.slides._sldIdLst))
