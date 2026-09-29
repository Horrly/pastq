// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { firstErrorMessage } from "./api";
import { normalizeCode, paperTitle, sessionYears, topicShare } from "./format";
import { renderMarkdown } from "./markdown";

describe("normalizeCode", () => {
  it("matches the backend's normalisation", () => {
    expect(normalizeCode("csc201")).toBe("CSC 201");
    expect(normalizeCode(" CSC-201 ")).toBe("CSC 201");
    expect(normalizeCode("mth101a")).toBe("MTH 101A");
    expect(normalizeCode("weird code")).toBe("WEIRD CODE");
  });
});

describe("sessionYears", () => {
  it("starts from the current session", () => {
    expect(sessionYears(new Date(2026, 9, 1))[0]).toBe(2026); // October: new session started
    expect(sessionYears(new Date(2026, 2, 1))[0]).toBe(2025); // March: still 2025/2026
    expect(sessionYears(new Date(2026, 9, 1)).at(-1)).toBe(2005);
  });
});

describe("paperTitle and topicShare", () => {
  it("formats", () => {
    expect(paperTitle({ session: "2023/2024", semester_label: "First semester", kind_label: "Exam" })).toBe("2023/2024 First semester Exam");
    expect(topicShare({ papers: 5 }, 7)).toBe(71);
    expect(topicShare({ papers: 1 }, 0)).toBe(0);
  });
});

describe("renderMarkdown", () => {
  it("renders markdown and strips dangerous HTML", () => {
    const html = renderMarkdown("### Answer\n**42** <img src=x onerror=alert(1)><script>alert(1)</script>");
    expect(html).toContain("<h3>Answer</h3>");
    expect(html).toContain("<strong>42</strong>");
    expect(html).not.toContain("onerror");
    expect(html).not.toContain("<script");
  });
});

describe("firstErrorMessage", () => {
  it("reads DRF errors", () => {
    expect(firstErrorMessage({ code: ["Use the course code as written, e.g. CSC 201."] })).toBe("code: Use the course code as written, e.g. CSC 201.");
  });
});
