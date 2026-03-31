import React, { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../api/client";

const workflows = [
  {
    "storyKey": "story",
    "title": "Story",
    "fields": [
      "title",
      "details"
    ],
    "submitPath": "/story/submit",
    "listPath": "/story",
    "routeName": "submit"
  }
];

const buildInitialForms = () =>
  Object.fromEntries(
    workflows.map((workflow) => [
      workflow.storyKey,
      Object.fromEntries(workflow.fields.map((field) => [field, ""])),
    ]),
  );

export function StoryPage() {
  const [forms, setForms] = useState(buildInitialForms);
  const [items, setItems] = useState([]);
  const [results, setResults] = useState({});
  const [activeWorkflow, setActiveWorkflow] = useState(workflows[0]?.storyKey || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const currentWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.storyKey === activeWorkflow) || workflows[0],
    [activeWorkflow],
  );

  const load = async () => {
    const data = await apiGet(workflows[0]?.listPath || "/story");
    setItems(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    load();
  }, []);

  const submit = async (event, workflow) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await apiPost(workflow.submitPath, forms[workflow.storyKey] || {});
      setResults((previous) => ({ ...previous, [workflow.storyKey]: data }));
      setForms((previous) => ({
        ...previous,
        [workflow.storyKey]: Object.fromEntries(workflow.fields.map((field) => [field, ""])),
      }));
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="module-shell">
      <section className="module-hero">
        <h2>Story</h2>
        <p>Review the latest records, submit new entries, and manage this workflow from a single page.</p>
      </section>

      <div className="module-layout">
        <article className="module-panel">
          <div className="button-row">
            {workflows.map((workflow) => (
              <button
                key={workflow.storyKey}
                type="button"
                className={activeWorkflow === workflow.storyKey ? "primary-button" : "ghost-button"}
                onClick={() => setActiveWorkflow(workflow.storyKey)}
              >
                {workflow.storyKey.replace(/_/g, " ")}
              </button>
            ))}
          </div>

          {currentWorkflow ? (
            <>
              <h3 style={{ marginTop: 20 }}>{currentWorkflow.title}</h3>
              <form onSubmit={(event) => submit(event, currentWorkflow)}>
                <div className="form-grid">
                  {currentWorkflow.fields.map((field, index) => (
                    <label key={field} className={index === currentWorkflow.fields.length - 1 && currentWorkflow.fields.length % 2 === 1 ? "field-span-full" : ""}>
                      <span>{field}</span>
                      <input
                        value={forms[currentWorkflow.storyKey]?.[field] || ""}
                        onChange={(event) =>
                          setForms((previous) => ({
                            ...previous,
                            [currentWorkflow.storyKey]: {
                              ...previous[currentWorkflow.storyKey],
                              [field]: event.target.value,
                            },
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>
                <div className="button-row">
                  <button type="submit" className="primary-button" disabled={loading}>
                    {loading ? "Saving..." : "Save"}
                  </button>
                </div>
              </form>
            </>
          ) : null}
          {error ? <div className="feedback-banner error" style={{ marginTop: 16 }}>{error}</div> : null}
          {currentWorkflow && results[currentWorkflow.storyKey] ? (
            <div className="feedback-banner success" style={{ marginTop: 16 }}>
              {results[currentWorkflow.storyKey].message || "Saved successfully"}
            </div>
          ) : null}
        </article>

        <aside className="module-panel">
          <div className="status-badge">{items.length} records loaded</div>
          <h4 style={{ marginTop: 16 }}>Persisted records</h4>
          <div className="record-stack">
            {items.length ? items.map((item) => (
              <div key={item.id} className="record-card">
                <p><strong>Workflow:</strong> {item.workflow}</p>
                <p><strong>Status:</strong> {item.status}</p>
                <ul>
                  {Object.entries(item.payload || {}).map(([key, value]) => (
                    <li key={key}><strong>{key}:</strong> {String(value)}</li>
                  ))}
                </ul>
              </div>
            )) : <p className="muted">No records saved yet for this module.</p>}
          </div>
        </aside>
      </div>
    </div>
  );
}
