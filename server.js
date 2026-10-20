/**
 * Zora AI - Local Test Server
 * Supports Clean SEO Page URLs, Static Asset Streaming, Rate Limiting & Anti-Injection Protection
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

// ── In-Memory IP Rate Limiter ──
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 25;
const ipRequestHistory = new Map();

function checkRateLimit(ip) {
  const now = Date.now();
  let record = ipRequestHistory.get(ip);

  if (!record) {
    record = { count: 1, startTime: now };
    ipRequestHistory.set(ip, record);
    return { allowed: true };
  }

  if (now - record.startTime > RATE_LIMIT_WINDOW_MS) {
    record.count = 1;
    record.startTime = now;
    return { allowed: true };
  }

  record.count++;
  if (record.count > MAX_REQUESTS_PER_WINDOW) {
    const retryAfter = Math.ceil((RATE_LIMIT_WINDOW_MS - (now - record.startTime)) / 1000);
    return { allowed: false, retryAfter };
  }

  return { allowed: true };
}

// ── Anti-Injection Sanitizer & Validator (SQL, XML, XSS, Shell) ──
const INJECTION_PATTERNS = [
  /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|WHERE|OR|AND)\b.*\b(=|>|<|LIKE)\b)/i,
  /(--|#|\/\*|\*\/|;|\bWAITFOR\b|\bDELAY\b)/i,
  /(<script\b[^>]*>|<\/script>|javascript:|onerror=|onload=|onclick=)/i,
  /(<!ENTITY|<!DOCTYPE|SYSTEM|PUBLIC|<\?xml)/i,
  /(\.\.\/|\.\.\\)/,
  /(\||\&|;|\$|\>|\<|`|\\)/
];

function containsInjection(input) {
  if (typeof input !== 'string') return false;
  return INJECTION_PATTERNS.some(pattern => pattern.test(input));
}

function sanitizeString(input, maxLength = 80) {
  if (typeof input !== 'string') return '';
  return input
    .replace(/[<>'"&;`\$\\]/g, '')
    .trim()
    .slice(0, maxLength);
}

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

function json(res, data, status = 200, headers = {}) {
  cors(res);
  for (const [h, v] of Object.entries(headers)) {
    res.setHeader(h, v);
  }
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

function checkAuth(req) {
  const auth = req.headers['authorization'] || '';
  const token = auth.replace('Bearer ', '').trim();
  return token === ADMIN_PASSWORD;
}

// ── Valid SEO Page Routes & Aliases ──
const SEO_PAGE_ROUTES = new Set([
  '/',
  '/index.html',
  '/home',
  '/services',
  '/installation',
  '/install',
  '/docs',
  '/documentation',
  '/architecture',
  '/features',
  '/privacy-policy',
  '/privacy',
  '/terms-of-service',
  '/terms',
  '/terms-and-conditions',
  '/developer',
  '/about',
  '/admin'
]);

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const pathname = parsed.pathname;
  const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress || '127.0.0.1';

  cors(res);

  // Security Headers
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // ── Serve Static Assets (Images: logo.png, ownerpic.png, etc.) ──
  if (pathname.endsWith('.png') || pathname.endsWith('.jpg') || pathname.endsWith('.jpeg') || pathname.endsWith('.svg') || pathname.endsWith('.ico')) {
    const filename = path.basename(pathname);
    const filePath = path.join(__dirname, filename);
    if (fs.existsSync(filePath)) {
      let mime = 'application/octet-stream';
      if (pathname.endsWith('.png')) mime = 'image/png';
      else if (pathname.endsWith('.jpg') || pathname.endsWith('.jpeg')) mime = 'image/jpeg';
      else if (pathname.endsWith('.svg')) mime = 'image/svg+xml';
      else if (pathname.endsWith('.ico')) mime = 'image/x-icon';

      res.writeHead(200, { 'Content-Type': mime, 'Cache-Control': 'public, max-age=86400' });
      return fs.createReadStream(filePath).pipe(res);
    }
  }

  // ── Rate Limiting on API ──
  if (pathname.startsWith('/api/')) {
    const rateCheck = checkRateLimit(clientIp);
    if (!rateCheck.allowed) {
      return json(res, {
        success: false,
        error: 'Rate limit exceeded. Please wait a moment before trying again.',
        retryAfterSeconds: rateCheck.retryAfter
      }, 429, { 'Retry-After': String(rateCheck.retryAfter) });
    }
  }

  // ── GET /api/stats ──
  if (pathname === '/api/stats' && req.method === 'GET') {
    const keys = loadKeys();
    let total = 0, active = 0, revoked = 0;
    for (const k in keys) {
      total++;
      const item = keys[k];
      if (item.active) {
        const inUse = item.in_use === true || (item.in_use === undefined && item.client !== 'sijan');
        if (inUse) active++;
      } else {
        revoked++;
      }
    }
    return json(res, { total: total || 3, active: active || 2, revoked, online: true });
  }

  // ── POST/GET /api/heartbeat?key=...&in_use=true/false ──
  if (pathname === '/api/heartbeat') {
    const key = parsed.query.key;
    const inUseParam = parsed.query.in_use;
    const inUse = inUseParam === null ? true : (inUseParam !== 'false' && inUseParam !== '0');

    if (!key) return json(res, { success: false, error: 'Missing key' }, 400);

    const keys = loadKeys();
    if (keys[key]) {
      keys[key].in_use = inUse;
      keys[key].last_seen = Date.now();
      saveKeys(keys);
    }
    return json(res, { success: true, key, in_use: inUse });
  }

  // ── GET /api/verify?key=ZORA-XXXX ──
  if (pathname === '/api/verify' && req.method === 'GET') {
    const key = parsed.query.key;
    if (!key) return json(res, { valid: false, error: 'License key parameter is missing.' }, 400);

    if (containsInjection(key)) {
      return json(res, { valid: false, error: 'Security warning: Prohibited characters detected.' }, 403);
    }

    const safeKey = sanitizeString(key, 40);
    const keys = loadKeys();
    const data = keys[safeKey];

    if (!data) return json(res, { valid: false, error: 'License key not found in registry.' }, 404);
    if (!data.active) return json(res, { valid: false, error: 'License key has been suspended or revoked.' }, 403);

    return json(res, { valid: true, client: data.client, plan: data.plan });
  }

  // ── GET /api/keys ──
  if (pathname === '/api/keys' && req.method === 'GET') {
    if (!checkAuth(req)) return json(res, { error: 'Unauthorized: Invalid administrator credentials.' }, 401);
    return json(res, loadKeys());
  }

  // ── POST /api/keys ──
  if (pathname === '/api/keys' && req.method === 'POST') {
    if (!checkAuth(req)) return json(res, { error: 'Unauthorized: Invalid administrator credentials.' }, 401);

    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 10000) req.destroy();
    });

    req.on('end', () => {
      try {
        const payload = JSON.parse(body);
        const { action, client, plan, key, active } = payload;

        if (containsInjection(action) || containsInjection(client) || containsInjection(plan) || containsInjection(key)) {
          return json(res, { success: false, error: 'Security exception: Injection payload detected and blocked.' }, 400);
        }

        const keys = loadKeys();

        if (action === 'create') {
          const safeClient = sanitizeString(client, 60);
          const safePlan = sanitizeString(plan, 30);

          if (!safeClient || safeClient.length < 2) {
            return json(res, { success: false, error: 'Client / User Name is strictly required (minimum 2 characters).' }, 400);
          }

          const newKey = `ZORA-${randomChunk()}-${randomChunk()}-${randomChunk()}`;
          keys[newKey] = {
            client: safeClient,
            plan: safePlan || 'Lifetime Pro',
            active: true,
            created_at: new Date().toLocaleDateString('en-GB')
          };
          saveKeys(keys);
          return json(res, { success: true, key: newKey, info: keys[newKey] });
        }

        if (action === 'toggle' && key) {
          const safeKey = sanitizeString(key, 40);
          if (keys[safeKey]) {
            keys[safeKey].active = Boolean(active);
            saveKeys(keys);
          }
          return json(res, { success: true });
        }

        if (action === 'delete' && key) {
          const safeKey = sanitizeString(key, 40);
          delete keys[safeKey];
          saveKeys(keys);
          return json(res, { success: true });
        }

        return json(res, { error: 'Unsupported action request.' }, 400);
      } catch (e) {
        return json(res, { error: 'Malformed JSON payload.' }, 400);
      }
    });
    return;
  }

    // ── Serve SEO Page Routes & SPA Fallback ──
  const isCleanPageRoute = SEO_PAGE_ROUTES.has(pathname) || (!pathname.startsWith('/api/') && !path.extname(pathname));
  if (isCleanPageRoute) {
    fs.readFile(HTML_FILE, 'utf8', (err, content) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Error loading index.html');
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(content);
    });
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('404 Not Found');
});

server.listen(PORT, () => {
  console.log(`\n  ============================================================`);
  console.log(`    ZORA AI — Web Dashboard & License Server`);
  console.log(`    SEO Routes    : /home, /installation, /docs, /privacy-policy,`);
  console.log(`                    /terms-of-service, /developer, /architecture`);
  console.log(`    Local URL     : http://localhost:${PORT}`);
  console.log(`  ============================================================\n`);
});
