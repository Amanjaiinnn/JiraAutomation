import React, { useEffect, useMemo, useState } from "react";
import { AuthPage } from "./pages/AuthPage";
import { TasksPage } from "./pages/TasksPage";
import { apiGet, apiPost } from "./api/client";

const pageMap = {
  "auth": AuthPage,
  "tasks": TasksPage
};

export function App() {
  const [activePage, setActivePage] = useState("tasks");
  const [session, setSession] = useState({ is_authenticated: false, user: null });
  const [sessionLoading, setSessionLoading] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const hasAuth = true;
  const contentModules = ["tasks"];

  const refreshSession = async () => {
    if (!hasAuth) {
      return;
    }
    setSessionLoading(true);
    setSessionError("");
    try {
      const data = await apiGet("/auth/session");
      setSession(data || { is_authenticated: false, user: null });
    } catch (error) {
      setSessionError(error.message);
      setSession({ is_authenticated: false, user: null });
    } finally {
      setSessionLoading(false);
    }
  };

  const applyAuthenticatedSession = (nextSession) => {
    setSession(nextSession || { is_authenticated: true, user: null });
    setSessionError("");
    setSessionLoading(false);
    if (contentModules.length && !contentModules.includes(activePage)) {
      setActivePage(contentModules[0]);
    }
  };

  const applyLoggedOutState = () => {
    setSession({ is_authenticated: false, user: null });
    setSessionLoading(false);
  };

  useEffect(() => {
    refreshSession();
  }, []);

  useEffect(() => {
    if (!contentModules.length) {
      setActivePage(hasAuth ? "auth" : "");
      return;
    }
    if (!contentModules.includes(activePage)) {
      setActivePage(contentModules[0]);
    }
  }, [activePage, hasAuth]);

  const ActivePage = useMemo(() => pageMap[activePage], [activePage]);

  const handleLogout = async () => {
    try {
      await apiPost("/auth/logout", {});
    } catch (_error) {
      // Keep the UI gated even if the backend session is already invalid.
    }
    applyLoggedOutState();
    setActivePage(contentModules[0] || "auth");
  };

  if (hasAuth && sessionLoading) {
    return (
      <div className="shell">
        <section className="auth-panel auth-panel-primary">
          <h2>Checking your session</h2>
          <p className="panel-copy">Protected content stays hidden until authentication is confirmed.</p>
        </section>
      </div>
    );
  }

  if (hasAuth && !session?.is_authenticated) {
    const AuthPage = pageMap.auth;
    return AuthPage ? <AuthPage onAuthenticated={applyAuthenticatedSession} onLoggedOut={applyLoggedOutState} /> : null;
  }

  if (hasAuth && !contentModules.length) {
    const AuthPage = pageMap.auth;
    return AuthPage ? <AuthPage onAuthenticated={applyAuthenticatedSession} onLoggedOut={applyLoggedOutState} /> : null;
  }

  return (
    <div className="shell">
      <header className="app-topbar">
        <div>
          <h1>Generated Story Application</h1>
          <p>A cohesive, production-style workflow generated from your current stories with consistent UI, connected services, and PostgreSQL-backed persistence.</p>
        </div>
      </header>
      {hasAuth ? (
        <section className="session-strip">
          <div>
            <strong>{session?.user?.name || "Authenticated user"}</strong>
            <p className="muted">{sessionError || session?.user?.email || "Your protected workspace is unlocked."}</p>
          </div>
          <button type="button" className="ghost-button" onClick={handleLogout}>Logout</button>
        </section>
      ) : null}
      {contentModules.length ? (
        <nav className="app-nav">
          <button key="tasks" className={activePage === "tasks" ? "active" : ""} onClick={() => setActivePage("tasks")}>Tasks</button>
        </nav>
      ) : null}
      <div className="page">
        {ActivePage ? <ActivePage /> : <p>No modules generated yet.</p>}
      </div>
    </div>
  );
}
