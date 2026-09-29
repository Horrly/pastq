import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./lib/auth";
import About from "./pages/About";
import AuthPage from "./pages/AuthPage";
import CoursePage from "./pages/CoursePage";
import Home from "./pages/Home";
import PaperPage from "./pages/PaperPage";
import Practice from "./pages/Practice";
import Upload from "./pages/Upload";

function Header() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const link = ({ isActive }) =>
    `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-stone-600 hover:bg-stone-100"}`;
  return (
    <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center gap-1 px-4 py-3">
        <Link to="/" className="mr-auto flex items-center gap-2 text-lg font-extrabold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm text-white">PQ</span>
          <span>
            Past<span className="text-brand-600">Q</span>
          </span>
        </Link>
        <NavLink to="/upload" className={link}>
          Upload
        </NavLink>
        <NavLink to="/about" className={`${link({ isActive: location.pathname === "/about" })} hidden sm:inline-flex`}>
          About
        </NavLink>
        {user ? (
          <button onClick={logout} className="ml-1 rounded-lg px-3 py-2 text-sm text-stone-500 hover:bg-stone-100" title={`Signed in as ${user.username}`}>
            Log out
          </button>
        ) : (
          <Link to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} className="btn-primary ml-1 py-2">
            Sign in
          </Link>
        )}
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/c/:slug" element={<CoursePage />} />
          <Route path="/c/:slug/practice" element={<Practice />} />
          <Route path="/p/:id" element={<PaperPage />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Home />} />
        </Routes>
      </main>
      <footer className="border-t border-stone-200 py-6 text-center text-xs text-stone-500">
        PastQ · shared by students, for students ·{" "}
        <Link to="/about" className="underline">
          About &amp; takedowns
        </Link>
      </footer>
    </div>
  );
}
