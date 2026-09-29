import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import QuestionCard from "../components/QuestionCard";
import { Empty, Spinner } from "../components/ui";
import { useFetch } from "../lib/useFetch";

export default function Practice() {
  const { slug } = useParams();
  const [params] = useSearchParams();
  const topic = params.get("topic");
  const [round, setRound] = useState(0);
  const { data: questions, loading } = useFetch(`/courses/${slug}/practice/?n=10${topic ? `&topic=${encodeURIComponent(topic)}` : ""}&r=${round}`);
  const { data: config } = useFetch("/config/");
  const [index, setIndex] = useState(0);

  if (loading) return <Spinner />;
  if (!questions?.length) return <Empty icon="🧩" title="No questions to practise yet" />;

  const q = questions[index];
  const done = index >= questions.length - 1;

  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/c/${slug}`} className="text-sm text-stone-500 hover:underline">
        ← Back to course
      </Link>
      <div className="mb-4 mt-2 flex items-end justify-between">
        <h1 className="text-2xl font-extrabold">Practice{topic ? `: ${topic}` : ""}</h1>
        <span className="text-sm text-stone-500">
          {index + 1} / {questions.length}
        </span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-stone-200">
        <div className="h-full bg-brand-500 transition-all" style={{ width: `${((index + 1) / questions.length) * 100}%` }} />
      </div>

      <p className="mb-2 text-xs text-stone-500">
        From the{" "}
        <Link to={`/p/${q.paper.id}`} className="underline">
          {q.paper.session} {q.paper.kind.toLowerCase()}
        </Link>
        . Try it yourself first, then check the explanation.
      </p>
      <QuestionCard key={q.id} question={q} courseSlug={slug} aiEnabled={Boolean(config?.ai_enabled)} />

      <div className="mt-4 flex justify-between">
        <button className="btn-secondary" onClick={() => setIndex((i) => i - 1)} disabled={index === 0}>
          ← Previous
        </button>
        {done ? (
          <button
            className="btn-primary"
            onClick={() => {
              setIndex(0);
              setRound((r) => r + 1);
            }}
          >
            New set ↻
          </button>
        ) : (
          <button className="btn-primary" onClick={() => setIndex((i) => i + 1)}>
            Next →
          </button>
        )}
      </div>
    </div>
  );
}
