export function sessionLabel(year) {
  return `${year}/${year + 1}`;
}

export function paperTitle(paper) {
  return `${paper.session} ${paper.semester_label} ${paper.kind_label}`.replace(" Other ", " ");
}

// Years offered in the upload form: current session back to 2005.
export function sessionYears(now = new Date()) {
  const latest = now.getMonth() >= 8 ? now.getFullYear() : now.getFullYear() - 1; // sessions start ~September
  return Array.from({ length: latest - 2004 }, (_, i) => latest - i);
}

// "appeared in 5 of 7 papers" -> 71
export function topicShare(topic, paperTotal) {
  return paperTotal ? Math.round((topic.papers / paperTotal) * 100) : 0;
}

export function normalizeCode(code) {
  const compact = (code || "").replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  const m = compact.match(/^([A-Z]+)(\d+[A-Z]?)$/);
  return m ? `${m[1]} ${m[2]}` : (code || "").toUpperCase().trim();
}

export const STATUS_NOTE = {
  processing: "Reading the paper… questions will appear here in a moment.",
  needs_text: "The questions on this paper haven't been typed in yet.",
};
