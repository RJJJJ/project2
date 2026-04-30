from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


@dataclass
class AcceptanceStep:
    name: str
    kind: str
    command: list[str]
    cwd: Path
    skipped: bool = False
    skip_reason: str | None = None


def _python() -> str:
    return sys.executable


def _npm_executable() -> str:
    return "npm.cmd" if sys.platform.startswith("win") else "npm"


def build_final_acceptance_steps(
    db_path: str,
    point_code: str,
    output_dir: str,
    frontend_dir: str = "frontend",
    skip_pytest: bool = False,
    skip_regression: bool = False,
    skip_smoke: bool = False,
    skip_confusion_audit: bool = False,
    skip_frontend_build: bool = False,
) -> list[AcceptanceStep]:
    output_root = Path(output_dir)
    steps: list[AcceptanceStep] = [
        AcceptanceStep(
            name="pytest",
            kind="pytest",
            command=[_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=PROJECT_ROOT,
            skipped=skip_pytest,
            skip_reason="--skip-pytest" if skip_pytest else None,
        ),
        AcceptanceStep(
            name="regression",
            kind="regression",
            command=[
                _python(),
                str(PROJECT_ROOT / "scripts" / "run_agent_regression_pack.py"),
                "--db-path",
                db_path,
                "--point-code",
                point_code,
                "--output-dir",
                "data/eval",
                "--catalog-adversarial-cases-path",
                "data/eval/catalog_adversarial_cases_reviewed.json",
            ],
            cwd=PROJECT_ROOT,
            skipped=skip_regression,
            skip_reason="--skip-regression" if skip_regression else None,
        ),
    ]
    smoke_queries = [
        ("smoke_sugar_shampoo", "我想買砂糖同洗頭水", {"status": "ok"}),
        ("smoke_nissin_brand", "出前一丁", {"query_type": "brand_search"}),
        ("smoke_nissin_sesame", "出前一丁麻油味", {"query_type_in": ["direct_product_search", "partial_product_search"]}),
        ("smoke_egg_not_covered", "雞蛋", {"status": "not_covered"}),
        ("smoke_subjective_noodle", "最好吃的麵", {"status": "unsupported"}),
    ]
    for name, query, _expected in smoke_queries:
        steps.append(
            AcceptanceStep(
                name=name,
                kind="smoke",
                command=[
                    _python(),
                    str(PROJECT_ROOT / "scripts" / "run_shopping_agent.py"),
                    "--query",
                    query,
                    "--db-path",
                    db_path,
                    "--point-code",
                    point_code,
                    "--include-price-plan",
                    "--retrieval-mode",
                    "rag_v2",
                    "--debug-json",
                ],
                cwd=PROJECT_ROOT,
                skipped=skip_smoke,
                skip_reason="--skip-smoke" if skip_smoke else None,
            )
        )
    steps.append(
        AcceptanceStep(
            name="confusion_audit",
            kind="confusion_audit",
            command=[
                _python(),
                str(PROJECT_ROOT / "scripts" / "run_catalog_confusion_audit.py"),
                "--db-path",
                db_path,
                "--output-dir",
                "data/eval",
                "--generate-adversarial-cases",
            ],
            cwd=PROJECT_ROOT,
            skipped=skip_confusion_audit,
            skip_reason="--skip-confusion-audit" if skip_confusion_audit else None,
        )
    )
    steps.append(
        AcceptanceStep(
            name="frontend_build",
            kind="frontend_build",
            command=[_npm_executable(), "run", "build"],
            cwd=Path(frontend_dir),
            skipped=skip_frontend_build,
            skip_reason="--skip-frontend-build" if skip_frontend_build else None,
        )
    )
    output_root.mkdir(parents=True, exist_ok=True)
    return steps


def _tail(text: str, max_lines: int = 20) -> str:
    lines = str(text or "").splitlines()
    return "\n".join(lines[-max_lines:])


def _evaluate_smoke_result(name: str, payload: dict[str, Any]) -> tuple[bool, str]:
    status = str(payload.get("status") or "")
    query_type = str((payload.get("query_router") or {}).get("query_type") or "")
    if name == "smoke_sugar_shampoo":
        return status == "ok", f"status={status}, query_type={query_type}"
    if name == "smoke_nissin_brand":
        return query_type == "brand_search", f"status={status}, query_type={query_type}"
    if name == "smoke_nissin_sesame":
        return query_type in {"direct_product_search", "partial_product_search"}, f"status={status}, query_type={query_type}"
    if name == "smoke_egg_not_covered":
        return status == "not_covered", f"status={status}, query_type={query_type}"
    if name == "smoke_subjective_noodle":
        return status == "unsupported", f"status={status}, query_type={query_type}"
    return False, "unknown smoke step"


def run_acceptance_step(step: AcceptanceStep) -> dict[str, Any]:
    if step.skipped:
        return {"name": step.name, "kind": step.kind, "status": "skipped", "reason": step.skip_reason}
    started = time.time()
    try:
        completed = subprocess.run(
            step.command,
            cwd=str(step.cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        return {
            "name": step.name,
            "kind": step.kind,
            "status": "failed",
            "returncode": None,
            "duration_seconds": round(time.time() - started, 3),
            "error": str(exc),
            "command": step.command,
            "cwd": str(step.cwd),
        }
    result: dict[str, Any] = {
        "name": step.name,
        "kind": step.kind,
        "returncode": completed.returncode,
        "duration_seconds": round(time.time() - started, 3),
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
        "command": step.command,
        "cwd": str(step.cwd),
    }
    if step.kind == "smoke":
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            result["status"] = "failed"
            result["smoke_check"] = {"ok": False, "detail": "invalid JSON output"}
            return result
        ok, detail = _evaluate_smoke_result(step.name, payload)
        result["status"] = "passed" if completed.returncode == 0 and ok else "failed"
        result["smoke_check"] = {"ok": ok, "detail": detail, "result_status": payload.get("status"), "query_type": (payload.get("query_router") or {}).get("query_type")}
        return result
    result["status"] = "passed" if completed.returncode == 0 else "failed"
    return result


def summarize_acceptance_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    smoke = [item for item in results if item.get("kind") == "smoke"]
    smoke_passed = sum(1 for item in smoke if item.get("status") == "passed")
    summary = {
        "pytest": next((item.get("status") for item in results if item.get("kind") == "pytest"), "skipped"),
        "regression": next((item.get("status") for item in results if item.get("kind") == "regression"), "skipped"),
        "smoke_tests": {"passed": smoke_passed, "total": len(smoke), "status": "passed" if smoke and smoke_passed == len(smoke) else ("skipped" if not smoke or all(item.get("status") == "skipped" for item in smoke) else "failed")},
        "confusion_audit": next((item.get("status") for item in results if item.get("kind") == "confusion_audit"), "skipped"),
        "frontend_build": next((item.get("status") for item in results if item.get("kind") == "frontend_build"), "skipped"),
    }
    overall_status = "passed"
    for item in results:
        if item.get("status") == "failed":
            overall_status = "failed"
            break
    summary["overall_status"] = overall_status
    return summary


def write_final_acceptance_outputs(output_dir: str | Path, results: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "final_acceptance_results.json"
    md_path = output_path / "final_acceptance_summary.md"
    json_path.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Final Acceptance Summary",
        "",
        f"- pytest: {summary['pytest']}",
        f"- regression: {summary['regression']}",
        f"- smoke_tests: {summary['smoke_tests']['passed']}/{summary['smoke_tests']['total']} passed",
        f"- confusion_audit: {summary['confusion_audit']}",
        f"- frontend_build: {summary['frontend_build']}",
        f"- overall_status: {summary['overall_status']}",
        "",
        "## Step results",
    ]
    for item in results:
        line = f"- {item['name']}: {item.get('status')}"
        if item.get("kind") == "smoke" and item.get("smoke_check"):
            line += f" ({item['smoke_check'].get('detail')})"
        lines.append(line)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Project2 final acceptance checks.")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--output-dir", default="data/eval/final_acceptance")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--skip-regression", action="store_true")
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--skip-confusion-audit", action="store_true")
    parser.add_argument("--skip-frontend-build", action="store_true")
    parser.add_argument("--frontend-dir", default="frontend")
    args = parser.parse_args()

    steps = build_final_acceptance_steps(
        db_path=args.db_path,
        point_code=args.point_code,
        output_dir=args.output_dir,
        frontend_dir=args.frontend_dir,
        skip_pytest=args.skip_pytest,
        skip_regression=args.skip_regression,
        skip_smoke=args.skip_smoke,
        skip_confusion_audit=args.skip_confusion_audit,
        skip_frontend_build=args.skip_frontend_build,
    )
    results = [run_acceptance_step(step) for step in steps]
    summary = summarize_acceptance_results(results)
    json_path, md_path = write_final_acceptance_outputs(args.output_dir, results, summary)

    print("FINAL ACCEPTANCE SUMMARY")
    print(f"pytest: {summary['pytest']}")
    print(f"regression: {summary['regression']}")
    print(f"smoke_tests: {summary['smoke_tests']['passed']}/{summary['smoke_tests']['total']} passed")
    print(f"confusion_audit: {summary['confusion_audit']}")
    print(f"frontend_build: {summary['frontend_build']}")
    print(f"overall_status: {summary['overall_status']}")
    print("outputs:")
    print(f"- {json_path}")
    print(f"- {md_path}")
    return 0 if summary["overall_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
