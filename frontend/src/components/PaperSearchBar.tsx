import { useEffect, useState } from "react";
import { searchPaper, type PaperSearchResult } from "../catalogApi";

interface PaperSearchBarProps {
  paperId: string;
  onSelectAnnotation: (id: string) => void;
  onJumpToPage: (page: number) => void;
}

export function PaperSearchBar({ paperId, onSelectAnnotation, onJumpToPage }: PaperSearchBarProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PaperSearchResult | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    const t = setTimeout(() => {
      searchPaper(paperId, query)
        .then(setResults)
        .catch(() => setResults({ blocks: [], annotations: [] }));
    }, 250);
    return () => clearTimeout(t);
  }, [paperId, query]);

  const total = (results?.blocks.length ?? 0) + (results?.annotations.length ?? 0);

  return (
    <div className="relative mx-auto max-w-4xl pb-2">
      <input
        type="search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        placeholder="Search this paper (text & annotations)…"
        className="w-full rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-sm shadow-sm"
      />
      {open && query.trim() && results && (
        <div className="absolute left-0 right-0 z-20 mt-1 max-h-64 overflow-y-auto rounded-lg border border-[var(--border)] bg-white shadow-lg">
          {total === 0 ? (
            <p className="px-3 py-2 text-xs text-[var(--muted)]">No matches</p>
          ) : (
            <>
              {results.annotations.map((a) => (
                <button
                  key={a.annotation_id}
                  type="button"
                  className="block w-full border-b border-[var(--border)] px-3 py-2 text-left text-xs hover:bg-gray-50"
                  onClick={() => {
                    onSelectAnnotation(a.annotation_id);
                    if (a.page) onJumpToPage(a.page);
                    setOpen(false);
                  }}
                >
                  <span className="font-medium text-[var(--accent)]">Annotation</span>
                  {a.page && <span className="ml-2 text-[var(--muted)]">p.{a.page}</span>}
                  <p className="mt-0.5 line-clamp-2 text-[var(--ink)]">{a.annotation_text}</p>
                </button>
              ))}
              {results.blocks.map((b) => (
                <button
                  key={b.block_id}
                  type="button"
                  className="block w-full border-b border-[var(--border)] px-3 py-2 text-left text-xs hover:bg-gray-50"
                  onClick={() => {
                    onJumpToPage(b.page);
                    setOpen(false);
                  }}
                >
                  <span className="font-medium">Text</span>
                  <span className="ml-2 text-[var(--muted)]">p.{b.page}</span>
                  <p className="mt-0.5 line-clamp-2 text-[var(--ink)]">{b.snippet}</p>
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
