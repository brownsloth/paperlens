import { useCallback, useEffect, useState } from "react";
import { annotateText, fetchSample } from "./api";
import { Header } from "./components/Header";
import { AnnotationPanel } from "./components/AnnotationPanel";
import { MarkerRail } from "./components/MarkerRail";
import { SpeechReader } from "./components/SpeechReader";
import { UploadPanel } from "./components/UploadPanel";
import { SAMPLE_DOCUMENT } from "./sample";
import type { AnnotateResponse, AnnotationDepth } from "./types";

type View = "home" | "reader";

export default function App() {
  const [view, setView] = useState<View>("reader");
  const [document, setDocument] = useState<AnnotateResponse | null>(SAMPLE_DOCUMENT);
  const [activeId, setActiveId] = useState<string | null>(SAMPLE_DOCUMENT.annotations[0]?.annotation_id ?? null);
  const [markerTops, setMarkerTops] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSample = useCallback(async () => {
    setError(null);
    try {
      const doc = await fetchSample();
      setDocument(doc);
    } catch {
      setDocument(SAMPLE_DOCUMENT);
    }
    setView("reader");
    setActiveId(SAMPLE_DOCUMENT.annotations[0]?.annotation_id ?? null);
  }, []);

  useEffect(() => {
    loadSample();
  }, [loadSample]);

  const handleAnnotate = async (text: string, mode: AnnotationDepth, title?: string) => {
    setLoading(true);
    setError(null);
    try {
      const doc = await annotateText(text, mode, title);
      setDocument(doc);
      setActiveId(doc.annotations[0]?.annotation_id ?? null);
      setView("reader");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Annotation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <Header
        onHome={() => setView("home")}
        onAnnotate={() => setView("home")}
        showAnnotate={view === "reader"}
      />

      {view === "home" ? (
        <UploadPanel
          onSubmit={handleAnnotate}
          onLoadSample={loadSample}
          loading={loading}
          error={error}
        />
      ) : document ? (
        <div className="flex min-h-0 flex-1">
          <AnnotationPanel
            annotations={document.annotations}
            activeId={activeId}
            onSelect={setActiveId}
          />
          <MarkerRail
            annotations={document.annotations}
            activeId={activeId}
            markerTops={markerTops}
            onSelect={setActiveId}
          />
          <SpeechReader
            document={document}
            activeId={activeId}
            onSelect={setActiveId}
            onMarkerPositions={setMarkerTops}
          />
        </div>
      ) : null}
    </div>
  );
}
