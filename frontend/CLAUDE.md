# Frontend Development

## Stack

- React 18 with Carbon Design System (IBM)
- Vite for dev server (HMR), npm for package management
- axios for API calls (`src/services/apiClient.ts`)
- WebSocket client: `src/services/websocketClient.ts`

## Patterns

- Components in `src/components/` grouped by feature (e.g., `search/`)
- Services in `src/services/` for API and external communication
- Types in `src/types/` for TypeScript definitions
- CSS modules co-located with components

## Commands

- Dev server: `npm run dev` (port 3000, Vite HMR)
- Install: `npm install`
- Lint: ESLint (`07-frontend-lint.yml` in CI)
- Backend URL: `REACT_APP_API_URL` environment variable
