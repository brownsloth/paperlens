import type { AnnotateResponse, AnnotationDepth } from "./types";

const API = "/api";

export interface LibrarySource {
  source_id: string;
  title: string;
  speeches_count: number;
  annotated_count: number;
  input_path?: string;
}

export interface LibrarySpeech {
  slug: string;
  title: string;
  chars: number;
  start_page?: number;
  end_page?: number;
  has_annotations: boolean;
}

export async function fetchSample(): Promise<AnnotateResponse> {
  const res = await fetch(`${API}/sample`);
  if (!res.ok) throw new Error("Failed to load sample document");
  return res.json();
}

export async function fetchLibrarySources(): Promise<LibrarySource[]> {
  const res = await fetch(`${API}/library/sources`);
  if (!res.ok) throw new Error("Failed to load library sources");
  return res.json();
}

export async function fetchLibrarySpeeches(
  sourceId: string,
  search = "",
): Promise<LibrarySpeech[]> {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  const res = await fetch(`${API}/library/${sourceId}/speeches${params}`);
  if (!res.ok) throw new Error("Failed to load speeches");
  return res.json();
}

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg ?? String(d)).join("; ");
  return fallback;
}

export async function fetchLibrarySpeech(
  sourceId: string,
  slug: string,
): Promise<AnnotateResponse> {
  const res = await fetch(`${API}/library/${sourceId}/speeches/${slug}`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load speech"));
  return res.json();
}

export async function annotateLibrarySpeech(
  sourceId: string,
  slug: string,
  mode: AnnotationDepth,
  options?: { requireSources?: boolean; enableWebSearch?: boolean },
): Promise<AnnotateResponse> {
  const res = await fetch(`${API}/library/${sourceId}/speeches/${slug}/annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      mode,
      require_sources: options?.requireSources ?? true,
      enable_web_search: options?.enableWebSearch ?? true,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Annotation failed");
  }
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
