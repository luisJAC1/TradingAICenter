/**
 * Brain Integration Routes
 *
 * Endpoints called by the Python Brain (UIBridge) to push agent state
 * changes and Knowledge Bus events into the Claw-Empire pixel office.
 *
 * POST /api/brain/agent-status  — update an agent's status + current_task
 * POST /api/brain/bus-event     — broadcast a raw bus event to all UI clients
 */

import type { RuntimeContext } from "../../../../types/runtime-context.ts";

// Map Python Brain AgentStatus → Claw-Empire DB status values
const BRAIN_TO_UI_STATUS: Record<string, string> = {
  idle: "idle",
  working: "working",
  thinking: "working",
  sending: "working",
  waiting: "working",
  error: "idle",
  paused: "offline",
};

export function registerBrainIntegrationRoutes(ctx: RuntimeContext): void {
  const { app, db, broadcast } = ctx;

  /**
   * POST /api/brain/agent-status
   *
   * Body: { agent_id: string, status: string, current_task?: string }
   *
   * Finds the matching DB agent by brain agent_id (stored in `name` or
   * matched via a brain_agent_id column if we add one later). For now we
   * match on `name` case-insensitively OR on agent `id` directly, whichever
   * works first — allowing zero-config wiring while we seed the 26 agents.
   */
  app.post("/api/brain/agent-status", (req, res) => {
    try {
      const body = (req.body ?? {}) as Record<string, unknown>;
      const brainAgentId = typeof body.agent_id === "string" ? body.agent_id.trim() : "";
      const rawStatus = typeof body.status === "string" ? body.status.trim().toLowerCase() : "idle";
      const currentTask = typeof body.current_task === "string" ? body.current_task.trim() : null;

      if (!brainAgentId) {
        return res.status(400).json({ error: "agent_id_required" });
      }

      const uiStatus = BRAIN_TO_UI_STATUS[rawStatus] ?? "idle";

      // Try to find the agent: exact id match first, then name match
      let agent = db
        .prepare("SELECT * FROM agents WHERE id = ? LIMIT 1")
        .get(brainAgentId) as Record<string, unknown> | undefined;

      if (!agent) {
        agent = db
          .prepare("SELECT * FROM agents WHERE LOWER(name) = LOWER(?) LIMIT 1")
          .get(brainAgentId) as Record<string, unknown> | undefined;
      }

      // Also try with hyphens replaced by spaces: "mood-ring" → "Mood Ring"
      if (!agent) {
        const nameWithSpaces = brainAgentId.replace(/-/g, " ");
        agent = db
          .prepare("SELECT * FROM agents WHERE LOWER(name) = LOWER(?) LIMIT 1")
          .get(nameWithSpaces) as Record<string, unknown> | undefined;
      }

      if (!agent) {
        return res.json({ ok: true, matched: false, agent_id: brainAgentId });
      }

      const agentId = String(agent.id);

      // Update status + current_task (column added by trading migration)
      try {
        db.prepare("UPDATE agents SET status = ?, current_task = ? WHERE id = ?").run(
          uiStatus,
          currentTask,
          agentId,
        );
      } catch {
        db.prepare("UPDATE agents SET status = ? WHERE id = ?").run(uiStatus, agentId);
      }

      const updated = db.prepare("SELECT * FROM agents WHERE id = ?").get(agentId);
      broadcast("agent_status", updated);

      return res.json({ ok: true, matched: true, agent_id: agentId, status: uiStatus });
    } catch (err) {
      console.error("[brain-integration] agent-status error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * POST /api/brain/bus-event
   *
   * Body: full BusMessage JSON from the Python Brain's Knowledge Bus.
   *
   * Stores recent events in brain_bus_events for the UI feed and broadcasts
   * verbatim to all connected WebSocket clients for live updates.
   */
  app.post("/api/brain/bus-event", (req, res) => {
    try {
      const body = (req.body ?? {}) as Record<string, unknown>;

      if (!body.message_id || !body.from_agent) {
        return res.status(400).json({ error: "invalid_bus_message" });
      }

      try {
        db.prepare(
          `INSERT INTO brain_bus_events (message_id, from_agent, category, type, tickers, confidence, summary)
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
        ).run(
          String(body.message_id),
          String(body.from_agent),
          typeof body.category === "string" ? body.category : null,
          typeof body.type === "string" ? body.type : null,
          Array.isArray(body.tickers) ? JSON.stringify(body.tickers) : null,
          typeof body.confidence === "number" ? body.confidence : 0,
          typeof body.summary === "string" ? body.summary : null,
        );
      } catch (err) {
        console.warn("[brain-integration] bus-event insert failed:", err);
      }

      // Trim to most recent 500 events to keep DB lean
      try {
        db.exec(
          `DELETE FROM brain_bus_events WHERE id NOT IN (SELECT id FROM brain_bus_events ORDER BY id DESC LIMIT 500)`,
        );
      } catch {
        /* best effort */
      }

      broadcast("bus_event", body);
      return res.json({ ok: true });
    } catch (err) {
      console.error("[brain-integration] bus-event error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * POST /api/brain/decision-inbox
   *
   * Body: { from_agent, ticker, message, raw_plan, confidence, tickers, timestamp }
   *
   * Stores a pending trade signal so the user can approve/reject from the UI.
   */
  app.post("/api/brain/decision-inbox", (req, res) => {
    try {
      const body = (req.body ?? {}) as Record<string, unknown>;
      const fromAgent = typeof body.from_agent === "string" ? body.from_agent : "";
      if (!fromAgent) return res.status(400).json({ error: "from_agent_required" });

      const id = `dec_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      db.prepare(
        `INSERT INTO brain_decisions (id, from_agent, ticker, message, raw_plan, confidence, tickers, status)
         VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')`,
      ).run(
        id,
        fromAgent,
        typeof body.ticker === "string" ? body.ticker : null,
        typeof body.message === "string" ? body.message : null,
        body.raw_plan ? JSON.stringify(body.raw_plan) : null,
        typeof body.confidence === "number" ? body.confidence : 0,
        Array.isArray(body.tickers) ? JSON.stringify(body.tickers) : null,
      );

      const row = db.prepare("SELECT * FROM brain_decisions WHERE id = ?").get(id);
      broadcast("brain_decision", row);

      return res.json({ ok: true, id });
    } catch (err) {
      console.error("[brain-integration] decision-inbox error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * GET /api/brain/decisions
   *
   * Returns recent brain decisions. Query: ?status=pending|all (default: pending)
   */
  app.get("/api/brain/decisions", (req, res) => {
    try {
      const status = typeof req.query?.status === "string" ? req.query.status : "pending";
      const limit = Math.min(Number(req.query?.limit ?? 100), 500);
      const rows = (status === "all"
        ? db.prepare("SELECT * FROM brain_decisions ORDER BY created_at DESC LIMIT ?").all(limit)
        : db
            .prepare("SELECT * FROM brain_decisions WHERE status = ? ORDER BY created_at DESC LIMIT ?")
            .all(status, limit)) as Array<Record<string, unknown>>;
      return res.json({ decisions: rows });
    } catch (err) {
      console.error("[brain-integration] decisions list error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * POST /api/brain/decisions/:id/respond
   *
   * Body: { action: 'approve' | 'reject' }
   * Marks a decision as approved/rejected and forwards approval to the brain.
   */
  app.post("/api/brain/decisions/:id/respond", async (req, res) => {
    try {
      const id = req.params.id;
      const action = (req.body as Record<string, unknown>)?.action;
      if (action !== "approve" && action !== "reject") {
        return res.status(400).json({ error: "action_must_be_approve_or_reject" });
      }
      const newStatus = action === "approve" ? "approved" : "rejected";
      const row = db.prepare("SELECT * FROM brain_decisions WHERE id = ?").get(id) as
        | Record<string, unknown>
        | undefined;
      if (!row) return res.status(404).json({ error: "not_found" });

      db.prepare(
        "UPDATE brain_decisions SET status = ?, decided_at = ? WHERE id = ?",
      ).run(newStatus, Date.now(), id);

      // Forward to brain so the Trigger agent can act
      const brainUrl = process.env.BRAIN_URL ?? "http://trading-brain:8791";
      try {
        await fetch(`${brainUrl}/api/brain/approval`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ decision_id: id, action, ticker: row.ticker }),
        });
      } catch (err) {
        console.warn("[brain-integration] brain approval forward failed:", err);
      }

      const updated = db.prepare("SELECT * FROM brain_decisions WHERE id = ?").get(id);
      broadcast("brain_decision_update", updated);
      return res.json({ ok: true, decision: updated });
    } catch (err) {
      console.error("[brain-integration] respond error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * GET /api/brain/bus-events
   *
   * Returns recent bus events for the UI feed.
   */
  app.get("/api/brain/bus-events", (req, res) => {
    try {
      const limit = Math.min(Number(req.query?.limit ?? 50), 500);
      const rows = db
        .prepare("SELECT * FROM brain_bus_events ORDER BY id DESC LIMIT ?")
        .all(limit);
      return res.json({ events: rows });
    } catch (err) {
      console.error("[brain-integration] bus-events list error:", err);
      return res.status(500).json({ error: "internal_error" });
    }
  });

  /**
   * GET /api/brain/status
   *
   * Aggregated brain health for UI dashboard.
   */
  app.get("/api/brain/status", async (_req, res) => {
    const brainUrl = process.env.BRAIN_URL ?? "http://trading-brain:8791";
    try {
      const r = await fetch(`${brainUrl}/health`);
      const data = (await r.json()) as Record<string, unknown>;
      const pending = (db
        .prepare("SELECT COUNT(*) as cnt FROM brain_decisions WHERE status = 'pending'")
        .get() as { cnt: number }).cnt;
      return res.json({ ...data, pending_decisions: pending });
    } catch (err) {
      return res.status(503).json({ error: "brain_unreachable", detail: String(err) });
    }
  });
}
