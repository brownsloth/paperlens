import { ColorSwatches } from "./ColorSwatches";

interface SelectionPromptModalProps {
  title: string;
  defaultQuestion?: string;
  busy?: boolean;
  onCancel: () => void;
  onSubmit: (question: string) => void;
}

export function SelectionPromptModal({
  title,
  defaultQuestion = "Explain this in plain language.",
  busy,
  onCancel,
  onSubmit,
}: SelectionPromptModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-xl border border-[var(--border)] bg-white p-5 shadow-xl">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Your question is sent to the LLM along with the selected content.
        </p>
        <textarea
          id="selection-question"
          defaultValue={defaultQuestion}
          rows={3}
          className="mt-3 w-full rounded-md border border-[var(--border)] px-3 py-2 text-sm"
          placeholder="What should the annotation explain?"
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-md border border-[var(--border)] px-3 py-1.5 text-xs font-medium"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              const el = document.getElementById("selection-question") as HTMLTextAreaElement | null;
              onSubmit(el?.value.trim() || defaultQuestion);
            }}
            className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          >
            {busy ? "Working…" : "Annotate"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface SelectionToolbarProps {
  position: { top: number; left: number };
  mode: "text" | "region";
  busy?: boolean;
  color: string;
  onColorChange: (color: string) => void;
  onHighlight?: () => void;
  onAnnotate: () => void;
  onDismiss: () => void;
}

export function SelectionToolbar({
  position,
  mode,
  busy,
  color,
  onColorChange,
  onHighlight,
  onAnnotate,
  onDismiss,
}: SelectionToolbarProps) {
  return (
    <div
      className="fixed z-40 flex flex-col gap-1 rounded-lg border border-gray-200 bg-white px-2 py-2 shadow-lg"
      style={{ top: position.top, left: position.left }}
      onMouseDown={(e) => e.preventDefault()}
    >
      <div className="flex items-center gap-1">
        {mode === "text" && onHighlight && (
          <button
            type="button"
            disabled={busy}
            onClick={onHighlight}
            className="rounded-md px-3 py-1.5 text-xs font-medium hover:bg-yellow-50 disabled:opacity-50"
          >
            Highlight
          </button>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={onAnnotate}
          className="rounded-md bg-[var(--accent)] px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
        >
          Annotate…
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={onDismiss}
          className="rounded-md px-2 py-1.5 text-xs text-[var(--muted)] hover:bg-gray-50"
        >
          ✕
        </button>
      </div>
      <ColorSwatches
        value={color}
        onChange={onColorChange}
        kind={mode === "text" && onHighlight ? "highlight" : "note"}
        disabled={busy}
      />
    </div>
  );
}
