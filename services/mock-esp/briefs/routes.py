"""Mock routes for all 8 brief platform APIs.

Each platform sub-router mimics the real API shape so that the
providers in ``app/briefs/providers/`` work without modification.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query, Request

from briefs.data import MOCK_BRIEFS

router = APIRouter(prefix="/briefs", tags=["briefs-mock"])


# ── Helpers ──────────────────────────────────────────────────────────


def _check_auth(authorization: str | None) -> None:
    """Accept any non-empty auth header — this is a mock."""
    if not authorization:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Missing authorization")


def _brief_to_asana_task(brief: dict) -> dict:
    """Convert mock brief to Asana task shape."""
    return {
        "gid": brief["id"],
        "name": brief["title"],
        "notes": brief["description"],
        "html_notes": brief["description"],
        "completed": brief["status"] == "done",
        "assignee": {"name": brief["assignees"][0]} if brief["assignees"] else None,
        "tags": [{"name": lbl} for lbl in brief.get("labels", [])],
        "due_on": brief.get("due_date"),
        "attachments": [],
    }


def _brief_to_jira_issue(brief: dict) -> dict:
    """Convert mock brief to Jira issue shape."""
    status_map = {
        "open": "To Do",
        "in_progress": "In Progress",
        "done": "Done",
        "cancelled": "Cancelled",
    }
    priority_map = {"high": "High", "medium": "Medium", "low": "Low"}
    return {
        "key": brief["id"],
        "fields": {
            "summary": brief["title"],
            "description": brief["description"],
            "status": {"name": status_map.get(brief["status"], "To Do")},
            "priority": {"name": priority_map.get(brief.get("priority", ""), "Medium")},
            "assignee": {"displayName": brief["assignees"][0]} if brief["assignees"] else None,
            "labels": brief.get("labels", []),
            "duedate": brief.get("due_date"),
            "attachment": [],
        },
        "renderedFields": {
            "description": brief["description"],
        },
    }


def _brief_to_clickup_task(brief: dict) -> dict:
    """Convert mock brief to ClickUp task shape."""
    status_map = {
        "open": "to do",
        "in_progress": "in progress",
        "done": "complete",
        "cancelled": "cancelled",
    }
    priority_map = {"high": 1, "medium": 3, "low": 4}
    return {
        "id": brief["id"],
        "name": brief["title"],
        "description": brief["description"],
        "status": {"status": status_map.get(brief["status"], "to do")},
        "priority": {"id": str(priority_map.get(brief.get("priority", ""), 3))},
        "assignees": [{"username": a} for a in brief.get("assignees", [])],
        "tags": [{"name": lbl} for lbl in brief.get("labels", [])],
        "due_date": None,
        "attachments": [],
    }


def _brief_to_trello_card(brief: dict) -> dict:
    """Convert mock brief to Trello card shape."""
    return {
        "id": brief["id"],
        "name": brief["title"],
        "desc": brief["description"],
        "closed": brief["status"] == "done",
        "labels": [{"name": lbl} for lbl in brief.get("labels", [])],
        "due": f"{brief['due_date']}T00:00:00.000Z" if brief.get("due_date") else None,
        "idMembers": [],
        "attachments": [],
    }


def _brief_to_notion_page(brief: dict) -> dict:
    """Convert mock brief to Notion page shape."""
    status_map = {
        "open": "Not Started",
        "in_progress": "In Progress",
        "done": "Done",
        "cancelled": "Cancelled",
    }
    return {
        "id": brief["id"],
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": brief["title"]}],
            },
            "Status": {
                "type": "status",
                "status": {"name": status_map.get(brief["status"], "Not Started")},
            },
            "Assignee": {
                "type": "people",
                "people": [{"name": a} for a in brief.get("assignees", [])],
            },
        },
    }


def _brief_to_wrike_task(brief: dict) -> dict:
    """Convert mock brief to Wrike task shape."""
    status_map = {
        "open": "Active",
        "in_progress": "Active",
        "done": "Completed",
        "cancelled": "Cancelled",
    }
    priority_map = {"high": "High", "medium": "Normal", "low": "Low"}
    return {
        "id": brief["id"],
        "title": brief["title"],
        "description": brief["description"],
        "status": status_map.get(brief["status"], "Active"),
        "importance": priority_map.get(brief.get("priority", ""), "Normal"),
        "responsibleIds": brief.get("assignees", []),
        "dates": {"due": brief.get("due_date")},
        "attachments": [],
    }


def _brief_to_monday_item(brief: dict) -> dict:
    """Convert mock brief to Monday.com item shape."""
    status_map = {"open": "", "in_progress": "Working on it", "done": "Done", "cancelled": "Stuck"}
    return {
        "id": brief["id"],
        "name": brief["title"],
        "column_values": [
            {"id": "status", "text": status_map.get(brief["status"], ""), "type": "status"},
            {
                "id": "person",
                "text": brief["assignees"][0] if brief["assignees"] else "",
                "type": "person",
            },
        ],
        "updates": [{"text_body": brief["description"]}] if brief["description"] else [],
    }


def _brief_to_basecamp_todo(brief: dict) -> dict:
    """Convert mock brief to Basecamp todo shape."""
    return {
        "id": int(brief["id"].replace("BRIEF-", "")),
        "title": brief["title"],
        "content": brief["title"],
        "description": brief["description"],
        "completed": brief["status"] == "done",
        "assignees": [{"name": a} for a in brief.get("assignees", [])],
    }


# ── Asana ────────────────────────────────────────────────────────────


@router.get("/asana/users/me")
async def asana_me(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {"data": {"gid": "mock-user-1", "name": "Mock User", "email": "mock@example.com"}}


@router.get("/asana/projects/{project_id}/tasks")
async def asana_list_tasks(
    project_id: str,  # noqa: ARG001
    authorization: str | None = Header(None),
) -> dict:
    _check_auth(authorization)
    return {"data": [_brief_to_asana_task(b) for b in MOCK_BRIEFS]}


@router.get("/asana/tasks/{task_id}")
async def asana_get_task(task_id: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == task_id:
            return {"data": _brief_to_asana_task(b)}
    return {"data": _brief_to_asana_task(MOCK_BRIEFS[0])}


# ── Jira ─────────────────────────────────────────────────────────────


@router.get("/jira/myself")
async def jira_myself(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {
        "accountId": "mock-user-1",
        "displayName": "Mock User",
        "emailAddress": "mock@example.com",
    }


@router.get("/jira/search")
async def jira_search(
    authorization: str | None = Header(None),
    jql: str | None = Query(None),  # noqa: ARG001
) -> dict:
    _check_auth(authorization)
    return {"issues": [_brief_to_jira_issue(b) for b in MOCK_BRIEFS], "total": len(MOCK_BRIEFS)}


@router.get("/jira/issue/{issue_key}")
async def jira_get_issue(issue_key: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == issue_key:
            return _brief_to_jira_issue(b)
    return _brief_to_jira_issue(MOCK_BRIEFS[0])


# ── ClickUp ──────────────────────────────────────────────────────────


@router.get("/clickup/user")
async def clickup_user(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {"user": {"id": 1, "username": "mock_user", "email": "mock@example.com"}}


@router.get("/clickup/list/{list_id}/task")
async def clickup_list_tasks(list_id: str, authorization: str | None = Header(None)) -> dict:  # noqa: ARG001
    _check_auth(authorization)
    return {"tasks": [_brief_to_clickup_task(b) for b in MOCK_BRIEFS]}


@router.get("/clickup/task/{task_id}")
async def clickup_get_task(task_id: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == task_id:
            return _brief_to_clickup_task(b)
    return _brief_to_clickup_task(MOCK_BRIEFS[0])


# ── Trello ───────────────────────────────────────────────────────────


@router.get("/trello/members/me")
async def trello_me(key: str | None = Query(None), token: str | None = Query(None)) -> dict:  # noqa: ARG001
    return {"id": "mock-user-1", "fullName": "Mock User"}


@router.get("/trello/boards/{board_id}/cards")
async def trello_list_cards(board_id: str) -> list[dict]:  # noqa: ARG001
    return [_brief_to_trello_card(b) for b in MOCK_BRIEFS]


@router.get("/trello/cards/{card_id}")
async def trello_get_card(card_id: str) -> dict:
    for b in MOCK_BRIEFS:
        if b["id"] == card_id:
            return _brief_to_trello_card(b)
    return _brief_to_trello_card(MOCK_BRIEFS[0])


# ── Notion ───────────────────────────────────────────────────────────


@router.get("/notion/users/me")
async def notion_me(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {"id": "mock-user-1", "name": "Mock User", "type": "person"}


@router.post("/notion/databases/{database_id}/query")
async def notion_query_database(database_id: str, authorization: str | None = Header(None)) -> dict:  # noqa: ARG001
    _check_auth(authorization)
    return {"results": [_brief_to_notion_page(b) for b in MOCK_BRIEFS], "has_more": False}


@router.get("/notion/pages/{page_id}")
async def notion_get_page(page_id: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == page_id:
            return _brief_to_notion_page(b)
    return _brief_to_notion_page(MOCK_BRIEFS[0])


@router.get("/notion/blocks/{block_id}/children")
async def notion_get_blocks(block_id: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == block_id:
            return {
                "results": [
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"plain_text": b["description"]}]},
                    }
                ]
            }
    return {"results": []}


# ── Wrike ────────────────────────────────────────────────────────────


@router.get("/wrike/contacts")
async def wrike_contacts(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {"data": [{"id": "mock-user-1", "firstName": "Mock", "lastName": "User"}]}


@router.get("/wrike/folders/{folder_id}/tasks")
async def wrike_list_tasks(folder_id: str, authorization: str | None = Header(None)) -> dict:  # noqa: ARG001
    _check_auth(authorization)
    return {"data": [_brief_to_wrike_task(b) for b in MOCK_BRIEFS]}


@router.get("/wrike/tasks/{task_id}")
async def wrike_get_task(task_id: str, authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        if b["id"] == task_id:
            return {"data": [_brief_to_wrike_task(b)]}
    return {"data": [_brief_to_wrike_task(MOCK_BRIEFS[0])]}


# ── Monday.com ───────────────────────────────────────────────────────


@router.post("/monday")
async def monday_graphql(
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    _check_auth(authorization)
    body = await request.json()
    query: str = body.get("query", "")

    # Auth check query
    if "me" in query and "boards" not in query and "items" not in query:
        return {"data": {"me": {"id": "mock-user-1", "name": "Mock User"}}}

    # Board items query
    if "boards" in query:
        return {
            "data": {
                "boards": [
                    {"items_page": {"items": [_brief_to_monday_item(b) for b in MOCK_BRIEFS]}}
                ]
            }
        }

    # Single item query
    if "items" in query:
        variables = body.get("variables", {})
        item_ids: list[str] = variables.get("itemId", [])
        target_id = item_ids[0] if item_ids else None
        for b in MOCK_BRIEFS:
            if b["id"] == target_id:
                return {"data": {"items": [_brief_to_monday_item(b)]}}
        return {"data": {"items": [_brief_to_monday_item(MOCK_BRIEFS[0])]}}

    return {"data": {}}


# ── Basecamp ─────────────────────────────────────────────────────────


@router.get("/basecamp/authorization.json")
async def basecamp_auth(authorization: str | None = Header(None)) -> dict:
    _check_auth(authorization)
    return {"identity": {"id": 1, "email_address": "mock@example.com"}}


@router.get("/basecamp/buckets/{bucket_id}/todolists.json")
async def basecamp_todolists(
    request: Request, bucket_id: str, authorization: str | None = Header(None)
) -> list[dict]:
    _check_auth(authorization)
    base = str(request.base_url).rstrip("/")
    return [
        {
            "id": 1,
            "name": "Campaign Tasks",
            "todos_url": f"{base}/briefs/basecamp/buckets/{bucket_id}/todolists/1/todos.json",
        }
    ]


@router.get("/basecamp/buckets/{bucket_id}/todolists/1/todos.json")
async def basecamp_todos(bucket_id: str, authorization: str | None = Header(None)) -> list[dict]:  # noqa: ARG001
    _check_auth(authorization)
    return [_brief_to_basecamp_todo(b) for b in MOCK_BRIEFS]


@router.get("/basecamp/buckets/{bucket_id}/todos/{todo_id}.json")
async def basecamp_get_todo(
    bucket_id: str,  # noqa: ARG001
    todo_id: int,
    authorization: str | None = Header(None),
) -> dict:
    _check_auth(authorization)
    for b in MOCK_BRIEFS:
        brief_id = int(b["id"].replace("BRIEF-", ""))
        if brief_id == todo_id:
            return _brief_to_basecamp_todo(b)
    return _brief_to_basecamp_todo(MOCK_BRIEFS[0])
