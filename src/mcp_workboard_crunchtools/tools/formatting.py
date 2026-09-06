"""Shared shaping of WorkBoard API responses.

WorkBoard returns the same action-item envelope from the activities endpoint
and from a workstream's activity list. Both tool modules used to carry a
byte-identical copy of the nested-collection handling below, so a renamed
field had to be fixed in two places or the two responses would drift.
"""

from __future__ import annotations

from typing import Any


def add_action_item_details(formatted: dict[str, Any], ai: dict[str, Any]) -> None:
    """Copy the nested collections of a raw action item onto ``formatted``.

    Each is optional in the API response and is omitted from the output when
    absent, which is why every block guards on both type and emptiness.
    """
    ai_column = ai.get("ai_column")
    if isinstance(ai_column, dict):
        formatted["column_id"] = ai_column.get("id", "")
        formatted["column_name"] = ai_column.get("name", "")

    comments = ai.get("ai_comments", [])
    if isinstance(comments, list) and comments:
        formatted["comments"] = [
            {
                "comment_id": c.get("comment_id", ""),
                "comment": c.get("comment", ""),
                "owner": c.get("comment_owner", ""),
                "timestamp": c.get("comment_timestamp", ""),
            }
            for c in comments
            if isinstance(c, dict)
        ]

    sub_actions = ai.get("ai_sub_actions", [])
    if isinstance(sub_actions, list) and sub_actions:
        formatted["sub_actions"] = [
            {
                "sub_ai_id": sa.get("sub_ai_id", ""),
                "description": sa.get("sub_ai_description", ""),
                "owner": sa.get("sub_ai_owner", ""),
            }
            for sa in sub_actions
            if isinstance(sa, dict)
        ]

    files = ai.get("ai_files", [])
    if isinstance(files, list) and files:
        formatted["files"] = [
            {
                "file_id": f.get("file_id", ""),
                "file_name": f.get("file_name", ""),
                "file_url": f.get("file_url", ""),
                "file_owner": f.get("file_owner", ""),
            }
            for f in files
            if isinstance(f, dict)
        ]

    tags = ai.get("ai_tags")
    if tags:
        formatted["tags"] = tags

    loop_members = ai.get("ai_loop_members", [])
    if isinstance(loop_members, list) and loop_members:
        formatted["loop_members"] = [
            {
                "user_id": lm.get("user_id", ""),
                "email": lm.get("user_email", ""),
            }
            for lm in loop_members
            if isinstance(lm, dict)
        ]

