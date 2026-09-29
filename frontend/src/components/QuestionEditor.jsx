import { useState } from "react";
import { api } from "../lib/api";
import { ErrorNote } from "./ui";

const blank = () => ({ number: "", text: "", marks: "", topic: "" });

export default function QuestionEditor({ paper, onSaved, onCancel }) {
  const [rows, setRows] = useState(() =>
    paper.questions.length
      ? paper.questions.map((q) => ({ number: q.number, text: q.text, marks: q.marks ?? "", topic: q.topic }))
      : [blank()],
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (i, key) => (e) => setRows((r) => r.map((row, j) => (j === i ? { ...row, [key]: e.target.value } : row)));

  async function save() {
    setBusy(true);
    setError("");
    try {
      const questions = rows
        .filter((r) => r.text.trim())
        .map((r) => ({ number: r.number.trim(), text: r.text, marks: r.marks ? Number(r.marks) : null, topic: r.topic }));
      onSaved(await api(`/papers/${paper.id}/questions/`, { method: "PUT", body: { questions } }));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        Type or correct each question exactly as it appears on the paper. Give sub-questions their own row (1a, 1b…). The topic is the concept
        being tested, e.g. <em>Recursion</em>.
      </p>
      {rows.map((row, i) => (
        <div key={i} className="card space-y-2 p-4" data-testid="editor-row">
          <div className="flex gap-2">
            <input className="input w-20" placeholder="No." value={row.number} onChange={update(i, "number")} aria-label="Question number" />
            <input className="input w-24" placeholder="Marks" inputMode="numeric" value={row.marks} onChange={update(i, "marks")} aria-label="Marks" />
            <input className="input flex-1" placeholder="Topic" value={row.topic} onChange={update(i, "topic")} aria-label="Topic" />
            <button className="px-2 text-stone-400 hover:text-rose-600" onClick={() => setRows((r) => r.filter((_, j) => j !== i))} aria-label="Remove question">
              ✕
            </button>
          </div>
          <textarea className="input min-h-24" placeholder="Question text" value={row.text} onChange={update(i, "text")} aria-label="Question text" />
        </div>
      ))}
      <ErrorNote>{error}</ErrorNote>
      <div className="flex flex-wrap gap-2">
        <button className="btn-secondary" onClick={() => setRows((r) => [...r, blank()])}>
          + Add question
        </button>
        <span className="flex-1" />
        {onCancel && (
          <button className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="btn-primary" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save questions"}
        </button>
      </div>
    </div>
  );
}
