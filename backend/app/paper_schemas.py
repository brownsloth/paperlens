from __future__ import annotations

from pydantic import BaseModel

from paperlens.models import AnnotationLens, BBox


class AnnotatePaperRequest(BaseModel):
    lens: AnnotationLens = AnnotationLens.BEGINNER
    max_candidates: int = 12


class CreatePaperAnnotationRequest(BaseModel):
    block_id: str
    annotation_text: str
    annotation_type: str = "concept_explanation"
    quote: str | None = None
    lens: AnnotationLens = AnnotationLens.BEGINNER
    color: str | None = None


class UpdatePaperAnnotationRequest(BaseModel):
    annotation_text: str | None = None
    annotation_type: str | None = None
    color: str | None = None


class PaperAnnotationChatRequest(BaseModel):
    message: str


class PaperBBoxRequest(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float


class PaperTextSelectionRequest(BaseModel):
    page: int
    quote: str
    question: str = ""
    block_id: str | None = None
    bbox: PaperBBoxRequest | None = None
    lens: AnnotationLens = AnnotationLens.BEGINNER
    color: str | None = None


class PaperHighlightRequest(BaseModel):
    page: int
    quote: str
    block_id: str | None = None
    bbox: PaperBBoxRequest | None = None
    color: str | None = None


class PaperRegionSelectionRequest(BaseModel):
    page: int
    bbox: PaperBBoxRequest
    question: str = "Explain what this region shows."
    lens: AnnotationLens = AnnotationLens.BEGINNER
    color: str | None = None


def bbox_from_request(req: PaperBBoxRequest | None) -> BBox | None:
    if not req:
        return None
    return BBox(x0=req.x0, y0=req.y0, x1=req.x1, y1=req.y1)
