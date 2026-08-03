"""ATAR user modeling — extract preferences from conversation patterns."""

from __future__ import annotations

import json
import os
import re
from collections import Counter

from atar_core.paths import _atar_home as atar_home

MODEL_PATH = os.path.join(atar_home(), "user_model.json")


def load_model() -> dict:
    try:
        with open(MODEL_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "languages": {},
            "topics": [],
            "preferred_tools": [],
            "style_hints": [],
            "files_touched": [],
            "session_count": 0,
        }


def save_model(model: dict) -> None:
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "w") as f:
        json.dump(model, f, indent=2)


def update_from_messages(model: dict, messages: list) -> dict:
    """Extract preferences from a list of message dicts."""
    user_msgs = [m.get("content", "") for m in messages if m.get("role") == "user"]
    assistant_msgs = [m.get("content", "") for m in messages if m.get("role") == "assistant"]

    # Language detection
    for msg in user_msgs:
        if re.search(r'[a-zA-Z]{3,}', msg):
            model["languages"]["en"] = model["languages"].get("en", 0) + 1
        if re.search(r'[a-zA-Z]{3,}', msg) and any(
            w in msg.lower() for w in ["aku", "kamu", "ini", "itu", "yang", "dan", "ada", "bisa", "mau", "tidak"]
        ):
            model["languages"]["id"] = model["languages"].get("id", 0) + 1

    # Topic extraction (keyword-based)
    topic_keywords = {
        "coding": ["code", "kode", "program", "python", "javascript", "html", "css", "function", "class", "import", "def "],
        "security": ["cve", "exploit", "vulnerability", "bug", "security", "hack", "pentest", "audit"],
        "writing": ["tulis", "write", "article", "artikel", "blog", "document", "readme"],
        "data": ["data", "json", "csv", "database", "sql", "query", "api"],
        "deployment": ["deploy", "docker", "server", "hosting", "nginx", "ci/cd"],
    }
    all_text = " ".join(user_msgs).lower()
    for topic, keywords in topic_keywords.items():
        if any(kw in all_text for kw in keywords):
            if topic not in model["topics"]:
                model["topics"].append(topic)

    # Tool preference
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("name"):
            model["preferred_tools"].append(msg["name"])

    # Style: response length preference
    for msg in assistant_msgs:
        if len(msg) < 200:
            model["style_hints"].append("concise")
        elif len(msg) > 1500:
            model["style_hints"].append("detailed")

    # Files touched
    for msg in messages:
        if msg.get("role") == "tool" and msg.get("name") in ("write_file", "read_file"):
            path = msg.get("args", {}).get("path", "")
            if path and path not in model["files_touched"]:
                model["files_touched"].append(path[:80])

    model["session_count"] += 1
    save_model(model)
    return model


def model_to_prompt(model: dict) -> str:
    """Convert user model to a compact prompt snippet."""
    parts = []
    if model.get("languages"):
        top_lang = max(model["languages"], key=model["languages"].get)
        lang_name = {"en": "English", "id": "Indonesian"}.get(top_lang, top_lang)
        parts.append(f"User prefers: {lang_name}")
    if model.get("topics"):
        parts.append(f"Topics: {', '.join(model['topics'][-5:])}")
    if model.get("style_hints"):
        style = Counter(model["style_hints"]).most_common(1)[0][0]
        parts.append(f"Style: {style}")
    if model.get("preferred_tools"):
        top_tools = [t for t, _ in Counter(model["preferred_tools"]).most_common(3)]
        parts.append(f"Often uses: {', '.join(top_tools)}")
    if not parts:
        return ""
    lines = ["<user_model>"] + [f"- {p}" for p in parts] + ["</user_model>"]
    return "\n".join(lines)
