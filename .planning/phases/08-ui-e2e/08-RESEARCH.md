# Phase 08: UI E2E Testing - Research

**Researched:** 2026-03-28
**Domain:** UI End-to-End Testing with Playwright
**Confidence:** HIGH

## Summary

This research focuses on integrating Playwright into the `web-ui-external` project, which uses Vite 7 and React 19. Playwright is the industry standard for E2E testing due to its speed, reliability, and excellent developer experience. The integration will involve adding `@playwright/test`, configuring it to work with Vite's dev server, and setting up cross-browser/device testing.

**Primary recommendation:** Use `@playwright/test` with a dedicated `e2e/` directory and configure the `webServer` option in `playwright.config.ts` to automatically manage the Vite dev server during tests.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@playwright/test` | ^1.58.2 | E2E Testing Framework | Native async/await, auto-waiting, and multi-browser support. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dotenv` | ^16.x | Environment variable management | To load `.env` for test credentials. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright | Cypress | Cypress has a different architecture (runs in-browser), is generally slower, and lacks native multi-tab/iframe support as robustly as Playwright. |
| Playwright | Selenium | Selenium is significantly slower, requires manual driver management, and lacks modern features like auto-waiting. |

**Installation:**
```bash
# Recommended initialization (interactive)
cd web-ui-external && npm init playwright@latest

# Or manual install
npm install -D @playwright/test
npx playwright install --with-deps
```

## Architecture Patterns

### Recommended Project Structure
```
web-ui-external/
├── e2e/                   # E2E test files (*.spec.ts)
│   ├── auth.setup.ts     # Global authentication setup
│   └── tests/             # Feature-specific tests
├── playwright.config.ts   # Playwright configuration
└── .auth/                 # Gitignored directory for session storage
```

### Pattern 1: WebServer Integration
**What:** Use Playwright's `webServer` to launch the Vite dev server before running tests.
**When to use:** Always for local development and CI.
**Example:**
```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
  },
  use: {
    baseURL: 'http://localhost:5173',
  },
});
```

### Pattern 2: Authentication State Reuse
**What:** Authenticate once and reuse the storage state across tests.
**When to use:** When many tests require a logged-in state.
**Example:**
```typescript
// e2e/auth.setup.ts
import { test as setup } from '@playwright/test';

const authFile = '.auth/user.json';

setup('authenticate', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Username').fill('user');
  await page.getByLabel('Password').fill('password');
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('/dashboard');
  await page.context().storageState({ path: authFile });
});

// playwright.config.ts
projects: [
  { name: 'setup', testMatch: /.*\.setup\.ts/ },
  {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], storageState: '.auth/user.json' },
    dependencies: ['setup'],
  },
]
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Waiting for elements | `setTimeout` or loops | `await expect(locator).toBeVisible()` | Playwright's auto-waiting handles race conditions reliably. |
| Browser management | Custom driver wrappers | Playwright Projects | Handles cross-browser, viewports, and permissions natively. |
| Authentication | Manual login in every `beforeEach` | Storage State | Significant speedup by avoiding redundant login flows. |

## Common Pitfalls

### Pitfall 1: Port Conflicts
**What goes wrong:** `webServer` fails to start because port 5173 is already in use.
**How to avoid:** Set `reuseExistingServer: !process.env.CI` and ensure your `webServer` config matches Vite's port.

### Pitfall 2: Flaky Tests due to Hydration
**What goes wrong:** Interactions fail because the React app hasn't hydrated yet (especially in React 19).
**How to avoid:** Use Playwright's locators which auto-wait for elements to be actionable. Avoid `page.waitForTimeout`.

### Pitfall 3: Committing Secrets
**What goes wrong:** Committing `.auth/user.json` containing session tokens.
**How to avoid:** Add `.auth/` to `.gitignore`.

## Code Examples

### Configuration for Multiple Viewports
```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 13'] },
    },
  ],
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `page.click('.btn')` | `page.getByRole('button')` | v1.27+ | More resilient to DOM changes, promotes accessibility. |
| Manual setup/teardown | Playwright UI Mode | v1.32+ | Better debugging and time-traveling. |

## Open Questions

1. **Backend Integration:** How will the E2E tests reset the database state before runs?
   - Recommendation: Add a `/api/test/reset` endpoint or use the existing Pytest infrastructure to seed data before E2E runs.
2. **React 19 Compatibility:** Are there specific hydration timing changes?
   - What we know: React 19 has improved hydration, but locators generally handle this.
   - Recommendation: Monitor for "element is not clickable" errors and use `waitForRole` if needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | All | ✓ | v22.14.0 | — |
| npm | Installation | ✓ | 10.9.2 | — |
| Playwright Browsers | Testing | ✗ | — | `npx playwright install` |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright v1.58.2 |
| Config file | `web-ui-external/playwright.config.ts` |
| Quick run command | `npx playwright test` |
| Full suite command | `npx playwright test --project=chromium --project=Mobile\ Safari` |

## Sources

### Primary (HIGH confidence)
- [Playwright Official Docs](https://playwright.dev/docs/intro) - Installation and setup.
- [Playwright Auth Guide](https://playwright.dev/docs/auth) - Session reuse and authentication.
- [Playwright Configuration](https://playwright.dev/docs/test-configuration) - Projects and webServer.

### Secondary (MEDIUM confidence)
- Community blogs on Vite 7 + Playwright 1.x integration.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Playwright is standard.
- Architecture: HIGH - Follows official recommendations.
- Pitfalls: MEDIUM - Based on common Vite/React issues.

**Research date:** 2026-03-28
**Valid until:** 2026-04-27
