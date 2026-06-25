import type { Annotation } from "../types";

const TYPE_LABELS: Record<string, string> = {
  entity: "Entity",
  historical_context: "Historical context",
  quote_verification: "Quote verification",
  doctrinal_context: "Doctrinal context",
  ambiguous_phrase: "Ambiguous phrase",
};

const STATUS_COLORS: Record<string, string> = {
  supported: "text-emerald-700 bg-emerald-50",
  supported_general_context: "text-emerald-700 bg-emerald-50",
  partially_supported: "text-amber-700 bg-amber-50",
  needs_verification: "text-amber-700 bg-amber-50",
  unclear: "text-gray-600 bg-gray-100",
  not_enough_evidence: "text-gray-600 bg-gray-100",
};

interface AnnotationCardProps {
  annotation: Annotation;
  index: number;
  active: boolean;
  onSelect: () => void;
}

export function AnnotationCard({ annotation, index, active, onSelect }: AnnotationCardProps) {
  const statusClass =
    STATUS_COLORS[annotation.evidence_status] ?? "text-gray-600 bg-gray-100";

  return (
    <article
      id={`card-${annotation.annotation_id}`}
      onClick={onSelect}
      className={`cursor-pointer border-b border-[var(--border)] px-5 py-5 transition ${
        active ? "bg-[var(--accent-soft)]" : "bg-white hover:bg-gray-50"
      }`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--accent)] text-xs font-semibold text-white">
          {index + 1}
        </span>
        <span className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
          SpeechLens
        </span>
        <span className="text-xs text-[var(--muted)]">·</span>
        <span className="text-xs text-[var(--muted)]">
          {TYPE_LABELS[annotation.annotation_type] ?? annotation.annotation_type}
        </span>
      </div>

      <h3 className="mb-2 text-sm font-semibold leading-snug text-[var(--ink)]">
        “{annotation.span_text}”
      </h3>

      <p className="mb-3 text-sm leading-relaxed text-gray-700">{annotation.annotation_text}</p>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full px-2 py-0.5 font-medium ${statusClass}`}>
          {annotation.evidence_status.replaceAll("_", " ")}
        </span>
        <span className="text-[var(--muted)]">
          Confidence {(annotation.confidence * 100).toFixed(0)}%
        </span>
        {annotation.needs_human_review && (
          <span className="rounded-full bg-orange-100 px-2 py-0.5 font-medium text-orange-800">
            needs review
          </span>
        )}
      </div>

      {annotation.sources.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-[var(--border)] pt-3 text-xs text-[var(--muted)]">
          {annotation.sources.map((s) => (
            <li key={s.title}>• {s.title}</li>
          ))}
        </ul>
      )}

      {annotation.alternative_interpretations.length > 0 && (
        <div className="mt-3 rounded-md bg-gray-50 p-3 text-xs text-gray-600">
          <span className="font-medium">Alternatives: </span>
          {annotation.alternative_interpretations.join(" ")}
        </div>
      )}
    </article>
  );
}
