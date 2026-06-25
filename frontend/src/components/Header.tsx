interface HeaderProps {
  onHome: () => void;
  onAnnotate?: () => void;
  showAnnotate?: boolean;
}

export function Header({ onHome, onAnnotate, showAnnotate }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] px-6">
      <button
        onClick={onHome}
        className="flex items-center gap-3 text-left transition hover:opacity-80"
      >
        <div className="flex h-9 w-9 items-center justify-center border border-black text-[10px] font-bold leading-tight">
          SPEECH
          <br />
          LENS
        </div>
        <span className="hidden text-sm font-semibold tracking-wide sm:inline">SpeechLens</span>
      </button>

      <nav className="flex items-center gap-6 text-sm text-[var(--muted)]">
        <span className="hidden md:inline">Reader</span>
        <span className="hidden md:inline">Researcher</span>
        {showAnnotate && onAnnotate && (
          <button
            onClick={onAnnotate}
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:brightness-95"
          >
            Annotate transcript
          </button>
        )}
      </nav>
    </header>
  );
}
