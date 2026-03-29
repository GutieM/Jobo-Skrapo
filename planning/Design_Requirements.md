# Jobo-Skrapo — Design Requirements

Status: Draft
Version: 0.6
Author: GutieM
Created: 2026-03-28
Last Updated: 2026-03-29

---

## Document Purpose

This document captures the design decisions, methodology evaluations, and technical
requirements established prior to implementation. It serves as the authoritative reference
for why key choices were made and what constraints shaped the architecture of v1.0.

---

## 1. Overview

Jobo-Skrapo is a personal job search automation and scoring tool. It accepts user-defined
weighted criteria, executes browser-automated searches against job listing sites, scores
each result against those criteria, and produces ranked HTML reports. A Report Compiler
then aggregates results across multiple searches into a single deduplicated master output.

The goal is precision over volume. The tool does not simply filter — it scores, ranks,
and surfaces the most relevant listings so the user can make informed decisions without
manually reviewing dozens of irrelevant postings.

The tool is designed for a single user running it locally via a GUI. There is no backend,
no database, and no authentication layer. Simplicity and reliability are prioritized over
feature breadth in v1.0.

---

## 2. Scope

In scope (v1.0):
- Browser automation against Indeed
- Weighted scoring engine (required / semi-helpful / concerning term categories)
- Regex-flexible criteria matching including term lists
- Multiple search queries per session
- Per-query ranked HTML report output
- Report Compiler — cross-query deduplication, re-scoring, master report output
- GUI for search configuration and file selection
- Default criteria file shipped with the application
- Custom criteria input via .txt file

In scope (v2.0+):
- Expanded site support (LinkedIn, Glassdoor, etc.)
- YAML / JSON criteria input format (flexible pending security testing)
- Additional scoring customization

Out of scope:
- Authenticated job applications
- Resume parsing or submission
- Real-time alerting or scheduling
- Cloud hosting or multi-user access

---

## 3. Site Integration — Methodology Decision

### 3.1 Indeed API
Evaluated and rejected. The free public Publisher API was deprecated circa 2020.
Current API access requires an official Indeed partnership and is not publicly available.

Decision: Not viable for this project.

### 3.2 Browser Automation — Selenium vs Playwright

Evaluation criteria: speed, reliability on JS-rendered content, anti-bot resilience,
Python support, setup complexity, and industry trajectory.

Selenium:
- Dominant in existing enterprise test suites
- Requires manual wait handling
- More detectable by anti-bot measures
- Higher setup complexity

Playwright:
- Built-in auto-waiting
- Better handling of JS-rendered pages
- Lower anti-bot detectability
- Simpler setup
- Growing adoption in modern test stacks

Decision: Playwright selected for v1.0.
Rationale: Indeed renders listings dynamically via JavaScript. Playwright handles this
more reliably than Selenium and requires less boilerplate for wait management.

### 3.3 ToS Consideration
Direct scraping may conflict with Indeed's Terms of Service. This tool is intended for
personal, non-commercial use only. A disclaimer is included in the README.

---

## 4. Text Extraction and Filtering Stack

### 4.1 HTML Parsing
Playwright provides direct DOM access via locators and selectors, returning clean extracted
text from targeted page elements. This eliminates the need for a separate HTML parsing
library in the standard flow — regex scoring runs against text extracted directly by Playwright.

Approved fallback: BeautifulSoup4
If Playwright's native DOM querying proves insufficient against Indeed's actual page structure
(e.g. deeply nested or dynamically keyed markup), BeautifulSoup4 is approved for addition.
It is not a leading dependency and should not be added until a specific need is confirmed
during Phase 3. If added, lxml is available as a faster BS4 backend.

### 4.2 Pattern Matching
Primary: Python re (standard library)
- Regex-based matching against criteria file terms
- Exact match, pattern match, and list-based matching supported
- Term list example: all US state initials as a single regex alternation

Rejected: rapidfuzz
Rationale: Fuzzy matching introduces accuracy risk. Precision of scoring is a core
requirement. Deferred to future consideration.

Future consideration: spell-check package for criteria file preprocessing (not v1.0)

### 4.3 URL Handling
Standard library urllib.parse for URL normalization and deduplication.

---

## 5. Scoring System

### 5.1 Overview
Each listing is scored by matching its extracted text content against the three categories
defined in the user's criteria file. Scores are accumulated per listing and used to rank
results in the output report.

### 5.2 Categories and Weights

All weights are user-configurable. The following are defaults:

Required terms:
- Default weight: +5 per match occurrence
- Example: "WFA" appears 10 times in a listing = +50

Semi-helpful terms:
- Default weight: +1 per match occurrence
- Example: "remote" appears 3 times = +3

Concerning terms:
- Default weight: -3 per match occurrence
- Reduces total score to penalize unwanted signals
- Example: US state initials list — any on-site location reference reduces score

### 5.3 Regex-Flexible Term Lists
Concerning term entries support regex patterns and grouped alternations.
Example: a single entry referencing all US state initials fires once per state match found,
applying the negative weight each time.

This allows a single criteria entry to cover broad exclusion patterns without requiring
individual lines per term.

### 5.4 Score Threshold
No minimum floor. All scored listings are included in output and sorted by score descending.
Rationale: scoring behavior cannot be fully anticipated across different user criteria
configurations. Enforcing a floor would risk hiding results that are valid under a
user's custom weighting scheme. The user determines relevance by reviewing the ranked list.

---

## 6. Input File — Format and Security

### 6.1 Primary Format: .txt
A plain text criteria file structured in three labeled sections:
- Required
- Semi-helpful
- Concerning

A default file (default_criteria.txt) ships with the application and serves as a working
starting point for first-time users and for testing.

### 6.2 Backup Formats: YAML / JSON
If plain text input is rejected as a security risk during development or testing, YAML
and JSON will be supported as structured alternatives. These formats provide schema
validation and reduce injection surface area.

Decision: .txt as primary for accessibility; YAML/JSON as fallback if security concerns
are not resolvable at the parsing layer.

### 6.3 Security — Input Injection Risks
User-supplied content is parsed and used to build regex patterns and search queries.
The following risks must be mitigated before v1.0 release:

ReDoS (Regex Denial of Service):
- Malformed or adversarial regex patterns in criteria file could cause catastrophic backtracking
- Mitigation: validate and compile all patterns at load time with error handling;
  reject patterns that fail compilation; consider pattern complexity limits

URL injection:
- Terms interpolated into search query URLs must be encoded
- Mitigation: urllib.parse.quote for all user-supplied query parameters

HTML output injection (XSS):
- Listing content written into HTML reports must be escaped
- Mitigation: use Jinja2 templating with autoescaping enabled; never write raw
  listing content into HTML via string concatenation

Input length and character limits:
- Enforce maximum term length and file size limits at parse time
- Reject files exceeding defined thresholds with a clear error message

---

## 7. Output Format — HTML Report

### 7.1 Rationale
HTML selected as the output format for the following reasons:
- Opens in any browser — no additional software required
- Supports clickable links natively
- Supports visual indicators (checkmarks, color, badges) without complex rendering
- Most accessible format for non-technical users
- Easily archived, shared, or printed

### 7.2 Per-Query Report Contents
Each search query generates one HTML report containing:
- Query label (e.g. "Search: SDET")
- Date and time of run
- Total listings evaluated
- Top N results sorted by score (cap: user-defined, max 1000)
- Per listing:
  - Total score
  - Clickable URL
  - Job title and company name (if extractable)
  - Description snippet
  - Positive indicators first — green checkmarks for required/semi-helpful terms found
  - Negative indicators after — red flags for concerning terms found
  - Display order rationale: surfaces listing strengths before penalties;
    report reads as a ranked recommendation, not an audit

### 7.3 HTML Templating
Selected: Jinja2
Rationale: Standard Python templating library. Autoescaping prevents XSS from listing
content. Separates report structure from data logic cleanly.

### 7.4 Report Compiler
The Report Compiler is a secondary processing step that operates on completed per-query
reports.

Function:
- Ingests all per-query HTML reports from a session
- Deduplicates listings (by URL)
- Re-applies scoring against the same criteria file
- Re-sorts by score across the full combined pool
- Outputs a single master HTML report

Rationale: Users running multiple search queries (e.g. "Marketing Director",
"Marketing Manager", "VP of Marketing") will receive overlapping results. The compiler
removes duplicates and produces a single prioritized view without requiring the user
to manually cross-reference multiple reports.

Deduplication logic: Detail design deferred to the reporting phase. Primary signal
expected to be URL-based. Secondary signals (title + company composite) to be
evaluated during that phase.

---

## 8. GUI

### 8.1 Scope
A GUI is required for v1.0. The tool must be usable by non-technical users without
requiring command line interaction.

### 8.2 GUI Responsibilities
- Criteria file selection (default or custom)
- Search query input (one or more queries per session)
- Result cap configuration (10–1000)
- Additional search parameter input (location, job type, etc.)
- Session launch ("Start SKRAPOing")
- Report output directory selection or display

### 8.3 Portability Requirement
The application must run as a portable local desktop application. No backend server,
no web framework, no hosted dependencies. Users should be able to run it on their
machine without any infrastructure setup beyond Python and the defined dependencies.

Web-based GUI (Flask, FastAPI, etc.) is explicitly rejected — it introduces backend
requirements and breaks the portable, self-contained goal.

### 8.4 Framework
Selected: tkinter
Rationale: Python standard library — no additional install required. Keeps the dependency
footprint minimal and the application fully portable. Sufficient for the GUI scope defined
in v1.0. Allows GUI development and iteration without introducing a heavyweight framework.

Rejected: PyQt / PySide — capable and polished but adds a significant external dependency
that conflicts with the portability goal.

### 8.5 Session Persistence
The GUI will persist the last session configuration between runs.

Scope of persistence (v1.0):
- Last criteria file path used
- Last search queries entered
- Last result cap setting

Extended persistence (reporting phase — deferred):
- File structure for organizing and navigating saved search sessions
- Caching of prior results to avoid redundant searches
- Management of historical reports
- Detail design for this area is deferred until the reporting phase is reached in development.

---

## 9. Development Phases

Implementation will follow this sequence. Design and planning precede all coding.

Phase 1 — Design (current):
- Architecture decisions documented
- Design requirements established before any code is written
- Default criteria file drafted
- Test plan written once core logic is defined

Phase 2 — Core parsing logic:
- First coding phase
- HTML content extraction via Playwright DOM selectors and locators
- Scoring engine (re + weighting logic)
- Input file parser and validator (criteria file loading, security mitigations)
- URL normalization utilities
- Unit tests written against this layer in isolation from browser

Phase 3 — Browser integration:
- Playwright search execution
- DOM selector module (isolated for maintainability)
- Integration with scoring engine
- Integration tests (live browser required)

Phase 4 — Report generation:
- Per-query HTML report output (Jinja2)
- Report Compiler
- Session file structure and persistence design
- Caching and saved search management

Phase 5 — GUI:
- Desktop GUI implementation (tkinter)
- Session persistence wired to GUI
- End-to-end testing

---

## 10. Dependencies

Production (install required):
- playwright — browser automation
- jinja2 — HTML report templating with autoescaping

Standard library (no install):
- tkinter — GUI framework
- re — pattern matching
- urllib.parse — URL normalization and query encoding

Approved, not yet added (Phase 3 evaluation):
- beautifulsoup4 — approved fallback if Playwright DOM querying proves insufficient
- lxml — faster BS4 backend if BS4 is added

Development / Testing (install required):
- pytest — unit and integration testing
- bandit — static security analysis
- safety — dependency vulnerability scanning

---

## 11. Known Constraints and Risks

Site stability:
- Indeed page structure changes may break DOM selectors without notice
- No official API means no version contract — the integration is inherently fragile
- Mitigation: isolate all DOM selectors into a single module for easier maintenance

Testing:
- Integration tests require a live browser instance — Indeed responses cannot be mocked
- Unit tests can cover scoring, parsing, and filtering logic independently of the browser layer
- CI/CD pipeline must include a Playwright browser installation step

Legal / ethical:
- Direct scraping may conflict with Indeed's Terms of Service
- Tool is scoped to personal, non-commercial use only
- Disclaimer is included in README
- ToS compliance is the responsibility of the end user

Security:
- User-supplied criteria file is a potential injection surface (ReDoS, URL injection, XSS)
- All mitigations documented in Section 6.3
- No credentials, API keys, or user data are stored or transmitted
- Static analysis (bandit) and dependency scanning (safety) included in dev toolchain
- .env and secrets patterns covered in .gitignore from project inception

---

## 12. Open Questions

Report Compiler — deduplication detail:
- Full deduplication design deferred to Phase 4 (reporting phase).
- URL as primary signal is assumed. Secondary composite key to be evaluated then.

---

## 13. Revision History

- 0.1 / 2026-03-28 / GutieM — Initial draft. Pre-implementation design decisions captured.
- 0.2 / 2026-03-28 / GutieM — Expanded with full scoring system, input file spec, HTML output
  format, Report Compiler, GUI scope, and security threat model.
- 0.3 / 2026-03-28 / GutieM — Scoring weights confirmed as user-configurable. Defaults locked:
  +5 required, +1 semi-helpful, -3 concerning. Report display order defined: positive
  indicators before negative flags.
- 0.4 / 2026-03-29 / GutieM — Score threshold resolved (no floor). GUI confirmed as portable
  desktop application, web-based approach rejected. Session persistence confirmed with extended
  file/cache management deferred to reporting phase. Development phases documented. Report
  Compiler deduplication detail deferred to Phase 4.
- 0.5 / 2026-03-29 / GutieM — GUI framework resolved: tkinter selected. PyQt/PySide rejected.
  Section numbering corrected. Dependencies section updated to reflect all confirmed packages.
- 0.6 / 2026-03-29 / GutieM — BeautifulSoup4 demoted from confirmed dependency to approved
  fallback. Playwright native DOM querying established as primary extraction approach.
  BS4/lxml retained in approved list pending Phase 3 evaluation. Typo fix in Section 2.
