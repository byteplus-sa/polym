#!/usr/bin/env python3
"""
Unit tests for polym-sdr-leads-qualification.

Covers:
- _extract_json_object()  — JSON parsing / markdown-fence stripping
- infer_title_seniority() — title normalisation
- validate_and_route()    — deterministic scoring and routing logic
- chat_completion()       — litellm adapter: kwargs, provider routing, error handling

litellm is mocked at module level so these tests run without it installed.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Mock litellm before score_csv is imported ─────────────────────────────────
_mock_litellm = MagicMock()
sys.modules["litellm"] = _mock_litellm

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from score_csv import (  # noqa: E402
    Campaign,
    _extract_json_object,
    chat_completion,
    infer_title_seniority,
    validate_and_route,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_campaign(**overrides) -> Campaign:
    defaults = dict(
        campaign_id="test",
        name="Test Product",
        tagline="Test tagline",
        score_weights={
            "segment_fit": 20,
            "buyer_fit": 20,
            "pain_fit": 25,
            "workflow_fit": 20,
            "commercial_fit": 15,
        },
        qualified_threshold=70,
        disqualified_threshold=60,
        scoring_system_prompt="",
    )
    defaults.update(overrides)
    return Campaign(**defaults)


def _make_decision(**overrides) -> dict:
    d = {
        "segment_fit": 15,
        "buyer_fit": 15,
        "pain_fit": 15,
        "workflow_fit": 15,
        "commercial_fit": 10,
        "decision": "review",
        "confidence": "medium",
        "score": 0,
        "disqualification_reasons": [],
        "qualification_reasons": [],
        "reasoning_summary": "",
        "suggested_use_case": "",
    }
    d.update(overrides)
    return d


def _make_litellm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── _extract_json_object ──────────────────────────────────────────────────────

class TestExtractJsonObject(unittest.TestCase):

    def test_plain_json(self):
        self.assertEqual(_extract_json_object('{"k": 1}'), {"k": 1})

    def test_markdown_json_fence(self):
        self.assertEqual(_extract_json_object('```json\n{"k": 1}\n```'), {"k": 1})

    def test_markdown_plain_fence(self):
        self.assertEqual(_extract_json_object('```\n{"k": 1}\n```'), {"k": 1})

    def test_json_embedded_in_prose(self):
        result = _extract_json_object('Here you go: {"k": 1} done.')
        self.assertEqual(result, {"k": 1})

    def test_whitespace_stripped(self):
        self.assertEqual(_extract_json_object('  \n{"k": 1}\n  '), {"k": 1})

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            _extract_json_object("")

    def test_no_json_raises(self):
        with self.assertRaises((ValueError, Exception)):
            _extract_json_object("no json here at all")


# ── infer_title_seniority ─────────────────────────────────────────────────────

class TestInferTitleSeniority(unittest.TestCase):

    def test_ceo(self):
        self.assertEqual(infer_title_seniority("CEO"), "executive")

    def test_founder(self):
        self.assertEqual(infer_title_seniority("Co-Founder & CTO"), "executive")

    def test_vp(self):
        self.assertEqual(infer_title_seniority("VP of Marketing"), "vp_head")

    def test_director(self):
        self.assertEqual(infer_title_seniority("Director of Engineering"), "director")

    def test_manager(self):
        self.assertEqual(infer_title_seniority("Product Manager"), "manager_lead")

    def test_intern(self):
        self.assertEqual(infer_title_seniority("Marketing Intern"), "junior")

    def test_empty(self):
        self.assertEqual(infer_title_seniority(""), "unknown")

    def test_ic(self):
        self.assertEqual(infer_title_seniority("Software Engineer"), "individual_contributor")


# ── validate_and_route ────────────────────────────────────────────────────────

class TestValidateAndRoute(unittest.TestCase):

    def test_qualified(self):
        # 15+15+15+15+10 = 70 → qualified (>= threshold of 70)
        evidence = {"hard_disqualifiers": [], "signal_strength": "high"}
        _, routing = validate_and_route(evidence, _make_decision(), _make_campaign())
        self.assertEqual(routing, "qualified")

    def test_review_band(self):
        # 13+13+13+13+10 = 62 → review (60 <= score < 70)
        evidence = {"hard_disqualifiers": [], "signal_strength": "medium"}
        decision = _make_decision(segment_fit=13, buyer_fit=13, pain_fit=13, workflow_fit=13, commercial_fit=8)
        _, routing = validate_and_route(evidence, decision, _make_campaign())
        self.assertEqual(routing, "review")

    def test_disqualified_by_low_score(self):
        # 10+10+10+10+8 = 48 → disqualified (< 60)
        evidence = {"hard_disqualifiers": [], "signal_strength": "medium"}
        decision = _make_decision(segment_fit=10, buyer_fit=10, pain_fit=10, workflow_fit=10, commercial_fit=8)
        _, routing = validate_and_route(evidence, decision, _make_campaign())
        self.assertEqual(routing, "disqualified")

    def test_hard_disqualifier_overrides_high_score(self):
        evidence = {"hard_disqualifiers": ["consumer product only"], "signal_strength": "high"}
        _, routing = validate_and_route(evidence, _make_decision(), _make_campaign())
        self.assertEqual(routing, "disqualified")

    def test_low_signal_disqualifies_regardless_of_score(self):
        evidence = {"hard_disqualifiers": [], "signal_strength": "low"}
        _, routing = validate_and_route(evidence, _make_decision(), _make_campaign())
        self.assertEqual(routing, "disqualified")

    def test_scores_clamped_to_max_weights(self):
        evidence = {"hard_disqualifiers": [], "signal_strength": "high"}
        # Pass scores way above the max weights
        decision = _make_decision(segment_fit=99, buyer_fit=99, pain_fit=99, workflow_fit=99, commercial_fit=99)
        result, _ = validate_and_route(evidence, decision, _make_campaign())
        self.assertEqual(result["segment_fit"], 20)
        self.assertEqual(result["buyer_fit"], 20)
        self.assertEqual(result["pain_fit"], 25)
        self.assertEqual(result["workflow_fit"], 20)
        self.assertEqual(result["commercial_fit"], 15)
        self.assertEqual(result["score"], 100)  # 20+20+25+20+15

    def test_score_recomputed_from_subscores(self):
        evidence = {"hard_disqualifiers": [], "signal_strength": "high"}
        decision = _make_decision(segment_fit=10, buyer_fit=10, pain_fit=10, workflow_fit=10, commercial_fit=10)
        result, _ = validate_and_route(evidence, decision, _make_campaign())
        # score must equal sum of subscores, not the stale model-provided value
        self.assertEqual(result["score"], 50)

    def test_hard_disqualifier_populates_reasons(self):
        reason = "B2C consumer app"
        evidence = {"hard_disqualifiers": [reason], "signal_strength": "high"}
        decision = _make_decision(disqualification_reasons=[])
        result, _ = validate_and_route(evidence, decision, _make_campaign())
        self.assertIn(reason, result["disqualification_reasons"])


# ── chat_completion (litellm adapter) ─────────────────────────────────────────

class TestChatCompletion(unittest.TestCase):

    def setUp(self):
        _mock_litellm.completion.reset_mock()
        _mock_litellm.completion.side_effect = None

    def _set_response(self, content: str):
        _mock_litellm.completion.return_value = _make_litellm_response(content)

    def _kwargs(self):
        return _mock_litellm.completion.call_args[1]

    def test_model_and_messages_passed(self):
        self._set_response('{"score": 75}')
        msgs = [{"role": "user", "content": "test"}]
        chat_completion(msgs, model="gpt-4o", api_key="sk-x", api_base="", provider="")
        self.assertEqual(self._kwargs()["model"], "gpt-4o")
        self.assertEqual(self._kwargs()["messages"], msgs)

    def test_temperature_zero(self):
        self._set_response('{"score": 75}')
        chat_completion([], model="gpt-4o", api_key="sk-x", api_base="", provider="")
        self.assertEqual(self._kwargs()["temperature"], 0)

    def test_provider_passed_as_custom_llm_provider(self):
        self._set_response('{"score": 80}')
        chat_completion([], model="claude-sonnet-4-6", api_key="sk-ant", api_base="", provider="anthropic")
        self.assertEqual(self._kwargs().get("custom_llm_provider"), "anthropic")

    def test_empty_provider_not_forwarded(self):
        self._set_response('{"score": 80}')
        chat_completion([], model="gpt-4o", api_key="sk-x", api_base="", provider="")
        self.assertNotIn("custom_llm_provider", self._kwargs())

    def test_api_base_forwarded_when_set(self):
        self._set_response('{"score": 80}')
        chat_completion([], model="ep-xxxx", api_key="key", api_base="https://ark.example.com/v1", provider="openai")
        self.assertEqual(self._kwargs().get("api_base"), "https://ark.example.com/v1")

    def test_empty_api_base_not_forwarded(self):
        self._set_response('{"score": 80}')
        chat_completion([], model="gpt-4o", api_key="key", api_base="", provider="")
        self.assertNotIn("api_base", self._kwargs())

    def test_response_json_parsed(self):
        self._set_response('{"decision": "qualified", "score": 75}')
        result = chat_completion([], model="gpt-4o", api_key="key", api_base="", provider="")
        self.assertEqual(result["decision"], "qualified")
        self.assertEqual(result["score"], 75)

    def test_markdown_fenced_response_parsed(self):
        self._set_response('```json\n{"decision": "review"}\n```')
        result = chat_completion([], model="gpt-4o", api_key="key", api_base="", provider="")
        self.assertEqual(result["decision"], "review")

    def test_litellm_exception_wrapped_as_runtime_error(self):
        _mock_litellm.completion.side_effect = Exception("rate limit exceeded")
        with self.assertRaises(RuntimeError) as ctx:
            chat_completion([], model="gpt-4o", api_key="key", api_base="", provider="")
        self.assertIn("rate limit exceeded", str(ctx.exception))

    def test_gemini_provider(self):
        self._set_response('{"score": 65}')
        chat_completion([], model="gemini-2.0-flash", api_key="AIza-x", api_base="", provider="gemini")
        self.assertEqual(self._kwargs().get("custom_llm_provider"), "gemini")
        self.assertEqual(self._kwargs()["model"], "gemini-2.0-flash")

    def test_byteplus_ark_with_api_base(self):
        self._set_response('{"score": 70}')
        ark_base = "https://ark.ap-southeast.bytepluses.com/api/v3"
        chat_completion([], model="ep-20250521-abc", api_key="ark-key", api_base=ark_base, provider="openai")
        self.assertEqual(self._kwargs().get("api_base"), ark_base)
        self.assertEqual(self._kwargs().get("custom_llm_provider"), "openai")


if __name__ == "__main__":
    unittest.main(verbosity=2)
