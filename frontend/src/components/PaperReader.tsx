import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PaperAnnotation, PaperDocument } from "../paperTypes";
import { bboxToOverlay } from "../paperTypes";
import {
  allAnnotations,
  annotateFromRegion,
  annotateFromSelection,
  highlightSelection,
  paperPageUrl,
} from "../paperApi";
import { BRAND } from "../brand";
import { annotationFillColor, DEFAULT_HIGHLIGHT_COLOR, DEFAULT_NOTE_COLOR } from "../paperColors";
import { PaperSearchBar } from "./PaperSearchBar";
import {
  collectTextSelection,
  columnSplitForPage,
  groupLinesByColumn,
  linesForPage,
  screenRectToPdfBBox,
  selectionToolbarPosition,
  textLineStyle,
  type RegionSelectionPayload,
  type SelectMode,
  type TextSelectionPayload,
} from "../paperSelection";
import { SelectionPromptModal, SelectionToolbar } from "./PaperSelectionUI";

function TextLineSpan({
  line,
  page,
  col,
}: {
  line: ReturnType<typeof linesForPage>[number];
  page: PaperDocument["pages"][number];
  col?: ReturnType<typeof groupLinesByColumn>[number];
}) {
  const style = textLineStyle(line, page, col);
  return (
    <span
      data-line-id={line.id}
      data-block-id={line.blockId}
      data-line-index={line.lineIndex}
      data-column={line.column}
      data-x0={line.bbox.x0}
      data-y0={line.bbox.y0}
      data-x1={line.bbox.x1}
      data-y1={line.bbox.y1}
      className="pointer-events-auto absolute cursor-text whitespace-pre text-transparent selection:bg-sky-300/50"
      style={{
        left: style.left,
        top: style.top,
        width: style.width,
        height: style.height,
        fontSize: style.fontSize,
        lineHeight: 1.05,
      }}
    >
      {line.text}
    </span>
  );
}

interface PaperReaderProps {
  document: PaperDocument;
  activeId: string | null;
  onSelect: (id: string) => void;
  onDocumentChange: (doc: PaperDocument) => void;
}

interface DragState {
  page: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
}

export function PaperReader({
  document,
  activeId,
  onSelect,
  onDocumentChange,
}: PaperReaderProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageContainerRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const dragRef = useRef<DragState | null>(null);

  const [mode, setMode] = useState<SelectMode>("text");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [textSelection, setTextSelection] = useState<TextSelectionPayload | null>(null);
  const [regionSelection, setRegionSelection] = useState<RegionSelectionPayload | null>(null);
  const [toolbarPos, setToolbarPos] = useState<{ top: number; left: number } | null>(null);
  const [showAnnotateModal, setShowAnnotateModal] = useState(false);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [selectionColor, setSelectionColor] = useState<string>(DEFAULT_HIGHLIGHT_COLOR);

  const [jumpPage, setJumpPage] = useState<number | null>(null);

  const visibleAnnotations = useMemo(() => allAnnotations(document), [document]);
  const refStart = document.metadata?.reference_start_page as number | undefined;
  const allPages = document.pages;
  const byPage = useMemo(() => {
    const map: Record<number, PaperAnnotation[]> = {};
    for (const ann of visibleAnnotations) {
      if (!ann.page || !ann.bbox) continue;
      (map[ann.page] ??= []).push(ann);
    }
    return map;
  }, [visibleAnnotations]);

  useEffect(() => {
    if (!jumpPage || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-page="${jumpPage}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
    setJumpPage(null);
  }, [jumpPage]);

  useEffect(() => {
    if (!activeId || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-ann="${activeId}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeId]);

  const clearTextUi = useCallback(() => {
    setTextSelection(null);
    setRegionSelection(null);
    setToolbarPos(null);
    setShowAnnotateModal(false);
    window.getSelection()?.removeAllRanges();
  }, []);

  const clearAll = useCallback(() => {
    clearTextUi();
    dragRef.current = null;
    setDrag(null);
  }, [clearTextUi]);

  const finishRegionDrag = useCallback(
    (page: number) => {
      const d = dragRef.current;
      if (!d || d.page !== page) return;

      const left = Math.min(d.startX, d.currentX);
      const top = Math.min(d.startY, d.currentY);
      const width = Math.abs(d.currentX - d.startX);
      const height = Math.abs(d.currentY - d.startY);

      dragRef.current = null;
      setDrag(null);

      if (width < 8 || height < 8) return;

      const container = pageContainerRefs.current[page];
      const pageInfo = document.pages.find((p) => p.page === page);
      if (!container || !pageInfo) return;

      const containerRect = container.getBoundingClientRect();
      const bbox = screenRectToPdfBBox({ left, top, width, height }, container, pageInfo);

      setRegionSelection({
        page,
        bbox,
        containerRect: { left, top, width, height },
      });
      setTextSelection(null);
      setToolbarPos(
        selectionToolbarPosition(
          new DOMRect(containerRect.left + left, containerRect.top + top, width, height),
        ),
      );
    },
    [document.pages],
  );

  // Global pointer tracking for region drag (works when cursor leaves the page)
  useEffect(() => {
    if (mode !== "region" || !drag) return;

    const onMove = (e: PointerEvent) => {
      const d = dragRef.current;
      if (!d) return;
      const container = pageContainerRefs.current[d.page];
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const next = {
        ...d,
        currentX: e.clientX - rect.left,
        currentY: e.clientY - rect.top,
      };
      dragRef.current = next;
      setDrag(next);
    };

    const onUp = () => {
      const d = dragRef.current;
      if (d) finishRegionDrag(d.page);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
  }, [mode, drag, finishRegionDrag]);

  const handleTextMouseUp = (page: number, container: HTMLDivElement, columnSplit: number | null) => {
    if (mode !== "text") return;
    const lineEls = container.querySelectorAll("[data-line-id]");
    const payload = collectTextSelection(page, container, lineEls, columnSplit);
    if (!payload) return;

    const sel = window.getSelection();
    const rect = sel?.rangeCount ? sel.getRangeAt(0).getBoundingClientRect() : null;
    if (!rect || rect.width === 0) return;

    setTextSelection(payload);
    setRegionSelection(null);
    setToolbarPos(selectionToolbarPosition(rect));
  };

  const handleRegionPointerDown = (page: number, e: React.PointerEvent<HTMLDivElement>) => {
    if (mode !== "region") return;
    e.preventDefault();
    clearTextUi();

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const next = { page, startX: x, startY: y, currentX: x, currentY: y };
    dragRef.current = next;
    setDrag(next);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const run = async (fn: () => Promise<PaperDocument>) => {
    setBusy(true);
    setError(null);
    try {
      const doc = await fn();
      onDocumentChange(doc);
      const newest = doc.annotations[doc.annotations.length - 1];
      if (newest) onSelect(newest.annotation_id);
      clearAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const handleHighlight = () => {
    if (!textSelection) return;
    void run(() =>
      highlightSelection(document.paper.paper_id, {
        page: textSelection.page,
        quote: textSelection.quote,
        block_id: textSelection.blockId,
        bbox: textSelection.bbox,
        color: selectionColor,
      }),
    );
  };

  const handleAnnotateSubmit = (question: string) => {
    const noteColor = selectionColor === DEFAULT_HIGHLIGHT_COLOR ? DEFAULT_NOTE_COLOR : selectionColor;
    if (textSelection) {
      void run(() =>
        annotateFromSelection(document.paper.paper_id, {
          page: textSelection.page,
          quote: textSelection.quote,
          question,
          block_id: textSelection.blockId,
          bbox: textSelection.bbox,
          color: noteColor,
        }),
      );
      return;
    }
    if (regionSelection) {
      void run(() =>
        annotateFromRegion(document.paper.paper_id, {
          page: regionSelection.page,
          bbox: regionSelection.bbox,
          question,
          color: noteColor,
        }),
      );
    }
  };

  useEffect(() => {
    if (!activeId || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-ann="${activeId}"]`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeId]);


  return (
    <div ref={scrollRef} className="min-w-0 flex-1 overflow-y-auto bg-gray-100">
      <div className="sticky top-0 z-30 border-b border-[var(--border)] bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-4xl px-6 pt-2">
          <PaperSearchBar
            paperId={document.paper.paper_id}
            onSelectAnnotation={onSelect}
            onJumpToPage={setJumpPage}
          />
        </div>
        <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-3 px-6 py-2">
          <span className="text-xs font-medium text-[var(--muted)]">Selection</span>
          <div className="flex rounded-lg border border-[var(--border)] p-0.5">
            <button
              type="button"
              onClick={() => {
                setMode("text");
                clearAll();
              }}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                mode === "text" ? "bg-[var(--accent)] text-white" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              Select text
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("region");
                clearAll();
              }}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                mode === "region" ? "bg-[var(--accent)] text-white" : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              Select region
            </button>
          </div>
          <p className="text-xs text-[var(--muted)]">
            {mode === "text"
              ? "Drag to select text in one column, then highlight or annotate."
              : "Click and drag a rectangle over figures, equations, or tables."}
          </p>
        </div>
        {error && <p className="mx-auto mt-2 max-w-4xl text-xs text-red-700">{error}</p>}
      </div>

      <div className="mx-auto max-w-4xl px-6 py-8">
        <header className="mb-8 text-center">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[var(--muted)]">{BRAND}</p>
          <h1 className="font-serif mt-2 text-2xl font-semibold text-[var(--ink)]">{document.paper.title}</h1>
          {document.paper.authors.length > 0 && (
            <p className="mt-1 text-sm text-[var(--muted)]">
              {document.paper.authors.slice(0, 4).join(", ")}
              {document.paper.year ? ` · ${document.paper.year}` : ""}
            </p>
          )}
          {refStart && (
            <p className="mt-2 text-xs text-[var(--muted)]">
              References from page {refStart} · citations can be downloaded to Misc
            </p>
          )}
        </header>

        {allPages.length === 0 ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            This paper has not been parsed yet. Go back and click Parse.
          </p>
        ) : (
          allPages.map((page) => {
            const lines = linesForPage(document.blocks, page.page, page, refStart);
            const columnSplit = columnSplitForPage(lines, page.pdf_width);
            const columns = groupLinesByColumn(lines, page);

            const dragRect =
              drag && drag.page === page.page
                ? {
                    left: Math.min(drag.startX, drag.currentX),
                    top: Math.min(drag.startY, drag.currentY),
                    width: Math.abs(drag.currentX - drag.startX),
                    height: Math.abs(drag.currentY - drag.startY),
                  }
                : null;

            const regionRect =
              regionSelection?.page === page.page ? regionSelection.containerRect : null;

            return (
              <div key={page.page} className="relative mb-8 shadow-md" data-page={page.page}>
                <div
                  ref={(el) => {
                    pageContainerRefs.current[page.page] = el;
                  }}
                  className={`relative w-full touch-none ${mode === "region" ? "cursor-crosshair" : ""}`}
                  style={{ aspectRatio: `${page.width_px} / ${page.height_px}`, containerType: "size" }}
                  onPointerDown={(e) => handleRegionPointerDown(page.page, e)}
                >
                  <img
                    src={paperPageUrl(document.paper.paper_id, page.page)}
                    alt={`Page ${page.page}`}
                    className="pointer-events-none absolute inset-0 block h-full w-full"
                    draggable={false}
                  />

                  {/* Selectable text layer — column clips only when layout is truly two-column */}
                  <div
                    className={`absolute inset-0 ${mode === "text" ? "" : "pointer-events-none"}`}
                    onMouseUp={() => {
                      const container = pageContainerRefs.current[page.page];
                      if (container) handleTextMouseUp(page.page, container, columnSplit);
                    }}
                  >
                    {columnSplit === null ? (
                      lines.map((line) => (
                        <TextLineSpan key={line.id} line={line} page={page} />
                      ))
                    ) : (
                      columns.map((col) => (
                        <div
                          key={col.column}
                          className="pointer-events-none absolute top-0 bottom-0 overflow-hidden"
                          style={{ left: `${col.leftPct}%`, width: `${col.widthPct}%` }}
                        >
                          {col.lines.map((line) => (
                            <TextLineSpan key={line.id} line={line} page={page} col={col} />
                          ))}
                        </div>
                      ))
                    )}
                  </div>

                  {/* Region drag preview */}
                  {dragRect && dragRect.width > 0 && dragRect.height > 0 && (
                    <div
                      className="pointer-events-none absolute z-20 border-2 border-dashed border-[var(--accent)] bg-[var(--accent)]/15"
                      style={dragRect}
                    />
                  )}

                  {/* Completed region selection */}
                  {regionRect && (
                    <div
                      className="pointer-events-none absolute z-20 border-2 border-[var(--accent)] bg-[var(--accent)]/20"
                      style={regionRect}
                    />
                  )}

                  {/* Existing annotation overlays */}
                  {(byPage[page.page] ?? []).map((ann) => {
                    if (!ann.bbox) return null;
                    const box = bboxToOverlay(ann.bbox, page);
                    const active = activeId === ann.annotation_id;
                    const colors = annotationFillColor(ann, active);
                    return (
                      <button
                        key={ann.annotation_id}
                        type="button"
                        data-ann={ann.annotation_id}
                        onClick={() => onSelect(ann.annotation_id)}
                        title={ann.target.quote ?? ann.annotation_type}
                        className={`absolute z-10 border-2 transition ${
                          active ? "ring-2 ring-[var(--accent)] ring-offset-1" : ""
                        }`}
                        style={{
                          left: `${(box.left / page.width_px) * 100}%`,
                          top: `${(box.top / page.height_px) * 100}%`,
                          width: `${(box.width / page.width_px) * 100}%`,
                          height: `${(box.height / page.height_px) * 100}%`,
                          pointerEvents: mode === "region" ? "none" : "auto",
                          backgroundColor: colors.backgroundColor,
                          borderColor: colors.borderColor,
                        }}
                      />
                    );
                  })}
                </div>
                <p className="mt-1 text-center text-xs text-[var(--muted)]">
                Page {page.page}
                {refStart && page.page >= refStart ? " · References" : ""}
              </p>
              </div>
            );
          })
        )}
      </div>

      {toolbarPos && (textSelection || regionSelection) && !showAnnotateModal && (
        <SelectionToolbar
          position={toolbarPos}
          mode={textSelection ? "text" : "region"}
          busy={busy}
          color={selectionColor}
          onColorChange={setSelectionColor}
          onHighlight={textSelection ? handleHighlight : undefined}
          onAnnotate={() => setShowAnnotateModal(true)}
          onDismiss={clearAll}
        />
      )}

      {showAnnotateModal && (
        <SelectionPromptModal
          title={regionSelection ? "Annotate region" : "Annotate selection"}
          defaultQuestion={
            regionSelection
              ? "Explain what this figure, equation, or region shows."
              : "Explain this passage in plain language."
          }
          busy={busy}
          onCancel={() => setShowAnnotateModal(false)}
          onSubmit={handleAnnotateSubmit}
        />
      )}
    </div>
  );
}
