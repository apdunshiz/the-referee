# Re-check of every (d) and (e) call against the owner's survey-or-reference-work standard

Researcher: Claude Opus 5.5, 2026-10-29. Read-only on the repo. The rule was read verbatim from `content/site.json` `evidence_rule`. Clauses (a), (b), (c) and (f) are kept exactly as each file has them, and so is "one disagreement charged once". Only (d) and (e) were re-decided.

**How the standard was applied, the same way on all 16 lines**

- **What qualifies.** A clause holds only on one of two sources:
  - a survey of the relevant specialists (PhilPapers 2020, Afshordi-Halper 2026);
  - a passage in SEP, IEP, REP or an Oxford, Cambridge or Blackwell handbook or companion.

  The passage has to say the premise is a minority or widely rejected view (d), or that the rival is widely or commonly accepted, or is the standard or most common response (e). A named scholar's own book or paper never carries a clause by itself.
- **Is it this line's premise or rival?** A passage counts only if it is about the premise this line needs, or the rival to this line's datum, as the line's summary states it. Sometimes a qualifying source shows the argument can run without the premise the minority statement is about. For against-03 that source is the same SEP entry; for against-08 it is the line's own Oxford Handbook source. Then the passage does not show that a *needed* premise is a minority view. This test decides against-03 and against-08, and is applied the same way to for-04. A for-04 passage that covers only one version of its argument is used as support, not as the basis.
- **"Many".** Wording like "taken by many to be…" or "some have suggested…", with nothing about majority, minority, "widely" or "most common", was not treated as enough. Neither was a passage that calls a field divided. The two places this mattered, for-03 and for-08, were settled another way (a survey for for-03; an explicit "fault line" for for-08), so no line's score rests on reading "many" one way or the other. Both readings are in Borderline.
- **How quotes were taken.** SEP and IEP entries were downloaded and searched as plain text, so every quote below is verbatim from the live entry, fetched 2026-10-29. Search terms used in every entry: *widely, majority, minority, most, many, popular, common, standard, consensus, dominant*, plus line-specific terms.

## Summary

| id | current | (d) now → after | (e) now → after | new strength |
|---|---|---|---|---|
| for-01 | 5 | holds → holds | no → no | 5 |
| for-02 | 7 | no → no | holds → holds | 7 |
| for-03 | 5 | holds → holds (now on PhilPapers 2020, not SEP) | no → no | 5 |
| for-04 | 7 | (d)=(e) charged once → same (PhilPapers arithmetic) | (charged with d) | 7 |
| for-05 | 6 | (d)=(e) charged once → same | (charged with d) | 6 |
| for-06 | 4 | no → no | holds → **no** | **5** |
| for-07 | 6 | no → no | not charged (against-03) → same | 6 |
| for-08 | 6 | no → no | holds → **no** | **7** |
| against-01 | 6 | no → no | holds → **no** | **7** |
| against-02 | 5 | no → no | holds → holds (now on IEP, not Swinburne) | 5 |
| against-03 | 5 | holds → **no** | no → no | **6** |
| against-04 | 5 | no → no | holds → **no** | **6** |
| against-05 | 4 | no → no | holds → **no** | **5** |
| against-06 | 4 | (d)=(e) charged once → **no** | (charged with d) → **no** | **5** |
| against-07 | 6 | no → no | no → no | 6 |
| against-08 | 5 | (d)=(e) charged once → **no** | (charged with d) → **no** | **6** |

**Sums.**

| | Before | After |
|---|---|---|
| For | 5+7+5+7+6+4+6+6 = 46 | 5+7+5+7+6+5+6+7 = **48** |
| Against | 6+5+5+5+4+4+6+5 = 40 | 7+5+6+6+5+5+6+6 = **46** |

**Headline:** round(100 × 48 / 94) = round(51.1) = **51%**, down from 53%. The verdict is still "the two sides weigh about the same". Every reading flagged in Borderline keeps the headline between 50% and 55%, so none approaches the 58% switch.

Changes, in short:
- **Down:** six "against" charges fail (against-01, -03, -04, -05, -06, -08), and two "for" charges fail (for-06, for-08).
- **No net change:** two charges now rest on different, qualifying sources (for-03, against-02).

## Per line

### for-01: The universe seems to have had a beginning (5 → 5)

**(d) holds.**
- Afshordi, Halper et al., Big Mysteries Survey, arXiv:2605.11058, §III.1 and App. B.1, N = 1,675. Asked what "the big bang" implies:
  - absolute beginning with a singularity: 19.5%
  - absolute beginning without one: 4.5%
  - "hot, dense state, with no claim about an absolute beginning": 68.4%
- URL: https://arxiv.org/html/2605.11058
- APS write-up: "A large majority (70%) chose to describe it as a hot, dense state", https://physics.aps.org/articles/v19/34

**(e) does not hold.** The 68% answer is agnosticism about a beginning, not a rival explanation. It is already counted under (d). No reference work says a bounce, no-boundary or eternal model is widely accepted. Checked:
- SEP Cosmological Argument
- SEP Cosmology and Theology

No change to `why`.

### for-02: Fine-tuning (7 → 7)

**(e) holds.**
- Same survey, §III.6 and App. B.6, N = 1,675:
  - multiverse: 19.9%
  - a principle such as naturalness: 15.7%
  - Darwinian process: 6.2%
  - together: 41.8%
  - against these, intelligent designer: 8.9%
  - brute fact, 26.0%, is a refusal to explain, not counted as a rival
- Supporting passage, SEP "Fine-Tuning" (Friederich, rev. 2026), §4.4, https://plato.stanford.edu/entries/fine-tuning/: "Many physicists nowadays believe that a specific version of the multiverse hypothesis is indeed suggested by contemporary developments in fundamental physics."

**(d) does not hold.** The premise that the constants need explanation is the majority view in the same survey.

No change to `why`.

### for-03: Something exists rather than nothing (5 → 5; the source for (d) changes)

The (d) charge stands, but on a different source.

**The old source does not meet the standard.** SEP "Principle of Sufficient Reason" (Melamed and Lin, rev. 2023), §1 intro, https://plato.stanford.edu/entries/sufficient-reason/: "The Principle seems at first sight to have a strong intuitive appeal—we always ask for explanations—yet it is taken by many to be too bold and expensive". This is a "many" statement in an entry that also calls the PSR "a powerful and controversial philosophical principle". It is not a minority or widely-rejected statement.
- The entry's §7 "The PSR in Contemporary Philosophy" says nothing about the PSR's standing.
- Neither does SEP "Cosmological Argument" §5.4: its closing judgement is "Critics of the argument will be skeptical regarding the universal application of the principles; defenders of the argument generally not so."

**(d) holds on a survey.**
- PhilPapers 2020, "Principle of sufficient reason: true or false?", target group, N = 936:
  - accept or lean towards true: 35.90% (35.47% exclusive)
  - accept or lean towards false: 45.73% (45.62% exclusive)
  - agnostic or undecided: 13.68%
- URL: https://survey2020.philpeople.org/survey/results/5134. The live page is behind Cloudflare; the figures were read from the Wayback copy of 2025-02-03, https://web.archive.org/web/20250203043421/https://survey2020.philpeople.org/survey/results/5134. The 35.47% figure is independently quoted at https://ruminativebiped.blogspot.com/2023/01/my-philosophical-views-answering-2020.html.
- The survey asks about the PSR in general. The cosmological argument needs the strong PSR, so if anything the minority is larger.
- Limitation: these are all-faculty figures. A metaphysics-only breakdown could not be retrieved; see Borderline.

**(e) does not hold.** A brute fact is a refusal, not a rival.

Replacement `why` (508 chars):
> Start at 5. (a) That the physical world is contingent and its laws and constants unexplained is the standard view (Reichenbach 2026) (+1). (c) Live in the SEP entry on the cosmological argument (Reichenbach 2026) (+1). (d) It needs the principle of sufficient reason, a minority view: 36% of philosophers accept it and 46% reject it (PhilPapers 2020) (−1). (f) From a necessary being to a personal creator is a further contested step (Oppy 2006) (−1). A brute fact is a refusal to explain, not a rival. Five.

### for-04: Morality (7 → 7; the support for (d)/(e) is restated)

**(d) and (e), charged once, hold on PhilPapers 2020, target faculty.**
- Moral realism: 62% (n = 1,719). Theism: 19% (n = 1,770).
- So at least 43% of philosophers are realists who are not theists. They accept that moral facts need no divine ground (the rival) and reject the premise that they do. The premise is therefore a minority view.
- The figures come from the specialist tables reproduced at https://www.greaterwrong.com/posts/JTekFwz3rWjsirBbr/2020-philpapers-survey-results.

**Supporting reference-work passage.** SEP "Moral Arguments for the Existence of God" (Evans and Baggett, rev. 2022), §3, https://plato.stanford.edu/entries/moral-arguments-god/: "the version of a moral argument for God's existence that rests on divine command theory will only be judged powerful by those who find a DCT plausible, and that will certainly be a minority of philosophers. (Although it is worth noting that no single metaethical theory seems to enjoy widespread support among philosophers, so a DCT is not alone in being a minority view.)"
- This covers only the divine-command version of the argument.
- The survey arithmetic covers every version, so the charge rests on the survey. Wielenberg is no longer cited as support.

Replacement `why` (535 chars):
> Start at 5. (a) Moral realism is the majority view: 62% of philosophers (PhilPapers 2020) (+1). (b) Mackie, an atheist, grants that objective values would make a god more probable (Mackie 1982) (+1). (c) Live in the SEP entry on moral arguments (Evans and Baggett 2022) (+1). (d) and (e) are one disagreement, charged once: only 19% of philosophers are theists, so most realists hold that moral facts need no divine ground (PhilPapers 2020; Evans and Baggett 2022) (−1). (f) does not apply: a moral lawgiver is already personal. Seven.

### for-05: Consciousness (6 → 6)

**(d) and (e), charged once, hold.**
- PhilPapers 2020, "Mind: non-physicalism or physicalism?": target 52% physicalism vs 32% non-physicalism (n = 1,733); philosophy-of-mind specialists 60% vs 26% (same tabulation as for-04).
- SEP "Dualism" (Robinson and Weir, rev. 2025), §1, https://plato.stanford.edu/entries/dualism/, confirms it from the reference-work side: "A 2020 survey suggests that dualism is, in this context, the second most popular response to the mind-body problem among professional philosophers … Twenty-two percent … compared to fifty-one percent for" materialism.

No change to `why`.

### for-06: Mathematics and intelligibility (4 → 5)

**(e) does not hold.** The current charge rests on "Pincock, IEP", which does not say the rival is widely accepted.
- IEP "Mathematics, Applicability of" (Pincock), https://iep.utm.edu/math-app/, §§1–3, describes structuralist two-stage accounts: "There are several ways to work out this structuralist program…". It presents them as answers to Frege's constraint and to Steiner. It never says they are standard, widely accepted, or the majority response to the puzzle.
- The entry was searched for *widely, most, standard, consensus, common, popular*, with no hits on the point.
- An extended web search for a reference-work statement on Wigner's puzzle found none.
- This is a reference work describing a rival, which the owner's ruling excludes.

**(d) does not hold.** No survey or reference work calls a needed premise a minority view.

Replacement `why` (482 chars):
> Start at 5. (a) That mathematics describes physical law with great precision is uncontroversial (Wigner 1960) (+1). (c) does not hold: the SEP lists the intelligibility of nature among problematic proposals (Ratzsch and Koperski 2023). (e) does not hold: the IEP describes non-theistic accounts such as structuralism but does not say they are widely accepted (Pincock, IEP). (f) From an intelligible world to a personal creator is a further contested step (Steiner 1998) (−1). Five.

### for-07: Religious experience (6 → 6)

**(d) does not hold.**
- The needed premise is credulity or phenomenal conservatism. PhilPapers 2020 has no question on it.
- SEP "Religious Experience" (Webb 2022) and SEP "Mysticism" (rev. 2026) contain no minority statement. Searched for *widely, majority, minority, most, many, popular*. The only nearby hits are about temporal-lobe seizures, not the premise.

**(e) is not charged.** The rival, natural explanations of religion, is scored as against-03, and each datum counts once. For the record, it would also fail the standard: SEP Mysticism calls it "a reasonable alternative explanation", which describes the rival without saying it is widely accepted.

No change to `why`.

### for-08: Resurrection appearances (6 → 7)

**(d) does not hold. The current refusal is confirmed.**
- SEP "Miracles" (McGrew and Larmer, rev. 2024), §3 on Hume's influence, https://plato.stanford.edu/entries/miracles/: Humean considerations are "endorsed, explicitly or implicitly, in many contemporary studies of the historical Jesus (Dawes 2001: 97–106) and the New Testament (Ehrman 2003: 228–30). Commitment to something like Hume's position lies on one side of a deep conceptual fault line that runs through the discipline of biblical studies."
- That calls the field divided, which the ruling excludes.

**(e) does not hold.** The current charge rests on Ehrman, Lüdemann and Habermas, who are named scholars, not surveys or reference works.
- **SEP "Miracles" §2.2.3** discusses the "minimal facts" argument and the dispute over how rich the agreed appearances are. It never says the vision or grief explanation is widely accepted.
- **Extended web search.** I searched for a handbook or encyclopedia saying most or many critical scholars accept the vision hypothesis and found none.
- **The only literature count cuts the other way.** Habermas, JSHJ 3.2 (2005), https://www.garyhabermas.com/articles/J_Study_Historical_Jesus_3-2_2005/J_Study_Historical_Jesus_3-2_2005.htm, writes that naturalistic alternatives are "argued or suggested by more than forty different scholars … The vast majority of scholars, however, still reject such proposals", and calls them "a minority option among recent scholars".
- It is an apologist's non-random tally, so it is not used as a qualifying survey either way. With nothing qualifying, (e) fails.

Replacement `why` (481 chars):
> Start at 5. (a) That the first followers sincerely believed Jesus appeared to them is near-universal among historians, sceptics included (Ehrman 2014; Habermas 2005) (+1). (c) Live in the SEP entry on miracles (McGrew and Larmer 2024) (+1). (d) does not hold: the SEP calls the refusal to infer miracles one side of a divided field, not the majority. (e) does not hold: no survey or reference work says many historians accept visions or grief experiences as the explanation. Seven.

The status line ("with most non-Christian scholars favouring visions or grief experiences") is not touched by this re-check, but it now has no qualifying source behind it. The owner may want it softened.

### against-01: The amount of suffering (6 → 7)

**(e) does not hold.** The current charge rests on Swinburne, a named scholar, plus Tooley. Tooley's SEP entry says the opposite.
- SEP "The Problem of Evil" (Tooley, rev. 2015), §7 "Theodicies", https://plato.stanford.edu/entries/evil/: "What are the prospects for a complete, or nearly complete theodicy? Some philosophers, such as Swinburne, are optimistic … Others, including many theists, are much less hopeful."
- The same entry, §5.1, names the most popular reply as skeptical theism, which is a refusal to explain, not a rival: "The most popular attempt at a total refutation of the argument from evil claims that, because of human cognitive limitations, there is no sound inductive argument…".
- IEP "The Evidential Problem of Evil" (Trakakis), §4 intro, https://iep.utm.edu/evil-evi/: "Most critics of Rowe's evidential argument have thought that the problem with the argument lies with its factual premise. … According to one popular line of thought, the factual premise can be shown to be false by identifying goods that we know of that would justify God in permitting evil. To do this is to develop a theodicy." "One popular line" among critics is not a statement that the theodicy is widely accepted as adequate. It is the nearest passage; see Borderline.
- Not applicable: IEP "The Logical Problem of Evil" says "it is widely agreed that Plantinga's Free Will Defense describes a state of affairs that is logically possible". That concerns the logical version and a defence, not an explanation of the amount of suffering.

**(d) does not hold.**
- IEP §2b on Rowe's theological premise: "the consensus seems to be that Rowe is right – the theological premise … is usually thought to be indisputable".
- IEP §2c: "most critics" attack the factual premise. Critics are by definition the ones who reject it, so this says nothing about specialists as a whole.

Replacement `why` (541 chars):
> Start at 5. (a) The amount of suffering, including animal suffering over deep time, is granted by both sides (Tooley 2015) (+1). (b) Swinburne, a theist, grants that evil lowers the probability of God (Swinburne 2004) (+1). (c) Live in the SEP entry on the problem of evil (Tooley 2015) (+1). (e) does not hold: the SEP reports that many theists doubt a theodicy can be given, and no survey shows one is widely accepted (Tooley 2015). (f) It rules out only a perfectly good God; an indifferent creator is untouched (Davies 2006) (−1). Seven.

### against-02: Divine hiddenness (5 → 5; the source for (e) changes)

**The SEP does not meet the standard.** SEP "Hiddenness of God" (Howard-Snyder and Green, rev. 2022), §1, https://plato.stanford.edu/entries/divine-hiddenness/: "just as some critics try to explain why God permits evil, so some critics try to explain why God permits nonbelief". That is "some", not "most" or "widely". The current `why` rests on this entry plus Swinburne.

**(e) holds on the IEP.** IEP "Divine Hiddenness Argument against God's Existence" (Teeninga), §2c "Greater Goods and Other Reasons God Might Hide", https://iep.utm.edu/divine-hiddenness-argument/: "The most common strategy for responding to arguments from divine hiddenness is to argue that there is some reason God allows nonresistant nonbelief … Usually, this involves identifying some good thing that God wants to bring about". The section's first named good is "morally significant free will … defended by Richard Swinburne".
- This states the rival is the most common response, which meets "standard/majority response".
- It names a positive explanation, a greater good, so it is not a refusal.

**(d) does not hold.** The relationship-requires-belief premise is attacked (IEP §2b, SEP §2), but no source calls it a minority view.

Replacement `why` (497 chars):
> Start at 5. (a) Most critics grant that some people open to God do not believe (Howard-Snyder and Green 2022) (+1). (b) does not hold: Swinburne finds it leaves God's probability unchanged. (c) Live in the SEP entry on divine hiddenness (Howard-Snyder and Green 2022) (+1). (e) The IEP reports that the most common response is that God permits such nonbelief for a greater good, such as free choice (Teeninga, IEP) (−1). (f) It rules out only a perfectly loving God (Schellenberg 2015) (−1). Five.

The (a) wording is kept as instructed. The SEP itself says "some critics deny the relevant facts", which is consistent with "most grant".

### against-03: Natural origins of religion (5 → 6)

**(d) does not hold, on the "needed premise" test.** SEP "Evolutionary Approaches to Religion" (Marsh, 2026), §2.2 "Criticisms of Evolutionary Debunking Arguments", https://plato.stanford.edu/entries/religion-evolutionary/:
- On sensitivity: "While truth-tracking or sensitivity theories held early promise, contemporary epistemologists tend to reject sensitivity as a requirement for knowledge … Most epistemologists will answer negatively." This meets the standard for the sensitivity condition. The current `why`'s "widely rejected" is not the entry's wording; "tend to reject" is.
- But the same section goes on: "Defenders of debunking arguments sometimes frame their challenges by invoking more widely accepted epistemological principles like safety". It also describes a "debunking argument from false beliefs" (Braddock 2016).
- The line's summary ("if belief in gods is fully explained by how brains and societies work, the beliefs are no evidence that gods exist") does not commit to sensitivity.
- So the reference work shows that one way of stating the premise is minority, and names a more widely accepted way the argument can run. It does not show that a premise the line *needs* is a minority view.

**(e) does not hold.** It is unchanged: the sensus divinitatis rival has no qualifying statement.

Replacement `why` (534 chars):
> Start at 5. (a) That religious belief draws on ordinary cognitive tendencies is the mainstream framework in its field (SEP Evolutionary Approaches to Religion 2026) (+1). (c) That entry treats debunking arguments as live (+1). (d) does not hold: the entry says epistemologists tend to reject the sensitivity condition, but that debunkers can use the more widely accepted safety condition instead. (f) From natural origins to no God is a further step, which the line itself grants: how a belief arises does not show it false (−1). Six.

### against-04: Religious diversity (5 → 6)

**(e) does not hold.** The current charge rests on Plantinga's book plus Basinger.
- SEP "Religious Diversity (Pluralism)" (Basinger, rev. 2025), https://plato.stanford.edu/entries/religious-pluralism/, sets out exclusivist, inclusivist and pluralist responses. Its only majority statements are about other things: the field's focus on theistic religions ("as it currently does for the majority of analytic philosophers of religion"), and "we are not here concerned with the empirical question of how many philosophers fall into each camp".
- IEP "Religious Pluralism" (Norton), https://iep.utm.edu/rel-plur/, §§1–3, likewise describes the views. Its "most commonly adopted strategies" refers to Race's taxonomy, not to exclusivism being accepted.
- No passage says the one-revelation reply is widely accepted.

**(d) does not hold.**
- The needed premise is a symmetry or conciliationist principle.
- PhilPapers 2020 has a "Rational disagreement" question, but it asks permissivism versus non-permissivism, not conciliationism, so it does not test the premise.
- No reference work calls the premise a minority view.

Replacement `why` (542 chars):
> Start at 5. (a) That religions contradict each other and are passed on by family and culture is undisputed (Basinger 2025) (+1). (b) does not hold: Alston's concession is about Christian belief, not God. (c) Live in the SEP entry on religious diversity (Basinger 2025) (+1). (e) does not hold: the SEP sets out exclusivist and inclusivist replies but does not say they are widely accepted. (f) From at most one religion being right to no God is a further step; Hick reads the same facts as many responses to one reality (Hick 1989) (−1). Six.

### against-05: A vast, old, hostile universe (4 → 5)

**(e) does not hold.** The current charge rests on Dicke 1961, a paper, and Collins in the Blackwell Companion to Natural Theology (2009).
- **SEP "Fine-Tuning" (Friederich, rev. 2026), §4.1**, https://plato.stanford.edu/entries/fine-tuning/: "A paradigmatic anthropic 'explanation' … is astrophysicist Robert Dicke's (1961) account of coincidences between large numbers in cosmology … (Earman [1987: 309], however, disputes that Dicke's account is adequately characterized as an 'explanation'.)"
  - It describes Dicke's account of the *age coincidence*.
  - It notes a dispute.
  - It never says the account is the accepted answer to the argument from scale or hostility.
- **Collins's Blackwell chapter** is on the owner's list of reference works, but I could not retrieve its text: the publisher is paywalled and the Messiah University repository would not resolve. As described in the cosmos report, it states that a life-permitting universe must be large and old, which is Collins's own argument within the volume. Nothing indicates it says this reply is widely or commonly accepted as the explanation of the datum. See Borderline.
- **Extended web search** for a reference work on the argument from scale found none.

**(d) does not hold.** No source.

Replacement `why` (467 chars):
> Start at 5. (a) The size, age and emptiness of the universe are mainstream cosmology (Dicke 1961) (+1). (e) does not hold: the SEP describes Dicke's account of why observers find an old universe but does not say it is the accepted answer to this argument (Friederich 2026). (f) From a universe not built mainly for humans to no God needs a contested premise about God's purposes (Dumsday 2019) (−1). No reference work treats it as live, and no theist grants it. Five.

### against-06: No detectable divine action (4 → 5)

**(d) and (e) do not hold.** They are one disagreement, charged once.
- SEP "Petitionary Prayer" (Davison, rev. 2026), §4, https://plato.stanford.edu/entries/petitionary-prayer/: "Some have suggested, though, that these kinds of studies are flawed from the outset (see Brümmer 2008 and Davison 2017, chapter 5). … Also, God is typically assumed to be a free person, not a natural force that acts automatically in all similar cases, so we cannot assume that God will simply ignore those people for whom petitionary prayers have not been offered."
  - The claim that rejects the line's premise is attributed to "some".
  - "Typically assumed" describes how God is usually conceived. It is not a statement that specialists reject the test premise, so it does not meet the standard; see Borderline.
- The STEP team's disclaimer (Harvard Gazette, 2006) is neither a survey nor a reference work.
- IEP has no petitionary-prayer entry; the URLs tried returned 404.

Replacement `why` (492 chars):
> Start at 5. (a) Controlled prayer trials find no effect (Benson 2006; Masters 2006; Cochrane 2009) (+1). (d) and (e) do not hold: the SEP entry on petitionary prayer says only that some judge such tests flawed, since God is taken to be a free person (Davison 2026). (f) It rules out only a God who intervenes visibly; a deist creator is untouched, and the trial team says its results do not bear on God's existence (Benson 2006) (−1). No reference work treats it as a standing argument. Five.

### against-07: Minds depend on brains (6 → 6)

**(e) does not hold.** The current refusal is confirmed.
- SEP "Dualism" (Robinson and Weir, rev. 2025), §1: dualism is "the second most popular response to the mind-body problem among professional philosophers" at 22%. That figure includes property dualists, who deny a separable soul.
- So no source says many specialists accept the rival this line needs: a soul that uses the brain and can exist without it.

**(d) does not hold.** No source.

No change to `why`.

### against-08: Gaps retreating (5 → 6)

**(d) and (e) do not hold.** They are one disagreement, charged once. The current charge rests on Plantinga 2011 and Numbers 2009, a book and an edited volume, so neither qualifies. The nearest reference-work passage fails the needed-premise test.
- SEP "Religion and Science" (De Cruz, rev. 2022), §1.2, https://plato.stanford.edu/entries/religion-science/, first defines the model: "The conflict model holds that science and religion are in perpetual and principal conflict. It relies heavily on two historical narratives: the trial of Galileo … and the reception of Darwinism".
- Then: "The vast majority of authors in the science and religion field is critical of the conflict model and believes it is based on a shallow and partisan reading of the historical record. While the conflict model is at present a minority position, … Alvin Plantinga (2011) has argued that the conflict is not between science and religion, but between science and naturalism."
- **Needed-premise test.** The line, as summarised ("explained by God and are now explained without him … God was never the explanation"), needs only that natural explanations replaced divine ones, domain by domain. It does not need science and religion to be in "perpetual and principal conflict".
- The line's own (c) source shows the argument runs without that model: Draper's chapter in the Oxford Handbook of Philosophy of Religion (2005), which is on the owner's list, argues from the success of naturalistic explanation as evidence, not from a conflict thesis.
- So the SEP's minority statement is about a stronger thesis this line does not need. This is the same test that decides against-03.
- The rival, same entry §3.1, is described but not said to be widely accepted: "Theistic evolutionists hold a non-interventionist approach to divine action: God creates indirectly, through the laws of nature".
- Also checked: SEP "Naturalism" (Papineau, rev. 2020) and IEP "Naturalism". Searched for *gaps, secondary causes, most theists, majority, widely*, with no qualifying statement.

Replacement `why` (539 chars):
> Start at 5. (a) Domain after domain once explained by God is now explained naturally (Papineau 2020) (+1). (c) Live in the SEP entry on naturalism and in Draper's Oxford Handbook chapter (Papineau 2020; Draper 2005) (+1). (d) and (e) do not hold: the SEP calls only the conflict model a minority position, and Draper argues from the same history without it (De Cruz 2022). (f) From God not being needed inside science to no God needs the further, contested step that why there are laws is a gap of the same kind (Plantinga 2011) (−1). Six.

## Borderline

1. **against-03 (d)** decides 6 against 5.
   - **Holds (5):** the SEP says epistemologists "tend to reject" sensitivity and "most epistemologists" reject its sceptical result. The line's debunking premise is, in practice, usually stated as sensitivity.
   - **Fails (6, applied):** the same passage says debunkers can use "more widely accepted" safety, so no needed premise is shown to be a minority view.
2. **against-08 (d)/(e)** decides 6 against 5.
   - **Fails (6, applied):** the SEP's conflict model is "perpetual and principal conflict", stronger than the line needs, and Draper's evidential version (Oxford Handbook 2005) runs without it.
   - **Holds (5):** the line's "God keeps retreating" framing is the warfare narrative the SEP calls "a minority position", rejected by "the vast majority of authors in the science and religion field".
   - against-03 and against-08 rest on one test, so they should move together. If the owner prefers the "holds" reading for both, each returns to 5: against 44, headline 48/92 = 52%.
3. **against-06 (d)/(e)** decides 5 against 4.
   - **Holds (4):** "God is typically assumed to be a free person, not a natural force that acts automatically" says, in substance, that the rival conception is the standard one.
   - **Fails (5, applied):** the inference that the trials are flawed is attributed to "some", and "typically assumed" is about how God is conceived, not about specialists' judgement of the test.
4. **against-01 (e)** decides 7 against 6.
   - **Holds (6):** IEP's "one popular line of thought … To do this is to develop a theodicy" counts as a commonly accepted response.
   - **Fails (7, applied):** "one popular line" among critics is weaker than against-02's "the most common strategy". The SEP entry explicitly says many theists are "much less hopeful" about theodicy, and names skeptical theism, a refusal, as the most popular reply.
5. **against-02 (e)** decides 5 against 6. IEP's "most common strategy" refers to the strategy of giving a reason. If the owner reads that as describing what critics *attempt*, not what specialists *accept as adequate*, (e) fails and against-02 is 6. Read evenly with against-01, both would then be at their higher scores: against-01 7, against-02 6.
6. **for-03 (d): which population counts.** PhilPapers 2020 all-faculty: 36% true, 46% false. A metaphysics-only breakdown was not retrievable through Cloudflare or the archive.
   - Philosophers of religion are 74% theist (same survey) and probably favour the PSR, so a philosophy-of-religion subgroup might show a majority for it.
   - The owner's ruling names PhilPapers without restricting it to a subfield, and for-01 uses an all-respondents physics survey. If the owner instead wants the argument's own subfield, (d) may fail and for-03 rises to 6.
   - Separately, the earlier SEP "taken by many to be too bold and expensive" would carry (d) only on the reading that "many" equals "widely". That same reading would then also make for-08's (d) hold ("endorsed … in many contemporary studies"), lowering for-08 to 6. The two must move together.
7. **for-02 (e).** The 42% is three rivals summed. The largest single one, the multiverse, is 19.9%, still more than twice the designer's 8.9%, and the SEP adds "Many physicists nowadays believe…" the multiverse is suggested by physics. If the owner requires one rival to reach "widely accepted" alone, (e) fails and for-02 is 8.
8. **against-05 (e) and Collins.** Collins's chapter in the Blackwell Companion to Natural Theology could not be read. If it states, as accepted physics, that any life-bearing universe must be vast and old, the owner may count it as a reference-work statement and return against-05 to 4. It would still not touch the "lethal nearly everywhere" part of the datum.
9. **for-08 (e) and Habermas.** If an apologist's literature count is accepted as a survey, it says the "vast majority of scholars … reject" naturalistic proposals. That confirms (e) fails, so it cannot lower for-08.

**Range.** Across all the alternative readings above, the headline stays between 50% and 55%:
- **Lowest:** for-08 at 6, with against-02 at 6, gives 47/94.
- **Highest:** for-02 at 8 and for-03 at 6, with against-01 at 6 and against-03, -05, -06 and -08 at their lower readings, gives 50/91.

No reading reaches the 58% verdict switch.

## Sources fetched (verbatim text, 2026-10-29)

- SEP Principle of Sufficient Reason (Melamed and Lin, rev. 2023): https://plato.stanford.edu/entries/sufficient-reason/
- SEP Cosmological Argument (Reichenbach, rev. 2026): https://plato.stanford.edu/entries/cosmological-argument/
- SEP Fine-Tuning (Friederich, rev. 2026): https://plato.stanford.edu/entries/fine-tuning/
- SEP Moral Arguments for the Existence of God (Evans and Baggett, rev. 2022): https://plato.stanford.edu/entries/moral-arguments-god/
- SEP Dualism (Robinson and Weir, rev. 2025): https://plato.stanford.edu/entries/dualism/
- SEP Religious Experience (Webb 2022): https://plato.stanford.edu/entries/religious-experience/ ; SEP Mysticism (rev. 2026): https://plato.stanford.edu/entries/mysticism/
- SEP Miracles (McGrew and Larmer, rev. 2024): https://plato.stanford.edu/entries/miracles/
- SEP The Problem of Evil (Tooley, rev. 2015): https://plato.stanford.edu/entries/evil/
- SEP Hiddenness of God (Howard-Snyder and Green, rev. 2022): https://plato.stanford.edu/entries/divine-hiddenness/
- SEP Evolutionary Approaches to Religion (Marsh, 2026): https://plato.stanford.edu/entries/religion-evolutionary/
- SEP Religious Diversity (Pluralism) (Basinger, rev. 2025): https://plato.stanford.edu/entries/religious-pluralism/
- SEP Petitionary Prayer (Davison, rev. 2026): https://plato.stanford.edu/entries/petitionary-prayer/
- SEP Religion and Science (De Cruz, rev. 2022): https://plato.stanford.edu/entries/religion-science/
- IEP Mathematics, Applicability of (Pincock): https://iep.utm.edu/math-app/
- IEP The Evidential Problem of Evil (Trakakis): https://iep.utm.edu/evil-evi/ ; IEP The Logical Problem of Evil: https://iep.utm.edu/evil-log/
- IEP Divine Hiddenness Argument against God's Existence (Teeninga): https://iep.utm.edu/divine-hiddenness-argument/
- IEP Religious Pluralism (Norton): https://iep.utm.edu/rel-plur/
- PhilPapers 2020, PSR question (archived 2025-02-03): https://web.archive.org/web/20250203043421/https://survey2020.philpeople.org/survey/results/5134
- PhilPapers 2020 specialist tables (Bensinger): https://www.greaterwrong.com/posts/JTekFwz3rWjsirBbr/2020-philpapers-survey-results
- Afshordi, Halper, Rini and Schirber, Big Mysteries Survey, arXiv:2605.11058 (2026): https://arxiv.org/html/2605.11058 ; APS write-up: https://physics.aps.org/articles/v19/34
- Habermas, "Resurrection Research from 1975 to the Present", JSHJ 3.2 (2005): https://www.garyhabermas.com/articles/J_Study_Historical_Jesus_3-2_2005/J_Study_Historical_Jesus_3-2_2005.htm
- Not retrievable: Collins, Blackwell Companion to Natural Theology ch. 4 (2009); PhilPapers 2020 metaphysics-only breakdown for the PSR.
