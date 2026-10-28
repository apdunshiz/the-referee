# Research brief: re-examine one worldview's scores on The Referee

The Referee (https://apdunshiz.github.io/the-referee/) scores seven worldviews 0-10 on five criteria, from an outsider's perspective, with a written rule per criterion. Alex (the owner) finds the current ranking hard to credit (Buddhism 29, Hinduism 26 above Christianity 25) and asked for deep research before any number moves. He said: "I don't want you to change them randomly." Your job is evidence, not a verdict: the owner decides every score change.

## Inputs (read these first)
- The worldview record: /Users/aplevell/Dev/personal/the-referee/content/worldviews/<id>.md (frontmatter has each score, its confidence and the `why` reasoning that states the arithmetic; the body is the outsider's note).
- The five rules, verbatim, in content/site.json under `criteria`; also pasted below.
- For calibration, skim the other six worldview files in the same folder so you apply the rules the same way the others were scored. The same rule must give the same deduction for the same kind of fact across traditions.

## The rules (apply exactly; propose a rule change only in the separate section at the end)
- history: Start at 5. Add 1 for each kind of foundation that holds under ordinary scrutiny: a well-attested founder or founding event; an early, stable text; a continuous, documented community; the scientific record where the worldview rests on it. Subtract 1 for each kind of foundational claim that scrutiny has gone against: founding events without support; biographical sources written late with legend; claims that conflict with the record. Miracle narratives are beyond history's reach and neither count nor cost. Popular claims, such as science read into scripture, are not scored.
- consistency: Start at 8 for a system whose core claims fit together; subtract 1 for each core doctrine that needs careful definition to avoid contradiction, judged on the tradition's own best statement (the Trinity, no-self with rebirth, divine mercy with eternal punishment, binding obligation in a world of particles). Disagreements between texts are a history matter, not scored here.
- explanation: Four questions: a lawful cosmos, conscious minds, moral obligation, suffering. Start at 2; add 1 for each question the worldview gives an answer to (an honest refusal to answer is not an answer; an inherited cosmology counts as an answer for everyone who has one). Add 1 more, once, if any of its answers is treated by philosophers across the divide as a distinctive resource.
- testability: Exposure of the central claim, 0 to 5. Then add 1 for each kind of checkable claim that has held and subtract 1 for each kind that has failed. Each kind is scored once: foundation claims already scored under history are not scored again; prayer trials count once against every tradition that promises answered prayer; meditation and rebirth-memory research count the same way for every tradition that makes those claims.
- moral: Start at 8 for an ethic that, in its best expression, extends to outsiders. Subtract 1 for each of three classes present in the record of the tradition or of states built on it: wars and conquest in its name; persecution or legal coercion of dissenters, apostates or a subordinate group; an exclusion written into its structure (caste, slavery sanctioned from its texts). Opposition from within does not restore a point. A stance with no communities and no record scores 5. Influence on the wider world is not scored.

## Research standard
- Use WebSearch in "extended" mode and WebFetch. Prefer peer-reviewed work, university-press books, standard reference works (Stanford Encyclopedia of Philosophy, Oxford handbooks), and named scholars on both sides of the divide (believing and non-believing). Avoid apologetics blogs and polemics unless you are quoting what the tradition's best defenders say, and label them as such.
- For each criterion, find the strongest scholarly case that the current score is too low AND the strongest case that it is too high. Steelman the tradition's own best defenders by name.
- Every claim you rely on gets a citation: author, title, year, and URL. At least 8 sources per worldview, at least one per criterion.
- Numbers of adherents are not evidence for any criterion; do not use them.
- Never include Reddit usernames or quote Reddit.
- Read-only on the repo: do not edit, commit or push anything under /Users/aplevell/Dev/personal/the-referee. Do not run tasks.py. Write only your report file.

## Output: write /Users/aplevell/.t3/scratch/2026-10-21-a-while-ago-you-helped-ad53e7c0/research/<id>.md
Structure, in this order, about 1500-2500 words:
1. `## Summary`: current total, proposed total, one paragraph on what the research changes and what it confirms.
2. One `## <Criterion name>` section per criterion, each with:
   - **Current:** score, confidence, and the file's `why` quoted.
   - **Evidence:** 3-8 bullets, each a fact with its citation, covering both directions.
   - **Rule applied:** the arithmetic, step by step, the way the file's `why` does it (e.g. "Start at 5. Holds: founder (+1), community (+1). Gone against: late biography (−1). Five.").
   - **Proposed:** keep N, or change N→M, with the single strongest reason, and a confidence 0-100.
   - **If the owner disagrees:** the one fact he would have to weigh differently.
3. `## Calibration check`: two or three cases where the same kind of fact was scored differently for another worldview in the folder (quote both files), and which way it should be reconciled.
4. `## Rule problems (not scored)`: anything in the rules that makes the comparison unfair, e.g. a rule that punishes traditions for having held state power longer, or a double count. Do not adjust scores for these; just name them with an example.
5. `## Sources`: numbered list, author, title, year, URL.

Final reply to the orchestrator (not the file): the model name on line 1, then current total → proposed total, a one-line reason per changed criterion, and the report path. Nothing else.
