function safeUrl(raw: string): URL | null {
  try {
    return new URL(raw);
  } catch {
    return null;
  }
}

function normalizedQuery(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  return trimmed ? trimmed : null;
}

function queryFromUrl(rawUrl: string | null | undefined): string | null {
  if (!rawUrl) return null;
  const parsed = safeUrl(rawUrl);
  if (!parsed) return null;
  return normalizedQuery(parsed.searchParams.get("q"));
}

export function buildMapsSearchUrl(rawMapUrl: string | null | undefined, fallbackQuery?: string | null): string | null {
  const raw = normalizedQuery(rawMapUrl);
  const parsed = raw ? safeUrl(raw) : null;

  if (parsed && /(^|\.)google\./i.test(parsed.hostname)) {
    const isEmbedPath = parsed.pathname.includes("/maps/embed");
    const hasEmbedOutput = parsed.searchParams.get("output") === "embed";
    const googleQuery =
      normalizedQuery(parsed.searchParams.get("q")) ??
      normalizedQuery(parsed.searchParams.get("query")) ??
      normalizedQuery(parsed.searchParams.get("destination")) ??
      normalizedQuery(parsed.searchParams.get("origin"));

    if (googleQuery) {
      return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(googleQuery)}`;
    }

    if (isEmbedPath || hasEmbedOutput) {
      return "https://www.google.com/maps";
    }
  }

  const query = queryFromUrl(rawMapUrl) ?? normalizedQuery(fallbackQuery);
  if (query) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
  }

  if (raw && /^https?:\/\//i.test(raw)) {
    return raw;
  }
  return null;
}

export function buildMapsEmbedUrl(rawMapUrl: string | null | undefined, fallbackQuery?: string | null): string | null {
  const raw = normalizedQuery(rawMapUrl);
  if (raw) {
    const parsed = safeUrl(raw);
    if (parsed) {
      const isGoogleMapsHost = /(^|\.)google\./i.test(parsed.hostname);
      const hasEmbedOutput = parsed.searchParams.get("output") === "embed";
      const isEmbedPath = parsed.pathname.includes("/maps/embed");

      if (isGoogleMapsHost && (hasEmbedOutput || isEmbedPath)) {
        return raw;
      }
    }
  }

  const query = queryFromUrl(raw) ?? normalizedQuery(fallbackQuery);
  if (!query) return null;
  return `https://www.google.com/maps?q=${encodeURIComponent(query)}&output=embed`;
}
