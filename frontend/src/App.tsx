import { useCallback, useEffect, useState } from "react";
import { fetchLibrarySpeech } from "./api";
import { fetchCategories, type Category } from "./catalogApi";
import { fetchPaper, parsePaper } from "./paperApi";
import { CategoriesSidebar } from "./components/CategoriesSidebar";
import { DocumentBrowser } from "./components/DocumentBrowser";
import { Header } from "./components/Header";
import { PaperAnnotationPanel } from "./components/PaperAnnotationPanel";
import { PaperReader } from "./components/PaperReader";
import { SpeechReader } from "./components/SpeechReader";
import type { PaperDocument } from "./paperTypes";
import type { AnnotateResponse } from "./types";

type View = "home" | "speech" | "paper";

export default function App() {
  const [view, setView] = useState<View>("home");
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);
  const [speech, setSpeech] = useState<AnnotateResponse | null>(null);
  const [paper, setPaper] = useState<PaperDocument | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingLabel, setLoadingLabel] = useState("");

  const refreshCategories = useCallback(() => {
    fetchCategories()
      .then((cats) => {
        setCategories(cats);
        if (!activeCategoryId && cats.length) setActiveCategoryId(cats[0].id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load categories"));
  }, [activeCategoryId]);

  useEffect(() => {
    refreshCategories();
  }, []);

  const openSpeech = useCallback((doc: AnnotateResponse) => {
    setSpeech(doc);
    setPaper(null);
    setActiveId(null);
    setView("speech");
    setError(null);
  }, []);

  const openPaper = useCallback((doc: PaperDocument) => {
    setPaper(doc);
    setSpeech(null);
    setActiveId(doc.annotations[0]?.annotation_id ?? null);
    setView("paper");
    setError(null);
  }, []);

  const handleOpenSpeech = async (sourceId: string, slug: string) => {
    setLoading(true);
    setLoadingLabel("Loading speech…");
    setError(null);
    try {
      const doc = await fetchLibrarySpeech(sourceId, slug);
      openSpeech(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load speech");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const handleOpenPaper = async (paperId: string) => {
    setLoading(true);
    setLoadingLabel("Loading paper…");
    setError(null);
    try {
      let doc = await fetchPaper(paperId);
      if (!doc.pages.length) {
        setLoadingLabel("Parsing PDF…");
        doc = await parsePaper(paperId);
      }
      openPaper(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load paper");
    } finally {
      setLoading(false);
      setLoadingLabel("");
    }
  };

  const title = view === "paper" ? paper?.paper.title : view === "speech" ? speech?.title : undefined;

  return (
    <div className="flex h-full flex-col">
      <Header
        onHome={() => setView("home")}
        showNav={view !== "home"}
        documentTitle={title}
      />

      {loading && (
        <div className="border-b border-[var(--accent-soft)] bg-[var(--accent-soft)] px-4 py-2 text-center text-sm text-[var(--accent)]">
          {loadingLabel}
        </div>
      )}

      {error && view === "home" && (
        <p className="border-b border-red-100 bg-red-50 px-4 py-2 text-center text-sm text-red-800">
          {error}
        </p>
      )}

      {view === "home" ? (
        <div className="flex min-h-0 flex-1">
          <CategoriesSidebar
            categories={categories}
            activeId={activeCategoryId}
            onSelect={setActiveCategoryId}
            onCreated={refreshCategories}
          />
          <DocumentBrowser
            categoryId={activeCategoryId}
            categories={categories}
            onOpenSpeech={handleOpenSpeech}
            onOpenPaper={handleOpenPaper}
          />
        </div>
      ) : view === "speech" && speech ? (
        <div className="flex min-h-0 flex-1">
          <aside className="w-80 shrink-0 border-r border-[var(--border)] bg-white p-4">
            <h2 className="text-sm font-semibold">Speech</h2>
            <p className="mt-2 text-xs text-[var(--muted)]">
              Read and select text. Add annotations from the transcript as you read.
            </p>
          </aside>
          <SpeechReader
            document={speech}
            activeId={activeId}
            onSelect={setActiveId}
            onMarkerPositions={() => {}}
          />
        </div>
      ) : view === "paper" && paper ? (
        <div className="flex min-h-0 flex-1">
          <PaperAnnotationPanel
            document={paper}
            annotations={paper.annotations}
            activeId={activeId}
            onSelect={setActiveId}
            onDocumentChange={(doc) => {
              setPaper(doc);
              if (doc.annotations.length && !doc.annotations.some((a) => a.annotation_id === activeId)) {
                setActiveId(doc.annotations[0]?.annotation_id ?? null);
              }
            }}
            categories={categories}
            onCitationDownloaded={refreshCategories}
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
