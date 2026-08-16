"""Fixed set of questions the critic must keep sorting correctly.

Three groups, and the third is the honest one:

  KNOWN_BAD        must be caught. A critic that misses these is decorative.
  KNOWN_GOOD       must NOT be caught. This half is what actually decays: it is
                   easy to tighten rules until they fire on everything, and a
                   critic that cries wolf is switched off by the second script.
  KNOWN_CONTESTED  real questions from a working script that the critic DOES
                   flag. Recorded, with the expected rule, rather than quietly
                   dropped or tuned away.

Every question in KNOWN_GOOD and KNOWN_CONTESTED is copied verbatim from the
a working interview script (3.1 to 3.3), which were used in a real 98-minute
interview on 16 Aug 2026 that produced usable findings. Nothing here is invented
to make the rules look good. An earlier version of this file did contain two
questions I wrote myself, and it claimed in this docstring that they were real:
that is precisely how a test set stops testing anything, because the examples
drift towards whatever the code already does.

KNOWN_CONTESTED exists because the critic is deliberately STRICTER than the
scripts it was built from. "If you could change one thing about how your business
runs tomorrow, what would it be?" is a real question from that script and the
critic calls it a hypothetical, correctly: it produces a wishlist, not evidence.
Keeping it visible here is the difference between a tool that improves a founder's
script and one that ratifies whatever it was shown first.

Run: python3 tests/test_critique.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from questionkit.critique import critique_question, critique_script  # noqa: E402

KNOWN_BAD = [
    ("Would you use a tool that did all of this for you?", "hypothetical"),
    ("Could you see yourself paying for something like that?", "hypothetical"),
    ("We're building a platform for solar installers, what do you think of this?", "pitching"),
    ("How much would you pay for this?", "pitching"),
    ("Don't you think managing subcontractors is a nightmare?", "leading"),
    ("Isn't it frustrating when the schedule falls apart?", "leading"),
    ("On a scale of 1 to 10, how painful is your current quoting process?", "scale"),
    ("Do you use a CRM?", "closed"),
    ("What tools do you use, and how much do they cost you?", "double-barrelled"),
    ("How do you leverage synergies across your ecosystem play?", "jargon"),
]

# Verbatim from a working interview script.
KNOWN_GOOD = [
    "Walk me through how you manage a job from when a lead comes in to when you get paid.",
    "What part of that process causes you the most stress or wasted time?",
    "Tell me about a time a sale did not go the way you wanted. What happened?",
    "How do you currently manage your install schedule?",
    "What happens when a product you have quoted is no longer available?",
    "Walk me through how you currently lodge STC claims.",
    "What have you tried to solve these problems?",
    "How do your subcontractors know what jobs they have coming up?",
    "How do you verify that each subcontractor's CEC accreditation and public liability "
    "insurance are current before they go on-site?",
    "What information does a subcontractor need to complete a job on-site?",
]

# Also verbatim from those scripts, and the critic flags them. Deliberate.
KNOWN_CONTESTED = [
    ("If you could change one thing about how your business runs tomorrow, what would it be?",
     "hypothetical",
     "Produces a wishlist. The answer is what they imagine wanting, not what they have done."),
    ("What information does a subcontractor need to complete a job on-site, and how do you "
     "get it to them?",
     "double-barrelled",
     "Two asks in one turn; the second half gets dropped in practice."),
    ("Do you offer finance through Brighte, Smart Ease, or similar in your proposals?",
     "closed",
     "Invites yes/no. Fine as a lead-in, weak as a standalone item."),
]


def run():
    failures = []

    for text, expected_rule in KNOWN_BAD:
        rules = {f.rule for f in critique_question(text).findings}
        if expected_rule not in rules:
            failures.append(f"MISSED {expected_rule!r} in: {text!r} (found {sorted(rules)})")

    for text in KNOWN_GOOD:
        blocking = [f for f in critique_question(text).findings
                    if f.severity in ("fatal", "warn")]
        if blocking:
            failures.append(
                f"FALSE ALARM on a real question that worked: {text!r} -> "
                f"{[(f.rule, f.severity) for f in blocking]}")

    for text, expected_rule, _why in KNOWN_CONTESTED:
        rules = {f.rule for f in critique_question(text).findings}
        if expected_rule not in rules:
            failures.append(
                f"CONTESTED question no longer flagged (rule weakened?): {text!r} "
                f"expected {expected_rule!r}, found {sorted(rules)}")

    # A critic that flags nothing, or everything, is equally useless. The two
    # sets must not overlap on score, or it is not separating them at all.
    bad = [critique_question(t).score for t, _ in KNOWN_BAD]
    good = [critique_question(t).score for t in KNOWN_GOOD]
    if max(bad) >= min(good):
        failures.append(
            f"NOT DISCRIMINATING: worst good={min(good)} best bad={max(bad)}; "
            "the two sets must not overlap on score")

    summary = critique_script([t for t, _ in KNOWN_BAD])
    if summary["fatal"] < 4:
        failures.append(f"script-level fatal count implausibly low: {summary['fatal']}")

    print(f"known-bad {len(KNOWN_BAD)} | known-good {len(KNOWN_GOOD)} | "
          f"contested {len(KNOWN_CONTESTED)}")
    print(f"score range   bad {min(bad)}-{max(bad)}   good {min(good)}-{max(good)}")
    if failures:
        print("\n".join("FAIL  " + f for f in failures))
        return 1
    print("all checks passed")
    return 0


def test_critic():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
