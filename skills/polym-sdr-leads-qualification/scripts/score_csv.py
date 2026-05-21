#!/usr/bin/env python3
"""
Standalone CSV scorer for polym-sdr-leads-qualification.

Environment variables:
- LLM_API_KEY   required
- LLM_MODEL     required  (e.g. claude-sonnet-4-6, gpt-4o, gemini-2.0-flash, ep-xxxx)
- LLM_PROVIDER  optional  (e.g. anthropic, openai, gemini — auto-detected from model name if omitted)
- LLM_API_BASE  optional  (override endpoint, e.g. BytePlus Ark URL)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import litellm
except ImportError:
    import subprocess
    print("litellm not found — installing now (one-time setup)...", flush=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "litellm", "--quiet"], check=True)
    import litellm

litellm.set_verbose = False

# ── Routing outcomes ──────────────────────────────────────────────────────────
QUALIFIED = "qualified"
REVIEW = "review"
DISQUALIFIED = "disqualified"

# ── Trigify CSV column names ──────────────────────────────────────────────────
class _Col:
    NAME = "NAME"
    TITLE = "JOB TITLE"
    COMPANY = "COMPANY"
    INDUSTRY = "INDUSTRY"
    SIZE = "COMPANY SIZE"
    ICP_SCORE = "ICP SCORE"
    COMPANY_URL = "COMPANY URL"
    LINKEDIN = "LINKEDIN PROFILE"
    LOCATION = "LOCATION"
    HQ_LOCATION = "HQ COMPANY LOCATION"
    INTERACTION = "INTERACTION"
    POST_URL = "POST URL"

INTERACTION_TYPE_MAP = {
    "liked": "linkedin_engagement",
    "commented": "linkedin_comment",
    "shared": "linkedin_share",
    "posted": "linkedin_post",
    "reacted": "linkedin_engagement",
}

TITLE_MAP = {
    r"\bvice\s+president\b": "VP",
    r"\bsvp\b": "SVP",
    r"\bevp\b": "EVP",
    r"\bceo\b": "CEO",
    r"\bcto\b": "CTO",
    r"\bcpo\b": "CPO",
    r"\bcmo\b": "CMO",
    r"\bcoo\b": "COO",
    r"\bcfo\b": "CFO",
    r"\bmd\b": "Managing Director",
    r"\bdir\b\.?": "Director",
    r"\bmgr\b\.?": "Manager",
    r"\bsr\.?\s+": "Senior ",
    r"\bjr\.?\s+": "Junior ",
}

SENIORITY_RULES = [
    ("executive", [r"\bceo\b", r"\bc[otfp]o\b", r"\bfounder\b", r"\bco[- ]founder\b", r"\bpresident\b"]),
    ("vp_head", [r"\bvp\b", r"\bhead of\b", r"\bmanaging director\b"]),
    ("director", [r"\bdirector\b", r"\bexecutive producer\b"]),
    ("manager_lead", [r"\bmanager\b", r"\blead\b", r"\bprincipal\b"]),
    ("junior", [r"\bintern\b", r"\bjunior\b", r"\bassistant\b", r"\bcoordinator\b", r"\banalyst\b"]),
]

SYSTEM_SCORING_TEMPLATE = """You are a deterministic lead qualification engine for {product_name} - {product_tagline}.

Your job is to analyze a lead signal, extract structured evidence, assign sub-scores, and propose a decision in a SINGLE pass.

Reason in this order:
1. Identify observed evidence only from explicit facts
2. Identify inferred evidence separately from observations
3. Identify unknowns that materially limit confidence
4. Check for confirmed hard disqualifiers
5. Assign sub-scores based on the scoring framework
6. Propose a score and decision that match the rules below

## Output Contract
You MUST return ONLY a single valid JSON object. No explanation, no markdown, no prose before or after.

{product_section}

{icp_section}

{signals_section}

{disqualification_rules_section}

{disqualification_section}

{evidence_rules_section}

{qualification_section}

## Decision Rules (Python will re-check these deterministically)
- score >= {qualified_threshold} -> decision = "qualified"
- score < {disqualified_threshold} -> decision = "disqualified"
- {disqualified_threshold} <= score < {qualified_threshold} -> decision = "review"
- If hard_disqualifiers is non-empty -> decision = "disqualified"
- If signal_strength = "low" -> decision = "disqualified"

## Required JSON Output Schema
{{
  "lead_id": "string",
  "segment": "string",
  "candidate_use_case": "string",
  "signal_strength": "high|medium|medium-low|low",
  "observed_evidence": ["string"],
  "inferred_evidence": ["string"],
  "unknowns": ["string"],
  "hard_disqualifiers": ["string"],
  "decision": "qualified|disqualified|review",
  "score": 0,
  "confidence": "high|medium|low",
  "segment_fit": 0,
  "workflow_fit": 0,
  "pain_fit": 0,
  "buyer_fit": 0,
  "commercial_fit": 0,
  "qualification_reasons": ["string"],
  "disqualification_reasons": ["string"],
  "reasoning_summary": "string",
  "suggested_use_case": "string"
}}

Rules:
- score MUST equal segment_fit + workflow_fit + pain_fit + buyer_fit + commercial_fit
- segment_fit max {w_segment}, buyer_fit max {w_buyer}, pain_fit max {w_pain}, workflow_fit max {w_workflow}, commercial_fit max {w_commercial}
- observed_evidence must contain only explicit facts from the lead or enrichment payload
- inferred_evidence must contain only deductions, not direct facts
- hard_disqualifiers must contain only confirmed negatives, never tentative language
- reasoning_summary: 2-3 sentences, factual, reference specific evidence
- qualification_reasons and disqualification_reasons: short evidence-based bullets

Return ONLY this JSON object. Nothing else."""


@dataclass
class Campaign:
    campaign_id: str
    name: str
    tagline: str
    score_weights: dict[str, int]
    qualified_threshold: int
    disqualified_threshold: int
    scoring_system_prompt: str


@dataclass
class LeadInput:
    lead_id: str
    person_name: str
    title: str
    company_name: str
    company_domain: str
    company_size: Optional[str]
    linkedin_url: Optional[str]
    signal_text: str
    signal_type: str
    signal_timestamp: str


@dataclass
class EnrichedLead:
    lead: dict[str, Any]
    company_domain: str
    title_seniority: str
    interaction_label: str
    website_summary: str
    website_title: str
    csv_context: dict[str, Any]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def load_campaign(campaign_id: str) -> Campaign:
    root = Path(__file__).resolve().parents[1] / "campaigns"
    campaign_dir = root / campaign_id
    common_dir = root / "common"
    if not campaign_dir.exists():
        raise FileNotFoundError(f"Campaign not found in skill package: {campaign_id}")

    cfg = json.loads(_read_text(campaign_dir / "config.json") or "{}")
    name = cfg.get("name", campaign_id.capitalize())
    tagline = cfg.get("tagline", "AI video generation platform")
    weights = cfg.get(
        "score_weights",
        {"segment_fit": 20, "buyer_fit": 20, "pain_fit": 25, "workflow_fit": 20, "commercial_fit": 15},
    )
    qualified_threshold = int(cfg.get("qualified_threshold", 70))
    disqualified_threshold = int(cfg.get("disqualified_threshold", 60))

    scoring = SYSTEM_SCORING_TEMPLATE.format(
        product_name=name,
        product_tagline=tagline,
        product_section=_read_text(campaign_dir / "product.md").strip(),
        icp_section=_read_text(campaign_dir / "icp.md").strip(),
        signals_section=_read_text(campaign_dir / "signals.md").strip(),
        disqualification_rules_section=_read_text(common_dir / "disqualification-rules.md").strip(),
        disqualification_section=_read_text(campaign_dir / "disqualification.md").strip(),
        evidence_rules_section=_read_text(common_dir / "evidence-extraction.md").strip(),
        qualification_section=_read_text(campaign_dir / "qualification.md").strip(),
        qualified_threshold=qualified_threshold,
        disqualified_threshold=disqualified_threshold,
        w_segment=weights.get("segment_fit", 20),
        w_buyer=weights.get("buyer_fit", 20),
        w_pain=weights.get("pain_fit", 25),
        w_workflow=weights.get("workflow_fit", 20),
        w_commercial=weights.get("commercial_fit", 15),
    )
    return Campaign(
        campaign_id=campaign_id,
        name=name,
        tagline=tagline,
        score_weights=weights,
        qualified_threshold=qualified_threshold,
        disqualified_threshold=disqualified_threshold,
        scoring_system_prompt=scoring,
    )


def _decode_csv_text(file_path: Path) -> tuple[str, str]:
    raw_bytes = file_path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", raw_bytes, 0, 1, "unable to decode CSV")


def _make_lead_id(name: str, company: str, index: int) -> str:
    raw = f"{name}_{company}_{index}"
    return re.sub(r"[^a-z0-9_]", "_", raw.lower().strip())[:64]


def _build_signal_text(row: dict[str, str]) -> str:
    parts: list[str] = []
    name = row.get(_Col.NAME, "").strip()
    title = row.get(_Col.TITLE, "").strip()
    company = row.get(_Col.COMPANY, "").strip()
    interaction = row.get(_Col.INTERACTION, "").strip()
    post_url = row.get(_Col.POST_URL, "").strip()
    icp_note = row.get(_Col.ICP_SCORE, "").strip()
    industry = row.get(_Col.INDUSTRY, "").strip()
    size = row.get(_Col.SIZE, "").strip()
    location = row.get(_Col.LOCATION, "").strip()
    hq = row.get(_Col.HQ_LOCATION, "").strip()
    if interaction and company:
        parts.append(
            f"{name} ({title} at {company}) {interaction.lower()} a LinkedIn post"
            + (f" (Post: {post_url})" if post_url else "")
            + "."
        )
    if icp_note:
        parts.append(f"Trigify qualification note: {icp_note}")
    firm_parts: list[str] = []
    if industry:
        firm_parts.append(f"industry: {industry}")
    if size:
        firm_parts.append(f"company size: {size} employees")
    if hq and hq != location:
        firm_parts.append(f"HQ: {hq}")
    elif hq:
        firm_parts.append(f"location: {hq}")
    if firm_parts:
        parts.append("Company details - " + ", ".join(firm_parts) + ".")
    return " ".join(parts).strip()


def load_csv(file_path: Path) -> list[tuple[LeadInput, dict[str, str]]]:
    csv_text, _ = _decode_csv_text(file_path)
    reader = csv.DictReader(io.StringIO(csv_text, newline=""))
    run_timestamp = datetime.now(timezone.utc).isoformat()
    results: list[tuple[LeadInput, dict[str, str]]] = []
    for index, row in enumerate(reader, start=1):
        name = (row.get(_Col.NAME) or "").strip()
        company = (row.get(_Col.COMPANY) or "").strip()
        if not name or not company:
            continue
        interaction = (row.get(_Col.INTERACTION) or "").strip().lower()
        signal_type = INTERACTION_TYPE_MAP.get(interaction, "linkedin_engagement")
        raw = {
            "lead_id": _make_lead_id(name, company, index),
            "person_name": name,
            "title": row.get(_Col.TITLE, "").strip(),
            "company_name": company,
            "company_domain": row.get(_Col.COMPANY_URL, "").strip(),
            "company_size": row.get(_Col.SIZE, "").strip() or None,
            "linkedin_url": row.get(_Col.LINKEDIN, "").strip() or None,
            "signal_text": _build_signal_text(row),
            "signal_type": signal_type,
            "signal_timestamp": run_timestamp,
        }
        results.append((normalize_lead(raw), row))
    return results


def _normalize_domain(value: str) -> str:
    value = str(value or "").strip().lower().rstrip("/")
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    host = urlparse(value).netloc
    return host.removeprefix("www.")


def _normalize_title(value: str) -> str:
    lower = str(value or "").strip().lower()
    for pattern, replacement in TITLE_MAP.items():
        lower = re.sub(pattern, replacement.lower(), lower, flags=re.IGNORECASE)
    return " ".join(word.capitalize() for word in lower.split())


def normalize_lead(raw: dict[str, Any]) -> LeadInput:
    signal_text = str(raw.get("signal_text") or "").strip()
    if not signal_text:
        raise ValueError("signal_text is required")
    linkedin = raw.get("linkedin_url")
    if linkedin:
        linkedin = str(linkedin).strip()
        if linkedin and not linkedin.startswith("http"):
            linkedin = f"https://{linkedin}"
    return LeadInput(
        lead_id=str(raw.get("lead_id", "")).strip(),
        person_name=str(raw.get("person_name", "")).strip(),
        title=_normalize_title(raw.get("title", "")),
        company_name=str(raw.get("company_name", "")).strip(),
        company_domain=_normalize_domain(raw.get("company_domain", "")),
        company_size=(str(raw.get("company_size", "")).strip() or None),
        linkedin_url=linkedin or None,
        signal_text=signal_text,
        signal_type=str(raw.get("signal_type", "")).strip(),
        signal_timestamp=str(raw.get("signal_timestamp", "")).strip(),
    )


def infer_title_seniority(title: str) -> str:
    text = title.lower()
    for label, patterns in SENIORITY_RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                return label
    if not text:
        return "unknown"
    return "individual_contributor"


def fetch_website_summary(domain: str, timeout: int = 8) -> tuple[str, str]:
    if not domain:
        return "", ""
    urls = []
    if domain.startswith("http://") or domain.startswith("https://"):
        urls.append(domain)
    else:
        urls.extend([f"https://{domain}", f"http://{domain}"])
    for url in urls:
        try:
            req = Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 LeadGenCortexSkill/1.0"},
                method="GET",
            )
            with urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    continue
                html = resp.read(150_000).decode("utf-8", errors="ignore")
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
            desc_match = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
            desc = re.sub(r"\s+", " ", desc_match.group(1)).strip() if desc_match else ""
            return title[:180], desc[:500]
        except Exception:
            continue
    return "", ""


def enrich_lead(lead: LeadInput, raw_row: dict[str, str], allow_web: bool) -> EnrichedLead:
    website_title = ""
    website_summary = ""
    if allow_web and lead.company_domain:
        website_title, website_summary = fetch_website_summary(lead.company_domain)
    return EnrichedLead(
        lead=asdict(lead),
        company_domain=lead.company_domain,
        title_seniority=infer_title_seniority(lead.title),
        interaction_label=(raw_row.get(_Col.INTERACTION) or "").strip().lower(),
        website_summary=website_summary,
        website_title=website_title,
        csv_context={
            "industry": (raw_row.get(_Col.INDUSTRY) or "").strip(),
            "company_size": (raw_row.get(_Col.SIZE) or "").strip(),
            "icp_note": (raw_row.get(_Col.ICP_SCORE) or "").strip(),
            "location": (raw_row.get(_Col.LOCATION) or "").strip(),
            "hq_company_location": (raw_row.get(_Col.HQ_LOCATION) or "").strip(),
            "post_url": (raw_row.get(_Col.POST_URL) or "").strip(),
        },
    )


def build_messages(system_prompt: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, indent=2, ensure_ascii=False)},
    ]


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("LLM returned empty content")
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("LLM response did not contain a valid JSON object")


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str,
    api_key: str,
    api_base: str,
    provider: str,
    timeout: int = 120,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "timeout": timeout,
        "num_retries": 2,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base
    if provider:
        kwargs["custom_llm_provider"] = provider
    try:
        response = litellm.completion(**kwargs)
    except Exception as exc:
        raise RuntimeError(f"LLM call failed: {exc}") from exc
    content = (response.choices[0].message.content or "").strip()
    return _extract_json_object(content)


def _clean_list(data: dict[str, Any], key: str) -> list[str]:
    return [str(x).strip() for x in (data.get(key) or []) if str(x).strip()]


def sanitize_stage1(data: dict[str, Any], lead_id: str) -> dict[str, Any]:
    signal_strength = str(data.get("signal_strength") or "medium-low").strip().lower()
    if signal_strength not in {"high", "medium", "medium-low", "low"}:
        signal_strength = "medium-low"
    return {
        "lead_id": str(data.get("lead_id") or lead_id),
        "segment": str(data.get("segment") or "unknown").strip(),
        "candidate_use_case": str(data.get("candidate_use_case") or "").strip(),
        "signal_strength": signal_strength,
        "observed_evidence": _clean_list(data, "observed_evidence"),
        "inferred_evidence": _clean_list(data, "inferred_evidence"),
        "unknowns": _clean_list(data, "unknowns"),
        "hard_disqualifiers": _clean_list(data, "hard_disqualifiers"),
    }


def apply_signal_strength_guardrail(evidence: dict[str, Any], interaction_label: str) -> dict[str, Any]:
    interaction = str(interaction_label or "").strip().lower()
    if (
        interaction in {"liked", "reacted"}
        and evidence.get("signal_strength") == "low"
        and not evidence.get("hard_disqualifiers")
    ):
        # Likes/reactions are soft signals. Without a confirmed hard disqualifier,
        # normalise to medium-low so routing falls back to score-based logic.
        evidence["signal_strength"] = "medium-low"
    return evidence


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def sanitize_stage2(data: dict[str, Any], lead_id: str) -> dict[str, Any]:
    return {
        "lead_id": str(data.get("lead_id") or lead_id),
        "decision": str(data.get("decision") or REVIEW).strip().lower(),
        "score": _coerce_int(data.get("score")),
        "confidence": str(data.get("confidence") or "medium").strip().lower(),
        "segment_fit": _coerce_int(data.get("segment_fit")),
        "workflow_fit": _coerce_int(data.get("workflow_fit")),
        "pain_fit": _coerce_int(data.get("pain_fit")),
        "buyer_fit": _coerce_int(data.get("buyer_fit")),
        "commercial_fit": _coerce_int(data.get("commercial_fit")),
        "qualification_reasons": _clean_list(data, "qualification_reasons"),
        "disqualification_reasons": _clean_list(data, "disqualification_reasons"),
        "reasoning_summary": str(data.get("reasoning_summary") or "").strip(),
        "suggested_use_case": str(data.get("suggested_use_case") or "").strip(),
    }


def validate_and_route(
    evidence: dict[str, Any], decision: dict[str, Any], campaign: Campaign
) -> tuple[dict[str, Any], str]:
    weights = campaign.score_weights
    decision["segment_fit"] = min(max(decision["segment_fit"], 0), int(weights.get("segment_fit", 20)))
    decision["buyer_fit"] = min(max(decision["buyer_fit"], 0), int(weights.get("buyer_fit", 20)))
    decision["pain_fit"] = min(max(decision["pain_fit"], 0), int(weights.get("pain_fit", 25)))
    decision["workflow_fit"] = min(max(decision["workflow_fit"], 0), int(weights.get("workflow_fit", 20)))
    decision["commercial_fit"] = min(max(decision["commercial_fit"], 0), int(weights.get("commercial_fit", 15)))
    decision["score"] = (
        decision["segment_fit"]
        + decision["buyer_fit"]
        + decision["pain_fit"]
        + decision["workflow_fit"]
        + decision["commercial_fit"]
    )

    if evidence.get("hard_disqualifiers"):
        if not decision["disqualification_reasons"]:
            decision["disqualification_reasons"] = list(evidence["hard_disqualifiers"])
        routing = DISQUALIFIED
    elif evidence.get("signal_strength") == "low":
        if not decision["disqualification_reasons"]:
            decision["disqualification_reasons"] = ["Signal strength is low"]
        routing = DISQUALIFIED
    elif decision["score"] >= campaign.qualified_threshold:
        routing = QUALIFIED
    elif decision["score"] < campaign.disqualified_threshold:
        routing = DISQUALIFIED
    else:
        routing = REVIEW
    decision["decision"] = routing
    return decision, routing


def write_results(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = output_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    fields = [
        "lead_id", "person_name", "title", "company_name", "company_domain",
        "company_size", "linkedin_url", "decision", "score", "confidence",
        "segment", "signal_strength", "candidate_use_case", "suggested_use_case",
        "qualification_reasons", "disqualification_reasons", "reasoning_summary",
    ]

    with (
        (output_dir / "all_scored_leads.csv").open("w", newline="", encoding="utf-8") as all_fp,
        (output_dir / "qualified_leads.csv").open("w", newline="", encoding="utf-8") as q_fp,
        (output_dir / "review_leads.csv").open("w", newline="", encoding="utf-8") as r_fp,
        (output_dir / "disqualified_leads.csv").open("w", newline="", encoding="utf-8") as d_fp,
    ):
        writers = {
            "all": csv.DictWriter(all_fp, fieldnames=fields),
            QUALIFIED: csv.DictWriter(q_fp, fieldnames=fields),
            REVIEW: csv.DictWriter(r_fp, fieldnames=fields),
            DISQUALIFIED: csv.DictWriter(d_fp, fieldnames=fields),
        }
        for writer in writers.values():
            writer.writeheader()

        for row in rows:
            export_row = {
                "lead_id": row["lead"]["lead_id"],
                "person_name": row["lead"]["person_name"],
                "title": row["lead"]["title"],
                "company_name": row["lead"]["company_name"],
                "company_domain": row["lead"]["company_domain"],
                "company_size": row["lead"]["company_size"] or "",
                "linkedin_url": row["lead"]["linkedin_url"] or "",
                "decision": row["routing"],
                "score": row["decision"]["score"],
                "confidence": row["decision"]["confidence"],
                "segment": row["evidence"]["segment"],
                "signal_strength": row["evidence"]["signal_strength"],
                "candidate_use_case": row["evidence"]["candidate_use_case"],
                "suggested_use_case": row["decision"]["suggested_use_case"],
                "qualification_reasons": " | ".join(row["decision"]["qualification_reasons"]),
                "disqualification_reasons": " | ".join(row["decision"]["disqualification_reasons"]),
                "reasoning_summary": row["decision"]["reasoning_summary"],
            }
            writers["all"].writerow(export_row)
            writers[row["routing"]].writerow(export_row)

            lead_id = row["lead"]["lead_id"]
            for suffix, payload in (
                ("input", row["lead"]),
                ("enrichment", row["enrichment"]),
                ("evidence", row["evidence"]),
                ("decision", row["decision"]),
            ):
                (artifact_dir / f"{lead_id}_{suffix}.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
                )

    summary = {
        "lead_count": len(rows),
        QUALIFIED: sum(1 for r in rows if r["routing"] == QUALIFIED),
        REVIEW: sum(1 for r in rows if r["routing"] == REVIEW),
        DISQUALIFIED: sum(1 for r in rows if r["routing"] == DISQUALIFIED),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a Trigify CSV with 1 direct LLM call per lead.")
    parser.add_argument("--input", required=True, help="Path to the CSV file")
    parser.add_argument("--output-dir", required=True, help="Directory to write scored outputs")
    parser.add_argument("--campaign", default="seedance", help="Bundled campaign id to use")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit on number of rows to process")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Optional pause between leads (ms)")
    parser.add_argument("--disable-web-enrichment", action="store_true", help="Skip best-effort website fetch")
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", ""), help="LLM provider (e.g. anthropic, openai, gemini). Auto-detected from model name if omitted.")
    parser.add_argument("--api-base", default=os.environ.get("LLM_API_BASE", ""), help="Override provider API base URL (e.g. BytePlus Ark endpoint)")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", ""), help="LLM model name (e.g. claude-sonnet-4-6, gpt-4o, gemini-2.0-flash, ep-xxxx)")
    parser.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", ""), help="LLM API key")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.api_key:
        print("Missing LLM_API_KEY or --api-key", file=sys.stderr)
        return 2
    if not args.model:
        print("Missing LLM_MODEL or --model", file=sys.stderr)
        return 2

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    campaign = load_campaign(args.campaign)
    lead_rows = load_csv(input_path)
    if args.limit and args.limit > 0:
        lead_rows = lead_rows[: args.limit]

    # Enrich all leads in parallel — website fetches are I/O-bound and dominate wall time.
    allow_web = not args.disable_web_enrichment
    n = len(lead_rows)
    if allow_web and n > 1:
        print(f"Enriching {n} leads (parallel)...")
        with ThreadPoolExecutor(max_workers=min(n, 10)) as pool:
            enriched_list = list(pool.map(
                lambda item: enrich_lead(item[0], item[1], allow_web=True),
                lead_rows,
            ))
    else:
        enriched_list = [enrich_lead(lead, row, allow_web=allow_web) for lead, row in lead_rows]

    results: list[dict[str, Any]] = []
    for index, ((lead, raw_row), enriched) in enumerate(zip(lead_rows, enriched_list), start=1):
        print(f"[{index}/{n}] scoring {lead.lead_id} - {lead.person_name} @ {lead.company_name}")
        scoring_payload = {"lead": asdict(lead), "enrichment": asdict(enriched)}
        scoring_response = chat_completion(
            build_messages(campaign.scoring_system_prompt, scoring_payload),
            model=args.model,
            api_key=args.api_key,
            api_base=args.api_base,
            provider=args.provider,
        )
        evidence = apply_signal_strength_guardrail(
            sanitize_stage1(scoring_response, lead.lead_id),
            enriched.interaction_label,
        )
        decision = sanitize_stage2(scoring_response, lead.lead_id)
        decision, routing = validate_and_route(evidence, decision, campaign)
        results.append(
            {
                "lead": asdict(lead),
                "enrichment": asdict(enriched),
                "evidence": evidence,
                "decision": decision,
                "routing": routing,
            }
        )
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    write_results(output_dir, results)
    print(json.dumps({"ok": True, "output_dir": str(output_dir), "lead_count": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
