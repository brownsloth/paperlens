from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from speechlens.annotator import SpeechAnnotator
from speechlens.models import AnnotateRequest, AnnotateResponse, AnnotateUrlRequest, Annotation
from speechlens.sample_data import SAMPLE_DOCUMENT

app = FastAPI(
    title="SpeechLens",
    description="Source-grounded agentic annotation for historical speeches",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_documents: dict[str, AnnotateResponse] = {SAMPLE_DOCUMENT.doc_id: SAMPLE_DOCUMENT}


@app.get("/sample", response_model=AnnotateResponse)
def get_sample() -> AnnotateResponse:
    return SAMPLE_DOCUMENT


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
