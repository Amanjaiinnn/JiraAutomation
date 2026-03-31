import React, { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api/client";

const workflowTitles = [
  "As a user, I want to register with a valid email and password to access the system.",
  "As a user, I want to log in with a valid email and password to access the system.",
  "As a user, I want to log out of the system to ensure security."
];

const ROUTES = {
  register: "#/register",
  login: "#/login",
  dashboard: "#/dashboard",
};

const getCurrentView = () => {
  const hash = window.location.hash || ROUTES.register;
  if (hash === ROUTES.login) return "login";
  if (hash === ROUTES.dashboard) return "dashboard";
  return "register";
};

const emptyRegisterForm = { name: "", email: "", password: "" };
const emptyLoginForm = { email: "", password: "" };

export function AuthPage({ onAuthenticated = () => {}, onLoggedOut = () => {} }) {
  const [view, setView] = useState(getCurrentView);
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm);
  const [loginForm, setLoginForm] = useState(emptyLoginForm);
  const [session, setSession] = useState({ is_authenticated: false, user: null });
  const [banner, setBanner] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const applyView = (nextView) => {
    window.location.hash = ROUTES[nextView] || ROUTES.register;
    setView(nextView);
  };

  const refreshSession = async () => {
    const sessionData = await apiGet("/auth/session");
    setSession(sessionData || { is_authenticated: false, user: null });
    if (sessionData?.is_authenticated && getCurrentView() !== "dashboard") {
      applyView("dashboard");
    }
    return sessionData;
  };

  useEffect(() => {
    const syncFromHash = () => setView(getCurrentView());
    window.addEventListener("hashchange", syncFromHash);
    refreshSession().catch((requestError) => setError(requestError.message));
    syncFromHash();
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  const welcomeTitle = useMemo(() => {
    if (session?.user?.name) return `Welcome back, ${session.user.name}`;
    return "Authentication workspace";
  }, [session]);

  const handleRegister = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/register", registerForm);
      setBanner(data.message || "Account created successfully");
      setRegisterForm(emptyRegisterForm);
      await refreshSession();
      applyView("login");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/login", loginForm);
      setBanner(data.message || "Logged in successfully");
      setLoginForm(emptyLoginForm);
      const sessionData = await refreshSession();
      if (sessionData?.is_authenticated) {
        onAuthenticated(sessionData);
      }
      applyView("dashboard");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    setError("");
    setBanner(null);
    try {
      const data = await apiPost("/auth/logout", {});
      setBanner(data.message || "Logged out successfully");
      setSession({ is_authenticated: false, user: null });
      applyView("login");
      onLoggedOut();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <header className="auth-header">
        <div>
          <h1>{welcomeTitle}</h1>
          <p className="hero-copy">Sign in first to unlock the application. Protected pages and navigation stay hidden until the session is authenticated.</p>
          {workflowTitles.length ? (
            <div className="button-row" style={{ marginTop: 12 }}>
              {workflowTitles.map((title) => (
                <span key={title} className="status-badge">{title}</span>
              ))}
            </div>
          ) : null}
        </div>
      </header>

      {banner ? <div className="feedback-banner success">{banner}</div> : null}
      {error ? <div className="feedback-banner error">{error}</div> : null}

      <section className="auth-content auth-content-single">
        <article className="auth-panel auth-panel-primary">
          {view === "register" ? (
            <>
              <h2>Create your account</h2>
              <p className="panel-copy">Register with your name, email, and password. After success, you will be guided to the login page.</p>
              <form className="auth-form" onSubmit={handleRegister}>
                <label>
                  <span>Full Name</span>
                  <input value={registerForm.name} onChange={(event) => setRegisterForm((previous) => ({ ...previous, name: event.target.value }))} placeholder="Aman Verma" />
                </label>
                <label>
                  <span>Email</span>
                  <input type="email" value={registerForm.email} onChange={(event) => setRegisterForm((previous) => ({ ...previous, email: event.target.value }))} placeholder="aman@example.com" />
                </label>
                <label>
                  <span>Password</span>
                  <input type="password" value={registerForm.password} onChange={(event) => setRegisterForm((previous) => ({ ...previous, password: event.target.value }))} placeholder="Choose a strong password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? "Creating account..." : "Create Account"}</button>
              </form>
              <p className="muted">Already have an account? <button type="button" className="inline-action" onClick={() => applyView("login")}>Go to login</button></p>
            </>
          ) : null}

          {view === "login" ? (
            <>
              <h2>Sign in to continue</h2>
              <p className="panel-copy">Use the credentials stored in PostgreSQL to create an authenticated session.</p>
              <form className="auth-form" onSubmit={handleLogin}>
                <label>
                  <span>Email</span>
                  <input type="email" value={loginForm.email} onChange={(event) => setLoginForm((previous) => ({ ...previous, email: event.target.value }))} placeholder="aman@example.com" />
                </label>
                <label>
                  <span>Password</span>
                  <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((previous) => ({ ...previous, password: event.target.value }))} placeholder="Enter your password" />
                </label>
                <button type="submit" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
              </form>
              <p className="muted">Need an account first? <button type="button" className="inline-action" onClick={() => applyView("register")}>Create one</button></p>
            </>
          ) : null}

          {view === "dashboard" ? (
            <>
              <h2>Authenticated dashboard</h2>
              <p className="panel-copy">Logout is available only while the session is active, and the header updates immediately after sign in or sign out.</p>
              <div className="session-card">
                <p><strong>Status:</strong> {session?.is_authenticated ? "Logged in" : "Logged out"}</p>
                <p><strong>Name:</strong> {session?.user?.name || "Guest"}</p>
                <p><strong>Email:</strong> {session?.user?.email || "Not available"}</p>
              </div>
              <div className="button-row">
                <button type="button" className="logout-button" onClick={handleLogout} disabled={loading}>
                  {loading ? "Signing out..." : "Logout"}
                </button>
              </div>
            </>
          ) : null}
        </article>
      </section>
    </div>
  );
}
