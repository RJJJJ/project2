from pathlib import Path
import json
import csv
import argparse


def extract_product_names(
    input_dir: Path,
    output_path: Path,
    category_start: int = 1,
    category_end: int = 18,
):
    seen = set()
    rows = []

    for category_id in range(category_start, category_end + 1):
        file_path = input_dir / f"category_{category_id}_prices.jsonl"

        if not file_path.exists():
            print(f"[WARN] File not found: {file_path}")
            continue

        line_count = 0
        extracted_count = 0

        with file_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                line_count += 1

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    print(f"[WARN] Invalid JSON: {file_path}, line={line_no}")
                    continue

                product_name = record.get("product_name")

                if not product_name:
                    continue

                product_name = str(product_name).strip()

                # 同一個商品名可能在不同 category / point 重複出現
                dedupe_key = (category_id, product_name)

                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                rows.append({
                    "category_id": category_id,
                    "product_name": product_name,
                })
                extracted_count += 1

        print(
            f"[OK] category_{category_id}: "
            f"lines={line_count}, unique_product_names_added={extracted_count}"
        )

    rows.sort(key=lambda x: (x["category_id"], x["product_name"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category_id", "product_name"])
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"[DONE] unique_category_product_names={len(rows)}")
    print(f"[DONE] output_written={output_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Folder containing category_1_prices.jsonl to category_18_prices.jsonl",
    )

    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/analysis/category_1_18_product_names.csv"),
        help="Output CSV path",
    )

    parser.add_argument(
        "--category-start",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--category-end",
        type=int,
        default=18,
    )

    args = parser.parse_args()

    extract_product_names(
        input_dir=args.input_dir,
        output_path=args.output_path,
        category_start=args.category_start,
        category_end=args.category_end,
    )


if __name__ == "__main__":
    main()