from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SearchAnswerStatus = Literal["answered", "refused", "completed", "partial", "failed"]


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=100_000)


class SearchRequest(BaseModel):
    question: str = Field(max_length=10_000)
    top_k: int | None = Field(default=None, ge=1, le=100)
    candidate_k: int | None = Field(default=None, ge=5, le=200)
    min_score: float | None = None
    knowledge_base_id: str | None = None
    history: list[ConversationMessage] = Field(default_factory=list, max_length=64)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class SourceItem(BaseModel):
    id: str
    document_id: str
    source: str
    title: str
    uri: str | None = None
    score: float
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SourceItem]
    retrieval: dict[str, Any]


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    retrieval: dict[str, Any]
    generation: dict[str, Any]


class MaterialAskRequest(BaseModel):
    question: str = Field(max_length=10_000)
    materials: list[SourceItem] = Field(min_length=1, max_length=20)
    history: list[ConversationMessage] = Field(default_factory=list, max_length=64)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be empty")
        return value


class SearchTestRun(BaseModel):
    id: str
    test_id: str
    run_number: int
    request: dict[str, Any]
    response: AskResponse
    created_at: datetime


class SearchTestItem(BaseModel):
    id: str
    question: str
    knowledge_base_id: str | None = None
    request: dict[str, Any]
    run_count: int = 0
    created_at: datetime
    updated_at: datetime
    latest_run_id: str | None = None
    latest_answer_status: SearchAnswerStatus | None = None
    latest_failure_category: Literal[
        "data_missing",
        "retrieval_failed",
        "evidence_extraction_failed",
        "generation_failed",
    ] | None = None
    latest_failure_reason: str | None = None
    latest_run: SearchTestRun | None = None


class SearchTestDetail(SearchTestItem):
    runs: list[SearchTestRun] = Field(default_factory=list)


class SearchTestPage(BaseModel):
    items: list[SearchTestItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class MarkdownImportRequest(BaseModel):
    path: str
    source: str = "local-markdown"
    limit: int = Field(default=0, ge=0)
    batch_size: int = Field(default=16, ge=1, le=256)
    recreate: bool = False


class ImportResponse(BaseModel):
    documents: int
    nodes: int


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class KnowledgeBaseItem(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: datetime
    updated_at: datetime
    file_count: int = 0


FileStatus = Literal["pending", "processing", "ready", "failed", "deleting"]
JobStatus = Literal["pending", "running", "completed", "failed"]
JobKind = Literal["file_ingest", "file_reindex", "finewiki_import"]


class FileItem(BaseModel):
    id: str
    knowledge_base_id: str
    filename: str
    content_type: str
    extension: str
    size: int
    sha256: str
    source: str
    status: FileStatus
    node_count: int = 0
    error: str | None = None
    last_job_id: str | None = None
    created_at: datetime
    updated_at: datetime


class JobItem(BaseModel):
    id: str
    kind: JobKind
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    stage: str
    message: str = ""
    documents_processed: int = 0
    nodes_processed: int = 0
    error: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobAccepted(BaseModel):
    job_id: str
    status: JobStatus = "pending"


class FileUploadAccepted(JobAccepted):
    file_id: str


class FineWikiImportRequest(BaseModel):
    path: str
    knowledge_base_id: str = "default"
    source: str = "finewiki-zh"
    titles: list[str] = Field(default_factory=list)
    limit: int = Field(default=0, ge=0)
    batch_size: int = Field(default=8, ge=1, le=128)
    recreate: bool = False


class FineWikiPathEntry(BaseModel):
    name: str
    path: str
    type: Literal["directory", "parquet"]
    size: int | None = None


class FineWikiPathPage(BaseModel):
    current: str
    parent: str | None = None
    roots: list[str]
    entries: list[FineWikiPathEntry]


class ChunkItem(BaseModel):
    id: str
    document_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkPage(BaseModel):
    items: list[ChunkItem]
    next_offset: str | None = None


class AdminHealth(BaseModel):
    status: Literal["ok", "degraded"]
    mongodb: dict[str, Any]
    lexical: dict[str, Any]
