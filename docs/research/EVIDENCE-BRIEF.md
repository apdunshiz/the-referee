# Research brief: re-examine The Referee's evidence lines

The Referee (https://apdunshiz.github.io/the-referee/) lists 16 lines of evidence, 8 for God and 8 against, each with a strength 0-10. The home page headline is sum(for) / (sum(for) + sum(against)), now 42 / 84 = 50%. Alex (the owner) asked for deep research before any number moves: "I don't want you to change them randomly." The worldview scores were fixed the same way: one written rule per criterion, applied evenly, every change ruled on by the owner. The evidence strengths have no written rule yet. Your job is evidence and arithmetic, not a verdict: the owner decides every change.

## Inputs (read first)
- Your evidence files: /Users/aplevell/Dev/personal/the-referee/content/evidence/<id>.md (frontmatter: title, summary, strength, confidence, status, best_objection, best_reply, sources; body is the outsider's note).
- Skim all 16 files in that folder so you score your lines on the same scale as the rest.
- How worldview rules look and are applied: content/site.json `criteria`, and any file in content/worldviews/ (each `why` states arithmetic that reaches the score).

## The draft strength rule (DRAFT, not yet approved; apply it exactly, propose changes only in the last section)
> Strength is how much the best version of the line moves an outsider toward its conclusion (God, or no God). Start at 5. Add 1 for each that holds: (a) its key datum is the mainstream view in the relevant science or scholarship; (b) leading defenders of the other side, named, grant that the datum is at least some evidence for this side; (c) standard reference works (Stanford Encyclopedia of Philosophy, Oxford or Cambridge handbooks) treat the argument as live, not as refuted. Subtract 1 for each that holds: (d) a premise the argument needs is a minority view among specialists in its field; (e) a rival explanation of the datum is accepted as adequate by many specialists in the field; (f) getting from the conclusion to God, or to no God, needs a further contested step (for example, from "a cause" to "a personal God", or from "no detectable action" to "no God"). Each datum counts once across both columns.

"Specialists" means the people who study that datum: cosmologists for the beginning, physicists for fine-tuning, historians of early Christianity for the resurrection, philosophers of mind for consciousness, and so on, believers and non-believers alike. Where survey data exists (PhilPapers 2009/2020, surveys of physicists or New Testament scholars), use it.

## Double counting (required section)
Judge whether each of these pairs is the same datum counted twice or two distinct data, where it touches your lines: for-02 vs against-05 (fine-tuning vs a vast hostile universe); for-05 vs against-07 (consciousness vs mind depends on brain); for-07 vs against-03 (religious experience vs natural explanations of religion); for-01 vs for-03 (beginning vs contingency); against-02, against-06, against-08 (hiddenness, no detectable action, God of the gaps retreating). For each: same datum or distinct, the reason, and what a merge would do (merged into which line, at what strength). Because the headline is a ratio of the two column sums, a merge on one side only moves the percentage for structural reasons; say so where it applies.

## Research standard
- Use WebSearch in "extended" mode and WebFetch. Prefer peer-reviewed work, university-press books, the Stanford Encyclopedia of Philosophy and Oxford/Cambridge handbooks, and named scholars on both sides. Apologetics or polemic only to report what a side's best defenders say, labelled as such.
- For each line, find the strongest scholarly case that the current strength is too high AND too low. Steelman both sides by name.
- Every claim you rely on gets a citation: author, title, year, URL. At least 4 sources per line.
- Numbers of believers are not evidence; do not use them.
- Never include Reddit usernames or quote Reddit.
- Read-only on the repo: do not edit, commit or push anything under /Users/aplevell/Dev/personal/the-referee. Do not run tasks.py. Write only your report file.

## Output: write /Users/aplevell/.t3/scratch/2026-10-21-a-while-ago-you-helped-ad53e7c0/research/evidence-<group>.md
In this order, about 600-900 words per line:
1. `## Summary`: a table of your lines (id, title, current strength, proposed strength, confidence 0-100), then one paragraph on what the research changes and what it confirms.
2. One `## <id>: <title>` section per line, each with:
   - **Current:** strength, confidence, and the file's `status` quoted.
   - **Evidence:** 4-8 bullets, each a fact with its citation, covering both directions.
   - **Rule applied:** step by step, each of (a)-(f) marked holds or not with the reason, ending in the number, e.g. "Start at 5. (a) holds: ... (+1). (b) holds: ... (+1). (e) holds: ... (−1). Six."
   - **Proposed:** keep N, or change N→M, the single strongest reason, and a confidence 0-100.
   - **Text fixes:** any sentence in summary, status, best_objection, best_reply or body that is false, overstated, or would be false after the change. Give the replacement text. Limits: summary 400, status 300, best_objection and best_reply 600 characters.
   - **If the owner disagrees:** the one fact he would have to weigh differently.
3. `## Double counting`: as above, for the pairs that touch your lines.
4. `## Rule problems (not scored)`: anything in the draft rule that judges your lines unfairly or can't be checked, with an example and a suggested rewording.
5. `## Sources`: numbered list, author, title, year, URL.

Final reply to the orchestrator (not the file): line 1 your model name, then one line per evidence id "id: current → proposed, reason", then the report path. Nothing else.
