"""Metrics model for review responses."""

from pydantic import BaseModel, ConfigDict, Field

class ReviewMetrics(BaseModel):
    processing_time_ms: int = Field(alias="processingTimeMs")
    model: str

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
