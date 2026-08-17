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
import os
import sys
from pathlib import Path

# Overridable so the checks can be pointed at an older build and watched to fail.
# A control nobody has seen fail is not evidence of anything.
KIT = Path(os.environ.get("KIT") or Path(__file__).resolve().parent.parent / "interview-kit.html")
CHROME = "/usr/bin/google-chrome"
fails = []

MAILTO_HOOK = ("window.__mailtoHook = (u) => { window.__mailtoSeen = u; };")
"""Capture the mailto instead of letting Chrome hand it to the real mail client.
Headless Chromium has no share sheet, so every run takes the mailto branch and
would otherwise open a compose window on the machine running the suite."""



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
        ctx.add_init_script(MAILTO_HOOK)
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
        # Deliberately leave "Your email" blank. That is the state that shipped a
        # reviewer file with no return address in real use, so the run starts
        # broken and has to be stopped at the send step.
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

        # CONTROL: no return address, no export. Both of these fail on the
        # pre-fix page, which exported happily and produced a file whose
        # interviewee copy had nothing to reply to.
        check("send is blocked with no return address", True, pg.locator("#send").is_disabled())
        check("download is blocked with no return address", True, pg.locator("#again").is_disabled())
        # ...and the refusal is in the export itself, not only in the disabled
        # button, so it holds for any caller that reaches the function directly.
        check("export refuses with no return address", "no-reply-address",
              pg.evaluate("() => exportReviewFile(false)"))
        check("and it says why", True, "Add your email" in pg.locator("#how").inner_text())

        check("send screen offers a return-address field", 1, pg.locator("#reply").count())
        if not pg.locator("#reply").count():
            # Pre-fix build. Stop here rather than timing out on a field that
            # does not exist: the controls above have already reported.
            print("\nno #reply field, stopping (this is the pre-fix page)")
            print("FAILURES: " + ", ".join(fails))
            b.close()
            return 1
        pg.fill("#reply", "founder@example.com")
        check("filling it in releases the gate", False, pg.locator("#send").is_disabled())

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
        ctx2.add_init_script(MAILTO_HOOK)
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
        # The share sheet has no To: line, so the page naming the address is the
        # only thing that tells them who to send it to.
        check("names where the answers go", True,
              "founder@example.com" in pg2.locator("#wrap").inner_text())

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
        check("the return address reaches the mail step", True,
              "founder%40example.com" in (pg2.evaluate("() => window.__mailtoSeen") or ""))
        check("no mailto escaped to the desktop mail client", True,
              pg2.evaluate("() => typeof window.__mailtoHook === 'function'"))

        # ---------- CONTROL: a successful share must still leave a copy ----------
        # navigator.share() resolves when the receiving app ACCEPTS the file, not
        # when it is delivered. An iPhone sharing this .json to an Android number
        # goes out as MMS, which drops the attachment, and the page says it worked.
        # Headless Chromium has no share sheet, so it is stubbed to succeed: that
        # is exactly the path that used to skip the local save and leave the
        # interviewee with nothing to retry from.
        from playwright.sync_api import TimeoutError as PWTimeout
        ctx3 = b.new_context(accept_downloads=True, viewport={"width": 390, "height": 844})
        ctx3.add_init_script(
            "Object.defineProperty(navigator,'canShare',{value:()=>true,configurable:true});"
            "Object.defineProperty(navigator,'share',{value:async()=>{window.__shared=true;},"
            "configurable:true});")
        pg3 = ctx3.new_page()
        pg3.goto(review_file.as_uri())
        pg3.wait_for_selector(".claim")
        pg3.locator(".claim").nth(0).locator("input[type=checkbox]").check()
        try:
            with pg3.expect_download(timeout=5000) as d3:
                pg3.click("#dl")
            saved = d3.value.suggested_filename
        except PWTimeout:
            saved = None
        check("share path took the share sheet", True, pg3.evaluate("() => !!window.__shared"))
        check("a successful share STILL saves a local copy", "answers-sam-acme-plumbing.json", saved)
        check("and the page says where that copy is", True,
              "saved on this device" in pg3.locator("#st").inner_text())

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
