import { useEffect, useMemo, useRef, useState } from "react";
import type { Category, CitationEntry } from "../catalogApi";
import { downloadCitationFromPaper, fetchPaperCitations } from "../catalogApi";
import type { PaperAnnotation, PaperBlock, PaperDocument } from "../paperTypes";
import { ColorSwatches } from "./ColorSwatches";
import { DEFAULT_NOTE_COLOR } from "../paperColors";
import {
  chatOnPaperAnnotation,
  createPaperAnnotation,
  deletePaperAnnotation,
  updatePaperAnnotation,
} from "../paperApi";

interface PaperAnnotationPanelProps {
  document: PaperDocument;
  annotations: PaperAnnotation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onDocumentChange: (doc: PaperDocument) => void;
  categories?: Category[];
  onCitationDownloaded?: () => void;
  publicMode?: boolean;
  exportMarkdownUrl?: string;
  exportJsonUrl?: string;
  exportPdfUrl?: string;
}

export function PaperAnnotationPanel({
  document,
  annotations,
  activeId,
  onSelect,
  onDocumentChange,
  onCitationDownloaded,
  publicMode = false,
  exportPdfUrl,
}: PaperAnnotationPanelProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const [tab, setTab] = useState<"annotations" | "citations">("annotations");
  const [annSearch, setAnnSearch] = useState("");
  const [citations, setCitations] = useState<CitationEntry[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newBlockId, setNewBlockId] = useState("");
  const [newText, setNewText] = useState("");

  const active = annotations.find((a) => a.annotation_id === activeId) ?? null;

  const filteredAnnotations = useMemo(() => {
    const q = annSearch.trim().toLowerCase();
    if (!q) return annotations;
    return annotations.filter(
      (a) =>
        a.annotation_text.toLowerCase().includes(q) ||
        (a.target.quote ?? "").toLowerCase().includes(q),
    );
  }, [annotations, annSearch]);

  const candidateBlocks = useMemo(() => {
    return document.blocks.filter((b) => b.text.trim().length > 20).slice(0, 120);
  }, [document.blocks]);

  useEffect(() => {
    if (publicMode || tab !== "citations") return;
    fetchPaperCitations(document.paper.paper_id)
      .then(setCitations)
      .catch(() => setCitations([]));
  }, [tab, document.paper.paper_id, publicMode]);

  useEffect(() => {
    if (!activeId || !listRef.current) return;
    const el = listRef.current.querySelector(`#paper-ann-${activeId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeId]);

  useEffect(() => {
    if (active) {
      setEditText(active.annotation_text);
      setChatInput("");
    }
  }, [active?.annotation_id]);

  const run = async (fn: () => Promise<PaperDocument>) => {
    setBusy(true);
    setError(null);
    try {
      const doc = await fn();
      onDocumentChange(doc);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveEdit = () => {
    if (!active || !editText.trim()) return;
    void run(() =>
      updatePaperAnnotation(document.paper.paper_id, active.annotation_id, {
        annotation_text: editText.trim(),
      }),
    );
    setEditingId(null);
  };

  const handleColorChange = (color: string) => {
    if (!active) return;
    void run(() =>
      updatePaperAnnotation(document.paper.paper_id, active.annotation_id, { color }),
    );
  };

  const handleDelete = (annotationId: string) => {
    if (!confirm("Delete this annotation?")) return;
    void run(() => deletePaperAnnotation(document.paper.paper_id, annotationId));
  };

  const handleChat = () => {
    if (!active || !chatInput.trim()) return;
    const msg = chatInput.trim();
    setChatInput("");
    void run(() => chatOnPaperAnnotation(document.paper.paper_id, active.annotation_id, msg));
  };

  const handleCreate = () => {
    if (!newBlockId || !newText.trim()) return;
    void run(() =>
      createPaperAnnotation(document.paper.paper_id, {
        block_id: newBlockId,
        annotation_text: newText.trim(),
      }),
    );
    setShowAdd(false);
    setNewBlockId("");
    setNewText("");
  };

  const handleDownloadCitation = async (cite: CitationEntry) => {
    setBusy(true);
    setError(null);
    try {
      await downloadCitationFromPaper(document.paper.paper_id, cite.arxiv_id, cite.doi);
      onCitationDownloaded?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex h-full w-[380px] shrink-0 flex-col border-r border-[var(--border)] bg-white">
      <div className="border-b border-[var(--border)] px-4 py-3">
        {publicMode ? (
          <div className="space-y-3">
            <div>
              <h2 className="text-sm font-semibold">Your notes</h2>
              <p className="text-xs text-[var(--muted)]">{annotations.length} annotations</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {exportPdfUrl && (
                <a
                  href={exportPdfUrl}
                  className="rounded-md border border-[var(--accent)] bg-[var(--accent-soft)] px-2 py-1 text-xs font-medium text-[var(--accent)] hover:opacity-90"
                >
                  Export PDF
                </a>
              )}
            </div>
          </div>
        ) : (
          <div className="mb-2 flex gap-1 rounded-lg border border-[var(--border)] p-0.5">
            <button
              type="button"
              onClick={() => setTab("annotations")}
              className={`flex-1 rounded-md py-1 text-xs font-medium ${
                tab === "annotations" ? "bg-[var(--accent)] text-white" : "text-gray-600"
              }`}
            >
              Annotations
            </button>
            <button
              type="button"
              onClick={() => setTab("citations")}
              className={`flex-1 rounded-md py-1 text-xs font-medium ${
                tab === "citations" ? "bg-[var(--accent)] text-white" : "text-gray-600"
              }`}
            >
              Citations
            </button>
          </div>
        )}
        {(publicMode || tab === "annotations") ? (
          <>
            {!publicMode && (
              <div className="flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold">Your notes</h2>
                  <p className="text-xs text-[var(--muted)]">{annotations.length} annotations</p>
                </div>
                <button
                  type="button"
                  disabled={busy || !document.blocks.length}
                  onClick={() => setShowAdd((v) => !v)}
                  className="rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
                >
                  + Add
                </button>
              </div>
            )}
            {publicMode && (
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  disabled={busy || !document.blocks.length}
                  onClick={() => setShowAdd((v) => !v)}
                  className="rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium hover:bg-gray-50 disabled:opacity-50"
                >
                  + Add
                </button>
              </div>
            )}
            <input
              type="search"
              value={annSearch}
              onChange={(e) => setAnnSearch(e.target.value)}
              placeholder="Filter annotations…"
              className="mt-2 w-full rounded border border-[var(--border)] px-2 py-1 text-xs"
            />
          </>
        ) : (
          <p className="text-xs text-[var(--muted)]">
            Download open-access arXiv papers to the Misc category
          </p>
        )}
      </div>

      {error && (
        <p className="border-b border-red-100 bg-red-50 px-4 py-2 text-xs text-red-800">{error}</p>
      )}

      {showAdd && (publicMode || tab === "annotations") && (
        <div className="space-y-2 border-b border-[var(--border)] bg-gray-50 px-4 py-3">
          <label className="block text-xs font-medium text-[var(--muted)]">Block</label>
          <select
            value={newBlockId}
            onChange={(e) => setNewBlockId(e.target.value)}
            className="w-full rounded border border-[var(--border)] px-2 py-1 text-xs"
          >
            <option value="">Select a paragraph…</option>
            {candidateBlocks.map((b: PaperBlock) => (
              <option key={b.block_id} value={b.block_id}>
                p.{b.page} · {b.text.slice(0, 60).replace(/\n/g, " ")}…
              </option>
            ))}
          </select>
          <textarea
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            rows={3}
            placeholder="Your annotation…"
            className="w-full rounded border border-[var(--border)] px-2 py-1 text-sm"
          />
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy || !newBlockId || !newText.trim()}
              onClick={handleCreate}
              className="rounded-md bg-[var(--accent)] px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
            >
              Save annotation
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setShowAdd(false);
                setNewBlockId("");
                setNewText("");
              }}
              className="rounded-md border border-[var(--border)] px-3 py-1 text-xs font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto">
        {!publicMode && tab === "citations" ? (
          <ul className="divide-y divide-[var(--border)]">
            {citations.length === 0 ? (
              <li className="p-4 text-sm text-[var(--muted)]">No parsed citations found.</li>
            ) : (
              citations.map((cite) => (
                <li key={cite.citation_id} className="px-4 py-3">
                  <p className="line-clamp-3 text-xs text-[var(--ink)]">{cite.text}</p>
                  <p className="mt-1 text-[10px] text-[var(--muted)]">
                    p.{cite.page}
                    {cite.arxiv_id && ` · arXiv:${cite.arxiv_id}`}
                    {cite.doi && ` · DOI:${cite.doi}`}
                  </p>
                  {cite.downloadable ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDownloadCitation(cite)}
                      className="mt-2 rounded-md bg-[var(--accent)] px-2 py-1 text-xs text-white disabled:opacity-50"
                    >
                      Download to Misc
                    </button>
                  ) : (
                    <p className="mt-2 text-[10px] text-amber-700">No open arXiv link — manual upload needed</p>
                  )}
                </li>
              ))
            )}
          </ul>
        ) : annotations.length === 0 ? (
          <p className="p-4 text-sm text-[var(--muted)]">
            No annotations yet. Click Annotate from the library, or add your own with + Add.
          </p>
        ) : (
          <ul className="divide-y divide-[var(--border)]">
            {filteredAnnotations.map((ann) => {
              const isActive = ann.annotation_id === activeId;
              const isEditing = editingId === ann.annotation_id;
              return (
                <li key={ann.annotation_id} id={`paper-ann-${ann.annotation_id}`}>
                  <button
                    type="button"
                    onClick={() => onSelect(ann.annotation_id)}
                    className={`w-full px-4 py-3 text-left transition ${
                      isActive ? "bg-[var(--accent-soft)]" : "hover:bg-gray-50"
                    }`}
                  >
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                      ann.annotation_type === "highlight"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                        {ann.annotation_type.replace(/_/g, " ")}
                      </span>
                      {ann.page && (
                        <span className="text-[10px] text-[var(--muted)]">p.{ann.page}</span>
                      )}
                    </div>
                    {ann.target.quote && (
                      <p className="mb-1 truncate text-xs italic text-[var(--muted)]">
                        &ldquo;{ann.target.quote}&rdquo;
                      </p>
                    )}
                    {!isEditing && (
                      <p className="line-clamp-3 text-sm leading-snug text-[var(--ink)]">
                        {ann.annotation_text}
                      </p>
                    )}
                  </button>
                  {isActive && (
                    <div className="space-y-3 border-t border-[var(--border)] bg-white px-4 py-3">
                      <ColorSwatches
                        value={
                          ann.color ??
                          (ann.annotation_type === "highlight"
                            ? "#FDE047"
                            : DEFAULT_NOTE_COLOR)
                        }
                        onChange={handleColorChange}
                        kind={ann.annotation_type === "highlight" ? "highlight" : "note"}
                        disabled={busy}
                      />
                      {isEditing ? (
                        <div className="space-y-2">
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            rows={4}
                            className="w-full rounded border border-[var(--border)] px-2 py-1 text-sm"
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              disabled={busy}
                              onClick={handleSaveEdit}
                              className="rounded-md bg-[var(--accent)] px-3 py-1 text-xs font-medium text-white"
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingId(null)}
                              className="rounded-md border border-[var(--border)] px-3 py-1 text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => setEditingId(ann.annotation_id)}
                            className="rounded-md border border-[var(--border)] px-2 py-1 text-xs"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleDelete(ann.annotation_id)}
                            className="rounded-md border border-red-200 px-2 py-1 text-xs text-red-700"
                          >
                            Delete
                          </button>
                        </div>
                      )}

                      {(ann.thread ?? []).length > 0 && (
                        <div className="max-h-40 space-y-2 overflow-y-auto rounded-md bg-gray-50 p-2">
                          {(ann.thread ?? []).map((msg, i) => (
                            <div
                              key={`${msg.created_at}-${i}`}
                              className={`text-xs leading-relaxed ${
                                msg.role === "user" ? "text-[var(--ink)]" : "text-[var(--muted)]"
                              }`}
                            >
                              <span className="font-medium capitalize">{msg.role}: </span>
                              {msg.content}
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={chatInput}
                          onChange={(e) => setChatInput(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && handleChat()}
                          placeholder="Ask a follow-up…"
                          className="min-w-0 flex-1 rounded border border-[var(--border)] px-2 py-1 text-sm"
                        />
                        <button
                          type="button"
                          disabled={busy || !chatInput.trim()}
                          onClick={handleChat}
                          className="shrink-0 rounded-md bg-gray-800 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
                        >
                          Ask
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
