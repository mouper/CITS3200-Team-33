"""
prompt_builder.py — Build compact, deterministic prompts for single-label classification.

Inputs: payload dict with keys Title, Description, Tags, Channel.
Outputs: dict with keys system, labels_block, user_payload, and assembled prompt parts.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def build_allowed_labels_block(allowed_labels: List[str]) -> str:
    lines = ["Allowed labels (choose exactly one, case-sensitive):"]
    for label in allowed_labels:
        lines.append(f"- {label}")
    lines.append("Choose the closest single label. If unclear, use ‘Other / Unclear’.")
    return "\n".join(lines)


def build_system_message() -> str:
    return (
        "You are a video title classifier. Choose exactly one label from the allowed list. "
        "Respond with strict JSON {\"category\":\"<Label>\"} only. "
        "No explanations. No extra fields."
    )


def build_user_payload(payload: Dict[str, str]) -> str:
    title = payload.get("Title", "")
    description = payload.get("Description", "")
    tags = payload.get("Tags", "")
    channel = payload.get("Channel", "")
    return (
        f"Title: \"{title}\"\n"
        f"Description: \"{description}\"\n"
        f"Tags: \"{tags}\"\n"
        f"Channel: \"{channel}\"\n"
        "Return: {\"category\":\"<one label from Allowed>\"}"
    )


def assemble_prompt(payload: Dict[str, str], allowed_labels: List[str]) -> Tuple[str, str, str]:
    """
    Returns a tuple: (system_message, labels_block, user_payload)
    The caller can pass these to the chat API in order: system -> labels block -> user.
    """
    system = build_system_message()
    labels_block = build_allowed_labels_block(allowed_labels)
    user_msg = build_user_payload(payload)
    return system, labels_block, user_msg


