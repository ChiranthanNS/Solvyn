(() => {
  "use strict";

  const API_BASE = (window.SOLVYN_API_URL || "").replace(/\/$/, "");
  const app = document.querySelector("#app");
  const state = {
    token: sessionStorage.getItem("solvyn_access_token"),
    mode: "login",
    view: "workspace",
    messages: [],
    diary: [],
    loadingHistory: false,
    loadingDiary: false,
    sending: false,
    authBusy: false,
    diaryBusy: false,
    apiState: "checking",
    historyError: "",
    diaryError: "",
    authError: "",
    notice: "",
    solveError: "",
  };

  const icons = {
    mark: '<svg viewBox="0 0 32 34" fill="none" aria-hidden="true"><path d="M18.4 2.5 5.5 14.2l7.1 4.2-2.1 11.1 16-14.2-8.2-4.1 2.1-8.7Z" stroke="currentColor" stroke-width="3.2" stroke-linejoin="round"/><path d="m7.8 20.2 2.8 1.7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
    home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><rect x="3.5" y="3.5" width="7" height="7" rx="1.2"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.2"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.2"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.2"/></svg>',
    history: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M3.4 11.5a8.7 8.7 0 1 1 2.3 6"/><path d="M3.5 5.7v5.8h5.8M12 7.2v5.1l3.3 2"/></svg>',
    diary: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M6 3.5h12a1.5 1.5 0 0 1 1.5 1.5v14a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 19V5A1.5 1.5 0 0 1 6 3.5Z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m4 4 16 8-16 8 3-8-3-8Z"/><path d="M7 12h13"/></svg>',
    assistant: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m12 2 2.3 7.7L22 12l-7.7 2.3L12 22l-2.3-7.7L2 12l7.7-2.3L12 2Z"/><path d="m19 2 .8 2.2L22 5l-2.2.8L19 8l-.8-2.2L16 5l2.2-.8L19 2Z"/></svg>',
  };

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const initials = (value) => (value || "S").trim().split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
  const formatDate = (value) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Date unavailable" : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
  };
  const isSolutionPayload = (value) => Boolean(
    value && typeof value === "object" && !Array.isArray(value) &&
    typeof value.title === "string" && typeof value.summary === "string" &&
    Array.isArray(value.analysis) && Array.isArray(value.steps) &&
    Array.isArray(value.tree) && typeof value.complexity === "string" &&
    Array.isArray(value.related_tools) &&
    value.steps.every((step) => step && typeof step.title === "string" && typeof step.description === "string") &&
    value.tree.every((node) => node && typeof node.id === "string" &&
      typeof node.label === "string" &&
      (node.parent_id === null || typeof node.parent_id === "string") &&
      (node.description === undefined || typeof node.description === "string")) &&
    value.analysis.every((item) => typeof item === "string") &&
    value.related_tools.every((item) => typeof item === "string") &&
    (value.code_language === null || value.code_language === undefined || typeof value.code_language === "string") &&
    (value.code === null || value.code === undefined || typeof value.code === "string") &&
    (value.formula === null || value.formula === undefined || typeof value.formula === "string") &&
    (value.elapsed_seconds === null || value.elapsed_seconds === undefined || (typeof value.elapsed_seconds === "number" && Number.isFinite(value.elapsed_seconds))) &&
    (value.token_usage === null || value.token_usage === undefined || (typeof value.token_usage === "number" && Number.isFinite(value.token_usage)))
  );
  const parseSolutionPayload = (message) => {
    if (isSolutionPayload(message)) return message;
    if (typeof message !== "string") return null;
    try {
      const parsed = JSON.parse(message);
      return isSolutionPayload(parsed) ? parsed : null;
    } catch {
      return null;
    }
  };
  const latestSolution = (messages) => {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index];
      if (item.sender !== "user") {
        const solution = parseSolutionPayload(item.message ?? item.content);
        if (solution) return solution;
      }
    }
    return null;
  };
  const request = async (path, options = {}) => {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (state.token) headers.Authorization = `Bearer ${state.token}`;
    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "omit" });
    } catch {
      state.apiState = "error";
      throw new Error(`Could not reach the Solvyn API${API_BASE ? ` at ${API_BASE}` : ""}. Check that the backend is running and the address is correct.`);
    }
    if (response.status === 401 && state.token) {
      sessionStorage.removeItem("solvyn_access_token");
      state.token = null;
      state.messages = [];
      state.diary = [];
      render();
      throw new Error("Your session has expired. Sign in again to continue.");
    }
    let payload = null;
    try { payload = await response.json(); } catch { /* response may have no JSON body */ }
    if (!response.ok) {
      const detail = payload?.detail;
      throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status}). Please try again.`);
    }
    state.apiState = "ready";
    return payload;
  };
  const setApiStatus = (stateName) => { state.apiState = stateName; };
  const navButton = (view, label, icon) => `<button type="button" class="nav-item" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}">${icon}<span>${label}</span></button>`;
  const mobileNavButton = (view, label, icon) => `<button type="button" data-view="${view}" aria-current="${state.view === view ? "page" : "false"}">${icon}<span>${label}</span></button>`;

  function render() {
    app.innerHTML = state.token ? renderWorkspace() : renderAuth();
    bindEvents();
  }

  function renderAuth() {
    const isRegister = state.mode === "register";
    return `<main class="auth-screen">
      <section class="auth-story" aria-label="About Solvyn">
        <div class="brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
        <div class="story-center">
          <div class="story-kicker">A quieter way through hard problems</div>
          <h1>Make room for<br><em>clear thinking.</em></h1>
          <p>Bring the question that is taking up space. Solvyn gives you a thoughtful place to work through it, one conversation at a time.</p>
          <div class="story-steps" aria-label="The Solvyn conversation">
            <div class="story-step"><span>01 / SHARE</span>Put the problem into words</div>
            <div class="story-step"><span>02 / EXPLORE</span>Work through it together</div>
            <div class="story-step"><span>03 / KEEP</span>Return to your history</div>
          </div>
        </div>
        <div class="auth-foot">A focused problem-solving workspace · Solvyn</div>
      </section>
      <section class="auth-side">
        <div class="auth-card">
          <h2>${isRegister ? "Create your account" : "Welcome back"}</h2>
          <p>${isRegister ? "Start a private workspace for the questions you want to untangle." : "Sign in to pick up where your thinking left off."}</p>
          <div class="auth-mode" role="group" aria-label="Account action">
            <button type="button" data-auth-mode="login" aria-pressed="${!isRegister}">Sign in</button>
            <button type="button" data-auth-mode="register" aria-pressed="${isRegister}">Create account</button>
          </div>
          ${state.authError ? `<p class="error-text" role="alert">${esc(state.authError)}</p>` : ""}
          <form id="auth-form">
            ${isRegister ? `<label class="field"><span>Name <small>(optional)</small></span><input name="name" autocomplete="name" maxlength="80" placeholder="How should Solvyn address you?" /></label>` : ""}
            <label class="field"><span>Email address</span><input name="email" type="email" autocomplete="email" required maxlength="254" placeholder="you@example.com" /></label>
            <label class="field"><span>Password</span><input name="password" type="password" autocomplete="${isRegister ? "new-password" : "current-password"}" required minlength="8" maxlength="128" placeholder="At least 8 characters" /></label>
            <button class="primary-button auth-submit" type="submit" ${state.authBusy ? "disabled" : ""}>${state.authBusy ? "Connecting…" : isRegister ? "Create account" : "Sign in"}</button>
          </form>
          <div class="auth-legal">Your access token stays in this browser tab and is removed when you sign out or close the tab.</div>
          <div class="auth-api"><strong>API connection</strong><br />${esc(API_BASE || "Same origin")}<br />Sign-in requires a reachable Solvyn backend.</div>
        </div>
      </section>
    </main>`;
  }

  function renderWorkspace() {
    const messages = state.messages;
    const apiLabel = state.apiState === "ready" ? "API connected" : state.apiState === "error" ? "API unavailable" : "Checking API";
    return `<div class="app-shell">
      <aside class="sidebar">
        <div class="brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
        <div class="user-card"><span class="avatar" aria-hidden="true">${esc(initials(sessionStorage.getItem("solvyn_user_email") || "You"))}</span><span class="user-copy"><span class="user-name">${esc(sessionStorage.getItem("solvyn_user_email") || "Your account")}</span><span class="user-caption">Personal workspace</span></span></div>
        <div class="nav-label">Workspace</div>
        <nav class="nav-list" aria-label="Workspace navigation">
          ${navButton("workspace", "Problem workspace", icons.home)}
          ${navButton("history", "Conversation history", icons.history)}
          ${navButton("diary", "Diary", icons.diary)}
          <button type="button" class="nav-item" disabled aria-describedby="feature-note">${icons.home}<span>Projects</span><small class="nav-tag">Not available</small></button>
          <button type="button" class="nav-item" disabled aria-describedby="feature-note">${icons.assistant}<span>Tools</span><small class="nav-tag">Not available</small></button>
        </nav>
        <p class="sidebar-note" id="feature-note">Projects and connected tools are not supported by the current API.</p>
        <div class="sidebar-bottom">
          <div class="account-actions"><span>${esc(sessionStorage.getItem("solvyn_user_email") || "Signed in")}</span><button class="plain-button" type="button" data-action="logout">Sign out</button></div>
          <div class="user-caption" style="padding:0 9px">Session ends when this tab closes.</div>
        </div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div class="mobile-brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
          <div class="eyebrow">AI problem-solving assistant</div>
          <div class="topbar-right"><div class="api-pill" data-state="${state.apiState}"><span class="api-dot"></span>${apiLabel}</div></div>
        </header>
        ${state.view === "workspace" ? renderWorkspaceView(messages) : state.view === "history" ? renderHistoryView(messages) : renderDiaryView()}
      </main>
      <nav class="mobile-nav" aria-label="Main navigation">
        ${mobileNavButton("workspace", "Workspace", icons.home)}
        ${mobileNavButton("history", "History", icons.history)}
        ${mobileNavButton("diary", "Diary", icons.diary)}
      </nav>
    </div>`;
  }

  function renderWorkspaceView(messages) {
    const threadContent = state.loadingHistory
      ? `<div class="skeleton" aria-label="Loading conversation history"></div><div class="skeleton"></div><div class="skeleton"></div>`
      : state.historyError
        ? `<div class="empty-state"><div><h3>History could not load</h3><p>${esc(state.historyError)}</p><button class="retry-button" type="button" data-action="retry-history">Try again</button></div></div>`
        : messages.length
          ? `<div class="chat-date">Recent conversation</div>${messages.map(renderMessage).join("")}${state.sending ? `<div class="message"><span class="message-avatar">${icons.assistant}</span><div class="message-content"><div class="message-label">Solvyn</div><div class="typing" role="status"><span></span><span></span><span></span> Working through the problem</div></div></div>` : ""}`
          : `<div class="empty-chat"><div><div class="empty-chat-mark">${icons.assistant}</div><h3>Start with the question</h3><p>Share what you are trying to solve. Solvyn will return a structured solution when the API completes successfully.</p></div></div>`;
    const solution = latestSolution(messages);
    return `<div class="view-heading"><div><h1>Problem workspace</h1><p>A clear space to think through what is on your mind.</p></div></div>
      <div class="workspace-grid">
        <section class="panel chat-panel" aria-label="Conversation with Solvyn">
          <div class="panel-heading"><h2 class="panel-title">Problem conversation</h2><div class="panel-tools"><span class="status-label">Solve API</span></div></div>
          ${state.solveError ? `<div class="notice error" role="alert">${esc(state.solveError)}</div>` : ""}
          <div class="chat-thread" id="chat-thread" aria-live="polite">${threadContent}</div>
          <div class="composer-wrap"><form id="chat-form" class="composer">
            <label class="sr-only" for="prompt-input">Describe the problem you want to work through</label>
            <textarea id="prompt-input" name="content" placeholder="Describe what you’re trying to solve…" rows="1" maxlength="6000" minlength="3" ${state.sending ? "disabled" : ""}></textarea>
            <button class="send-button" type="submit" aria-label="Send message" ${state.sending ? "disabled" : ""}>${icons.send}</button>
          </form><div class="composer-hint"><span>Enter to send · Shift + Enter for a new line</span><span>${state.sending ? "Waiting for API…" : "3–6,000 characters"}</span></div></div>
        </section>
        <div class="middle-column">
          <section class="panel breakdown-panel">
            <div class="panel-heading"><h2 class="panel-title">Latest solution</h2>${solution ? `<span class="status-label">API result</span>` : ""}</div>
            ${solution ? renderSolutionBreakdown(solution) : `<div class="breakdown-body"><div class="solution-placeholder"><div class="empty-chat-mark">${icons.assistant}</div><h3>No solution yet</h3><p>Submit a problem to see the returned analysis, steps, and solution tree here.</p></div></div>`}
          </section>
          <section class="panel detail-panel">
            <div class="panel-heading"><h2 class="panel-title">Code &amp; formula</h2><span class="api-contract-label">POST /ai/solve</span></div>
            ${solution ? renderSolutionOutputs(solution) : `<div class="output-empty">Code and formula outputs will be shown when included in a returned solution.</div>`}
          </section>
        </div>
        <aside class="side-column" aria-label="Workspace status">
          <section class="panel insight-panel">
            <div class="panel-heading"><h2 class="panel-title">Solution metrics</h2></div>
            ${renderSolutionMetrics(solution)}
          </section>
          <section class="panel tools-panel">
            <div class="panel-heading"><h2 class="panel-title">Related tools</h2></div>
            ${solution ? renderRelatedTools(solution) : `<div class="tool-placeholder">Tools returned by a solution will appear here.</div>`}
          </section>
        </aside>
      </div>`;
  }

  function renderSolutionBreakdown(solution) {
    return `<div class="solution-body">
      <div class="solution-intro"><h3>${esc(solution.title)}</h3><p>${esc(solution.summary)}</p></div>
      ${renderAnalysis(solution)}
      ${renderSteps(solution)}
      ${renderTree(solution)}
    </div>`;
  }

  function renderAnalysis(solution) {
    if (!solution.analysis.length) return `<section class="solution-section"><h3>Analysis</h3><p class="optional-missing">No analysis points were returned.</p></section>`;
    return `<section class="solution-section"><h3>Analysis</h3><ul class="analysis-list">${solution.analysis.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></section>`;
  }

  function renderSteps(solution) {
    if (!solution.steps.length) return `<section class="solution-section"><h3>Steps</h3><p class="optional-missing">No solution steps were returned.</p></section>`;
    return `<section class="solution-section"><h3>Steps <span>${solution.steps.length}</span></h3><ol class="solution-steps">${solution.steps.map((step, index) => `<li><span class="step-number">${String(index + 1).padStart(2, "0")}</span><div><strong>${esc(step.title)}</strong><p>${esc(step.description)}</p></div></li>`).join("")}</ol></section>`;
  }

  function renderTree(solution) {
    if (!solution.tree.length) return `<section class="solution-section"><h3>Solution tree</h3><p class="optional-missing">No solution tree was returned.</p></section>`;
    const nodes = solution.tree.slice(0, 300);
    const idIndex = new Map();
    nodes.forEach((node, index) => { if (!idIndex.has(node.id)) idIndex.set(node.id, index); });
    const children = nodes.map(() => []);
    const roots = [];
    nodes.forEach((node, index) => {
      const parentIndex = node.parent_id == null ? undefined : idIndex.get(node.parent_id);
      if (parentIndex === undefined || parentIndex === index) roots.push(index);
      else children[parentIndex].push(index);
    });
    const visited = new Set();
    const renderNode = (index, depth = 0) => {
      if (visited.has(index) || depth > 60) return "";
      visited.add(index);
      const node = nodes[index];
      const childMarkup = children[index].map((child) => renderNode(child, depth + 1)).join("");
      return `<li class="tree-node" style="--depth:${Math.min(depth, 10)}"><div class="tree-node-card"><span class="tree-node-label">${esc(node.label)}</span>${node.description ? `<p>${esc(node.description)}</p>` : ""}</div>${childMarkup ? `<ul>${childMarkup}</ul>` : ""}</li>`;
    };
    let treeMarkup = roots.map((index) => renderNode(index)).join("");
    nodes.forEach((_, index) => { if (!visited.has(index)) treeMarkup += renderNode(index); });
    return `<section class="solution-section"><h3>Solution tree <span>${solution.tree.length}</span></h3><ul class="solution-tree">${treeMarkup}</ul>${solution.tree.length > nodes.length ? `<p class="optional-missing">Showing the first ${nodes.length} of ${solution.tree.length} returned nodes.</p>` : ""}</section>`;
  }

  function renderSolutionOutputs(solution) {
    const codeMarkup = typeof solution.code === "string" && solution.code.length
      ? `<pre><code>${esc(solution.code)}</code></pre>`
      : `<p class="optional-missing">No code was returned for this solution.</p>`;
    const formulaMarkup = typeof solution.formula === "string" && solution.formula.length
      ? `<div class="formula-value">${esc(solution.formula)}</div>`
      : `<p class="optional-missing">No formula was returned for this solution.</p>`;
    return `<div class="solution-outputs">
      <section class="output-card"><div class="output-heading"><h3>Code</h3><span>${solution.code ? esc(solution.code_language || "Language not specified") : "Not provided"}</span></div>${codeMarkup}</section>
      <section class="output-card"><div class="output-heading"><h3>Formula</h3><span>${solution.formula ? "Returned" : "Not provided"}</span></div>${formulaMarkup}</section>
    </div>`;
  }

  function renderSolutionMetrics(solution) {
    if (!solution) return `<div class="insight-body"><p class="metrics-empty">Metrics will appear here after a solution is returned.</p></div>`;
    const elapsed = solution.elapsed_seconds !== null && solution.elapsed_seconds !== undefined && Number.isFinite(Number(solution.elapsed_seconds))
      ? `${Number(solution.elapsed_seconds).toFixed(2)} s`
      : "Not returned";
    const tokens = Number.isFinite(Number(solution.token_usage)) && solution.token_usage !== null
      ? String(solution.token_usage)
      : "Not provided";
    const complexity = solution.complexity.trim() || "Not provided";
    return `<div class="insight-body">
      <div class="insight-row"><div class="insight-top"><span>Complexity</span><span class="insight-value">${esc(complexity)}</span></div><div class="insight-help">As reported by the solve API</div></div>
      <div class="insight-row"><div class="insight-top"><span>Elapsed</span><span class="insight-value">${esc(elapsed)}</span></div><div class="insight-help">Time reported for this solve request</div></div>
      <div class="insight-row"><div class="insight-top"><span>Token usage</span><span class="insight-value">${esc(tokens)}</span></div><div class="insight-help">${tokens === "Not provided" ? "The API did not include token usage." : "As reported by the solve API"}</div></div>
    </div>`;
  }

  function renderRelatedTools(solution) {
    if (!solution.related_tools.length) return `<div class="tool-placeholder">No related tools were returned.</div>`;
    return `<div class="related-tool-list">${solution.related_tools.map((tool) => `<div class="tool-placeholder related-tool">${esc(tool)}</div>`).join("")}</div>`;
  }

  function renderFullSolution(solution) {
    return `<div class="full-solution-details">
      ${renderAnalysis(solution)}
      ${renderSteps(solution)}
      ${renderTree(solution)}
      ${renderSolutionOutputs(solution)}
      <section class="solution-section"><h3>Metrics</h3>${renderSolutionMetrics(solution)}</section>
      <section class="solution-section"><h3>Related tools</h3>${renderRelatedTools(solution)}</section>
    </div>`;
  }

  function renderMessage(message) {
    const isUser = message.sender === "user";
    const body = message.message ?? message.content ?? "";
    const solution = isUser ? null : parseSolutionPayload(body);
    const messageBody = solution
      ? `<div class="solution-message"><div class="solution-message-label">Structured solution</div><h3>${esc(solution.title)}</h3><p>${esc(solution.summary)}</p><details class="solution-transcript"><summary>View full solution details</summary>${renderFullSolution(solution)}</details></div>`
      : `<div class="bubble">${esc(body)}</div>`;
    return `<article class="message ${isUser ? "user" : "assistant"}">
      <span class="message-avatar" aria-hidden="true">${isUser ? esc(initials(sessionStorage.getItem("solvyn_user_email") || "You")) : icons.assistant}</span>
      <div class="message-content"><div class="message-label">${isUser ? "You" : "Solvyn"}</div>${messageBody}<div class="message-time">${esc(formatDate(message.timestamp || message.created_at))}</div></div>
    </article>`;
  }

  function renderHistoryView(messages) {
    let content;
    if (state.loadingHistory) content = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
    else if (state.historyError) content = `<div class="empty-state"><div><h3>History is unavailable</h3><p>${esc(state.historyError)}</p><button class="retry-button" type="button" data-action="retry-history">Try again</button></div></div>`;
    else if (!messages.length) content = `<div class="empty-state"><div><h3>No conversations yet</h3><p>Messages will appear here after they are saved by the Solvyn solve API.</p></div></div>`;
    else content = `<div class="data-list">${messages.slice().reverse().map(renderHistoryMessage).join("")}</div>`;
    return `<div class="view-heading"><div><h1>Conversation history</h1><p>Messages loaded from your account. The backend keeps the most recent 200.</p></div></div>
      ${state.notice ? `<div class="notice success" role="status">${esc(state.notice)}</div>` : ""}
      <section class="panel view-card data-panel"><div class="panel-heading"><h2 class="panel-title">Saved messages</h2><button class="plain-button" type="button" data-action="retry-history">Refresh</button></div>${content}</section>`;
  }

  function renderHistoryMessage(message) {
    const isUser = message.sender === "user";
    const body = message.message ?? message.content ?? "";
    const solution = isUser ? null : parseSolutionPayload(body);
    const content = solution
      ? `<div class="solution-message history-solution"><div class="solution-message-label">Structured solution</div><h3>${esc(solution.title)}</h3><p>${esc(solution.summary)}</p>${renderFullSolution(solution)}</div>`
      : `<p>${esc(body)}</p>`;
    return `<article class="history-record"><div class="history-record-meta"><strong>${isUser ? "You" : "Solvyn"}</strong><time>${esc(formatDate(message.timestamp || message.created_at))}</time></div><div class="data-copy">${content}</div></article>`;
  }

  function renderDiaryView() {
    let content;
    if (state.loadingDiary) content = `<div class="skeleton"></div><div class="skeleton"></div>`;
    else if (state.diaryError) content = `<div class="empty-state"><div><h3>Diary could not load</h3><p>${esc(state.diaryError)}</p><button class="retry-button" type="button" data-action="retry-diary">Try again</button></div></div>`;
    else if (!state.diary.length) content = `<div class="empty-state"><div><h3>A place to keep a thought</h3><p>Your diary is empty. Add a note here; it will be saved to your account using the diary API.</p></div></div>`;
    else content = `<div class="data-list">${state.diary.map((entry) => `<article class="data-row"><div class="data-copy"><p>${esc(entry.content)}</p><time>${esc(formatDate(entry.created_at))}</time></div></article>`).join("")}</div>`;
    return `<div class="view-heading"><div><h1>Diary</h1><p>A personal record of the things you want to remember.</p></div></div>
      ${state.notice ? `<div class="notice success" role="status">${esc(state.notice)}</div>` : ""}
      <section class="panel view-card data-panel">
        <div class="panel-heading"><h2 class="panel-title">Your entries</h2><button class="plain-button" type="button" data-action="retry-diary">Refresh</button></div>
        <form id="diary-form" class="entry-form"><label class="sr-only" for="diary-content">Write a diary entry</label><textarea id="diary-content" name="content" maxlength="6000" required placeholder="Write a thought you’d like to keep…"></textarea><div class="entry-form-bottom"><small>Saved to your account when submitted.</small><button class="primary-button" type="submit" ${state.diaryBusy ? "disabled" : ""}>${state.diaryBusy ? "Saving…" : "Save entry"}</button></div></form>
        ${content}
      </section>`;
  }

  async function loadHistory() {
    if (!state.token) return;
    state.loadingHistory = true;
    state.historyError = "";
    render();
    try {
      const history = await request("/ai/chat/history");
      state.messages = Array.isArray(history) ? history : [];
      setApiStatus("ready");
    } catch (error) {
      state.historyError = error.message;
    } finally {
      state.loadingHistory = false;
      render();
    }
  }

  async function loadDiary() {
    if (!state.token) return;
    state.loadingDiary = true;
    state.diaryError = "";
    render();
    try {
      const entries = await request("/diary");
      state.diary = Array.isArray(entries) ? entries : [];
    } catch (error) {
      state.diaryError = error.message;
    } finally {
      state.loadingDiary = false;
      render();
    }
  }

  async function submitAuth(form) {
    const formData = new FormData(form);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const name = String(formData.get("name") || "").trim();
    if (state.mode === "register" && password.length < 8) {
      state.authError = "Choose a password with at least 8 characters.";
      render();
      return;
    }
    state.authBusy = true;
    state.authError = "";
    render();
    try {
      if (state.mode === "register") {
        await request("/auth/signup", { method: "POST", body: JSON.stringify({ email, password, ...(name ? { name } : {}) }) });
      }
      const result = await request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      if (!result?.access_token) throw new Error("The API did not return an access token. Please try again.");
      state.token = result.access_token;
      sessionStorage.setItem("solvyn_access_token", result.access_token);
      sessionStorage.setItem("solvyn_user_email", email);
      state.authBusy = false;
      state.view = "workspace";
      render();
      await Promise.all([loadHistory(), loadDiary()]);
    } catch (error) {
      state.authBusy = false;
      state.authError = error.message;
      render();
    }
  }

  async function sendMessage(form) {
    const textarea = form.elements.content;
    const content = textarea.value.trim();
    if (content.length < 3 || state.sending) return;
    state.sending = true;
    state.historyError = "";
    state.solveError = "";
    const optimisticMessage = { sender: "user", message: content, timestamp: new Date().toISOString(), localOnly: true };
    state.messages.push(optimisticMessage);
    render();
    scrollChatToBottom();
    form = document.querySelector("#chat-form");
    const currentTextarea = form?.elements.content;
    if (currentTextarea) currentTextarea.value = "";
    try {
      const result = await request("/ai/solve", { method: "POST", body: JSON.stringify({ content }) });
      if (!isSolutionPayload(result)) {
        throw new Error("The solve service returned an incomplete solution. No structured result was displayed.");
      }
      optimisticMessage.localOnly = false;
      state.messages.push({ sender: "ai", message: JSON.stringify(result), timestamp: new Date().toISOString() });
      state.notice = "";
      render();
      scrollChatToBottom();
    } catch (error) {
      state.solveError = `${error.message} This prompt remains visible in this view; refresh history before retrying in case the request was saved.`;
      render();
      scrollChatToBottom();
    } finally {
      state.sending = false;
      render();
      scrollChatToBottom();
    }
  }

  async function saveDiary(form) {
    const textarea = form.elements.content;
    const content = textarea.value.trim();
    if (!content || state.diaryBusy) return;
    state.diaryBusy = true;
    state.diaryError = "";
    render();
    try {
      const entry = await request("/diary", { method: "POST", body: JSON.stringify({ content }) });
      if (!entry || typeof entry.content !== "string") throw new Error("The API did not confirm that the diary entry was saved.");
      state.diary.unshift(entry);
      state.notice = "Diary entry saved.";
      state.diaryBusy = false;
      render();
    } catch (error) {
      state.diaryBusy = false;
      state.diaryError = error.message;
      render();
    }
  }

  function scrollChatToBottom() {
    const thread = document.querySelector("#chat-thread");
    if (thread) thread.scrollTop = thread.scrollHeight;
  }

  function logout() {
    sessionStorage.removeItem("solvyn_access_token");
    sessionStorage.removeItem("solvyn_user_email");
    state.token = null;
    state.messages = [];
    state.diary = [];
    state.view = "workspace";
    state.historyError = "";
    state.diaryError = "";
    state.notice = "";
    render();
  }

  function bindEvents() {
    app.querySelectorAll("[data-auth-mode]").forEach((button) => button.addEventListener("click", () => {
      state.mode = button.dataset.authMode;
      state.authError = "";
      render();
    }));
    app.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
      state.view = button.dataset.view;
      state.notice = "";
      render();
      if (state.view === "history") loadHistory();
      if (state.view === "diary" && !state.loadingDiary && !state.diary.length && !state.diaryError) loadDiary();
    }));
    app.querySelectorAll("[data-action='logout']").forEach((button) => button.addEventListener("click", logout));
    app.querySelectorAll("[data-action='retry-history']").forEach((button) => button.addEventListener("click", loadHistory));
    app.querySelectorAll("[data-action='retry-diary']").forEach((button) => button.addEventListener("click", loadDiary));
    const authForm = app.querySelector("#auth-form");
    if (authForm) authForm.addEventListener("submit", (event) => { event.preventDefault(); submitAuth(authForm); });
    const chatForm = app.querySelector("#chat-form");
    if (chatForm) {
      chatForm.addEventListener("submit", (event) => { event.preventDefault(); sendMessage(chatForm); });
      chatForm.elements.content.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
          event.preventDefault();
          chatForm.requestSubmit();
        }
      });
      chatForm.elements.content.addEventListener("input", () => {
        chatForm.elements.content.style.height = "auto";
        chatForm.elements.content.style.height = `${Math.min(chatForm.elements.content.scrollHeight, 120)}px`;
      });
    }
    const diaryForm = app.querySelector("#diary-form");
    if (diaryForm) diaryForm.addEventListener("submit", (event) => { event.preventDefault(); saveDiary(diaryForm); });
  }

  function checkApi() {
    request("/health").then(() => {
      state.apiState = "ready";
      render();
    }).catch(() => {
      state.apiState = "error";
      render();
    });
  }

  render();
  checkApi();
  if (state.token) {
    loadHistory();
    loadDiary();
  }
})();
