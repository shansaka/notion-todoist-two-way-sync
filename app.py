import requests
from datetime import datetime, timezone
import time
import os

import smtplib
from email.message import EmailMessage

# -----------------------------
# Email Notification Function
# -----------------------------
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_USER)

def send_error_email(subject, body):
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"📧 Error email sent to {EMAIL_TO}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send error email: {e}", flush=True)

# -----------------------------
# Credentials & Endpoints
# -----------------------------
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

NOTION_URL = "https://api.notion.com/v1/pages"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

TODOIST_TASKS_URL = "https://api.todoist.com/rest/v2/tasks"
TODOIST_PROJECTS_URL = "https://api.todoist.com/rest/v2/projects"
TODOIST_LABELS_URL = "https://api.todoist.com/rest/v2/labels"
TODOIST_HEADERS = {"Authorization": f"Bearer {TODOIST_API_KEY}"}

# -----------------------------
# Safe API Calls with Error Logging
# -----------------------------
def safe_post(url, headers, data):
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print(f"\n❌ POST request to {url} failed!", flush=True)
        print(f"Status code: {e.response.status_code}", flush=True)
        print(f"Response text: {e.response.text}", flush=True)
        print(f"Payload sent: {data}", flush=True)
        raise

def safe_patch(url, headers, data):
    try:
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print(f"\n❌ PATCH request to {url} failed!", flush=True)
        print(f"Status code: {e.response.status_code}", flush=True)
        print(f"Response text: {e.response.text}", flush=True)
        print(f"Payload sent: {data}", flush=True)
        raise

def safe_post_todoist(url, headers, data=None):
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.HTTPError as e:
        print(f"\n❌ Todoist POST request to {url} failed!", flush=True)
        print(f"Status code: {e.response.status_code}", flush=True)
        print(f"Response text: {e.response.text}", flush=True)
        print(f"Payload sent: {data}", flush=True)
        raise

# -----------------------------
# Helper Functions
# -----------------------------
def get_todoist_tasks():
    response = requests.get(TODOIST_TASKS_URL, headers=TODOIST_HEADERS)
    response.raise_for_status()
    return response.json()

def get_todoist_projects():
    response = requests.get(TODOIST_PROJECTS_URL, headers=TODOIST_HEADERS)
    response.raise_for_status()
    return {str(p["id"]): p["name"] for p in response.json()}

def get_todoist_labels():
    response = requests.get(TODOIST_LABELS_URL, headers=TODOIST_HEADERS)
    response.raise_for_status()
    return {l["name"]: l["id"] for l in response.json()}

def query_notion_tasks():
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(query_url, headers=NOTION_HEADERS, json={})
    response.raise_for_status()
    results = response.json()["results"]

    notion_map = {}
    for page in results:
        props = page["properties"]
        todoist_id = None
        if "Todoist ID" in props and props["Todoist ID"]["rich_text"]:
            todoist_id = props["Todoist ID"]["rich_text"][0]["text"]["content"]
        if todoist_id:
            notion_map[todoist_id] = {
                "page_id": page["id"],
                "properties": props
            }
    return notion_map

# -----------------------------
# Build Notion Properties
# -----------------------------
def build_notion_properties(task, project_map, existing_props=None, include_sync_time=True):
    project_name = project_map.get(str(task["project_id"]), "Unknown Project")
    new_start = None
    if task.get("due"):
        if task["due"].get("datetime"):
            new_start = datetime.fromisoformat(task["due"]["datetime"].replace("Z", "+00:00"))
        elif task["due"].get("date"):
            new_start = datetime.fromisoformat(task["due"]["date"])

    start_iso, end_iso = None, None
    if existing_props and "Due Date" in existing_props and existing_props["Due Date"]["date"]:
        existing_date = existing_props["Due Date"]["date"]
        start_str = existing_date.get("start")
        end_str = existing_date.get("end")
        if start_str and end_str:
            start_dt = datetime.fromisoformat(start_str)
            end_dt = datetime.fromisoformat(end_str)
            duration = end_dt - start_dt
            if new_start:
                start_iso = new_start.isoformat()
                end_iso = (new_start + duration).isoformat()
            else:
                start_iso, end_iso = start_str, end_str
        elif start_str:
            start_iso = new_start.isoformat() if new_start else start_str
    else:
        if new_start:
            start_iso = new_start.isoformat()

    due_date_obj = {"date": {"start": start_iso}} if start_iso else None
    if end_iso and due_date_obj:
        due_date_obj["date"]["end"] = end_iso

    labels = [{"name": label} for label in task.get("labels", [])]

    props = {
        "Name": {"title": [{"text": {"content": task["content"]}}]},
        "Done": {"checkbox": task.get("is_completed", False)},
        "Todoist ID": {"rich_text": [{"text": {"content": str(task["id"])}}]},
        "Priority": {"select": {"name": f"P{task['priority']}"}} if task.get("priority") else None,
        "Due Date": due_date_obj,
        "Project": {"select": {"name": project_name}},
        "Labels": {"multi_select": labels}  # labels
    }

    if include_sync_time:
        props["Last Sync Time"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}

    return {k: v for k, v in props.items() if v is not None}


# -----------------------------
# Compare Notion Properties
# -----------------------------
def normalize_datetime(dt_str):
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except Exception:
        return dt_str

def has_changes(existing_props, new_props):
    def get_text(prop, key):
        return (prop.get(key, {}).get("title") or [{}])[0].get("text", {}).get("content", "")

    existing_name = get_text(existing_props, "Name")
    new_name = get_text(new_props, "Name")
    if existing_name != new_name:
        print(f"🔄 Change detected: Name '{existing_name}' → '{new_name}'", flush=True)
        return True

    existing_done = existing_props.get("Done", {}).get("checkbox", False)
    new_done = new_props.get("Done", {}).get("checkbox", False)
    if existing_done != new_done:
        print(f"🔄 Change detected: Done {existing_done} → {new_done}", flush=True)
        return True

    existing_pri = existing_props.get("Priority", {}).get("select", {}).get("name")
    new_pri = new_props.get("Priority", {}).get("select", {}).get("name")
    if (existing_pri or "") != (new_pri or ""):
        print(f"🔄 Change detected: Priority '{existing_pri}' → '{new_pri}'", flush=True)
        return True

    existing_due = existing_props.get("Due Date", {}).get("date") or {}
    new_due = new_props.get("Due Date", {}).get("date") or {}
    if normalize_datetime(existing_due.get("start")) != normalize_datetime(new_due.get("start")):
        print(f"🔄 Change detected: Due start '{existing_due.get('start')}' → '{new_due.get('start')}'", flush=True)
        return True
    if normalize_datetime(existing_due.get("end")) != normalize_datetime(new_due.get("end")):
        print(f"🔄 Change detected: Due end '{existing_due.get('end')}' → '{new_due.get('end')}'", flush=True)
        return True

    existing_proj = existing_props.get("Project", {}).get("select", {}).get("name")
    new_proj = new_props.get("Project", {}).get("select", {}).get("name")
    if (existing_proj or "") != (new_proj or ""):
        print(f"🔄 Change detected: Project '{existing_proj}' → '{new_proj}'", flush=True)
        return True

    existing_labels = set([l["name"] for l in (existing_props.get("Labels", {}).get("multi_select") or [])])
    new_labels = set([l["name"] for l in (new_props.get("Labels", {}).get("multi_select") or [])])
    if existing_labels != new_labels:
        print(f"🔄 Change detected: Labels {existing_labels} → {new_labels}", flush=True)
        return True

    return False


# -----------------------------
# Notion → Todoist Sync
# -----------------------------
def get_notion_tasks_to_sync():
    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(query_url, headers=NOTION_HEADERS, json={
        "filter": {"property": "Need Sync", "checkbox": {"equals": True}}
    })
    response.raise_for_status()
    results = response.json()["results"]

    tasks_to_sync = []
    for page in results:
        props = page["properties"]
        todoist_id = None
        if "Todoist ID" in props and props["Todoist ID"]["rich_text"]:
            todoist_id = props["Todoist ID"]["rich_text"][0]["text"]["content"]

        tasks_to_sync.append({
            "page_id": page["id"],
            "todoist_id": todoist_id,
            "properties": props
        })
    return tasks_to_sync

def update_todoist_task(notion_task):
    tid = notion_task["todoist_id"]
    props = notion_task["properties"]
    data = {}

    if "Name" in props and props["Name"]["title"]:
        data["content"] = props["Name"]["title"][0]["text"]["content"]
    if "Priority" in props and props["Priority"]["select"]:
        priority_str = props["Priority"]["select"]["name"]
        if priority_str.startswith("P"):
            data["priority"] = int(priority_str[1])
    if "Due Date" in props and props["Due Date"]["date"]:
        due = props["Due Date"]["date"]["start"]
        if "T" in due:
            if due.endswith("Z") or "+" in due:
                data["due_datetime"] = due
            else:
                data["due_datetime"] = due + "Z"
        else:
            data["due_date"] = due
    if "Labels" in props:
        label_names = [l["name"] for l in props["Labels"]["multi_select"]]
        label_map = get_todoist_labels()
        label_ids = [label_map[name] for name in label_names if name in label_map]
        data["label_ids"] = label_ids

    if not tid:
        response = safe_post_todoist(TODOIST_TASKS_URL, TODOIST_HEADERS, data)
        new_tid = response.get("id")
        if new_tid:
            safe_patch(f"{NOTION_URL}/{notion_task['page_id']}", NOTION_HEADERS, {
                "properties": {
                    "Todoist ID": {"rich_text": [{"text": {"content": str(new_tid)}}]}
                }
            })
            tid = new_tid
    else:
        if data:
            safe_post_todoist(f"{TODOIST_TASKS_URL}/{tid}", TODOIST_HEADERS, data)
        if "Done" in props:
            if props["Done"]["checkbox"]:
                safe_post_todoist(f"{TODOIST_TASKS_URL}/{tid}/close", TODOIST_HEADERS)
            else:
                safe_post_todoist(f"{TODOIST_TASKS_URL}/{tid}/reopen", TODOIST_HEADERS)

def update_notion_last_sync(page_id):
    data = {
        "properties": {
            "Last Sync Time": {"date": {"start": datetime.now(timezone.utc).isoformat()}}
        }
    }
    safe_patch(f"https://api.notion.com/v1/pages/{page_id}", NOTION_HEADERS, data)

# -----------------------------
# Todoist → Notion Sync
# -----------------------------
def create_notion_task(task, project_map):
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": build_notion_properties(task, project_map)
    }
    safe_post(NOTION_URL, NOTION_HEADERS, data)

def update_notion_task(page_id, task, project_map, existing_props=None):
    new_props = build_notion_properties(task, project_map, existing_props, include_sync_time=False)
    if not has_changes(existing_props, new_props):
        return False

    new_props["Last Sync Time"] = {"date": {"start": datetime.now(timezone.utc).isoformat()}}
    data = {"properties": new_props}
    safe_patch(f"{NOTION_URL}/{page_id}", NOTION_HEADERS, data)
    return True

def sync_tasks():
    todoist_tasks = get_todoist_tasks()
    project_map = get_todoist_projects()
    notion_tasks = query_notion_tasks()

    new_count, update_count = 0, 0

    for task in todoist_tasks:
        tid = str(task["id"])
        if tid not in notion_tasks:
            create_notion_task(task, project_map)
            new_count += 1
        else:
            existing_props = notion_tasks[tid]["properties"]
            updated = update_notion_task(
                notion_tasks[tid]["page_id"],
                task,
                project_map,
                existing_props=existing_props
            )
            if updated:
                update_count += 1

    print(f"✅ Todoist → Notion sync complete. {new_count} new tasks, {update_count} updated.", flush=True)

# -----------------------------
# Two-Way Sync Entry
# -----------------------------
def sync_two_way():
    notion_tasks_to_sync = get_notion_tasks_to_sync()
    for nt in notion_tasks_to_sync:
        update_todoist_task(nt)
        update_notion_last_sync(nt["page_id"])
    print(f"✅ Notion → Todoist sync complete. {len(notion_tasks_to_sync)} tasks updated.", flush=True)

    sync_tasks()

# -----------------------------
# Run every 1 minute
# -----------------------------
if __name__ == "__main__":
    while True:
        print(f"\n⏰ Running sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        try:
            sync_two_way()
        except Exception as e:
            print(f"❌ Error in sync loop: {e}", flush=True)
            send_error_email(
                subject="🚨 Notion-Todoist Sync Error",
                body=f"An error occurred during sync:\n\n{e}"
            )
        print("", flush=True)
        time.sleep(120)
