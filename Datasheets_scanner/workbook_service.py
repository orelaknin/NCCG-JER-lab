from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Callable, Optional

import pandas as pd
from openpyxl import load_workbook

try:
    from .ollama_utils import (
        ExtractionResult,
        check_ollama_ready,
        extract_temperature_by_regex,
        extract_temperature_info,
        finalize_extraction,
    )
    from .pdf_utils import extract_pdf_text
    from .path_utils import connect_to_share, normalize_datasheet_path
except ImportError:
    from ollama_utils import (
        ExtractionResult,
        check_ollama_ready,
        extract_temperature_by_regex,
        extract_temperature_info,
        finalize_extraction,
    )
    from pdf_utils import extract_pdf_text
    from path_utils import connect_to_share, normalize_datasheet_path


@dataclass
class ProcessingConfig:
    input_excel: str
    output_excel: str
    datasheet_column: str
    unique_id_column: str
    drive_letter: str = ""
    network_root: str = ""
    username: str = ""
    password: str = ""
    domain: str = ""
    model: str = "llama3.1"
    prompt: str = ""


ProgressCallback = Callable[[int, int], None]
LogCallback = Callable[[str], None]


DEFAULT_OUTPUT_COLUMNS = {
    "normalized_datasheet_path": "normalized_datasheet_path",
    "temperature_range": "temperature_range",
    "source_sentence": "source_sentence",
    "extraction_status": "extraction_status",
    "extraction_error": "extraction_error",
}


ILLEGAL_XLSX_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def load_excel_columns(excel_path: str) -> list[str]:
    """Return column names from the first sheet with a fast header-only read."""

    suffix = Path(excel_path).suffix.lower()

    if suffix in {".xlsx", ".xlsm"}:
        workbook = load_workbook(excel_path, read_only=True, data_only=True)
        try:
            worksheet = workbook[workbook.sheetnames[0]]
            header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
            if header_row is None:
                return []
            return [str(cell).strip() for cell in header_row if cell is not None and str(cell).strip()]
        finally:
            workbook.close()

    preview = pd.read_excel(excel_path, nrows=0, engine="openpyxl")
    return [str(col).strip() for col in preview.columns.tolist() if str(col).strip()]


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def _sanitize_for_excel(value: object) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    return ILLEGAL_XLSX_CHARS_RE.sub("", text)


def process_excel(
    config: ProcessingConfig,
    progress_callback: Optional[ProgressCallback] = None,
    log_callback: Optional[LogCallback] = None,
) -> str:
    """Process the workbook and create a new Excel file with extracted data."""

    def log(message: str) -> None:
        if log_callback:
            log_callback(message)

    def progress(current: int, total: int) -> None:
        if progress_callback:
            progress_callback(current, total)

    input_path = Path(config.input_excel)
    output_path = Path(config.output_excel)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    log(f"Reading workbook: {input_path}")
    df = pd.read_excel(input_path, engine="openpyxl")
    if config.datasheet_column not in df.columns:
        raise ValueError(f"Datasheet column '{config.datasheet_column}' was not found in the workbook.")
    if config.unique_id_column not in df.columns:
        raise ValueError(f"Unique ID column '{config.unique_id_column}' was not found in the workbook.")

    if config.network_root:
        ok, message = connect_to_share(config.network_root, config.username, config.password, config.domain)
        log(message)
        if not ok:
            log("Continuing without authenticated share connection.")

    total = len(df)
    log(f"Rows to process: {total}")

    normalized_paths: list[str] = []
    temp_ranges: list[str] = []
    source_sentences: list[str] = []
    statuses: list[str] = []
    errors: list[str] = []

    task_prompt = config.prompt.strip()
    if not task_prompt:
        task_prompt = (
            "Extract the operating temperature range from the datasheet text and return the exact source sentence."
        )

    use_llm = True
    llm_check_ok, llm_check_message = check_ollama_ready(config.model)
    if not llm_check_ok:
        use_llm = False
        log(f"Ollama unavailable. Using regex fallback for this run. Reason: {llm_check_message}")
    else:
        log(f"Ollama ready. Using model: {config.model}")

    for idx, row in df.iterrows():
        uid = _safe_text(row.get(config.unique_id_column, ""))
        raw_path = row.get(config.datasheet_column, "")
        normalized_path = normalize_datasheet_path(raw_path, config.drive_letter, config.network_root)
        normalized_paths.append(_sanitize_for_excel(normalized_path))

        current_row = len(normalized_paths)
        progress(current_row, total)

        if not normalized_path:
            temp_ranges.append("")
            source_sentences.append("")
            statuses.append("missing_path")
            errors.append(_sanitize_for_excel("Datasheet path is empty"))
            log(f"[{current_row}/{total}] {uid or idx}: missing datasheet path")
            continue

        if not Path(normalized_path).exists():
            temp_ranges.append("")
            source_sentences.append("")
            statuses.append("file_not_found")
            errors.append(_sanitize_for_excel(f"File not found: {normalized_path}"))
            log(f"[{current_row}/{total}] {uid or idx}: file not found -> {normalized_path}")
            continue

        pdf_result = extract_pdf_text(normalized_path)
        if pdf_result.error:
            temp_ranges.append("")
            source_sentences.append("")
            statuses.append("pdf_read_error")
            errors.append(_sanitize_for_excel(pdf_result.error))
            log(f"[{current_row}/{total}] {uid or idx}: {pdf_result.error}")
            continue

        if not pdf_result.text.strip():
            temp_ranges.append("")
            source_sentences.append("")
            statuses.append("no_text_extracted")
            errors.append(_sanitize_for_excel("No searchable text extracted from PDF"))
            log(f"[{current_row}/{total}] {uid or idx}: no searchable text extracted")
            continue

        if use_llm:
            extraction = extract_temperature_info(
                pdf_result.text,
                prompt=task_prompt,
                model=config.model,
            )
            if extraction.error and "ollama" in extraction.error.lower():
                use_llm = False
                log(f"Ollama became unavailable during run. Switching to regex fallback. Reason: {extraction.error}")
                extraction = extract_temperature_by_regex(pdf_result.text)
            else:
                extraction = finalize_extraction(pdf_result.text, extraction)
        else:
            extraction = extract_temperature_by_regex(pdf_result.text)

        if extraction.temperature_range and not extraction.source_sentence:
            extraction = finalize_extraction(pdf_result.text, extraction)

        temp_ranges.append(_sanitize_for_excel(extraction.temperature_range))
        source_sentences.append(_sanitize_for_excel(extraction.source_sentence))
        if extraction.error:
            statuses.append("extraction_warning")
            errors.append(_sanitize_for_excel(extraction.error))
            log(f"[{current_row}/{total}] {uid or idx}: extraction warning -> {extraction.error}")
        else:
            if not extraction.temperature_range:
                statuses.append("extraction_warning")
                reason = "Temperature range not found"
                errors.append(reason)
                log(f"[{current_row}/{total}] {uid or idx}: extraction warning -> {reason}")
            else:
                statuses.append("ok_llm" if use_llm else "ok_regex")
                errors.append("")
                log(f"[{current_row}/{total}] {uid or idx}: extracted temperature range")

    df[DEFAULT_OUTPUT_COLUMNS["normalized_datasheet_path"]] = normalized_paths
    df[DEFAULT_OUTPUT_COLUMNS["temperature_range"]] = temp_ranges
    df[DEFAULT_OUTPUT_COLUMNS["source_sentence"]] = source_sentences
    df[DEFAULT_OUTPUT_COLUMNS["extraction_status"]] = statuses
    df[DEFAULT_OUTPUT_COLUMNS["extraction_error"]] = errors

    for col in DEFAULT_OUTPUT_COLUMNS.values():
        df[col] = df[col].map(_sanitize_for_excel)

    log(f"Writing output workbook: {output_path}")
    df.to_excel(output_path, index=False, engine="openpyxl")
    return str(output_path)
