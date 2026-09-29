import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorNote, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { normalizeCode, sessionYears } from "../lib/format";
import { useFetch } from "../lib/useFetch";

function NewCourseForm({ university, initialCode, onCreated, onCancel }) {
  const [form, setForm] = useState({ code: initialCode, title: "", level: "", department: "" });
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function create() {
    setError("");
    try {
      const course = await api("/courses/", {
        method: "POST",
        body: { university, code: form.code, title: form.title, department: form.department, level: form.level ? Number(form.level) : null },
      });
      onCreated(course);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-xl bg-stone-50 p-4">
      <p className="text-sm font-medium">Add a new course</p>
      <div className="grid gap-2 sm:grid-cols-[140px_1fr]">
        <input className="input" placeholder="Code, e.g. CSC 201" value={form.code} onChange={set("code")} aria-label="Course code" />
        <input className="input" placeholder="Title, e.g. Computer Programming I" value={form.title} onChange={set("title")} aria-label="Course title" />
        <select className="input" value={form.level} onChange={set("level")} aria-label="Level">
          <option value="">Level (optional)</option>
          {[100, 200, 300, 400, 500].map((l) => (
            <option key={l} value={l}>
              {l} level
            </option>
          ))}
        </select>
        <input className="input" placeholder="Department (optional)" value={form.department} onChange={set("department")} aria-label="Department" />
      </div>
      {form.code && <p className="text-xs text-stone-500">Will be saved as {normalizeCode(form.code)}.</p>}
      <ErrorNote>{error}</ErrorNote>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={create} disabled={!form.code || !form.title}>
          Add course
        </button>
        <button className="btn-secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function CoursePicker({ value, onChange }) {
  const { data: universities } = useFetch("/universities/");
  const [university, setUniversity] = useState(() => localStorage.getItem("pq.university") || "oau");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (value || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      api(`/courses/?university=${university}&q=${encodeURIComponent(query.trim())}`).then(setResults).catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [query, university, value]);

  if (value) {
    return (
      <div className="flex items-center justify-between rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
        <div>
          <p className="font-semibold">
            {value.university_name ?? value.university} {value.code}
          </p>
          <p className="text-sm text-stone-600">{value.title}</p>
        </div>
        <button className="text-sm text-brand-700 hover:underline" onClick={() => onChange(null)}>
          Change
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <select className="input sm:w-40" value={university} onChange={(e) => setUniversity(e.target.value)} aria-label="University">
          {(universities ?? []).map((u) => (
            <option key={u.slug} value={u.slug}>
              {u.short_name}
            </option>
          ))}
        </select>
        <input className="input" placeholder="Find the course — e.g. CSC 201" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Find course" />
      </div>
      {results.length > 0 && (
        <ul className="mt-2 divide-y divide-stone-100 rounded-xl border border-stone-200 bg-white">
          {results.map((c) => (
            <li key={c.slug}>
              <button className="w-full px-4 py-2.5 text-left hover:bg-stone-50" onClick={() => onChange(c)}>
                <span className="font-semibold">{c.code}</span> <span className="text-sm text-stone-500">{c.title}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {!adding && query.trim().length >= 2 && (
        <button className="mt-2 text-sm font-medium text-brand-700 hover:underline" onClick={() => setAdding(true)}>
          Can't find it? Add “{normalizeCode(query)}” as a new course
        </button>
      )}
      {adding && (
        <NewCourseForm
          university={university}
          initialCode={query}
          onCancel={() => setAdding(false)}
          onCreated={(c) => {
            setAdding(false);
            onChange(c);
          }}
        />
      )}
    </div>
  );
}

export default function Upload() {
  const { user, loading: authLoading } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { data: preselected } = useFetch(params.get("course") ? `/courses/${params.get("course")}/` : null);
  const { data: config } = useFetch("/config/");

  const [course, setCourse] = useState(null);
  const [details, setDetails] = useState({ year: sessionYears()[1], semester: "first", kind: "exam" });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (preselected && !course) setCourse(preselected);
  }, [preselected, course]);

  const previews = useMemo(() => files.map((f) => ({ name: f.name, url: f.type.startsWith("image/") ? URL.createObjectURL(f) : null })), [files]);
  useEffect(() => () => previews.forEach((p) => p.url && URL.revokeObjectURL(p.url)), [previews]);

  if (authLoading) return <Spinner />;
  if (!user) {
    return (
      <div className="card mx-auto max-w-md p-8 text-center">
        <p className="text-4xl">📤</p>
        <p className="mt-3 font-semibold">Sign in to upload a paper</p>
        <p className="mt-1 text-sm text-stone-500">It's free, and your name appears on the papers you share.</p>
        <Link to="/login?next=/upload" className="btn-primary mt-4">
          Sign in
        </Link>
      </div>
    );
  }

  const set = (k) => (e) => setDetails((d) => ({ ...d, [k]: e.target.value }));

  async function submit() {
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.append("course", course.slug);
    Object.entries(details).forEach(([k, v]) => form.append(k, v));
    files.forEach((f) => form.append("files", f));
    try {
      const paper = await api("/papers/", { method: "POST", body: form });
      navigate(`/p/${paper.id}`);
    } catch (err) {
      setError({ text: err.message, paperId: err.data?.paper_id });
      setBusy(false);
    }
  }

  const step = "flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-600 text-sm font-bold text-white";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold">Upload a past paper</h1>
        <p className="text-stone-600">
          Photos from your phone are fine. {config?.ai_enabled ? "We'll read the questions for you." : "You'll type the questions in after uploading."}
        </p>
      </div>

      <section className="card space-y-3 p-5">
        <div className="flex items-center gap-3">
          <span className={step}>1</span>
          <h2 className="font-semibold">Which course?</h2>
        </div>
        <CoursePicker value={course} onChange={setCourse} />
      </section>

      <section className={`card space-y-3 p-5 ${course ? "" : "opacity-50"}`}>
        <div className="flex items-center gap-3">
          <span className={step}>2</span>
          <h2 className="font-semibold">Which sitting?</h2>
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <select className="input" value={details.year} onChange={set("year")} disabled={!course} aria-label="Session">
            {sessionYears().map((y) => (
              <option key={y} value={y}>
                {y}/{y + 1} session
              </option>
            ))}
          </select>
          <select className="input" value={details.semester} onChange={set("semester")} disabled={!course} aria-label="Semester">
            <option value="first">First semester</option>
            <option value="second">Second semester</option>
            <option value="other">Other</option>
          </select>
          <select className="input" value={details.kind} onChange={set("kind")} disabled={!course} aria-label="Type">
            <option value="exam">Exam</option>
            <option value="test">Test</option>
            <option value="other">Other</option>
          </select>
        </div>
      </section>

      <section className={`card space-y-3 p-5 ${course ? "" : "opacity-50"}`}>
        <div className="flex items-center gap-3">
          <span className={step}>3</span>
          <h2 className="font-semibold">Photos or PDF of the paper</h2>
        </div>
        <label className={`block cursor-pointer rounded-xl border-2 border-dashed border-stone-300 p-6 text-center hover:border-brand-500 ${course ? "" : "pointer-events-none"}`}>
          <span className="text-3xl">📷</span>
          <span className="mt-2 block text-sm font-medium">Tap to choose photos or a PDF</span>
          <span className="block text-xs text-stone-500">
            Up to {config?.max_pages ?? 12} pages, {config?.max_file_mb ?? 10} MB each. Make sure the text is sharp and well lit.
          </span>
          <input
            type="file"
            accept="image/*,application/pdf"
            multiple
            className="sr-only"
            onChange={(e) => setFiles((prev) => [...prev, ...Array.from(e.target.files)])}
            aria-label="Paper files"
          />
        </label>
        {files.length > 0 && (
          <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {previews.map((p, i) => (
              <li key={i} className="relative overflow-hidden rounded-lg border border-stone-200 bg-stone-50">
                {p.url ? <img src={p.url} alt="" className="h-28 w-full object-cover" /> : <div className="grid h-28 place-items-center text-xs text-stone-500">📄 {p.name}</div>}
                <button
                  className="absolute right-1 top-1 rounded-full bg-white/90 px-1.5 text-xs text-stone-600 shadow"
                  onClick={() => setFiles((f) => f.filter((_, j) => j !== i))}
                  aria-label={`Remove ${p.name}`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {error && (
        <ErrorNote>
          {error.text}{" "}
          {error.paperId && (
            <Link to={`/p/${error.paperId}`} className="font-semibold underline">
              Open it
            </Link>
          )}
        </ErrorNote>
      )}
      <button className="btn-primary w-full py-3 text-base" disabled={!course || files.length === 0 || busy} onClick={submit}>
        {busy ? "Uploading…" : "Upload paper"}
      </button>
      <p className="text-center text-xs text-stone-500">Only share papers students already circulate. Don't upload marking schemes or anything confidential.</p>
    </div>
  );
}
