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
    diaryHasMore: false,
    loadingMoreDiary: false,
    diaryDrafts: {},
    diarySearch: "",
    diaryMoodFilter: "",
    diaryDateFrom: "",
    diaryDateTo: "",
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
    chatError: "",
    diaryEditingId: null,
    aiConfigured: false,
    googleClientId: null,
    googleNonce: null,
    reflectionEntryId: null,
    reflectionSummary: "",
    reflectionLoading: false,
  };
  const moods = ["happy", "sad", "stressed", "angry", "excited", "confused", "neutral"];

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
      sessionStorage.removeItem("solvyn_user_email");
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
    mountGoogleButton();
  }

  function renderAuth() {
    const isRegister = state.mode === "register";
    return `<main class="auth-screen">
      <section class="auth-story" aria-label="About Solvyn">
        <div class="brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
        <div class="story-center">
          <div class="story-kicker">A private space to reflect</div>
          <h1>Make room for<br><em>your own thoughts.</em></h1>
          <p>Keep the moments you want to remember, notice how you feel, and talk things through with a companion who listens.</p>
          <div class="story-steps" aria-label="The Solvyn conversation">
            <div class="story-step"><span>01 / WRITE</span>Give a thought somewhere to land</div>
            <div class="story-step"><span>02 / REFLECT</span>Explore it at your own pace</div>
            <div class="story-step"><span>03 / RETURN</span>Revisit what matters to you</div>
          </div>
        </div>
        <div class="auth-foot">Your private diary and reflection companion · Solvyn</div>
      </section>
      <section class="auth-side">
        <div class="auth-card">
          <h2>${isRegister ? "Create your account" : "Welcome back"}</h2>
          <p>${isRegister ? "Start a private diary and reflection space of your own." : "Sign in to return to your diary and conversations."}</p>
          <div class="auth-mode" role="group" aria-label="Account action">
            <button type="button" data-auth-mode="login" aria-pressed="${!isRegister}">Sign in</button>
            <button type="button" data-auth-mode="register" aria-pressed="${isRegister}">Create account</button>
          </div>
          ${state.googleClientId ? `<div class="google-signin-wrap"><div class="auth-divider"><span>or continue with</span></div><div id="google-signin-button"></div></div>` : ""}
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
    const apiLabel = state.apiState === "ready" ? "API connected" : state.apiState === "error" ? "API unavailable" : "Checking API";
    const page = state.view === "chat"
      ? renderChatView()
      : state.view === "diary"
        ? renderDiaryView()
        : renderHomeView();
    return `<div class="app-shell">
      <aside class="sidebar">
        <div class="brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
        <div class="user-card"><span class="avatar" aria-hidden="true">${esc(initials(sessionStorage.getItem("solvyn_user_email") || "You"))}</span><span class="user-copy"><span class="user-name">${esc(sessionStorage.getItem("solvyn_user_email") || "Your account")}</span><span class="user-caption">Personal workspace</span></span></div>
        <div class="nav-label">Your space</div>
        <nav class="nav-list" aria-label="Workspace navigation">
          ${navButton("workspace", "Today", icons.home)}
          ${navButton("chat", "Companion", icons.assistant)}
          ${navButton("diary", "Diary", icons.diary)}
        </nav>
        <div class="sidebar-bottom">
          <div class="account-actions"><span>${esc(sessionStorage.getItem("solvyn_user_email") || "Signed in")}</span><button class="plain-button" type="button" data-action="logout">Sign out</button></div>
          <div class="user-caption" style="padding:0 9px">Session ends when this tab closes.</div>
        </div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div class="mobile-brand"><span class="brand-mark">${icons.mark}</span>Solvyn</div>
          <div class="eyebrow">Your personal reflection space</div>
          <div class="topbar-right"><div class="api-pill" data-state="${state.apiState}"><span class="api-dot"></span>${apiLabel}</div></div>
        </header>
        ${page}
      </main>
      <nav class="mobile-nav" aria-label="Main navigation">
        ${mobileNavButton("workspace", "Today", icons.home)}
        ${mobileNavButton("chat", "Companion", icons.assistant)}
        ${mobileNavButton("diary", "Diary", icons.diary)}
      </nav>
    </div>`;
  }

  function renderHomeView() {
    const date = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date());
    const recent = state.diary.slice(0, 3);
    const recentContent = state.loadingDiary
      ? `<div class="skeleton"></div><div class="skeleton"></div>`
      : state.diaryError
        ? `<p class="muted-copy">${esc(state.diaryError)}</p>`
        : recent.length
          ? `<div class="data-list">${recent.map((entry) => `<article class="data-row"><div class="data-copy">${entry.title ? `<h3 class="diary-entry-title">${esc(entry.title)}</h3>` : ""}<p>${esc(entry.content)}</p><time>${esc(formatDate(entry.created_at))}</time>${entry.mood ? `<span class="mood-chip">${esc(entry.mood)}</span>` : ""}${entry.entry_type === "chat_summary" ? `<span class="source-chip">AI reflection from chat</span>` : ""}</div></article>`).join("")}</div>`
          : `<div class="empty-state"><div><h3>Your diary starts here</h3><p>Save a small moment, a feeling, or anything you want to remember.</p><button class="plain-button" type="button" data-view="diary">Open your diary</button></div></div>`;
    return `<div class="view-heading home-heading"><div><div class="story-kicker">${esc(date)}</div><h1>A little space for you</h1><p>Write what’s on your mind. Nothing needs to be polished or solved.</p></div></div>
      ${state.notice ? `<div class="notice success" role="status">${esc(state.notice)}</div>` : ""}
      ${state.diaryError && !state.loadingDiary ? `<div class="notice error" role="alert">${esc(state.diaryError)}</div>` : ""}
      <div class="home-grid">
        <section class="panel journal-compose">
          <div class="panel-heading"><h2 class="panel-title">A thought for today</h2><span class="status-label">Private to your account</span></div>
          <form id="diary-form" class="entry-form" data-entry-id="new">${renderDiaryFields(state.diaryDrafts.new || {}, "diary", "new")}<div class="entry-form-bottom"><small>${state.diary.length ? `${state.diary.length} saved ${state.diary.length === 1 ? "entry" : "entries"}` : "Your first entry can be just a few words."}</small><button class="primary-button" type="submit" ${state.diaryBusy ? "disabled" : ""}>${state.diaryBusy ? "Saving…" : "Save to diary"}</button></div></form>
        </section>
        <section class="panel recent-panel">
          <div class="panel-heading"><h2 class="panel-title">Recently written</h2><button class="plain-button" type="button" data-view="diary">View diary</button></div>
          ${recentContent}
        </section>
      </div>
      <section class="companion-invite"><div><span class="story-kicker">When you want to talk</span><h2>Make sense of it together.</h2><p>Share what’s on your mind and take the conversation one step at a time.</p></div><button class="primary-button" type="button" data-view="chat">Talk with Solvyn</button></section>`;
  }

  function renderChatView() {
    const chatContent = state.loadingHistory
      ? `<div class="skeleton" aria-label="Loading conversation"></div><div class="skeleton"></div>`
      : state.historyError
        ? `<div class="empty-state"><div><h3>Conversation could not load</h3><p>${esc(state.historyError)}</p><button class="retry-button" type="button" data-action="retry-history">Try again</button></div></div>`
        : state.messages.length
          ? state.messages.map(renderMessage).join("")
          : `<div class="empty-chat"><div><div class="empty-chat-mark">${icons.assistant}</div><h3>Start wherever you are</h3><p>Tell Solvyn what has been on your mind. You can take the conversation at your own pace.</p></div></div>`;
    return `<div class="view-heading"><div><div class="story-kicker">A thoughtful conversation</div><h1>Your companion</h1><p>Share what’s on your mind. Your conversation is saved to your account.</p></div></div>
      ${state.chatError ? `<div class="notice error" role="alert">${esc(state.chatError)}</div>` : ""}
      ${!state.aiConfigured && state.apiState === "ready" ? `<div class="notice" role="status">AI chat is unavailable until a Gemini API key is added to the app’s secrets. Your diary remains available.</div>` : ""}
      <section class="panel chat-panel chat-page" aria-label="Conversation with Solvyn">
        <div class="panel-heading"><h2 class="panel-title">A private conversation</h2><span class="status-label">${state.aiConfigured ? "Ready when you are" : "AI not configured"}</span></div>
        <div class="chat-thread" id="chat-thread" aria-live="polite">${chatContent}${state.sending ? `<div class="message"><span class="message-avatar">${icons.assistant}</span><div class="message-content"><div class="message-label">Solvyn</div><div class="typing" role="status"><span></span><span></span><span></span> Thinking…</div></div></div>` : ""}</div>
        <div class="composer-wrap"><form id="chat-form" class="composer">
          <label class="sr-only" for="prompt-input">Message Solvyn</label>
          <textarea id="prompt-input" name="content" placeholder="Write what’s on your mind…" rows="1" maxlength="8000" ${state.sending ? "disabled" : ""}></textarea>
          <button class="send-button" type="submit" aria-label="Send message" ${state.sending || !state.aiConfigured ? "disabled" : ""}>${icons.send}</button>
        </form><div class="composer-hint"><span>Enter to send · Shift + Enter for a new line</span><span>Up to 8,000 characters</span></div></div>
      </section>`;
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
    else if (state.diaryError && !state.diary.length) content = `<div class="empty-state"><div><h3>Diary could not load</h3><p>${esc(state.diaryError)}</p><button class="retry-button" type="button" data-action="retry-diary">Try again</button></div></div>`;
    else if (!state.diary.length) content = `<div class="empty-state"><div><h3>Your diary is ready when you are</h3><p>Write down a moment, a feeling, or anything you would like to revisit later.</p></div></div>`;
    else content = `<div class="data-list diary-list">${state.diary.map((entry) => {
      const editing = state.diaryEditingId === entry.id;
      const draft = state.diaryDrafts[String(entry.id)] || entry;
      const entryDate = typeof entry.created_at === "string" ? entry.created_at.slice(0, 10) : "";
      return `<article class="data-row diary-entry" data-title="${esc(entry.title || "")}" data-content="${esc(entry.content)}" data-mood="${esc(entry.mood || "")}" data-created="${esc(entryDate)}">
        <div class="data-copy">
          ${entry.title ? `<h3 class="diary-entry-title">${esc(entry.title)}</h3>` : ""}
          <time>${esc(formatDate(entry.created_at))}</time>
          ${editing
            ? `<form class="entry-form diary-edit-form" data-entry-id="${Number(entry.id)}">${renderDiaryFields(draft, `edit-entry-${Number(entry.id)}`, String(entry.id))}<div class="entry-form-bottom"><small>Changes are saved to your account.</small><div class="entry-actions"><button class="plain-button" type="button" data-action="cancel-edit">Cancel</button><button class="primary-button" type="submit" ${state.diaryBusy ? "disabled" : ""}>${state.diaryBusy ? "Saving…" : "Save changes"}</button></div></div></form>`
            : `<p>${esc(entry.content)}</p>${entry.mood ? `<span class="mood-chip">${esc(entry.mood)}</span>` : ""}${entry.entry_type === "chat_summary" ? `<span class="source-chip">AI reflection from chat</span>` : ""}`}
        </div>
        ${!editing ? `<div class="entry-actions">${state.aiConfigured ? `<button class="plain-button" type="button" data-action="summary-entry" data-entry-id="${Number(entry.id)}" ${state.reflectionLoading && state.reflectionEntryId === entry.id ? "disabled" : ""}>${state.reflectionLoading && state.reflectionEntryId === entry.id ? "Reflecting…" : "Reflect"}</button>` : ""}<button class="plain-button" type="button" data-action="edit-entry" data-entry-id="${Number(entry.id)}">Edit</button><button class="plain-button danger-button" type="button" data-action="delete-entry" data-entry-id="${Number(entry.id)}" ${state.diaryBusy ? "disabled" : ""}>Delete</button></div>` : ""}
      </article>`;
    }).join("")}</div>`;
    return `<div class="view-heading"><div><div class="story-kicker">Your personal record</div><h1>Diary</h1><p>Keep the thoughts and moments you want to return to.</p></div></div>
      ${state.notice ? `<div class="notice success" role="status">${esc(state.notice)}</div>` : ""}
      ${state.reflectionEntryId !== null ? `<div class="notice" role="status"><strong>Optional reflection</strong><p>${state.reflectionLoading ? "Preparing a reflection…" : esc(state.reflectionSummary)}</p><button class="plain-button" type="button" data-action="dismiss-reflection">Dismiss</button></div>` : ""}
      ${state.diaryError && !state.loadingDiary ? `<div class="notice error" role="alert">${esc(state.diaryError)}</div>` : ""}
      <section class="panel view-card data-panel">
        <div class="panel-heading"><h2 class="panel-title">Your entries <span class="entry-count">${state.diary.length}</span></h2><button class="plain-button" type="button" data-action="retry-diary">Refresh</button></div>
        <form id="diary-form" class="entry-form" data-entry-id="new">${renderDiaryFields(state.diaryDrafts.new || {}, "diary", "new")}<div class="entry-form-bottom"><small>Saved privately to your account.</small><button class="primary-button" type="submit" ${state.diaryBusy ? "disabled" : ""}>${state.diaryBusy ? "Saving…" : "Save entry"}</button></div></form>
        <div class="diary-filters" role="search" aria-label="Filter diary entries">
          <label><span>Search</span><input id="diary-search" type="search" maxlength="160" value="${esc(state.diarySearch)}" placeholder="Search title or text" /></label>
          <label><span>Mood</span><select id="diary-mood-filter"><option value="">All moods</option>${moods.map((mood) => `<option value="${mood}" ${state.diaryMoodFilter === mood ? "selected" : ""}>${mood}</option>`).join("")}</select></label>
          <label><span>From</span><input id="diary-date-from" type="date" value="${esc(state.diaryDateFrom)}" /></label>
          <label><span>To</span><input id="diary-date-to" type="date" value="${esc(state.diaryDateTo)}" /></label>
        </div>
        <p class="diary-filter-status" role="status" aria-live="polite"></p>
        ${content}
        ${state.diaryHasMore ? `<div class="load-more-wrap"><button class="plain-button" type="button" data-action="load-more" ${state.loadingMoreDiary ? "disabled" : ""}>${state.loadingMoreDiary ? "Loading…" : "Load older entries"}</button></div>` : ""}
      </section>`;
  }

  function renderDiaryFields(draft, prefix, entryId) {
    const selectedMood = draft.mood || "";
    return `<label class="field"><span>Title <small>(optional)</small></span><input id="${prefix}-title" name="title" maxlength="160" value="${esc(draft.title || "")}" placeholder="Give this entry a title" /></label>
      <label class="sr-only" for="${prefix}-content">Write a diary entry</label><textarea id="${prefix}-content" name="content" maxlength="6000" required placeholder="Write a thought you’d like to keep…">${esc(draft.content || "")}</textarea>
      <div class="diary-mood-row"><label class="field"><span>Mood <small>(optional)</small></span><select name="mood"><option value="">No mood selected</option>${moods.map((mood) => `<option value="${mood}" ${selectedMood === mood ? "selected" : ""}>${mood[0].toUpperCase()}${mood.slice(1)}</option>`).join("")}</select></label><button class="plain-button" type="button" data-action="suggest-mood" data-entry-id="${esc(entryId)}" ${!state.aiConfigured ? "disabled" : ""}>Suggest mood</button></div>`;
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

  async function loadDiary(append = false) {
    if (!state.token) return;
    if (append) state.loadingMoreDiary = true;
    else state.loadingDiary = true;
    state.diaryError = "";
    render();
    try {
      const offset = append ? state.diary.length : 0;
      const entries = await request(`/diary?limit=200&offset=${offset}`);
      const page = Array.isArray(entries) ? entries : [];
      state.diary = append ? [...state.diary, ...page] : page;
      state.diaryHasMore = page.length === 200;
    } catch (error) {
      state.diaryError = error.message;
    } finally {
      state.loadingDiary = false;
      state.loadingMoreDiary = false;
      render();
    }
  }

  async function completeSignIn(result, email) {
    if (!result?.access_token) throw new Error("The API did not return an access token.");
    state.token = result.access_token;
    sessionStorage.setItem("solvyn_access_token", result.access_token);
    if (email) sessionStorage.setItem("solvyn_user_email", email);
    state.authBusy = false;
    state.view = "workspace";
    state.authError = "";
    render();
    await Promise.all([loadHistory(), loadDiary()]);
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
      await completeSignIn(result, email.toLowerCase());
    } catch (error) {
      state.authBusy = false;
      state.authError = error.message;
      render();
    }
  }

  async function sendMessage(form) {
    const textarea = form.elements.content;
    const content = textarea.value.trim();
    if (!state.aiConfigured) {
      state.chatError = "AI chat is not configured. Add GEMINI_API_KEY in Replit Secrets to enable it.";
      render();
      return;
    }
    if (content.length < 1 || state.sending) return;
    state.sending = true;
    state.historyError = "";
    state.chatError = "";
    const optimisticMessage = { sender: "user", message: content, timestamp: new Date().toISOString(), localOnly: true };
    state.messages.push(optimisticMessage);
    render();
    scrollChatToBottom();
    form = document.querySelector("#chat-form");
    const currentTextarea = form?.elements.content;
    if (currentTextarea) currentTextarea.value = "";
    try {
      const result = await request("/ai/chat", { method: "POST", body: JSON.stringify({ content }) });
      if (!result || typeof result.reply !== "string" || !result.reply.trim()) {
        throw new Error("Solvyn did not return a reply. Please try again.");
      }
      optimisticMessage.localOnly = false;
      state.messages.push({ sender: "ai", message: result.reply, timestamp: new Date().toISOString() });
      state.notice = "";
      render();
      scrollChatToBottom();
    } catch (error) {
      state.chatError = `${error.message} Your message may have been saved; refresh the conversation to check.`;
      try {
        const history = await request("/ai/chat/history");
        state.messages = Array.isArray(history) ? history : state.messages;
        state.chatError = error.message;
      } catch {
        // Keep the local message visible when the API cannot confirm persistence.
      }
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
    const entryId = form.dataset.entryId ? Number(form.dataset.entryId) : null;
    const draftKey = entryId ? String(entryId) : "new";
    const title = String(form.elements.title?.value || "").trim();
    const mood = String(form.elements.mood?.value || "") || null;
    state.diaryDrafts[draftKey] = { title, content: textarea.value, mood };
    state.diaryBusy = true;
    state.diaryError = "";
    render();
    try {
      const entry = entryId
        ? await request(`/diary/${entryId}`, { method: "PATCH", body: JSON.stringify({ title, content, mood }) })
        : await request("/diary", { method: "POST", body: JSON.stringify({ title, content, mood }) });
      if (!entry || typeof entry.content !== "string") throw new Error("The API did not confirm that the diary entry was saved.");
      if (entryId) {
        state.diary = state.diary.map((saved) => saved.id === entryId ? entry : saved);
        state.diaryEditingId = null;
        state.notice = "Changes saved.";
      } else {
        state.diary.unshift(entry);
        state.notice = "Diary entry saved.";
      }
      delete state.diaryDrafts[draftKey];
      state.diaryBusy = false;
      render();
    } catch (error) {
      state.diaryBusy = false;
      state.diaryError = error.message;
      render();
    }
  }

  function applyDiaryFilters() {
    const search = app.querySelector("#diary-search");
    const mood = app.querySelector("#diary-mood-filter");
    const from = app.querySelector("#diary-date-from");
    const to = app.querySelector("#diary-date-to");
    if (search) state.diarySearch = search.value.trim();
    if (mood) state.diaryMoodFilter = mood.value;
    if (from) state.diaryDateFrom = from.value;
    if (to) state.diaryDateTo = to.value;
    const query = state.diarySearch.toLocaleLowerCase();
    let visible = 0;
    const entries = app.querySelectorAll(".diary-entry");
    entries.forEach((element) => {
      const text = `${element.dataset.title || ""} ${element.dataset.content || ""}`.toLocaleLowerCase();
      const moodMatches = !state.diaryMoodFilter || element.dataset.mood === state.diaryMoodFilter;
      const created = element.dataset.created ? element.dataset.created.slice(0, 10) : "";
      const dateMatches = (!state.diaryDateFrom || created >= state.diaryDateFrom) &&
        (!state.diaryDateTo || created <= state.diaryDateTo);
      const matches = (!query || text.includes(query)) && moodMatches && dateMatches;
      element.style.display = matches ? "" : "none";
      if (matches) visible += 1;
    });
    const status = app.querySelector(".diary-filter-status");
    if (status && entries.length) {
      status.textContent = visible ? `Showing ${visible} of ${entries.length} loaded entries.` : "No entries match these filters.";
    } else if (status) {
      status.textContent = "";
    }
  }

  async function suggestMood(form, entryId) {
    const content = String(form.elements.content?.value || "").trim();
    if (!content) {
      state.diaryError = "Write the entry before asking for a mood suggestion.";
      render();
      return;
    }
    state.diaryDrafts[entryId] = {
      title: String(form.elements.title?.value || ""),
      content: String(form.elements.content?.value || ""),
      mood: String(form.elements.mood?.value || ""),
    };
    state.diaryError = "";
    try {
      const result = await request("/ai/mood", {
        method: "POST",
        body: JSON.stringify({ text: content }),
      });
      if (!moods.includes(result?.mood)) throw new Error("Solvyn did not return a valid mood.");
      state.diaryDrafts[entryId].mood = result.mood;
      state.notice = `Mood suggestion: ${result.mood}. You can change it before saving.`;
      render();
    } catch (error) {
      state.diaryError = error.message;
      render();
    }
  }

  async function summarizeEntry(entryId) {
    state.reflectionEntryId = entryId;
    state.reflectionSummary = "";
    state.reflectionLoading = true;
    render();
    try {
      const result = await request(`/diary/${entryId}/summary`, { method: "POST" });
      state.reflectionSummary = result?.summary || "No reflection was returned.";
    } catch (error) {
      state.reflectionSummary = error.message;
    } finally {
      state.reflectionLoading = false;
      render();
    }
  }

  async function deleteDiaryEntry(entryId) {
    if (!window.confirm("Permanently delete this diary entry? This cannot be undone.")) return;
    state.diaryBusy = true;
    state.diaryError = "";
    render();
    try {
      await request(`/diary/${entryId}`, { method: "DELETE" });
      state.diary = state.diary.filter((entry) => entry.id !== entryId);
      state.notice = "Diary entry deleted.";
    } catch (error) {
      state.diaryError = error.message;
    } finally {
      state.diaryBusy = false;
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
    state.chatError = "";
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
      if (state.view === "chat") loadHistory();
      if (state.view === "diary" && !state.loadingDiary && !state.diary.length && !state.diaryError) loadDiary();
    }));
    app.querySelectorAll("[data-action='logout']").forEach((button) => button.addEventListener("click", logout));
    app.querySelectorAll("[data-action='retry-history']").forEach((button) => button.addEventListener("click", loadHistory));
    app.querySelectorAll("[data-action='retry-diary']").forEach((button) => button.addEventListener("click", loadDiary));
    app.querySelectorAll("[data-action='edit-entry']").forEach((button) => button.addEventListener("click", () => {
      state.diaryEditingId = Number(button.dataset.entryId);
      state.notice = "";
      render();
      document.querySelector(`#edit-entry-${state.diaryEditingId}`)?.focus();
    }));
    app.querySelectorAll("[data-action='cancel-edit']").forEach((button) => button.addEventListener("click", () => {
      delete state.diaryDrafts[String(state.diaryEditingId)];
      state.diaryEditingId = null;
      render();
    }));
    app.querySelectorAll("[data-action='delete-entry']").forEach((button) => button.addEventListener("click", () => {
      deleteDiaryEntry(Number(button.dataset.entryId));
    }));
    app.querySelectorAll("[data-action='summary-entry']").forEach((button) => button.addEventListener("click", () => {
      summarizeEntry(Number(button.dataset.entryId));
    }));
    app.querySelectorAll("[data-action='dismiss-reflection']").forEach((button) => button.addEventListener("click", () => {
      state.reflectionEntryId = null;
      state.reflectionSummary = "";
      render();
    }));
    app.querySelectorAll("[data-action='suggest-mood']").forEach((button) => button.addEventListener("click", () => {
      const form = button.closest("form");
      if (form) suggestMood(form, button.dataset.entryId || "new");
    }));
    app.querySelectorAll("[data-action='load-more']").forEach((button) => button.addEventListener("click", () => loadDiary(true)));
    const filterSearch = app.querySelector("#diary-search");
    const filterMood = app.querySelector("#diary-mood-filter");
    const filterFrom = app.querySelector("#diary-date-from");
    const filterTo = app.querySelector("#diary-date-to");
    [filterSearch, filterMood, filterFrom, filterTo].forEach((element) => {
      element?.addEventListener("input", applyDiaryFilters);
      element?.addEventListener("change", applyDiaryFilters);
    });
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
    app.querySelectorAll("#diary-form, .diary-edit-form").forEach((form) => {
      form.addEventListener("input", () => {
        const key = form.dataset.entryId || "new";
        state.diaryDrafts[key] = {
          title: String(form.elements.title?.value || ""),
          content: String(form.elements.content?.value || ""),
          mood: String(form.elements.mood?.value || ""),
        };
      });
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        saveDiary(form);
      });
    });
    if (app.querySelector("#diary-search")) applyDiaryFilters();
  }

  function newGoogleNonce() {
    if (!window.crypto?.getRandomValues) return null;
    const bytes = new Uint8Array(24);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  let googleScriptPromise;
  function ensureGoogleScript() {
    if (window.google?.accounts?.id) return Promise.resolve();
    if (!googleScriptPromise) {
      googleScriptPromise = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = resolve;
        script.onerror = () => reject(new Error("Google sign-in could not be loaded."));
        document.head.appendChild(script);
      });
    }
    return googleScriptPromise;
  }

  function mountGoogleButton() {
    const target = app.querySelector("#google-signin-button");
    if (!target || !state.googleClientId || !window.google?.accounts?.id) return;
    state.googleNonce ||= newGoogleNonce();
    window.google.accounts.id.initialize({
      client_id: state.googleClientId,
      ...(state.googleNonce ? { nonce: state.googleNonce } : {}),
      callback: async (credentialResponse) => {
        state.authBusy = true;
        state.authError = "";
        const nonce = state.googleNonce;
        render();
        try {
          const result = await request("/auth/google", {
            method: "POST",
            body: JSON.stringify({ id_token: credentialResponse.credential, ...(nonce ? { nonce } : {}) }),
          });
          state.googleNonce = newGoogleNonce();
          await completeSignIn(result, result.email || "Google account");
        } catch (error) {
          state.authBusy = false;
          state.googleNonce = newGoogleNonce();
          state.authError = error.message;
          render();
        }
      },
    });
    window.google.accounts.id.renderButton(target, {
      type: "standard",
      theme: "filled_black",
      size: "large",
      shape: "pill",
      text: "continue_with",
      width: Math.min(320, Math.max(220, target.clientWidth || 280)),
    });
  }

  async function loadGoogleConfig() {
    try {
      const config = await request("/auth/google/config");
      if (typeof config?.client_id !== "string" || !config.client_id) return;
      state.googleClientId = config.client_id;
      await ensureGoogleScript();
      render();
    } catch {
      // Password sign-in remains available when Google is not configured or reachable.
    }
  }

  function checkApi() {
    request("/health").then((health) => {
      state.apiState = "ready";
      state.aiConfigured = Boolean(health?.ai_configured);
      render();
    }).catch(() => {
      state.apiState = "error";
      render();
    });
  }

  render();
  checkApi();
  loadGoogleConfig();
  if (state.token) {
    loadHistory();
    loadDiary();
  }
})();
