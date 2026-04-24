---
title: Control Panel Real Data Implementation
status: active
created: 2026-04-24
origin: user request
scope: phases 1-2 first
---

# Control Panel Real Data Implementation

## Problem

The Vue control panel currently has route/page scaffolding and some store behavior, but many pages still render fallback/demo data. The backend exposes mutation endpoints for core workflows but lacks query APIs needed by the control panel to load dashboard, opportunity, run, Agent, notification, audit, and customer data.

## Scope

This plan turns the control panel into a usable local development surface. The first implementation pass covers:

- Phase 1: backend query APIs.
- Phase 2: frontend API/store real-data wiring.

Later UI page conversion is intentionally separate after the data layer is in place.

## Phase 1: Backend Query APIs

### Files

- `src/opportunity_crawler/control_plane/app.py`
- `tests/integration/test_control_panel_queries.py`
- Existing service modules under `src/opportunity_crawler/control_plane/services/` if query logic becomes too large for `app.py`.

### API Endpoints

- `GET /api/dashboard/summary`
- `GET /api/opportunities`
- `GET /api/opportunities/{id}`
- `GET /api/collection-runs`
- `GET /api/agents`
- `GET /api/notifications/logs`
- `GET /api/audit-logs`
- `GET /api/customers`
- `GET /api/sources/{id}`
- `GET /api/sources/{id}/advanced-rules`

### Decisions

- Reuse the current monolithic `create_app()` route style for this phase to avoid introducing a router refactor while the app already defines all active endpoints there.
- Use the existing token/permission helpers for every query endpoint. Read-only endpoints require an authenticated user unless a stricter existing permission clearly applies.
- Return JSON objects with stable `items` arrays for list endpoints and detail objects for entity endpoints.
- Include enough related data for the frontend to avoid immediate N+1 follow-up calls: opportunity detail should include source, evidence, and analysis.
- Keep pagination lightweight in this phase with `limit` and `offset` query params where lists may grow.

### Test Scenarios

- Authenticated users can load dashboard summary from real SQLite data.
- Unauthenticated users receive `401` for control panel query APIs.
- Opportunity list supports `review_status` filtering and returns source names.
- Opportunity detail includes source, evidence, and analysis payloads.
- Source detail includes basic rules and active advanced rule summary.
- Advanced rule versions list returns draft/active versions in newest-first order.
- Collection run, Agent, notification log, audit log, and customer list endpoints return real rows.
- Missing opportunity/source detail returns `404`.

## Phase 2: Frontend API/Store Wiring

### Files

- `frontend/src/stores/dashboard.ts`
- `frontend/src/stores/opportunities.ts`
- `frontend/src/stores/sources.ts`
- `frontend/src/stores/runtime.ts`
- `frontend/src/stores/customers.ts`
- `frontend/src/stores/notifications.ts`
- `frontend/src/stores/audit.ts`
- `frontend/src/stores/agents.ts`
- `frontend/src/stores/goals.ts`
- `frontend/src/tests/*.test.ts`

### Decisions

- Keep API access centralized through `frontend/src/api/client.ts`.
- Stores own loading/error state and normalize API response shapes for pages.
- Existing stores should be extended rather than replaced.
- New stores should follow the Pinia patterns already used by `sources.ts`, `opportunities.ts`, and `runtime.ts`.
- Mutation actions should update local state when cheap and return the backend response for pages that need immediate feedback.

### Test Scenarios

- Dashboard store loads `/api/dashboard/summary` and records loading/error state.
- Opportunities store loads review queue, loads detail, creates manual imports, reviews candidates, and updates follow-up status.
- Sources store loads source detail and advanced rule versions.
- Runtime store loads collection runs and health state.
- Agents, notifications, audit, customers, and goals stores load their corresponding backend query endpoints.
- Store actions clear stale errors on retry and keep existing data stable when a request fails.

## Deferred Phases

### Phase 3: Core Business Pages

- `DashboardPage.vue`
- `SourcesPage.vue`
- `ReviewQueuePage.vue`
- `OpportunityDetailPage.vue`

Replace fallback/demo data with store-driven UI, full loading/empty/error states, rule editing workflows, manual import, review, and follow-up controls.

### Phase 4: Operations Pages

- `CollectionRunsPage.vue`
- `CustomersPage.vue`
- `GoalsPage.vue`
- `NotificationsPage.vue`
- `AgentsPage.vue`
- `AuditLogsPage.vue`

Replace static demo tables with real query data and operational actions.

### Phase 5: UI State And Permissions

- Route guard for unauthenticated users.
- Token-expiry handling.
- Permission-gated actions.
- Duplicate-submit protection.
- Layout hardening for long text and empty/error states.

### Phase 6: End-To-End Acceptance

- Start `./scripts/start_dev.sh`.
- Login with `admin/admin-pass`.
- Load sources from SQLite.
- Manually import a candidate.
- Review and follow up the candidate.
- Confirm customer history, goal progress, notification logs, and audit logs update.

## Verification

- `python3 -m pytest -q`
- `npm --prefix frontend run test -- --run`
- `npm --prefix frontend run build`
- Manual local smoke through `./scripts/start_dev.sh` after page phases are implemented.
