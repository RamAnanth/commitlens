from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CommitCritique(BaseModel):
    id: str
    commit: str
    score: int = Field(ge=0, le=10)
    issue: Optional[str] = None
    better: Optional[str] = None
    why_good: Optional[str] = None

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id is empty")
        return value

    @field_validator("commit")
    @classmethod
    def commit_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("commit is empty")
        return value


class CritiqueResponse(BaseModel):
    critiques: List[CommitCritique]


class SuggestionResponse(BaseModel):
    summary_bullets: List[str]
    subject: str
    body_bullets: List[str]

    @property
    def full_message(self) -> str:
        body = "\n".join(f"- {item}" for item in self.body_bullets)
        if body:
            return f"{self.subject}\n\n{body}".strip()
        return self.subject


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
