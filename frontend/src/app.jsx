import React, { useEffect, useMemo, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const FRONTEND_STACK_OPTIONS = [
  { value: "react_vite", label: "React + Vite" },
  { value: "nextjs", label: "Next.js" },
  { value: "vue_vite", label: "Vue 3 + Vite" },
];
const BACKEND_STACK_OPTIONS = [
  { value: "python_fastapi", label: "Python + FastAPI" },
  { value: "node_express", label: "Node.js + Express" },
  { value: "java_spring", label: "Java + Spring Boot" },
];
const DATABASE_OPTIONS = [{ value: "postgresql", label: "PostgreSQL" }];
const DEFAULT_PROJECT_CONFIG = {
  frontend_stack: "react_vite",
  backend_stack: "python_fastapi",
  database: "postgresql",
};
const EMPTY_PREVIEW = {
  title: "Generated Application",
  summary: "Generate a build pack from any story to preview the cumulative project structure here.",
  highlights: [],
  entrypoints: [],
  routes: [],
  components: [],
  html: "",
};
const EMPTY_DEMO = {
  ready: false,
  url: "",
  title: "Generated Application",
};
const DEFAULT_PREVIEW_HTML = `
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body {
        margin: 0;
        font-family: 'Segoe UI', sans-serif;
        background: linear-gradient(160deg, #0f172a, #111827 45%, #1d4ed8 100%);
        color: #e2e8f0;
        padding: 24px;
      }
      .card {
        max-width: 720px;
        margin: 0 auto;
        border-radius: 20px;
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(191, 219, 254, 0.18);
        padding: 24px;
      }
      h1 { margin: 0 0 12px; }
      p { margin: 0; line-height: 1.6; color: #cbd5e1; }
    </style>
  </head>
  <body>
    <section class="card">
      <h1>Project Preview</h1>
      <p>Generate deliverables for a story to inspect the accumulated application blueprint here.</p>
    </section>
  </body>
</html>
`;

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

const getBackendUrl = (path) => {
  if (API_BASE_URL) {
    try {
      return new URL(path, `${API_BASE_URL}/`).toString();
    } catch {
      return path;
    }
  }

  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000${path}`;
  }

  return path;
};

const getLiveAppUrl = () => {
  if (typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:5174`;
  }
  return "http://localhost:5174";
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
  completed: false,
  ui_reference: {
    text: "",
    image_name: "",
    image_media_type: "",
    image_data_url: "",
  },
  delivery_status: "idle",
  test_generation_state: "idle",
  test_run_state: "idle",
  test_run_result: null,
  jira_issue_key: "",
  jira_status: "",
  jira_transition_state: "idle",
  generated_files: {},
  unit_test_files: {},
  manual_test_cases: [],
  automated_test_cases: [],
  preview: null,
};

const safeArray = (value) => (Array.isArray(value) ? value : []);
const safeObject = (value) => (value && typeof value === "object" && !Array.isArray(value) ? value : {});
const normalizeUiReference = (value = {}) => {
  const candidate = safeObject(value);
  return {
    text: String(candidate.text || "").trim(),
    image_name: String(candidate.image_name || "").trim(),
    image_media_type: String(candidate.image_media_type || "").trim(),
    image_data_url: String(candidate.image_data_url || "").trim(),
  };
};
const hasUiReference = (value = {}) => {
  const reference = normalizeUiReference(value);
  return Boolean(reference.text || reference.image_name || reference.image_data_url);
};
const normalizeProjectConfig = (value = {}, legacyStack = "python_fastapi") => {
  const candidate = safeObject(value);
  const frontendValues = new Set(FRONTEND_STACK_OPTIONS.map((option) => option.value));
  const backendValues = new Set(BACKEND_STACK_OPTIONS.map((option) => option.value));
  const databaseValues = new Set(DATABASE_OPTIONS.map((option) => option.value));
  const fallbackBackend = backendValues.has(legacyStack) ? legacyStack : DEFAULT_PROJECT_CONFIG.backend_stack;

  return {
    frontend_stack: frontendValues.has(candidate.frontend_stack) ? candidate.frontend_stack : DEFAULT_PROJECT_CONFIG.frontend_stack,
    backend_stack: backendValues.has(candidate.backend_stack) ? candidate.backend_stack : fallbackBackend,
    database: databaseValues.has(candidate.database) ? candidate.database : DEFAULT_PROJECT_CONFIG.database,
  };
};
const getLegacyStackFromProjectConfig = (projectConfig) =>
  normalizeProjectConfig(projectConfig).backend_stack;
const linesToArray = (value) => value.split("\n").map((line) => line.trim()).filter(Boolean);
const arrayToLines = (value) => safeArray(value).join("\n");
const countFiles = (value) => Object.keys(safeObject(value)).length;
const countPythonUnitTestsInFiles = (files) =>
  Object.values(keepOnlyTestFiles(files)).reduce((total, content) => {
    const matches = String(content).match(/^\s*(?:async\s+def|def)\s+test_[A-Za-z0-9_]*\s*\(/gm);
    return total + (matches ? matches.length : 0);
  }, 0);
const isTestFilePath = (path = "") => {
  const normalized = String(path).replace(/\\/g, "/").trim();
  if (!normalized) return false;
  const lowered = normalized.toLowerCase();
  const name = lowered.split("/").pop() || lowered;
  return (
    lowered.startsWith("tests/") ||
    lowered.includes("/tests/") ||
    name.startsWith("test_") ||
    name.endsWith("_test.py") ||
    name.endsWith(".test.js") ||
    name.endsWith(".spec.js") ||
    name.endsWith(".test.jsx") ||
    name.endsWith(".spec.jsx") ||
    name.endsWith(".test.ts") ||
    name.endsWith(".spec.ts") ||
    name.endsWith(".test.tsx") ||
    name.endsWith(".spec.tsx")
  );
};
const stripTestFiles = (files) =>
  Object.fromEntries(Object.entries(safeObject(files)).filter(([path]) => !isTestFilePath(path)));
const keepOnlyTestFiles = (files) =>
  Object.fromEntries(Object.entries(safeObject(files)).filter(([path]) => isTestFilePath(path)));
const deriveWorkspaceName = (filename = "") =>
  filename.replace(/\.[^/.]+$/, "").replace(/[_-]+/g, " ").trim() || "Delivery Workspace";
const getStoryJiraPayload = (epic, story) => ({
  ...story,
  epic_name: epic.summary || epic.epic_name || "AI Generated Epic",
  description: story.description || story.details,
});
const buildCodeContext = (files) => {
  const entries = Object.entries(safeObject(files));
  if (!entries.length) return "No existing project files yet.";

  return entries
    .sort(([left], [right]) => left.localeCompare(right))
    .slice(0, 24)
    .map(([path, content]) => `FILE: ${path}\n${String(content).slice(0, 4000)}`)
    .join("\n\n");
};
const mergeStoryTestFiles = (epics) =>
  safeArray(epics).reduce(
    (acc, epic) => ({
      ...acc,
      ...safeArray(epic.stories).reduce(
        (storyAcc, story) => ({ ...storyAcc, ...keepOnlyTestFiles(story.unit_test_files) }),
        {},
      ),
    }),
    {},
  );
const collectStoryTestPaths = (epics) =>
  safeArray(epics).flatMap((epic) =>
    safeArray(epic.stories).flatMap((story) => Object.keys(keepOnlyTestFiles(story.unit_test_files))),
  );
const countAllUnitTests = (epics) =>
  safeArray(epics).reduce((total, epic) => total + safeArray(epic.stories).reduce((storyTotal, story) => storyTotal + countPythonUnitTestsInFiles(story.unit_test_files), 0), 0);
const getRunResultTone = (result) => {
  if (!result) return "muted";
  if (result.ok) return "good";
  if (result.supported === false) return "muted";
  return "bad";
};
const formatRunResultSummary = (result) => {
  if (!result) return "No test run yet.";
  if (typeof result.pass_percentage === "number" && typeof result.total_tests === "number" && result.total_tests > 0) {
    return `${result.passed_tests || 0}/${result.total_tests} tests passed (${result.pass_percentage}%).`;
  }
  if (result.message) return result.message;
  if (typeof result.returncode === "number") return `Command finished with exit code ${result.returncode}.`;
  return "No test run yet.";
};
const formatNotificationStatus = (notification, actionLabel) => {
  if (!notification) return actionLabel;
  if (notification.sent && notification.recipient) {
    return `${actionLabel} and emailed ${notification.recipient}.`;
  }
  if (notification.skipped) {
    return `${actionLabel}. Email skipped: ${notification.reason}`;
  }
  if (notification.reason) {
    return `${actionLabel}. Email failed: ${notification.reason}`;
  }
  return actionLabel;
};

const normalizeStory = (story) => ({
  ...EMPTY_STORY,
  ...story,
  summary: story?.summary || "",
  details: story?.details || story?.description || "",
  description: story?.description || story?.details || "",
  acceptance_criteria: safeArray(story?.acceptance_criteria),
  definition_of_done: safeArray(story?.definition_of_done),
  selected: Boolean(story?.selected),
  completed: Boolean(story?.completed),
  delivery_status: story?.delivery_status || "idle",
  test_generation_state: story?.test_generation_state || "idle",
  test_run_state: story?.test_run_state || "idle",
  test_run_result: story?.test_run_result || null,
  jira_issue_key: story?.jira_issue_key || "",
  jira_status: story?.jira_status || "",
  jira_transition_state: story?.jira_transition_state || "idle",
  generated_files: safeObject(story?.generated_files),
  unit_test_files: safeObject(story?.unit_test_files),
  manual_test_cases: safeArray(story?.manual_test_cases),
  automated_test_cases: safeArray(story?.automated_test_cases),
  ui_reference: normalizeUiReference(story?.ui_reference),
  preview: story?.preview || null,
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

const TestRunResult = ({ result, emptyLabel = "No test run yet." }) => {
  if (!result) {
    return <p className="muted">{emptyLabel}</p>;
  }

  return (
    <div className="test-run-result">
      <p className={getRunResultTone(result)}>{formatRunResultSummary(result)}</p>
      {typeof result.pass_percentage === "number" ? (
        <p className="muted">
          <strong>Pass Rate:</strong> {result.pass_percentage}%{typeof result.total_tests === "number" ? ` (${result.passed_tests || 0}/${result.total_tests})` : ""}
        </p>
      ) : null}
      {result.command ? <p className="muted"><strong>Command:</strong> {result.command}</p> : null}
      {safeArray(result.collected_test_files).length ? (
        <p className="muted"><strong>Files:</strong> {safeArray(result.collected_test_files).join(", ")}</p>
      ) : null}
      {result.stdout ? (
        <details className="code-preview-item">
          <summary>Stdout</summary>
          <pre>{result.stdout}</pre>
        </details>
      ) : null}
      {result.stderr ? (
        <details className="code-preview-item">
          <summary>Stderr</summary>
          <pre>{result.stderr}</pre>
        </details>
      ) : null}
    </div>
  );
};

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
  </nav>
);

const DemoLinkButton = ({ ready, url, label = "Open Live App" }) => {
  if (!url) {
    return (
      <button type="button" disabled>
        {label}
      </button>
    );
  }

  return (
    <a className={`button-link ${ready ? "" : "button-link-pending"}`.trim()} href={url} target="_blank" rel="noreferrer">
      {label}
    </a>
  );
};

const FileCollection = ({ title, files, selectedFilePath, onSelectFile }) => {
  const entries = Object.entries(safeObject(files));
  if (!entries.length) return null;

  return (
    <div className="file-collection">
      <h5>{title}</h5>
      <div className="file-chip-row">
        {entries.map(([path]) => (
          <button
            key={path}
            type="button"
            className={`file-chip ${selectedFilePath === path ? "active" : ""}`}
            onClick={() => onSelectFile(path)}
          >
            {path}
          </button>
        ))}
      </div>
    </div>
  );
};

const InlineCodePreview = ({ title, files }) => {
  const entries = Object.entries(safeObject(files));
  if (!entries.length) return null;

  return (
    <div className="code-preview-stack">
      <h5>{title}</h5>
      {entries.map(([path, content]) => (
        <details key={path} className="code-preview-item">
          <summary>{path}</summary>
          <pre>{content}</pre>
        </details>
      ))}
    </div>
  );
};

const TestCaseList = ({ title, cases, automated = false }) => {
  const items = safeArray(cases);
  if (!items.length) return null;

  return (
    <div>
      <h5>{title}</h5>
      <ul className="result-list">
        {items.map((item, index) => (
          <li key={item.id || `${title}-${index}`}>
            <strong>{item.id || `${automated ? "A" : "M"}-${String(index + 1).padStart(3, "0")}`}</strong>
            {" "}
            {item.title || "Untitled"}
            {" "}
            <span className="muted-inline">({item.category || item.type || "general"})</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

const BuildPackPromptModal = ({
  open,
  storySummary,
  value,
  imagePreviewUrl,
  onTextChange,
  onFileChange,
  onClose,
  onConfirm,
  loading,
}) => {
  if (!open) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Build pack design prompt">
      <div className="modal-card">
        <div className="card-header">
          <div>
            <h3>Build Pack Design Prompt</h3>
            <p className="muted">Guide the generated UI for {storySummary || "this story"} with text, a screenshot, or both.</p>
          </div>
        </div>

        <label>Visualization Notes</label>
        <textarea
          rows={7}
          placeholder="Describe the layout, style, sections, navigation, cards, tables, forms, colors, and interaction patterns you want."
          value={value.text}
          onChange={(event) => onTextChange(event.target.value)}
        />

        <label>Reference Screenshot</label>
        <input type="file" accept="image/*" onChange={onFileChange} />
        {value.image_name ? <p className="muted">Attached: {value.image_name}</p> : <p className="muted">Optional. Add a screenshot reference if you have one.</p>}
        {imagePreviewUrl ? <img className="reference-image-preview" src={imagePreviewUrl} alt="UI reference preview" /> : null}

        <div className="row">
          <button type="button" className="secondary-button" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="button" onClick={onConfirm} disabled={loading}>
            {loading ? "Generating..." : "Generate Build Pack"}
          </button>
        </div>
      </div>
    </div>
  );
};

const StoryEditor = ({
  epic,
  story,
  storyIndex,
  demo,
  selectedFilePath,
  onSelectFile,
  onChange,
  onToggleSelected,
  onToggleCompleted,
  onOpenBuildPackPrompt,
  onGenerateDeliverables,
  onGenerateTests,
  onRunStoryTests,
  onPublishStory,
  onCompleteStoryInJira,
}) => {
  const canMarkDone =
    countFiles(story.generated_files) > 0 &&
    Boolean(story.jira_issue_key) &&
    story.jira_transition_state !== "updating" &&
    story.delivery_status !== "generating";
  const canGenerateTests = countFiles(story.generated_files) > 0 && story.delivery_status !== "generating" && story.test_generation_state !== "generating";
  const canRunStoryTests = countFiles(story.unit_test_files) > 0 && story.test_run_state !== "running";
  const unitTestCount = countPythonUnitTestsInFiles(story.unit_test_files);

  return (
  <details className="story-card story-dropdown">
    <summary className="dropdown-summary">
      <div className="dropdown-title-block">
        <h4>{story.summary || `Story ${storyIndex + 1}`}</h4>
        <p>Story {storyIndex + 1}</p>
      </div>
      <div className="dropdown-pill-row">
        <span className="story-status">
          {story.delivery_status === "generating" ? "Generating build pack" : story.selected ? "Selected for Jira" : "Draft"}
        </span>
        <span className="review-tag">{countFiles(story.generated_files)} app files</span>
        {unitTestCount ? <span className="review-tag">{unitTestCount} unit tests</span> : null}
        {story.jira_issue_key ? <span className="meta-pill">{story.jira_issue_key}</span> : null}
        {story.jira_status ? <span className="meta-pill">Jira: {story.jira_status}</span> : null}
      </div>
    </summary>

    <div className="dropdown-body">
      <div className="story-card-top">
        <div className="story-controls">
          <label className="story-row">
            <input type="checkbox" checked={Boolean(story.selected)} onChange={onToggleSelected} />
            <strong>Include in Jira publish</strong>
          </label>
          <label className="story-row">
            <input type="checkbox" checked={Boolean(story.completed)} onChange={onToggleCompleted} />
            <strong>Mark as done for email</strong>
          </label>
        </div>
        <div className="row">
          <DemoLinkButton ready={demo?.ready} url={demo?.url || getLiveAppUrl()} />
          <button type="button" onClick={() => onPublishStory(epic, story)} disabled={!story.selected}>
            Add Story to Jira
          </button>
          <button type="button" onClick={onOpenBuildPackPrompt} disabled={story.delivery_status === "generating"}>
            {story.delivery_status === "generating"
              ? "Generating..."
              : hasUiReference(story.ui_reference)
                ? "Edit Prompt Inbox"
                : "Open Prompt Inbox"}
          </button>
          {hasUiReference(story.ui_reference) ? (
            <button type="button" className="secondary-button" onClick={onGenerateDeliverables} disabled={story.delivery_status === "generating"}>
              Generate with Saved Prompt
            </button>
          ) : null}
          <button type="button" onClick={() => onGenerateTests(epic, story)} disabled={!canGenerateTests}>
            {story.test_generation_state === "generating" ? "Generating Tests..." : "Generate Test Cases"}
          </button>
          <button type="button" onClick={() => onRunStoryTests(epic, story)} disabled={!canRunStoryTests}>
            {story.test_run_state === "running" ? "Running Tests..." : "Run Story Tests"}
          </button>
          <button
            type="button"
            onClick={() => onCompleteStoryInJira(epic, story)}
            disabled={!canMarkDone}
            title={story.jira_issue_key ? "" : "Add this story to Jira before marking it done"}
          >
            {story.jira_transition_state === "updating" ? "Updating Jira..." : "Mark Done in Jira"}
          </button>
        </div>
        {story.ui_reference?.text || story.ui_reference?.image_name ? (
          <p className="muted build-pack-reference-note">
            UI reference saved
            {story.ui_reference?.text ? ": text prompt added" : ""}
            {story.ui_reference?.text && story.ui_reference?.image_name ? " and " : ""}
            {story.ui_reference?.image_name ? `screenshot ${story.ui_reference.image_name}` : ""}.
          </p>
        ) : null}
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

      {(countFiles(story.generated_files) > 0 || story.manual_test_cases.length > 0 || story.automated_test_cases.length > 0) && (
        <div className="deliverables-grid">
          <div className="deliverables-card">
            <div className="card-header">
              <h5>Story Deliverables</h5>
            </div>
            <p className="muted">
              {demo?.ready
                ? `Open ${demo.url} to interact with the live generated app and run manual testing against the latest project state.`
                : "Generate a build pack to launch the live app preview for this story."}
            </p>
            <FileCollection title="Application Files" files={story.generated_files} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} />
            <InlineCodePreview title="Generated Code" files={story.generated_files} />
          </div>
          <div className="deliverables-card">
            <h5>QA Coverage</h5>
            <TestCaseList title="Manual Test Cases" cases={story.manual_test_cases} />
            <TestCaseList title="Automated Test Cases" cases={story.automated_test_cases} automated />
            <FileCollection title="Unit Test Files" files={story.unit_test_files} selectedFilePath={selectedFilePath} onSelectFile={onSelectFile} />
            <InlineCodePreview title="Generated Unit Test Code" files={story.unit_test_files} />
            <TestRunResult result={story.test_run_result} emptyLabel="Run this story's tests to view results here." />
          </div>
        </div>
      )}
    </div>
  </details>
  );
};

const EpicEditor = ({
  epic,
  epicIndex,
  demo,
  selectedFilePath,
  onSelectFile,
  onChangeEpicField,
  onGenerateStories,
  onChangeStoryField,
  onToggleStory,
  onToggleStoryCompleted,
  onOpenBuildPackPrompt,
  onGenerateDeliverables,
  onGenerateTests,
  onRunStoryTests,
  onPublishStory,
  onPublishEpic,
  onCompleteStoryInJira,
}) => {
  const completedStories = safeArray(epic.stories).filter((story) => story.completed);

  return (
  <details className="card epic-card epic-dropdown">
    <summary className="dropdown-summary">
      <div className="dropdown-title-block">
        <h3>{epic.summary || epic.epic_name || `Epic ${epicIndex + 1}`}</h3>
        <p>Epic {epicIndex + 1}</p>
      </div>
      <div className="dropdown-pill-row">
        <span className="meta-pill">Stories: {safeArray(epic.stories).length}</span>
        <span className="meta-pill">Selected: {safeArray(epic.stories).filter((story) => story.selected).length}</span>
        <span className="meta-pill">Build Packs: {safeArray(epic.stories).filter((story) => countFiles(story.generated_files) > 0).length}</span>
        <span className="meta-pill">Done for Email: {completedStories.length}</span>
      </div>
    </summary>

    <div className="dropdown-body">
      <div className="card-header">
        <h3>Epic Workspace</h3>
        <div className="row">
          <button type="button" onClick={() => onGenerateStories(epicIndex)}>Generate Stories</button>
          <button type="button" onClick={() => onPublishEpic(epic)}>
            Publish Epic to Jira
          </button>
        </div>
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
            epic={epic}
            story={story}
            storyIndex={storyIndex}
            demo={demo}
            selectedFilePath={selectedFilePath}
            onSelectFile={onSelectFile}
            onToggleSelected={() => onToggleStory(epicIndex, storyIndex)}
            onToggleCompleted={() => onToggleStoryCompleted(epicIndex, storyIndex)}
            onChange={(field, value) => onChangeStoryField(epicIndex, storyIndex, field, value)}
            onOpenBuildPackPrompt={() => onOpenBuildPackPrompt(epicIndex, storyIndex)}
            onGenerateDeliverables={() => onGenerateDeliverables(epicIndex, storyIndex)}
            onGenerateTests={onGenerateTests}
            onRunStoryTests={onRunStoryTests}
            onPublishStory={onPublishStory}
            onCompleteStoryInJira={onCompleteStoryInJira}
          />
        ))}
      </div>
    </div>
  </details>
  );
};

const WorkspacePersistencePanel = ({
  workspaceName,
  onWorkspaceNameChange,
  savedWorkspaces,
  selectedWorkspaceId,
  onSelectWorkspace,
  onSaveWorkspace,
  onLoadWorkspace,
  isSavingWorkspace,
  isLoadingWorkspace,
  canSaveWorkspace,
  lastSavedWorkspace,
}) => (
  <section className="panel">
    <SectionHeader
      title="Saved Workspace"
      subtitle="Save the generated epic/story order and the cumulative frontend, backend, and database code to disk so you can reopen it later and keep extending the same project."
    />

    <div className="workspace-persistence-grid">
      <div>
        <label>Workspace Name</label>
        <input
          value={workspaceName}
          onChange={(event) => onWorkspaceNameChange(event.target.value)}
          placeholder="Delivery Workspace"
        />
      </div>
      <div>
        <label>Saved Sessions</label>
        <select value={selectedWorkspaceId} onChange={(event) => onSelectWorkspace(event.target.value)}>
          <option value="">Select a saved workspace</option>
          {safeArray(savedWorkspaces).map((workspace) => (
            <option key={workspace.workspace_id} value={workspace.workspace_id}>
              {workspace.workspace_name} - {workspace.story_count} stories - {workspace.file_count} files
            </option>
          ))}
        </select>
      </div>
    </div>

    <div className="row">
      <button type="button" onClick={onSaveWorkspace} disabled={!canSaveWorkspace || isSavingWorkspace}>
        {isSavingWorkspace ? "Saving Workspace..." : "Save Workspace"}
      </button>
      <button type="button" onClick={onLoadWorkspace} disabled={!selectedWorkspaceId || isLoadingWorkspace}>
        {isLoadingWorkspace ? "Loading Workspace..." : "Load Workspace"}
      </button>
    </div>

    {lastSavedWorkspace ? (
      <div className="workspace-summary-card">
        <p className="muted"><strong>Workspace folder:</strong> {lastSavedWorkspace.workspace_path}</p>
        <p className="muted"><strong>Code folder:</strong> {lastSavedWorkspace.code_path}</p>
        <p className="muted"><strong>Tests folder:</strong> {lastSavedWorkspace.tests_path}</p>
        <p className="muted"><strong>Planning file:</strong> {lastSavedWorkspace.planning_path}</p>
      </div>
    ) : null}
  </section>
);

const ProjectWorkspace = ({
  epics,
  projectConfig,
  onProjectConfigChange,
  projectFiles,
  projectTestFiles,
  projectPreview,
  demo,
  selectedFilePath,
  onSelectFile,
  buildPackCount,
  manualCaseCount,
  automatedCaseCount,
  projectNotificationEmail,
  projectNotificationState,
  onProjectNotificationEmailChange,
  onSendProjectNotification,
}) => {
  const files = stripTestFiles(projectFiles);
  const testFiles = keepOnlyTestFiles(projectTestFiles);
  const unitTestCount = countPythonUnitTestsInFiles(testFiles);
  const browsableFiles = { ...files, ...testFiles };
  const preview = projectPreview || EMPTY_PREVIEW;
  const activeFilePath = selectedFilePath && browsableFiles[selectedFilePath] ? selectedFilePath : Object.keys(browsableFiles)[0] || "";
  const activeFileContent = activeFilePath ? browsableFiles[activeFilePath] : "";
  const demoUrl = demo?.url || getLiveAppUrl();
  const demoReady = Boolean(demo?.ready && demoUrl);
  const resolvedProjectConfig = normalizeProjectConfig(projectConfig);
  const completedStoryCount = safeArray(epics).reduce(
    (count, epic) => count + safeArray(epic.stories).filter((story) => story.completed).length,
    0,
  );

  return (
    <section className="panel">
      <SectionHeader
        title="Localhost Demo Workspace"
        subtitle="Each story build pack updates one cumulative localhost demo so you can inspect the generated UI as the same project grows."
      />

      <div className="project-email-panel">
        <div>
          <label>Project Notification Email</label>
          <input
            type="email"
            placeholder="team@example.com"
            value={projectNotificationEmail}
            onChange={(event) => onProjectNotificationEmailChange(event.target.value)}
          />
        </div>
        <div className="row">
          <span className="meta-pill">{safeArray(epics).length} epics</span>
          <span className="meta-pill">{completedStoryCount} completed stories selected</span>
          <button
            type="button"
            onClick={onSendProjectNotification}
            disabled={projectNotificationState === "sending"}
            title={projectNotificationEmail ? "" : "Add a notification email to deliver the project summary"}
          >
            {projectNotificationState === "sending" ? "Sending Email..." : "Send Project Email"}
          </button>
        </div>
      </div>

      <div className="workspace-toolbar">
        <div className="stack-picker">
          <label>Frontend Stack</label>
          <select
            value={resolvedProjectConfig.frontend_stack}
            onChange={(event) => onProjectConfigChange("frontend_stack", event.target.value)}
          >
            {FRONTEND_STACK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
        <div className="stack-picker">
          <label>Backend Stack</label>
          <select
            value={resolvedProjectConfig.backend_stack}
            onChange={(event) => onProjectConfigChange("backend_stack", event.target.value)}
          >
            {BACKEND_STACK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
        <div className="stack-picker">
          <label>Database</label>
          <select
            value={resolvedProjectConfig.database}
            onChange={(event) => onProjectConfigChange("database", event.target.value)}
          >
            {DATABASE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
        <div className="workspace-pills">
          <span className="meta-pill">{Object.keys(files).length} total files</span>
          <span className="meta-pill">{unitTestCount} unit tests</span>
          <span className="meta-pill">{buildPackCount} story build packs</span>
          <span className="meta-pill">{manualCaseCount} manual tests</span>
          <span className="meta-pill">{automatedCaseCount} automated tests</span>
          <span className="meta-pill">DB: {resolvedProjectConfig.database}</span>
        </div>
      </div>

      <div className="project-layout">
        <div className="project-preview-card">
          <div className="card-header">
            <h4>{demo?.title || preview.title || "Generated Application"}</h4>
            <DemoLinkButton ready={demoReady} url={demoUrl} />
          </div>
          <p>{preview.summary || EMPTY_PREVIEW.summary}</p>
          <div className="preview-highlight-row">
            {safeArray(preview.highlights).map((item) => (
              <span key={item} className="review-tag">{item}</span>
            ))}
          </div>
          <p className="muted">
            {demoReady
              ? `The cumulative demo is now available at ${demoUrl}. Each new story updates this same localhost page.`
              : "Generate a build pack to publish the cumulative demo to localhost."}
          </p>
          <iframe
            className="preview-frame"
            title="Generated application preview"
            src={demoReady ? demoUrl : undefined}
            srcDoc={demoReady ? undefined : (preview.html || DEFAULT_PREVIEW_HTML)}
          />
        </div>

        <div className="project-files-card">
          <h4>Project Files</h4>
          <FileCollection title="Application Files" files={files} selectedFilePath={activeFilePath} onSelectFile={onSelectFile} />
          <FileCollection title="Test Files" files={testFiles} selectedFilePath={activeFilePath} onSelectFile={onSelectFile} />
          {!Object.keys(browsableFiles).length ? <p className="muted">No project files generated yet.</p> : null}
          {activeFilePath ? (
            <div className="code-block">
              <h5>{activeFilePath}</h5>
              <pre>{activeFileContent}</pre>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
};

const CumulativeTestRunner = ({
  totalUnitTests,
  totalTestStories,
  projectTestRunState,
  projectTestRunResult,
  onRunAllStoryTests,
}) => (
  <section className="panel">
    <SectionHeader
      title="Cumulative Test Runner"
      subtitle="Run the generated test files across multiple stories together without changing the current build-pack generation flow."
    />
    <div className="row">
      <span className="meta-pill">{totalTestStories} stories with tests</span>
      <span className="meta-pill">{totalUnitTests} total unit tests</span>
      <button type="button" disabled={!totalUnitTests || projectTestRunState === "running"} onClick={onRunAllStoryTests}>
        {projectTestRunState === "running" ? "Running All Story Tests..." : "Run All Story Tests"}
      </button>
    </div>
    <TestRunResult result={projectTestRunResult} emptyLabel="Run all generated story tests to see the cumulative result here." />
  </section>
);

const PlanningPage = ({
  epics,
  chunks,
  workspaceName,
  savedWorkspaces,
  selectedWorkspaceId,
  isSavingWorkspace,
  isLoadingWorkspace,
  lastSavedWorkspace,
  projectConfig,
  projectFiles,
  projectPreview,
  projectDemo,
  selectedFilePath,
  selectedStories,
  totalStories,
  buildPackCount,
  manualCaseCount,
  automatedCaseCount,
  projectNotificationEmail,
  projectNotificationState,
  onSelectFile,
  onWorkspaceNameChange,
  onSelectWorkspace,
  onSaveWorkspace,
  onLoadWorkspace,
  onProjectConfigChange,
  onUploadRequirements,
  onGenerateEpics,
  onGenerateStories,
  onOpenBuildPackPrompt,
  onGenerateDeliverables,
  onGenerateTests,
  onRunStoryTests,
  onChangeEpicField,
  onChangeStoryField,
  onToggleStorySelection,
  onToggleStoryCompleted,
  onPublishSelectedStories,
  onPublishEpic,
  onPublishStory,
  onCompleteStoryInJira,
  onPublishAll,
  totalUnitTests,
  totalTestStories,
  projectTestFiles,
  projectTestRunState,
  projectTestRunResult,
  onRunAllStoryTests,
  onProjectNotificationEmailChange,
  onSendProjectNotification,
}) => (
  <>
    <section className="insight-row four-up">
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
      <div className="insight-card">
        <p>Build Packs</p>
        <h3>{buildPackCount}</h3>
      </div>
    </section>

    <WorkspacePersistencePanel
      workspaceName={workspaceName}
      onWorkspaceNameChange={onWorkspaceNameChange}
      savedWorkspaces={savedWorkspaces}
      selectedWorkspaceId={selectedWorkspaceId}
      onSelectWorkspace={onSelectWorkspace}
      onSaveWorkspace={onSaveWorkspace}
      onLoadWorkspace={onLoadWorkspace}
      isSavingWorkspace={isSavingWorkspace}
      isLoadingWorkspace={isLoadingWorkspace}
      canSaveWorkspace={Boolean(chunks.length || epics.length || Object.keys(stripTestFiles(projectFiles)).length || Object.keys(projectTestFiles).length)}
      lastSavedWorkspace={lastSavedWorkspace}
    />

    <section className="panel">
      <SectionHeader title="Epic and Story Planning" subtitle="Generate from requirements, then review each story and build implementation assets directly inside the planning flow." />

      <div className="row">
        <input type="file" onChange={onUploadRequirements} />
        <button disabled={!chunks.length} onClick={onGenerateEpics}>Generate Epics</button>
      </div>

      {safeArray(epics).map((epic, epicIndex) => (
        <EpicEditor
          key={`${epic.summary || epic.epic_name || "epic"}-${epicIndex}`}
          epic={epic}
          epicIndex={epicIndex}
          demo={projectDemo}
          selectedFilePath={selectedFilePath}
          onSelectFile={onSelectFile}
          onChangeEpicField={onChangeEpicField}
          onGenerateStories={onGenerateStories}
          onOpenBuildPackPrompt={onOpenBuildPackPrompt}
          onGenerateDeliverables={onGenerateDeliverables}
          onGenerateTests={onGenerateTests}
          onRunStoryTests={onRunStoryTests}
          onChangeStoryField={onChangeStoryField}
          onToggleStory={onToggleStorySelection}
          onToggleStoryCompleted={onToggleStoryCompleted}
          onPublishEpic={onPublishEpic}
          onPublishStory={onPublishStory}
          onCompleteStoryInJira={onCompleteStoryInJira}
        />
      ))}

      <div className="row">
        <button disabled={!selectedStories.length} onClick={onPublishSelectedStories}>
          Create {selectedStories.length} Selected Stories in Jira
        </button>
        <button disabled={!totalStories} onClick={onPublishAll}>
          Publish All Epics and Stories to Jira
        </button>
      </div>
    </section>

    <ProjectWorkspace
      epics={epics}
      projectConfig={projectConfig}
      onProjectConfigChange={onProjectConfigChange}
      projectFiles={projectFiles}
      projectTestFiles={projectTestFiles}
      projectPreview={projectPreview}
      demo={projectDemo}
      selectedFilePath={selectedFilePath}
      onSelectFile={onSelectFile}
      buildPackCount={buildPackCount}
      manualCaseCount={manualCaseCount}
      automatedCaseCount={automatedCaseCount}
      projectNotificationEmail={projectNotificationEmail}
      projectNotificationState={projectNotificationState}
      onProjectNotificationEmailChange={onProjectNotificationEmailChange}
      onSendProjectNotification={onSendProjectNotification}
    />

    <CumulativeTestRunner
      totalUnitTests={totalUnitTests}
      totalTestStories={totalTestStories}
      projectTestRunState={projectTestRunState}
      projectTestRunResult={projectTestRunResult}
      onRunAllStoryTests={onRunAllStoryTests}
    />
  </>
);

const DuplicateCheckerPage = ({ duplicateStory, setDuplicateStory, duplicates, checkDuplicates }) => (
  <section className="panel">
    <SectionHeader title="Duplicate Checker" subtitle="Dedicated workspace for analysts validating repeated stories. Planning data stays untouched." />

    <label>Story Summary</label>
    <input placeholder="Story summary" value={duplicateStory.summary} onChange={(event) => setDuplicateStory((previous) => ({ ...previous, summary: event.target.value }))} />

    <label>Story Details</label>
    <textarea rows={4} placeholder="Story details" value={duplicateStory.details} onChange={(event) => setDuplicateStory((previous) => ({ ...previous, details: event.target.value, description: event.target.value }))} />

    <button onClick={checkDuplicates}>Check Duplicates</button>

    <ul className="result-list">
      {safeArray(duplicates).map((dup) => (
        <li key={dup.jira_key}>{dup.jira_key} - Similarity {dup.similarity}</li>
      ))}
    </ul>
  </section>
);

export function App() {
  const [status, setStatus] = useState("");
  const [activePage, setActivePage] = useState("planning");

  const [jiraConfig, setJiraConfig] = useState({});
  const [jiraHealth, setJiraHealth] = useState(null);

  const [chunks, setChunks] = useState([]);
  const [epics, setEpics] = useState([]);
  const [requirementsFilename, setRequirementsFilename] = useState("");
  const [workspaceName, setWorkspaceName] = useState("Delivery Workspace");
  const [savedWorkspaces, setSavedWorkspaces] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState("");
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [lastSavedWorkspace, setLastSavedWorkspace] = useState(null);
  const [projectConfig, setProjectConfig] = useState({ ...DEFAULT_PROJECT_CONFIG });
  const [projectFiles, setProjectFiles] = useState({});
  const [projectTestFiles, setProjectTestFiles] = useState({});
  const [projectPreview, setProjectPreview] = useState(EMPTY_PREVIEW);
  const [projectDemo, setProjectDemo] = useState(EMPTY_DEMO);
  const [projectNotificationEmail, setProjectNotificationEmail] = useState("");
  const [projectNotificationState, setProjectNotificationState] = useState("idle");
  const [projectTestRunState, setProjectTestRunState] = useState("idle");
  const [projectTestRunResult, setProjectTestRunResult] = useState(null);
  const [selectedFilePath, setSelectedFilePath] = useState("");
  const [buildPackModalState, setBuildPackModalState] = useState({
    open: false,
    epicIndex: -1,
    storyIndex: -1,
    value: normalizeUiReference(),
  });

  const [duplicateStory, setDuplicateStory] = useState({ ...EMPTY_STORY });
  const [duplicates, setDuplicates] = useState([]);

  useEffect(() => {
    fetchJson("/jira/config")
      .then((data) => setJiraConfig(data || {}))
      .catch((error) => setStatus(error.message));
  }, []);

  useEffect(() => {
    fetchJson("/workspaces")
      .then((data) => {
        const workspaces = safeArray(data?.workspaces);
        setSavedWorkspaces(workspaces);
        if (workspaces[0]?.workspace_id) {
          setSelectedWorkspaceId((previous) => previous || workspaces[0].workspace_id);
        }
      })
      .catch(() => {});
  }, []);

  const selectedStories = useMemo(
    () =>
      safeArray(epics).flatMap((epic) =>
        safeArray(epic.stories)
          .filter((story) => story.selected)
          .map((story) => getStoryJiraPayload(epic, story))
      ),
    [epics]
  );
  const allGeneratedStories = useMemo(
    () =>
      safeArray(epics).flatMap((epic) =>
        safeArray(epic.stories).map((story) => getStoryJiraPayload(epic, story))
      ),
    [epics]
  );

  const totalStories = useMemo(() => safeArray(epics).reduce((acc, epic) => acc + safeArray(epic.stories).length, 0), [epics]);
  const buildPackCount = useMemo(
    () =>
      safeArray(epics).reduce(
        (acc, epic) => acc + safeArray(epic.stories).filter((story) => countFiles(story.generated_files) > 0).length,
        0,
      ),
    [epics]
  );
  const manualCaseCount = useMemo(
    () =>
      safeArray(epics).reduce(
        (acc, epic) => acc + safeArray(epic.stories).reduce((sum, story) => sum + safeArray(story.manual_test_cases).length, 0),
        0,
      ),
    [epics]
  );
  const automatedCaseCount = useMemo(
    () =>
      safeArray(epics).reduce(
        (acc, epic) => acc + safeArray(epic.stories).reduce((sum, story) => sum + safeArray(story.automated_test_cases).length, 0),
        0,
      ),
    [epics]
  );
  const totalUnitTests = useMemo(() => countAllUnitTests(epics), [epics]);
  const totalTestStories = useMemo(
    () =>
      safeArray(epics).reduce(
        (acc, epic) => acc + safeArray(epic.stories).filter((story) => countFiles(story.unit_test_files) > 0).length,
        0,
      ),
    [epics]
  );

  const updateEpic = (epicIndex, updater) => {
    setEpics((previous) => previous.map((epic, index) => (index === epicIndex ? updater(epic) : epic)));
  };

  const updateStory = (epicIndex, storyIndex, updater) => {
    updateEpic(epicIndex, (epic) => ({
      ...epic,
      stories: safeArray(epic.stories).map((story, index) => (index === storyIndex ? updater(story) : story)),
    }));
  };

  const resetWorkspace = () => {
    setProjectFiles({});
    setProjectTestFiles({});
    setProjectPreview(EMPTY_PREVIEW);
    setProjectDemo(EMPTY_DEMO);
    setProjectNotificationEmail("");
    setProjectNotificationState("idle");
    setProjectTestRunState("idle");
    setProjectTestRunResult(null);
    setSelectedFilePath("");
  };

  const refreshSavedWorkspaces = async (preferredWorkspaceId = "") => {
    const data = await fetchJson("/workspaces");
    const workspaces = safeArray(data?.workspaces);
    setSavedWorkspaces(workspaces);
    if (preferredWorkspaceId) {
      setSelectedWorkspaceId(preferredWorkspaceId);
      return;
    }
    if (!selectedWorkspaceId && workspaces[0]?.workspace_id) {
      setSelectedWorkspaceId(workspaces[0].workspace_id);
    }
  };

  const publishDemoSnapshot = async (files, preview, nextProjectConfig) => {
    const resolvedProjectConfig = normalizeProjectConfig(nextProjectConfig);
    if (!Object.keys(stripTestFiles(files)).length) {
      setProjectDemo(EMPTY_DEMO);
      return { ready: false, url: "", title: preview?.title || EMPTY_DEMO.title };
    }

    const previewUrl = getLiveAppUrl();
    const demoState = await fetchJson("/project/publish-demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: stripTestFiles(files),
        preview,
        stack: resolvedProjectConfig.backend_stack,
        project_config: resolvedProjectConfig,
      }),
    });

    const nextDemo = {
      ready: Boolean(previewUrl || demoState?.ready),
      url: previewUrl,
      title: demoState?.title || preview?.title || "Generated Application",
    };
    setProjectDemo(nextDemo);
    return nextDemo;
  };

  const applyLoadedWorkspace = async (workspace) => {
    const nextEpics = safeArray(workspace?.epics).map(normalizeEpic);
    const nextFiles = stripTestFiles(workspace?.project_files);
    const nextTestFiles = keepOnlyTestFiles(workspace?.project_test_files);
    const nextPreview = workspace?.project_preview || EMPTY_PREVIEW;
    const nextProjectConfig = normalizeProjectConfig(workspace?.project_config, workspace?.project_stack);
    const nextBrowsableFiles = { ...nextFiles, ...nextTestFiles };
    const nextSelectedFilePath =
      workspace?.selected_file_path && nextBrowsableFiles[workspace.selected_file_path]
        ? workspace.selected_file_path
        : Object.keys(nextBrowsableFiles)[0] || "";

    setRequirementsFilename(workspace?.requirements_filename || "");
    setWorkspaceName(workspace?.workspace_name || workspaceName);
    setChunks(safeArray(workspace?.chunks));
    setEpics(nextEpics);
    setProjectConfig(nextProjectConfig);
    setProjectFiles(nextFiles);
    setProjectTestFiles(nextTestFiles);
    setProjectPreview(nextPreview);
    setProjectNotificationEmail(workspace?.project_notification_email || "");
    setProjectNotificationState("idle");
    setProjectTestRunState("idle");
    setProjectTestRunResult(null);
    setSelectedFilePath(nextSelectedFilePath);
    setCurrentWorkspaceId(workspace?.workspace_id || workspace?.summary?.workspace_id || "");
    setSelectedWorkspaceId(workspace?.workspace_id || workspace?.summary?.workspace_id || "");
    setLastSavedWorkspace(workspace?.summary || null);

    try {
      await publishDemoSnapshot(nextFiles, nextPreview, nextProjectConfig);
      setStatus(`Loaded workspace ${workspace?.workspace_name || workspace?.workspace_id || ""}`);
    } catch (error) {
      setProjectDemo({
        ready: false,
        url: "",
        title: nextPreview.title || EMPTY_DEMO.title,
      });
      setStatus(`Loaded workspace, but localhost demo publish failed: ${error.message}`);
    }
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
      setEpics([]);
      setRequirementsFilename(data?.filename || file.name);
      setWorkspaceName((previous) => {
        const trimmed = (previous || "").trim();
        return trimmed && trimmed !== "Delivery Workspace" ? previous : deriveWorkspaceName(data?.filename || file.name);
      });
      resetWorkspace();
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
      resetWorkspace();
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

  const onGenerateDeliverables = async (epicIndex, storyIndex, uiReferenceOverride = null) => {
    const epic = epics[epicIndex];
    const story = epic?.stories?.[storyIndex];
    if (!epic || !story) return;
    const previousStoryTestPaths = Object.keys(keepOnlyTestFiles(story.unit_test_files));
    const resolvedUiReference = normalizeUiReference(uiReferenceOverride ?? story.ui_reference);

    updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, delivery_status: "generating" }));
    setStatus(`Generating build pack for ${story.summary}...`);

    try {
      const payload = {
        ...story,
        epic_name: epic.summary || epic.epic_name || "AI Generated Epic",
        description: story.description || story.details,
        ui_reference: resolvedUiReference,
      };
      const data = await fetchJson("/stories/generate-deliverables", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story: payload,
          stack: getLegacyStackFromProjectConfig(projectConfig),
          project_config: normalizeProjectConfig(projectConfig),
          existing_files: stripTestFiles(projectFiles),
        }),
      });

      const nextFiles = stripTestFiles(data?.files);
      const mergedProjectFiles = { ...stripTestFiles(projectFiles), ...nextFiles };
      const nextTestFiles = keepOnlyTestFiles(data?.unit_test_files);
      const remainingProjectTestFiles = Object.fromEntries(
        Object.entries(projectTestFiles).filter(([path]) => !previousStoryTestPaths.includes(path)),
      );
      const mergedProjectTestFiles = { ...remainingProjectTestFiles, ...nextTestFiles };
      const nextPreview = data?.preview || EMPTY_PREVIEW;

      setProjectFiles(mergedProjectFiles);
      setProjectTestFiles(mergedProjectTestFiles);
      if (!selectedFilePath) {
        const firstFile = Object.keys({ ...nextFiles, ...nextTestFiles })[0];
        if (firstFile) setSelectedFilePath(firstFile);
      }

      setProjectPreview(nextPreview);

      updateStory(epicIndex, storyIndex, (previous) =>
        normalizeStory({
          ...previous,
          generated_files: nextFiles,
          unit_test_files: nextTestFiles,
          manual_test_cases: safeArray(data?.manual_test_cases),
          automated_test_cases: safeArray(data?.automated_test_cases),
          preview: data?.preview || null,
          ui_reference: resolvedUiReference,
          delivery_status: "ready",
          test_generation_state: nextTestFiles && Object.keys(nextTestFiles).length ? "done" : previous.test_generation_state,
        }),
      );

      try {
        await publishDemoSnapshot(mergedProjectFiles, nextPreview, projectConfig);
      } catch (demoError) {
        setProjectDemo({
          ready: false,
          url: "",
          title: nextPreview.title || "Generated Application",
        });
        setStatus(`Generated build pack for ${story.summary}, but localhost demo publish failed: ${demoError.message}`);
        return;
      }

      setStatus(formatNotificationStatus(data?.notification, `Generated build pack for ${story.summary}`));
    } catch (error) {
      updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, delivery_status: "error" }));
      setStatus(error.message);
    }
  };

  const generateStoryTests = async (epic, story) => {
    const epicIndex = epics.findIndex((candidate) => candidate === epic);
    const storyIndex = safeArray(epic?.stories).findIndex((candidate) => candidate === story);
    if (epicIndex < 0 || storyIndex < 0 || countFiles(story.generated_files) === 0) return;
    const previousStoryTestPaths = Object.keys(keepOnlyTestFiles(story.unit_test_files));

    updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, test_generation_state: "generating" }));
    setStatus(`Generating test cases for ${story.summary || "story"}...`);

    try {
      const data = await fetchJson("/stories/generate-tests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story: getStoryJiraPayload(epic, story),
          existing_code: buildCodeContext({ ...stripTestFiles(projectFiles), ...safeObject(story.generated_files) }),
          stack: getLegacyStackFromProjectConfig(projectConfig),
          project_config: normalizeProjectConfig(projectConfig),
        }),
      });

      const nextTestFiles = keepOnlyTestFiles(data?.unit_test_files);
      const remainingProjectTestFiles = Object.fromEntries(
        Object.entries(projectTestFiles).filter(([path]) => !previousStoryTestPaths.includes(path)),
      );
      const mergedProjectTestFiles = { ...remainingProjectTestFiles, ...nextTestFiles };
      setProjectTestFiles(mergedProjectTestFiles);
      if (!selectedFilePath) {
        const firstTestFile = Object.keys(nextTestFiles)[0];
        if (firstTestFile) setSelectedFilePath(firstTestFile);
      }

      updateStory(epicIndex, storyIndex, (previous) =>
        normalizeStory({
          ...previous,
          unit_test_files: nextTestFiles,
          manual_test_cases: safeArray(data?.manual_test_cases),
          automated_test_cases: safeArray(data?.automated_test_cases),
          test_generation_state: "done",
        }),
      );

      setStatus(formatNotificationStatus(data?.notification, `Generated test cases for ${story.summary || "story"}`));
    } catch (error) {
      updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, test_generation_state: "idle" }));
      setStatus(error.message);
    }
  };

  const runStoryTests = async (epic, story) => {
    const epicIndex = epics.findIndex((candidate) => candidate === epic);
    const storyIndex = safeArray(epic?.stories).findIndex((candidate) => candidate === story);
    const storyTestPaths = Object.keys(keepOnlyTestFiles(story?.unit_test_files));
    if (epicIndex < 0 || storyIndex < 0 || !storyTestPaths.length) return;

    updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, test_run_state: "running" }));
    setStatus(`Running tests for ${story.summary || "story"}...`);

    try {
      const mergedTestFiles = mergeStoryTestFiles(epics);
      const data = await fetchJson("/project/run-tests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: { ...stripTestFiles(projectFiles), ...mergedTestFiles },
          stack: getLegacyStackFromProjectConfig(projectConfig),
          test_paths: storyTestPaths,
        }),
      });

      updateStory(epicIndex, storyIndex, (previous) =>
        normalizeStory({
          ...previous,
          test_run_state: "done",
          test_run_result: data,
        }),
      );

      setStatus(`${story.summary || "Story"} tests ${data?.ok ? "passed" : "finished with failures"}.`);
    } catch (error) {
      updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, test_run_state: "idle" }));
      setStatus(error.message);
    }
  };

  const sendProjectNotification = async () => {
    setProjectNotificationState("sending");
    setStatus("Sending project email...");

    try {
      const data = await fetchJson("/project/send-notification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          epics,
          notification_email: projectNotificationEmail,
        }),
      });

      setProjectNotificationState("idle");
      setStatus(formatNotificationStatus(data?.notification, "Sent project notification"));
    } catch (error) {
      setProjectNotificationState("idle");
      setStatus(error.message);
    }
  };

  const runAllStoryTests = async () => {
    const testPaths = collectStoryTestPaths(epics);
    if (!testPaths.length) return;

    setProjectTestRunState("running");
    setStatus("Running all generated story tests...");

    try {
      const mergedTestFiles = mergeStoryTestFiles(epics);
      const data = await fetchJson("/project/run-tests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          files: { ...stripTestFiles(projectFiles), ...mergedTestFiles },
          stack: getLegacyStackFromProjectConfig(projectConfig),
          test_paths: testPaths,
        }),
      });
      setProjectTestRunState("done");
      setProjectTestRunResult(data);
      setStatus(data?.ok ? "All generated story tests passed." : "Some generated story tests failed.");
    } catch (error) {
      setProjectTestRunState("idle");
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

  const onToggleStoryCompleted = (epicIndex, storyIndex) => {
    updateStory(epicIndex, storyIndex, (story) => ({ ...story, completed: !story.completed }));
  };

  const publishStoriesToJira = async (stories, statusLabel) => {
    if (!stories.length) return [];

    setStatus(`${statusLabel}...`);
    try {
      const data = await fetchJson("/jira/create-stories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stories }),
      });
      const keys = safeArray(data?.keys);
      setStatus(keys.length ? `Created Jira issues: ${keys.join(", ")}` : "Story creation request sent to Jira");
      return keys;
    } catch (error) {
      setStatus(error.message);
      return [];
    }
  };

  const createJiraStories = async () => publishStoriesToJira(selectedStories, "Creating selected stories in Jira");

  const publishStoryToJira = async (epic, story) => {
    if (!story?.selected) return;
    const epicIndex = epics.findIndex((candidate) => candidate === epic);
    const storyIndex = safeArray(epic?.stories).findIndex((candidate) => candidate === story);
    const keys = await publishStoriesToJira([getStoryJiraPayload(epic, story)], `Creating ${story.summary || "story"} in Jira`);
    if (epicIndex >= 0 && storyIndex >= 0 && keys[0]) {
      updateStory(epicIndex, storyIndex, (previous) => normalizeStory({ ...previous, jira_issue_key: keys[0], jira_status: previous.jira_status || "Created" }));
    }
  };

  const publishEpicToJira = async (epic) => {
    const stories = safeArray(epic?.stories).map((story) => getStoryJiraPayload(epic, story));
    await publishStoriesToJira(stories, `Publishing ${epic?.summary || epic?.epic_name || "epic"} to Jira`);
  };

  const publishAllToJira = async () => publishStoriesToJira(allGeneratedStories, "Publishing all epics and stories to Jira");

  const completeStoryInJira = async (epic, story) => {
    const epicIndex = epics.findIndex((candidate) => candidate === epic);
    const storyIndex = safeArray(epic?.stories).findIndex((candidate) => candidate === story);
    if (epicIndex < 0 || storyIndex < 0 || countFiles(story.generated_files) === 0) return;

    updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, jira_transition_state: "updating" }));
    setStatus(`Updating Jira status for ${story.summary || "story"}...`);

    try {
      const data = await fetchJson("/jira/complete-story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          story: getStoryJiraPayload(epic, story),
          issue_key: story.jira_issue_key || "",
        }),
      });

      updateStory(epicIndex, storyIndex, (previous) =>
        normalizeStory({
          ...previous,
          jira_issue_key: data?.issue_key || previous.jira_issue_key,
          jira_status: data?.status || "Done",
          jira_transition_state: "done",
        }),
      );

      setStatus(
        `${story.summary || "Story"} is ${data?.status || "Done"} in Jira${data?.issue_key ? ` (${data.issue_key})` : ""}${
          data?.created_issue ? " after creating the issue." : "."
        }`,
      );
    } catch (error) {
      updateStory(epicIndex, storyIndex, (previous) => ({ ...previous, jira_transition_state: "idle" }));
      if (String(error.message || "").includes("404")) {
        setStatus("`/jira/complete-story` returned 404. Restart the backend on port 8000 so it loads the new Jira completion endpoint, then try again.");
      } else {
        setStatus(error.message);
      }
    }
  };

  const onSaveWorkspace = async () => {
    setIsSavingWorkspace(true);
    setStatus("Saving workspace to disk...");

    try {
      const payload = {
        workspace_id: currentWorkspaceId || undefined,
        workspace_name: workspaceName.trim() || deriveWorkspaceName(requirementsFilename),
        requirements_filename: requirementsFilename,
        chunks,
        epics,
        project_stack: getLegacyStackFromProjectConfig(projectConfig),
        project_config: normalizeProjectConfig(projectConfig),
        project_files: stripTestFiles(projectFiles),
        project_test_files: projectTestFiles,
        project_preview: projectPreview,
        project_demo: projectDemo,
        project_notification_email: projectNotificationEmail,
        selected_file_path: selectedFilePath,
      };

      const data = await fetchJson("/workspaces/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      setCurrentWorkspaceId(data?.workspace_id || "");
      setSelectedWorkspaceId(data?.workspace_id || "");
      setWorkspaceName(data?.workspace_name || payload.workspace_name);
      setLastSavedWorkspace(data || null);
      await refreshSavedWorkspaces(data?.workspace_id || "");
      setStatus(`Workspace saved to ${data?.code_path || "saved_workspaces"}`);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsSavingWorkspace(false);
    }
  };

  const onLoadWorkspace = async () => {
    if (!selectedWorkspaceId) return;

    setIsLoadingWorkspace(true);
    setStatus("Loading saved workspace...");

    try {
      const workspace = await fetchJson(`/workspaces/${selectedWorkspaceId}`);
      await applyLoadedWorkspace(workspace);
    } catch (error) {
      setStatus(error.message);
    } finally {
      setIsLoadingWorkspace(false);
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

  const closeBuildPackModal = () => {
    setBuildPackModalState({
      open: false,
      epicIndex: -1,
      storyIndex: -1,
      value: normalizeUiReference(),
    });
  };

  const openBuildPackModal = (epicIndex, storyIndex) => {
    const story = epics[epicIndex]?.stories?.[storyIndex];
    if (!story) return;

    setBuildPackModalState({
      open: true,
      epicIndex,
      storyIndex,
      value: normalizeUiReference(story.ui_reference),
    });
  };

  const onBuildPackReferenceTextChange = (text) => {
    setBuildPackModalState((previous) => ({
      ...previous,
      value: {
        ...previous.value,
        text,
      },
    }));
  };

  const onBuildPackReferenceFileChange = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    const dataUrl = await new Promise((resolve, reject) => {
      reader.onload = () => resolve(String(reader.result || ""));
      reader.onerror = () => reject(new Error("Unable to read the selected screenshot."));
      reader.readAsDataURL(file);
    });

    setBuildPackModalState((previous) => ({
      ...previous,
      value: {
        ...previous.value,
        image_name: file.name,
        image_media_type: file.type || "image/png",
        image_data_url: dataUrl,
      },
    }));
  };

  const confirmBuildPackGeneration = async () => {
    if (buildPackModalState.epicIndex < 0 || buildPackModalState.storyIndex < 0) return;

    const normalizedReference = normalizeUiReference(buildPackModalState.value);
    updateStory(buildPackModalState.epicIndex, buildPackModalState.storyIndex, (story) =>
      normalizeStory({
        ...story,
        ui_reference: normalizedReference,
      }),
    );

    await onGenerateDeliverables(buildPackModalState.epicIndex, buildPackModalState.storyIndex, normalizedReference);
    closeBuildPackModal();
  };

  return (
    <>
      <div className="app-shell">
      <header className="hero">
        <div>
          <h1>Jira Delivery Studio</h1>
          <p>Plan epics, generate story build packs, and grow the application project inside one workflow.</p>
        </div>
        <div className="status-pill">{status || "Ready"}</div>
      </header>

      <section className="panel">
        <SectionHeader title="Jira Workspace Configuration" subtitle="Shared config for planning and publishing generated stories into Jira." />
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
          workspaceName={workspaceName}
          savedWorkspaces={savedWorkspaces}
          selectedWorkspaceId={selectedWorkspaceId}
          isSavingWorkspace={isSavingWorkspace}
          isLoadingWorkspace={isLoadingWorkspace}
          lastSavedWorkspace={lastSavedWorkspace}
          projectConfig={projectConfig}
          projectFiles={projectFiles}
          projectTestFiles={projectTestFiles}
          projectPreview={projectPreview}
          projectDemo={projectDemo}
          projectNotificationEmail={projectNotificationEmail}
          projectNotificationState={projectNotificationState}
          selectedFilePath={selectedFilePath}
          selectedStories={selectedStories}
          totalStories={totalStories}
          buildPackCount={buildPackCount}
          manualCaseCount={manualCaseCount}
          automatedCaseCount={automatedCaseCount}
          onSelectFile={setSelectedFilePath}
          onWorkspaceNameChange={setWorkspaceName}
          onSelectWorkspace={setSelectedWorkspaceId}
          onSaveWorkspace={onSaveWorkspace}
          onLoadWorkspace={onLoadWorkspace}
          onProjectConfigChange={(field, value) =>
            setProjectConfig((previous) => normalizeProjectConfig({ ...previous, [field]: value }))
          }
          onProjectNotificationEmailChange={setProjectNotificationEmail}
          onSendProjectNotification={sendProjectNotification}
          onUploadRequirements={onUploadRequirements}
          onGenerateEpics={onGenerateEpics}
          onGenerateStories={onGenerateStories}
          onOpenBuildPackPrompt={openBuildPackModal}
          onGenerateDeliverables={onGenerateDeliverables}
          onGenerateTests={generateStoryTests}
          onRunStoryTests={runStoryTests}
          onChangeEpicField={onChangeEpicField}
          onChangeStoryField={onChangeStoryField}
          onToggleStorySelection={onToggleStorySelection}
          onToggleStoryCompleted={onToggleStoryCompleted}
          onPublishSelectedStories={createJiraStories}
          onPublishEpic={publishEpicToJira}
          onPublishStory={publishStoryToJira}
          onCompleteStoryInJira={completeStoryInJira}
          onPublishAll={publishAllToJira}
          totalUnitTests={totalUnitTests}
          totalTestStories={totalTestStories}
          projectTestRunState={projectTestRunState}
          projectTestRunResult={projectTestRunResult}
          onRunAllStoryTests={runAllStoryTests}
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
      </div>
      <BuildPackPromptModal
        open={buildPackModalState.open}
        storySummary={epics[buildPackModalState.epicIndex]?.stories?.[buildPackModalState.storyIndex]?.summary || ""}
        value={buildPackModalState.value}
        imagePreviewUrl={buildPackModalState.value.image_data_url}
        onTextChange={onBuildPackReferenceTextChange}
        onFileChange={onBuildPackReferenceFileChange}
        onClose={closeBuildPackModal}
        onConfirm={confirmBuildPackGeneration}
        loading={epics[buildPackModalState.epicIndex]?.stories?.[buildPackModalState.storyIndex]?.delivery_status === "generating"}
      />
    </>
  );
}
