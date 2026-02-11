from __future__ import annotations

import json
from typing import Iterable, List

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from .config import AppConfig, require_api_key
from .diff_cleaner import clean_diff
from .git_ops import CommitEntry, DiffSummary
from .models import CritiqueResponse, SuggestionResponse


class LLMClient:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        api_key = require_api_key()
        self.client = OpenAI(api_key=api_key)

    def critique_commits(self, commits: List[CommitEntry]) -> CritiqueResponse:
        system_prompt = (
            "You are a Principal Engineer. Grade commit messages based on the "
            "Conventional Commits 1.0.0 specification. Be concise and critical."
        )
        commit_payload = [{"id": c.sha, "message": c.message} for c in commits]
        user_prompt = (
            "Return JSON only with this schema:"
            " {\"critiques\": [{\"id\": str, \"commit\": str, \"score\": int (0-10), "
            "\"issue\": str, \"better\": str | null, \"why_good\": str | null}]}\n"
            "Return exactly one critique per input item and preserve each id.\n"
            "Commit messages as JSON:\n"
            f"{json.dumps(commit_payload, ensure_ascii=False)}"
        )

        payload = self._call_model_json(system_prompt, user_prompt)
        try:
            data = _parse_json(payload)
            response = CritiqueResponse.model_validate(data)
            expected_ids = {c.sha for c in commits}
            returned_ids = {c.id for c in response.critiques}
            if returned_ids != expected_ids:
                raise RuntimeError(
                    "The AI returned an incomplete or mismatched analysis. "
                    f"Expected {len(expected_ids)} commit ids, got {len(returned_ids)}."
                )
            return response
        except (json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(
                "The AI returned an invalid response while analyzing commits. "
                "Please try again."
            ) from exc

    def suggest_commit(self, diff: str, summary: DiffSummary) -> SuggestionResponse:
        cleaned = clean_diff(diff)
        system_prompt = (
            "You are a Principal Engineer. Propose a commit message that strictly follows "
            "Conventional Commits 1.0.0. Use the format: type(scope): subject. "
            "If scope is unknown, omit it. Be specific."
        )
        user_prompt = (
            "Return JSON only with this schema:"
            " {\"summary_bullets\": [str], \"subject\": str, \"body_bullets\": [str]}\n"
            f"Stats: {summary.files_changed} files changed, +{summary.insertions} -{summary.deletions}\n"
            "Diff:\n"
            f"{cleaned.text}"
        )
        payload = self._call_model_json(system_prompt, user_prompt)
        try:
            data = _parse_json(payload)
            return SuggestionResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise RuntimeError(
                "The AI returned an invalid response while drafting a commit message. "
                "Please try again."
            ) from exc

    def suggest_commit_stream(
        self, diff: str, summary: DiffSummary
    ) -> Iterable[str]:
        cleaned = clean_diff(diff)
        system_prompt = (
            "You are a Principal Engineer. Propose a commit message that strictly follows "
            "Conventional Commits 1.0.0. Use the format: type(scope): subject. "
            "If scope is unknown, omit it. Be specific."
        )
        user_prompt = (
            "Return plain text using this exact format:\n"
            "SUMMARY:\n"
            "- <summary bullet>\n"
            "SUBJECT:\n"
            "<single-line subject>\n"
            "BODY:\n"
            "- <body bullet>\n\n"
            f"Stats: {summary.files_changed} files changed, +{summary.insertions} -{summary.deletions}\n"
            "Diff:\n"
            f"{cleaned.text}"
        )

        return self._stream_model(system_prompt, user_prompt)

    def parse_suggestion_text(self, text: str) -> SuggestionResponse:
        return _parse_suggestion_text(text)

    def _call_model_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            if hasattr(self.client, "responses"):
                response = self.client.responses.create(
                    model=self.cfg.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text={"format": {"type": "json_object"}},
                    temperature=0,
                )
                return response.output_text

            chat = self.client.chat.completions.create(
                model=self.cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            return chat.choices[0].message.content or ""
        except RateLimitError as exc:
            raise RuntimeError(
                "Please try again in a moment. The request was rate limited."
            ) from exc
        except APITimeoutError as exc:
            raise RuntimeError(
                "Please try again. The request to the AI model timed out."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                "Please check your network connection and try again."
            ) from exc
        except APIStatusError as exc:
            raise RuntimeError(
                f"Please try again. The AI service returned an error (status {exc.status_code})."
            ) from exc

    def _stream_model(self, system_prompt: str, user_prompt: str) -> Iterable[str]:
        try:
            if hasattr(self.client, "responses"):
                stream = self.client.responses.create(
                    model=self.cfg.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text={"format": {"type": "text"}},
                    temperature=0,
                    stream=True,
                )
                for event in stream:
                    if getattr(event, "type", None) == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        if delta:
                            yield delta
                return

            stream = self.client.chat.completions.create(
                model=self.cfg.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                stream=True,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except RateLimitError as exc:
            raise RuntimeError(
                "Please try again in a moment. The request was rate limited."
            ) from exc
        except APITimeoutError as exc:
            raise RuntimeError(
                "Please try again. The request to the AI model timed out."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                "Please check your network connection and try again."
            ) from exc
        except APIStatusError as exc:
            raise RuntimeError(
                f"Please try again. The AI service returned an error (status {exc.status_code})."
            ) from exc



def _parse_json(payload: str) -> dict:
    return json.loads(payload)


def _parse_suggestion_text(text: str) -> SuggestionResponse:
    section = None
    summary: list[str] = []
    body: list[str] = []
    subject = ""

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper() == "SUMMARY:":
            section = "summary"
            continue
        if line.upper() == "SUBJECT:":
            section = "subject"
            continue
        if line.upper() == "BODY:":
            section = "body"
            continue

        if section == "subject":
            if not subject:
                subject = line
            continue

        if section in ("summary", "body"):
            if line.startswith("-"):
                item = line.lstrip("-").strip()
                if item:
                    if section == "summary":
                        summary.append(item)
                    else:
                        body.append(item)
            continue

    if not subject:
        for raw in text.splitlines():
            candidate = raw.strip()
            if not candidate:
                continue
            if candidate.upper() in {"SUMMARY:", "SUBJECT:", "BODY:"}:
                continue
            if candidate.startswith("-"):
                continue
            subject = candidate
            break
    if not subject:
        subject = "chore: update"

    return SuggestionResponse(
        summary_bullets=summary,
        subject=subject,
        body_bullets=body,
    )
