import { useEffect, useState } from "react";
import type { CatalogDocument, Category } from "../catalogApi";
import { fetchCategoryDocuments, moveDocument } from "../catalogApi";

interface DocumentBrowserProps {
  categoryId: string | null;
  categories: Category[];
  onOpenSpeech: (sourceId: string, slug: string) => void;
  onOpenPaper: (paperId: string) => void;
}

export function DocumentBrowser({
  categoryId,
  categories,
  onOpenSpeech,
  onOpenPaper,
}: DocumentBrowserProps) {
  const [documents, setDocuments] = useState<CatalogDocument[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    if (!categoryId) return;
    setLoading(true);
    setError(null);
    fetchCategoryDocuments(categoryId, search)
      .then(setDocuments)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, [categoryId, search]);

  const handleMove = async (doc: CatalogDocument, newCategoryId: string) => {
    if (newCategoryId === doc.category_id) return;
    try {
      await moveDocument(doc.doc_id, newCategoryId);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Move failed");
    }
  };

  if (!categoryId) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-[var(--muted)]">
        Select a category
      </div>
    );
  }

  const catName = categories.find((c) => c.id === categoryId)?.name ?? categoryId;

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="border-b border-[var(--border)] bg-white px-6 py-4">
        <h2 className="text-lg font-semibold">{catName}</h2>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search documents in this category…"
          className="mt-3 w-full max-w-md rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
        />
      </div>

      {error && (
        <p className="border-b border-red-100 bg-red-50 px-6 py-2 text-sm text-red-800">{error}</p>
      )}

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {loading ? (
          <p className="text-sm text-[var(--muted)]">Loading…</p>
        ) : documents.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No documents in this category.</p>
        ) : (
          <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] bg-white">
            {documents.map((doc) => (
              <li key={doc.doc_id} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{doc.title}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {doc.kind === "paper" ? `Paper · ${doc.arxiv_id ?? doc.paper_id}` : "Speech"}
                    {doc.snippet && (
                      <span className="ml-2 italic">…{doc.snippet.slice(0, 80)}…</span>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <select
                    value={doc.category_id}
                    onChange={(e) => handleMove(doc, e.target.value)}
                    className="rounded border border-[var(--border)] px-2 py-1 text-xs"
                    title="Move to category"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => {
                      if (doc.kind === "speech" && doc.source_id && doc.slug) {
                        onOpenSpeech(doc.source_id, doc.slug);
                      } else if (doc.kind === "paper" && doc.paper_id) {
                        onOpenPaper(doc.paper_id);
                      }
                    }}
                    className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white"
                  >
                    Open
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
