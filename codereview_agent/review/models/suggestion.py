"""Suggestion-related response models."""
from pydantic import BaseModel, ConfigDict, Field

class SuggestionRange(BaseModel):
    start_line: int = Field(alias="startLine")
    start_col: int = Field(alias="startCol")
    end_line: int = Field(alias="endLine")
    end_col: int = Field(alias="endCol")

    model_config = ConfigDict(populate_by_name=True)


class SuggestionFix(BaseModel):
    type: str
    diff: str

    model_config = ConfigDict(populate_by_name=True)


class Suggestion(BaseModel):
    id: str
    title: str
    rationale: str
    severity: str
    tags: list[str]
    range: SuggestionRange
    fix: SuggestionFix
    fix_snippet: str = Field(alias="fixSnippet")
    confidence: float
    status: str

    model_config = ConfigDict(populate_by_name=True)
