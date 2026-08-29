"""Mock Gmail connector."""
def download_attachment(query: str = "eng_report.csv") -> dict:
    return {"file": query, "rows": 128, "source": "gmail"}
