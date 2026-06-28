import type { PaperDocument, PaperLens, PaperMeta, BBox } from "./paperTypes";
import { apiPrefix } from "./apiBase";

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  return fallback;
}

export async function fetchPapers(): Promise<PaperMeta[]> {
  const res = await fetch(`${apiPrefix()}/papers`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load papers"));
  return res.json();
}

export async function fetchStarterPapers(limit?: number): Promise<void> {
  const params = limit ? `?limit=${limit}` : "";
  const res = await fetch(`${apiPrefix()}/papers/fetch-starter${params}`, { method: "POST" });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to fetch papers"));
}

export async function fetchPaper(paperId: string): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load paper"));
  return res.json();
}

export async function parsePaper(paperId: string): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/parse`, { method: "POST" });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to parse paper"));
  return res.json();
}

export async function annotatePaper(
  paperId: string,
  lens: PaperLens,
  maxCandidates = 12,
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lens, max_candidates: maxCandidates }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Annotation failed"));
  return res.json();
}

export async function createPaperAnnotation(
  paperId: string,
  body: {
    block_id: string;
    annotation_text: string;
    annotation_type?: string;
    quote?: string;
    lens?: PaperLens;
    color?: string;
  },
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to create annotation"));
  return res.json();
}

export async function updatePaperAnnotation(
  paperId: string,
  annotationId: string,
  body: { annotation_text?: string; annotation_type?: string; color?: string },
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/${annotationId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to update annotation"));
  return res.json();
}

export async function deletePaperAnnotation(
  paperId: string,
  annotationId: string,
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/${annotationId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to delete annotation"));
  return res.json();
}

export async function chatOnPaperAnnotation(
  paperId: string,
  annotationId: string,
  message: string,
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/${annotationId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Chat failed"));
  const data = await res.json();
  return data.document as PaperDocument;
}

export function paperPageUrl(paperId: string, page: number): string {
  return `${apiPrefix()}/papers/${paperId}/pages/${page}.png`;
}

export function allAnnotations(doc: PaperDocument) {
  return doc.annotations;
}

/** @deprecated use allAnnotations — references are included */
export function bodyAnnotations(doc: PaperDocument) {
  return doc.annotations;
}

export async function highlightSelection(
  paperId: string,
  body: {
    page: number;
    quote: string;
    block_id?: string;
    bbox?: BBox;
    color?: string;
  },
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/highlight`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to highlight"));
  return res.json();
}

export async function annotateFromSelection(
  paperId: string,
  body: {
    page: number;
    quote: string;
    question: string;
    block_id?: string;
    bbox?: BBox;
    lens?: PaperLens;
    color?: string;
  },
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/from-selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to annotate selection"));
  return res.json();
}

export async function annotateFromRegion(
  paperId: string,
  body: {
    page: number;
    bbox: BBox;
    question: string;
    lens?: PaperLens;
    color?: string;
  },
): Promise<PaperDocument> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/annotations/from-region`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to annotate region"));
  return res.json();
}
