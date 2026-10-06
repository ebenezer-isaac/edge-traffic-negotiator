"""Foundry alias -> model id resolution (slm_agent._match_model).

Regression: discovery used to take the FIRST id from /v1/models. Foundry lists every
cached model there, so with a 7B reasoning model cached first, `--model qwen3-0.6b`
silently served deepseek-r1-7b and the run hung on the 6 GB GPU.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from slm_agent import _match_model  # noqa: E402

CACHED = [
    "deepseek-r1-distill-qwen-7b-generic-gpu:4",
    "Phi-4-mini-reasoning-generic-gpu:3",
    "Phi-4-mini-instruct-generic-gpu:5",
    "qwen3-0.6b-ft1",
    "qwen3-0.6b-generic-cpu:4",
    "qwen3-0.6b-generic-gpu:2",
    "qwen3-0.6b-ft0",
]


def test_catalog_alias_resolves_to_its_own_gpu_build_not_first_listed():
    assert _match_model(CACHED, "qwen3-0.6b") == "qwen3-0.6b-generic-gpu:2"


def test_catalog_alias_does_not_resolve_to_a_fine_tuned_sibling():
    assert _match_model(CACHED, "qwen3-0.6b") not in ("qwen3-0.6b-ft0", "qwen3-0.6b-ft1")


def test_custom_registration_matches_exactly():
    assert _match_model(CACHED, "qwen3-0.6b-ft1") == "qwen3-0.6b-ft1"
    assert _match_model(CACHED, "qwen3-0.6b-ft0") == "qwen3-0.6b-ft0"


def test_phi_alias_prefers_instruct_over_reasoning():
    assert _match_model(CACHED, "phi-4-mini") == "Phi-4-mini-instruct-generic-gpu:5"
    assert _match_model(CACHED, "phi-4-mini-reasoning") == "Phi-4-mini-reasoning-generic-gpu:3"


def test_full_id_and_case_insensitive():
    assert _match_model(CACHED, "PHI-4-MINI-INSTRUCT-GENERIC-GPU:5") == "Phi-4-mini-instruct-generic-gpu:5"


def test_cpu_build_used_when_no_gpu_build_cached():
    assert _match_model(["qwen3-0.6b-generic-cpu:4"], "qwen3-0.6b") == "qwen3-0.6b-generic-cpu:4"


def test_unknown_alias_and_empty_list_return_none():
    assert _match_model(CACHED, "llama-9b") is None
    assert _match_model([], "qwen3-0.6b") is None
