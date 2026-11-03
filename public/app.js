"use strict";

const deckListEl = document.getElementById("deck-list");
const contentEl = document.getElementById("content");
const modal = document.getElementById("modal");
const modalImg = document.getElementById("modal-img");
const modalInfo = document.getElementById("modal-info");

let decks = [];
let currentDir = null;
let currentFile = null;

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error("HTTP " + res.status + " for " + url);
  return res.json();
}

function groupDot(category) {
  const key = String(category || "").toLowerCase();
  return `<span class="dot ${esc(key)}"></span>`;
}

function sourceBlock(source) {
  if (!source || typeof source !== "object") return "";
  const parts = [];
  if (source.result) parts.push(`<div class="m-row"><b>Result</b> ${esc(source.result)}</div>`);
  if (source.format) parts.push(`<div class="m-row"><b>Format</b> ${esc(source.format)}</div>`);
  if (source.archetype_record)
    parts.push(`<div class="m-row"><b>Record</b> ${esc(source.archetype_record)}</div>`);
  if (source.note) parts.push(`<div class="m-row"><b>Note</b> ${esc(source.note)}</div>`);
  const links = [];
  if (source.archetype_page)
    links.push(
      `<a href="${esc(source.archetype_page)}" target="_blank" rel="noopener">Archetype page</a>`
    );
  if (source.list_page)
    links.push(
      `<a href="${esc(source.list_page)}" target="_blank" rel="noopener">Deck list</a>`
    );
  if (!parts.length && !links.length) return "";
  return (
    `<div class="source-block">` +
    parts.join("") +
    (links.length ? `<div class="source-links">${links.join(" · ")}</div>` : "") +
    `</div>`
  );
}

// ---------------------------------------------------------------------------
// rendering
// ---------------------------------------------------------------------------

function renderDeckList() {
  deckListEl.innerHTML = "";
  const groups = [
    { dir: "decks", label: "Your decks" },
    { dir: "example", label: "Examples" },
  ];

  groups.forEach((group) => {
    const items = decks.filter((d) => d.dir === group.dir);
    if (!items.length) return;

    const header = document.createElement("div");
    header.className = "deck-group-label";
    header.textContent = group.label;
    deckListEl.appendChild(header);

    items.forEach((d) => {
      const btn = document.createElement("button");
      btn.className = "deck-item";
      if (d.dir === currentDir && d.file === currentFile) btn.classList.add("active");
      btn.innerHTML =
        `<span class="deck-title">${esc(d.deck_name)}</span>` +
        `<span class="deck-meta">${d.total} cards · ${esc(d.groupCounts)}</span>`;
      btn.addEventListener("click", () => selectDeck(d.dir, d.file));
      deckListEl.appendChild(btn);
    });
  });

  if (!decks.length) {
    deckListEl.innerHTML = `<p class="muted">No decks found.</p>`;
  }
}

function cardTile(card) {
  const low = card.image && card.image.low ? card.image.low : "";
  const fallback = `<div class="fallback">${esc(card.name)}</div>`;
  const imgTag = low
    ? `<img src="${esc(low)}" alt="${esc(card.name)}" loading="lazy" ` +
      `onerror="this.style.display='none'; this.parentElement.querySelector('.fallback').style.display='flex';">`
    : "";

  const tile = document.createElement("div");
  tile.className = "card-tile" + (card.found ? "" : " not-found");
  tile.innerHTML =
    `<div class="thumb">${fallback}${imgTag}</div>` +
    `<div class="card-count">${Number(card.count)}&times;</div>` +
    `<div class="card-body">` +
    `<div class="card-name">${esc(card.name)}</div>` +
    (card.id ? `<div class="card-id">${esc(card.id)}</div>` : "") +
    (card.role ? `<div class="card-role">${esc(card.role)}</div>` : "") +
    `</div>`;
  tile.addEventListener("click", () => openModal(card));
  return tile;
}

function renderDeck(deck) {
  const findCount = (cat) =>
    (deck.groups.find((g) => g.category === cat) || {}).total || 0;
  const statPokemon = findCount("Pokémon");
  const statTrainer = findCount("Trainer");
  const statEnergy = findCount("Energy");

  let html =
    `<div class="deck-head">` +
    `<div class="deck-title-row">` +
    `<h2>${esc(deck.deck_name)}</h2>` +
    (deck.dir === "example" ? `<span class="badge">Example</span>` : "") +
    `</div>` +
    `<div class="deck-stats">` +
    `<span class="stat">Total <b>${deck.total}</b></span>` +
    `<span class="stat pokemon">Pokémon <b>${statPokemon}</b></span>` +
    `<span class="stat trainer">Trainer <b>${statTrainer}</b></span>` +
    `<span class="stat energy">Energy <b>${statEnergy}</b></span>` +
    `</div>` +
    (deck.requirements ? `<p class="deck-requirements">${esc(deck.requirements)}</p>` : "") +
    (deck.source ? sourceBlock(deck.source) : "") +
    `</div>`;

  if (deck.strategy) {
    html +=
      `<section class="section">` +
      `<h3>Strategy</h3>` +
      `<div class="strategy">${esc(deck.strategy)}</div>` +
      `</section>`;
  }

  // The cards, grouped by category, each with an empty grid we fill below.
  for (const g of deck.groups) {
    html +=
      `<section class="section">` +
      `<h3>${groupDot(g.category)} ${esc(g.category)} <span class="muted">(${g.total})</span></h3>` +
      `<div class="card-grid"></div>` +
      `</section>`;
  }

  if (deck.synergies && deck.synergies.length) {
    html +=
      `<section class="section"><h3>Synergies</h3>` +
      deck.synergies
        .map(
          (s) =>
            `<div class="synergy">` +
            `<p class="syn-title">${esc((s.cards || []).join(" + "))}</p>` +
            (s.card_text && s.card_text.length
              ? `<div class="quote">${s.card_text.map(esc).join("\n")}</div>`
              : "") +
            (s.how_they_interact
              ? `<div class="how">${esc(s.how_they_interact)}</div>`
              : "") +
            `</div>`
        )
        .join("") +
      `</section>`;
  }

  if (deck.rejected && deck.rejected.length) {
    html +=
      `<section class="section"><h3>Rejected cards</h3>` +
      deck.rejected
        .map(
          (r) =>
            `<div class="rejected-item">` +
            `<div class="rej-name">${esc(r.name)}</div>` +
            (r.reason ? `<div class="rej-reason">${esc(r.reason)}</div>` : "") +
            `</div>`
        )
        .join("") +
      `</section>`;
  }

  if (deck.comparisons) {
    const text =
      typeof deck.comparisons === "string"
        ? deck.comparisons
        : JSON.stringify(deck.comparisons, null, 2);
    html +=
      `<section class="section"><details class="panel"><summary>Comparisons</summary>` +
      `<pre>${esc(text)}</pre>` +
      `</details></section>`;
  }

  contentEl.innerHTML = html;

  // Fill the grids in the same order as the groups.
  const grids = contentEl.querySelectorAll(".card-grid");
  let i = 0;
  for (const g of deck.groups) {
    const grid = grids[i++];
    g.cards.forEach((c) => grid.appendChild(cardTile(c)));
  }
}

// ---------------------------------------------------------------------------
// modal
// ---------------------------------------------------------------------------

function openModal(card) {
  const high = card.image && card.image.high ? card.image.high : "";
  modalImg.src = high || "";
  modalImg.alt = card.name;
  modalImg.style.display = high ? "" : "none";

  const rows = [];
  if (card.id) rows.push(`<span class="m-id">${esc(card.id)}</span>`);
  if (card.hp != null) rows.push(`<div class="m-row"><b>HP</b> ${esc(card.hp)}</div>`);
  if (card.stage) rows.push(`<div class="m-row"><b>Stage</b> ${esc(card.stage)}</div>`);
  if (card.trainerType)
    rows.push(`<div class="m-row"><b>Kind</b> ${esc(card.trainerType)}</div>`);
  if (card.types && card.types.length)
    rows.push(`<div class="m-row"><b>Type</b> ${esc(card.types.join(", "))}</div>`);
  if (card.energyType)
    rows.push(`<div class="m-row"><b>Energy</b> ${esc(card.energyType)}</div>`);
  rows.push(`<div class="m-row"><b>Copies</b> ${Number(card.count)}</div>`);

  modalInfo.innerHTML =
    `<h3>${esc(card.name)}</h3>` +
    rows.join("") +
    (card.role ? `<div class="m-role">${esc(card.role)}</div>` : "");

  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  modalImg.src = "";
}

modal.addEventListener("click", (e) => {
  if (e.target.closest("[data-close]")) closeModal();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// ---------------------------------------------------------------------------
// selection / boot
// ---------------------------------------------------------------------------

async function selectDeck(dir, file) {
  currentDir = dir;
  currentFile = file;
  renderDeckList();
  contentEl.innerHTML = `<p class="empty">Loading deck…</p>`;
  try {
    const deck = await getJson(
      `/api/deck?dir=${encodeURIComponent(dir)}&file=${encodeURIComponent(file)}`
    );
    renderDeck(deck);
    window.scrollTo({ top: 0 });
  } catch (err) {
    contentEl.innerHTML = `<p class="empty">Failed to load deck: ${esc(err.message)}</p>`;
  }
}

async function boot() {
  try {
    decks = await getJson("/api/decks");
    renderDeckList();
    if (decks.length) {
      await selectDeck(decks[0].dir, decks[0].file);
    } else {
      deckListEl.innerHTML = `<p class="muted">No decks found in decks/.</p>`;
      contentEl.innerHTML = `<p class="empty">No decks found.</p>`;
    }
  } catch (err) {
    deckListEl.innerHTML = `<p class="muted">Failed to load decks.</p>`;
    contentEl.innerHTML = `<p class="empty">Failed to load: ${esc(err.message)}</p>`;
  }
}

boot();
