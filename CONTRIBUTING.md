# Contributing

Thanks for wanting to improve Interview Kit. This is a small, solo-maintained
project, so the process is deliberately light. The few rules below exist so that
contributions land rather than stalling.

## Where things go

- **Bugs**: [open an issue](https://github.com/rodlunt/interview-kit/issues/new/choose)
  using the bug form. Browser, operating system and what you expected are the
  three things that get a bug fixed fast.
- **A question the critic gets wrong**: this is the most useful contribution
  there is, in either direction. A good question it flags, or a bad question it
  misses. Use the rule-feedback form and paste the exact question.
- **Ideas**: open a discussion before writing code, so neither of us wastes an evening.

## The one rule that matters

**The rules live in `questionkit/rules.json`, and nowhere else.**

They are read by the Python module and injected into both HTML files at build
time. If you edit a rule anywhere other than that file, CI will fail, and it
should: two hand-written copies of the same logic drift, and the failure shows up
as the two tools disagreeing in front of somebody mid-interview.

```bash
python3 build_web.py           # regenerate both HTML files
python3 build_web.py --check   # what CI runs
```

Commit the regenerated HTML with your change.

## Adding or changing a rule

1. Edit `questionkit/rules.json`.
2. Add cases to `tests/test_critique.py`: at least one **known-bad** the rule must
   catch, and at least one **known-good** it must not.
3. Run `python3 tests/test_critique.py`.

The second half is the part people skip and the part that matters. A rule that
fires on good questions is worse than no rule, because a tool that flags four
questions in five gets switched off and ignored. The test asserts the known-good
and known-bad sets do not overlap on score, so a rule tightened until it flags
everything fails as loudly as one loosened until it flags nothing.

If a rule flags a real question and you think it is right to, add it to
**known-contested** with the reason, rather than deleting the example.

## Tests

```bash
python3 tests/test_critique.py                            # no dependencies
uv run --with playwright python tests/test_web_parity.py  # python and javascript agree
uv run --with playwright python tests/test_kit_loop.py    # the whole loop, two people
```

The browser tests need Chrome. They skip loudly rather than passing quietly when
it is missing, because a check that could not run must never look like one that did.

## Style

- Plain HTML, CSS and JavaScript. **No frameworks, no build step at runtime, no
  external requests, ever.** The entire value of this tool is that it is one file
  that works offline and sends nothing anywhere. A CDN link would end that.
- Python is standard library only.
- Australian English in user-facing text.
- Explain *why* in comments, not *what*. The what is in the code.

## What will not be merged

- Anything that makes a network request from the tool.
- Analytics, telemetry or "anonymous usage statistics", however well meant.
- A dependency on a hosted service for the standalone path.
- Rules that pattern-match on subject matter rather than on how a question is put.
  The critic checks **how** you ask, never **whether it is worth asking**, and
  blurring that would make it confidently wrong about things it cannot judge.
