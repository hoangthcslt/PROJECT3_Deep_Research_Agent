import assert from "node:assert/strict";
import test from "node:test";
import {
  MAX_PDF_BYTES,
  parseResearchUrls,
  resolveSourceLink,
  validatePdfSelection,
} from "./researchInputs.ts";

test("validates provided URL count, scheme, credentials, and length", () => {
  const urls = Array.from({ length: 8 }, (_, index) => "https://example.org/" + index);
  assert.deepEqual(parseResearchUrls(urls.join("\n")), { urls, error: null });
  assert.equal(parseResearchUrls("https://example.org/" + "x".repeat(2028)).error, null);
  assert.equal(parseResearchUrls(urls.concat("https://example.org/9").join("\n")).error, "too_many_urls");
  assert.equal(parseResearchUrls("ftp://example.org/file").error, "invalid_url");
  assert.equal(parseResearchUrls("https://user:pass@example.org/file").error, "invalid_url");
  assert.equal(parseResearchUrls("https://example.org/" + "x".repeat(2048)).error, "url_too_long");
});

test("limits PDF selections to three valid files no larger than 10 MiB", () => {
  const pdf = { name: "paper.pdf", type: "application/pdf", size: MAX_PDF_BYTES };
  assert.equal(validatePdfSelection([pdf, pdf, pdf]), null);
  assert.equal(validatePdfSelection([pdf, pdf, pdf, pdf]), "too_many_pdfs");
  assert.equal(validatePdfSelection([{ name: "notes.txt", type: "text/plain", size: 10 }]), "not_pdf");
  assert.equal(validatePdfSelection([{ ...pdf, size: MAX_PDF_BYTES + 1 }]), "pdf_too_large");
});

test("resolves exact internal PDF paths and keeps local footnote hashes", () => {
  const pdfPath = "/api/v1/research/123e4567-e89b-12d3-a456-426614174000/sources/REF_1/pdf";
  assert.equal(
    resolveSourceLink(pdfPath, "https://api.example.org/api/v1"),
    "https://api.example.org/api/v1/research/123e4567-e89b-12d3-a456-426614174000/sources/REF_1/pdf",
  );
  assert.equal(
    resolveSourceLink("https://api.example.org" + pdfPath, "https://api.example.org/api/v1"),
    "https://api.example.org" + pdfPath,
  );
  assert.equal(resolveSourceLink("#user-content-fn-1", "https://api.example.org/api/v1"), "#user-content-fn-1");
  assert.equal(resolveSourceLink("relative.pdf", "https://api.example.org/api/v1"), null);
  assert.equal(resolveSourceLink("/api/v1/research/not-a-uuid/sources/REF_1/pdf", "https://api.example.org/api/v1"), null);
  assert.equal(resolveSourceLink("/api/v1/other/path", "https://api.example.org/api/v1"), null);
});

test("rejects unsafe Markdown links and allows external HTTP(S)", () => {
  assert.equal(resolveSourceLink("javascript:alert(1)", "https://api.example.org/api/v1"), null);
  assert.equal(resolveSourceLink("https://user:pass@example.org/", "https://api.example.org/api/v1"), null);
  assert.equal(resolveSourceLink("https://example.org/article", "/api/v1"), "https://example.org/article");
});
