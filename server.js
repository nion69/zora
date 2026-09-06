/**
 * Zora AI - Local Test Server
 * Mimics the Cloudflare Worker API using Node.js built-in http module
 * No npm install needed — uses only Node.js built-ins
 * Run: node server.js
 * Open: http://localhost:3000
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 3000;
const ADMIN_PASSWORD = 'zora2026admin';
const KEYS_FILE = path.join(__dirname, 'keys.json');
const HTML_FILE = path.join(__dirname, 'index.html');

// Load or init keys store
function loadKeys() {
  try {
    if (fs.existsSync(KEYS_FILE)) {
      return JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8'));
    }
  } catch (e) {}
  return {};
}

function saveKeys(keys) {
  fs.writeFileSync(KEYS_FILE, JSON.stringify(keys, null, 2), 'utf8');
}

function randomChunk() {
  return Math.random().toString(36).substring(2, 6).toUpperCase();
}

function cors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

function json(res, data, status = 200) {
  cors(res);
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function checkAuth(req) {
  const auth = req.headers['authorization'] || '';
  const token = auth.replace('Bearer ', '').trim();
  return token === ADMIN_PASSWORD;
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const pathname = parsed.pathname;

  cors(res);

  // OPTIONS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // ── GET /api/verify?key=ZORA-XXXX ──────────────────────
  if (pathname === '/api/verify' && req.method === 'GET') {
    const key = parsed.query.key;
    if (!key) return json(res, { valid: false, error: 'Missing key' }, 400);

    const keys = loadKeys();
    const data = keys[key];

    if (!data) return json(res, { valid: false, error: 'License key not found' }, 404);
    if (!data.active) return json(res, { valid: false, error: 'License key is revoked' }, 403);

    return json(res, { valid: true, client: data.client, plan: data.plan });
  }

  // ── GET /api/keys ── list all keys (admin) ──────────────
  if (pathname === '/api/keys' && req.method === 'GET') {
    if (!checkAuth(req)) return json(res, { error: 'Unauthorized' }, 401);
    return json(res, loadKeys());
  }

  // ── POST /api/keys ── create / toggle / delete ──────────
  if (pathname === '/api/keys' && req.method === 'POST') {
    if (!checkAuth(req)) return json(res, { error: 'Unauthorized' }, 401);

    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const { action, client, plan, key, active } = JSON.parse(body);
        const keys = loadKeys();

        if (action === 'create') {
          const newKey = `ZORA-${randomChunk()}-${randomChunk()}-${randomChunk()}`;
          keys[newKey] = {
            client: client || 'Client',
            plan: plan || 'Lifetime Pro',
            active: true,
            created_at: new Date().toLocaleDateString('en-GB')
          };
          saveKeys(keys);
          return json(res, { success: true, key: newKey, info: keys[newKey] });
        }

        if (action === 'toggle' && key) {
          if (keys[key]) { keys[key].active = active; saveKeys(keys); }
          return json(res, { success: true });
        }

        if (action === 'delete' && key) {
          delete keys[key]; saveKeys(keys);
          return json(res, { success: true });
        }

        return json(res, { error: 'Invalid action' }, 400);
      } catch (e) {
        return json(res, { error: e.message }, 500);
      }
    });
    return;
  }

  // ── Serve index.html ────────────────────────────────────
  if (pathname === '/' || pathname === '/index.html') {
    try {
      const html = fs.readFileSync(HTML_FILE, 'utf8');
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(html);
    } catch (e) {
      res.writeHead(404); res.end('index.html not found');
    }
    return;
  }

  res.writeHead(404); res.end('Not found');
});

server.listen(PORT, () => {
  console.log('');
  console.log('  ╔══════════════════════════════════════╗');
  console.log('  ║     ZORA AI — Local Test Server      ║');
  console.log('  ╠══════════════════════════════════════╣');
  console.log(`  ║  Dashboard : http://localhost:${PORT}    ║`);
  console.log(`  ║  Password  : ${ADMIN_PASSWORD}          ║`);
  console.log('  ║  Keys file : keys.json               ║');
  console.log('  ╚══════════════════════════════════════╝');
  console.log('');
  console.log('  Press Ctrl+C to stop.');
  console.log('');
});
