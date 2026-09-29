import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CourseRow, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { paperTitle } from "../lib/format";
import { useFetch } from "../lib/useFetch";

function CourseSearch() {
  const { data: universities } = useFetch("/universities/");
  const [university, setUniversity] = useState(() => localStorage.getItem("pq.university") || "oau");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);

  useEffect(() => {
    localStorage.setItem("pq.university", university);
  }, [university]);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const q = query.trim();
        const data = await api(`/courses/?university=${university}${q ? `&q=${encodeURIComponent(q)}` : ""}`);
        if (!cancelled) setResults(data);
      } catch {
        if (!cancelled) setResults([]);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, university]);

  return (
    <div className="card p-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <select className="input sm:w-44" value={university} onChange={(e) => setUniversity(e.target.value)} aria-label="University">
          {(universities ?? [{ slug: "oau", short_name: "OAU" }]).map((u) => (
            <option key={u.slug} value={u.slug}>
              {u.short_name}
            </option>
          ))}
        </select>
        <input
          className="input py-3 text-base"
          placeholder="Course code or title — e.g. CSC 201"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search courses"
        />
      </div>
      <div className="mt-2">
        {results === null ? (
          <Spinner />
        ) : results.length === 0 ? (
          <p className="px-3 py-4 text-sm text-stone-500">
            {query ? "No course matches that yet." : "No courses yet for this university."}{" "}
            <Link to="/upload" className="font-semibold text-brand-700 hover:underline">
              Upload the first paper →
            </Link>
          </p>
        ) : (
          <div className="divide-y divide-stone-100">
            {results.slice(0, 8).map((c) => (
              <CourseRow key={c.slug} course={c} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Home() {
  const { data: stats } = useFetch("/stats/");

  return (
    <>
      <section className="mb-8 grid gap-8 md:grid-cols-[1fr_1.1fr] md:items-center">
        <div>
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight md:text-5xl">
            Past questions, <span className="text-brand-600">explained.</span>
          </h1>
          <p className="mt-4 text-lg text-stone-600">
            Find past exam papers for your courses, get step-by-step explanations, and see which topics come up every year.
          </p>
          {stats && (
            <p className="mt-4 text-sm text-stone-500">
              <strong className="text-stone-800">{stats.papers}</strong> papers · <strong className="text-stone-800">{stats.questions}</strong> questions ·{" "}
              <strong className="text-stone-800">{stats.courses}</strong> courses, shared by students
            </p>
          )}
        </div>
        <CourseSearch />
      </section>

      <div className="grid gap-6 md:grid-cols-[1.5fr_1fr]">
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">Recently added</h2>
          {!stats ? (
            <Spinner />
          ) : stats.recent_papers.length === 0 ? (
            <div className="card p-6 text-sm text-stone-500">Nothing yet. Be the first to upload a paper.</div>
          ) : (
            <ul className="card divide-y divide-stone-100">
              {stats.recent_papers.map((p) => (
                <li key={p.id}>
                  <Link to={`/p/${p.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-stone-50">
                    <span className="w-20 shrink-0 font-semibold">{p.course.code}</span>
                    <span className="min-w-0 flex-1 truncate text-sm text-stone-600">
                      {p.course.university} · {paperTitle(p)}
                    </span>
                    <span className="text-xs text-stone-400">{p.question_count} Qs</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="space-y-6">
          <div className="card bg-brand-900 p-5 text-white">
            <p className="font-semibold">Got past questions on your phone?</p>
            <p className="mt-1 text-sm text-brand-100">Snap or upload them. We turn them into searchable questions your coursemates can learn from.</p>
            <Link to="/upload" className="btn mt-4 bg-white text-brand-900 hover:bg-brand-50">
              Upload a paper
            </Link>
          </div>
          {stats?.top_contributors.length > 0 && (
            <div className="card p-5">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">Top contributors</h2>
              <ol className="space-y-2 text-sm">
                {stats.top_contributors.map((c, i) => (
                  <li key={c.username} className="flex items-center gap-3">
                    <span className="w-5 text-stone-400">{i + 1}.</span>
                    <span className="flex-1 font-medium">{c.username}</span>
                    <span className="text-stone-500">
                      {c.uploads} paper{c.uploads === 1 ? "" : "s"}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
