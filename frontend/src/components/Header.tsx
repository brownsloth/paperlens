import { BRAND } from "../brand";

interface HeaderProps {
  onHome: () => void;
  showNav?: boolean;
  documentTitle?: string;
}

export function Header({ onHome, showNav, documentTitle }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] px-6">
      <button
        onClick={onHome}
        className="flex items-center gap-3 text-left transition hover:opacity-80"
      >
        <div className="flex h-9 w-9 items-center justify-center border border-black text-[8px] font-bold leading-tight">
          PAPER
          <br />
          LENS
        </div>
        <span className="hidden text-sm font-semibold tracking-wide sm:inline">{BRAND}</span>
      </button>

      {documentTitle && showNav && (
        <p className="mx-4 hidden flex-1 truncate text-center text-sm text-[var(--muted)] md:block">
          {documentTitle}
        </p>
      )}

      <nav className="flex items-center gap-4 text-sm">
        {showNav && (
          <button onClick={onHome} className="font-medium text-[var(--accent)] hover:underline">
            Library
          </button>
        )}
      </nav>
    </header>
  );
}
