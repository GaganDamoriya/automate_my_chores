"""Mock Google Sheets connector."""
def compute_weekly_metrics(report: dict) -> dict:
    done = report.get("done_count", 0)
    summary = f"Weekly Engineering Report: {done} tickets completed."
    return {"sheet": "Eng Weekly Metrics", "tickets_done": done, "summary": summary}


def clean_customer_csv(download: dict) -> dict:
    """Dedupe + normalize a downloaded customer CSV (deterministic mock)."""
    rows_in = int(download.get("rows", 128))
    duplicates = max(1, rows_in // 8)
    rows_out = rows_in - duplicates
    summary = f"Customer CSV Cleanup: {rows_out} rows cleaned ({duplicates} duplicates removed)."
    return {"sheet": "Customer Master", "rows_in": rows_in,
            "duplicates_removed": duplicates, "rows_out": rows_out, "summary": summary}
