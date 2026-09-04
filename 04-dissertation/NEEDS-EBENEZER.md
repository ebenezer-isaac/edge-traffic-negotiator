# Things only you can supply — dissertation + article

Everything else is done. Give me the answers and I apply them in minutes.
Ordered: blocking first.

---

## 1. BLOCKING — the declaration wording
**File:** `04-dissertation/frontmatter.tex` line 22
**Currently on the title page:**

> This report is submitted as part requirement for the MSc in Systems Engineering
> for the Internet of Things at University College London. It is substantially the
> result of my own work except where explicitly indicated in the text.
> **[TODO: replace with the exact departmental declaration wording]**

The sentences above are a paraphrase I wrote. UCL CS publishes exact wording that
must be used verbatim, and some departments also require a signed/typed name, a
date, and a **statement of word count**.

**What I need:** the exact declaration paragraph from the Moodle submission page or
the MSc handbook, including anything that must follow it (name, date, word count).

**Why it blocks:** the TODO prints in red on page 1 of the submitted PDF. I cannot
flip draft mode off until this is real text.

---

## 2. Word limit — confirm the figure AND what it excludes
Currently the body is **13,727 words** (eight chapters, excluding front matter,
tables, captions, bibliography and appendix).

The repo contradicts itself: a commit message says "limit confirmed 14,000", the
submission checklist says the target is 12,000, and every chapter header still
carries `COMP0234 limit UNVERIFIED`.

**What I need:** the limit, and whether it excludes appendices, references,
figure captions and tables. If it is 12,000 I have a plan; if 14,000 we are fine
with 273 words to spare.

---

## 3. Is the research article a required deliverable?
It is written and complete either way (`05-article/article.tex`, 4pp, IEEE format).
The public COMP0234 catalogue lists only the dissertation and a viva.

**What I need:** confirm with the module lead whether it is submitted, and if so
in what format.

---

## 4. Title-page details — confirm each is exactly right
**File:** `04-dissertation/frontmatter.tex`

| Line | Currently reads | Confirm |
|---|---|---|
| 9 | `Ebenezer Veeraraju` / `Student 25153651` | name as registered, and the student number |
| 11 | `Supervisors: Dr Akin Delibasi (UCL) | Lee Stott (Microsoft)` | Akin's title, and whether Lee should carry one |
| 13 | `MSc Systems Engineering for the Internet of Things` | the exact degree title as awarded |
| 13 | `University College London` | whether the department must also appear |
| 16 | `September 2026` | the date format your department wants |

Also: the title page does **not** currently name a department. The article names
"Dept. of Computer Science". If the MSc sits in a different department, one of the
two is wrong.

---

## 5. Article author block
**File:** `05-article/article.tex` lines 29-38
Co-authorship is confirmed (Akin and Lee), so only the details need checking:

- Your email is `ebenezer.veeraraju.24@ucl.ac.uk` — confirm the exact format.
- Akin is listed with affiliation `University College London` only. Add a
  department or title if he wants one.
- Lee is listed as `Microsoft`. Confirm that is how he wants to appear.

---

## 6. Optional, needs your decision (not blocking)

- **Em dashes.** You said twice you do not want them. The dissertation has 217,
  because the LaTeX `---` I used as house style renders as one. Fixing properly
  means paraphrasing 217 sentences. My advice is to leave it: em dashes are
  normal in academic writing and no marker penalises them. Your call.
- **Glossary + plain-language summary.** You asked twice for a terms legend and a
  layman explanation. Neither exists in the dissertation. Adding both costs about
  300 words, which we do not have unless the deployment-economics subsection in
  the discussion is cut (it is ~500 words of third-party pricing, no evidence of
  ours).
- **Figures.** You asked for charts over text. There are three figures in 40 pages.
  The 18.3% result and the authorship shift are the two most chartable findings
  and are currently prose only.
