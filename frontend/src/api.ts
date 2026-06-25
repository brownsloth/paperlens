import type { AnnotateResponse } from "./types";

const API = "/api";

export async function fetchSample(): Promise<AnnotateResponse> {
  const res = await fetch(`${API}/sample`);
  if (!res.ok) throw new Error("Failed to load sample document");
  return res.json();
}

export async function annotateText(
  text: string,
  mode: string,
  title?: string,
): Promise<AnnotateResponse> {
  const res = await fetch(`${API}/annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, mode, require_sources: true, title }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Annotation failed");
  }
  return res.json();
}
