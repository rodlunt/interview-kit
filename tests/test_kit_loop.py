#!/usr/bin/env python3
"""Drive the standalone interview kit end to end, as two different people.

The whole point of this tool is that it works with no server, so the test uses
no server: it opens the file from disk, plays the founder through questions,
interview and write-up, catches the file it exports, opens THAT file as the
interviewee, ticks boxes, catches the answers file, and feeds it back to the
founder's copy.

The control that matters: the exported reviewer file must be genuinely
self-contained. It is opened in a FRESH browser context with its own storage, so
anything it inherited from the founder's session would show up as a failure here
rather than in front of a real interviewee.
"""
import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "interview-kit.html"
CHROME = "/usr/bin/google-chrome"
fails = []


def check(name, expected, actual):
    if expected == actual:
        print(f"PASS  {name} [{actual!r}]")
    else:
        print(f"FAIL  {name}\n        expected: {expected!r}\n        actual:   {actual!r}")
        fails.append(name)


def main():
    import tempfile
    from playwright.sync_api import sync_playwright
    dl = Path(tempfile.mkdtemp())

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)

        # ---------- founder ----------
        ctx = b.new_context(accept_downloads=True, viewport={"width": 400, "height": 860})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(KIT.as_uri())
        pg.wait_for_selector("#qs")
        check("founder view loads clean", [], errs)

        pg.fill("#who", "Sam, Acme Plumbing")
        pg.fill("#promise", "Not a sales call, nothing goes public, strike anything you like.")
        pg.fill("#them", "sam@acmeplumbing.com.au")
        pg.fill("#mine", "founder@example.com")
        pg.fill("#qs", "Walk me through how you handle that today.\n"
                       "Tell me about the last time it went wrong. What happened?\n"
                       "Would you use a tool that did all of this for you?")
        pg.click("#check")
        pg.wait_for_selector(".q")
        check("critique runs on the founder's own questions", 3, pg.locator(".q").count())
        check("the hypothetical is flagged fatal", 1, pg.locator(".q.fatal").count())

        pg.click("#go")
        pg.wait_for_selector(".qtext")
        check("interview starts on question 1", "1 of 3", pg.locator("#pos").inner_text())
        pg.fill("#note", "They run the whole schedule off one shared calendar.")
        pg.click("#next")
        pg.fill("#note", "Last failure was a double booking nobody noticed for two days.")
        pg.click("#next")
        pg.fill("#note", "Said yes, but could not say what they would stop paying for.")

        pg.click("#next")              # finish -> write-up
        pg.wait_for_selector("#mk")
        check("write-up seeded from the notes", 3, pg.locator(".claim").count())
        pg.click("#mk")
        pg.wait_for_selector("#again")
        with pg.expect_download() as d:
            pg.click("#again")         # explicit download path (no share sheet in headless)
        review_file = dl / "review.html"
        d.value.save_as(review_file)
        check("reviewer file exported", True, review_file.exists() and review_file.stat().st_size > 20000)
        check("founder reaches the send step", True, "Send it to them" in pg.locator("h1").inner_text())
        check("reply address embedded for the return leg", True, "founder@example.com" in review_file.read_text())

        # CONTROL: the exported file must carry the data, not a reference to it.
        src = review_file.read_text()
        check("payload embedded in the exported file", True, "Acme Plumbing" in src)
        check("exported file has no external references", 0,
              len([1 for t in ("http://", "https://", "src=") if t in src]))

        # ---------- interviewee, fresh browser, own storage ----------
        ctx2 = b.new_context(accept_downloads=True, viewport={"width": 390, "height": 844})
        pg2 = ctx2.new_page()
        errs2 = []
        pg2.on("pageerror", lambda e: errs2.append(str(e)))
        pg2.on("console", lambda m: errs2.append(m.text) if m.type == "error" else None)
        pg2.goto(review_file.as_uri())
        pg2.wait_for_selector(".claim")
        check("interviewee file opens clean in a fresh browser", [], errs2)
        check("shows the founder's points", 3, pg2.locator(".claim").count())
        check("shows the promise back to them", True,
              "nothing goes public" in pg2.locator("blockquote").inner_text())
        check("does NOT show the founder's tools", 0, pg2.locator("#qs").count())

        pg2.locator(".claim").nth(1).locator("input[type=checkbox]").check()
        pg2.locator(".claim").nth(1).locator("textarea").fill("Rather you left that one out.")
        pg2.locator("#gen").fill("Otherwise all fine.")
        with pg2.expect_download() as d2:
            pg2.click("#dl")
        answers = dl / "answers.json"
        d2.value.save_as(answers)
        a = json.loads(answers.read_text())
        check("answers file records one flag", 1,
              sum(1 for v in a["claims"].values() if v.get("flagged")))
        check("answers file carries their note", True,
              any("left that one out" in (v.get("note") or "") for v in a["claims"].values()))
        check("answers file carries the general comment", "Otherwise all fine.", a["general"])
        check("answers file contains no interview content beyond ids", True,
              "shared calendar" not in answers.read_text())

        # ---------- back to the founder ----------
        pg.click("#read")
        pg.wait_for_selector("#f")
        pg.set_input_files("#f", str(answers))
        pg.wait_for_selector(".item", timeout=10000)
        body = pg.locator("#res").inner_text()
        check("founder sees exactly one thing to remove", True, "1 thing(s) to remove" in body)
        check("and it is the right one", True, "double booking" in body)
        check("their note is shown", True, "left that one out" in body)
        check("general comment shown", True, "Otherwise all fine" in body)
        check("no page errors across the whole loop", [], errs)
        b.close()

    print("\n" + ("FAILURES: " + ", ".join(fails) if fails else "all checks passed"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
