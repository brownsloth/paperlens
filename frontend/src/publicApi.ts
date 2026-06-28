import type { PaperDocument } from "./paperTypes";
import { apiPrefix } from "./apiBase";
import {
  annotateFromRegion,
  annotateFromSelection,
  annotatePaper,
  chatOnPaperAnnotation,
  createPaperAnnotation,
  deletePaperAnnotation,
  fetchPaper,
  highlightSelection,
  updatePaperAnnotation,
} from "./paperApi";

export async function uploadPdf(file: File): Promise<PaperDocument> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${apiPrefix()}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === "string" ? err.detail : "Upload failed");
  }
  return res.json();
}

export async function reloadPaper(paperId: string): Promise<PaperDocument> {
  return fetchPaper(paperId);
}

export function exportPaperUrl(paperId: string, format: "markdown" | "json" | "pdf"): string {
  return `${apiPrefix()}/papers/${paperId}/export?format=${format}`;
}

export async function runBulkAiAnnotate(paperId: string): Promise<PaperDocument> {
  return annotatePaper(paperId, "beginner", 12);
}

export {
  annotateFromRegion,
  annotateFromSelection,
  chatOnPaperAnnotation,
  createPaperAnnotation,
  deletePaperAnnotation,
  highlightSelection,
  updatePaperAnnotation,
};
