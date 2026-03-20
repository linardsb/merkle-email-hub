"""Seed data for mock brief platforms — realistic campaign brief items."""

from __future__ import annotations

MOCK_BRIEFS: list[dict] = [
    {
        "id": "BRIEF-001",
        "title": "Spring Collection Launch Email",
        "description": "<p>Design and develop the hero email for the Spring 2026 collection launch. "
        "Must include product carousel, CTA to shop page, and countdown timer.</p>"
        "<ul><li>Target: loyalty members</li><li>Send date: April 1</li>"
        "<li>A/B test subject lines</li></ul>",
        "status": "in_progress",
        "priority": "high",
        "assignees": ["Sarah Chen", "Mike Torres"],
        "labels": ["campaign", "seasonal", "high-priority"],
        "due_date": "2026-04-01",
    },
    {
        "id": "BRIEF-002",
        "title": "Welcome Series — Email 3 Redesign",
        "description": "<p>Redesign the third email in the welcome series. Current version has "
        "low engagement. Needs new hero image, updated copy, and mobile-first layout.</p>",
        "status": "open",
        "priority": "medium",
        "assignees": ["Alex Kim"],
        "labels": ["automation", "redesign"],
        "due_date": "2026-03-28",
    },
    {
        "id": "BRIEF-003",
        "title": "Abandoned Cart Recovery — Dark Mode Fix",
        "description": "<p>Fix dark mode rendering issues in the abandoned cart email. "
        "Logo and CTA buttons are invisible in Outlook dark mode.</p>",
        "status": "open",
        "priority": "high",
        "assignees": ["Jordan Lee"],
        "labels": ["bug", "dark-mode", "outlook"],
        "due_date": "2026-03-22",
    },
    {
        "id": "BRIEF-004",
        "title": "Monthly Newsletter — March Edition",
        "description": "<p>Assemble the March newsletter using the standard template. "
        "Content team will provide articles by March 20.</p>",
        "status": "done",
        "priority": "medium",
        "assignees": ["Sarah Chen"],
        "labels": ["newsletter", "recurring"],
        "due_date": "2026-03-15",
    },
    {
        "id": "BRIEF-005",
        "title": "Flash Sale Notification Template",
        "description": "<p>Create a reusable flash sale template with countdown timer, "
        "dynamic product grid, and urgency-driven copy slots.</p>",
        "status": "open",
        "priority": "low",
        "assignees": [],
        "labels": ["template", "reusable"],
        "due_date": None,
    },
]
