import { useEffect, useMemo, useState } from "react";
import type { LibrarySource, LibrarySpeech } from "../api";
import { fetchLibrarySources, fetchLibrarySpeeches } from "../api";
import type { AnnotationDepth } from "../types";

interface LibraryPickerProps {
  onRead: (sourceId: string, slug: string) => void;
  onAnnotate: (sourceId: string, slug: string, mode: AnnotationDepth) => void;
  loading: boolean;
}

export function LibraryPicker({ onRead, onAnnotate, loading }: LibraryPickerProps) {
  const [sources, setSources] = useState<LibrarySource[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [speeches, setSpeeches] = useState<LibrarySpeech[]>([]);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<AnnotationDepth>("light");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchLibrarySources()
      .then((data) => {
        setSources(data);
        if (data[0]) setSourceId(data[0].source_id);
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load library"));
  }, []);

  useEffect(() => {
    if (!sourceId) return;
    const timer = setTimeout(() => {
      fetchLibrarySpeeches(sourceId, search)
        .then(setSpeeches)
        .catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load speeches"));
    }, search ? 200 : 0);
    return () => clearTimeout(timer);
  }, [sourceId, search]);

  const activeSource = useMemo(
    () => sources.find((s) => s.source_id === sourceId),
    [sources, sourceId],
  );

  if (loadError && sources.length === 0) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Library unavailable ({loadError}). Start the API:{" "}
        <code className="rounded bg-white px-1">uvicorn backend.app.main:app --reload</code>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Seeded library</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {activeSource
              ? `${activeSource.speeches_count} speeches extracted · ${activeSource.annotated_count} annotated`
              : "Pick a seeded collection"}
          </p>
        </div>
        {sources.length > 1 && (
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="rounded-md border border-[var(--border)] px-3 py-2 text-sm"
          >
            {sources.map((s) => (
              <option key={s.source_id} value={s.source_id}>
                {s.title}
              </option>
            ))}
          </select>
        )}
      </div>

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search speeches… e.g. grassroots, ballot, oxford"
        className="mb-4 w-full rounded-md border border-[var(--border)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
      />

      <div className="mb-4 flex items-center gap-3">
        <span className="text-sm font-medium text-[var(--muted)]">Annotate depth</span>
        {(["light", "medium", "dense"] as AnnotationDepth[]).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setMode(d)}
            className={`rounded-full px-3 py-1 text-sm capitalize ${
              mode === d
                ? "bg-[var(--accent)] text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="max-h-80 overflow-y-auto rounded-lg border border-[var(--border)]">
        {speeches.length === 0 ? (
          <p className="p-4 text-sm text-[var(--muted)]">No speeches match your search.</p>
        ) : (
          <ul className="divide-y divide-[var(--border)]">
            {speeches.map((speech) => (
              <li
                key={speech.slug}
                className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{speech.title}</p>
                  <p className="text-xs text-[var(--muted)]">
                    pp. {speech.start_page}–{speech.end_page}
                    {speech.has_annotations && (
                      <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-700">
                        annotated
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => onRead(sourceId, speech.slug)}
                    className="rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium hover:bg-white disabled:opacity-50"
                  >
                    Read
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => onAnnotate(sourceId, speech.slug, mode)}
                    className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
                  >
                    {speech.has_annotations ? "Re-annotate" : "Annotate"}
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
