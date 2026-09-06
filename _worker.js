/**
 * Cloudflare Pages Function / Worker for Zora AI
 * Supports:
 * - GET /api/verify?key=ZORA-XXXX-XXXX (Used by client PC to verify license)
 * - GET /api/keys (Admin: List all keys)
 * - POST /api/keys (Admin: Create, Toggle, Delete keys)
 */

// Default admin password if not set in Cloudflare Environment variables
const DEFAULT_ADMIN_PASS = "zora2026admin";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const ADMIN_PASSWORD = env.ADMIN_PASSWORD || DEFAULT_ADMIN_PASS;

    // Helper for CORS
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
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

      // Read from Cloudflare KV (or in-memory mock if KV not bound)
      let keyData = null;
      if (env.ZORA_KEYS) {
        keyData = await env.ZORA_KEYS.get(key, { type: "json" });
      }

      // Default demo key for testing if KV is empty
      if (!keyData && key === "ZORA-TEST-PRO-2026") {
        keyData = { client: "Tester", plan: "Pro", active: true, created_at: "2026-09-06" };
      }

      if (!keyData) {
        return new Response(JSON.stringify({ valid: false, error: "License key not found" }), {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      if (!keyData.active) {
        return new Response(JSON.stringify({ valid: false, error: "License key has been revoked or expired" }), {
          status: 403,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      return new Response(JSON.stringify({
        valid: true,
        client: keyData.client,
        plan: keyData.plan
      }), {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // 2. ADMIN ENDPOINTS: /api/keys
    if (url.pathname === "/api/keys") {
      // Check Admin Authorization
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace("Bearer ", "").trim();
      if (token !== ADMIN_PASSWORD) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      // GET: List all keys
      if (request.method === "GET") {
        let keysObj = {};
        if (env.ZORA_KEYS) {
          const list = await env.ZORA_KEYS.list();
          for (const k of list.keys) {
            const data = await env.ZORA_KEYS.get(k.name, { type: "json" });
            if (data) keysObj[k.name] = data;
          }
        } else {
          // Demo fallback
          keysObj["ZORA-TEST-PRO-2026"] = { client: "Demo User", plan: "Lifetime Pro", active: true, created_at: "2026-09-06" };
        }

        return new Response(JSON.stringify(keysObj), {
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      // POST: Create / Toggle / Delete
      if (request.method === "POST") {
        try {
          const body = await request.json();
          const { action, client, plan, key, active } = body;

          if (action === "create") {
            // Generate random key: ZORA-XXXX-XXXX-XXXX
            const randomChunk = () => Math.random().toString(36).substring(2, 6).toUpperCase();
            const newKey = `ZORA-${randomChunk()}-${randomChunk()}-${randomChunk()}`;
            const keyInfo = {
              client: client || "Client",
              plan: plan || "Pro",
              active: true,
              created_at: new Date().toLocaleDateString()
            };

            if (env.ZORA_KEYS) {
              await env.ZORA_KEYS.put(newKey, JSON.stringify(keyInfo));
            }

            return new Response(JSON.stringify({ success: true, key: newKey, info: keyInfo }), {
              headers: { ...corsHeaders, "Content-Type": "application/json" }
            });
          }

          if (action === "toggle") {
            if (env.ZORA_KEYS && key) {
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

          if (action === "delete") {
            if (env.ZORA_KEYS && key) {
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
          return new Response(JSON.stringify({ error: err.message }), {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
      }
    }

    // Default static file fallback
    return env.ASSETS ? env.ASSETS.fetch(request) : new Response("Not found", { status: 404 });
  }
};
