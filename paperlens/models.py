from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    EQUATION = "equation"
    FIGURE = "figure"
    CAPTION = "caption"
    LIST_ITEM = "list_item"
    TABLE = "table"
    OTHER = "other"


class PaperAnnotationType(str, Enum):
    HIGHLIGHT = "highlight"
    CONCEPT_EXPLANATION = "concept_explanation"
    EQUATION_INTUITION = "equation_intuition"
    SYMBOL_DEFINITION = "symbol_definition"
    METHOD_SUMMARY = "method_summary"
    FIGURE_EXPLANATION = "figure_explanation"
    CITATION_CONTEXT = "citation_context"
    IMPLEMENTATION_HINT = "implementation_hint"
    HISTORICAL_CONTEXT = "historical_context"


class AnnotationLens(str, Enum):
    BEGINNER = "beginner"
    IMPLEMENTATION = "implementation"
    MATH = "math"
    HISTORICAL = "historical"
    LINEAGE = "lineage"


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    def as_list(self) -> list[float]:
        return [self.x0, self.y0, self.x1, self.y1]


class PaperBlock(BaseModel):
    block_id: str
    paper_id: str
    page: int
    block_type: BlockType
    text: str = ""
    bbox: BBox
    reading_order: int
    section: str | None = None
    font_size: float | None = None
    linked_blocks: list[str] = Field(default_factory=list)
    image_crop_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageInfo(BaseModel):
    page: int
    image_path: str
    width_px: int
    height_px: int
    pdf_width: float
    pdf_height: float


class PaperMeta(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    arxiv_id: str | None = None
    abstract: str | None = None
    pdf_path: str | None = None
    pdf_status: str = "unknown"
    source: str = "arxiv"
    page_count: int = 0
    block_count: int = 0
    has_annotations: bool = False


class AnnotationTarget(BaseModel):
    block_id: str
    quote: str | None = None
    char_start: int | None = None
    char_end: int | None = None


class PaperChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    created_at: str = ""


class PaperAnnotation(BaseModel):
    annotation_id: str
    paper_id: str
    target: AnnotationTarget
    annotation_type: PaperAnnotationType
    annotation_text: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    lens: AnnotationLens = AnnotationLens.BEGINNER
    evidence_status: str = "interpretive"
    page: int | None = None
    bbox: BBox | None = None
    color: str | None = None
    thread: list[PaperChatMessage] = Field(default_factory=list)


class PaperDocument(BaseModel):
    paper: PaperMeta
    blocks: list[PaperBlock]
    pages: list[PageInfo] = Field(default_factory=list)
    annotations: list[PaperAnnotation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
