export const HIGHLIGHT_PALETTE = [
  "#FDE047",
  "#FDBA74",
  "#F9A8D4",
  "#86EFAC",
  "#93C5FD",
  "#C4B5FD",
] as const;

export const NOTE_PALETTE = [
  "#93C5FD",
  "#86EFAC",
  "#FDE047",
  "#FDBA74",
  "#F9A8D4",
  "#C4B5FD",
] as const;

export const DEFAULT_HIGHLIGHT_COLOR = HIGHLIGHT_PALETTE[0];
export const DEFAULT_NOTE_COLOR = NOTE_PALETTE[0];

export function hexToRgba(hex: string, alpha: number): string {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) return `rgba(253, 224, 71, ${alpha})`;
  const r = parseInt(raw.slice(0, 2), 16);
  const g = parseInt(raw.slice(2, 4), 16);
  const b = parseInt(raw.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function annotationFillColor(
  ann: { annotation_type: string; color?: string | null },
  active: boolean,
): { backgroundColor: string; borderColor: string } {
  const isHighlight = ann.annotation_type === "highlight";
  const base = ann.color ?? (isHighlight ? DEFAULT_HIGHLIGHT_COLOR : DEFAULT_NOTE_COLOR);
  const alpha = active ? 0.5 : isHighlight ? 0.38 : 0.3;
  return {
    backgroundColor: hexToRgba(base, alpha),
    borderColor: hexToRgba(base, active ? 0.95 : 0.75),
  };
}
