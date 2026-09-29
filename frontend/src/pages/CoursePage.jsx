import { Link, useParams } from "react-router-dom";
import { Empty, Spinner } from "../components/ui";
import { topicShare } from "../lib/format";
import { useFetch } from "../lib/useFetch";

export default function CoursePage() {
  const { slug } = useParams();
  const { data: course, loading, error } = useFetch(`/courses/${slug}/`);

  if (loading) return <Spinner />;
  if (error) return <Empty icon="🔎" title="Course not found" />;

  const bySession = course.papers.reduce((acc, p) => {
    (acc[p.session] ??= []).push(p);
    return acc;
  }, {});

  return (
    <>
      <p className="text-sm text-stone-500">
        <Link to="/" className="hover:underline">
          {course.university_name}
        </Link>
        {course.level ? ` · ${course.level} level` : ""}
        {course.department ? ` · ${course.department}` : ""}
      </p>
      <div className="mb-6 mt-1 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold">{course.code}</h1>
          <p className="text-lg text-stone-600">{course.title}</p>
        </div>
        <div className="flex gap-2">
          {course.paper_total > 0 && (
            <Link to={`/c/${slug}/practice`} className="btn-primary">
              Practice questions
            </Link>
          )}
          <Link to={`/upload?course=${slug}`} className="btn-secondary">
            + Add a paper
          </Link>
        </div>
      </div>

      {course.paper_total === 0 ? (
        <Empty icon="📄" title="No papers for this course yet">
          Have one? <Link to={`/upload?course=${slug}`} className="font-semibold text-brand-700 hover:underline">Upload it</Link> and help your coursemates.
        </Empty>
      ) : (
        <div className="grid gap-6 md:grid-cols-[1fr_1.2fr]">
          <section className="card p-5">
            <h2 className="font-semibold">Most examined topics</h2>
            <p className="mb-4 text-xs text-stone-500">Across {course.paper_total} paper{course.paper_total === 1 ? "" : "s"}. Tap a topic to practise it.</p>
            {course.top_topics.length === 0 ? (
              <p className="text-sm text-stone-500">Topics appear once questions are added.</p>
            ) : (
              <ul className="space-y-3">
                {course.top_topics.map((t) => {
                  const share = topicShare(t, course.paper_total);
                  return (
                    <li key={t.topic}>
                      <Link to={`/c/${slug}/practice?topic=${encodeURIComponent(t.topic)}`} className="group block">
                        <div className="mb-1 flex justify-between text-sm">
                          <span className="font-medium group-hover:text-brand-700">{t.topic}</span>
                          <span className="text-stone-500">
                            {t.papers} of {course.paper_total} papers · {t.questions} Q{t.questions === 1 ? "" : "s"}
                          </span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-stone-100">
                          <div className="h-full rounded-full bg-brand-500" style={{ width: `${share}%` }} />
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section>
            <h2 className="mb-3 font-semibold">Papers</h2>
            <div className="space-y-4">
              {Object.entries(bySession).map(([session, papers]) => (
                <div key={session}>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">{session} session</p>
                  <ul className="card divide-y divide-stone-100">
                    {papers.map((p) => (
                      <li key={p.id}>
                        <Link to={`/p/${p.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-stone-50" data-testid="paper-row">
                          <span className="flex-1 font-medium">
                            {p.semester_label} {p.kind_label.toLowerCase()}
                          </span>
                          {p.status === "processing" ? (
                            <span className="text-xs text-amber-600">Reading…</span>
                          ) : (
                            <span className="text-xs text-stone-500">{p.question_count} questions</span>
                          )}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </>
  );
}
