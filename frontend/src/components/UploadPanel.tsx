import { useState } from "react";
import type { AnnotationDepth } from "../types";
import { LibraryPicker } from "./LibraryPicker";
import { PaperPicker } from "./PaperPicker";

type HomeTab = "speeches" | "papers";

interface UploadPanelProps {
  onSubmit: (text: string, mode: AnnotationDepth, title?: string) => Promise<void>;
  onReadLibrary: (sourceId: string, slug: string) => Promise<void>;
  onAnnotateLibrary: (sourceId: string, slug: string, mode: AnnotationDepth) => Promise<void>;
  onLoadSample: () => void;
  onOpenPaper: (paperId: string) => Promise<void>;
  onPaperAnnotated: (paperId: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export function UploadPanel({
  onSubmit,
  onReadLibrary,
  onAnnotateLibrary,
  onLoadSample,
  onOpenPaper,
  onPaperAnnotated,
  loading,
  error,
}: UploadPanelProps) {
  const [tab, setTab] = useState<HomeTab>("speeches");

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-8 text-center">
        <h1 className="font-serif text-4xl font-semibold text-[var(--ink)]">
          Source-grounded annotation for speeches &amp; papers
        </h1>
        <p className="mt-3 text-[var(--muted)]">
          SpeechLens for transcripts · PaperLens for PDFs with layout-anchored overlays
        </p>
      </div>

      <div className="mb-6 flex justify-center gap-2">
        {(["speeches", "papers"] as HomeTab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-full px-4 py-2 text-sm font-medium capitalize ${
              tab === t
                ? "bg-[var(--accent)] text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {tab === "speeches" ? (
        <>
          <div className="mb-8">
            <LibraryPicker
              onRead={onReadLibrary}
              onAnnotate={onAnnotateLibrary}
              loading={loading}
            />
          </div>
          <details className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
            <summary className="cursor-pointer text-sm font-medium text-[var(--muted)]">
              Or paste a custom transcript
            </summary>
            <PasteForm onSubmit={onSubmit} onLoadSample={onLoadSample} loading={loading} />
          </details>
        </>
      ) : (
        <PaperPicker
          onOpen={onOpenPaper}
          onAnnotated={onPaperAnnotated}
          loading={loading}
        />
      )}
    </div>
  );
}

function PasteForm({
  onSubmit,
  onLoadSample,
  loading,
}: {
  onSubmit: (text: string, mode: AnnotationDepth, title?: string) => Promise<void>;
  onLoadSample: () => void;
  loading: boolean;
}) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<AnnotationDepth>("medium");

  return (
    <div className="mt-4">
      <label className="mb-2 block text-sm font-medium">Title (optional)</label>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Debate between Malcolm X and James Baldwin"
        className="mb-4 w-full rounded-md border border-[var(--border)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
      />

      <label className="mb-2 block text-sm font-medium">Transcript</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={10}
        placeholder={"MALCOLM X:\nYour speech text here…"}
        className="mb-4 w-full resize-y rounded-md border border-[var(--border)] px-3 py-2 font-mono text-sm outline-none focus:border-[var(--accent)]"
      />

      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm font-medium">Depth</label>
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

      <div className="flex flex-wrap gap-3">
        <button
          disabled={!text.trim() || loading}
          onClick={() => onSubmit(text, mode, title || undefined)}
          className="rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Working…" : "Annotate transcript"}
        </button>
        <button
          type="button"
          onClick={onLoadSample}
          className="rounded-md border border-[var(--border)] px-5 py-2.5 text-sm font-medium hover:bg-gray-50"
        >
          View hardcoded demo
        </button>
      </div>
    </div>
  );
}
