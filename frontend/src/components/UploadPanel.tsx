import { useState } from "react";
import type { AnnotationDepth } from "../types";

interface UploadPanelProps {
  onSubmit: (text: string, mode: AnnotationDepth, title?: string) => Promise<void>;
  onLoadSample: () => void;
  loading: boolean;
  error: string | null;
}

export function UploadPanel({ onSubmit, onLoadSample, loading, error }: UploadPanelProps) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState<AnnotationDepth>("medium");

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-3xl flex-col justify-center px-6 py-12">
      <div className="mb-8 text-center">
        <h1 className="font-serif text-4xl font-semibold text-[var(--ink)]">
          Turn speeches into readable, annotated documents
        </h1>
        <p className="mt-3 text-[var(--muted)]">
          Paste a transcript. SpeechLens adds source-backed context without rewriting the speech.
        </p>
      </div>

      <div className="rounded-xl border border-[var(--border)] bg-white p-6 shadow-sm">
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
          rows={12}
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

        {error && (
          <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
        )}

        <div className="flex flex-wrap gap-3">
          <button
            disabled={!text.trim() || loading}
            onClick={() => onSubmit(text, mode, title || undefined)}
            className="rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {loading ? "Annotating…" : "Annotate transcript"}
          </button>
          <button
            type="button"
            onClick={onLoadSample}
            className="rounded-md border border-[var(--border)] px-5 py-2.5 text-sm font-medium hover:bg-gray-50"
          >
            View sample (no API key)
          </button>
        </div>
      </div>
    </div>
  );
}
