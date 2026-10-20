/**
 * Cloudflare Pages Function / Worker for Zora AI
 * Supports:
 * - GET /api/stats (Public live counts)
 * - GET /api/verify?key=ZORA-XXXX-XXXX (Used by client PC to verify license)
 * - GET /api/keys (Admin: List all keys)
 * - POST /api/keys (Admin: Create, Toggle, Delete keys with STRICT name validation)
 */

const DEFAULT_ADMIN_PASS = "zora2026admin";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ADMIN_PASSWORD = env.ADMIN_PASSWORD || DEFAULT_ADMIN_PASS;

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // 0. PUBLIC STATS: /api/stats
    if (url.pathname === "/api/stats" && request.method === "GET") {
      return new Response(JSON.stringify({ online: true, platform: "Cloudflare Edge", version: "1.7.0" }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // 1. CLIENT VERIFICATION ENDPOINT: /api/verify?key=...
    if (url.pathname === "/api/verify" && request.method === "GET") {
      const key = url.searchParams.get("key");
      if (!key) {
        return new Response(JSON.stringify({ valid: false, error: "Missing key parameter" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      let keyData = null;
      if (env.ZORA_KEYS) {
        keyData = await env.ZORA_KEYS.get(key, { type: "json" });
      }

      if (keyData) {
        if (!keyData.active) {
          return new Response(JSON.stringify({ valid: false, error: "License key is revoked / inactive" }), {
            status: 403,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        return new Response(JSON.stringify({ valid: true, client: keyData.client, plan: keyData.plan }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      return new Response(JSON.stringify({ valid: false, error: "License key not found" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // 2. ADMIN ENDPOINTS REQUIRE AUTHENTICATION
    const authHeader = request.headers.get("Authorization") || "";
    const token = authHeader.replace("Bearer ", "").trim();
    if (token !== ADMIN_PASSWORD) {
      return new Response(JSON.stringify({ error: "Unauthorized: Invalid admin credentials" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /api/keys
    if (url.pathname === "/api/keys" && request.method === "GET") {
      if (!env.ZORA_KEYS) {
        return new Response(JSON.stringify({}), {
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
      const list = await env.ZORA_KEYS.list();
      const allKeys = {};
      for (const item of list.keys) {
        const val = await env.ZORA_KEYS.get(item.name, { type: "json" });
        if (val) allKeys[item.name] = val;
      }
      return new Response(JSON.stringify(allKeys), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // POST /api/keys
    if (url.pathname === "/api/keys" && request.method === "POST") {
      try {
        const body = await request.json();
        const { action, client, plan, key, active } = body;

        if (action === "create") {
          // STRICT VALIDATION: Cannot create key without client name!
          if (!client || !client.trim()) {
            return new Response(JSON.stringify({ success: false, error: "Client / User Name is strictly required to generate a key!" }), {
              status: 400,
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }

          const seg = () => Math.random().toString(36).substring(2, 6).toUpperCase();
          const newKey = `ZORA-${seg()}-${seg()}-${seg()}`;
          const newRecord = {
            client: client.trim(),
            plan: plan || "Lifetime Pro",
            active: true,
            created_at: new Date().toISOString()
          };

          if (env.ZORA_KEYS) {
            await env.ZORA_KEYS.put(newKey, JSON.stringify(newRecord));
          }

          return new Response(JSON.stringify({ success: true, key: newKey, info: newRecord }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }

        if (action === "toggle" && key) {
          if (env.ZORA_KEYS) {
            const existing = await env.ZORA_KEYS.get(key, { type: "json" });
            if (existing) {
              existing.active = active;
              await env.ZORA_KEYS.put(key, JSON.stringify(existing));
            }
          }
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }

        if (action === "delete" && key) {
          if (env.ZORA_KEYS) {
            await env.ZORA_KEYS.delete(key);
          }
          return new Response(JSON.stringify({ success: true }), {
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }

        return new Response(JSON.stringify({ error: "Invalid action" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: "Bad Request" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders });
  }
};
