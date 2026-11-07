#!/usr/bin/env python3
"""CLI Jira tối giản cho agent — thay cho Jira MCP. Chỉ dùng thư viện chuẩn Python.

Cấu hình trong file .env ở gốc repo (KHÔNG commit):
    JIRA_BASE_URL=https://<site>.atlassian.net
    JIRA_EMAIL=ban@example.com
    JIRA_API_TOKEN=xxxxxxxx
    JIRA_PROJECT=SCRUM

Lệnh (kết quả in ra JSON):
    whoami                                  kiểm tra kết nối
    get KEY                                 chi tiết ticket + comment + subtask
    search "JQL" [--max N]                  tìm ticket
    comment KEY "nội dung" | --file F | -   thêm comment ("-" = đọc stdin)
    create --type Story|Task|Subtask --summary S [--parent KEY]
           [--description D | --description-file F] [--labels a,b]
           [--assignee ID|@parent|@KEY] [--link KEY]   (@KEY = người được giao của KEY; --link = "relates to" KEY)
    transition KEY "In Review"              chuyển trạng thái theo tên cột
    label KEY [--add a,b] [--remove c]      thêm/bớt label
    sprints                                 liệt kê sprint của board
    move-to-sprint SPRINT_ID KEY [KEY ...]  đưa ticket vào sprint
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ---------- cấu hình ----------
def load_env():
    for folder in (Path.cwd(), Path(__file__).resolve().parent.parent):
        env = folder / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


load_env()
BASE = os.getenv("JIRA_BASE_URL", "").rstrip("/")
EMAIL = os.getenv("JIRA_EMAIL", "")
TOKEN = os.getenv("JIRA_API_TOKEN", "")
PROJECT = os.getenv("JIRA_PROJECT", "SCRUM")


def die(msg, code=1):
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


# ---------- HTTP ----------
def call(method, path, body=None):
    if not (BASE and EMAIL and TOKEN):
        die("Thiếu JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN trong .env")
    auth = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} {method} {path}: {e.read().decode()[:500]}")
    except urllib.error.URLError as e:
        die(f"Không kết nối được {BASE}: {e.reason}")


# ---------- trường tùy biến (story point, sprint) ----------
_fields = None


def field_id(*names):
    global _fields
    if _fields is None:
        _fields = call("GET", "/rest/api/2/field")
    wanted = {n.lower() for n in names}
    for f in _fields:
        if f.get("name", "").lower() in wanted:
            return f["id"]
    return None


def sp_field():
    return os.getenv("JIRA_SP_FIELD") or field_id("Story point estimate", "Story Points")


def sprint_field():
    return field_id("Sprint")


# ---------- rút gọn issue ----------
def slim(issue):
    f = issue.get("fields", {})
    sp, sf = sp_field(), sprint_field()
    sprints = f.get(sf) or [] if sf else []
    return {
        "key": issue["key"],
        "type": (f.get("issuetype") or {}).get("name"),
        "summary": f.get("summary"),
        "status": (f.get("status") or {}).get("name"),
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "assignee_id": (f.get("assignee") or {}).get("accountId"),
        "labels": f.get("labels", []),
        "story_points": f.get(sp) if sp else None,
        "sprint": [s.get("name") for s in sprints if isinstance(s, dict)],
        "parent": (f.get("parent") or {}).get("key"),
        "updated": f.get("updated"),
    }


def base_fields():
    return [x for x in ["summary", "status", "issuetype", "assignee", "labels",
                        "parent", "updated", sp_field(), sprint_field()] if x]


# ---------- lệnh ----------
def cmd_whoami(_):
    me = call("GET", "/rest/api/2/myself")
    return {"ok": True, "name": me.get("displayName"), "email": me.get("emailAddress"),
            "base_url": BASE, "project": PROJECT}


def cmd_get(a):
    fields = base_fields() + ["description", "subtasks", "issuelinks"]
    issue = call("GET", f"/rest/api/2/issue/{a.key}?fields={','.join(fields)}")
    out = slim(issue)
    f = issue["fields"]
    out["description"] = f.get("description") or ""
    out["subtasks"] = [{"key": s["key"], "summary": s["fields"]["summary"],
                        "status": s["fields"]["status"]["name"]} for s in f.get("subtasks", [])]
    out["links"] = []
    for l in f.get("issuelinks", []):
        other, rel = (l["outwardIssue"], l["type"]["outward"]) if "outwardIssue" in l else (l["inwardIssue"], l["type"]["inward"])
        out["links"].append({"relation": rel, "key": other["key"], "summary": other["fields"]["summary"],
                             "status": other["fields"]["status"]["name"]})
    cm = call("GET", f"/rest/api/2/issue/{a.key}/comment?maxResults=100&orderBy=created")
    out["comments"] = [{"author": (c.get("author") or {}).get("displayName"),
                        "created": c.get("created"), "body": c.get("body")}
                       for c in cm.get("comments", [])]
    return out


def cmd_search(a):
    items, token = [], None
    while len(items) < a.max:
        body = {"jql": a.jql, "fields": base_fields(), "maxResults": min(100, a.max - len(items))}
        if token:
            body["nextPageToken"] = token
        res = call("POST", "/rest/api/2/search/jql", body)
        items += [slim(i) for i in res.get("issues", [])]
        token = res.get("nextPageToken")
        if not token or res.get("isLast"):
            break
    return {"count": len(items), "issues": items}


def read_text(text, file):
    if file:
        return Path(file).read_text(encoding="utf-8")
    if text == "-":
        return sys.stdin.read()
    return text or ""


def cmd_comment(a):
    body = read_text(a.text, a.file)
    if not body.strip():
        die("Comment rỗng")
    c = call("POST", f"/rest/api/2/issue/{a.key}/comment", {"body": body})
    return {"ok": True, "key": a.key, "comment_id": c.get("id")}


def cmd_create(a):
    fields = {"project": {"key": PROJECT}, "summary": a.summary,
              "issuetype": {"name": a.type},
              "description": read_text(a.description, a.description_file)}
    if a.parent:
        fields["parent"] = {"key": a.parent}
    if a.labels:
        fields["labels"] = [x.strip() for x in a.labels.split(",") if x.strip()]
    if a.assignee and a.assignee.startswith("@"):
        src = a.parent if a.assignee == "@parent" else a.assignee[1:]
        if not src:
            die("--assignee @parent cần --parent")
        pid = (call("GET", f"/rest/api/2/issue/{src}?fields=assignee")["fields"].get("assignee") or {}).get("accountId")
        if pid:
            fields["assignee"] = {"accountId": pid}
    elif a.assignee:
        fields["assignee"] = {"accountId": a.assignee}
    res = call("POST", "/rest/api/2/issue", {"fields": fields})
    out = {"ok": True, "key": res.get("key")}
    if a.link:
        call("POST", "/rest/api/2/issueLink", {"type": {"name": "Relates"},
             "inwardIssue": {"key": res["key"]}, "outwardIssue": {"key": a.link}})
        out["linked_to"] = a.link
    return out


def cmd_transition(a):
    ts = call("GET", f"/rest/api/2/issue/{a.key}/transitions")["transitions"]
    target = a.status.lower()
    match = next((t for t in ts if t["to"]["name"].lower() == target or t["name"].lower() == target), None)
    if not match:
        die(f"Không chuyển được sang '{a.status}'. Có thể chuyển sang: {[t['to']['name'] for t in ts]}")
    call("POST", f"/rest/api/2/issue/{a.key}/transitions", {"transition": {"id": match["id"]}})
    return {"ok": True, "key": a.key, "status": match["to"]["name"]}


def cmd_label(a):
    ops = [{"add": x.strip()} for x in (a.add or "").split(",") if x.strip()]
    ops += [{"remove": x.strip()} for x in (a.remove or "").split(",") if x.strip()]
    if not ops:
        die("Cần --add hoặc --remove")
    call("PUT", f"/rest/api/2/issue/{a.key}", {"update": {"labels": ops}})
    return {"ok": True, "key": a.key, "changes": ops}


def board_id():
    boards = call("GET", f"/rest/agile/1.0/board?projectKeyOrId={PROJECT}").get("values", [])
    if not boards:
        die(f"Không tìm thấy board của project {PROJECT}")
    return boards[0]["id"]


def cmd_sprints(_):
    res = call("GET", f"/rest/agile/1.0/board/{board_id()}/sprint?state=active,future,closed&maxResults=50")
    return {"sprints": [{"id": s["id"], "name": s["name"], "state": s["state"],
                         "start": s.get("startDate"), "end": s.get("endDate")}
                        for s in res.get("values", [])]}


def cmd_move_to_sprint(a):
    call("POST", f"/rest/agile/1.0/sprint/{a.sprint_id}/issue", {"issues": a.keys})
    return {"ok": True, "sprint_id": a.sprint_id, "issues": a.keys}


def main():
    p = argparse.ArgumentParser(description="CLI Jira cho agent (thay Jira MCP)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    s = sub.add_parser("get"); s.add_argument("key")
    s = sub.add_parser("search"); s.add_argument("jql"); s.add_argument("--max", type=int, default=100)
    s = sub.add_parser("comment"); s.add_argument("key"); s.add_argument("text", nargs="?"); s.add_argument("--file")
    s = sub.add_parser("create")
    s.add_argument("--type", required=True, choices=["Story", "Task", "Subtask", "Epic"])
    s.add_argument("--summary", required=True); s.add_argument("--parent")
    s.add_argument("--description"); s.add_argument("--description-file")
    s.add_argument("--labels"); s.add_argument("--assignee"); s.add_argument("--link")
    s = sub.add_parser("transition"); s.add_argument("key"); s.add_argument("status")
    s = sub.add_parser("label"); s.add_argument("key"); s.add_argument("--add"); s.add_argument("--remove")
    sub.add_parser("sprints")
    s = sub.add_parser("move-to-sprint"); s.add_argument("sprint_id", type=int); s.add_argument("keys", nargs="+")
    a = p.parse_args()
    handler = globals()["cmd_" + a.cmd.replace("-", "_")]
    print(json.dumps(handler(a), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
