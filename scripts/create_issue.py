from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

import requests


def issue_exists(issues: List[Dict], title: str) -> bool:
    return any(issue.get("title") == title for issue in issues)


def find_issue_by_title(issues: List[Dict], title: str) -> Dict | None:
    for issue in issues:
        if issue.get("title") == title:
            return issue
    return None


def load_report_payload(report_json_path: str) -> Dict:
    return json.loads(Path(report_json_path).read_text(encoding="utf-8"))


def fetch_existing_issues(repo: str, token: str) -> List[Dict]:
    response = requests.get(
        f"https://api.github.com/repos/{repo}/issues",
        params={"state": "all", "per_page": 100},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_issue(repo: str, token: str, title: str, body: str, labels: List[str]) -> Dict:
    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": labels},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def update_issue(repo: str, token: str, issue_number: int, title: str, body: str, labels: List[str]) -> Dict:
    response = requests.patch(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"title": title, "body": body, "labels": labels},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    report_json_path = os.environ.get("REPORT_JSON_PATH", "output/report.json")
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]

    payload = load_report_payload(report_json_path)
    issues = fetch_existing_issues(repo, token)
    existing = find_issue_by_title(issues, payload["title"])
    if existing:
        updated = update_issue(repo, token, existing["number"], payload["title"], payload["body"], payload.get("labels", []))
        print(f"Issue 已更新: #{updated['number']} {updated['html_url']}")
        return

    created = create_issue(repo, token, payload["title"], payload["body"], payload.get("labels", []))
    print(f"Issue 创建成功: #{created['number']} {created['html_url']}")


if __name__ == "__main__":
    main()
