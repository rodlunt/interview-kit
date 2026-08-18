## What and why

<!-- What changes, and what problem it solves. -->

Closes #

## Verification

<!-- The artefact that proves it works: a test file, a manual check, an output you compared. -->

## Checklist

- [ ] If I changed a rule, I edited `questionkit/rules.json` and nothing else
- [ ] I ran `python3 build_web.py` and committed the regenerated HTML
- [ ] I added a **known-good** case that must keep passing, not only a known-bad one
- [ ] `python3 tests/test_critique.py` passes
- [ ] The tool still makes **no network requests**
