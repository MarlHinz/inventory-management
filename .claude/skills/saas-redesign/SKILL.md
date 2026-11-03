---
name: saas-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS / fintech-style interface - left vertical sidebar navigation instead of a top nav bar, design tokens (CSS custom properties) with light and dark theme, consistent spacing, clean card layouts, and fully responsive behaviour. Use when asked to redesign, modernize, restyle or "make it look like a SaaS / fintech dashboard", or to move a top navigation into a sidebar.
---

# SaaS Redesign for Vue 3

Turn a working Vue 3 app into a polished SaaS dashboard without touching its behaviour. Data loading, routes, props, emits, i18n keys and computed logic stay as they are. Only markup structure and styling change.

## Workflow

Work in this order. Each phase must render correctly before the next starts.

1. **Audit** (read-only). Record:
   - The layout shell: where the nav, header, filters and `<router-view>` live.
   - Global, unscoped style blocks and the class names views depend on.
   - Hardcoded colors: run `grep -rnoE "#[0-9a-fA-F]{3,8}\b" src | wc -l` per file.
   - Fixed widths over 280px, `minmax(>300px)` and existing `@media` queries.
   - Chart colors set in templates or JS instead of CSS.
   - Fonts that are declared but never loaded.
2. **Tokens.** Create the token sheet (see below) in the global style block, or in `src/styles/tokens.css` imported from `main.js`.
3. **Shell.** Build the sidebar, mobile drawer and theme toggle. Restyle the global classes (`.card`, `.badge`, `table`, `.page-header`, stat or KPI cards) using tokens only.
4. **Views.** Migrate one view at a time:
   - Replace every hex value with a token.
   - Fix grids and fixed widths.
   - Move chart colors to tokens.
   - Independent views can be split across parallel agents once the shell is merged.
5. **Verify** with the acceptance checklist at the end.

**Rule:** after phase 4, view and component files contain **no hex, rgb or hsl literals**. The only exception is the token sheet itself. Use `color-mix(in srgb, var(--accent) 12%, transparent)` for tints.

## Token sheet

Name tokens by role, not by color:

```css
:root {
  /* surfaces */
  --bg: #f6f7fb; --surface: #ffffff; --surface-2: #f1f3f9; --border: #e4e7ef; --border-strong: #cfd5e2;
  /* text */
  --text: #0b1020; --text-muted: #5b6478; --text-faint: #8a93a6;
  /* brand */
  --accent: #4f46e5; --accent-hover: #4338ca; --accent-contrast: #ffffff;
  --accent-soft: color-mix(in srgb, var(--accent) 10%, transparent);
  /* status */
  --success: #059669; --warning: #d97706; --danger: #dc2626; --info: #0284c7;
  /* charts: an ordered categorical palette, used in this order */
  --chart-1: #4f46e5; --chart-2: #06b6d4; --chart-3: #10b981; --chart-4: #f59e0b; --chart-5: #ef4444; --chart-6: #8b5cf6;
  /* sidebar */
  --sidebar-bg: #0b1020; --sidebar-text: #a4acc4; --sidebar-active: #ffffff; --sidebar-w: 248px;
  /* shape and space */
  --radius-sm: 6px; --radius: 10px; --radius-lg: 14px;
  --shadow-sm: 0 1px 2px rgb(16 24 40 / .05); --shadow: 0 4px 16px -4px rgb(16 24 40 / .08);
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px;
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
}
[data-theme="dark"] {
  --bg: #070a13; --surface: #0e1322; --surface-2: #141a2c; --border: #1f2740; --border-strong: #2c3654;
  --text: #e7eaf3; --text-muted: #98a1b8; --text-faint: #6b7590;
  --accent: #818cf8; --accent-hover: #a5b4fc; --accent-contrast: #0b1020;
  --success: #34d399; --warning: #fbbf24; --danger: #f87171; --info: #38bdf8;
  --chart-1: #818cf8; --chart-2: #22d3ee; --chart-3: #34d399; --chart-4: #fbbf24; --chart-5: #f87171; --chart-6: #a78bfa;
  --sidebar-bg: #05070e;
  --shadow-sm: none; --shadow: 0 0 0 1px var(--border);
}
```

Spacing uses only `--space-*`. Corners use only `--radius*`. Never invent a one-off value.

## Layout shell

- **Grid:** `.app { display: grid; grid-template-columns: var(--sidebar-w) 1fr; min-height: 100dvh; }`.
- **Sidebar** (`<aside>` containing `<nav aria-label="Main">`):
  - Sticky, full height.
  - Logo block at the top.
  - Nav links in the middle: inline SVG icon (20px, `stroke="currentColor"`) plus label. Active state via `router-link-active` or `exact-active-class`: accent bar on the left plus a lighter background.
  - Footer at the bottom: language switcher, theme toggle, profile menu.
  - Dropdowns that used to open downwards from a top-right header must now open **upwards** (`bottom: calc(100% + 8px)`) and stay inside the viewport.
- **Content column:** an optional sticky toolbar (page filters), then `<main>` with `max-width: 1440px; padding: var(--space-6)`.
- **Below 1024px:**
  - The grid collapses to one column.
  - A 56px top bar shows a hamburger button and the logo.
  - The sidebar becomes an off-canvas drawer (`transform: translateX(-100%)`, `transition: transform .2s`) with a backdrop overlay.
  - The drawer closes on overlay click, `Escape`, and route change (`watch(() => route.path, close)`).
  - Hamburger accessibility: `aria-expanded`, `aria-controls`. Focus goes into the drawer when it opens.
- **Sticky offsets:** never hardcode them from another element's height (e.g. `top: 70px`). Use `top: 0` inside the scroll context, or a `--topbar-h` token.

## Theme toggle

- An inline script in `index.html` `<head>` sets `document.documentElement.dataset.theme` **before first paint**, from `localStorage['theme']` or `prefers-color-scheme`. This prevents a flash.
- A small composable `useTheme()` holds a `ref`, writes `localStorage` (wrapped in try/catch) and updates `data-theme`. The toggle is a `<button>` with `aria-pressed` and a sun or moon SVG.
- Charts and SVGs use `fill="var(--chart-1)"` or CSS classes so they re-theme automatically. Don't compute colors in JS. If JS has to choose a color, return the token string (`'var(--success)'`).

## Fintech look

- **Fonts:** load Inter (400/500/600/700) and JetBrains Mono (500) via Google Fonts `<link>` with `preconnect`. Numbers, money and IDs (SKUs, order numbers) use `font-variant-numeric: tabular-nums`. IDs use the mono font.
- **KPI card:**
  - Small uppercase label (`--text-muted`, 12px, letter-spacing .04em).
  - Large value (28-32px, 600, tabular).
  - Optional delta pill: `--success` or `--danger` on a `color-mix` tint.
  - Optional thin progress or sparkline.
- **Cards:** `--surface`, 1px `--border`, `--radius-lg`, `--shadow-sm`, padding `--space-5`. Header row: title (15-16px, 600) on the left, actions on the right. Prefer a hairline border over a heavy shadow.
- **Tables:**
  - Sticky header on `--surface-2`.
  - Uppercase 11-12px muted header labels.
  - Row hover `--surface-2`.
  - Numbers right-aligned.
  - Generous row height (44px).
- **Badges:** pill, 12px, 500, tinted background via `color-mix` and full-strength text of the same status token.
- **Buttons:**
  - Primary: `--accent` background, `--accent-contrast` text, `--radius`, 36-40px tall.
  - Secondary: `--surface` with a `--border`.
  - Visible `:focus-visible` ring: `outline: 2px solid var(--accent); outline-offset: 2px`.
  - Disabled at 50% opacity with `cursor: not-allowed`.
- **Form controls:** custom-style `input[type=range]` with `accent-color: var(--accent)`. Selects and inputs are 36px tall with a `--border`, and the focus ring goes on the accent.
- **Motion:** 150-200ms ease on hover and focus only. Respect `prefers-reduced-motion`.
- **No emojis** anywhere in the UI.

## Responsive rules

- Breakpoints are only `640px` and `1024px`. Mobile-first: base styles target phones, enhanced with `@media (min-width: ...)`.
- Grids: `repeat(auto-fit, minmax(min(100%, 260px), 1fr))`. Never use a bare `minmax(450px, 1fr)`.
- No fixed width over 280px on content elements. Use `max-width` and `width: 100%`.
- Tables stay in an `overflow-x: auto` wrapper. The page itself must never scroll horizontally.
- Filter bars wrap (`flex-wrap: wrap`). On phones, controls go full width in a 2-column grid.
- Modals: `width: min(640px, 100% - 32px)` and `max-height: calc(100dvh - 32px)` with internal scroll.
- Touch targets are at least 40px tall on mobile.

## Acceptance checklist

Verify with Playwright MCP tools (`browser_resize`, `browser_navigate`, `browser_take_screenshot`, `browser_evaluate`) on **every route**, at **375, 768 and 1440px**, in **light and dark**:

- [ ] `document.documentElement.scrollWidth <= window.innerWidth` (no horizontal scroll).
- [ ] Below 1024px the drawer opens and closes via the hamburger, the overlay and Escape, and closes on navigation.
- [ ] The theme choice survives a reload, with no flash of the wrong theme.
- [ ] No unreadable text: body text has at least 4.5:1 contrast against its surface in both themes.
- [ ] Keyboard: Tab reaches every nav item and control, and the focus ring is visible.
- [ ] `grep -rnE "#[0-9a-fA-F]{3,8}\b" src/views src/components` returns nothing.
- [ ] The browser console has no errors. All existing features (filters, modals, language switch) still work.
