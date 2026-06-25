import { useEffect, useRef } from "react";
import type { Annotation } from "../types";
import { AnnotationCard } from "./AnnotationCard";

interface AnnotationPanelProps {
  annotations: Annotation[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

export function AnnotationPanel({ annotations, activeId, onSelect }: AnnotationPanelProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeId || !listRef.current) return;
    const el = listRef.current.querySelector(`#card-${activeId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeId]);

  return (
    <aside className="flex h-full w-[380px] shrink-0 flex-col border-r border-[var(--border)] bg-white">
      <div className="border-b border-[var(--border)] px-5 py-4">
        <h2 className="text-sm font-semibold">Annotations</h2>
        <p className="mt-1 text-xs text-[var(--muted)]">
          {annotations.length} source-backed notes · click a highlight or marker
        </p>
      </div>
      <div ref={listRef} className="flex-1 overflow-y-auto">
        {annotations.map((ann, idx) => (
          <AnnotationCard
            key={ann.annotation_id}
            annotation={ann}
            index={idx}
            active={activeId === ann.annotation_id}
            onSelect={() => onSelect(ann.annotation_id)}
          />
        ))}
      </div>
      <div className="border-t border-[var(--border)] p-4">
        <p className="mb-2 text-xs text-[var(--muted)]">
          Human reviewers can approve, edit, or flag annotations.
        </p>
        <div className="rounded-md border border-[var(--border)] bg-gray-50 px-3 py-2 text-sm text-gray-400">
          Write a review note…
        </div>
      </div>
    </aside>
  );
}
