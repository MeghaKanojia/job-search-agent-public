import { useState } from "react";
import { NavLink, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Analytics from "./pages/Analytics";
import ApplicationsTracker from "./pages/ApplicationsTracker";
import NewMatches from "./pages/NewMatches";
import Profile from "./pages/Profile";
import ResumeLibrary from "./pages/ResumeLibrary";
import ReviewQueue from "./pages/ReviewQueue";
import SettingsPage from "./pages/Settings";
import { getAuthHeader, setAuthHeader } from "./api/client";
import LoadingIndicator from "./components/LoadingIndicator";
import Login from "./components/Login";
import { ToastProvider } from "./components/Toast";

const NAV_ITEMS = [
  { to: "/", label: "New Matches" },
  { to: "/review", label: "Review Queue" },
  { to: "/tracker", label: "Applications" },
  { to: "/resumes", label: "Resume Library" },
  { to: "/analytics", label: "Analytics" },
  { to: "/profile", label: "Profile" },
  { to: "/settings", label: "Settings" },
];

export default function App() {
  const [authed, setAuthed] = useState(() => !!getAuthHeader());

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  const signOut = () => {
    setAuthHeader(null);
    setAuthed(false);
  };

  return (
    <ToastProvider>
      <LoadingIndicator />
      <Router>
        <div className="app-shell">
          <nav className="sidebar">
            <div className="sidebar-profile-card">
              <div className="sidebar-avatar">
                <img src="/logo.png" alt="Job Search Agent logo" />
              </div>
              <div className="sidebar-name">Job Search Agent</div>
              <div className="sidebar-tagline">AI-tailored job search, end to end</div>
            </div>

            <div className="sidebar-nav-card">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
                >
                  {item.label}
                </NavLink>
              ))}
              <button className="nav-link sign-out-link" onClick={signOut}>
                Sign out
              </button>
            </div>

            <div className="sidebar-footer-card">
              Zero-budget pipeline: ingestion, RAG-tailored resumes and cover letters, and
              application tracking, end to end.
            </div>
          </nav>
          <main className="main-content">
            <Routes>
              <Route path="/" element={<NewMatches />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/tracker" element={<ApplicationsTracker />} />
              <Route path="/resumes" element={<ResumeLibrary />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ToastProvider>
  );
}
