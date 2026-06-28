import { HIGHLIGHT_PALETTE, NOTE_PALETTE } from "../paperColors";

interface ColorSwatchesProps {
  value: string;
  onChange: (color: string) => void;
  kind?: "highlight" | "note";
  disabled?: boolean;
}

export function ColorSwatches({
  value,
  onChange,
  kind = "highlight",
  disabled,
}: ColorSwatchesProps) {
  const palette = kind === "highlight" ? HIGHLIGHT_PALETTE : NOTE_PALETTE;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted)]">
        Color
      </span>
      {palette.map((color) => (
        <button
          key={color}
          type="button"
          disabled={disabled}
          title={color}
          onClick={() => onChange(color)}
          className={`h-5 w-5 rounded-full border-2 transition disabled:opacity-50 ${
            value === color ? "border-gray-800 scale-110" : "border-white shadow-sm"
          }`}
          style={{ backgroundColor: color }}
        />
      ))}
    </div>
  );
}
