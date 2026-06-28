declare global {
  interface Window {
    /** Set in static/paperlens/config.js when UI is hosted on the portfolio (Netlify). */
    PAPERLENS_API?: string;
  }
}

/** `/api` on same-origin Railway, or `https://your-app.up.railway.app/api` from portfolio. */
export function apiPrefix(): string {
  const fromEnv = import.meta.env.VITE_API_URL as string | undefined;
  if (fromEnv?.trim()) {
    return fromEnv.trim().replace(/\/$/, "");
  }
  if (typeof window !== "undefined" && window.PAPERLENS_API?.trim()) {
    return `${window.PAPERLENS_API.trim().replace(/\/$/, "")}/api`;
  }
  return "/api";
}
