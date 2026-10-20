/**
 * Cloudflare Pages Function / Worker for Zora AI
 * Supports:
 * - Static Asset Delivery & Clean SEO SPA Routing (via env.ASSETS)
 * - GET /api/stats (Public live counts)
 * - GET /api/verify?key=ZORA-XXXX-XXXX (Public client PC license verification)
 * - GET /api/keys (Admin: List all keys - Protected by ADMIN_PASSWORD)
 * - POST /api/keys (Admin: Create, Toggle, Delete keys with STRICT client name validation)
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

    // ─────────────────────────────────────────────────────────
    // 1. STATIC ASSETS & CLEAN SEO SPA ROUTES (HTML, PNG, ICONS)
    // ─────────────────────────────────────────────────────────
    if (!url.pathname.startsWith("/api/")) {
      if (env.ASSETS) {
        let response = await env.ASSETS.fetch(request);
        // If exact path is not a file (e.g. /home, /services, /terms-of-service, /docs, /developer)
        // and returns 404, fallback to index.html for client-side SEO router
        if (response.status === 404 && !url.pathname.includes(".")) {
          response = await env.ASSETS.fetch(new URL("/", request.url));
        }
        return response;
      }
      return new Response("Static assets binding not found", { status: 500 });
    }

    // ─────────────────────────────────────────────────────────
    // 2. PUBLIC API ENDPOINTS
    // ─────────────────────────────────────────────────────────

    // GET /api/stats
    if (url.pathname === "/api/stats" && request.method === "GET") {
      let total = 0, active = 0;
      if (env.ZORA_KEYS) {
        try {
          const list = await env.ZORA_KEYS.list();
          total = list.keys.length;
          for (const item of list.keys) {
            const val = await env.ZORA_KEYS.get(item.name, { type: "json" });
            if (val && val.active !== false) active++;
          }
        } catch (e) {}
      }
      return new Response(JSON.stringify({
        online: true,
        platform: "Cloudflare Edge",
        version: "1.7.0",
        total: total || 1,
        active: active || 1
      }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // GET /api/verify?key=...
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
          return new Response(JSON.stringify({ valid: false, error: "License key is revoked or suspended" }), {
            status: 403,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
        return new Response(JSON.stringify({ valid: true, client: keyData.client, plan: keyData.plan }), {
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      return new Response(JSON.stringify({ valid: false, error: "License key not found in registry" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" }
      });
    }

    // ─────────────────────────────────────────────────────────
    // 3. ADMIN API ENDPOINTS (PROTECTED BY ADMIN_PASSWORD)
    // ─────────────────────────────────────────────────────────
    if (url.pathname === "/api/keys") {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace("Bearer ", "").trim();

      if (token !== ADMIN_PASSWORD) {
        return new Response(JSON.stringify({ error: "Unauthorized: Invalid admin credentials" }), {
          status: 401,
          headers: { ...corsHeaders, "Content-Type": "application/json" }
        });
      }

      // GET /api/keys
      if (request.method === "GET") {
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
      if (request.method === "POST") {
        try {
          const body = await request.json();
          const { action, client, plan, key, active } = body;

          if (action === "create") {
            if (!client || !client.trim() || client.trim().length < 2) {
              return new Response(JSON.stringify({
                success: false,
                error: "Client / User Name is strictly required (minimum 2 characters)!"
              }), {
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
              created_at: new Date().toLocaleDateString("en-GB")
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
                existing.active = Boolean(active);
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

          return new Response(JSON.stringify({ error: "Invalid action request" }), {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        } catch (err) {
          return new Response(JSON.stringify({ error: "Malformed JSON payload" }), {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" }
          });
        }
      }
    }

    return new Response(JSON.stringify({ error: "Endpoint not found" }), {
      status: 404,
      headers: { ...corsHeaders, "Content-Type": "application/json" }
    });
  }
};
