from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response

from catalog.store import search_paper
from backend.app.paper_schemas import (
    AnnotatePaperRequest,
    CreatePaperAnnotationRequest,
    PaperAnnotationChatRequest,
    PaperHighlightRequest,
    PaperRegionSelectionRequest,
    PaperTextSelectionRequest,
    UpdatePaperAnnotationRequest,
    bbox_from_request,
)
from paperlens.annotate import PaperAnnotator, load_parsed
from paperlens.export import export_annotated_pdf, export_json, export_markdown
from paperlens.models import PaperDocument
from paperlens.paths import PAPER_FIGURES_DIR, PAPER_PAGES_DIR
from paperlens.session import (
    create_session_from_upload,
    get_public_paper,
    is_public_session,
    public_pdf_path,
)
from paperlens.storage import (
    annotate_region_selection,
    annotate_text_selection,
    chat_on_annotation,
    create_annotation,
    create_highlight,
    delete_annotation,
    update_annotation,
)

router = APIRouter()


def _require_public_paper(paper_id: str) -> PaperDocument:
    if not is_public_session(paper_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {paper_id}")
    doc = get_public_paper(paper_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")
    return doc


@router.post("/upload", response_model=PaperDocument)
async def public_upload(file: UploadFile) -> PaperDocument:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    try:
        content = await file.read()
        return create_session_from_upload(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/papers/{paper_id}", response_model=PaperDocument)
def public_get_paper(paper_id: str) -> PaperDocument:
    return _require_public_paper(paper_id)


@router.post("/papers/{paper_id}/annotate", response_model=PaperDocument)
def public_annotate_paper(paper_id: str, request: AnnotatePaperRequest) -> PaperDocument:
    _require_public_paper(paper_id)
    doc = load_parsed(paper_id)
    if not doc:
        raise HTTPException(status_code=400, detail="Paper not parsed")
    try:
        annotator = PaperAnnotator(lens=request.lens, max_candidates=request.max_candidates)
        return annotator.annotate(doc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/papers/{paper_id}/annotations", response_model=PaperDocument)
def public_create_annotation(paper_id: str, request: CreatePaperAnnotationRequest) -> PaperDocument:
    _require_public_paper(paper_id)
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


@router.patch("/papers/{paper_id}/annotations/{annotation_id}", response_model=PaperDocument)
def public_update_annotation(
    paper_id: str,
    annotation_id: str,
    request: UpdatePaperAnnotationRequest,
) -> PaperDocument:
    _require_public_paper(paper_id)
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


@router.delete("/papers/{paper_id}/annotations/{annotation_id}", response_model=PaperDocument)
def public_delete_annotation(paper_id: str, annotation_id: str) -> PaperDocument:
    _require_public_paper(paper_id)
    try:
        return delete_annotation(paper_id, annotation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/papers/{paper_id}/annotations/{annotation_id}/chat")
def public_annotation_chat(
    paper_id: str,
    annotation_id: str,
    request: PaperAnnotationChatRequest,
) -> dict:
    _require_public_paper(paper_id)
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


@router.post("/papers/{paper_id}/annotations/highlight", response_model=PaperDocument)
def public_highlight(paper_id: str, request: PaperHighlightRequest) -> PaperDocument:
    _require_public_paper(paper_id)
    try:
        return create_highlight(
            paper_id,
            page=request.page,
            quote=request.quote,
            block_id=request.block_id,
            bbox=bbox_from_request(request.bbox),
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/papers/{paper_id}/annotations/from-selection", response_model=PaperDocument)
def public_annotate_selection(paper_id: str, request: PaperTextSelectionRequest) -> PaperDocument:
    _require_public_paper(paper_id)
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
            bbox=bbox_from_request(request.bbox),
            lens=request.lens,
            color=request.color,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/papers/{paper_id}/annotations/from-region", response_model=PaperDocument)
def public_annotate_region(paper_id: str, request: PaperRegionSelectionRequest) -> PaperDocument:
    _require_public_paper(paper_id)
    bbox = bbox_from_request(request.bbox)
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


@router.get("/papers/{paper_id}/search")
def public_search_paper(paper_id: str, q: str = "") -> dict:
    _require_public_paper(paper_id)
    return search_paper(paper_id, q)


@router.get("/papers/{paper_id}/export")
def public_export(paper_id: str, format: str = "markdown") -> Response:
    doc = _require_public_paper(paper_id)
    if format == "json":
        return Response(
            content=export_json(doc),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{paper_id}.json"'},
        )
    if format == "markdown":
        return PlainTextResponse(
            content=export_markdown(doc),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{paper_id}.md"'},
        )
    if format == "pdf":
        pdf_path = public_pdf_path(paper_id) or doc.paper.pdf_path
        if not pdf_path:
            raise HTTPException(status_code=404, detail="Source PDF not found")
        try:
            content = export_annotated_pdf(doc, pdf_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        safe_name = (doc.paper.title or paper_id)[:80].replace('"', "")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}-annotated.pdf"'
            },
        )
    raise HTTPException(status_code=400, detail="format must be markdown, json, or pdf")


@router.get("/papers/{paper_id}/pdf")
def public_pdf(paper_id: str) -> FileResponse:
    path = public_pdf_path(paper_id)
    if not path:
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, media_type="application/pdf", filename=f"{paper_id}.pdf")


@router.get("/papers/{paper_id}/pages/{page_num}.png")
def public_page_image(paper_id: str, page_num: int) -> FileResponse:
    if not is_public_session(paper_id):
        raise HTTPException(status_code=404, detail="Session not found")
    image_path = PAPER_PAGES_DIR / paper_id / f"page_{page_num:03d}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Page image not found")
    return FileResponse(image_path, media_type="image/png")


@router.get("/papers/{paper_id}/figures/{block_id}.png")
def public_figure_crop(paper_id: str, block_id: str) -> FileResponse:
    if not is_public_session(paper_id):
        raise HTTPException(status_code=404, detail="Session not found")
    image_path = PAPER_FIGURES_DIR / paper_id / f"{block_id}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Figure crop not found")
    return FileResponse(image_path, media_type="image/png")
