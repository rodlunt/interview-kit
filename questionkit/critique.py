"""Judge an interview question without asking a model anything.

Founders ask bad questions in a small number of very predictable ways, and every
one of them is detectable from the text. This module applies those patterns so a
question can be criticised deterministically, for free, offline, and identically
every time.

It exists for three reasons, in order of importance:

1. **It is useful on its own.** Someone with no API key can paste in their own
   questions and be told which will produce worthless answers.
2. **It keeps a generator honest.** Anything a model writes gets held to the same
   standard as anything a human writes. A generator marking its own homework is
   not a quality control.
3. **It makes regressions visible.** The rules are testable against a fixed set
   of known-good and known-bad questions, so "the questions got worse" becomes a
   failing test rather than a feeling six weeks later.

The underlying idea is not mine: it is the discipline behind The Mom Test, which
is that you learn from what people HAVE DONE and lose nothing but time asking
what they WOULD do. Every rule is a mechanical proxy for that.

THE RULES LIVE IN rules.json, NOT HERE. The shipped single-file web tool reads
the same file, so the two implementations cannot drift apart in the way an
embedded copy always eventually does. CI fails if the web tool's embedded copy
falls out of step with the source.

WHAT THIS DELIBERATELY DOES NOT DO. It cannot tell you whether a question is
about the right subject, whether it probes a risky assumption, or whether it is
the question that matters most. A question can pass every rule here and still be
a waste of everyone's time, and the report says so rather than implying that a
clean pass means a good script.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RULES_PATH = Path(__file__).with_name("rules.json")
_SPEC = json.loads(RULES_PATH.read_text())
_PENALTY = _SPEC["severity_penalty"]
LIMITS = _SPEC["limits"]
SEVERITY_ORDER = {"fatal": 0, "warn": 1, "note": 2}

# The past-behaviour pattern, needed directly for the script-level "anchored"
# count as well as for the rule itself.
_ANCHOR_RE = re.compile(
    next(r["pattern"] for r in _SPEC["rules"] if r["name"] == "no-past-anchor"), re.I)

_COMPILED = [
    (r, re.compile(r["pattern"], re.I) if "pattern" in r else None)
    for r in _SPEC["rules"]
]


@dataclass
class Finding:
    rule: str
    severity: str          # fatal | warn | note
    message: str
    why: str
    suggestion: str = ""
    span: str = ""


@dataclass
class Critique:
    question: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def fatal(self) -> bool:
        return any(f.severity == "fatal" for f in self.findings)

    @property
    def score(self) -> int:
        """0-100. Blunt on purpose: a traffic light, not a measurement. Reporting
        it to two decimal places would imply a precision the rules do not have."""
        return max(0, 100 - sum(_PENALTY[f.severity] for f in self.findings))


def _sentences(text: str) -> list[str]:
    return [q.strip() for q in re.split(r"(?<=\?)\s+", text.strip()) if q.strip()]


def critique_question(text: str) -> Critique:
    q = text.strip()
    c = Critique(question=q)
    if not q:
        c.findings.append(Finding("empty", "fatal", "Empty question.", "Nothing to ask."))
        return c

    deferred = []
    for spec, pattern in _COMPILED:
        kind = spec["kind"]
        hit, span = False, ""

        if kind == "regex":
            m = pattern.search(q)
            hit, span = bool(m), (m.group(0).strip() if m else "")
        elif kind == "regex_absent":
            hit = not pattern.search(q)
        elif kind == "multi_sentence":
            n = len(_sentences(q))
            hit, span = n > 1, f"{n} sentences"
        elif kind == "word_count":
            n = len(q.split())
            hit, span = n > spec["threshold"], f"{n} words"
        else:
            raise ValueError(f"unknown rule kind {kind!r} in rules.json")

        if not hit:
            continue
        f = Finding(spec["name"], spec["severity"],
                    spec["message"] + (f": “{span}”." if span else "."),
                    spec["why"], spec.get("suggestion", ""), span)
        # e.g. no-past-anchor is noise on a question already fatally broken.
        (deferred if spec.get("skip_if_fatal") else c.findings).append(f)

    if not c.fatal:
        c.findings.extend(deferred)

    c.findings.sort(key=lambda f: SEVERITY_ORDER[f.severity])
    return c


def critique_script(questions: list[str]) -> dict:
    """Critique a whole script and report on it as a set, not just item by item."""
    crits = [critique_question(q) for q in questions]
    # Test the pattern directly rather than inferring from the absence of the
    # finding. no-past-anchor is suppressed on a question that is already fatally
    # broken, so "no flag" and "is anchored" are not the same thing: inferring it
    # reported 6 of 7 questions anchored when 2 were, which would tell a founder
    # their script is well grounded when it is the opposite.
    anchored = sum(1 for q in questions if _ANCHOR_RE.search(q))
    return {
        "questions": len(crits),
        "fatal": sum(1 for c in crits if c.fatal),
        "clean": sum(1 for c in crits if not c.findings),
        "anchored_in_past_behaviour": anchored,
        "mean_score": round(sum(c.score for c in crits) / len(crits)) if crits else 0,
        "critiques": crits,
        "limits": LIMITS,
    }
