# React Frontend — Specification

**Phase**: 8
**Status**: Implemented (retroactive spec)
**Change**: react-frontend

## Intent

Build the complete React 18 single-page application with Keycloak authentication,
three main pages (Chat, Documents, Search), WebSocket-based real-time chat, and a modern
dark-themed UI using TailwindCSS v4. The frontend communicates with the FastAPI backend via
a Vite dev-server proxy.

## Key Requirements

### REQ-8.1: Project Setup

**GIVEN** the frontend needs a modern React toolchain
**WHEN** initializing the project
**THEN** a Vite + React + TypeScript project must be created with: TailwindCSS v4
(`@tailwindcss/vite` plugin, no `tailwind.config.js`), proper TypeScript configs
(`tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`), and a Vite config with
API proxy for `/api` → `http://localhost:8000` and `/ws` → `ws://localhost:8000`.

### REQ-8.2: Keycloak Integration

**GIVEN** authentication is handled by Keycloak
**WHEN** the frontend initializes
**THEN** `keycloak.ts` must configure `keycloak-js` with PKCE (`pkceMethod: 'S256'`),
`onLoad: 'login-required'`, `checkLoginIframe: false`, automatic token refresh every 10s,
and utility functions: `getToken()`, `getUserDisplayName()`, `logout()`.

### REQ-8.3: API Client

**GIVEN** the frontend needs to communicate with the backend
**WHEN** making API calls
**THEN** `api.ts` must provide typed functions for: document upload (via `FormData`),
document listing/retrieval, chat session CRUD, session message history, and entity search.
All requests must include `Authorization: Bearer` header from the Keycloak token.

### REQ-8.4: WebSocket Manager

**GIVEN** real-time chat requires persistent WebSocket connections
**WHEN** the chat page is active
**THEN** `WebSocketManager` must: connect to `/ws/chat` with token and optional session_id
as query params, support reconnection with exponential backoff (up to 5 attempts, max 30s),
provide `onMessage()` handler registration returning an unsubscribe function, and support
`send()`, `disconnect()`, and `isConnected()` methods.

### REQ-8.5: Shared TypeScript Types

**GIVEN** the frontend and backend share data structures
**WHEN** defining TypeScript types
**THEN** `types.ts` must define interfaces matching backend Pydantic schemas:
`DocumentResponse`, `DocumentUploadResponse`, `ChatSession`, `ChatMessage`,
`EntityResponse`, `EntitySearchResult`, and `WebSocketMessage` (with `session`, `message`,
and `title_updated` types).

### REQ-8.6: Layout Component

**GIVEN** the app needs consistent navigation
**WHEN** any page is rendered
**THEN** a `Layout` component must provide a navigation bar with links to Chat, Documents,
and Search pages, plus the user's display name and a logout button.

### REQ-8.7: Chat Page

**GIVEN** users need to chat with the knowledge agent
**WHEN** navigating to the Chat page
**THEN** the page must include: a session sidebar listing existing sessions with
create/delete actions, a main chat area with message bubbles (user/assistant), markdown
rendering for assistant messages, a typing indicator while waiting for responses, and
real-time title updates from the WebSocket `title_updated` message type.

### REQ-8.8: Documents Page

**GIVEN** users need to manage documents
**WHEN** navigating to the Documents page
**THEN** the page must include: drag-and-drop file upload, a document list showing filename,
status, and stage, and processing status polling to update the list as documents progress
through the ingestion pipeline.

### REQ-8.9: Search Page

**GIVEN** users need to search the knowledge graph
**WHEN** navigating to the Search page
**THEN** the page must include: a search input with entity type filtering dropdown,
expandable result cards showing entity name, type, and properties, and result count display.

### REQ-8.10: Dark Theme

**GIVEN** the app uses a dark theme
**WHEN** styling the application
**THEN** TailwindCSS v4 custom theme variables must define dark backgrounds, appropriate
text colors, and accent colors. The `index.css` must include custom prose styles for
markdown rendering in chat and a typing animation for the indicator.

### REQ-8.11: Build Verification

**GIVEN** the frontend must be deployable
**WHEN** running `tsc -b && vite build`
**THEN** the build must succeed, producing `dist/` with `index.html` and hashed assets.

## Implementation Summary

### Files Created

- `frontend/package.json` — Dependencies: react 18, keycloak-js 26, react-markdown 9,
  react-router-dom 7, tailwindcss 4, vite 6
- `frontend/index.html` — HTML entry with dark theme body class
- `frontend/vite.config.ts` — Vite with react + tailwindcss plugins, proxy config
- `frontend/tsconfig.json` — Project references to app + node configs
- `frontend/tsconfig.app.json` — Strict TS config for src/
- `frontend/tsconfig.node.json` — TS config for vite.config.ts
- `frontend/src/index.css` — TailwindCSS v4 import, custom theme vars, prose styles
- `frontend/src/vite-env.d.ts` — Vite client type reference
- `frontend/src/main.tsx` — Keycloak init, React Router, app mount
- `frontend/src/App.tsx` — Router with Layout and page routes
- `frontend/src/components/Layout.tsx` — Navigation bar with auth
- `frontend/src/pages/ChatPage.tsx` — WebSocket chat with session sidebar
- `frontend/src/pages/DocumentsPage.tsx` — Upload + document list
- `frontend/src/pages/SearchPage.tsx` — Entity search with filters
- `frontend/src/lib/keycloak.ts` — Keycloak PKCE configuration
- `frontend/src/lib/api.ts` — Typed API client
- `frontend/src/lib/websocket.ts` — WebSocket manager with reconnection
- `frontend/src/lib/types.ts` — Shared TypeScript interfaces

### Key Patterns & Decisions

- TailwindCSS v4 uses the Vite plugin directly — no `tailwind.config.js` needed
- `checkLoginIframe: false` avoids CORS issues with Keycloak iframe checks
- WebSocket reconnection uses exponential backoff: `min(1000 * 2^attempts, 30000)ms`
- Vite proxy handles both HTTP (`/api`) and WebSocket (`/ws`) forwarding
- `keycloak-js 26` matches the Keycloak 26 server version

## Discoveries

- TailwindCSS v4 import syntax changed: use `@import "tailwindcss"` not `@tailwind` directives
- React Router v7 changed from `<Routes>` wrapper to standard component patterns
- Keycloak `checkLoginIframe: false` is required in development to avoid silent refresh issues
- Token refresh interval of 10 seconds with 30-second minimum validity works reliably
