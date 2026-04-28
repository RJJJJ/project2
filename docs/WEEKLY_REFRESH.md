# Weekly Refresh Workflow

澳門消費者委員會價格資料通常每星期三更新。Project2 建議每週三資料更新後執行 weekly refresh，重新抓取 15 個採集點的完整分類資料、驗證 coverage、匯入 SQLite，並產生報告。

## 手動執行

```powershell
Set-Location D:\project2
.\venv\Scripts\Activate.ps1
python scripts\weekly_data_refresh.py --max-points 15 --categories 1-19
```

## 更新線上 demo fallback data

只有需要更新 `demo_data/processed` 給部署 fallback 使用時才加 `--sync-demo-data`：

```powershell
python scripts\weekly_data_refresh.py --max-points 15 --categories 1-19 --sync-demo-data
```

## 執行後檢查

- `WEEKLY_REFRESH_REPORT.md`
- `data/reports/weekly_refresh_report.json`
- `FULL_CATEGORY_COVERAGE_REPORT.md`
- `data/reports/full_category_coverage_report.json`
- `data/app_state/project2_dev.sqlite3`

## 不應 commit

- `data/raw`
- `data/processed`
- `data/app_state/project2_dev.sqlite3`

## 可 commit

如果使用 `--sync-demo-data`，可審核後 commit：

- `demo_data/processed`
- `WEEKLY_REFRESH_REPORT.md`
- `data/reports/weekly_refresh_report.json`
- `FULL_CATEGORY_COVERAGE_REPORT.md`
- `data/reports/full_category_coverage_report.json`

## Windows Task Scheduler 建議

本 repo 不會自動建立排程。若要自動化，可用 Windows Task Scheduler 每週三晚上（例如 20:00）執行 PowerShell 腳本，腳本內容可呼叫：

```powershell
Set-Location D:\project2
.\venv\Scripts\Activate.ps1
python scripts\weekly_data_refresh.py --max-points 15 --categories 1-19
```

如果要同步 demo fallback，請明確改成加上 `--sync-demo-data`，並在事後檢查 git diff。
