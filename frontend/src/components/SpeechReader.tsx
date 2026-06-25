import { useCallback, useEffect, useMemo, useRef, type ReactNode } from "react";
import type { AnnotateResponse, Annotation } from "../types";

interface SpeechReaderProps {
  document: AnnotateResponse;
  activeId: string | null;
  onSelect: (id: string) => void;
  onMarkerPositions: (positions: Record<string, number>) => void;
}

function renderSegmentText(
  text: string,
  annotations: Annotation[],
  activeId: string | null,
  onSelect: (id: string) => void,
) {
  const sorted = [...annotations].sort((a, b) => a.span_start - b.span_start);
  const parts: ReactNode[] = [];
  let offset = 0;

  sorted.forEach((ann) => {
    if (ann.span_start > offset) {
      parts.push(<span key={`t-${offset}`}>{text.slice(offset, ann.span_start)}</span>);
    }
    const active = activeId === ann.annotation_id;
    parts.push(
      <mark
        key={ann.annotation_id}
        id={`span-${ann.annotation_id}`}
        onClick={() => onSelect(ann.annotation_id)}
        className={`cursor-pointer rounded-sm px-0.5 transition ${
          active
            ? "bg-[var(--highlight-active)] ring-2 ring-[var(--accent)]"
            : "bg-[var(--highlight)] hover:bg-[var(--highlight-active)]"
        }`}
      >
        {ann.span_text}
      </mark>,
    );
    offset = ann.span_end;
  });

  if (offset < text.length) {
    parts.push(<span key={`t-end`}>{text.slice(offset)}</span>);
  }

  return parts;
}

export function SpeechReader({
  document,
  activeId,
  onSelect,
  onMarkerPositions,
}: SpeechReaderProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const bySegment = useMemo(() => {
    const map: Record<string, Annotation[]> = {};
    for (const ann of document.annotations) {
      (map[ann.segment_id] ??= []).push(ann);
    }
    return map;
  }, [document.annotations]);

  const updateMarkers = useCallback(() => {
    if (!scrollRef.current || !containerRef.current) return;
    const scrollTop = scrollRef.current.scrollTop;
    const positions: Record<string, number> = {};
    for (const ann of document.annotations) {
      const el = containerRef.current.querySelector(`#span-${ann.annotation_id}`);
      if (el instanceof HTMLElement) {
        positions[ann.annotation_id] = el.offsetTop - scrollTop + el.offsetHeight / 2 - 7;
      }
    }
    onMarkerPositions(positions);
  }, [document.annotations, onMarkerPositions]);

  useEffect(() => {
    updateMarkers();
    const node = scrollRef.current;
    node?.addEventListener("scroll", updateMarkers);
    window.addEventListener("resize", updateMarkers);
    return () => {
      node?.removeEventListener("scroll", updateMarkers);
      window.removeEventListener("resize", updateMarkers);
    };
  }, [updateMarkers, document]);

  useEffect(() => {
    if (!activeId || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`#span-${activeId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeId]);

  return (
    <div ref={scrollRef} className="min-w-0 flex-1 overflow-y-auto bg-[var(--paper)]">
      <div ref={containerRef} className="mx-auto max-w-3xl px-10 py-10">
        <header className="mb-10 text-center">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--muted)]">
            Annotated Speech
          </p>
          <h1 className="font-serif mt-3 text-3xl font-semibold leading-tight text-[var(--ink)]">
            {document.title}
          </h1>
          {document.metadata?.mode && (
            <p className="mt-2 text-sm text-[var(--muted)]">
              Depth: {String(document.metadata.mode)} · {document.annotations.length} annotations
            </p>
          )}
        </header>

        {document.segments.map((segment) => (
          <section key={segment.segment_id} className="mb-8">
            {segment.speaker && (
              <h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-gray-500">
                {segment.speaker}
              </h2>
            )}
            <p className="font-serif text-[1.05rem] leading-[1.85] text-[var(--ink)]">
              {renderSegmentText(
                segment.text,
                bySegment[segment.segment_id] ?? [],
                activeId,
                onSelect,
              )}
            </p>
          </section>
        ))}
      </div>
    </div>
  );
}
