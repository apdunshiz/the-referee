# Moral fruit: two alternative rules (draft for Alex, 2026-10-28)

## The problem
The current rule subtracts a point for each of three classes "present in the record of the tradition or of states built on it". Presence is binary and the record is cumulative, so any tradition that governed for centuries has all three classes and sits at 5, while a stance that never held power is capped at 5 by the no-record clause. After the research pass every worldview scores 5 except naturalism (6). The criterion no longer discriminates, and what it did measure was tenure of state power, not ethic. Every one of the seven reports flagged this.

Current rule: "Start at 8 for an ethic that, in its best expression, extends to outsiders. Subtract 1 for each of three classes present in the record of the tradition or of states built on it: wars and conquest in its name; persecution or legal coercion of dissenters, apostates or a subordinate group; an exclusion written into its structure (caste, slavery sanctioned from its texts). Opposition from within does not restore a point. A stance with no communities and no record scores 5. Influence on the wider world is not scored."

## Option A: texts and self-correction (recommended)
Score what the tradition teaches and whether it corrected itself, not how long it held power.

> Start at 8 for an ethic that, in its best expression, extends to outsiders. Subtract 1 for each of three classes that the tradition's own authoritative texts or traditional law command or sanction: war or conquest; coercion of dissenters, apostates or a subordinate group; an exclusion written into its structure (caste, slavery, a subordinate class). What states did on their own account is not scored. Add 1, once, if the tradition reversed one of those classes from within, by appeal to its own sources, and the reversal now holds in its mainstream. A stance with no texts of its own is tested on its canonical statements, and a state that professed it by decree or constitution counts for the coercion class only.

Why: it keeps "best expression and record" but scores the record a tradition is responsible for (its texts and law) rather than the one it had the opportunity to make. The reform credit rewards the clearest moral fact in the data, a tradition reversing its own sanction (abolitionism, the bhikkhuni revival, rabbinic neutralisation of herem), which the current rule says is "worth exactly nothing".

Estimated effect (moral score, then total). Estimates only; a research pass under the new rule would set them.

| Worldview | Moral now | Moral A | Total A | Basis |
|---|---|---|---|---|
| Naturalism | 6 | 7 | 30 | manifestos command none; Soviet decree counts for coercion (−1) |
| Buddhism | 5 | 7 | 29 | garudhammas (−1); war and coercion not in its texts; bhikkhuni revival not yet mainstream (no credit) |
| Deism | 5 | 7 | 27 | nothing in its texts; the Jacobin decree and Terror count for coercion (−1) |
| Christianity | 5 | 6 | 26 | inherited holy-war texts, heresy law, slavery (−3); abolition from within now mainstream (+1) |
| Islam | 5 | 5 | 25 | jihad verses, apostasy law, slavery (−3); abolition contested as from within (no credit; 6 if credited) |
| Judaism | 5 | 6 | 25 | herem, Deut 13 coercion, Lev 25 slavery (−3); rabbinic law neutralised herem (+1) |
| Hinduism | 5 | 5 | 24 | Manu on war and heretics, caste (−3); caste reform came from the state, not the tradition's law (no credit) |

## Option B: the living record
Score present practice only; the historical record measures opportunity, not ethic.

> Start at 8 for an ethic that, in its best expression, extends to outsiders. Subtract 1 for each of three classes present in the tradition's mainstream practice, law or movements within the last fifty years: violence or war in its name; legal coercion of dissenters, apostates or a subordinate group by states built on it; an exclusion still written into its structure. The historical record is not scored. A stance with no communities and no record scores 5.

Why: simplest to source, and it answers the question a visitor actually asks (what does this tradition do now). Cost: it rewards traditions whose states happen to be liberal today and still caps stateless stances at 5.

| Worldview | Moral now | Moral B | Total B | Basis |
|---|---|---|---|---|
| Naturalism | 6 | 7 | 30 | China's persecution of believers (−1) |
| Christianity | 5 | 7 | 27 | women barred from ordination in Catholic and Orthodox structure (−1); war and state coercion marginal |
| Buddhism | 5 | 5 | 27 | Myanmar and Sri Lanka violence, Myanmar's 2015 religion laws, garudhammas (−3) |
| Islam | 5 | 5 | 25 | jihadist war, apostasy and blasphemy laws, women's legal status (−3) |
| Deism | 5 | 5 | 25 | no record clause |
| Judaism | 5 | 6 | 25 | religious-nationalist violence contested; rabbinate's legal control and Orthodox women's status (−2) |
| Hinduism | 5 | 5 | 24 | Hindutva violence, anti-conversion laws, caste (−3) |

## Either way
The new rule goes into content/site.json, the seven moral `why` lines are rewritten with sources under the new rule (a research pass, one agent, about 30 minutes), the Rubric and Religions pages pick up the new text automatically, and nothing moves until you approve each line.
