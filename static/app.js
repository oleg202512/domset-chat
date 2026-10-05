const STORAGE_KEY = "domset_api_key";
const SESSION_KEY = "domset_session_id";

const $ = (selector) => document.querySelector(selector);
const messages = $("#messages");
const chunks = $("#chunks");
const chunkCount = $("#chunk-count");
const typing = $("#typing");
const input = $("#message-input");
const modal = $("#settings-modal");
const apiKeyInput = $("#api-key");

let sessionId = sessionStorage.getItem(SESSION_KEY);
if (!sessionId) {
  sessionId = crypto.randomUUID().replaceAll("-", "");
  sessionStorage.setItem(SESSION_KEY, sessionId);
}

function addMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

function showWelcome() {
  messages.replaceChildren();
  chunks.replaceChildren();
  chunkCount.textContent = "0";
  $("#chunks-empty").classList.remove("hidden");
  addMessage("assistant", "Привет! Какой у тебя вопрос ?");
}

function renderChunks(items) {
  chunks.replaceChildren();
  chunkCount.textContent = items.length;
  $("#chunks-empty").classList.toggle("hidden", items.length > 0);
  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "chunk";
    const title = document.createElement("div");
    title.className = "chunk-title";
    title.textContent = `Фрагмент ${item.number}`;
    const score = document.createElement("span");
    score.textContent = `релевантность: ${item.score}`;
    title.appendChild(score);
    const text = document.createElement("div");
    text.className = "chunk-text";
    text.textContent = item.text;
    card.append(title, text);
    chunks.appendChild(card);
  });
}

function setLoading(value) {
  typing.classList.toggle("hidden", !value);
  input.disabled = value;
  $("#chat-form button").disabled = value;
}

async function sendMessage(message) {
  const key = localStorage.getItem(STORAGE_KEY);
  if (!key) {
    modal.classList.remove("hidden");
    apiKeyInput.focus();
    addMessage("assistant", "Сначала откройте настройки и сохраните API-ключ.");
    return;
  }
  addMessage("user", message);
  setLoading(true);
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось получить ответ.");
    renderChunks(data.chunks || []);
    addMessage("assistant", data.answer);
  } catch (error) {
    addMessage("assistant", error.message || "Произошла ошибка. Попробуйте ещё раз.");
  } finally {
    setLoading(false);
    input.focus();
  }
}

$("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendMessage(message);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("#chat-form").requestSubmit();
  }
});

$("#new-chat").addEventListener("click", async () => {
  await fetch(`/api/chat/${sessionId}`, { method: "DELETE" });
  showWelcome();
});

$("#settings-button").addEventListener("click", () => {
  apiKeyInput.value = localStorage.getItem(STORAGE_KEY) || "";
  $("#settings-status").textContent = "";
  modal.classList.remove("hidden");
  apiKeyInput.focus();
});
$("#close-settings").addEventListener("click", () => modal.classList.add("hidden"));
modal.addEventListener("click", (event) => {
  if (event.target === modal) modal.classList.add("hidden");
});
$("#save-settings").addEventListener("click", () => {
  const key = apiKeyInput.value.trim();
  if (!key) {
    $("#settings-status").textContent = "Введите API-ключ.";
    return;
  }
  localStorage.setItem(STORAGE_KEY, key);
  $("#settings-status").textContent = "Ключ сохранён в браузере.";
  setTimeout(() => modal.classList.add("hidden"), 500);
});

showWelcome();
