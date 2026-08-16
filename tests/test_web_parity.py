"""The shipped web tool must agree with the Python module, question for question.

Two implementations of one set of rules is the whole risk of shipping a
single-file version. They are generated from the same rules.json, which removes
the obvious way to drift, but NOT the subtle one: Python's `re` and JavaScript's
RegExp are not the same engine, and a pattern can quietly mean something
different in each. Only running both and comparing catches that.

This test drives the real question-critic.html in a real browser, feeds it every
question from the critic's test set, and asserts the findings and scores match
Python exactly. A mismatch means a founder using the shared file gets a different
answer from the same rules, which is worse than having no shared file.

Needs Chrome and playwright:
  uv run --python 3.12 --with playwright python tools/tests/test_web_parity.py
Skips cleanly (exit 0, loudly) if neither is available, because a test that
cannot run must never be reported as a test that passed.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
sys.path.insert(0, str(TOOLS))

from questionkit.critique import critique_question           # noqa: E402
from tests.test_critique import KNOWN_BAD, KNOWN_GOOD, KNOWN_CONTESTED  # noqa: E402

PAGE = TOOLS / "question-critic.html"
CHROME = "/usr/bin/google-chrome"


def main() -> int:
    if not PAGE.exists():
        print(f"CANNOT RUN: {PAGE.name} not built. Run tools/build_web.py")
        return 1
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIPPED (not passed): playwright unavailable, parity unverified")
        return 0
    if not Path(CHROME).exists():
        print("SKIPPED (not passed): chrome unavailable, parity unverified")
        return 0

    questions = ([q for q, _ in KNOWN_BAD] + list(KNOWN_GOOD)
                 + [q for q, _, _ in KNOWN_CONTESTED])

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        page = b.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(PAGE.as_uri())
        js = page.evaluate(
            """(qs) => qs.map(q => {
                   const c = critique(q);
                   return {score: c.score, rules: c.findings.map(f => f.rule).sort()};
               })""", questions)
        b.close()

    if errs:
        print("FAIL  javascript errors on load:", errs)
        return 1

    # Control: if the page silently returned nothing useful, every comparison
    # below would trivially "pass" against an empty result set.
    if len(js) != len(questions):
        print(f"CONTROL FAILED: page returned {len(js)} results for {len(questions)} questions")
        return 1
    if all(r["score"] == 100 and not r["rules"] for r in js):
        print("CONTROL FAILED: the page flagged nothing at all; it is not running the rules")
        return 1

    failures = []
    for q, got in zip(questions, js):
        want = critique_question(q)
        want_rules = sorted(f.rule for f in want.findings)
        if got["score"] != want.score or got["rules"] != want_rules:
            failures.append(
                f"{q[:70]!r}\n      python: score={want.score} {want_rules}"
                f"\n      web:    score={got['score']} {got['rules']}")

    print(f"compared {len(questions)} questions across both implementations")
    if failures:
        print("\n".join("FAIL  " + f for f in failures))
        return 1
    print("all checks passed: web tool and python module agree exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
