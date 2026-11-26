const SESSION_KEY = "crokuta.session";

const authView = document.querySelector("#auth-view");
const workspaceView = document.querySelector("#workspace-view");
const authForm = document.querySelector("#auth-form");
const authMessage = document.querySelector("#auth-message");
const authSetup = document.querySelector("#auth-setup");
const signupFields = document.querySelector("#signup-fields");
const authTitle = document.querySelector("#auth-title");
const authSubtitle = document.querySelector("#auth-subtitle");
const authSubmit = document.querySelector("#auth-submit");
const authSubmitLabel = document.querySelector("#auth-submit-label");
const loginTab = document.querySelector("#login-tab");
const signupTab = document.querySelector("#signup-tab");
const confirmWrap = document.querySelector("#confirm-wrap");
const confirmPassword = document.querySelector("#confirm-password");
const historyError = document.querySelector("#history-error");
const researchForm = document.querySelector("#research-form");
const researchTopic = document.querySelector("#research-topic");
const researchSubmit = document.querySelector("#research-submit");
const researchSubmitLabel = document.querySelector("#research-submit-label");
const researchError = document.querySelector("#research-error");
const report = document.querySelector("#report");
const reportEmpty = document.querySelector("#report-empty");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatSubmit = document.querySelector("#chat-submit");
const chatEmpty = document.querySelector("#chat-empty");
const chatMessages = document.querySelector("#chat-messages");
const chatError = document.querySelector("#chat-error");

let authMode = "login";
let session = readSession();
let currentReport = null;
let currentConversationId = null;
let conversation = [];

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

function saveSession(value) {
  session = value;
  if (value) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(value));
  } else {
    localStorage.removeItem(SESSION_KEY);
  }
}

function showNotice(element, message, kind = "notice-error") {
  element.textContent = message;
  element.className = `notice ${kind}`;
  element.hidden = false;
}

function hideNotice(element) {
  element.hidden = true;
  element.textContent = "";
}

function apiError(payload, fallback) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
  }
  return fallback;
}

async function responseData(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

async function refreshSession() {
  if (!session?.refresh_token) return false;
  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: session.refresh_token }),
  });
  const data = await responseData(response);
  if (!response.ok || !data.access_token) {
    saveSession(null);
    return false;
  }
  saveSession({ ...data, user: data.user || session.user });
  return true;
}

async function api(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && retry && session?.refresh_token && path !== "/api/v1/auth/refresh") {
    if (await refreshSession()) return api(path, options, false);
  }
  const data = await responseData(response);
  if (!response.ok) {
    throw new Error(apiError(data, `Request failed (${response.status}).`));
  }
  return data;
}

function setAuthMode(mode) {
  authMode = mode;
  const isSignup = mode === "signup";
  loginTab.classList.toggle("is-active", !isSignup);
  signupTab.classList.toggle("is-active", isSignup);
  loginTab.setAttribute("aria-selected", String(!isSignup));
  signupTab.setAttribute("aria-selected", String(isSignup));
  signupFields.hidden = !isSignup;
  for (const field of signupFields.querySelectorAll("input")) {
    field.required = isSignup;
  }
  confirmWrap.hidden = !isSignup;
  confirmPassword.required = isSignup;
  document.querySelector("#password").autocomplete = isSignup ? "new-password" : "current-password";
  authTitle.textContent = isSignup ? "Create your account" : "Welcome back";
  authSubtitle.textContent = isSignup
    ? "Make a little room for your next big question."
    : "Sign in to pick up where your curiosity left off.";
  authSubmitLabel.textContent = isSignup ? "Create account" : "Sign in";
  hideNotice(authMessage);
}

function showAuth(message = "") {
  workspaceView.hidden = true;
  authView.hidden = false;
  if (message) showNotice(authMessage, message);
}

async function loadConversation(id) {
  hideNotice(researchError);
  try {
    const data = await api(`/api/v1/conversations/${encodeURIComponent(id)}`);
    currentConversationId = data.id;
    currentReport = data.report;
    conversation = data.messages;
    renderReport(currentReport);
    renderMessages();
  } catch (error) {
    showNotice(researchError, error.message);
  }
}

function resetCurrentConversation() {
  currentReport = null;
  currentConversationId = null;
  conversation = [];
  report.hidden = true;
  reportEmpty.hidden = false;
  chatInput.disabled = true;
  chatInput.value = "";
  chatSubmit.disabled = true;
  renderMessages();
}

async function renderHistory() {
  const list = document.querySelector("#history-list");
  list.replaceChildren();
  hideNotice(historyError);
  try {
    const items = await api("/api/v1/conversations");
    for (const item of items) {
      const row = element("div", "history-row");
      const openButton = element("button", "history-item", item.title);
      openButton.type = "button";
      openButton.title = item.title;
      openButton.addEventListener("click", () => loadConversation(item.id));

      const deleteButton = element("button", "history-delete", "×");
      deleteButton.type = "button";
      deleteButton.setAttribute("aria-label", `Delete conversation: ${item.title}`);
      deleteButton.title = "Delete conversation";
      deleteButton.addEventListener("click", async () => {
        if (!window.confirm(`Permanently delete "${item.title}" and its messages?`)) return;
        try {
          await api(`/api/v1/conversations/${encodeURIComponent(item.id)}`, { method: "DELETE" });
          if (currentConversationId === item.id) resetCurrentConversation();
          await renderHistory();
        } catch (error) {
          showNotice(historyError, error.message);
        }
      });

      row.append(openButton, deleteButton);
      list.append(row);
    }
  } catch (error) {
    showNotice(historyError, error.message);
  }
}

async function enterWorkspace(user) {
  const displayName = user?.full_name || user?.email?.split("@")[0] || "Researcher";
  document.querySelector("#account-name").textContent = displayName;
  document.querySelector("#account-email").textContent = user?.email || "";
  document.querySelector("#account-avatar").textContent = displayName.slice(0, 1).toUpperCase();
  authView.hidden = true;
  workspaceView.hidden = false;
  hideNotice(authMessage);
  await renderHistory();
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function addListCard(container, title, values) {
  const card = element("article", "report-card");
  card.append(element("h3", "", title));
  const list = element("ul", "report-list");
  for (const value of values || []) list.append(element("li", "", value));
  card.append(list);
  container.append(card);
}

function renderReport(data) {
  report.replaceChildren();
  report.hidden = false;
  reportEmpty.hidden = true;
  chatEmpty.hidden = true;
  chatInput.disabled = false;
  chatSubmit.disabled = false;

  const header = element("header", "report-header");
  const heading = document.createElement("div");
  heading.append(element("span", "report-kicker", "YOUR RESEARCH BRIEF"));
  heading.append(element("h2", "", data.topic));
  const timestamp = data.generated_at
    ? new Date(data.generated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
    : "Just now";
  heading.append(element("span", "report-meta", `Prepared ${timestamp} · ${data.research_type?.replaceAll("_", " ") || "preliminary analysis"}`));
  header.append(heading, element("span", "report-status", data.status || "ready"));
  report.append(header);

  const summary = element("article", "report-card");
  summary.append(element("h3", "", "Executive summary"));
  summary.append(element("p", "", data.executive_summary || "A first-pass framework for your research question."));
  report.append(summary);

  const columns = element("div", "report-columns");
  addListCard(columns, "Keywords", data.keywords?.length ? data.keywords : ["No keywords identified"]);
  const areas = element("article", "report-card");
  areas.append(element("h3", "", "Areas to explore"));
  for (const item of data.research_areas || []) {
    const area = element("div", "area-item");
    area.append(element("strong", "", item.area));
    area.append(element("span", "", item.description));
    areas.append(area);
  }
  columns.append(areas);
  report.append(columns);

  addListCard(report, "Questions to guide your research", data.research_questions);
  if (data.recommended_next_steps?.length) {
    addListCard(report, "Suggested next steps", data.recommended_next_steps);
  }
  const caveats = element("div", "report-disclaimer");
  caveats.append(element("span", "", "ⓘ"));
  caveats.append(element("span", "", "This is a preliminary research framework. It does not retrieve or verify external sources."));
  report.append(caveats);
}

function renderMessages() {
  chatMessages.replaceChildren();
  for (const message of conversation) {
    chatMessages.append(element(
      "div",
      `chat-message ${message.role === "user" ? "user" : "assistant"}`,
      message.content,
    ));
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;
  chatEmpty.hidden = Boolean(currentReport);
}

loginTab.addEventListener("click", () => setAuthMode("login"));
signupTab.addEventListener("click", () => setAuthMode("signup"));

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideNotice(authMessage);
  const email = document.querySelector("#email").value.trim();
  const password = document.querySelector("#password").value;
  if (authMode === "signup" && password !== confirmPassword.value) {
    showNotice(authMessage, "Those passwords do not match.");
    return;
  }

  authSubmit.disabled = true;
  authSubmitLabel.textContent = authMode === "signup" ? "Creating account…" : "Signing in…";
  try {
    const request = { email, password };
    if (authMode === "signup") {
      request.full_name = document.querySelector("#full-name").value.trim();
      request.phone_number = document.querySelector("#phone-number").value.trim();
      request.country = document.querySelector("#country").value.trim();
    }
    const data = await api(`/api/v1/auth/${authMode}`, {
      method: "POST",
      body: JSON.stringify(request),
    });
    if (!data.access_token) {
      setAuthMode("login");
      showNotice(authMessage, "Account created. Check your email to confirm your address, then sign in.", "notice notice-warn");
      return;
    }
    saveSession(data);
    await enterWorkspace(data.user);
  } catch (error) {
    showNotice(authMessage, error.message);
  } finally {
    authSubmit.disabled = false;
    authSubmitLabel.textContent = authMode === "signup" ? "Create account" : "Sign in";
  }
});

researchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideNotice(researchError);
  const topic = researchTopic.value.trim();
  if (topic.length < 3) {
    showNotice(researchError, "Enter a research question with at least 3 characters.");
    return;
  }
  researchSubmit.disabled = true;
  researchSubmitLabel.textContent = "Building brief…";
  report.hidden = true;
  reportEmpty.hidden = true;
  currentReport = null;
  currentConversationId = null;
  conversation = [];
  renderMessages();
  try {
    currentReport = await api("/research", {
      method: "POST",
      body: JSON.stringify({ topic }),
    });
    currentConversationId = currentReport.conversation_id;
    renderReport(currentReport);
    await renderHistory();
    researchTopic.value = "";
  } catch (error) {
    reportEmpty.hidden = false;
    showNotice(researchError, error.message);
  } finally {
    researchSubmit.disabled = false;
    researchSubmitLabel.textContent = "Build my brief";
  }
});

chatInput.addEventListener("input", () => {
  chatSubmit.disabled = !currentReport || !chatInput.value.trim();
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = chatInput.value.trim();
  if (!prompt || !currentReport) return;
  hideNotice(chatError);
  conversation.push({ role: "user", content: prompt });
  chatInput.value = "";
  chatSubmit.disabled = true;
  renderMessages();

  try {
    const provider = document.querySelector("#provider").value;
    const model = provider === "ollama" ? "llama3.1" : provider === "openai" ? "gpt-4o-mini" : provider === "anthropic" ? "claude-3-5-sonnet-20241022" : provider === "gemini" ? "gemini-1.5-flash" : provider === "groq" ? "llama-3.1-8b-instant" : "auto";
    const result = await api(`/api/v1/conversations/${encodeURIComponent(currentConversationId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ provider, model, content: prompt }),
    });
    conversation.push({ role: "assistant", content: result.content });
  } catch (error) {
    showNotice(chatError, error.message);
  } finally {
    chatSubmit.disabled = !chatInput.value.trim();
    renderMessages();
    chatSubmit.disabled = !currentReport || !chatInput.value.trim();
  }
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    researchTopic.value = button.dataset.prompt;
    researchTopic.focus();
  });
});

document.querySelector("#new-research").addEventListener("click", () => {
  resetCurrentConversation();
  chatEmpty.hidden = false;
  researchTopic.focus();
});

document.querySelector("#logout").addEventListener("click", async () => {
  try {
    if (session?.access_token) await api("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // The local session is cleared even if the remote session has already expired.
  }
  saveSession(null);
  resetCurrentConversation();
  showAuth();
});

async function initialize() {
  try {
    const authConfig = await api("/api/v1/auth/config");
    authSetup.hidden = authConfig.configured;
    authSubmit.disabled = !authConfig.configured;
    if (!authConfig.configured) {
      showNotice(
        authMessage,
        "Authentication needs to be configured before you can sign in or create an account.",
        "notice notice-warn",
      );
    }
  } catch {
    showNotice(authMessage, "Could not connect to the API. Check the server and try again.");
  }

  if (!session?.access_token) return;
  try {
    const user = await api("/api/v1/auth/me");
    session.user = user;
    saveSession(session);
    await enterWorkspace(user);
  } catch {
    saveSession(null);
  }
}

initialize();
