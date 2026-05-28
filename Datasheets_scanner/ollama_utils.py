from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import ollama


@dataclass
class ExtractionResult:
    temperature_range: str
    source_sentence: str
    raw_response: str = ""
    error: str = ""


JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
TEMP_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(?:°\s*)?[Cc]\s*(?:to|-|–|—|through)\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*)?[Cc]",
    re.IGNORECASE,
)
SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TEMP_PAIR_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:°\s*)?[Cc].{0,30}?(-?\d+(?:\.\d+)?)\s*(?:°\s*)?[Cc]", re.IGNORECASE)

POSITIVE_HINTS = (
    "operating",
    "recommended operating",
    "ambient",
    "ta",
    "temperature range",
)

NEGATIVE_HINTS = (
    "storage",
    "junction",
    "solder",
    "lead temperature",
    "reflow",
    "thermal shutdown",
)


def _client() -> ollama.Client:
    host = os.environ.get("OLLAMA_HOST")
    return ollama.Client(host=host) if host else ollama.Client()


def check_ollama_ready(model: str = "llama3.1") -> tuple[bool, str]:
    """Check whether Ollama is reachable and the selected model exists."""

    try:
        models_resp = _client().list()
    except Exception as exc:
        return False, f"Ollama connection failed: {exc}"

    models: list[dict[str, Any]] = []
    if isinstance(models_resp, dict):
        models = list(models_resp.get("models", []) or [])

    model_names: set[str] = set()
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        model_id = str(item.get("model", "") or "").strip()
        if name:
            model_names.add(name)
        if model_id:
            model_names.add(model_id)

    if model not in model_names and f"{model}:latest" not in model_names:
        return False, f"Ollama is running but model '{model}' is not found. Run: ollama pull {model}"

    return True, "Ollama is reachable"


def extract_temperature_by_regex(text: str) -> ExtractionResult:
    """Fallback extraction without LLM, using temperature regex and source sentence detection."""

    if not text.strip():
        return ExtractionResult(temperature_range="", source_sentence="", error="No text extracted from PDF")

    match = _best_temperature_match(text)
    if not match:
        return ExtractionResult(temperature_range="", source_sentence="", error="Temperature range not found by regex")

    temp = f"{match.group(1)} C to {match.group(2)} C"
    source = ""
    idx = match.start()

    for sentence in SPLIT_RE.split(text):
        if not sentence.strip():
            continue
        start = text.find(sentence)
        if start <= idx < start + len(sentence):
            source = sentence.strip()
            break

    if not source:
        source = text[max(0, idx - 120): match.end() + 120].strip()

    return ExtractionResult(temperature_range=temp, source_sentence=source, error="")


def _best_temperature_match(text: str):
    best = None
    best_score = -10**9
    for match in TEMP_RE.finditer(text):
        start = match.start()
        end = match.end()
        context = text[max(0, start - 180): min(len(text), end + 180)].lower()
        score = 0
        for hint in POSITIVE_HINTS:
            if hint in context:
                score += 3
        for hint in NEGATIVE_HINTS:
            if hint in context:
                score -= 4

        span_len = end - start
        if span_len < 50:
            score += 1

        if score > best_score:
            best_score = score
            best = match
    return best


def _parse_temp_pair(value: str) -> tuple[str, str] | None:
    match = TEMP_PAIR_RE.search(value or "")
    if not match:
        return None
    return (match.group(1), match.group(2))


def _temp_pair_exists_in_text(temp_value: str, text: str) -> bool:
    pair = _parse_temp_pair(temp_value)
    if not pair:
        return False
    low, high = pair
    pattern = re.compile(
        rf"{re.escape(low)}\s*(?:°\s*)?[Cc].{{0,35}}?{re.escape(high)}\s*(?:°\s*)?[Cc]",
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.search(text or "") is not None


def _find_source_for_temp(text: str, temp_value: str) -> str:
    pair = _parse_temp_pair(temp_value)
    if not pair:
        return ""
    low, high = pair
    pattern = re.compile(
        rf"{re.escape(low)}\s*(?:°\s*)?[Cc].{{0,35}}?{re.escape(high)}\s*(?:°\s*)?[Cc]",
        re.IGNORECASE,
    )
    match = pattern.search(text or "")
    if not match:
        return ""
    idx = match.start()

    for sentence in SPLIT_RE.split(text):
        if not sentence.strip():
            continue
        start = text.find(sentence)
        if start <= idx < start + len(sentence):
            return sentence.strip()

    return text[max(0, idx - 120): match.end() + 120].strip()


def finalize_extraction(text: str, extraction: ExtractionResult) -> ExtractionResult:
    """Validate extraction against source text and ensure source sentence is present when temp exists."""

    temp = (extraction.temperature_range or "").strip()
    source = (extraction.source_sentence or "").strip()
    err = (extraction.error or "").strip()

    if not temp:
        return ExtractionResult(temperature_range="", source_sentence=source, raw_response=extraction.raw_response, error=err or "Temperature range not extracted")

    if not _temp_pair_exists_in_text(temp, text):
        fallback = extract_temperature_by_regex(text)
        fallback_err = "LLM value not found in datasheet text"
        if fallback.temperature_range:
            return ExtractionResult(
                temperature_range=fallback.temperature_range,
                source_sentence=fallback.source_sentence,
                raw_response=extraction.raw_response,
                error=fallback_err,
            )
        return ExtractionResult(temperature_range="", source_sentence="", raw_response=extraction.raw_response, error=fallback_err)

    if not source:
        source = _find_source_for_temp(text, temp)
        if not source:
            return ExtractionResult(temperature_range=temp, source_sentence="", raw_response=extraction.raw_response, error="Source sentence not found for extracted temperature")

    return ExtractionResult(temperature_range=temp, source_sentence=source, raw_response=extraction.raw_response, error=err)


def _parse_response(raw: str) -> ExtractionResult:
    text = raw.strip()
    if not text:
        return ExtractionResult(temperature_range="", source_sentence="", raw_response=raw, error="Empty response from model")

    data: dict[str, Any] | None = None
    match = JSON_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None

    if isinstance(data, dict):
        temp = str(data.get("temperature_range", "") or "").strip()
        source = str(data.get("source_sentence", "") or "").strip()
        return ExtractionResult(temperature_range=temp, source_sentence=source, raw_response=raw, error="")

    temp_match = TEMP_RE.search(text)
    temp = ""
    if temp_match:
        temp = f"{temp_match.group(1)} C to {temp_match.group(2)} C"

    return ExtractionResult(temperature_range=temp, source_sentence="", raw_response=raw, error="Could not parse structured JSON response")


def extract_temperature_info(text: str, prompt: str, model: str = "llama3.1", max_chars: int = 30000) -> ExtractionResult:
    """Use Ollama to extract temperature range and source sentence."""

    if not text.strip():
        return ExtractionResult(temperature_range="", source_sentence="", error="No text extracted from PDF")

    snippet = text[:max_chars]
    full_prompt = f"""{prompt}

Return ONLY valid JSON with exactly these keys:
- temperature_range
- source_sentence

Rules:
- temperature_range should be the operating temperature range only.
- source_sentence must be the exact sentence or table row from the datasheet that supports the answer.
- If not found, return empty strings for both keys.
- Do not include markdown or extra commentary.

Datasheet text:
<<<
{snippet}
>>>
"""

    try:
        response = _client().generate(model=model, prompt=full_prompt, options={"temperature": 0})
        raw = str(response.get("response", ""))
    except Exception as exc:
        return ExtractionResult(temperature_range="", source_sentence="", error=f"Ollama error: {exc}")

    parsed = _parse_response(raw)
    if not parsed.temperature_range and not parsed.source_sentence and not parsed.error:
        parsed.error = "Model did not return temperature information"
    return parsed
