from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from catalog.citations import extract_citations, fetch_citation_to_misc
from catalog.store import (
    create_category,
    ensure_real_world_learning_category,
    ensure_seeded,
    list_categories,
    list_documents,
    move_document,
    search_category,
    search_paper,
)
from paperlens.annotate import PaperAnnotator, load_annotated, load_parsed, parse_paper
from paperlens.arxiv import fetch_real_world_learning_papers, fetch_starter_papers, load_manifest
from paperlens import library as paper_library
from paperlens.models import AnnotationLens, BBox, PaperDocument
from paperlens.paths import PAPER_FIGURES_DIR, PAPER_PAGES_DIR
from paperlens.storage import (
    annotate_region_selection,
    annotate_text_selection,
    chat_on_annotation,
    create_annotation,
    create_highlight,
    delete_annotation,
    update_annotation,
)
from speechlens.annotator import SpeechAnnotator
from speechlens import library as speech_library
from speechlens.models import AnnotateRequest, AnnotateResponse, AnnotateUrlRequest, Annotation, AnnotationDepth
from speechlens.sample_data import SAMPLE_DOCUMENT

app = FastAPI(
    title="PaperLens",
    description="User-annotated documents: speeches, research papers, and PDFs",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_documents: dict[str, AnnotateResponse] = {SAMPLE_DOCUMENT.doc_id: SAMPLE_DOCUMENT}


class AnnotateSpeechRequest(BaseModel):
    mode: AnnotationDepth = AnnotationDepth.MEDIUM
    require_sources: bool = True
    enable_web_search: bool = True


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


class CreateCategoryRequest(BaseModel):
    name: str


class MoveDocumentRequest(BaseModel):
    category_id: str


class FetchCitationRequest(BaseModel):
    arxiv_id: str | None = None
    doi: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sample", response_model=AnnotateResponse)
def get_sample() -> AnnotateResponse:
    return SAMPLE_DOCUMENT


@app.get("/library/sources")
def library_sources() -> list[dict]:
    return speech_library.list_sources()


@app.get("/library/{source_id}/speeches")
def library_speeches(
    source_id: str,
    search: str = Query("", description="Filter by title or slug"),
) -> list[dict]:
    try:
        return speech_library.list_speeches(source_id, search=search)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/library/{source_id}/speeches/{slug}", response_model=AnnotateResponse)
def library_speech(source_id: str, slug: str) -> AnnotateResponse:
    try:
        doc = speech_library.load_speech(source_id, slug)
        _documents[doc.doc_id] = doc
        return doc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/library/{source_id}/speeches/{slug}/annotate", response_model=AnnotateResponse)
def library_annotate_speech(
    source_id: str,
    slug: str,
    request: AnnotateSpeechRequest,
) -> AnnotateResponse:
    try:
        doc = speech_library.annotate_speech(
            source_id,
            slug,
            mode=request.mode.value,
            require_sources=request.require_sources,
            enable_web_search=request.enable_web_search,
        )
        _documents[doc.doc_id] = doc
        return doc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/annotate", response_model=AnnotateResponse)
def annotate(request: AnnotateRequest) -> AnnotateResponse:
    try:
        annotator = SpeechAnnotator(mode=request.mode, require_sources=request.require_sources)
        doc = annotator.from_text(request.text, title=request.title)
        result = annotator.annotate(doc).response
        _documents[result.doc_id] = result
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/annotate_url", response_model=AnnotateResponse)
def annotate_url(request: AnnotateUrlRequest) -> AnnotateResponse:
    try:
        annotator = SpeechAnnotator(mode=request.mode, require_sources=request.require_sources)
        doc = annotator.from_url(request.url)
        result = annotator.annotate(doc).response
        _documents[result.doc_id] = result
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/document/{doc_id}", response_model=AnnotateResponse)
def get_document(doc_id: str) -> AnnotateResponse:
    doc = _documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.patch("/annotation/{annotation_id}", response_model=Annotation)
def patch_annotation(annotation_id: str, annotation_text: str) -> Annotation:
    for doc in _documents.values():
        for idx, ann in enumerate(doc.annotations):
            if ann.annotation_id == annotation_id:
                updated = ann.model_copy(update={"annotation_text": annotation_text})
                doc.annotations[idx] = updated
                return updated
    raise HTTPException(status_code=404, detail="Annotation not found")


# --- PaperLens catalog ---


@app.get("/categories")
def categories_list() -> list[dict]:
    ensure_seeded()
    return list_categories()


@app.post("/categories")
def categories_create(request: CreateCategoryRequest) -> dict:
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Category name required")
    return create_category(request.name.strip())


@app.get("/categories/{category_id}/documents")
def categories_documents(category_id: str, search: str = Query("")) -> list[dict]:
    ensure_seeded()
    if search.strip():
        return search_category(category_id, search)
    return list_documents(category_id)


@app.patch("/documents/{doc_id}/category")
def documents_move(doc_id: str, request: MoveDocumentRequest) -> dict:
    try:
        return move_document(doc_id, request.category_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/papers/{paper_id}/search")
def papers_search(paper_id: str, q: str = Query("")) -> dict:
    return search_paper(paper_id, q)


@app.get("/papers/{paper_id}/citations")
def papers_citations(paper_id: str) -> list[dict]:
    doc = load_parsed(paper_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Parse the paper first")
    return extract_citations(paper_id)


@app.post("/papers/{paper_id}/citations/fetch")
def papers_fetch_citation(paper_id: str, request: FetchCitationRequest) -> dict:
    try:
        return fetch_citation_to_misc(arxiv_id=request.arxiv_id, doi=request.doi)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --- Papers ---


@app.get("/papers")
def papers_list() -> list[dict]:
    return [p.model_dump() for p in paper_library.list_papers()]


@app.post("/papers/fetch-starter")
def papers_fetch_starter(limit: int | None = Query(None)) -> dict:
    entries = fetch_starter_papers(limit=limit)
    return {"count": len(entries), "papers": entries}


@app.post("/papers/fetch-real-world-learning")
def papers_fetch_real_world_learning(force: bool = Query(False)) -> dict:
    entries = fetch_real_world_learning_papers(force=force)
    category = ensure_real_world_learning_category()
    return {"count": len(entries), "papers": entries, "category": category}


@app.get("/papers/{paper_id}", response_model=PaperDocument)
def papers_get(paper_id: str) -> PaperDocument:
    doc = paper_library.get_paper(paper_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    return doc


@app.post("/papers/{paper_id}/parse", response_model=PaperDocument)
def papers_parse(paper_id: str, force: bool = False) -> PaperDocument:
    manifest = load_manifest()
    entry = next((e for e in manifest.get("papers", []) if e["paper_id"] == paper_id), None)
    if not entry or entry.get("pdf_status") != "available":
        raise HTTPException(status_code=404, detail=f"PDF unavailable for {paper_id}")
    if not force and load_parsed(paper_id):
        doc = paper_library.get_paper(paper_id)
        assert doc
        return doc
    return parse_paper(
        Path(entry["pdf_path"]),
        paper_id=paper_id,
        title=entry.get("title", paper_id),
        authors=entry.get("authors"),
        year=entry.get("year"),
        arxiv_id=entry.get("arxiv_id"),
        abstract=entry.get("abstract"),
        force=force,
    )


@app.post("/papers/{paper_id}/annotate", response_model=PaperDocument)
def papers_annotate(paper_id: str, request: AnnotatePaperRequest) -> PaperDocument:
    doc = load_parsed(paper_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Parse the paper first")
    try:
        annotator = PaperAnnotator(lens=request.lens, max_candidates=request.max_candidates)
        return annotator.annotate(doc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/papers/{paper_id}/annotations", response_model=PaperDocument)
def papers_create_annotation(paper_id: str, request: CreatePaperAnnotationRequest) -> PaperDocument:
    try:
        return create_annotation(
            paper_id,
            block_id=request.block_id,
            annotation_text=request.annotation_text,
            annotation_type=request.annotation_type,
            quote=request.quote,
            lens=request.lens,
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/papers/{paper_id}/annotations/{annotation_id}", response_model=PaperDocument)
def papers_update_annotation(
    paper_id: str,
    annotation_id: str,
    request: UpdatePaperAnnotationRequest,
) -> PaperDocument:
    try:
        return update_annotation(
            paper_id,
            annotation_id,
            annotation_text=request.annotation_text,
            annotation_type=request.annotation_type,
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/papers/{paper_id}/annotations/{annotation_id}", response_model=PaperDocument)
def papers_delete_annotation(paper_id: str, annotation_id: str) -> PaperDocument:
    try:
        return delete_annotation(paper_id, annotation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/papers/{paper_id}/annotations/{annotation_id}/chat")
def papers_annotation_chat(
    paper_id: str,
    annotation_id: str,
    request: PaperAnnotationChatRequest,
) -> dict:
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")
    try:
        doc, reply = chat_on_annotation(paper_id, annotation_id, message=request.message)
        return {"document": doc.model_dump(), "reply": reply.model_dump()}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _bbox_from_request(req: PaperBBoxRequest | None) -> BBox | None:
    if not req:
        return None
    return BBox(x0=req.x0, y0=req.y0, x1=req.x1, y1=req.y1)


@app.post("/papers/{paper_id}/annotations/highlight", response_model=PaperDocument)
def papers_highlight_selection(paper_id: str, request: PaperHighlightRequest) -> PaperDocument:
    try:
        return create_highlight(
            paper_id,
            page=request.page,
            quote=request.quote,
            block_id=request.block_id,
            bbox=_bbox_from_request(request.bbox),
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/papers/{paper_id}/annotations/from-selection", response_model=PaperDocument)
def papers_annotate_selection(paper_id: str, request: PaperTextSelectionRequest) -> PaperDocument:
    if not request.quote.strip():
        raise HTTPException(status_code=400, detail="Selection text is required")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question is required for annotation")
    try:
        return annotate_text_selection(
            paper_id,
            page=request.page,
            quote=request.quote,
            question=request.question,
            block_id=request.block_id,
            bbox=_bbox_from_request(request.bbox),
            lens=request.lens,
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/papers/{paper_id}/annotations/from-region", response_model=PaperDocument)
def papers_annotate_region(paper_id: str, request: PaperRegionSelectionRequest) -> PaperDocument:
    bbox = _bbox_from_request(request.bbox)
    if not bbox:
        raise HTTPException(status_code=400, detail="Region bbox is required")
    try:
        return annotate_region_selection(
            paper_id,
            page=request.page,
            bbox=bbox,
            question=request.question,
            lens=request.lens,
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/papers/{paper_id}/pdf")
def papers_pdf(paper_id: str) -> FileResponse:
    pdf_path = paper_library.get_pdf_path(paper_id)
    if not pdf_path or not Path(pdf_path).exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{paper_id}.pdf")


@app.get("/papers/{paper_id}/pages/{page_num}.png")
def papers_page_image(paper_id: str, page_num: int) -> FileResponse:
    image_path = PAPER_PAGES_DIR / paper_id / f"page_{page_num:03d}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found. Parse the paper first.")
    return FileResponse(image_path, media_type="image/png")


@app.get("/papers/{paper_id}/figures/{block_id}.png")
def papers_figure_crop(paper_id: str, block_id: str) -> FileResponse:
    image_path = PAPER_FIGURES_DIR / paper_id / f"{block_id}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Figure crop not found")
    return FileResponse(image_path, media_type="image/png")
