# E2E Test — Exploratory Browser Testing

## Pre-flight Check

### 1. agent-browser Installation

Check if agent-browser is installed:
```bash
agent-browser --version
```

If not found, install automatically:
```bash
npm install -g agent-browser && agent-browser install --with-deps
```

### 2. Frontend Check

Verify the frontend is running:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/login
```

If not running, start it:
```bash
NEXT_PUBLIC_DEMO_MODE=true make dev-fe  # frontend only, port 3000
# OR
make dev  # full stack, backend :8891 + frontend :3000
```

Wait for the server to be ready before proceeding.

## Project Context

- **Demo credentials**: admin / demo123
- **Frontend**: http://localhost:3000
- **API base**: http://localhost:8891/api/v1

## Phase 1: Setup

```bash
mkdir -p e2e-screenshots/{login,dashboard,workspace,components,approvals,connectors,intelligence,knowledge,renderings,figma,briefs,settings,responsive}
```

Open the app and confirm it loads:
```bash
agent-browser open http://localhost:3000/login
agent-browser screenshot e2e-screenshots/login/01-login-page.png
```

Use `Read` tool to view each screenshot and analyze for visual issues.

## Phase 2: agent-browser CLI Reference

```bash
agent-browser open <url>              # Navigate to a page
agent-browser snapshot -i             # Get interactive elements with refs (@e1, @e2...)
agent-browser click @eN               # Click element by ref
agent-browser fill @eN "text"         # Clear field and type
agent-browser select @eN "option"     # Select dropdown option
agent-browser press Enter             # Press a key
agent-browser press Escape            # Dismiss modal/dropdown
agent-browser screenshot <path>       # Save screenshot (no subdirs in path)
agent-browser set viewport W H        # Set viewport (e.g., 375 812 for mobile)
agent-browser console                 # Check for JS errors
agent-browser errors                  # Check for uncaught exceptions
agent-browser get url                 # Get current URL
agent-browser close                   # End session
```

**IMPORTANT:** Refs become invalid after navigation or DOM changes. Always re-snapshot after page navigation, form submissions, or dynamic content updates.

## Phase 3: Key Journeys

Test each journey. For each: navigate, snapshot, interact with every button/control, screenshot, analyze with Read tool.

### Login Flow
1. Open `/login`, fill username "admin" + password "demo123", click Sign In
2. Verify redirect to `/` dashboard
3. Screenshot before and after

### Dashboard (`/`)
- Verify: stat cards, quality overview, recent activity, project cards
- Click: Open Workspace, Browse Components, New Project, View All

### Workspace (`/projects/1/workspace`)
Test ALL interactive elements:
- **Template selector** — dropdown with templates + New Template
- **Code/Visual tabs** — switch between Monaco editor and Liquid builder
- **Preview controls** — Desktop/Tablet/Mobile viewports, dark mode toggle, zoom, compile
- **Test As** — persona selector (9 presets + Create custom)
- **Run QA** — triggers 10-point gate, shows pass/fail results
- **Export** — 5 platform tabs (Raw HTML, Braze, SFMC, Adobe, Taxi)
- **Generate Image** — AI image dialog with style presets and aspect ratios
- **AI Chat** — 10 agent tabs (Chat, Scaffolder, Dark Mode, Content, Outlook, A11y, Personalize, Reviewer, Knowledge, Innovator)
- **History tab** — conversation history with session list

### Components (`/components`)
- Category filter tabs (All, action, commerce, content, social, structure)
- Search box — type "hero" and verify filtering
- Click component card → detail dialog (Preview/Source/Versions tabs)
- Dark mode toggle in component preview

### Approvals (`/approvals`)
- Status filter tabs (All/Pending/Approved/Rejected/Revision Requested)
- Verify cards show correct status badges

### Connectors (`/connectors`)
- Platform filter tabs (All/Braze/SFMC/Adobe Campaign/Taxi/Raw HTML)
- Verify Success/Failed status badges and error messages

### Intelligence (`/intelligence`)
- 4 summary stat cards
- Check Performance bars for all 10 QA checks
- Quality Trend chart
- Export Report button

### Knowledge (`/knowledge`)
- Search bar, domain filter tabs, tag chips
- Document cards with chunk counts

### Renderings (`/renderings`)
- Stats cards, compatibility matrix, Request Rendering Test button

### Figma Sync (`/figma`)
- Connection cards with status badges, Sync Now/Remove, Connect File

### Briefs (`/briefs`)
- All Briefs/Connections tabs, client org filters, PM tool filters, status filters

### Settings (`/settings`)
- Language selector, preferences section

### Global Features
- **Dark mode** — toggle theme button in sidebar footer
- **Locale switching** — select different language from sidebar dropdown, verify translations
- **Logout** — click Logout, verify redirect to `/login`

## Phase 4: Issue Handling

When an issue is found:
1. Document: expected vs actual, screenshot path
2. Fix the code directly
3. Re-test and screenshot to confirm fix

## Phase 5: Cleanup

```bash
agent-browser close
```

## Phase 6: Report

Present a summary:

```
## E2E Testing Complete

**Journeys Tested:** [count]
**Screenshots Captured:** [count]
**Issues Found:** [count] ([count] fixed, [count] remaining)

### Pages Tested
[table of pages with status]

### Issues Fixed During Testing
- [Description] — [file:line]

### Remaining Issues
- [Description] — [severity: high/medium/low]

### Screenshots
All saved to: `e2e-screenshots/`
```

## API Endpoints for Mutation Verification

```bash
# Projects
curl -s http://localhost:8891/api/v1/projects

# Templates
curl -s http://localhost:8891/api/v1/templates

# Components
curl -s http://localhost:8891/api/v1/components

# QA results
curl -s http://localhost:8891/api/v1/qa/results

# Approval requests
curl -s http://localhost:8891/api/v1/approvals
```
