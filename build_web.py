#!/usr/bin/env python3
"""Build the shareable single-file question critic.

Injects questionkit/rules.json into web/critic.template.html and writes
question-critic.html, which is one self-contained file a founder can download,
open, and use offline with no account and no data leaving their browser.

WHY THIS IS GENERATED RATHER THAN HAND-MAINTAINED. The rules would otherwise
exist twice, in Python and in JavaScript, and two hand-written copies of the same
logic drift. You find out when the two tools disagree in front of a founder. The
interview runner in this repo already carries exactly that hazard with its
embedded SCRIPTS block, which its own CLAUDE.md warns "cannot detect stale
content". No reason to build a second one.

  build_web.py           write question-critic.html
  build_web.py --check   exit 1 if the committed file is stale (used by CI)

The --check mode is the point. A generated file that nobody verifies is just a
copy that has not drifted YET.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = HERE / "questionkit" / "rules.json"
# (template, output) pairs. Both embed the same rules.json.
TARGETS = [
    (HERE / "web" / "critic.template.html", HERE / "question-critic.html"),
    (HERE / "web" / "kit.template.html", HERE / "interview-kit.html"),
]
MARKER = "/*__RULES_JSON__*/null"


def build(template) -> str:
    spec = json.loads(RULES.read_text())          # parse, so invalid JSON fails here
    tpl = template.read_text()
    if MARKER not in tpl:
        raise SystemExit(f"marker {MARKER!r} not found in {template.name}: "
                         "the template changed shape and this build would silently "
                         "produce a page with no rules in it")
    return tpl.replace(MARKER, json.dumps(spec, indent=1, ensure_ascii=False))


def main() -> int:
    n = len(json.loads(RULES.read_text())["rules"])
    rc = 0
    for template, output in TARGETS:
        html = build(template)
        if "--check" in sys.argv:
            if not output.exists():
                print(f"MISSING: {output.name} has never been built. Run tools/build_web.py")
                rc = 1
            elif output.read_text() != html:
                print(f"STALE: {output.name} does not match questionkit/rules.json "
                      f"+ {template.name}.\nRun tools/build_web.py and commit the result.")
                rc = 1
            else:
                print(f"{output.name} is current ({n} rules)")
        else:
            output.write_text(html)
            print(f"wrote {output.name}: {n} rules, {len(html):,} bytes, self-contained")
    return rc


if __name__ == "__main__":
    sys.exit(main())
