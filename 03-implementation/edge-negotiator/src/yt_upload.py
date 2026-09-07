"""Upload the demo video to YouTube with the Data API v3 (resumable upload).

Needs three environment variables from a Google OAuth client that has the
https://www.googleapis.com/auth/youtube scope authorised for the channel:
    GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
(or YOUTUBE_GATE_GOOGLE_REFRESH_TOKEN, the name my-dear-bob's docker-compose uses). Get the refresh token with
`python oauth-setup.py --youtube` from that project.

Usage:
    python src/yt_upload.py --file ../../WKSR2_COMP0234_SEIoT_Demo.mp4 --privacy unlisted
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

TITLE = "The Edge Negotiator: on-device small-language-model traffic signal control with a provable accident audit"
DESCRIPTION = """Can a small language model, running entirely on a cheap local computer, control London traffic signals safely and leave a record of every decision that would stand up after a crash?

This three-minute demo accompanies an MSc dissertation (Systems Engineering for the Internet of Things, University College London, 2026). Everything shown was computed in the run on screen; nothing is mocked.

0:00 The question
0:26 One live closed-loop run: a fine-tuned Qwen3-0.6B model (4-bit, Microsoft Foundry Local, one 6 GB consumer GPU) controlling nine signalised junctions in Bloomsbury in SUMO. A deterministic safety layer built on MaxPressure checks every proposal before the lights change.
1:14 The run's numbers from SUMO's own output: 598 of 686 vehicles completed, zero teleports, the model authored 77% of 435 decisions.
1:34 The audit chain: every decision is signed with the junction's Ed25519 key and hash-chained. Tampering breaks the chain; a forged signature fails verification.
1:56 Accident reconstruction: seven crash scenarios, each verified end to end with the governing UK road rule inferred from the verified facts.
2:13 The ambulance evidence pack: cited rules, no verdict.
2:31 What the study found across 30 seeds: fine-tuning moves authorship, not delay; where the network can clear, the trained model cuts delay by 18.3% against its untrained twin on 30 of 30 seeds; a model six times larger does no better; on the congested Euston corridor the gain does not reproduce.

Stack: SUMO with TraCI, Microsoft Foundry Local (ONNX int4), QLoRA fine-tuning, Ed25519 signed hash-chained audit records, UK road-law knowledge base.

Narration is synthesised speech reading a fixed script.
"""
TAGS = ["traffic signal control", "small language model", "SLM", "edge AI", "Foundry Local", "SUMO",
        "MaxPressure", "audit trail", "Ed25519", "UCL", "Internet of Things", "smart city", "London"]


def access_token() -> str:
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "refresh_token": os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ["YOUTUBE_GATE_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--privacy", choices=["public", "unlisted", "private"], default="unlisted")
    ap.add_argument("--title", default=TITLE)
    args = ap.parse_args()
    for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"):
        if not os.environ.get(k):
            print(f"missing {k}", file=sys.stderr); return 2
    if not (os.environ.get("YOUTUBE_REFRESH_TOKEN") or os.environ.get("YOUTUBE_GATE_GOOGLE_REFRESH_TOKEN")):
        print("missing YOUTUBE_REFRESH_TOKEN (or YOUTUBE_GATE_GOOGLE_REFRESH_TOKEN)", file=sys.stderr); return 2
    tok = access_token()
    meta = {"snippet": {"title": args.title[:100], "description": DESCRIPTION, "tags": TAGS, "categoryId": "28",
                        "defaultLanguage": "en-GB"},
            "status": {"privacyStatus": args.privacy, "selfDeclaredMadeForKids": False, "license": "youtube"}}
    size = os.path.getsize(args.file)
    init = httpx.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      content=json.dumps(meta), timeout=60)
    init.raise_for_status()
    session = init.headers["Location"]
    with open(args.file, "rb") as fh:
        up = httpx.put(session, headers={"Authorization": f"Bearer {tok}", "Content-Type": "video/mp4",
                                         "Content-Length": str(size)}, content=fh.read(), timeout=600)
    if up.status_code not in (200, 201):
        print("upload failed", up.status_code, up.text[:500], file=sys.stderr); return 1
    vid = up.json()["id"]
    print(f"uploaded: https://www.youtube.com/watch?v={vid}  privacy={args.privacy}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
