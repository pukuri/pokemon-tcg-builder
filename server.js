#!/usr/bin/env node
/**
 * Local server for the Pokémon TCG deck viewer.
 *
 * It reads the built decks from decks/*.json and the card data from
 * data/pokemon_standard/cards_full.json, resolves every deck entry to its card
 * image URL, and serves a small single-page frontend from public/.
 *
 * No dependencies, no build step. Run with:
 *     npm start            (or: node server.js)
 *
 * The card images are hosted by TCGdex (https://assets.tcgdex.net), so the
 * browser needs internet access to show them.
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const PUBLIC_DIR = path.join(ROOT, "public");
const DECKS_DIR = path.join(ROOT, "decks");
const EXAMPLE_DIR = path.join(ROOT, "example");
const DIRS = [
  { dir: "decks", path: DECKS_DIR, label: "Your decks" },
  { dir: "example", path: EXAMPLE_DIR, label: "Examples" },
];
const CARD_FILES = [
  path.join(ROOT, "data", "pokemon_standard", "cards_full.json"),
  path.join(ROOT, "data", "cards_full.json"),
  path.join(ROOT, "data", "cards_unique.json"),
];

const PORT = Number(process.env.PORT) || 3000;

// ---------------------------------------------------------------------------
// helpers (mirror the logic in check_deck.py / simulate_deck.py)
// ---------------------------------------------------------------------------

function norm(text) {
  return String(text == null ? "" : text)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[\u2018\u2019]/g, "'")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

function loadCards() {
  let cardsPath = null;
  for (const p of CARD_FILES) {
    if (fs.existsSync(p)) {
      cardsPath = p;
      break;
    }
  }
  if (!cardsPath) {
    throw new Error("Card data not found. Put cards_full.json in data/.");
  }
  const raw = fs.readFileSync(cardsPath, "utf8");
  let data = JSON.parse(raw);
  if (Array.isArray(data)) {
    data = { cards: data };
  }
  const list = data.cards || data.data || Object.values(data);

  const byId = new Map();
  const byName = new Map();
  for (const card of list) {
    if (!card || typeof card !== "object" || !card.name) continue;
    if (card.id) byId.set(norm(card.id), card);
    if (!byName.has(norm(card.name))) byName.set(norm(card.name), []);
    byName.get(norm(card.name)).push(card);
  }
  return { byId, byName, path: cardsPath };
}

function imageUrls(card) {
  const base = (card && card.image) || "";
  return {
    base,
    low: base ? base + "/low.png" : "",
    high: base ? base + "/high.png" : "",
  };
}

function categoryOf(card) {
  const c = norm(card.category);
  if (c === "pokemon" || c === "pok\u00e9mon") return "Pok\u00e9mon";
  if (c === "trainer") return "Trainer";
  if (c === "energy") return "Energy";
  return card.category || "Other";
}

function resolveCard(entry, byId, byName) {
  let card = null;
  if (entry.id) card = byId.get(norm(entry.id)) || null;
  if (!card && entry.name) {
    const versions = byName.get(norm(entry.name));
    if (versions && versions.length) card = versions[0];
  }
  return card;
}

function listDir(entry) {
  if (!fs.existsSync(entry.path)) return [];
  return fs
    .readdirSync(entry.path)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .map((file) => ({ dir: entry.dir, file }));
}

function listAllDecks() {
  const all = [];
  for (const entry of DIRS) all.push(...listDir(entry));
  return all;
}

function resolveDir(dir) {
  const entry = DIRS.find((d) => d.dir === dir);
  return entry || null;
}

function buildDeck(dir, file, byId, byName) {
  const entry = resolveDir(dir);
  if (!entry) throw new Error("Unknown deck directory: " + dir);
  const deck = JSON.parse(fs.readFileSync(path.join(entry.path, file), "utf8"));
  const entries = Array.isArray(deck) ? deck : deck.cards || [];

  const cards = entries.map((entry) => {
    const card = resolveCard(entry, byId, byName);
    return {
      name: entry.name || (card && card.name) || entry.id || "?",
      count: entry.count,
      id: entry.id || (card && card.id) || "",
      role: entry.role || "",
      category: card ? categoryOf(card) : "Unknown",
      found: Boolean(card),
      image: imageUrls(card),
      types: (card && card.types) || [],
      hp: (card && card.hp) || null,
      stage: (card && card.stage) || null,
      trainerType: (card && card.trainerType) || null,
      energyType: (card && card.energyType) || null,
    };
  });

  // Group counts by category, preserving the deck's own order.
  const groups = [];
  const byCat = new Map();
  for (const c of cards) {
    if (!byCat.has(c.category)) {
      const g = { category: c.category, cards: [], total: 0 };
      byCat.set(c.category, g);
      groups.push(g);
    }
    const g = byCat.get(c.category);
    g.cards.push(c);
    g.total += c.count;
  }

  const total = cards.reduce((s, c) => s + (Number(c.count) || 0), 0);

  return {
    dir,
    file,
    deck_name: deck.deck_name || file.replace(/\.json$/, ""),
    requirements: deck.requirements || "",
    strategy: deck.strategy || "",
    source: deck.source || null,
    synergies: deck.synergies || [],
    rejected: deck.rejected || [],
    comparisons: deck.comparisons || null,
    consistency_checks: deck.consistency_checks || [],
    total,
    groups,
  };
}

// ---------------------------------------------------------------------------
// HTTP
// ---------------------------------------------------------------------------

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
};

function sendJson(res, code, obj) {
  const body = JSON.stringify(obj, null, 2);
  res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
  res.end(body);
}

function serveStatic(req, res) {
  let urlPath = decodeURIComponent(req.url.split("?")[0]);
  if (urlPath === "/") urlPath = "/index.html";
  const filePath = path.normalize(path.join(PUBLIC_DIR, urlPath));
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0];

  if (url === "/api/decks") {
    try {
      const byIdName = loadCards();
      const summaries = listAllDecks().map(({ dir, file }) => {
        const deck = buildDeck(dir, file, byIdName.byId, byIdName.byName);
        const groupCounts = deck.groups.map((g) => `${g.category} ${g.total}`).join(" / ");
        return {
          dir,
          file,
          deck_name: deck.deck_name,
          requirements: deck.requirements,
          total: deck.total,
          groupCounts,
          strategy: deck.strategy,
        };
      });
      sendJson(res, 200, summaries);
    } catch (e) {
      sendJson(res, 500, { error: String(e && e.message ? e.message : e) });
    }
    return;
  }

  if (url === "/api/deck") {
    try {
      const q = new URL(req.url, "http://localhost").searchParams;
      const dir = q.get("dir") || "decks";
      const file = q.get("file") || "";
      if (!/^[a-z0-9._-]+\.json$/i.test(file)) {
        sendJson(res, 400, { error: "bad deck file name" });
        return;
      }
      const byIdName = loadCards();
      const deck = buildDeck(dir, file, byIdName.byId, byIdName.byName);
      deck.cardDataPath = byIdName.path;
      sendJson(res, 200, deck);
    } catch (e) {
      sendJson(res, 500, { error: String(e && e.message ? e.message : e) });
    }
    return;
  }

  serveStatic(req, res);
});

server.listen(PORT, () => {
  console.log(`\n  Pok\u00e9mon TCG deck viewer running at:\n`);
  console.log(`      http://localhost:${PORT}\n`);
  console.log(`  Reading decks from:  ${DECKS_DIR}`);
  console.log(`  Reading examples from: ${EXAMPLE_DIR}`);
  const cardsPath = CARD_FILES.find((p) => fs.existsSync(p));
  console.log(`  Reading cards from:  ${cardsPath || "(not found)"}\n`);
});
