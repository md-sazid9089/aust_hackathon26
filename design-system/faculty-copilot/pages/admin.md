# Page override — /admin/\* (users, runs, usage, department)

Overrides MASTER.md for admin routes only.

- **Density:** table rows 40 px (vs 44 px), 13 px captions allowed in table cells (never below 13 px), 1400 px content max-width.
- **Read-only emphasis:** no amber accent on this surface except the guarded `Reset demo data` action (which requires typed confirmation `RESET`). Everything else is navy/neutral.
- **Tables:** sticky header, `overflow-x-auto`, sortable columns with visible sort indicator + `aria-sort`, per-page 25.
- **Charts:** usage = stacked bar (tokens by module) with data-table toggle; department attainment = heat-grid course × PO with printed percentages and threshold legend.
- **No finding cards** on admin pages; drill-down links go to the faculty run page.
