"""Narrated demo video: neural-voice narration paced to the rendered segments.

Builds on demo_render (same segments, same capture). For each segment a narration
clip is synthesised, its duration measured, and the segment rendered to exactly
that many frames; the clips are then concatenated and muxed with the video.

Usage:
    python src/demo_narrate.py --capture results/demo_capture__<tag>.json.gz --out demo.mp4
"""
from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import math
import os
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import demo_render as R  # noqa: E402

VOICE = "en-GB-RyanNeural"
RATE = "+4%"
PAD_S = 0.6  # silence after each clip

NARRATION = [
    ("title",
     "This is The Edge Negotiator, a dissertation by a student on the Master of Science in Systems Engineering "
     "for the Internet of Things at University College London. It asks one question. Can a small artificial "
     "intelligence model run London traffic lights from a cheap roadside computer, do it safely, and keep a "
     "record of every decision that would hold up after a crash? Everything in this video was computed in the "
     "run you are about to see."),
    ("sim",
     "This is a real run. Nine sets of traffic lights in Bloomsbury, six hundred and eighty-six vehicles, twenty "
     "minutes of simulated time. The controller is a small language model with six hundred million parameters, "
     "taught by a much larger model and shrunk to run locally on Microsoft's Foundry Local. Every ten seconds, "
     "each junction asks the model which direction gets the next green. The answer never goes straight to the "
     "lights. A safety layer checks it first. An unsafe answer is replaced. A queue that has waited too long is "
     "served instead. Teal rings mean the model's own choice was used; amber means the safety layer stepped in. "
     "On the right, every decision is signed with the junction's digital key and linked to the one before it, "
     "like pages in a ledger. Each decision takes about a second and a half, against a budget of ten."),
    ("summary",
     "In this run, five hundred and ninety-eight of the six hundred and eighty-six vehicles finished. None got "
     "stuck. The model made seventy-seven percent of the decisions itself, and disagreed with the classical "
     "controller on only four percent. One run is a demonstration, not proof. The dissertation's results come "
     "from thirty runs per comparison."),
    ("audit",
     "Now the record. The ledger from that run has four hundred and thirty-five entries, and every link and "
     "signature checks out. Change one served phase, and the chain breaks exactly there. Sign an entry with the "
     "wrong key, and the chain holds but the signature fails. Nothing can be altered, or blamed on the wrong "
     "junction, without being caught."),
    ("crash",
     "The same records reconstruct accidents. Seven crash scenarios were tested, from a car running a red light "
     "to a fake ambulance signal. In every case the record verifies, a forgery is caught, and the applicable UK "
     "road rule is drawn from the verified facts."),
    ("pack",
     "The output is an evidence pack for a human to judge. It is never a verdict. For the ambulance case, it "
     "cites three rules: the emergency exemption, the usual sixty-forty split from case law, and the duty of "
     "care on a green light. Each rule carries a weight taken from the law, not from the model."),
    ("results",
     "What did the study find? Across thirty runs, training changes who is in charge more than how fast traffic "
     "moves: the trained model makes most of the decisions on every map. Where roads can flow, it cuts delay by "
     "eighteen point three percent against its untrained twin, thirty runs out of thirty, and a model six times "
     "larger does no better. Where roads are jammed, on the Euston corridor, the gain disappears, and the report "
     "says so. A modest claim, and a record you can trust."),
]


async def _tts(text, path):
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)


OR_MODEL = "openai/gpt-audio"
OR_VOICE = os.environ.get("NARRATION_VOICE", "ash")
OR_STYLE = ("You are a voice-over artist recording the narration for a short academic documentary about an "
            "engineering dissertation. Read the user's text aloud exactly as written, word for word, in a calm, "
            "measured, confident British documentary tone at a natural brisk pace. Do not add, remove, summarise "
            "or comment on anything. Output only the spoken reading.")


def tts_openrouter(text, wav_path):
    """gpt-audio via OpenRouter (streamed pcm16 at 24 kHz) -> wav. Returns the transcript."""
    import base64
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    stream = client.chat.completions.create(
        model=OR_MODEL, stream=True, modalities=["text", "audio"],
        audio={"voice": OR_VOICE, "format": "pcm16"},
        messages=[{"role": "system", "content": OR_STYLE}, {"role": "user", "content": text}])
    chunks, transcript = [], []
    for ev in stream:
        d = ev.choices[0].delta if ev.choices else None
        if d is None:
            continue
        a = getattr(d, "audio", None)
        if a is None and getattr(d, "model_extra", None):
            a = d.model_extra.get("audio")
        if not a:
            continue
        data = a.get("data") if isinstance(a, dict) else getattr(a, "data", None)
        tr = a.get("transcript") if isinstance(a, dict) else getattr(a, "transcript", None)
        if data:
            chunks.append(base64.b64decode(data))
        if tr:
            transcript.append(tr)
    pcm = b"".join(chunks)
    if len(pcm) < 24000:  # under half a second: treat as failure
        raise RuntimeError(f"gpt-audio returned {len(pcm)} bytes")
    raw = wav_path + ".pcm"
    open(raw, "wb").write(pcm)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", raw,
                    "-ar", "44100", wav_path], check=True)
    os.remove(raw)
    return "".join(transcript)


def synth(text, key, audio_dir, backend):
    """Return path to a clip (mp3 or wav) for ``text`` using the chosen backend, with fallback."""
    if backend == "openrouter" and os.environ.get("OPENROUTER_API_KEY"):
        wav = os.path.join(audio_dir, f"{key}.or.wav")
        for attempt in range(5):
            try:
                tr = tts_openrouter(text, wav)
                words_in, words_out = len(text.split()), len(tr.split())
                if abs(words_in - words_out) > max(3, 0.08 * words_in):
                    print(f"  {key}: transcript length {words_out} vs script {words_in}, retrying", flush=True)
                    continue
                return wav
            except Exception as exc:  # noqa: BLE001
                print(f"  {key}: openrouter attempt {attempt + 1} failed: {exc}", flush=True)
        print(f"  {key}: falling back to edge-tts", flush=True)
    mp3 = os.path.join(audio_dir, f"{key}.mp3")
    asyncio.run(_tts(text, mp3))
    return mp3


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True)
    ap.add_argument("--crash", default=os.path.join(_HERE, "..", "results", "experiment_crash_law.json"))
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "..", "..", "WKSR2_COMP0234_SEIoT_Demo_Narrated.mp4"))
    ap.add_argument("--work", default=os.path.join(_HERE, "..", "results", "_demo_narrated"))
    ap.add_argument("--backend", choices=["edge", "openrouter"], default="edge")
    args = ap.parse_args()

    audio_dir = os.path.join(args.work, "audio"); os.makedirs(audio_dir, exist_ok=True)
    frames_dir = os.path.join(args.work, "frames")
    if os.path.isdir(frames_dir): shutil.rmtree(frames_dir)

    # 1. narration clips + durations -> frame budgets
    clips = {}
    import hashlib
    for key, text in NARRATION:
        h = hashlib.sha1((args.backend + OR_VOICE + text).encode()).hexdigest()[:10]
        cached = [f for f in os.listdir(audio_dir) if f.startswith(f"{key}.{h}.") and not f.endswith(".pcm")]
        if cached:
            mp3 = os.path.join(audio_dir, cached[0]); print(f"  {key}: cached clip", flush=True)
        else:
            mp3 = synth(text, f"{key}.{h}", audio_dir, args.backend)
        wav = os.path.join(audio_dir, f"{key}.wav")
        d = duration(mp3) + PAD_S
        n = int(math.ceil(d * R.FPS)); d_exact = n / R.FPS
        # pad with silence to the exact frame-aligned length
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-af", f"apad=whole_dur={d_exact}",
                        "-t", f"{d_exact}", "-ar", "44100", "-ac", "1", wav], check=True)
        clips[key] = (wav, n)
        print(f"{key:<8} {d_exact:6.2f}s  {n:4d} frames", flush=True)
    total_s = sum(n for _, n in clips.values()) / R.FPS
    print(f"total narration {total_s:.1f}s", flush=True)

    # 2. render segments to those budgets
    with gzip.open(args.capture, "rt", encoding="utf-8") as fh:
        cap = json.load(fh)
    fr = R.Frames(frames_dir)
    m = cap["metrics"]; ds = cap["decision_stats"]; au = cap["audit"]
    dec_total = ds.get("decisions") or len(cap["decisions"])
    sb = ds.get("served_by", {}) if isinstance(ds.get("served_by"), dict) else {}
    auth_share = (sb.get("slm", 0) / dec_total) if dec_total else 0.0
    acc = (ds.get("slm_proposal_served", 0) / ds["slm_valid_proposals"]) if ds.get("slm_valid_proposals") else 0.0
    div = (ds.get("slm_diverged_and_served", 0) / ds["slm_proposal_served"]) if ds.get("slm_proposal_served") else 0.0

    R.text_card(fr, [
        ("The Edge Negotiator", 34, R.INK, "bold", R.SANS, 0.62),
        ("On-device small-language-model traffic control with a provable accident audit", 16, R.MUTED, "normal", R.SANS, 0.53),
        ("One live closed-loop run, then the audit layer that records it", 13, R.INK, "normal", R.SANS, 0.42),
        ("MSc Systems Engineering for the Internet of Things · University College London", 13, R.INK, "normal", R.SANS, 0.35),
        ("Candidate WKSR2 · COMP0234 · 2026", 12, R.MUTED, "normal", R.MONO, 0.29),
    ], hold_s=0, n_frames=clips["title"][1],
       footer="SUMO · Microsoft Foundry Local · NVIDIA RTX 2060 6 GB · everything shown is computed live in this run")

    n_sim = clips["sim"][1]
    plan_frac = [
        (0.00, "Nine junctions, 686 vehicles, 1,200 simulated seconds. A 0.6-billion-parameter model, taught by a larger one and shrunk to run locally."),
        (0.30, "Every 10 s the model proposes the next green. A safety layer (the MaxPressure shield) checks it before the lights change."),
        (0.52, "Teal ring: the model's own choice was served. Amber ring: the safety layer served a queue that had waited too long."),
        (0.72, "Each decision is signed with the junction's key and chained to the previous one. The head hash changes with every record."),
        (0.88, "About 1.5 s per decision on the 6 GB card, against a 10 s budget."),
    ]
    steps_total = cap["frames"][-1]["step"]
    plan = [(int(fr_ * steps_total), txt) for fr_, txt in plan_frac]
    R.sim_segment(fr, cap, caption_plan=plan, n_frames=n_sim)

    R.text_card(fr, [
        ("This run, seed %d" % cap["seed"], 22, R.INK, "bold", R.SANS, 0.72),
        (f"loaded {m['loaded']}   completed {m['completed']} ({100 * m['completed'] / max(1, m['loaded']):.1f}%)   teleports {m['teleports']}   undeparted {m['undeparted']}", 14, R.INK, "normal", R.MONO, 0.60),
        (f"mean network delay {m['mean_network_delay_s']:.1f} s", 14, R.INK, "normal", R.MONO, 0.54),
        (f"decisions {dec_total}   SLM-authored {sb.get('slm', 0)} ({auth_share:.2f})   shield {sb.get('shield', 0)}   anti-starvation {sb.get('anti_starvation', 0)}   acceptance {acc:.2f}   divergence {div:.2f}", 12.5, R.MUTED, "normal", R.MONO, 0.46),
        (f"audit: {au['entries']} entries, verify_chain={au['verify_chain']}, verify_signatures={au['verify_signatures']}, inclusion proof {au['inclusion_proof_valid']}", 13, R.TEAL, "normal", R.MONO, 0.40),
        ("One seed is a demonstration, not a result. The report's numbers are thirty paired seeds per cell.", 12.5, R.AMBER, "normal", R.SANS, 0.28),
    ], hold_s=0, n_frames=clips["summary"][1])

    jsonl = args.capture.replace(".json.gz", ".audit.jsonl"); pk = args.capture.replace(".json.gz", ".pubkeys.json")
    R.audit_segment(fr, cap, jsonl, pk, n_frames=clips["audit"][1])
    R.crash_segment(fr, args.crash, n_table=clips["crash"][1], n_pack=clips["pack"][1])

    R.text_card(fr, [
        ("What the study found (n = 30 seeds per cell)", 22, R.INK, "bold", R.SANS, 0.80),
        ("Fine-tuning moves authorship, not delay: SLM-authored share 0.39–0.62 → 0.56–0.77 on every map", 13.5, R.INK, "normal", R.SANS, 0.68),
        ("Where the network can clear, the distilled 0.6B student cuts delay 18.3% against its stock twin, 30 of 30 seeds", 13.5, R.TEAL, "normal", R.SANS, 0.61),
        ("The 3.8B student lands within ±0.38% of the 0.6B: scale saturates at 0.6B", 13.5, R.INK, "normal", R.SANS, 0.54),
        ("Seven crash scenarios reconstructed end-to-end with forgeries caught; the output is a cited evidence pack", 13.5, R.INK, "normal", R.SANS, 0.47),
        ("Limits stated in the report: single-network headline, Euston did not reproduce it, no unmasked arm, trust battery at three seeds", 12.5, R.AMBER, "normal", R.SANS, 0.36),
        ("Candidate WKSR2 · COMP0234 · 2026", 11.5, R.MUTED, "normal", R.MONO, 0.22),
    ], hold_s=0, n_frames=clips["results"][1])

    expected = sum(n for _, n in clips.values())
    print(f"frames rendered {fr.n}, expected {expected}", flush=True)

    # 3. audio track + mux
    lst = os.path.join(audio_dir, "list.txt")
    with open(lst, "w", encoding="utf-8") as fh:
        for key, _ in NARRATION:
            fh.write(f"file '{os.path.abspath(clips[key][0])}'\n".replace("\\", "/"))
    track = os.path.join(audio_dir, "narration.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", track], check=True)
    out = os.path.abspath(args.out)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(R.FPS), "-i", os.path.join(frames_dir, "f%05d.png"),
                    "-i", track, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"-> {out}  video {fr.n / R.FPS:.1f}s  audio {duration(track):.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
