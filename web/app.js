// Frontend for the AI Job-Match Helper. Plain JavaScript, no build step needed.

const $ = (id) => document.getElementById(id);
const state = { config: null, language: "English" };

// ---------- helpers ----------
function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function showError(message) {
  $("error").textContent = "⚠️ " + message;
  $("error").hidden = !message;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* not JSON */ }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res;
}

function setLoading(button, loading) {
  button.disabled = loading;
  button.classList.toggle("loading", loading);
}

// Colour for a 0-100 value: red -> orange -> green
function scoreColor(pct) {
  if (pct >= 75) return "#10b981";
  if (pct >= 50) return "#f59e0b";
  return "#ef4444";
}

// A tiny, safe Markdown renderer for the AI tips (headings, lists, bold, italics, code).
function renderMarkdown(md) {
  const inline = (s) =>
    escapeHtml(s)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
      .replace(/(^|\W)\*(?!\s)(.+?)\*(?=\W|$)/g, "$1<i>$2</i>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");
  let html = "";
  let list = null;
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of md.split("\n")) {
    const line = raw.trimEnd();
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) {
      closeList();
      const level = Math.min(m[1].length + 1, 4);
      html += `<h${level}>${inline(m[2])}</h${level}>`;
    } else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) {
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) {
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

// ---------- settings ----------
async function loadConfig() {
  state.config = await (await api("/api/config")).json();
  const select = $("provider");
  for (const p of state.config.providers) {
    select.add(new Option(p.label, p.key, false, p.key === state.config.default_provider));
  }
  select.addEventListener("change", onProviderChange);
  onProviderChange();

  for (const lang of state.config.languages) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = lang;
    btn.classList.toggle("active", lang === state.language);
    btn.addEventListener("click", () => {
      state.language = lang;
      document.querySelectorAll("#languages button").forEach((b) => b.classList.toggle("active", b === btn));
      updateSummary();
    });
    $("languages").append(btn);
  }
  updateSummary();
}

function currentProvider() {
  return state.config.providers.find((p) => p.key === $("provider").value);
}

function onProviderChange() {
  const p = currentProvider();
  $("model").value = p.default_model;
  $("key-wrap").hidden = !p.needs_api_key;
  updateSummary();
}

function updateSummary() {
  $("settings-summary").textContent = `· ${currentProvider().label} · tips in ${state.language}`;
}
$("model").addEventListener("input", updateSummary);

// ---------- inputs ----------
document.querySelectorAll("[data-sample]").forEach((btn) =>
  btn.addEventListener("click", async () => {
    const name = btn.dataset.sample;
    const { text } = await (await api(`/api/samples/${name}`)).json();
    $(name === "cv" ? "cv" : "job").value = text;
    if (name !== "cv" && !$("cv").value.trim()) {
      $("cv").value = (await (await api("/api/samples/cv")).json()).text;
    }
  })
);

async function uploadFile(file) {
  if (!file) return;
  showError("");
  const form = new FormData();
  form.append("file", file);
  try {
    const { text } = await (await api("/api/extract", { method: "POST", body: form })).json();
    $("cv").value = text;
  } catch (err) {
    showError(err.message);
  }
}

const drop = $("drop");
$("file").addEventListener("change", (e) => uploadFile(e.target.files[0]));
["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); })
);
["dragleave", "drop"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); })
);
drop.addEventListener("drop", (e) => uploadFile(e.dataTransfer.files[0]));

// ---------- match ----------
function chips(id, items) {
  $(id).innerHTML = items.length
    ? items.map((s, i) => `<span class="chip" style="animation-delay:${i * 40}ms">${escapeHtml(s)}</span>`).join("")
    : '<span class="none">none</span>';
}

function animateScore(target) {
  const ring = $("ring");
  const color = scoreColor(target);
  ring.style.setProperty("--c", color);
  const start = performance.now();
  const step = (now) => {
    const t = Math.min(1, (now - start) / 900);
    const value = Math.round(target * (1 - Math.pow(1 - t, 3)));
    $("score").textContent = value;
    ring.style.setProperty("--p", value);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderResult(r) {
  $("results").hidden = false;
  animateScore(r.score);

  const label = $("label");
  label.textContent = r.label;
  label.className = "pill " + r.label.split(" ")[0].toLowerCase();

  const skillPct = r.skill_score === null ? null : Math.round(r.skill_score * 100);
  const semPct = Math.round(r.semantic_score * 100);
  $("skill-pct").textContent = skillPct === null ? "n/a" : skillPct + "%";
  $("sem-pct").textContent = semPct + "%";
  requestAnimationFrame(() => {
    $("skill-bar").style.width = (skillPct ?? 0) + "%";
    $("sem-bar").style.width = semPct + "%";
  });
  const sw = Math.round(state.config.skill_weight * 100);
  const mw = Math.round(state.config.semantic_weight * 100);
  $("formula").textContent =
    `Score = ${sw}% skill overlap + ${mw}% semantic similarity. Skill overlap counts the job's skills found in ` +
    `your CV (nice-to-haves count half). Semantic similarity checks how well each job requirement is covered ` +
    `by some part of your CV.`;

  chips("matched-req", r.matched_required);
  chips("missing-req", r.missing_required);
  chips("matched-opt", r.matched_optional);
  chips("missing-opt", r.missing_optional);
  chips("extra", r.extra_cv_skills);
  $("extra-wrap").hidden = !r.extra_cv_skills.length;

  const coverage = [...r.coverage].sort((a, b) => a.score - b.score);
  $("coverage").innerHTML = coverage
    .map((c) => {
      const pct = Math.round(c.score * 100);
      return `<li>
        <div class="cov-pct" style="background:${scoreColor(pct)}">${pct}%</div>
        <div><div class="cov-req">${escapeHtml(c.requirement)}</div>
        <div class="cov-cv">Closest part of your CV: ${escapeHtml(c.best_cv_match.slice(0, 250))}</div></div>
      </li>`;
    })
    .join("");

  $("tips").innerHTML =
    '<p class="muted">Click the button to get rewritten bullets, ways to close each gap and keywords to add.</p>';
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function inputs() {
  return { cv_text: $("cv").value, job_text: $("job").value };
}

$("match-btn").addEventListener("click", async () => {
  showError("");
  const body = inputs();
  if (!body.cv_text.trim() || !body.job_text.trim()) {
    showError("Add both your CV and the job post first (or click a sample button).");
    return;
  }
  const btn = $("match-btn");
  setLoading(btn, true);
  btn.querySelector("span").textContent = "Scoring... (the first time downloads the model)";
  try {
    const res = await api("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderResult(await res.json());
  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(btn, false);
    btn.querySelector("span").textContent = "🔍 Check match";
  }
});

// ---------- tips (streamed) ----------
$("tips-btn").addEventListener("click", async () => {
  const btn = $("tips-btn");
  const out = $("tips");
  setLoading(btn, true);
  out.innerHTML = '<p class="muted">Thinking...</p>';
  try {
    const res = await api("/api/tips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...inputs(),
        provider: $("provider").value,
        model: $("model").value.trim(),
        api_key: $("api-key").value.trim(),
        language: state.language,
      }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      out.innerHTML = renderMarkdown(text);
    }
    if (!text.trim()) out.innerHTML = '<p class="muted">The AI returned an empty answer. Try again.</p>';
  } catch (err) {
    out.innerHTML = `<p class="error">⚠️ ${escapeHtml(err.message)}</p>`;
  } finally {
    setLoading(btn, false);
  }
});

loadConfig().catch((err) => showError("Could not reach the server: " + err.message));
