import { useState } from "react";
import type { Category } from "../catalogApi";
import { createCategory } from "../catalogApi";

interface CategoriesSidebarProps {
  categories: Category[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreated: () => void;
}

export function CategoriesSidebar({
  categories,
  activeId,
  onSelect,
  onCreated,
}: CategoriesSidebarProps) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await createCategory(name.trim());
      setName("");
      setShowForm(false);
      onCreated();
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-[var(--border)] bg-white">
      <div className="border-b border-[var(--border)] px-4 py-3">
        <h2 className="text-sm font-semibold">Categories</h2>
      </div>
      <ul className="flex-1 overflow-y-auto py-2">
        {categories.map((cat) => (
          <li key={cat.id}>
            <button
              type="button"
              onClick={() => onSelect(cat.id)}
              className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition ${
                activeId === cat.id ? "bg-[var(--accent-soft)] font-medium" : "hover:bg-gray-50"
              }`}
            >
              <span className="truncate">{cat.name}</span>
              <span className="ml-2 shrink-0 text-xs text-[var(--muted)]">{cat.document_count}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="border-t border-[var(--border)] p-3">
        {showForm ? (
          <div className="space-y-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Category name"
              className="w-full rounded border border-[var(--border)] px-2 py-1 text-sm"
            />
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={handleCreate}
                className="rounded bg-[var(--accent)] px-2 py-1 text-xs text-white"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded border border-[var(--border)] px-2 py-1 text-xs"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="w-full rounded border border-dashed border-[var(--border)] py-1.5 text-xs text-[var(--muted)] hover:bg-gray-50"
          >
            + New category
          </button>
        )}
      </div>
    </aside>
  );
}
