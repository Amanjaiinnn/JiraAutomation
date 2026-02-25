import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app";
import "./styles.css";

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error?.message || "Unknown UI error" };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("React render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "24px", fontFamily: "Arial, sans-serif" }}>
          <h2>UI failed to render</h2>
          <p>{this.state.errorMessage}</p>
          <p>Open browser console for details and refresh after fixing the error.</p>
        </div>
      );
    }

    return this.props.children;
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Missing #root element in index.html");
}

createRoot(rootElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>
);