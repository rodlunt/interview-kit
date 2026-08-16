# Interview Kit

**One file. You interview someone, and they get to take back anything they said that they would rather you did not use.**

No account. No install. No internet connection needed. Nothing you type ever leaves your computer.

### [**Use it now**](https://rodlunt.github.io/interview-kit/interview-kit.html)

Opens in your browser and works immediately. Nothing is installed and nothing you
type is sent anywhere.

### [**Or download a copy to keep**](https://github.com/rodlunt/interview-kit/releases/latest/download/interview-kit.html)

One file. Save it, open it whenever, works with no internet at all.

> **Do not use the "raw" link to the file in this repository.** GitHub serves it
> as plain text, so your browser shows you a page of source code rather than the
> tool. Use one of the two links above.

---

## 1. Just want to use it

You are a founder, a researcher, a student, anyone who needs to talk to people and write down what they said. You do not need to know what a repository is.

### What it does, in order

1. **You type your questions.** It tells you which ones will get you useless answers. "Would you use this?" gets you a polite yes and nothing else, and it will say so before you waste an hour of someone's time.
2. **You run the interview.** One question per screen, a clock ticking, and a box for your notes. It quietly records how far into the conversation each question was asked, so you can find the moment again in whatever you recorded it on.
3. **You write up what you took from it**, starting from your own notes.
4. **You send them a file.** They open it, tick anything they would rather you did not use, and it comes back to you.
5. **You read their answers** and take those things out.

### Step by step

**Open it.** Either [click here](https://rodlunt.github.io/interview-kit/interview-kit.html)
and start straight away, or [download the file](https://github.com/rodlunt/interview-kit/releases/latest/download/interview-kit.html),
put it somewhere you will find it again, and double-click it. Both are the same tool.
The downloaded one keeps working with no internet.

**Type your questions,** one per line, and press "Check my questions". It will flag things like:

> **FATAL · HYPOTHETICAL** — Asks what they WOULD do.
> People are cheerfully, sincerely wrong about their own future behaviour. A yes here costs them nothing and tells you nothing.
> **Try:** "When did you last hit that problem, and what did you do?"

Fix the ones it complains about. Ignore it if you disagree; it is not the boss of you.

**Press "Start the interview"** when you are with the person. Read the question, listen, type notes, press Next.

**At the end** you turn your notes into plain statements. Read them properly before you send: a note you scribbled mid-conversation is not something you want landing in front of the person who said it.

**Press "Send it to them".** On a phone this hands the file to your usual share sheet and you pick Mail, WhatsApp, whatever. On a computer it saves the file and opens an email for you to attach it to. A web page is not allowed to attach files to emails by itself, so that last bit is on you.

**They open the file, tick, and send it back.** Same deal at their end.

**Drop their file onto your copy** and it tells you exactly what to remove.

### The bit that actually matters

Most interview advice is about getting more out of people. This is about the other side. If you have ever finished an interview thinking "they told me more than they meant to", this is how you make that right without just promising you will be careful.

### Common questions

**Do I need the internet?** No. Once the file is downloaded it works on a plane.

**Where is my work saved?** In your browser, on your machine. Use the same browser and do not clear its data halfway through.

**Can you see my interviews?** No. There is no server. Nothing is sent anywhere. See [Is my data safe?](#is-my-data-safe) below, which answers this properly rather than just saying no.

**Does it record audio?** No. Use your phone's voice recorder. The kit notes the time each question was asked so you can find it.

**Someone sent me one of these files, what is it?** Someone interviewed you and is showing you what they wrote down, so you can strike anything you are not happy with. Open it, tick, press the button, send the file back. You are not signing anything.

---

## 2. Want to host it yourself

For a cohort, a research team, or a university group where you would rather hand people a link than an attachment.

There is nothing to install. It is one static HTML file.

**Any web server, or none:**

```bash
git clone https://github.com/rodlunt/interview-kit.git
cd interview-kit
python3 -m http.server 8000
# then open http://localhost:8000/interview-kit.html
```

**Put it on a site you already have:** copy `interview-kit.html` anywhere it can be served. It has no dependencies, no build step at runtime, no external requests. It will work from a file share, a Dropbox link or an S3 bucket.

**Keeping your own copy current:** watch this repo for releases, or re-download when you want the fixes. People who already have a copy keep working; they just do not get the fixes.

**What hosting does NOT change:** the interviewee still receives a file, not a link, and their answers still come back as a file. Nothing is stored on your server, because the tool never sends anything to one.

A hosted version where the interviewee gets a link instead of an attachment is designed but not built. It is end-to-end encrypted by design, so the person running the server cannot read what is collected. See [the design notes](#the-hosted-version-designed-not-built).

---

## 3. Technical

### Layout

```
interview-kit.html      the tool. generated. do not hand-edit
question-critic.html    just the question checker, if that is all you want
questionkit/rules.json  THE source of truth for the rules
questionkit/critique.py the same rules in Python, for scripting
web/*.template.html     sources for the generated files
build_web.py            generator, and the staleness gate
tests/                  browser and unit tests
```

### The rules live in one place

`questionkit/rules.json` is read by the Python module and injected into both HTML files at build time. Two hand-written copies of the same logic drift, and you find out when the two tools disagree in front of somebody.

```bash
python3 build_web.py           # rebuild both HTML files
python3 build_web.py --check   # CI: fail if either is stale
```

The check is not decoration. It was verified to catch drift by changing a threshold and watching it fail.

### Tests

```bash
python3 tests/test_critique.py                          # rules, no dependencies
uv run --with playwright python tests/test_web_parity.py # python vs javascript agree
uv run --with playwright python tests/test_kit_loop.py   # the whole loop, two people
```

`test_critique.py` holds three fixed groups: **known-bad** which must be caught, **known-good** which must not be, and **known-contested**, real questions from a working script that the critic flags anyway, recorded with the reason rather than tuned away. The good and bad groups must not overlap on score, so a critic that flags everything fails as loudly as one that flags nothing. That check earned its keep immediately: the first version of one rule flagged **78%** of a working script.

`test_kit_loop.py` drives the real file in a real browser as two different people. The exported reviewer file is opened in a **fresh browser context with its own storage**. That is the control: anything the file inherited from the founder's session shows up there rather than in front of a real interviewee.

### How the interviewee's file works

When you export, the kit writes out **a copy of itself** with the interview embedded in a payload constant. That is what makes the file self-contained: the interviewee needs a browser and nothing else. No server, no account, no trust in anyone's hosting.

The answers file coming back carries **only claim ids, ticks and notes**, never the interview content.

### Adding or changing a rule

Edit `questionkit/rules.json`, add cases to `tests/test_critique.py`, run `build_web.py`, commit the regenerated HTML. Four rule kinds are supported: `regex`, `regex_absent`, `multi_sentence`, `word_count`. A rule that fires on good questions is worse than no rule, so add a known-good case that must keep passing.

### Is my data safe?

Answered properly, including the parts that are not perfect.

**What is genuinely true:**

- The tool makes **zero network requests**. Verified in the test suite, not just claimed: the exported file is asserted to contain no external references.
- There is no server, no account, no telemetry, no analytics.
- Your work is in your browser's local storage on your own machine.
- The answers file that travels back by email contains no interview content, only ids and the interviewee's own words.

**What is not:**

- **Email is not encrypted.** The file you send your interviewee travels through your mail provider and theirs. For most research this is the same exposure as emailing them a document, which is what everyone already does. If your subject matter is genuinely sensitive, put the file in something encrypted.
- **Local storage persists.** If you use the kit on a shared or public computer, the next person can open it and see your last interview. Use your own machine, or clear the browser data afterwards.
- **The exported file contains your email address**, so the reply can be addressed automatically. If you would rather it did not, leave that field blank.
- **Anyone your interviewee forwards the file to can read it.** That is their choice about their own words, which is rather the point, but it is worth knowing.
- **This has not had a third-party security review.** It is a static page with no server and no dependencies, which is a small target, but small is not zero.

If you find something, see [SECURITY.md](SECURITY.md).

### The hosted version, designed not built

For people who would rather send a link than an attachment:

- **End-to-end encrypted.** The browser encrypts before upload and the key lives in the URL fragment, which browsers never send to a server. The operator stores ciphertext they cannot read. That is the only version of "your interviews are private" that is a fact rather than a promise.
- Consequence, stated plainly: **a lost link is unrecoverable**, because there is no key to reset.
- Invite codes so an operator can host for a known group without it being open to the world. Anti-abuse only; confidentiality comes from the encryption.
- Notification by email, address supplied by the founder and held in the clear. The operator sees who is using it, never what they collected.
- **No audio.** Encrypting and storing tens of megabytes per interview from a phone browser is a much larger problem where every failure mode loses an interview.

### Licence

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

The question rules encode the discipline described in **The Mom Test** by Rob Fitzpatrick: you learn from what people have done, and lose nothing but time asking what they would do. The implementation is original, the idea is his, and the book is worth your afternoon.
