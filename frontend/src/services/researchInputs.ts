export const MAX_RESEARCH_URLS = 8;
export const MAX_PDF_FILES = 3;
export const MAX_PDF_BYTES = 10 * 1024 * 1024;

export type ResearchInputError =
  | "too_many_urls"
  | "url_too_long"
  | "invalid_url"
  | "too_many_pdfs"
  | "not_pdf"
  | "pdf_too_large";

export function parseResearchUrls(text: string): { urls: string[]; error: ResearchInputError | null } {
  const urls = text.split(/\r?\n/).map((url) => url.trim()).filter(Boolean);
  if (urls.length > MAX_RESEARCH_URLS) return { urls, error: "too_many_urls" };
  for (const value of urls) {
    if (value.length > 2048) return { urls, error: "url_too_long" };
    try {
      const url = new URL(value);
      if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
        return { urls, error: "invalid_url" };
      }
    } catch {
      return { urls, error: "invalid_url" };
    }
  }
  return { urls, error: null };
}

export function validatePdfSelection(
  files: readonly Pick<File, "name" | "size" | "type">[],
): ResearchInputError | null {
  if (files.length > MAX_PDF_FILES) return "too_many_pdfs";
  if (files.some((file) => file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"))) {
    return "not_pdf";
  }
  if (files.some((file) => file.size > MAX_PDF_BYTES)) return "pdf_too_large";
  return null;
}

const INTERNAL_PDF_PATH = /^\/api\/v1\/research\/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\/sources\/[A-Za-z0-9_-]{1,128}\/pdf$/i;

export function resolveSourceLink(value: string | undefined, apiBaseUrl: string): string | null {
  if (!value) return null;
  try {
    const apiBase = new URL(
      apiBaseUrl,
      typeof window === "undefined" ? "http://localhost" : window.location.origin,
    );
    if (/^#[A-Za-z0-9_.:-]+$/.test(value)) return value;
    if (value.startsWith("/")) {
      if (!INTERNAL_PDF_PATH.test(value)) return null;
      const internalUrl = new URL(value, apiBase);
      return internalUrl.origin === apiBase.origin ? internalUrl.href : null;
    }

    const url = new URL(value);
    if (url.username || url.password || (url.protocol !== "http:" && url.protocol !== "https:")) return null;
    if (url.origin === apiBase.origin
      && (!INTERNAL_PDF_PATH.test(url.pathname) || url.search || url.hash)) return null;
    return url.href;
  } catch {
    return null;
  }
}
