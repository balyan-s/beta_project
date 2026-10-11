# Step 8 Review — Typing Simulator: Condition Report

**Verdict: STRUCTURALLY SOUND, RESULTS NOT USABLE YET.**
The simulator architecture is good and should be kept. The *policy comparison
results* in `results/` are misleading and need to be regenerated after fixing
the issues below. Ranked by severity.

---

## What is genuinely good (keep it)

1. **Right data sources, right division of labor.** Per-query pace from
   AmazonQAC (`amazonqac_pace_quantiles.csv`, median 0.67 s/key) + gap *shape*
   from Aalto 136M keystrokes (`aalto_gap_shape.csv`), rescaled so mean gap =
   real pace. This satisfies "do not invent pause timings" as well as the data
   allows — see Issue A for the honest caveat.
2. **Step 8's timestamp question was correctly answered.** AmazonQAC gives one
   `first_prefix_typed_time` and one `search_time` **per prefix sequence, not
   per keystroke** — confirmed empirically by the code itself
   (`src/typing_sim.py` docstring, `make_pace_table.py`). Falling back to Aalto
   for intra-query gap shape is exactly what `PROJECT_GUIDELINE.md` §2a
   prescribes ("fall back to the Aalto typing studies if finer granularity is
   needed").
3. **Metric wiring is correct.** `policy_eval.py` reads `metric_choice.json`
   per granularity (keystrokes for partial_word/next_word/phrase, embeddings
   for sentence) — matches Step 6 output, no retired metric used.
4. **Seeded and reproducible.** I re-ran `python -m src.policy_eval aalto` with
   seed 42; output is byte-identical to `results/policy_eval_aalto.txt`. Rule 5
   satisfied.
5. **Staleness rule enforced in code**, as Step 10 demands (`ks0 >= k` check in
   `policy_eval.py` lines 142–145), with value discounted by characters typed
   during latency. Good.
6. **Frozen inputs respected.** Reads `phase1_results_v2.csv` read-only; no
   overwrite risk flagged in the guide.

---

## Issues that make the current results untrustworthy

### A. HIGH — "Real gap shape" is only half-real, and the paper must say so
AmazonQAC timestamps are per-**prefix**, so per-keystroke gaps are *modeled*,
not observed — from Aalto. That is defensible, but two properties are silently
dropped:
- **Backspacing.** Real prefix sequences contain corrections (the old
  `typing_simulator.py` even prints "backspacing seen in the raw data"). Both
  simulators assume strictly monotonic character-by-character growth. Pauses
  before a correction are a major real source of >0.5 s gaps — precisely the
  events pause-based policies key on. Current results therefore *understate*
  how often pauses occur before hard-to-predict continuations.
- **Correlation structure.** Gaps are drawn i.i.d.; real typing has autocorrelated
  bursts (thinking blocks). With i.i.d. gaps, "pause 0.3s" fires on 78% of keys
  under the Aalto style simply because every gap is an independent draw near
  the median — a realistic typist clusters pauses instead.
**Fix:** either add a documented backspace/correction model, or state the
i.i.d.-gap assumption explicitly in the write-up and treat absolute pause
thresholds as relative comparisons only.

### B. HIGH — The headline finding is an artifact of a broken denominator
Look at `missed %`: word boundary misses **100%** of good partial_word
suggestions while `every 3 keys` "misses" only ~64%. That is not a policy
result — it is arithmetic: the decision point for partial_word is mid-word, and
a space can never occur at that exact key, so the policy is structurally unable
to fire there. Reporting it as "100% missed" without saying "this pairing is
impossible by construction" is wrong.
Related: the invocation-rate column mixes denominators — it averages over ALL
keys typed up to the decision point (including the irrelevant early part of
the message), while calls/value are counted only AT the decision point. So
"calls/100 keys" for word-boundary (≈20) describes behavior the experiment
never actually uses. Pick one denominator (recommendation: keys within the last
word, or normalize per session and report both) and document it.

### C. HIGH — Quality numbers are dominated by Phase 1's zero-inflation, not by timing
From the frozen predictions: median `keystrokes_saved` = **0 at every
granularity**; ks0>0 only 17–35%; `sim >= 0.4` essentially 0% except phrase/
sentence (~14–17%). Consequences visible in the results files:
- `value/call` for always-invoke is 0.09–0.17 (partial_word) — mostly zeros.
- My recomputation: at typical pace, **84% of partial_word suggestions arrive
  with value ≤ 0 even with zero policy delay**. So "value kept %" and
  "missed %" conflate *"the model was never useful here"* with *"the policy
  skipped a useful call."* A policy comparison where the baseline itself
  delivers almost nothing cannot answer the research question.
**Fix:** restrict the policy pilot to examples where always-invoke delivers
positive value (a "decidable subset"), report the subset size, and keep the
full-set numbers as a secondary table. Also replace `GOOD_SIM = 0.4` — marked
"provisional" in the code — with a threshold justified against the label data,
and pre-register it like Step 6.

### D. MEDIUM — Pause thresholds were chosen without looking at the simulated distribution
Measured on the actual simulator output (Aalto style): median gap 0.56 s,
p90 1.83 s; **78% of gaps exceed 0.3 s** → "pause 0.3s" is barely a filter at
all (it still calls on 78 of 100 keys). The interesting operating points are
0.6–1.0 s+. Add thresholds like 0.5 / 0.8 / 1.5 / 2.0 s, and calibrate them to
target invocation rates rather than round numbers.

### E. MEDIUM — Pace tail distorts the robustness styles
The AmazonQAC pace distribution has a heavy tail (p90 = 1.65 s/key, trimmed max
≈ 24 s/key). Because each style rescales gaps to preserve the *mean*, slow
typists get their gaps stretched, which inflates the modelled styles' p90 and
compresses the intended sigma contrast: style 2 ("bursty") actually produces
*fewer* >1 s gaps (21%) than the Aalto real-shape run (25%). The three "styles"
are less distinct than their names suggest. Consider trimming pace harder
(e.g., drop queries > 5 s/key), or sampling gaps around the typist's *median*
rather than mean.

### F. LOW — Dead/duplicate code creates confusion about what "the simulator" is
Four overlapping entry points: root `typing_simulator.py` (wall-clock demo,
sleeps in real time, unusable for experiments), `run_typing_simulator.py`
(one-off dataset inspection), `src/typing_sim.py` + `src/gap_shape.py` (the
real engine), `src/policy_timing.py` (superseded by `policy_eval.py`, and its
"in time %" definition differs from the staleness rule in `policy_eval.py` —
two different notions of timeliness in one repo). Move the demo scripts to
`scripts/` or delete them; note in the README that `policy_timing.py` is
deprecated in favor of `policy_eval.py`.

### G. LOW — Scope vs. Step 11
The pilot runs on the frozen 200-message Phase 1 results, which is fine for a
pilot, but the guideline warns the final eval needs `N_MESSAGES=260` and a
message-level split. Don't let these tables become the paper's main table.
Also: `src/policy_timing.py` seeds via module-level rng (ok), but the demo
`typing_simulator.py` is unseeded/async and adds nothing — see F.

### H. LOW — Missing deliverables from Step 8 itself
Step 8 says: *"Write down the answer [per-keystroke or per-prefix] and cite
it."* The answer is implicitly in code comments but nowhere written up with a
citation (AmazonQAC paper/dataset card + Aalto 136M Keystrokes link, which
`fit_aalto_gaps.py` does carry). Add a short "Timing model" section to the
README documenting: per-prefix confirmed; pace source + quantiles; gap-shape
source + the 1.48× boundary multiplier and 0.86 log-std actually produced;
i.i.d./no-backspace assumptions.

---

## Sanity checks performed for this review
- Re-ran `src.policy_eval aalto`: output identical to committed file (reproducible ✓)
- `src.typing_sim` self-test runs ✓
- `metric_choice.json` present, matches README Part-1 story ✓ (Part 1 done)
- Recomputed gap distributions from both simulators (numbers quoted above)
- Recomputed zero-inflation of ks0/sim from `phase1_results_v2.csv`

## Recommended order of work
1. Fix B (denominator + impossible-policy reporting) — small code change, removes the worst artifact.
2. Fix C (decidable subset + GOOD_SIM justification) — without it, quality columns are noise.
3. Fix D (threshold grid) — cheap, immediately more informative.
4. Write up H (assumptions + citations) — required by Step 8 regardless.
5. Then A (backspace model) and E (pace trimming) as refinements; F cleanup any time.
6. Only then re-run all four styles and treat the tables as pilot findings feeding Step 9 (learned policy).
