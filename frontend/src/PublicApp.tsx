import { useCallback, useRef, useState } from "react";
import { PaperAnnotationPanel } from "./components/PaperAnnotationPanel";
import { PaperReader } from "./components/PaperReader";
import { Header } from "./components/Header";
import { exportPaperUrl, uploadPdf } from "./publicApi";
import type { PaperDocument } from "./paperTypes";

type View = "home" | "paper";

export default function PublicApp() {
  const [view, setView] = useState<View>("home");
  const [paper, setPaper] = useState<PaperDocument | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const openPaper = useCallback((doc: PaperDocument) => {
    setPaper(doc);
    setActiveId(doc.annotations[0]?.annotation_id ?? null);
    setView("paper");
    setError(null);
  }, []);

  const handleUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const doc = await uploadPdf(file);
      openPaper(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <Header
        onHome={() => {
          setView("home");
          setPaper(null);
          setActiveId(null);
        }}
        showNav={view !== "home"}
        documentTitle={paper?.paper.title}
      />

      {view === "home" ? (
        <div className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-6 py-12">
          <div className="text-center">
            <h1 className="font-serif text-4xl font-semibold text-[var(--ink)]">PaperLens</h1>
            <p className="mt-3 text-[var(--muted)]">
              Upload a PDF, highlight and annotate text or regions, export your notes. Nothing is
              saved to a library — this session is ephemeral.
            </p>
          </div>

          {error && (
            <p className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </p>
          )}

          <img
            src={`${import.meta.env.BASE_URL}supermeme_14h6_2.png`}
            alt="Let's make reading papers great again"
            className="mx-auto mt-8 w-full max-w-md rounded-lg shadow-sm"
          />

          <div
            className="mt-8 rounded-xl border-2 border-dashed border-[var(--border)] bg-white p-10 text-center shadow-sm"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) void handleUpload(file);
            }}
          >
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUpload(file);
              }}
            />
            <p className="text-sm text-[var(--muted)]">Drop a PDF here or</p>
            <button
              type="button"
              disabled={loading}
              onClick={() => fileRef.current?.click()}
              className="mt-4 rounded-md bg-[var(--accent)] px-6 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {loading ? "Parsing PDF…" : "Choose PDF"}
            </button>
          </div>

          <p className="mt-6 text-center text-xs text-[var(--muted)]">
            AI annotations require an API key on the server. Highlights and manual notes work
            offline.
          </p>
        </div>
      ) : paper ? (
        <div className="flex min-h-0 flex-1">
          <PaperAnnotationPanel
            document={paper}
            annotations={paper.annotations}
            activeId={activeId}
            onSelect={setActiveId}
            onDocumentChange={setPaper}
            publicMode
            exportPdfUrl={exportPaperUrl(paper.paper.paper_id, "pdf")}
          />
          <PaperReader
            document={paper}
            activeId={activeId}
            onSelect={setActiveId}
            onDocumentChange={setPaper}
          />
        </div>
      ) : null}
    </div>
  );
}
