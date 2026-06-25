import type { Annotation } from "../types";

interface MarkerRailProps {
  annotations: Annotation[];
  activeId: string | null;
  markerTops: Record<string, number>;
  onSelect: (id: string) => void;
}

export function MarkerRail({ annotations, activeId, markerTops, onSelect }: MarkerRailProps) {
  return (
    <div className="relative w-10 shrink-0 border-r border-[var(--border)] bg-[#fbfbfa]">
      <div className="absolute inset-x-0 top-0 bottom-0 mx-auto w-px bg-gray-200" />
      {annotations.map((ann, idx) => {
        const top = markerTops[ann.annotation_id] ?? 120 + idx * 80;
        const active = activeId === ann.annotation_id;
        return (
          <button
            key={ann.annotation_id}
            onClick={() => onSelect(ann.annotation_id)}
            className="absolute left-1/2 -translate-x-1/2 transition-transform hover:scale-110"
            style={{ top }}
            aria-label={`Annotation ${idx + 1}: ${ann.span_text}`}
          >
            <span
              className={`block h-3.5 w-3.5 rounded-full border-2 ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent)]"
                  : "border-gray-300 bg-white hover:border-[var(--accent)]"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}
