import { Link } from "react-router-dom";
import { renderMarkdown } from "../lib/markdown";

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-stone-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-stone-300 border-t-brand-600" />
      {label}
    </div>
  );
}

export function Empty({ icon = "📄", title, children }) {
  return (
    <div className="card px-6 py-12 text-center">
      <div className="text-4xl">{icon}</div>
      <p className="mt-3 font-semibold">{title}</p>
      {children && <div className="mt-2 text-sm text-stone-500">{children}</div>}
    </div>
  );
}

export function ErrorNote({ children }) {
  if (!children) return null;
  return <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{children}</p>;
}

export function Markdown({ text }) {
  return <div className="prose-pq text-sm text-stone-700" dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }} />;
}

export function TopicChip({ topic, to }) {
  if (!topic) return null;
  const cls = "inline-block rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700";
  return to ? (
    <Link to={to} className={`${cls} hover:bg-brand-100`}>
      {topic}
    </Link>
  ) : (
    <span className={cls}>{topic}</span>
  );
}

export function CourseRow({ course }) {
  return (
    <Link to={`/c/${course.slug}`} className="flex items-center gap-3 rounded-xl px-3 py-3 hover:bg-stone-50" data-testid="course-row">
      <span className="grid h-10 w-14 shrink-0 place-items-center rounded-lg bg-brand-50 text-xs font-bold text-brand-700">
        {course.university_name ?? course.university}
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{course.code}</p>
        <p className="truncate text-sm text-stone-500">{course.title}</p>
      </div>
      <span className="text-xs text-stone-500">
        {course.paper_count} paper{course.paper_count === 1 ? "" : "s"}
      </span>
    </Link>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-stone-600">{label}</span>
      <div className="mt-1">{children}</div>
      {hint && <span className="mt-1 block text-xs text-stone-400">{hint}</span>}
    </label>
  );
}
