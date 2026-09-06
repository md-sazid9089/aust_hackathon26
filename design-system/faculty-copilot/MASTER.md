# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Faculty Copilot
**Generated:** 2026-09-06 10:27:55
**Category:** Academic Journal / Scholarly Publishing
**Design Dials:** Variance 3/10 (Centered / Minimal) | Motion 3/10 (Subtle) | Density 6/10 (Standard)

---

## Global Rules

### Color Palette

| Role             | Hex       | CSS Variable               |
| ---------------- | --------- | -------------------------- |
| Primary          | `#1E3A5F` | `--color-primary`          |
| On Primary       | `#FFFFFF` | `--color-on-primary`       |
| Secondary        | `#334155` | `--color-secondary`        |
| On Secondary     | `#FFFFFF` | `--color-on-secondary`     |
| Accent/CTA       | `#B45309` | `--color-accent`           |
| On Accent/CTA    | `#FFFFFF` | `--color-on-accent`        |
| Background       | `#F8FAFC` | `--color-background`       |
| Foreground       | `#0F172A` | `--color-foreground`       |
| Card             | `#FFFFFF` | `--color-card`             |
| Card Foreground  | `#0F172A` | `--color-card-foreground`  |
| Muted            | `#E9EEF5` | `--color-muted`            |
| Muted Foreground | `#475569` | `--color-muted-foreground` |
| Border           | `#CBD5E1` | `--color-border`           |
| Destructive      | `#DC2626` | `--color-destructive`      |
| On Destructive   | `#FFFFFF` | `--color-on-destructive`   |
| Ring             | `#1E3A5F` | `--color-ring`             |

**Color Notes:** Scholarly navy + citation gold + serif accent

### Typography

- **Heading Font:** Crimson Pro
- **Body Font:** Atkinson Hyperlegible
- **Mood:** academic, research, scholarly, accessible, readable, educational
- **Google Fonts:** [Crimson Pro + Atkinson Hyperlegible](https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Crimson+Pro:wght@400;500;600;700&display=swap)

**CSS Import:**

```css
@import url("https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Crimson+Pro:wght@400;500;600;700&display=swap");
```

### Spacing Variables

_Density: 6/10 — Standard_

| Token         | Value             | Usage                     |
| ------------- | ----------------- | ------------------------- |
| `--space-xs`  | `4px` / `0.25rem` | Tight gaps                |
| `--space-sm`  | `8px` / `0.5rem`  | Icon gaps, inline spacing |
| `--space-md`  | `16px` / `1rem`   | Standard padding          |
| `--space-lg`  | `24px` / `1.5rem` | Section padding           |
| `--space-xl`  | `32px` / `2rem`   | Large gaps                |
| `--space-2xl` | `48px` / `3rem`   | Section margins           |
| `--space-3xl` | `64px` / `4rem`   | Hero padding              |

### Shadow Depths

| Level         | Value                          | Usage                       |
| ------------- | ------------------------------ | --------------------------- |
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)`   | Subtle lift                 |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)`    | Cards, buttons              |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)`  | Modals, dropdowns           |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #b45309;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #1e3a5f;
  border: 2px solid #1e3a5f;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #f8fafc;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #1e3a5f;
  outline: none;
  box-shadow: 0 0 0 3px #1e3a5f20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Minimalism & Swiss Style

**Keywords:** Clean, simple, spacious, functional, white space, high contrast, geometric, sans-serif, grid-based, essential

**Best For:** Enterprise apps, dashboards, documentation sites, SaaS platforms, professional tools

**Key Effects:** Subtle hover (200-250ms), smooth transitions, sharp shadows if any, clear type hierarchy, fast loading

### Page Pattern

**Pattern Name:** Newsletter / Content First

- **Conversion Strategy:** Keep the form to the fields actually required and link to a sample issue. Show a subscriber count only when it is current, verified, and dated; otherwise use qualitative social proof.
- **CTA Placement:** Hero inline form + Sticky header form
- **Section Order:** Hero (Value Prop + Form) > Recent Issues/Archives > Social Proof (Subscriber count) > About Author

---

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, {
  opacity: 0,
  y: 12,
  duration: 0.35,
  ease: "power1.out",
  scrollTrigger: {
    trigger: el,
    start: "top 90%",
    toggleActions: "play none none reverse",
  },
});
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger); Use matchMedia('(prefers-reduced-motion: reduce)') to skip non-essential motion and render the final state immediately

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

---

## Anti-Patterns (Do NOT Use)

- ❌ Low contrast
- ❌ Visual clutter
- ❌ motion-heavy chrome

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

---

## DESIGN RATIONALE (project-specific, authoritative over generated specs above)

Users: AUST faculty (30–60, time-pressed, mixed tech comfort, laptop + projector, Bangla/English), department admin (read-only scanning), judges (5-minute demo). Every decision below names the need it serves and the alternative rejected. Where this section conflicts with the generated component CSS above, this section wins.

| Area                                           | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                            | User need served                                                                                                                                                | Alternative rejected & why                                                                                                                                   |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Page pattern**                               | Application shell: fixed left rail (courses / dashboard / admin), course-scoped sub-nav, single content column max 1200 px. No hero, no marketing sections.                                                                                                                                                                                                                                                                                         | Faculty return to the same course repeatedly; the rail keeps "where am I" constant on a projector.                                                              | Generated "Newsletter / Content First" pattern — a landing pattern; the product has no marketing page (scope §12).                                           |
| **Layout model for results**                   | Every run result page uses one fixed reading order: **Input summary → What the AI did (stages) → Evidence (computed numbers + charts) → Decisions (finding cards)**. Sticky section anchors on the right.                                                                                                                                                                                                                                           | Judges must read "input → AI → evidence → decision" at a glance; faculty must find the accept/dismiss step without hunting.                                     | Tabbed results — hides the chain of evidence behind clicks and fails the projector test (hover/tab-only information).                                        |
| **Colour roles**                               | One accent (`--accent` amber #B45309) reserved for _primary decisions_ (Run, Accept, Export). Navy (`--primary`) for navigation/selected. Severity uses a 4-step semantic scale (info slate / low blue / medium amber / high red) **always paired with a text label and an icon**. Deterministic numbers use `--measure` (navy ink) ; AI prose sits on `--ai-surface` (warm tint) with a left rule.                                                 | Trust: colour must never be the only carrier (WCAG 1.4.1); severity must be legible on washed-out projectors; the eye must separate "computed" from "LLM says". | Green/red pass-fail only — colour-blind unsafe; multi-hue brand palette — clutter, competes with severity.                                                   |
| **Deterministic vs AI encoding**               | Computed values: tabular numerals, navy, `Computed` caption with a calculator glyph. AI explanation: `AI explanation` caption with sparkle glyph, warm surface, serif-free body, always followed by its `evidence_snippet` in a quote block.                                                                                                                                                                                                        | AI-004 / AI-003: faculty must know which numbers are arithmetic and which sentences are model output; judges must see evidence next to every claim.             | Mixing both in one card body — indistinguishable; hiding evidence behind "show more" — buried trust signal.                                                  |
| **Type scale**                                 | Headings Crimson Pro (600) at 32/24/20; body Atkinson Hyperlegible 16 px (min), table 15 px, captions 13 px never below. Bengali falls back to Noto Sans Bengali; line-height 1.6 on any element that may hold Bangla; `lang` attribute set from `artefact.lang`.                                                                                                                                                                                   | Projector-safe (≥16 px), dyslexia-friendly body font, Bangla glyphs need taller line boxes to avoid clipping matras.                                            | Serif body (EB Garamond pairing) — lower legibility on projectors and poor Bengali fallback; system UI stack — less distinctive, but kept as final fallback. |
| **Density**                                    | Dial 6/10: 8-px rhythm, 16 px card padding, 44-px row height in editable tables, 12 px gaps in finding lists. Admin tables tighten to 40 px rows (page override).                                                                                                                                                                                                                                                                                   | Faculty edit dozens of extracted questions; admin scans many courses — both need density without cramping.                                                      | Spacious dial 3 — too much scrolling for extraction confirm; dense dial 9 — too small on projector.                                                          |
| **Motion**                                     | Dial 3/10: 150–200 ms opacity/colour transitions only; run progress uses a determinate bar + stage list, no spinners beyond 300 ms; all motion disabled under `prefers-reduced-motion`. No GSAP (the scroll-reveal snippet above is **not used**).                                                                                                                                                                                                  | Restraint reads as trustworthy; scroll reveals hide content on a projector and hurt reduced-motion users.                                                       | Skeleton shimmer + slide-ins — visual noise in an evidence tool.                                                                                             |
| **Iconography**                                | Single family `lucide-react`, 1.5 px stroke, sizes token `icon-sm 16 / icon-md 20 / icon-lg 24`. Icons decorative (`aria-hidden`) when text is present; icon-only buttons carry `aria-label`. No emojis anywhere.                                                                                                                                                                                                                                   | Consistency across 19 routes; screen-reader correctness.                                                                                                        | Phosphor — equally good, lucide chosen because shadcn primitives ship with it (fewer families to govern).                                                    |
| **Empty / loading / partial / error strategy** | Empty: one sentence + one primary action (e.g. "Upload a question paper"). Loading: layout-stable skeleton (no spinner) with `aria-busy`. Run in progress: determinate stage list (10/30/55/75/90/100 %) streamed over SSE, each stage shows ✓/●/✗ text state. Partial: amber banner "Analysis partially completed — findings below are from completed stages" plus retry. Error: card with `code`, human message, `request_id` for support, retry. | F-014 / AI-002: faculty must always know what to do next; judges will see a failure path during the demo (W6).                                                  | Toast-only errors — vanish before the audience reads them; blank tables — dead ends.                                                                         |
| **Finding card anatomy**                       | Fixed order top→bottom: severity chip + type label · title · target chip (Q3 / CO5 / topic) · **AI rationale** · **evidence quote** · confidence (if any) · actions Accept / Dismiss / Reopen. Status changes are optimistic with undo toast. Keyboard: J/K move, A accept, D dismiss. Bulk bar appears on multi-select.                                                                                                                            | F-013, F-022, AI-003; a lecturer triaging 30 findings needs speed; judges need the same anatomy on every module so they learn it once.                          | Table of findings — rationale/evidence don't fit; modal per finding — slow.                                                                                  |
| **Charts**                                     | Recharts. Coverage → grid heat map **with values printed in cells** and a data-table toggle; Bloom → horizontal bar with labels; attainment → bar per CO with threshold reference line and met/not-met label; divergence → grouped bar per criterion; overlap → matrix with printed similarity %. Never colour-only.                                                                                                                                | Chart-domain guidance: heatmaps/bars need printed values and table fallback for accessibility; faculty distrust unlabeled visuals.                              | Radar for Bloom — unfamiliar to audience; gauges — single-KPI only.                                                                                          |
| **Dark mode**                                  | Full token set for `.dark`; surfaces stay low-saturation, severity hues re-tuned for ≥4.5:1 on dark; toggle in the rail. Default follows OS.                                                                                                                                                                                                                                                                                                        | Some faculty present in dim rooms; judges may use dark OS themes.                                                                                               | Light-only — fails the brief.                                                                                                                                |
| **Bulk actions & shortcuts (added UX)**        | Bulk accept/dismiss selected findings (client fans out `PATCH /findings/{id}`; no new endpoint). Shortcuts listed in a `?` help popover; never the only way to act.                                                                                                                                                                                                                                                                                 | Speed for triage; keyboard-complete requirement.                                                                                                                | New bulk endpoint — avoided to keep backend contract stable during the hackathon.                                                                            |
| **Data layer (added)**                         | All pages call `features/*/api.ts` hooks → `Api` interface → `HttpApi` (live, `/api/v1`) or `MockApi` (`VITE_API_MODE=mock`, in-memory fixtures with simulated SSE). Swapping is one env var.                                                                                                                                                                                                                                                       | Frontend must demo before backend is ready; single seam per architecture §12.                                                                                   | Sprinkling `fetch` in components — impossible to swap; MSW at runtime — heavier than needed for a demo (kept for tests).                                     |

**Token summary (implemented in `frontend/src/index.css`):** colour roles above + `--measure`, `--ai-surface`, `--ai-border`, `--sev-info/low/medium/high` (+`-fg`); radii `--radius-sm 6 / --radius 8 / --radius-lg 12`; motion `--dur-fast 150ms / --dur 200ms / --ease ease-out`; spacing 8-px scale; icon sizes 16/20/24.
