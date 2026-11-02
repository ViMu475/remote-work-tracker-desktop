# Privacy (GDPR) — what this repository must never contain

The application processes **personal data**: working times of a real person (and, in the SAP time statements that can be
imported, names, addresses, personnel numbers and e-mail addresses). This repository is source code only.

## What stays out of the repository

| Never commit | Why | Protection |
|---|---|---|
| Time statements and every other **PDF** (`*.pdf`) | contain private addresses and personal data | `.gitignore`, privacy guard |
| Screenshots and images, CSV/Excel/Word exports | show real working times or addresses | `.gitignore`, privacy guard |
| `tracker_state*.json`, backups (`remote_tracker_backup*`, `daily_records_*`) | the person's working times | `.gitignore`, privacy guard |
| `.env` (contains `GOOGLE_API_KEY`) | secret | `.gitignore`, privacy guard |
| Private documentation (`docs/`), `.mcp.json`, `.claude/` | local paths, user names, PDFs | `.gitignore` |
| Real statements for local testing | personal data | put them in `tests/real_statements/` (ignored by Git); the tests use them only if present |

**All test data is fictional** (invented dates, times and names). The PDF import tests generate their PDFs on the fly from
invented text (`tests/test_pdf_service.py`); no real document is needed or included.

## Automatic guard

`python tools/check_privacy.py` scans the files Git would publish and fails on forbidden file types (PDF, images, office
files, CSV, state files, `.env`, archives) and on e-mail addresses, street addresses, postal code + city, phone numbers,
personnel numbers and home directories of real users. It runs

* in the test suite (`tests/test_repo_hygiene.py`, in a Git checkout),
* as the first job of the GitHub Actions workflow (`ci/build-desktop.yml`) — the builds only start when it is green.

Run it yourself before every push. If it reports a file: remove it from the repository **and from the Git history** (a
file that was once committed stays readable in old commits; rewrite the history before publishing).

## What the program does with data

* Everything is stored **locally** in `tracker_state.json` (next to the program, or where `RW_DATA_FILE` points). There is
  no account, no server of the author, no telemetry.
* The program listens on `127.0.0.1` only. Stopping it through the user interface needs a per-run token.
* Importing a time statement reads the PDF **on the computer** (pdfplumber). Only the optional **Gemini fallback**
  (used when the local parser finds nothing and `GOOGLE_API_KEY` is set) uploads the PDF to Google's API. That would
  transfer personal data to a third party: leave `GOOGLE_API_KEY` unset unless you have a legal basis and, where needed, a
  data-processing agreement. The prebuilt programs do **not** contain the Gemini code unless built with
  `RW_BUNDLE_GEMINI=1`.
* Deleting the data: delete `tracker_state.json` (or use "delete all" / "clear history" in the program).

## Rules for contributors

1. Use fictional data in tests, examples and screenshots.
2. Never paste real statements, addresses, names or screenshots into issues, pull requests or commit messages.
3. Run `python tools/check_privacy.py` and the tests before every push.
4. Do not widen `.gitignore` exceptions for data files.
