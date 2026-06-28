import { useEffect, useState } from "react";
import type { PaperLens, PaperMeta } from "../paperTypes";
import { annotatePaper, fetchPapers, fetchStarterPapers, parsePaper, fetchPaper } from "../paperApi";

interface PaperPickerProps {
  onOpen: (paperId: string) => void;
  onAnnotated: (paperId: string) => void;
  loading: boolean;
}

const LENSES: PaperLens[] = ["beginner", "implementation", "math", "historical", "lineage"];

export function PaperPicker({ onOpen, onAnnotated, loading }: PaperPickerProps) {
  const [papers, setPapers] = useState<PaperMeta[]>([]);
  const [lens, setLens] = useState<PaperLens>("beginner");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    fetchPapers()
      .then(setPapers)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load papers"));
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleFetchStarter = async () => {
    setBusy(true);
    setError(null);
    try {
      await fetchStarterPapers();
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fetch failed");
    } finally {
      setBusy(false);
    }
  };

  const handleParse = async (paperId: string) => {
    setBusy(true);
    setError(null);
    try {
      await parsePaper(paperId);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Parse failed");
    } finally {
      setBusy(false);
    }
  };

  const handleAnnotate = async (paperId: string) => {
    setBusy(true);
    setError(null);
    try {
      let doc = await fetchPaper(paperId);
      if (!doc.pages.length) {
        doc = await parsePaper(paperId);
      }
      await annotatePaper(paperId, lens);
      onAnnotated(paperId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Annotate failed");
    } finally {
      setBusy(false);
    }
  };

  const disabled = loading || busy;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Research papers (PaperLens)</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Schmidhuber starter corpus · block-anchored PDF annotations
          </p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={handleFetchStarter}
          className="shrink-0 rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
        >
          Fetch starter PDFs
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-[var(--muted)]">Lens</span>
        {LENSES.map((l) => (
          <button
            key={l}
            type="button"
            onClick={() => setLens(l)}
            className={`rounded-full px-3 py-1 text-xs capitalize ${
              lens === l
                ? "bg-[var(--accent)] text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {papers.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">
          No papers yet. Click &quot;Fetch starter PDFs&quot; (downloads verified Schmidhuber papers from arXiv).
        </p>
      ) : (
        <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)]">
          {papers.map((paper) => (
            <li
              key={paper.paper_id}
              className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{paper.title}</p>
                <p className="text-xs text-[var(--muted)]">
                  {paper.arxiv_id && `arXiv:${paper.arxiv_id} · `}
                  {paper.page_count ? `${paper.page_count} pp · ` : ""}
                  {paper.pdf_status}
                  {paper.has_annotations && (
                    <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                      annotated
                    </span>
                  )}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                {!paper.block_count && paper.pdf_status === "available" && (
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => handleParse(paper.paper_id)}
                    className="rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium disabled:opacity-50"
                  >
                    Parse
                  </button>
                )}
                <button
                  type="button"
                  disabled={disabled || paper.pdf_status !== "available"}
                  onClick={() => onOpen(paper.paper_id)}
                  className="rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                >
                  Read
                </button>
                <button
                  type="button"
                  disabled={disabled || paper.pdf_status !== "available"}
                  onClick={() => handleAnnotate(paper.paper_id)}
                  className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                >
                  Annotate
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
