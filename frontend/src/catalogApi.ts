import { apiPrefix } from "./apiBase";

export interface Category {
  id: string;
  name: string;
  document_count: number;
}

export interface CatalogDocument {
  doc_id: string;
  category_id: string;
  kind: "speech" | "paper";
  title: string;
  source_id?: string;
  slug?: string;
  paper_id?: string;
  arxiv_id?: string;
  match?: string;
  snippet?: string;
}

export interface PaperSearchResult {
  blocks: { block_id: string; page: number; text: string; snippet: string }[];
  annotations: { annotation_id: string; page?: number; annotation_text: string; quote?: string }[];
}

export interface CitationEntry {
  citation_id: string;
  text: string;
  block_id: string;
  page: number;
  arxiv_id?: string;
  doi?: string;
  downloadable: boolean;
}

async function errorDetail(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => ({}));
  return typeof err.detail === "string" ? err.detail : fallback;
}

export async function fetchCategories(): Promise<Category[]> {
  const res = await fetch(`${apiPrefix()}/categories`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load categories"));
  return res.json();
}

export async function createCategory(name: string): Promise<Category> {
  const res = await fetch(`${apiPrefix()}/categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to create category"));
  return res.json();
}

export async function fetchCategoryDocuments(
  categoryId: string,
  search = "",
): Promise<CatalogDocument[]> {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  const res = await fetch(`${apiPrefix()}/categories/${categoryId}/documents${params}`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load documents"));
  return res.json();
}

export async function moveDocument(docId: string, categoryId: string): Promise<CatalogDocument> {
  const res = await fetch(`${apiPrefix()}/documents/${docId}/category`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category_id: categoryId }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to move document"));
  return res.json();
}

export async function searchPaper(paperId: string, q: string): Promise<PaperSearchResult> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error(await errorDetail(res, "Search failed"));
  return res.json();
}

export async function fetchPaperCitations(paperId: string): Promise<CitationEntry[]> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/citations`);
  if (!res.ok) throw new Error(await errorDetail(res, "Failed to load citations"));
  return res.json();
}

export async function downloadCitation(arxivId?: string, doi?: string): Promise<void> {
  const res = await fetch(`${apiPrefix()}/papers/_/citations/fetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ arxiv_id: arxivId, doi }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Download failed"));
}

export async function downloadCitationFromPaper(
  paperId: string,
  arxivId?: string,
  doi?: string,
): Promise<{ paper: Record<string, unknown>; document: CatalogDocument }> {
  const res = await fetch(`${apiPrefix()}/papers/${paperId}/citations/fetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ arxiv_id: arxivId, doi }),
  });
  if (!res.ok) throw new Error(await errorDetail(res, "Download failed"));
  return res.json();
}
