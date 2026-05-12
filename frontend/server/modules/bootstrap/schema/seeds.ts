import { randomUUID } from "node:crypto";
import type { DatabaseSync } from "node:sqlite";
import { seedDefaultWorkflowPacks } from "./workflow-pack-seeds.ts";

type DbLike = Pick<DatabaseSync, "exec" | "prepare">;

export function applyDefaultSeeds(db: DbLike): void {
  seedDefaultWorkflowPacks(db);

  const deptCount = (db.prepare("SELECT COUNT(*) as cnt FROM departments").get() as { cnt: number }).cnt;

  if (deptCount === 0) {
    const insertDept = db.prepare(
      "INSERT INTO departments (id, name, name_ko, name_ja, name_zh, icon, color, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    );
    // Workflow order: 기획 → 개발 → 디자인 → QA → 인프라보안 → 운영
    insertDept.run("research",  "Research",  "Investigación",     "", "", "🔍", "#5a7a42", 1);
    insertDept.run("analysis",  "Analysis",  "Análisis",          "", "", "📊", "#4a6a8a", 2);
    insertDept.run("strategy",  "Strategy",  "Estrategia",        "", "", "♟️", "#ae9871", 3);
    insertDept.run("decision",  "Decision",  "Decisión y Riesgo", "", "", "⚖️", "#8a4a4a", 4);
    insertDept.run("execution", "Execution", "Ejecución",         "", "", "⚡", "#ae6a42", 5);
    insertDept.run("learning",  "Learning",  "Aprendizaje",       "", "", "🧪", "#6a4a8a", 6);
    console.log("[Claw-Empire] Seeded default departments");
  }

  const agentCount = (db.prepare("SELECT COUNT(*) as cnt FROM agents").get() as { cnt: number }).cnt;

  if (agentCount === 0) {
    // TradingAICenter: 26 V1 trading agents — sourced from config/agents.json
    // Special/Meta agents (Eleventh Man, Maverick, Tokin) placed in closest dept:
    //   The Eleventh Man → decision | Maverick → strategy | Tokin → learning
    const insertAgent = db.prepare(
      `INSERT INTO agents (id, name, name_ko, department_id, role, cli_provider, avatar_emoji, personality)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    );

    const v1Agents: [string, string, string, string, string, string, string][] = [
      // [name, name_ko (Spanish), department_id, role, cli_provider, avatar_emoji, personality]
      // ── DEPT 1: INVESTIGACIÓN (Research) ─────────────────────────────────────────
      ["X-Ray",            "X-Ray",          "research",  "senior",      "claude", "🛰️",  "Cold and precise. Obsessed with signals others miss. Tracks political leaders like a hawk and connects every tweet to a price move."],
      ["The Scheduler",    "El Planificador","research",  "senior",      "claude", "📅",  "Methodical and forward-looking. Lives 90 days ahead. Loves economic calendars and hates surprises."],
      ["Headlines",        "Los Titulares",  "research",  "senior",      "claude", "📰",  "Voracious news reader. Traces every story three levels deep. First to find the hidden market angle."],
      ["Charts",           "Las Gráficas",   "research",  "senior",      "claude", "📈",  "Speaks in candles and indicators. Every setup needs a stop-loss or it doesn't exist. Quietly confident."],
      ["The Accountant",   "El Contador",    "research",  "senior",      "claude", "🧮",  "Trusts numbers, not stories. Catches accounting tricks others miss. Red flags are his specialty."],
      ["Cryptid",          "Cryptid",        "research",  "senior",      "claude", "🕸️",  "Lives on-chain. Tracks whale wallets like a ghost. Understands DeFi flows most traders have never heard of."],
      ["Globe",            "El Globo",       "research",  "senior",      "claude", "🌍",  "Macro economist at heart. DXY is his north star. Sees money flows between countries before anyone else."],
      ["Ape",              "El Mono",        "research",  "junior",      "claude", "🦍",  "Enthusiastic and energetic. Feels the pulse of retail before it moves. Knows when a meme stock is about to ignite."],
      ["Recon",            "El Espía",       "research",  "senior",      "claude", "🕵️",  "Dark and methodical. Hunts for signals in unusual options, dark pools, and congressional filings. Trusts nothing obvious."],
      // ── DEPT 2: ANÁLISIS (Analysis) ──────────────────────────────────────────────
      ["Mood Ring",        "El Termómetro",  "analysis",  "team_leader", "claude", "💎",  "Aggregates all sentiment into one score. Master at detecting divergences. Knows when smart money and retail disagree."],
      ["Pattern Master",   "El Maestro",     "analysis",  "senior",      "claude", "⭐",  "Finds setups with surgical precision. Every trade scored 1-5 stars. Never presents an entry without a stop-loss."],
      ["Bull",             "El Toro",        "analysis",  "senior",      "claude", "🐂",  "Relentless optimist — but intellectually honest. Presents the strongest buy case. Challenges every bear argument head-on."],
      ["Bear",             "El Oso",         "analysis",  "senior",      "claude", "🐻",  "Professional skeptic. Finds every risk. Builds the strongest case for not trading. The voice of caution."],
      ["The Bridge",       "El Puente",      "analysis",  "senior",      "claude", "🌉",  "Cross-asset specialist. Spots correlation breakdowns before they happen. Connects markets that seem unrelated."],
      // ── DEPT 3: ESTRATEGIA (Strategy) ────────────────────────────────────────────
      ["The Architect",    "El Arquitecto",  "strategy",  "team_leader", "claude", "🏛️",  "Cool and decisive. Synthesizes chaos into clean trade plans. Moderates the Bull vs Bear debate with authority."],
      ["The Scribe",       "El Escriba",     "strategy",  "senior",      "claude", "✍️",  "Transforms raw analysis into beautiful, readable reports. Visual-first. Believes clarity is respect for the reader."],
      ["Maverick",         "El Maverick",    "strategy",  "junior",      "claude", "🎲",  "Eccentric creative genius. Connects red-string dots on the whiteboard. Finds lateral plays nobody else sees."],
      // ── DEPT 4: DECISIÓN Y RIESGO (Decision) ─────────────────────────────────────
      ["The Shield",       "El Escudo",      "decision",  "team_leader", "claude", "🛡️",  "Unyielding risk guardian. Has veto power. Non-negotiable rules, no exceptions. Circuit breaker for the whole system."],
      ["The Boss",         "El Jefe",        "decision",  "team_leader", "claude", "👔",  "Final AI decision maker. Reads everything, weighs all voices, and delivers a verdict in plain language."],
      ["The Messenger",    "El Mensajero",   "decision",  "senior",      "claude", "📲",  "The only agent who touches WhatsApp. Routes all alerts. Formats trade signals for human approval. Waits patiently."],
      ["The Eleventh Man", "El Undécimo",    "decision",  "senior",      "claude", "🎭",  "Cold contrarian. Must disagree when everyone agrees. Paranoid historian. Sees the crash in every consensus trade."],
      // ── DEPT 5: EJECUCIÓN (Execution) ────────────────────────────────────────────
      ["The Trigger",      "El Gatillo",     "execution", "team_leader", "claude", "⚡",  "Patient, precise, and fast. Executes only on human approval. Places stop-loss and take-profit automatically."],
      ["The Watchdog",     "El Guardián",    "execution", "senior",      "claude", "🐕",  "Loyal 24/7 monitor. Tracks every open position in real time. Escalates anything unusual to the human immediately."],
      // ── DEPT 6: APRENDIZAJE (Learning) ───────────────────────────────────────────
      ["The Historian",    "El Historiador", "learning",  "team_leader", "claude", "📚",  "Systematic backtester. Demands a full year of data before trusting any strategy. Measures what actually works."],
      ["The Professor",    "El Profesor",    "learning",  "senior",      "claude", "🎓",  "The system's self-improvement engine. Tracks every agent's accuracy. Adjusts weights when patterns are found."],
      ["Tokin",            "El Contador2",   "learning",  "senior",      "claude", "💰",  "Stingy CFO. Monitors every token spent and every API call. Has veto over all LLM calls when budget is exhausted."],
    ];

    for (const [name, nameKo, dept, role, provider, emoji, personality] of v1Agents) {
      insertAgent.run(randomUUID(), name, nameKo, dept, role, provider, emoji, personality);
    }
    console.log(`[TradingAICenter] Seeded ${v1Agents.length} V1 trading agents`);
  }

  // Seed default settings if none exist
  {
    const defaultRoomThemes = {
      ceoOffice: { accent: 0xa77d0c, floor1: 0xe5d9b9, floor2: 0xdfd0a8, wall: 0x998243 },
      research:  { accent: 0x7ab855, floor1: 0xd5e8c5, floor2: 0xc8ddb5, wall: 0x5a7a42 },
      analysis:  { accent: 0x5a9fd4, floor1: 0xc5d5e8, floor2: 0xb5c8dd, wall: 0x4a6a8a },
      strategy:  { accent: 0xd4a85a, floor1: 0xf0e1c5, floor2: 0xeddaba, wall: 0xae9871 },
      decision:  { accent: 0xc45a5a, floor1: 0xe8d5d5, floor2: 0xddc8c8, wall: 0x8a4a4a },
      execution: { accent: 0xe87a42, floor1: 0xf0d5c5, floor2: 0xedcdba, wall: 0xae6a42 },
      learning:  { accent: 0x9a6fc4, floor1: 0xe0d5f0, floor2: 0xd8c8ee, wall: 0x6a4a8a },
      breakRoom: { accent: 0xf0c878, floor1: 0xf7e2b7, floor2: 0xf6dead, wall: 0xa99c83 },
    };

    const settingsCount = (db.prepare("SELECT COUNT(*) as c FROM settings").get() as { c: number }).c;
    const isLegacySettingsInstall = settingsCount > 0;
    if (settingsCount === 0) {
      const insertSetting = db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)");
      insertSetting.run("companyName", "Claw-Empire");
      insertSetting.run("ceoName", "CEO");
      insertSetting.run("autoAssign", "true");
      insertSetting.run("yoloMode", "false");
      insertSetting.run("autoUpdateEnabled", "false");
      insertSetting.run("autoUpdateNoticePending", "false");
      insertSetting.run("oauthAutoSwap", "true");
      insertSetting.run("language", "en");
      insertSetting.run("defaultProvider", "claude");
      insertSetting.run(
        "providerModelConfig",
        JSON.stringify({
          claude: { model: "claude-opus-4-6", subModel: "claude-sonnet-4-6" },
          codex: {
            model: "gpt-5.3-codex",
            reasoningLevel: "xhigh",
            subModel: "gpt-5.3-codex",
            subModelReasoningLevel: "high",
          },
          gemini: { model: "gemini-3-pro-preview" },
          opencode: { model: "github-copilot/claude-sonnet-4.6" },
          copilot: { model: "github-copilot/claude-sonnet-4.6" },
          antigravity: { model: "google/antigravity-gemini-3-pro" },
        }),
      );
      insertSetting.run("roomThemes", JSON.stringify(defaultRoomThemes));
      console.log("[Claw-Empire] Seeded default settings");
    }

    const hasLanguageSetting = db.prepare("SELECT 1 FROM settings WHERE key = 'language' LIMIT 1").get() as
      | { 1: number }
      | undefined;
    if (!hasLanguageSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run("language", "en");
    }

    const hasOAuthAutoSwapSetting = db.prepare("SELECT 1 FROM settings WHERE key = 'oauthAutoSwap' LIMIT 1").get() as
      | { 1: number }
      | undefined;
    if (!hasOAuthAutoSwapSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run("oauthAutoSwap", "true");
    }

    const hasAutoUpdateEnabledSetting = db
      .prepare("SELECT 1 FROM settings WHERE key = 'autoUpdateEnabled' LIMIT 1")
      .get() as { 1: number } | undefined;
    if (!hasAutoUpdateEnabledSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run("autoUpdateEnabled", "false");
    }

    const hasYoloModeSetting = db.prepare("SELECT 1 FROM settings WHERE key = 'yoloMode' LIMIT 1").get() as
      | { 1: number }
      | undefined;
    if (!hasYoloModeSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run("yoloMode", "false");
    }

    const hasAutoUpdateNoticePendingSetting = db
      .prepare("SELECT 1 FROM settings WHERE key = 'autoUpdateNoticePending' LIMIT 1")
      .get() as { 1: number } | undefined;
    if (!hasAutoUpdateNoticePendingSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run(
        "autoUpdateNoticePending",
        isLegacySettingsInstall ? "true" : "false",
      );
    }

    const hasRoomThemesSetting = db.prepare("SELECT 1 FROM settings WHERE key = 'roomThemes' LIMIT 1").get() as
      | { 1: number }
      | undefined;
    if (!hasRoomThemesSetting) {
      db.prepare("INSERT INTO settings (key, value) VALUES (?, ?)").run(
        "roomThemes",
        JSON.stringify(defaultRoomThemes),
      );
    }
  }

  // TradingAICenter: ensure the office pack defaults to "development" so all
  // 26 trading agents are visible. Newcomers may land on a different pack
  // and see "0 agents". Force the trading pack on every boot.
  try {
    const packRow = db.prepare("SELECT value FROM settings WHERE key = 'officeWorkflowPack' LIMIT 1").get() as
      | { value: string }
      | undefined;
    const current = packRow?.value;
    if (current !== "development") {
      db.prepare(
        "INSERT INTO settings (key, value) VALUES ('officeWorkflowPack', 'development') ON CONFLICT(key) DO UPDATE SET value = 'development'",
      ).run();
      console.log("[TradingAICenter] Forced officeWorkflowPack to 'development' for trading agent visibility");
    }
  } catch (err) {
    console.warn("[TradingAICenter] Failed to force officeWorkflowPack:", err);
  }

  // TradingAICenter: add free-text current_task column to agents for brain status updates
  try {
    db.exec("ALTER TABLE agents ADD COLUMN current_task TEXT");
  } catch {
    /* already exists */
  }

  // Migrate: add sort_order column & set correct ordering for existing DBs
  {
    try {
      db.exec("ALTER TABLE agents ADD COLUMN acts_as_planning_leader INTEGER NOT NULL DEFAULT 0");
    } catch {
      /* already exists */
    }
    try {
      db.exec(`
        UPDATE agents
        SET acts_as_planning_leader = CASE
          WHEN role = 'team_leader' AND department_id = 'planning' THEN 1
          ELSE COALESCE(acts_as_planning_leader, 0)
        END
      `);
    } catch {
      /* best effort */
    }

    try {
      db.exec("ALTER TABLE departments ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 99");
    } catch {
      /* already exists */
    }

    // UNIQUE 인덱스 일시 제거 → 값 갱신 → 인덱스 재생성 (충돌 방지)
    try {
      db.exec("DROP INDEX IF EXISTS idx_departments_sort_order");
    } catch {
      /* noop */
    }
    const DEPT_ORDER: Record<string, number> = { research: 1, analysis: 2, strategy: 3, decision: 4, execution: 5, learning: 6 };

    const updateOrder = db.prepare("UPDATE departments SET sort_order = ? WHERE id = ?");
    for (const [id, order] of Object.entries(DEPT_ORDER)) {
      updateOrder.run(order, id);
    }

    const allDepartments = db
      .prepare("SELECT id, sort_order FROM departments ORDER BY sort_order ASC, id ASC")
      .all() as Array<{ id: string; sort_order: number }>;
    const existingDeptIds = new Set(allDepartments.map((row) => row.id));
    const usedOrders = new Set<number>();
    for (const [id, order] of Object.entries(DEPT_ORDER)) {
      if (!existingDeptIds.has(id)) continue;
      usedOrders.add(order);
    }

    let nextOrder = 1;
    for (const row of allDepartments) {
      if (Object.prototype.hasOwnProperty.call(DEPT_ORDER, row.id)) continue;
      while (usedOrders.has(nextOrder)) nextOrder += 1;
      updateOrder.run(nextOrder, row.id);
      usedOrders.add(nextOrder);
      nextOrder += 1;
    }

    try {
      db.exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_departments_sort_order ON departments(sort_order)");
    } catch (err) {
      console.warn("[Claw-Empire] Failed to recreate idx_departments_sort_order:", err);
    }

    const insertAgentIfMissing = db.prepare(
      `INSERT OR IGNORE INTO agents (id, name, name_ko, department_id, role, cli_provider, avatar_emoji, personality)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    );

    // Check which agents exist by name to avoid duplicates
    const existingNames = new Set(
      (db.prepare("SELECT name FROM agents").all() as { name: string }[]).map((r) => r.name),
    );

    const newAgents: [string, string, string, string, string, string, string][] = [
      // TradingAICenter: no legacy agents to migrate — 25 trading agents seeded separately
    ];

    let added = 0;
    for (const [name, nameKo, dept, role, provider, emoji, personality] of newAgents) {
      if (!existingNames.has(name)) {
        if (!existingDeptIds.has(dept)) {
          console.warn(`[Claw-Empire] Skip adding agent "${name}": missing department "${dept}"`);
          continue;
        }
        try {
          insertAgentIfMissing.run(randomUUID(), name, nameKo, dept, role, provider, emoji, personality);
          added++;
        } catch (err) {
          console.warn(`[Claw-Empire] Skip adding agent "${name}":`, err);
        }
      }
    }
    if (added > 0) console.log(`[Claw-Empire] Added ${added} new agents`);
  }
}
