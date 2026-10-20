# Zora AI — Studio Web Dashboard & Documentation Portal

Official web application, documentation center, and cryptographic license management dashboard for **Zora AI**, engineered by **MD NION** ([AP Development](https://github.com/nion69)).

---

## Features

- **Clean SEO URL Architecture**: Dedicated semantic routes with full HTML5 `history.pushState` & `popstate` support:
  - `/home` — Overview, WebRTC telemetry, and capabilities
  - `/services` — Voice intelligence & automation services
  - `/installation` — Setup and quickstart guide for Windows 10/11
  - `/docs` — Technical documentation, CLI commands, and voice protocols
  - `/architecture` — Engine architecture & sub-second audio pipeline
  - `/privacy-policy` — Ephemeral real-time voice processing guarantees
  - `/terms-of-service` — Official terms, conditions & license agreement
  - `/developer` — MD NION (AP Development) developer profile & bio
  - `/admin` — Enterprise license provisioning & key registry *(role-protected)*
- **Sub-Second Telemetry UI**: Realtime latency metrics, active status pulse, and studio aesthetics.
- **Protected Authentication**:
  - One-click Google Sign-In & Email/Password authentication
  - Client-side cooldown rate limiter (5 failed attempts locks for 60s)
  - Firebase Firestore integration with Role-Based Access Control (RBAC)
- **Hardened Security**:
  - Anti-injection validation against SQL, XML/XXE, XSS, and command injections
  - IP-based rate limiting (25 requests/min per IP)
- **Deployment Ready**:
  - Local Node.js test server with static streaming & SPA route fallbacks
  - Cloudflare Pages Worker (`_worker.js`) for edge global deployments

---

## Getting Started

### Local Development (Node.js)

1. Ensure Node.js (v18+) is installed.
2. Start the local server:
   ```bash
   node server.js
   ```
3. Open your browser at:
   ```
   http://localhost:3000
   ```

### Cloudflare Pages / Edge Deployment

Deploy to Cloudflare Pages with zero configuration:
- Build output directory: `/`
- Functions / Worker script: `_worker.js`
- Set `ADMIN_PASSWORD` in your Cloudflare Pages environment variables.

---

## File Structure

```
├── index.html               # Main website UI, tab views, auth modals & SEO routing
├── server.js                # Node.js local test server with static streaming & rate limits
├── _worker.js               # Cloudflare Pages Edge Worker
├── logo.png                 # Official brand logo
├── ownerpic.png             # Developer portrait for MD NION
├── firestore.rules          # Hardened Firebase Firestore security rules
├── FIRESTORE_RULES_GUIDE.md # Instructions for deploying Firestore rules
└── README.md                # Project documentation
```

---

## Developer Information

- **Creator & Lead Engineer**: MD NION
- **Studio**: AP Development
- **Experience**: 7+ years developing high-performance Discord bots, Minecraft plugins, desktop systems, and web apps.

---

## License

Copyright © 2026 Zora AI • AP Development. Engineered exclusively by MD NION. All rights reserved.
