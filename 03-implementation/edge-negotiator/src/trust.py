"""Per-agent TRUST COEFFICIENT with local sensing as the ultimate ground truth
(MASTER-SPEC §4 H2 extension; requested by both supervisors, full-scale phase).

Each junction agent has its OWN visibility (local sensing). When a neighbour SIGNS a
claim that an emergency vehicle is approaching the recipient, that claim is later
VERIFIED against the recipient's own local sensing when (or if) the vehicle actually
arrives. Local sensing is the ULTIMATE TRUTH: it is the one signal an agent can always
trust, and it is never itself doubted -- it is the arbiter every claim is scored
against.

Trust dynamics (asymmetric, lies punished extremely):
  * a VERIFIED TRUE claim (local sensing confirms arrival) nudges the source's trust UP
    with diminishing returns toward 1: trust += reward * (1 - trust);
  * a LIE (local sensing contradicts the claim -- the vehicle never arrived within the
    window) COLLAPSES trust multiplicatively: trust *= lie_factor (default 0.25), so a
    single lie undoes many truths. The penalty for a lie is EXTREME and asymmetric by
    design -- honesty is earned slowly, betrayed instantly.

Trust then WEIGHTS corroboration: a claim from a high-trust source counts fully; a
source whose trust has collapsed below ``corroboration_floor`` can no longer help force
a preemption. This bounds the insider-liar: once caught by local sensing, its future
claims are discounted. All state is rebuilt immutably (house style); trust stays in
[0, 1].
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

# Defaults. reward: how fast verified truths build trust (diminishing). lie_factor:
# multiplicative collapse on a lie (0.25 -> lose 75% in one lie). prior: trust of a
# never-seen source. floor: below this, a source cannot corroborate a preemption.
REWARD = 0.15
LIE_FACTOR = 0.25
PRIOR = 0.5
CORROBORATION_FLOOR = 0.5


@dataclass(frozen=True)
class TrustState:
    """Immutable trust record for one source (a signing key / neighbour junction)."""
    source: str
    trust: float = PRIOR
    truths: int = 0
    lies: int = 0
    claims: int = 0


@dataclass(frozen=True)
class TrustLedger:
    """Per-source trust, updated only by local-sensing verification (the ground truth).

    Frozen + rebuilt on every update (no in-place mutation). ``prior``/``reward``/
    ``lie_factor``/``floor`` are the pinned parameters; local sensing is the arbiter and
    is never doubted."""
    states: dict = field(default_factory=dict)
    prior: float = PRIOR
    reward: float = REWARD
    lie_factor: float = LIE_FACTOR
    floor: float = CORROBORATION_FLOOR

    def _get(self, source: str) -> TrustState:
        return self.states.get(source, TrustState(source=source, trust=self.prior))

    def trust_of(self, source: str) -> float:
        return self._get(source).trust

    def _with(self, st: TrustState) -> "TrustLedger":
        return replace(self, states={**self.states, st.source: st})

    def record_claim(self, source: str) -> "TrustLedger":
        """Register that ``source`` made a (signed) claim; verification comes later."""
        s = self._get(source)
        return self._with(replace(s, claims=s.claims + 1))

    def verify(self, source: str, confirmed_by_local_sensing: bool) -> "TrustLedger":
        """Score one of ``source``'s claims against LOCAL SENSING (the ground truth).

        ``confirmed_by_local_sensing=True`` -> the vehicle actually arrived: a TRUTH,
        trust rises with diminishing returns. ``False`` -> local sensing says it never
        came: a LIE, trust collapses multiplicatively (extreme, asymmetric)."""
        s = self._get(source)
        if confirmed_by_local_sensing:
            new_trust = s.trust + self.reward * (1.0 - s.trust)
            s = replace(s, trust=min(1.0, new_trust), truths=s.truths + 1)
        else:
            s = replace(s, trust=max(0.0, s.trust * self.lie_factor), lies=s.lies + 1)
        return self._with(s)

    def can_corroborate(self, source: str) -> bool:
        """True iff ``source`` is trusted enough to count toward forcing a preemption.
        A collapsed-trust (caught-lying) source cannot -- local sensing has demoted it."""
        return self.trust_of(source) >= self.floor

    def weight(self, source: str) -> float:
        """Trust weight in [0,1] for scoring this source's claim."""
        return self.trust_of(source)

    def summary(self) -> dict:
        return {src: {"trust": round(s.trust, 4), "truths": s.truths, "lies": s.lies,
                      "claims": s.claims, "can_corroborate": s.trust >= self.floor}
                for src, s in self.states.items()}


def truths_to_reach(target: float, prior: float = PRIOR, reward: float = REWARD) -> int:
    """How many consecutive verified truths to raise trust from ``prior`` to ``target``
    (for the asymmetry demonstration: many truths up, one lie down)."""
    t, n = prior, 0
    while t < target and n < 10000:
        t += reward * (1.0 - t)
        n += 1
    return n
