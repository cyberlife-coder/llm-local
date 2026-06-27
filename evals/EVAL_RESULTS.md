# Eval results — 4 local models × 50 scenarios

> Companion to [`scenarios.json`](scenarios.json). Machine- and date-specific
> (see [../BENCHMARKS.md](../BENCHMARKS.md) for the test rig: Apple M5 Pro, 64 GB,
> June 2026). Quality is a judged screening, not an absolute leaderboard.

## v2.0 update — budget revision (current)

The body below is the **v1.1** run. The suite was then revised to **v2.0**: output
budgets were raised (design 1500→3200, etc.) to remove truncation, and the three
kept models were re-run and re-judged. Current scores live in
[LEADERBOARD.md](LEADERBOARD.md). What changed:

- **Objective auto-grade jumped** (answers now fit): math+business pass-rate went
  Qwen3.6-A3B 25→62 %, SuperGemma 50→88 %, 80B 62→88 % — confirming v1.1 was
  truncation-limited.
- **Design was a v1.1 artifact.** At v2.0 it's a **~3-way tie (7.0–7.2)**. With room
  to finish, **Qwen3-Coder-Next-80B writes the most polished UIs** (gradient SVG
  fills, numeric-aware table sort, richest product card; won 4/6 design scenarios)
  but still truncated 2/6 even at 3200 tokens; **SuperGemma finished all 6** (most
  reliable); **Qwen3.6-A3B** is clean but plainer.
- **Overall (v2.0):** Qwen3-Coder-Next-80B **8.11** (5/8 wins) > SuperGemma **7.86**
  (3/8) > Qwen3.6-35B-A3B **7.41**. The 80B consolidates the quality lead.
- **Bugs caught by running the code (v2.0 judges executed it):** Qwen3.6-A3B's
  rate-limiter is silently disabled by a misused bare `@wraps`, and its
  ConnectionPool deadlocks (never calls the factory); the 80B's `calc` has a
  unary-minus index bug (`-5+3` → `-5`); SuperGemma answered the RPN task in **R**
  instead of Python. Fast ≠ correct.

## How it was judged

- **4 models**, each run on **all 50 scenarios** (200 generations), `temperature=0`,
  served one at a time through `llm-local` (OpenAI endpoint), no contention.
- **Scoring 0–10 per scenario against each scenario's `rubric`:**
  - **math** and **business** were judged by the author (a Claude model) because
    they have **verifiable answers** (e.g. break-even = 6250 units, RICE order
    B>A>C>D, 100! → 24 zeros) — graded on correct final answer + completeness.
  - **coding, coding_complex, debugging, architecture, design, agentic** were
    judged by **independent per-category LLM judges** reading the raw outputs
    against the rubric, then reviewed and synthesized here.
- **Truncation = penalty.** Outputs cut off by the token budget before delivering
  the answer/code were scored down (this notably affected `design`, see caveat).

## Overall ranking (avg /10 over 8 categories)

| Rank | Model | Score | Cat. wins | Speed | Size |
|---|---|:--:|:--:|--:|--:|
| 🥇 | **qwen3-coder-next-80b** (Qwen3-Coder-Next, 80B/3B MoE) | **7.82** | 4/8 | 21.5 tok/s | 42 GB |
| 🥈 | **supergemma4-26b** (SuperGemma4, 26B/4B MoE) | **7.70** | 4/8 | **62.9 tok/s** | **13 GB** |
| 🥉 | **qwen36-a3b** (Qwen3.6-35B-A3B) | 6.99 | 0/8 | **84.9 tok/s** | 19 GB |
|  | **qwen3-coder-30b** (Qwen3-Coder-30B-A3B) | 5.39 | 0/8 | 71.3 tok/s | 16 GB |

## Category matrix (avg /10)

| Category | qwen3-coder-next-80b | supergemma4-26b | qwen36-a3b | qwen3-coder-30b | 🏆 |
|---|:--:|:--:|:--:|:--:|---|
| coding | **8.86** | 7.43 | 8.43 | 5.71 | next-80b |
| coding_complex | **7.71** | 6.14 | 6.57 | 4.79 | next-80b |
| debugging | **9.8** | 8.8 | 8.4 | 6.4 | next-80b |
| agentic (tool plans) | **8.7** | 8.5 | 7.2 | 3.7 | next-80b |
| architecture | 6.3 | **7.0** | 5.8 | 5.2 | supergemma |
| math | 7.5 | **9.5** | 7.0 | 6.0 | supergemma |
| business | 8.5 | **8.5** | 8.0 | 6.0 | supergemma (tie) |
| design (front-end)¹ | 5.2 | **5.7** | 4.5 | 5.3 | supergemma |

¹ All design scores are low because the per-scenario token budget (1400–1500) **truncated most full-page HTML** — this is a probe-budget artifact, not purely model quality. See caveat.

## What the judges found

- **qwen3-coder-next-80b** — best raw quality, owns everything *code-shaped*:
  cleanest LRU/flatten/diff, only model with a lock-releasing rate limiter,
  flawless debugging (9.8 — added Morris traversal, `quantize` rounding), and the
  best agent plans (verify-first, "warns against blind sed"). **But it is the
  slowest (21.5 tok/s) and largest (42 GB).**
- **supergemma4-26b** — the **best quality/speed ratio**: wins the reasoning-heavy
  half (math, business, architecture) and is essentially tied for the agentic lead
  (sanity-checks before sending, surgical lint loops), while being **3× faster and
  3× smaller** than the 80B. The pragmatic daily driver.
- **qwen36-a3b** — fastest (85 tok/s), a dependable generalist (2nd in coding/debug)
  but wins no category; verbose, so it often truncates long answers.
- **qwen3-coder-30b** — **clear last (5.39), despite its "coder" label and 71 tok/s.**
  Repeated catastrophic failures: degenerates into repetition loops (agentic,
  debug-04 produced no fix), wrong language (**Java** for a Python parser, **R** for
  the RPN task), fatal syntax bugs (`**args`, `is is`), invalid CSS (`rounded:`,
  `shadow:`), and arithmetic/logic errors (RICE, grid-paths). **Recommend dropping it.**

## Recommendation by session type

| Your session is… | Use | Why |
|---|---|---|
| **Agentic coding / debugging, quality-first** (Claude Code, OpenCode) | **qwen3-coder-next-80b** | top code/debug/agent quality — if you accept ~21 tok/s |
| **Daily driver, fast + very good** | **supergemma4-26b** | 2nd overall, **3× faster**, wins reasoning & design; best all-round value |
| **Quick code / fast feedback loops** | **qwen36-a3b** | fastest (85 tok/s), reliable generalist |
| **Math / business / architecture reasoning** | **supergemma4-26b** | clear winner on verifiable reasoning |
| **OpenDesign / front-end** | **supergemma4-26b** (fast) or **qwen3-coder-next-80b** (quality) | both produce valid components; avoid coder-30b (broken CSS) |

**Bottom line:** keep **supergemma4-26b** (best value) and **qwen3-coder-next-80b**
(best quality) as your two pillars, **qwen36-a3b** for speed, and **retire
qwen3-coder-30b**.

## Caveats

- Quality judging is partly subjective (LLM judges + author); scores ±1 are noise.
- The **design** budget (1400–1500 tok) truncated most pages — design ranks reflect
  *who finished within budget* as much as aesthetics; re-run with a larger budget
  for a pure design comparison. (`design-05` was incomplete for **all** models.)
- `temperature=0`, single sample per scenario. Speed = decode tok/s (see BENCHMARKS).

## Appendix — per-scenario scores

Order: **qwen3-coder-next-80b / supergemma4-26b / qwen36-a3b / qwen3-coder-30b**

| id | 80b | gemma | a3b | 30b | note |
|---|:--:|:--:|:--:|:--:|---|
| code-01 | 9 | 6 | 5 | 6 | only 80b releases lock during sleep |
| code-02 | 7 | 1 | **9** | 2 | a3b full correct parser; 30b loop bug; gemma truncated |
| code-03 | 10 | 9 | 9 | 8 | all iterative; 80b's lazy stack cleanest |
| code-04 | 9 | 9 | 9 | 1 | 30b returned **Java** (wrong language) |
| code-05 | 9 | 9 | 9 | 8 | all correct anagram grouping |
| code-06 | 9 | 9 | 9 | 6 | 30b's cancel permanently kills the fn |
| code-07 | 9 | 9 | 9 | 9 | all correct heap merge |
| cplx-01 | 8.5 | 8 | **9** | 5 | 30b O(n) set + misnamed class |
| cplx-02 | 5 | **8** | 3 | 4.5 | a3b never calls factory; 30b syntax error |
| cplx-03 | 8.5 | 6.5 | 8.5 | 3.5 | 30b `**args` fatal bug |
| cplx-04 | 9 | 2 | 9 | 7.5 | gemma truncated; 30b no CRLF |
| cplx-05 | 8.5 | 8 | 5.5 | 2 | 30b garbled diff |
| cplx-06 | 5.5 | 2 | 2 | 5 | gemma wrote **R**; a3b truncated |
| cplx-07 | 9 | 8.5 | 9 | 6 | 30b `is is` syntax error |
| debug-01 | 10 | 10 | 9 | 8 | race→Lock; 30b broken 3rd option |
| debug-02 | 10 | 9 | 9 | 8 | 80b adds Morris traversal |
| debug-03 | 10 | 9 | 8 | 9 | unbounded cache → bounded/TTL |
| debug-04 | 10 | 7 | 8 | 1 | 30b repetition loop, no fix |
| debug-05 | 9 | 9 | 8 | 6 | 30b `.ttzinfo` typo crashes |
| arch-01 | 5 | 5 | 5 | **7** | only 30b completes before truncating |
| arch-02 | 6 | **7** | 5 | 3 | gemma covers ACK/seq guarantees |
| arch-03 | 8 | **9** | 7 | 6 | gemma sharpest monolith-vs-micro reasons |
| arch-04 | 6 | **8** | 6 | 5 | only gemma reaches fail-open mode |
| arch-05 | 6 | **7** | 6 | 3 | gemma adds dark-reads verification |
| arch-06 | 7 | 6 | 6 | 7 | 80b strong comparison table |
| design-01 | 4 | 3 | 3 | 4 | all truncated (glass pricing) |
| design-02 | 4 | **8** | 3 | 8 | gemma & 30b: real SVG sparkline |
| design-03 | 3 | 4 | **8** | 6 | a3b complete gradient hero |
| design-04 | **9** | 8 | 3 | 8 | 80b cleanest JS sort |
| design-05 | 3 | 3 | 2 | 3 | incomplete for all |
| design-06 | 8 | 8 | 8 | 3 | 30b broken CSS + truncated |
| agent-01 | 9 | 9 | 6 | 3 | 30b loops |
| agent-02 | 9 | 8 | 6 | 2 | 80b multi-source + citations |
| agent-03 | 8 | **9** | 6 | 6 | gemma sanity-checks before send |
| agent-04 | 9 | 7 | 8 | 3 | 80b warns vs blind sed |
| agent-05 | 9 | 9 | 8 | 4 | mitigation-first, clear rollback criteria |
| agent-06 | 8 | 9 | 9 | 4 | 30b blind hardcoded edits |
| math-01..07 | 7.5 | **9.5** | 7.0 | 6.0 | gemma only one to land Monty-Hall form, t=11, paths=8; 30b arithmetic error |
| biz-01..06 | 8.5 | **8.5** | 8.0 | 6.0 | numbers verified; 30b wrong "healthy" verdict + RICE error |
