from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

STEP_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}
STEP_RE = re.compile(r"\bstep\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b", re.IGNORECASE)


def detect_step_number(text: str) -> Optional[int]:
    match = STEP_RE.search(text or "")
    if not match:
        return None
    value = match.group(1).lower()
    if value.isdigit():
        return int(value)
    return STEP_WORDS.get(value)


def build_steps(collected: List[Dict[str, Any]]):
    """Group collected items into ordered steps preserving encounter order."""
    preamble_content: List[Dict[str, Any]] = []
    steps: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
    current_step: Optional[int] = None

    for itm in collected:
        if itm["type"] == "text":
            step_no = itm["step"]
            if step_no is not None:
                current_step = step_no
                steps.setdefault(step_no, {"content": []})
                steps[step_no]["content"].append({"type": "text", "text": itm["text"]})
            else:
                if current_step is None:
                    preamble_content.append(itm)
                else:
                    steps.setdefault(current_step, {"content": []})
                    steps[current_step]["content"].append({"type": "text", "text": itm["text"]})
        elif itm["type"] == "image":
            assoc = itm["step"] if itm.get("step") is not None else current_step
            if assoc is None:
                preamble_content.append(itm)
            else:
                steps.setdefault(assoc, {"content": []})
                steps[assoc]["content"].append(itm)

    # If no steps detected, create a default step 1 with all preamble content
    if not steps:
        steps[1] = {"content": preamble_content}
        preamble_content = []
    # If steps exist but we have unassigned content, prefix it to the first step
    elif preamble_content:
        first_step = sorted(steps.keys())[0]
        steps[first_step]["content"] = preamble_content + steps[first_step]["content"]
        preamble_content = []

    ordered_steps = sorted(steps.items(), key=lambda kv: kv[0])
    return ordered_steps

