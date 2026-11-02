# Desktop-to-Web Feature Parity Plan

## Scope and hard boundaries

This repository is the independent browser edition. It owns its own users, passwords, SQLite/PostgreSQL data, sessions, settings, uploaded files, and backups.

The Windows desktop EXE project `yalangisexter-ux/audit-report`, its installer, updater, desktop source code, LocalAppData database, encryption keys, and existing customer snapshots are read-only references for this project. Do not import or migrate desktop accounts or records. Do not connect the web app to the desktop encrypted customer-data sync endpoints.

## Desktop feature inventory to reproduce in the web edition

| Area | Required browser behaviour | Current web baseline / remaining work |
|---|---|---|
| Shell and navigation | Raw Strength branding, responsive collapsible navigation, Home, Dashboard, consistent page headers, responsive dialogs, keyboard/touch friendly controls | Existing SPA/navigation; visual and accessibility parity pass required |
| Appearance | Night/day themes, glass panels, readable day-mode contrast, wallpaper selector, original Galaxy, Lord Shiva, Love & Couples, Milky Way Waves and Ocean artwork | Real SVG wallpaper artwork and selectors added on parity branch; verify mobile/day/night and saved preference behaviour |
| Dashboard | Live operational KPIs, employee/task/attendance/business summaries, live clock, sync/health indicators | Basic KPIs present; richer cards, filters and activity summaries remain |
| Employees | Full employee register, employee code, role/designation, department, contact, active state, employee groups/order, edit/delete/search | Basic CRUD exists; extended fields, grouping, bulk operations and validation remain |
| Task Manager | Assign tasks, dates/times, priority/status, details, target/actual quantities, completion, next action, evidence/proof links, arbitrary custom key/value tracking fields, edit/delete/filter | Basic CRUD exists; custom tracking fields, richer lifecycle, proof links and complete filter parity remain |
| Employee Tracker | Per-employee assigned/open/completed task summary and progress views | Basic summary exists; targets, performance views and historical filtering remain |
| Attendance | Daily roster, check-in/check-out, attendance statuses, edits, notes, holidays and historical views | Basic attendance CRUD exists; shift/time validation, holiday calendar and complete reports remain |
| Employee targets | Per-employee dated targets, status, edit/history and report integration | Not present in current web baseline |
| Print Center | Preview and export Audit/EOD, Productivity, Attendance, Employee Details and business reports; individual/consolidated scope; optional EOD sections; clickable evidence links; PDF, DOCX, CSV and browser print | Basic summary/CSV/print exists; report types, options and format parity remain |
| EOD Archive | Search, filter, view and reprint stored daily reports | Basic archive tab exists; persistence/search/export parity remains |
| Business dashboard | Sales/stock/member/service/activities KPIs and status summaries | Basic KPIs exist; full dashboard and reconciliation remain |
| Products & inventory | SKU, category, brand, package/unit, opening/received/reserved/dispatched/free/returned/damaged/expired/quarantined stock, reorder levels, batch/expiry/location, cost/price, stock ledger | Basic product records exist; ledger and full stock arithmetic are required |
| Orders | Order IDs, date/channel/customer/contact/payment, line items, paid/free quantities, discounts, totals, invoice/shipment, assigned employee, status lifecycle, remarks | Basic order records exist; order lines, stock deduction and invoice workflow remain |
| Services & members | Service descriptions, training mode (online/offline), units, session duration/count, validity, price, active state; member plan dates, purchased/completed sessions, trainer, payment and status | Basic services/members exist; complete plan/session/payment lifecycle remains |
| Employee activities | Assign/track operational activities, related orders/services/products, quantity, start/completion, status, verification, proof and remarks | Basic activity records exist; full links and verification lifecycle remain |
| Store Directory / prospects | Search/filter, regional coverage, source/evidence links, contact details, verification, deduplication, workbook import/export, print, saved leads | Basic directory exists; rich schema/import/export and regional dashboard remain |
| Web scraping | Server-side background search across supported public search engines and public merchant pages; category, state/region, keywords, deep-scrape option, progress/results, evidence URLs, deduplication, review-before-save | Current web only saves a manually supplied URL/name; true scraper is not implemented. Implement server-side with rate limits, timeouts, robots/terms respect, SSRF protection and provenance |
| Live Chat | Private/group conversations with authorized users, unread state, reconnect and history | Tab exists; web-specific chat backend and realtime parity require validation |
| User and roles | First-admin setup, user creation/deactivation, role separation, password change/reset, session expiry/revocation, audit events | New first-admin flow and password change/reset endpoints exist; complete user-management UI and security tests remain |
| Settings and backup | App settings, theme persistence, database backup/restore, validation, rollback and restore audit | Backup download exists; safe restore UI and automated restore verification remain |
| Payment settings | Provider placeholders and safe secret configuration for Razorpay, Cashfree, Stripe and PayPal; test/live separation; webhook verification before enabling | Configuration placeholders are not full payment processing; keep checkout disabled until integration and end-to-end verification |
| Data portability | Web-native CSV/Excel import/export, database backup, restore, integrity checks | CSV export baseline; broad import/export and restore remain |

## Acceptance criteria

1. Every visible control performs its advertised action and reports success or a useful error.
2. Create, read, update, delete, search, filtering, sorting and pagination work for every applicable module.
3. Business calculations are server-side, validated, transactional, and covered by regression tests.
4. Reports are generated from the same filters and scope shown in the UI; evidence URLs remain clickable in PDF/DOCX/CSV where supported.
5. Day/night and every wallpaper are readable on desktop, tablet and iPhone-sized screens; preferences persist per web user/device.
6. Scraping is a server-side job with progress, cancellation, safe URL handling, rate limiting, deduplication and source provenance; scraped results are reviewed before saving.
7. Backup/restore is web-database-only, validated, atomic, and retains a rollback backup.
8. CI validates Python tests, frontend syntax/assets, endpoint contracts, and security boundaries.
9. No feature is marked complete until its UI workflow and API behaviour have passed tests.
