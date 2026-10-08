"""Pydantic request/response schemas for casemap server API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ponytail: Literal over Enum keeps the wire format a plain string and matches
# the TestStatus enum values in casemap.models.testcase. Adding a new status
# means touching both lists, but that's a 1-line change instead of a
# cascade of conversions.
CaseStatusLiteral = Literal["pending", "in_progress", "passed", "failed", "blocked", "skipped"]
SpecFormatLiteral = Literal["openapi", "postman", "apifox", "auto"]
SourceLiteral = Literal["human", "ci", "import"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    llm_provider: str | None = None
    llm_model: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    llm_provider: str | None
    llm_model: str | None


class ProjectCreated(ProjectOut):
    """One-time response carrying the raw API key."""

    project_api_key: str


class SpecOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    format: str
    created_at: datetime
    # ponytail: graph_id exposed so the SPA can resolve the brain-map endpoint
    # without a second round-trip. One spec currently maps to one graph; if
    # multi-version support lands, this stays the "latest graph" pointer.
    graph_id: str | None = None


class SpecCreated(BaseModel):
    """Returned by POST /projects/{id}/specs."""

    model_config = ConfigDict(extra="forbid")

    spec_id: str
    graph_id: str
    case_count: int


class CaseOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    graph_id: str
    project_id: str
    type: str
    title: str
    description: str
    steps: list[dict[str, Any]]
    endpoint_ref: str | None
    tags: list[str]
    status: CaseStatusLiteral
    note: str = ""
    updated_at: datetime | None = None


class StatusPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CaseStatusLiteral
    note: str | None = None
    source: SourceLiteral = "human"


class ProgressOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    pending: int
    in_progress: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    completion_pct: float


class BulkImportEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: CaseStatusLiteral
    note: str = ""
    updated_at: datetime | None = None
    source: SourceLiteral = "import"


class BulkImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[BulkImportEntry]


class BulkExportEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    status: CaseStatusLiteral
    note: str = ""
    updated_at: datetime
    source: SourceLiteral


class BulkExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[BulkExportEntry]


class CIResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str
    status: Literal["passed", "failed"]
    duration_ms: int | None = None
    matched_case_id: str | None = None


class CIReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[CIResult]


class CIReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: int
    unmatched: int


class CITokenOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    ci_token: str
    endpoint: str


__all__ = [
    "ProjectCreate",
    "ProjectOut",
    "ProjectCreated",
    "SpecOut",
    "SpecCreated",
    "CaseOut",
    "StatusPatch",
    "ProgressOut",
    "BulkImportEntry",
    "BulkImportRequest",
    "BulkExportEntry",
    "BulkExportResponse",
    "CIResult",
    "CIReportRequest",
    "CIReportResponse",
    "CITokenOut",
]
