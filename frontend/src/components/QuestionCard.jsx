import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Markdown, TopicChip } from "./ui";

export default function QuestionCard({ question, courseSlug, aiEnabled, footer }) {
  const { user } = useAuth();
  const location = useLocation();
  const [explanation, setExplanation] = useState(question.explanation);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function explain() {
    if (explanation) {
      setOpen((o) => !o);
      return;
    }
    setBusy(true);
    setError("");
    try {
      setExplanation(await api(`/questions/${question.id}/explain/`, { method: "POST" }));
      setOpen(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function vote(value) {
    try {
      setExplanation(await api(`/explanations/${explanation.id}/vote/`, { method: "POST", body: { value } }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <article className="card p-5" data-testid="question">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-stone-900 px-2 py-0.5 text-xs font-bold text-white">Q{question.number}</span>
        {question.marks && <span className="text-xs text-stone-500">{question.marks} marks</span>}
        <TopicChip topic={question.topic} to={question.topic && courseSlug ? `/c/${courseSlug}/practice?topic=${encodeURIComponent(question.topic)}` : null} />
      </div>
      <p className="whitespace-pre-wrap leading-relaxed text-stone-800">{question.text}</p>

      {(aiEnabled || explanation) && (
        <div className="mt-4">
          {user || explanation ? (
            <button className={explanation ? "btn-secondary" : "btn-primary"} onClick={explain} disabled={busy}>
              {busy ? "Working it out…" : explanation ? (open ? "Hide explanation" : "Show explanation") : "✨ Explain step by step"}
            </button>
          ) : (
            <Link to={`/login?next=${encodeURIComponent(location.pathname)}`} className="btn-secondary">
              Sign in to get an explanation
            </Link>
          )}
          {busy && <p className="mt-2 text-xs text-stone-500">This takes about 10 seconds the first time. After that, it's instant for everyone.</p>}
          {error && <p className="mt-2 text-sm text-rose-600">{error}</p>}
        </div>
      )}

      {open && explanation && (
        <div className="mt-4 rounded-xl border border-brand-100 bg-brand-50/40 p-4" data-testid="explanation">
          <Markdown text={explanation.text} />
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-brand-100 pt-3 text-xs text-stone-500">
            <span className="mr-auto">AI-generated. Check it against your notes.</span>
            {user && (
              <>
                <span>Helpful?</span>
                <button onClick={() => vote(1)} className={`rounded-md border px-2 py-1 ${explanation.my_vote === 1 ? "border-brand-500 bg-brand-100 text-brand-700" : "border-stone-200 bg-white"}`}>
                  👍 {explanation.helpful}
                </button>
                <button onClick={() => vote(-1)} className={`rounded-md border px-2 py-1 ${explanation.my_vote === -1 ? "border-rose-400 bg-rose-50 text-rose-700" : "border-stone-200 bg-white"}`}>
                  👎 {explanation.not_helpful}
                </button>
              </>
            )}
          </div>
        </div>
      )}
      {footer}
    </article>
  );
}
