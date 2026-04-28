# Collection Points Discovery

## 1. Why 45 points

Project2 currently ships a stable 15-point demo dataset. For government demo / public beta, wider geographic coverage is more important than account-system work. The Consumer Council supermarket page exposes collection-centre coordinates through browser network requests when a user changes the map/search area.

## 2. Browser capture tool

The capture tool opens the Consumer Council supermarket page with Playwright and listens for network requests containing `/itemsPrice/by_condition`. It extracts `cet=lat,lng`, `dst`, `categories`, `lang`, and related query parameters into UTF-8 JSONL.

```powershell
python scripts\discover_collection_points_from_browser.py --manual --output data\discovery\collection_points_capture.jsonl
```

Default page:

```text
https://api03.consumer.gov.mo/app/supermarket/main?me=&r=400&st=2&lang=cn&ctntype=2&ctnn=&plt=web
```

If the page changes, pass a replacement URL with `--url`.

## 3. Manual capture flow

1. Run the capture script.
2. In the opened browser, click 「查看更多」.
3. Select a district / location.
4. Click 「確定修改」.
5. Watch the terminal for a captured `lat/lng/dst` line.
6. Repeat until around 45 unique locations are captured.
7. Press Ctrl+C when done; the script prints a JSON summary.

Manual mode is the primary supported workflow because page selectors may change. The script does not require manually copying Network URLs.

## 4. Build candidate config

```powershell
python scripts\build_collection_points_candidate_config.py --capture-path data\discovery\collection_points_capture.jsonl --output-config data\discovery\collection_points_45_candidate.json
```

This creates a reviewable candidate file only. It does **not** overwrite `config/collection_points.json`.

## 5. Manually review names and districts

Browser requests may only contain coordinates. To add names/districts, create:

```text
data/discovery/collection_point_names.csv
```

CSV columns:

```text
point_code,name,district,lat,lng,dst,notes
```

Then rebuild:

```powershell
python scripts\build_collection_points_candidate_config.py --capture-path data\discovery\collection_points_capture.jsonl --names-csv data\discovery\collection_point_names.csv --output-config data\discovery\collection_points_45_candidate.json
```

Unnamed points are generated as `candidate_001`, `待命名地點 001`, `待確認` and must be reviewed before merging into the real config.

## 6. Plan 45-point expansion

```powershell
python scripts\plan_45_point_expansion.py --candidate-config data\discovery\collection_points_45_candidate.json --max-points 45 --categories 1-19
```

The planner reports point count, missing names, `dst` values, estimated API requests, and recommended commands.

## 7. Fetch / coverage / SQLite import after review

Dry-run first:

```powershell
python scripts\fetch_full_category_points.py --max-points 45 --categories 1-19 --config data\discovery\collection_points_45_candidate.json --dry-run
```

Then, only after review:

```powershell
python scripts\fetch_full_category_points.py --max-points 45 --categories 1-19 --config data\discovery\collection_points_45_candidate.json
python scripts\generate_full_category_coverage_report.py --max-points 45 --config data\discovery\collection_points_45_candidate.json
python scripts\import_processed_to_sqlite.py --date latest --max-points 45 --config data\discovery\collection_points_45_candidate.json
```

## 8. Git and data safety

- Do not directly commit raw `data/discovery` capture JSONL unless confirmed safe to publish.
- Do not directly overwrite `config/collection_points.json`; use the candidate file for review first.
- Do not commit `data/raw`, `data/processed`, browser cache, screenshots, or SQLite DB files.
- Whether 45-point `demo_data/processed` should be committed depends on final data size and release needs.
