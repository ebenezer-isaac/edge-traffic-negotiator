"""Insider-liar injection for the coordination bus (H2 trust axis).

A designated 'liar' junction publishes FALSE neighbour claims -- an inflated 'release' toward its
neighbours (claiming it sent more vehicles than it did). Critically the liar signs the false
payload with its OWN valid Ed25519 key, so the message passes signature + registry + adjacency
verification: it is a signature-valid INSIDER lie, not a spoof. It is caught only by the
recipient's conservation check against LOCAL SENSING (claimed-entered vs observed-exited), which
is the trust mechanism's ground truth (MASTER-SPEC §4: local sensing is the ultimate arbiter).

Profiles:
  * honest  -- no change (control).
  * blatant -- inflate every toward-release by +BLATANT_ADD (a surge that never happened);
               large, easy for conservation to flag.
  * stealth -- inflate by a small +STEALTH_ADD only on some ticks (tick %% STEALTH_EVERY == 0),
               probing whether small persistent lies evade the per-claim conservation flag and
               still erode trust cumulatively.

LyingBus subclasses MessageBus and overrides publish() ONLY for liar senders; honest senders and
all inbox/verify logic are untouched. Opt-in: no liar map => behaves exactly like MessageBus.
"""
from __future__ import annotations

from message_bus import MessageBus

BLATANT_ADD = 25
STEALTH_ADD = 3
STEALTH_EVERY = 3


def _falsify(payload: dict, profile: str, tick: int) -> dict:
    """Return a NEW payload with the 'toward' releases inflated per profile (immutably)."""
    toward = payload.get("toward")
    if not isinstance(toward, dict):
        return payload
    if profile == "stealth" and (tick % STEALTH_EVERY != 0):
        return payload  # stealth liar only lies intermittently
    add = BLATANT_ADD if profile == "blatant" else STEALTH_ADD
    new_toward = {}
    for nb, entry in toward.items():
        if isinstance(entry, dict):
            e = dict(entry)
            if isinstance(e.get("release"), int) and not isinstance(e.get("release"), bool):
                e["release"] = e["release"] + add
                # queue_forecast is advisory; keep it consistent with the (false) release.
                if isinstance(e.get("queue_forecast"), int):
                    e["queue_forecast"] = e["queue_forecast"] + add
            new_toward[nb] = e
        else:
            new_toward[nb] = entry
    return {**payload, "toward": new_toward}


class LyingBus(MessageBus):
    """MessageBus where designated senders publish signature-valid but content-false claims.

    ``liars``: {junction_id: profile} with profile in {"blatant","stealth"} (absent/"honest"
    => truthful). Everything else -- signing, verification, adjacency, replay, inbox -- is the
    parent's behaviour unchanged."""

    def __init__(self, registry, adjacency, liars=None):
        super().__init__(registry, adjacency)
        self._liars = {k: v for k, v in (liars or {}).items() if v and v != "honest"}
        self.lie_log = []  # (tick, sender, profile) each time a lie was actually injected

    def publish(self, identity, t: int, payload: dict):
        prof = self._liars.get(identity.junction_id)
        if prof:
            falsified = _falsify(payload, prof, t)
            if falsified is not payload and falsified != payload:
                self.lie_log.append((t, identity.junction_id, prof))
            payload = falsified
        return super().publish(identity, t, payload)


def replay_trust(events, liars):
    """Offline: replay the controller's detection events through a TrustLedger to get each
    source's trust trajectory and lie-catch counts. A claim from source S is 'confirmed by local
    sensing' iff its conservation Detection is NOT flagged. Returns a summary dict."""
    from trust import TrustLedger
    ledger = TrustLedger()
    per_source = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        for d in ev.get("detections", []):          # each event carries a list of Detections
            src = d.get("src")
            if not src:
                continue
            flagged = bool(d.get("flagged"))
            ledger = ledger.record_claim(src).verify(src, confirmed_by_local_sensing=not flagged)
            st = per_source.setdefault(src, {"claims": 0, "flagged": 0})
            st["claims"] += 1
            st["flagged"] += int(flagged)
    summary = {}
    for src, st in per_source.items():
        summary[src] = {"claims": st["claims"], "lies_caught": st["flagged"],
                        "final_trust": round(ledger.trust_of(src), 4),
                        "can_corroborate": ledger.can_corroborate(src),
                        "declared_profile": liars.get(src, "honest")}
    return summary
