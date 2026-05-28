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


def _client() -> ollama.Client:
    host = os.environ.get("OLLAMA_HOST")
    return ollama.Client(host=host) if host else ollama.Client()


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
