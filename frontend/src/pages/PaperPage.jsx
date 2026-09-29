import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import QuestionCard from "../components/QuestionCard";
import QuestionEditor from "../components/QuestionEditor";
import { Empty, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { STATUS_NOTE, paperTitle } from "../lib/format";
import { useFetch } from "../lib/useFetch";

function FlagButton({ paperId }) {
  const { user } = useAuth();
  const [done, setDone] = useState(false);
  if (!user) return null;
  async function flag() {
    const reason = window.prompt("What's wrong with this paper? (wrong course, duplicate, unreadable, shouldn't be here…)");
    if (!reason) return;
    await api(`/papers/${paperId}/flag/`, { method: "POST", body: { reason } });
    setDone(true);
  }
  return (
    <button onClick={flag} disabled={done} className="text-xs text-stone-400 hover:text-rose-600">
      {done ? "Reported. Thanks!" : "Report a problem"}
    </button>
  );
}

export default function PaperPage() {
  const { id } = useParams();
  const { data: paper, loading, error, reload, setData } = useFetch(`/papers/${id}/`);
  const { data: config } = useFetch("/config/");
  const [tab, setTab] = useState("questions");
  const [editing, setEditing] = useState(false);

  // While the AI reads the paper, check back every few seconds.
  useEffect(() => {
    if (paper?.status !== "processing") return;
    const t = setInterval(reload, 3000);
    return () => clearInterval(t);
  }, [paper?.status, reload]);

  if (loading) return <Spinner />;
  if (error) return <Empty icon="🔎" title="Paper not found">It may have been removed.</Empty>;

  const aiEnabled = Boolean(config?.ai_enabled);

  async function retry() {
    await api(`/papers/${id}/retry/`, { method: "POST" });
    reload();
  }

  return (
    <>
      <Link to={`/c/${paper.course.slug}`} className="text-sm text-stone-500 hover:underline">
        ← {paper.course.university} {paper.course.code}
      </Link>
      <div className="mb-5 mt-1 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold">
            {paper.course.code}: {paper.course.title}
          </h1>
          <p className="text-stone-600">{paperTitle(paper)}</p>
          {paper.uploaded_by && <p className="text-xs text-stone-400">Shared by {paper.uploaded_by}</p>}
        </div>
        <div className="flex rounded-lg border border-stone-200 bg-white p-1 text-sm">
          {[["questions", `Questions (${paper.questions.length})`], ["pages", `Original (${paper.pages.length} pages)`]].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} className={`rounded-md px-3 py-1.5 ${tab === key ? "bg-brand-600 text-white" : "text-stone-600"}`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {config?.fake_ai && (
        <p className="mb-4 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Development mode: questions and explanations come from a fake AI provider.
        </p>
      )}

      {tab === "pages" ? (
        <div className="space-y-4">
          {paper.pages.map((p) => (
            <img key={p.order} src={p.url} alt={`Page ${p.order + 1}`} loading="lazy" className="w-full rounded-xl border border-stone-200 bg-white" />
          ))}
        </div>
      ) : editing ? (
        <QuestionEditor
          paper={paper}
          onCancel={() => setEditing(false)}
          onSaved={(updated) => {
            setData(updated);
            setEditing(false);
          }}
        />
      ) : (
        <div className="space-y-4">
          {paper.status === "processing" && (
            <div className="card flex items-center gap-3 p-5 text-sm text-stone-600" data-testid="processing">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-stone-300 border-t-brand-600" />
              {STATUS_NOTE.processing}
            </div>
          )}

          {paper.status === "needs_text" && (
            <div className="card p-5 text-sm">
              <p className="font-medium">{STATUS_NOTE.needs_text}</p>
              {paper.processing_error && <p className="mt-1 text-stone-500">{paper.processing_error}</p>}
              <div className="mt-3 flex flex-wrap gap-2">
                {paper.can_edit && (
                  <button className="btn-primary" onClick={() => setEditing(true)}>
                    Type the questions
                  </button>
                )}
                {paper.can_edit && aiEnabled && (
                  <button className="btn-secondary" onClick={retry}>
                    Try reading it again
                  </button>
                )}
                <button className="btn-secondary" onClick={() => setTab("pages")}>
                  View the original pages
                </button>
              </div>
            </div>
          )}

          {paper.instructions && <p className="rounded-lg bg-stone-100 px-4 py-3 text-sm italic text-stone-700">{paper.instructions}</p>}

          {paper.questions.map((q) => (
            <QuestionCard key={q.id} question={q} courseSlug={paper.course.slug} aiEnabled={aiEnabled} />
          ))}

          <div className="flex items-center justify-between pt-2">
            {paper.can_edit && paper.questions.length > 0 ? (
              <button className="text-sm font-medium text-brand-700 hover:underline" onClick={() => setEditing(true)}>
                ✎ Correct the questions
              </button>
            ) : (
              <span />
            )}
            <FlagButton paperId={paper.id} />
          </div>
        </div>
      )}
    </>
  );
}
