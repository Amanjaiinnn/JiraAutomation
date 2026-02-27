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

const EMPTY_ITEM = {
  summary: "",
  details: "",
  description: "",
  acceptance_criteria: [],
  definition_of_done: [],
};

const EMPTY_STORY = {
  ...EMPTY_ITEM,
  selected: false,
};

const safeArray = (value) => (Array.isArray(value) ? value : []);
const linesToArray = (value) => value.split("\n").map((line) => line.trim()).filter(Boolean);
const arrayToLines = (value) => safeArray(value).join("\n");

const normalizeStory = (story) => ({
  ...EMPTY_STORY,
  ...story,
  summary: story?.summary || "",
  details: story?.details || story?.description || "",
  description: story?.description || story?.details || "",
  acceptance_criteria: safeArray(story?.acceptance_criteria),
  definition_of_done: safeArray(story?.definition_of_done),
  selected: Boolean(story?.selected),
});

const normalizeEpic = (epic) => ({
  ...EMPTY_ITEM,
  ...epic,
  epic_name: epic?.epic_name || epic?.summary || "Untitled Epic",
  summary: epic?.summary || epic?.epic_name || "",
  details: epic?.details || epic?.description || "",
  description: epic?.description || epic?.details || "",
  acceptance_criteria: safeArray(epic?.acceptance_criteria),
  definition_of_done: safeArray(epic?.definition_of_done),
  stories: safeArray(epic?.stories).map(normalizeStory),
});

const SectionHeader = ({ title, subtitle }) => (
  <div className="section-header">
    <h2>{title}</h2>
    {subtitle ? <p>{subtitle}</p> : null}
  </div>
);

const Navigation = ({ activePage, onChange }) => (
  <nav className="main-tabs">
    <button className={activePage === "planning" ? "active" : ""} onClick={() => onChange("planning")}>Planning Studio</button>
    <button className={activePage === "duplicates" ? "active" : ""} onClick={() => onChange("duplicates")}>Duplicate Checker</button>
    <button className={activePage === "code" ? "active" : ""} onClick={() => onChange("code")}>Code Generator</button>
  </nav>
);

const StoryEditor = ({ story, storyIndex, onChange, onToggleSelected }) => (
  <div className="story-card">
    <div className="story-heading">
      <h4>🧩 Story {storyIndex + 1}</h4>
      <span className="story-status">{story.selected ? "Selected for Jira" : "Draft"}</span>
    </div>

    <div className="story-card-top">
      <label className="story-row">
        <input type="checkbox" checked={Boolean(story.selected)} onChange={onToggleSelected} />
        <strong>Include in Jira publish</strong>
      </label>
      <span className="review-tag">Reviewable</span>
    </div>

    <div className="grid">
      <div>
        <label>Summary</label>
        <input value={story.summary} onChange={(event) => onChange("summary", event.target.value)} />
      </div>

      <div>
        <label>Details</label>
        <textarea rows={4} value={story.details} onChange={(event) => onChange("details", event.target.value)} />
      </div>

      <div>
        <label>Acceptance Criteria (one per line)</label>
        <textarea rows={4} value={arrayToLines(story.acceptance_criteria)} onChange={(event) => onChange("acceptance_criteria", linesToArray(event.target.value))} />
      </div>

      <div>
        <label>Definition of Done (one per line)</label>
        <textarea rows={4} value={arrayToLines(story.definition_of_done)} onChange={(event) => onChange("definition_of_done", linesToArray(event.target.value))} />
      </div>
    </div>
  </div>
);

const EpicEditor = ({ epic, epicIndex, onChangeEpicField, onGenerateStories, onChangeStoryField, onToggleStory }) => (
  <article className="card epic-card">
    <div className="card-header">
      <h3>🚀 Epic {epicIndex + 1}</h3>
      <button onClick={() => onGenerateStories(epicIndex)}>Generate Stories</button>
    </div>

    <div className="epic-meta-row">
      <span className="meta-pill">Stories: {safeArray(epic.stories).length}</span>
      <span className="meta-pill">Selected: {safeArray(epic.stories).filter((story) => story.selected).length}</span>
    </div>

    <div className="grid">
      <div>
        <label>Summary</label>
        <input value={epic.summary} onChange={(event) => onChangeEpicField(epicIndex, "summary", event.target.value)} />
      </div>

      <div>
        <label>Details</label>
        <textarea rows={4} value={epic.details} onChange={(event) => onChangeEpicField(epicIndex, "details", event.target.value)} />
      </div>

      <div>
        <label>Acceptance Criteria (one per line)</label>
        <textarea rows={4} value={arrayToLines(epic.acceptance_criteria)} onChange={(event) => onChangeEpicField(epicIndex, "acceptance_criteria", linesToArray(event.target.value))} />
      </div>

      <div>
        <label>Definition of Done (one per line)</label>
        <textarea rows={4} value={arrayToLines(epic.definition_of_done)} onChange={(event) => onChangeEpicField(epicIndex, "definition_of_done", linesToArray(event.target.value))} />
      </div>
    </div>

    <div className="story-list">
      {safeArray(epic.stories).map((story, storyIndex) => (
        <StoryEditor
          key={`${story.summary || "story"}-${storyIndex}`}
          story={story}
          storyIndex={storyIndex}
          onToggleSelected={() => onToggleStory(epicIndex, storyIndex)}
          onChange={(field, value) => onChangeStoryField(epicIndex, storyIndex, field, value)}
        />
      ))}
    </div>
  </article>
);

const PlanningPage = ({
  epics,
  chunks,
  selectedStories,
  totalStories,
  onUploadRequirements,
  onGenerateEpics,
  onGenerateStories,
  onChangeEpicField,
  onChangeStoryField,
  onToggleStorySelection,
  createJiraStories,
}) => (
  <>
    <section className="insight-row">
      <div className="insight-card">
        <p>Total Epics</p>
        <h3>{epics.length}</h3>
      </div>
      <div className="insight-card">
        <p>Total Stories</p>
        <h3>{totalStories}</h3>
      </div>
      <div className="insight-card">
        <p>Selected for Jira</p>
        <h3>{selectedStories.length}</h3>
      </div>
    </section>

    <section className="panel">
      <SectionHeader title="Epic and Story Planning" subtitle="Generate from requirements, then review and edit every field before publishing to Jira." />

      <div className="row">
        <input type="file" onChange={onUploadRequirements} />
        <button disabled={!chunks.length} onClick={onGenerateEpics}>Generate Epics</button>
      </div>

      {safeArray(epics).map((epic, epicIndex) => (
        <EpicEditor
          key={`${epic.summary || epic.epic_name || "epic"}-${epicIndex}`}
          epic={epic}
          epicIndex={epicIndex}
          onChangeEpicField={onChangeEpicField}
          onGenerateStories={onGenerateStories}
          onChangeStoryField={onChangeStoryField}
          onToggleStory={onToggleStorySelection}
        />
      ))}

      <button disabled={!selectedStories.length} onClick={createJiraStories}>Create {selectedStories.length} Selected Stories in Jira</button>
    </section>
  </>
);

const DuplicateCheckerPage = ({ duplicateStory, setDuplicateStory, duplicates, checkDuplicates }) => (
  <section className="panel">
    <SectionHeader title="Duplicate Checker" subtitle="Dedicated workspace for analysts validating repeated stories. Planning data is intentionally hidden." />

    <label>Story Summary</label>
    <input placeholder="Story summary" value={duplicateStory.summary} onChange={(event) => setDuplicateStory((previous) => ({ ...previous, summary: event.target.value }))} />

    <label>Story Details</label>
    <textarea rows={4} placeholder="Story details" value={duplicateStory.details} onChange={(event) => setDuplicateStory((previous) => ({ ...previous, details: event.target.value, description: event.target.value }))} />

    <button onClick={checkDuplicates}>Check Duplicates</button>

    <ul className="result-list">
      {safeArray(duplicates).map((dup) => (
        <li key={dup.jira_key}>{dup.jira_key} — Similarity {dup.similarity}</li>
      ))}
    </ul>
  </section>
);

const CodeGeneratorPage = ({ codeStory, setCodeStory, codeStack, setCodeStack, generateCode, generatedCode }) => (
  <section className="panel">
    <SectionHeader title="Code Generator" subtitle="Dedicated engineering page for generating implementation scaffolding from detailed story inputs." />

    <label>Story Summary</label>
    <input placeholder="Story summary" value={codeStory.summary} onChange={(event) => setCodeStory((previous) => ({ ...previous, summary: event.target.value }))} />

    <label>Story Details</label>
    <textarea rows={4} placeholder="Story details" value={codeStory.details} onChange={(event) => setCodeStory((previous) => ({ ...previous, details: event.target.value, description: event.target.value }))} />

    <label>Acceptance Criteria (one per line)</label>
    <textarea rows={4} placeholder="Acceptance Criteria" value={arrayToLines(codeStory.acceptance_criteria)} onChange={(event) => setCodeStory((previous) => ({ ...previous, acceptance_criteria: linesToArray(event.target.value) }))} />

    <label>Definition of Done (one per line)</label>
    <textarea rows={4} placeholder="Definition of Done" value={arrayToLines(codeStory.definition_of_done)} onChange={(event) => setCodeStory((previous) => ({ ...previous, definition_of_done: linesToArray(event.target.value) }))} />

    <label>Technology Stack</label>
    <select value={codeStack} onChange={(event) => setCodeStack(event.target.value)}>
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
);

export function App() {
  const [status, setStatus] = useState("");
  const [activePage, setActivePage] = useState("planning");

  const [jiraConfig, setJiraConfig] = useState({});
  const [jiraHealth, setJiraHealth] = useState(null);

  const [chunks, setChunks] = useState([]);
  const [epics, setEpics] = useState([]);

  const [duplicateStory, setDuplicateStory] = useState({ ...EMPTY_STORY });
  const [duplicates, setDuplicates] = useState([]);

  const [codeStory, setCodeStory] = useState({ ...EMPTY_STORY });
  const [codeStack, setCodeStack] = useState("python_fastapi");
  const [generatedCode, setGeneratedCode] = useState({});

  useEffect(() => {
    fetchJson("/jira/config")
      .then((data) => setJiraConfig(data || {}))
      .catch((error) => setStatus(error.message));
  }, []);

  const selectedStories = useMemo(
    () =>
      safeArray(epics).flatMap((epic) =>
        safeArray(epic.stories)
          .filter((story) => story.selected)
          .map((story) => ({
            ...story,
            epic_name: epic.summary || epic.epic_name || "AI Generated Epic",
            description: story.description || story.details,
          }))
      ),
    [epics]
  );

  const totalStories = useMemo(() => safeArray(epics).reduce((acc, epic) => acc + safeArray(epic.stories).length, 0), [epics]);

  const updateEpic = (epicIndex, updater) => {
    setEpics((previous) => previous.map((epic, index) => (index === epicIndex ? updater(epic) : epic)));
  };

  const updateStory = (epicIndex, storyIndex, updater) => {
    updateEpic(epicIndex, (epic) => ({
      ...epic,
      stories: safeArray(epic.stories).map((story, index) => (index === storyIndex ? updater(story) : story)),
    }));
  };

  const onUploadRequirements = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setStatus("Parsing requirements...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await fetchJson("/requirements/parse", { method: "POST", body: formData });
      setChunks(data?.chunks || []);
      setStatus(`Loaded ${data?.chunks?.length || 0} chunks from ${data?.filename || file.name}`);
    } catch (error) {
      setStatus(error.message);
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
      const normalized = safeArray(data?.epics).map((epic) => normalizeEpic({ ...epic, stories: [] }));
      setEpics(normalized);
      setStatus(`Generated ${normalized.length} epics`);
    } catch (error) {
      setStatus(error.message);
    }
  };

  const onGenerateStories = async (epicIndex) => {
    const targetEpic = epics[epicIndex];
    if (!targetEpic) return;

    setStatus(`Generating stories for ${targetEpic.summary || targetEpic.epic_name}...`);

    try {
      const data = await fetchJson("/stories/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ epic: targetEpic, chunks, top_k: 4 }),
      });

      updateEpic(epicIndex, (epic) => ({
        ...epic,
        stories: safeArray(data?.stories).map((story) => normalizeStory({ ...story, selected: false })),
      }));

      setStatus(`Generated ${safeArray(data?.stories).length} stories for ${targetEpic.summary || targetEpic.epic_name}`);
    } catch (error) {
      setStatus(error.message);
    }
  };

  const onChangeEpicField = (epicIndex, field, value) => {
    updateEpic(epicIndex, (epic) => {
      const nextEpic = { ...epic, [field]: value };
      if (field === "summary") nextEpic.epic_name = value;
      if (field === "details") nextEpic.description = value;
      return nextEpic;
    });
  };

  const onChangeStoryField = (epicIndex, storyIndex, field, value) => {
    updateStory(epicIndex, storyIndex, (story) => {
      const nextStory = { ...story, [field]: value };
      if (field === "details") nextStory.description = value;
      return nextStory;
    });
  };

  const onToggleStorySelection = (epicIndex, storyIndex) => {
    updateStory(epicIndex, storyIndex, (story) => ({ ...story, selected: !story.selected }));
  };

  const createJiraStories = async () => {
    setStatus("Creating selected stories in Jira...");
    try {
      const data = await fetchJson("/jira/create-stories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stories: selectedStories }),
      });
      const keys = safeArray(data?.keys);
      setStatus(keys.length ? `Created Jira issues: ${keys.join(", ")}` : "Story creation request sent to Jira");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const saveJiraConfig = async () => {
    setStatus("Saving Jira configuration...");
    try {
      const data = await fetchJson("/jira/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...jiraConfig, auto_fill_env: true }),
      });
      setJiraConfig(data || {});
      setStatus("Jira configuration saved");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const testJiraConnection = async () => {
    setStatus("Testing Jira connection...");
    try {
      const health = await fetchJson("/jira/health");
      setJiraHealth(health || null);
      setStatus(health?.ok ? "Jira connection successful" : "Jira connection failed");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const checkDuplicates = async () => {
    setStatus("Checking duplicate stories...");
    try {
      const payload = {
        ...duplicateStory,
        description: duplicateStory.description || duplicateStory.details,
      };
      const data = await fetchJson("/stories/check-duplicates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ story: payload }),
      });
      setDuplicates(safeArray(data?.duplicates));
      setStatus("Duplicate check completed");
    } catch (error) {
      setStatus(error.message);
    }
  };

  const generateCode = async () => {
    setStatus("Generating implementation scaffolding...");
    try {
      const payload = {
        ...codeStory,
        description: codeStory.description || codeStory.details,
      };
      const data = await fetchJson("/stories/generate-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ story: payload, stack: codeStack }),
      });
      setGeneratedCode(data?.files || {});
      setStatus("Code generation completed");
    } catch (error) {
      setStatus(error.message);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <h1>Jira Delivery Studio</h1>
          <p>Navigate by role-specific pages: planning, duplicate checking, or code generation.</p>
        </div>
        <div className="status-pill">{status || "Ready"}</div>
      </header>

      <section className="panel">
        <SectionHeader title="Jira Workspace Configuration" subtitle="Shared config for all pages. Teams can work independently after this setup." />
        <div className="grid">
          <input placeholder="Jira URL" value={jiraConfig.jira_url || ""} onChange={(event) => setJiraConfig((previous) => ({ ...previous, jira_url: event.target.value }))} />
          <input placeholder="Jira Email" value={jiraConfig.jira_email || ""} onChange={(event) => setJiraConfig((previous) => ({ ...previous, jira_email: event.target.value }))} />
          <input placeholder="Jira API Token" value={jiraConfig.jira_api_token || ""} onChange={(event) => setJiraConfig((previous) => ({ ...previous, jira_api_token: event.target.value }))} />
          <input placeholder="Jira Project Key" value={jiraConfig.jira_project_key || ""} onChange={(event) => setJiraConfig((previous) => ({ ...previous, jira_project_key: event.target.value }))} />
        </div>
        <div className="row">
          <button onClick={saveJiraConfig}>Save Configuration</button>
          <button onClick={testJiraConnection}>Test Connection</button>
        </div>
        {jiraHealth ? <p className={jiraHealth.ok ? "good" : "bad"}>{jiraHealth.ok ? `Connected as ${jiraHealth.user}` : jiraHealth.error}</p> : null}
      </section>

      <Navigation activePage={activePage} onChange={setActivePage} />

      {activePage === "planning" && (
        <PlanningPage
          epics={epics}
          chunks={chunks}
          selectedStories={selectedStories}
          totalStories={totalStories}
          onUploadRequirements={onUploadRequirements}
          onGenerateEpics={onGenerateEpics}
          onGenerateStories={onGenerateStories}
          onChangeEpicField={onChangeEpicField}
          onChangeStoryField={onChangeStoryField}
          onToggleStorySelection={onToggleStorySelection}
          createJiraStories={createJiraStories}
        />
      )}

      {activePage === "duplicates" && (
        <DuplicateCheckerPage
          duplicateStory={duplicateStory}
          setDuplicateStory={setDuplicateStory}
          duplicates={duplicates}
          checkDuplicates={checkDuplicates}
        />
      )}

      {activePage === "code" && (
        <CodeGeneratorPage
          codeStory={codeStory}
          setCodeStory={setCodeStory}
          codeStack={codeStack}
          setCodeStack={setCodeStack}
          generateCode={generateCode}
          generatedCode={generatedCode}
        />
      )}
    </div>
  );
}