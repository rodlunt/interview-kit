# Security

## Reporting

Report privately through
[GitHub Security Advisories](https://github.com/rodlunt/interview-kit/security/advisories/new),
not a public issue. I will acknowledge within a week. This is a side project, not
a company, so please read that as an honest estimate rather than an SLA.

## What this project is, in security terms

A static HTML file with no server, no dependencies, no build step at runtime and
no network requests. That is a small attack surface, deliberately. Small is not
none.

Things I would very much like to hear about:

- Any way the tool makes a network request. There should be none, and the test
  suite asserts the exported file has no external references.
- Any way the exported interviewee file could carry data from the interviewer's
  session other than the interview it was exported for.
- Cross-site scripting through interview text, question text or an answers file.
  All three are user-supplied and all three are escaped, but escaping is exactly
  the sort of thing that is right until it is not.
- Anything in an answers file that could harm the interviewer's copy when loaded.

## Known limitations, already documented

These are in the README under "Is my data safe?" and are design trade-offs rather
than bugs. Reporting them is welcome but they will not be a surprise:

- Email is not encrypted; the file travels through both parties' mail providers.
- Browser local storage persists, so a shared computer exposes the last interview.
- The exported file contains the interviewer's email address, if they entered one.
- No third-party security review has been done.

## What is out of scope

- The security of the interviewee's or interviewer's own email account.
- Social engineering of either party.
- The unbuilt hosted version. When it exists it will be in scope, and its whole
  design premise is that the operator cannot read what is stored.
