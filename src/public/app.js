// ---------- Config ----------
const DEFAULT_API_BASE = "http://127.0.0.1:8000";
const state = {
  apiBase: localStorage.getItem("juno_api_base") || DEFAULT_API_BASE,
};

const $ = (id) => document.getElementById(id);

// ---------- Tabs ----------
const panelTitles = { events: "Events", transcribe: "Transcribe", content: "Content" };

document.querySelectorAll(".rail-btn[data-panel]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".rail-btn[data-panel]").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    const name = btn.dataset.panel;
    $("panel-" + name).classList.add("active");
    $("panelTitle").textContent = panelTitles[name];
  });
});

// ---------- Settings modal ----------
$("openSettings").addEventListener("click", () => {
  $("apiBaseInput").value = state.apiBase;
  $("settingsModal").classList.remove("hidden");
});
$("closeSettings").addEventListener("click", () => $("settingsModal").classList.add("hidden"));
$("saveSettings").addEventListener("click", () => {
  const val = $("apiBaseInput").value.trim().replace(/\/$/, "");
  if (val) {
    state.apiBase = val;
    localStorage.setItem("juno_api_base", val);
  }
  $("settingsModal").classList.add("hidden");
  checkHealth();
});

// ---------- API status ----------
async function checkHealth() {
  const dot = $("statusDot");
  const text = $("statusText");
  dot.className = "status-dot";
  text.textContent = "checking API…";
  try {
    const res = await fetch(`${state.apiBase}/api/events/pune?max_events=1`, { method: "GET" });
    if (res.ok || res.status === 502) {
      dot.classList.add("ok");
      text.textContent = state.apiBase;
    } else {
      throw new Error("bad status " + res.status);
    }
  } catch (e) {
    dot.classList.add("bad");
    text.textContent = "API unreachable";
  }
}
checkHealth();

// ---------- Events ----------
$("ev-search").addEventListener("click", async () => {
  const keywords = $("ev-keywords").value.trim();
  const max = $("ev-max").value || 10;
  const refresh = $("ev-refresh").checked;
  const params = new URLSearchParams({ max_events: max, refresh });
  if (keywords) params.set("keywords", keywords);

  setStatus("ev-status", "Searching Pune meetups…");
  try {
    const res = await fetch(`${state.apiBase}/api/events/pune?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderEvents(data);
    setStatus("ev-status", `${data.count ?? data.events?.length ?? 0} events${data.cached ? " (cached)" : ""}`, "ok");
  } catch (e) {
    setStatus("ev-status", "Failed to fetch events: " + e.message, "error");
  }
});

$("ev-search-groups").addEventListener("click", async () => {
  const raw = $("ev-groups").value.trim();
  if (!raw) return;
  const groups = raw.split("\n").map((l) => l.trim()).filter(Boolean);
  const max = $("ev-max").value || 10;

  setStatus("ev-status", "Scraping group URLs…");
  try {
    const res = await fetch(`${state.apiBase}/api/events/groups?refresh=${$("ev-refresh").checked}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ groups, max_events: Number(max) }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderEvents(data);
    setStatus("ev-status", `${data.count ?? data.events?.length ?? 0} events${data.cached ? " (cached)" : ""}`, "ok");
  } catch (e) {
    setStatus("ev-status", "Failed to scrape groups: " + e.message, "error");
  }
});

function renderEvents(data) {
  const grid = $("ev-results");
  grid.innerHTML = "";
  const events = data.events || [];
  if (!events.length) {
    grid.innerHTML = `<div class="hint">No events found.</div>`;
    return;
  }
  events.forEach((ev) => {
    const card = document.createElement("div");
    card.className = "event-card";
    if (ev.error) {
      card.innerHTML = `<h3>Error</h3><p>${escapeHtml(ev.error)}</p>`;
      grid.appendChild(card);
      return;
    }
    card.innerHTML = `
      <h3>${escapeHtml(ev.title || "Untitled event")}</h3>
      <div class="meta">${escapeHtml(ev.datetime_display || ev.datetime_iso || "")}</div>
      <p>${escapeHtml((ev.venue ? ev.venue + " · " : "") + (ev.group_name || ""))}</p>
      ${ev.url ? `<a href="${escapeAttr(ev.url)}" target="_blank" rel="noopener">Open on Meetup →</a>` : ""}
    `;
    grid.appendChild(card);
  });
}

// ---------- Transcribe ----------
$("tr-run").addEventListener("click", async () => {
  const filePath = $("tr-path").value.trim();
  if (!filePath) return setStatus("tr-status", "Enter a file path first.", "error");

  setStatus("tr-status", "Transcribing… this can take a while for long videos.");
  $("tr-result").hidden = true;
  try {
    const res = await fetch(`${state.apiBase}/api/transcript/video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_path: filePath }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.status) throw new Error("Transcription service reported failure");
    const segments = Array.isArray(data.text) ? data.text : [String(data.text || "")];
    state.lastTranscript = segments.join("\n");
    $("tr-segments").textContent = state.lastTranscript;
    $("tr-result").hidden = false;
    setStatus("tr-status", `Done — ${segments.length} segments`, "ok");
  } catch (e) {
    setStatus("tr-status", "Transcription failed: " + e.message, "error");
  }
});

$("tr-copy").addEventListener("click", () => {
  if (state.lastTranscript) navigator.clipboard.writeText(state.lastTranscript);
});

$("tr-send").addEventListener("click", () => {
  if (!state.lastTranscript) return;
  $("ct-input").value = state.lastTranscript;
  document.querySelector('.rail-btn[data-panel="content"]').click();
});

// ---------- Content generation ----------
$("ct-run").addEventListener("click", async () => {
  const transcription = $("ct-input").value.trim();
  if (!transcription) return setStatus("ct-status", "Paste or send a transcription first.", "error");

  setStatus("ct-status", "Generating content ideas…");
  $("ct-output").innerHTML = "";
  try {
    const res = await fetch(`${state.apiBase}/api/content/c`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcription }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderContent(data);
    setStatus("ct-status", "Done", "ok");
  } catch (e) {
    setStatus("ct-status", "Content generation failed: " + e.message, "error");
  }
});

function renderContent(data) {
  const out = $("ct-output");
  out.innerHTML = "";

  // Try to find the raw text payload wherever it lives in the response
  let raw = null;
  if (typeof data === "string") raw = data;
  else if (typeof data?.content === "string") raw = data.content;
  else if (typeof data?.text === "string") raw = data.text;
  else if (Array.isArray(data?.content)) raw = data.content.map((c) => c.text || "").join("\n");

  const sections = raw ? parseSections(raw) : null;

  if (!sections || !sections.length) {
    out.innerHTML = `<div class="raw-fallback">${escapeHtml(JSON.stringify(data, null, 2))}</div>`;
    return;
  }

  // Compute a shared time scale across every timestamp found, so all scrubbers line up
  let maxSeconds = 1;
  sections.forEach((sec) => sec.entries.forEach((entry) => {
    ["timestamp", "source-range"].forEach((key) => {
      const range = parseRange(entry[key]);
      if (range) maxSeconds = Math.max(maxSeconds, range.end);
    });
  }));

  sections.forEach((sec) => {
    const secEl = document.createElement("div");
    secEl.className = "content-section";
    secEl.innerHTML = `<div class="content-section-title">${escapeHtml(sec.title)}</div>`;
    sec.entries.forEach((entry) => secEl.appendChild(renderIdeaCard(entry, maxSeconds)));
    out.appendChild(secEl);
  });
}

function renderIdeaCard(entry, maxSeconds) {
  const card = document.createElement("div");
  card.className = "idea-card";

  const titleKey = ["post-idea", "clip-idea"].find((k) => entry[k]);
  if (titleKey) {
    const t = document.createElement("div");
    t.className = "idea-title";
    t.textContent = entry[titleKey];
    card.appendChild(t);
  }

  Object.entries(entry).forEach(([key, val]) => {
    if (key === titleKey || key === "timestamp" || key === "source-range") return;
    const f = document.createElement("div");
    f.className = "idea-field";
    f.innerHTML = `<b>${escapeHtml(key)}:</b> ${escapeHtml(val)}`;
    card.appendChild(f);
  });

  const range = parseRange(entry.timestamp) || parseRange(entry["source-range"]);
  if (range) {
    const scrub = document.createElement("div");
    scrub.className = "scrubber";
    const leftPct = (range.start / maxSeconds) * 100;
    const widthPct = Math.max(((range.end - range.start) / maxSeconds) * 100, 0.6);
    scrub.innerHTML = `
      <div class="scrubber-track">
        <div class="scrubber-fill" style="left:${leftPct}%;width:${widthPct}%"></div>
      </div>
      <div class="scrubber-labels">
        <span>${entry.timestamp || entry["source-range"]}</span>
        <span>${secondsToTimecode(maxSeconds)}</span>
      </div>
    `;
    card.appendChild(scrub);
  }

  return card;
}

// Parses the "=== SECTION ===" / "key: value" format from the Juno prompt file
function parseSections(raw) {
  const sectionRegex = /===\s*(.+?)\s*===/g;
  const parts = raw.split(sectionRegex).filter((s) => s.trim());
  if (parts.length < 2) return null; // no section headers found

  const sections = [];
  for (let i = 0; i < parts.length; i += 2) {
    const title = parts[i];
    const body = parts[i + 1] || "";
    const entries = body
      .split(/\n\s*\n/)
      .map((block) => {
        const entry = {};
        block.split("\n").forEach((line) => {
          const m = line.match(/^([a-zA-Z-]+):\s*(.*)$/);
          if (m) entry[m[1].trim()] = m[2].trim();
        });
        return entry;
      })
      .filter((e) => Object.keys(e).length);
    if (entries.length) sections.push({ title, entries });
  }
  return sections;
}

function parseRange(str) {
  if (!str) return null;
  const m = str.match(/(\d{1,2}(?::\d{2}){1,2})\s*-\s*(\d{1,2}(?::\d{2}){1,2})/);
  if (!m) return null;
  return { start: timecodeToSeconds(m[1]), end: timecodeToSeconds(m[2]) };
}

function timecodeToSeconds(tc) {
  const parts = tc.split(":").map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return Number(parts[0]) || 0;
}

function secondsToTimecode(s) {
  s = Math.round(s);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}

// ---------- Helpers ----------
function setStatus(id, msg, kind) {
  const el = $(id);
  el.textContent = msg;
  el.className = "hint" + (kind ? " " + kind : "");
}
function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(str) { return escapeHtml(str); }