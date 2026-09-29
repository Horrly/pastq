import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: false });

// AI output is untrusted: always sanitize before putting it in the page.
export function renderMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ""));
}
