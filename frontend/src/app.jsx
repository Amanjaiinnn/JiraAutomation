import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const fetchJson = async (path, options = {}) => {
  const target = API_BASE_URL ? `${API_BASE_URL}${path}` : path;
  const response = await fetch(target, options);

  let payload = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    const text = await response.text();
    payload = { error: text || "Non-JSON response" };
  }

  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  }
  return payload;
};

const defaultStory = {
  summary: "",
  description: "",
  acceptance_criteria: [],
  definition_of_done: [],
};

export function App() {
  const [activeTab, setActiveTab] = useState("planning");
  const [jiraConfig, setJiraConfig] = useState({});
  const [jiraHealth, setJiraHealth] = useState(null);
  const [status, setStatus] = useState("");

  const [chunks, setChunks] = useState([]);
  const [epics, setEpics] = useState([]);

  const [duplicateStory, setDuplicateStory] = useState(defaultStory);
  const [duplicates, setDuplicates] = useState([]);

  const [codeStory, setCodeStory] = useState(defaultStory);
  const [codeStack, setCodeStack] = useState("python_fastapi");
  const [generatedCode, setGeneratedCode] = useState({});

  useEffect(() => {
    fetchJson("/jira/config")
      .then(setJiraConfig)
      .catch((err) => setStatus(err.message));
  }, []);

  const selectedStories = useMemo(
    () => epics.flatMap((epic) => (epic.stories || []).filter((story) => story.selected)),
    [epics]
  );

  const onUploadRequirements = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setStatus("Parsing requirements...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await fetchJson("/requirements/parse", { method: "POST", body: formData });
      setChunks(data.chunks || []);
      setStatus(`Loaded ${data.chunks?.length || 0} chunks from ${data.filename}`);
    } catch (err) {
      setStatus(err.message);
    }
  };

  const onGenerateEpics = async () => {
    setStatus("Generating epics...");
    try {
      const data = await fetchJson("/epics/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chunks }),
      });
      const normalized = (data.epics || []).map((epic) => ({ ...epic, stories: [] }));
      setEpics(normalized);
      setStatus(`Generated ${normalized.length} epics`);
    } catch (err) {
      setStatus(err.message);
    }
  };

  const onGenerateStories = async (epicIndex) => {
    const epic = epics[epicIndex];
    setStatus(`Generating stories for ${epic.epic_name}...`);
    try {
      const data = await fetchJson("/stories/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ epic, chunks, top_k: 4 }),
      });

      const next = [...epics];
      next[epicIndex].stories = (data.stories || []).map((story) => ({ ...story, selected: false }));
      setEpics(next);
      setStatus(`Generated ${next[epicIndex].stories.length} stories for ${epic.epic_name}`);
    } catch (err) {
      setStatus(err.message);
    }
  };

  const toggleStorySelection = (epicIndex, storyIndex) => {
    const next = [...epics];
    next[epicIndex].stories[storyIndex].selected = !next[epicIndex].stories[storyIndex].selected;
    setEpics(next);
  };

  const createJiraStories = async () => {
    setStatus("Creating stories in Jira...");
    try {
      const payloadStories = selectedStories.map((story) => ({
        ...story,
        epic_name: story.epic_name || "AI Generated Epic",
      }));

      const data = await fetchJson("/jira/create-stories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stories: payloadStories }),
      });
      setStatus(`Created Jira issues: ${(data.keys || []).join(", ")}`);
    } catch (err) {
      setStatus(err.message);
    }
  };

  const saveJiraConfig = async () => {
    setStatus("Configuring Jira...");
    try {
      const data = await fetchJson("/jira/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...jiraConfig, auto_fill_env: true }),
      });
      setJiraConfig(data);
      setStatus("Jira configuration saved");
    } catch (err) {
      setStatus(err.message);
    }
  };

  const testJira = async () => {
    setStatus("Testing Jira connection...");
    try {
      const health = await fetchJson("/jira/health");
      setJiraHealth(health);
      setStatus(health.ok ? "Jira connection successful" : "Jira connection failed");
    } catch (err) {
      setStatus(err.message);
    }
  };

  const checkDuplicateStories = async () => {
    setStatus("Checking duplicates...");
    try {
      const data = await fetchJson("/stories/check-duplicates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ story: duplicateStory }),
      });
      setDuplicates(data.duplicates || []);
      setStatus("Duplicate check completed");
    } catch (err) {
      setStatus(err.message);
    }
  };

  const generateCode = async () => {
    setStatus("Generating code...");
    try {
      const data = await fetchJson("/stories/generate-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ story: codeStory, stack: codeStack }),
      });
      setGeneratedCode(data.files || {});
      setStatus("Code generation completed");
    } catch (err) {
      setStatus(err.message);
    }
  };

  return (
    <div className="container">
      <h1>Jira AI Automation (React UI)</h1>
      <p className="status">{status}</p>

      <section className="panel">
        <h2>Jira Auto Configuration</h2>
        <div className="grid">
          <input value={jiraConfig.jira_url || ""} onChange={(e) => setJiraConfig({ ...jiraConfig, jira_url: e.target.value })} placeholder="Jira URL" />
          <input value={jiraConfig.jira_email || ""} onChange={(e) => setJiraConfig({ ...jiraConfig, jira_email: e.target.value })} placeholder="Jira Email" />
          <input value={jiraConfig.jira_api_token || ""} onChange={(e) => setJiraConfig({ ...jiraConfig, jira_api_token: e.target.value })} placeholder="Jira API Token" />
          <input value={jiraConfig.jira_project_key || ""} onChange={(e) => setJiraConfig({ ...jiraConfig, jira_project_key: e.target.value })} placeholder="Jira Project Key" />
        </div>
        <div className="row">
          <button onClick={saveJiraConfig}>Save Configuration</button>
          <button onClick={testJira}>Test Connection</button>
        </div>
        {jiraHealth && <p>{jiraHealth.ok ? `Connected as ${jiraHealth.user}` : jiraHealth.error}</p>}
      </section>

      <div className="tabs">
        <button className={activeTab === "planning" ? "active" : ""} onClick={() => setActiveTab("planning")}>Epic & Story Planning</button>
        <button className={activeTab === "duplicates" ? "active" : ""} onClick={() => setActiveTab("duplicates")}>Duplicate Checker</button>
        <button className={activeTab === "code" ? "active" : ""} onClick={() => setActiveTab("code")}>Code Generator</button>
      </div>

      {activeTab === "planning" && (
        <section className="panel">
          <h2>Epic and Story Generation</h2>
          <input type="file" onChange={onUploadRequirements} />
          <button disabled={!chunks.length} onClick={onGenerateEpics}>Generate Epics</button>

          {epics.map((epic, epicIndex) => (
            <div className="card" key={`${epic.epic_name}-${epicIndex}`}>
              <h3>{epic.epic_name}</h3>
              <p>{epic.description}</p>
              <button onClick={() => onGenerateStories(epicIndex)}>Generate Stories</button>
              {(epic.stories || []).map((story, storyIndex) => (
                <label key={`${story.summary}-${storyIndex}`} className="story-row">
                  <input type="checkbox" checked={story.selected || false} onChange={() => toggleStorySelection(epicIndex, storyIndex)} />
                  <span>{story.summary}</span>
                </label>
              ))}
            </div>
          ))}

          <button disabled={!selectedStories.length} onClick={createJiraStories}>Create Selected Stories in Jira</button>
        </section>
      )}

      {activeTab === "duplicates" && (
        <section className="panel">
          <h2>Duplicate Story Checker</h2>
          <input
            placeholder="Story summary"
            value={duplicateStory.summary}
            onChange={(e) => setDuplicateStory({ ...duplicateStory, summary: e.target.value })}
          />
          <textarea
            placeholder="Story description"
            value={duplicateStory.description}
            onChange={(e) => setDuplicateStory({ ...duplicateStory, description: e.target.value })}
          />
          <button onClick={checkDuplicateStories}>Check Duplicates</button>
          <ul>
            {(Array.isArray(duplicates) ? duplicates : []).map((dup) => (
              <li key={dup.jira_key}>{dup.jira_key} - Similarity {dup.similarity}</li>
            ))}
          </ul>
        </section>
      )}

      {activeTab === "code" && (
        <section className="panel">
          <h2>Story Code Generator</h2>
          <input
            placeholder="Story summary"
            value={codeStory.summary}
            onChange={(e) => setCodeStory({ ...codeStory, summary: e.target.value })}
          />
          <textarea
            placeholder="Story description"
            value={codeStory.description}
            onChange={(e) => setCodeStory({ ...codeStory, description: e.target.value })}
          />
          <input
            placeholder="Acceptance Criteria (line separated)"
            onChange={(e) => setCodeStory({ ...codeStory, acceptance_criteria: e.target.value.split("\n") })}
          />
          <select value={codeStack} onChange={(e) => setCodeStack(e.target.value)}>
            <option value="python_fastapi">Python + FastAPI</option>
            <option value="react_node">React + Node</option>
            <option value="java_springboot">Java + Spring Boot</option>
          </select>
          <button onClick={generateCode}>Generate Code</button>
          {Object.entries(generatedCode || {}).map(([filename, content]) => (
            <div key={filename} className="code-block">
              <h4>{filename}</h4>
              <pre>{content}</pre>
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
