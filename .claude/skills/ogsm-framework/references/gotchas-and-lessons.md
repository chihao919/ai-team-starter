# Gotchas and Lessons — Factory Friction Log

**Document Type:** Phase D Integration — Friction Log
**Created:** 2026-04-11
**Purpose:** 記錄 factory run 實際碰到的雷區與意外，避免下一次 run 重新踩一次同樣的坑。

---

## Critical gotchas (這些下次還會咬你)

### G-001: Gemini 2.5 Flash 會 hang（非 quota 原因）

- **Discovered**: Team 1 Cycle 1，Team 1 Cycle 2 重現，Team 1 Cycle 3 確認為非 topic-dependent
- **Symptom**: `gemini -m gemini-2.5-flash -p "..."` 或 `bash call_with_fallback.sh` 走到 Gemini Flash 時，process 停 60–360 秒無 output 無 error，然後要手動 kill
- **Root cause hypothesis**: Gemini 2.5 Flash 在服務端可能被 silently routed 到某個 capacity-constrained pool（Team 1 iteration-log 稱 "silent routing to gemini-3-flash-preview capacity issue"）；stdout buffer 無 flush；非 quota error 所以不會進到 fallback advance 邏輯
- **Current mitigation**: `call_with_fallback.sh` 只處理 quota error，不會 timeout 或偵測 hang。Team 1 Cycle 3 harness 手動跳過 Gemini Flash primary，wall-clock 從 720s → 360s
- **Proper fix**: INT-001 Option A — 在 `~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh` 加 per-model timeout（例如 90 秒），timeout 就視為 advance 條件進到下一個 model。一次解決所有 caller 的問題
- **Workaround until fixed**: 跳過 Gemini Flash primary，直接用 Gemini Flash Lite 或 WebSearch secondary
- **Who is affected**: 任何 heavy 使用 /ai-fallback 的 agent（Investigator A/B、Fact Checker、Research 類）；Claude-native 主路徑 agent（Writer、Reviewer）基本不受影響

### G-002: `validate_s_to_m_coverage.py` 在 0 agent 狀況 silent PASS

- **Discovered**: Team 1 Cycle 1 surprising findings #1
- **Symptom**: Script exit 0 PASS，即使 document 裡完全沒有可解析的 agent section（0 個 agents, 0 gaps → 嚴格來講 0 gaps 就是 PASS）
- **Why this matters**: Latent false positive。Team 1 baseline mini-research-agent.md 當時所有 4 個 validator 裡 3 個 FAIL，但這一個 silent PASS，差一點讓人誤以為 coverage 沒問題
- **Fix**: 在 `validate_s_to_m_coverage.py` 加一個 assertion — "at least 1 agent must be parsed, else exit 2 with explicit error"
- **Priority**: 高。ogsm-framework-updates.md 必改項目
- **Who is affected**: 任何執行此 validator 的人，尤其新寫 mini-spec 時

### G-003: 單 agent spec format vs 多 agent OGSM format 格式落差

- **Discovered**: Cycle 1 三隊同時碰到
- **Symptom**: Mini-agent spec 用 `## G — Goal` level-2 heading，但所有 validator 預期 `### <emoji> <Agent>` + `**G（...）**` bold sub-label。錯誤訊息 `"no '### ' agent headings found"` 或 `"No agent sections detected"`
- **Fix applied**: Cycle 1 結構 diff 插入 `### <emoji> <Agent>` heading + bold sub-label；P-002 pattern
- **Prevention**: **Factory run 啟動前 pre-flight 跑 validator 一次**，結構 FAIL 直接列為 Cycle 0 work，不浪費 Cycle 1
- **Who is affected**: 任何**新寫**的單 agent spec；既有 HSW-002/006/007 等 OGSM plan 已符合格式，不受影響

### G-004: `check_skill_architecture.py` 要求 document-level section，讓 pointer 模式無法 substitute

- **Discovered**: Team 1 Cycle 2（Pattern P-005 的 negative finding）
- **Symptom**: 原本預期用 `get_skills_for_role.sh` pointer 取代 spec 內嵌的 Skill Invocation Map，briefing char count 應該下降。實際：7331 → 8776（+19.7%），因為 validator 仍要求 `## Skill Invocation Map` document-level section 存在，pointer 只能 append
- **Fix**: ogsm-framework-updates.md — 改 validator 讓 "single pointer line referencing get_skills_for_role.sh" 等同於 full document section
- **Priority**: 中。目前 workaround（保留 full map + pointer line）可用，但跟 pointer pattern 的本意（去重、縮 spec）相左
- **Who is affected**: 所有試圖縮 spec size 的 iteration；若 spec 已經長 spec 不 care，可忽略

### G-005: fallback scenario passing-by-absence（vacuous PASS）

- **Discovered**: Team 2 Cycle 2
- **Symptom**: BDD 的 fallback wiring scenario（W-09 / SCN-R-004）在 happy-path 下 always PASS，因為 writer 根本沒觸發 fallback（upstream 完整，fallback_events=0）。這是 honestly reported 0 但完全不是 behavioral evidence
- **Fix**: INT-002 — Cycle 3 harness 提供 deliberately partial upstream fixture 強制觸發 fallback。Team 3 也用類似設計（Input-B 植入 wrong clause）
- **Prevention**: BDD Verifier 要主動問「這 scenario 在 happy-path 下會不會 always PASS？如果是，Cycle 2 或 3 必須設計 fixture 強制觸發」
- **Priority**: 高。影響 `/ai-fallback`、`/content-scout` 任何 optional skill 的 wire test

### G-006: Fixture wall-clock budget 壓縮掉 side-effect script

- **Discovered**: Team 1 cycles 1/2/3 全部
- **Symptom**: `flag_candidate.sh` 在 Team 1 三個 cycle 中全部 `content_scout_flag_executed_via_script: false` — spec 正確記載要呼叫，但 15 分鐘 cycle budget 沒留給 script 真的跑
- **Root cause**: script 本身需要時間 + `/ai-fallback` 又會 hang（G-001）+ Iterator 要寫 diff → budget 被前面階段吃光
- **Fix**: (a) 把 `flag_candidate.sh` 移到 async post-cycle step；(b) 放寬 budget 到 ≥15 min；(c) iteration metric 追蹤 `script_executed_live` 以顯現 silent skip
- **Priority**: 中。不影響 BDD pass，但 spec 的關鍵 side effect 從未被 live 驗證
- **Tracked as**: INT-003 (proposed by Team 1)

### G-007: Spec-diff=0 但 BDD 還在漲 → 誤判繼續 iterate

- **Discovered**: Team 1 Cycle 3
- **Symptom**: Cycle 2 → Cycle 3 BDD pass rate 跳 +17pp（83% → 100%），直覺會認為 spec 還在改善，應該繼續 iterate。但 spec file byte-identical，改善來自 harness 層（跳過 Gemini primary）
- **Why this matters**: Plateau 規則 "improvement < 5%" 如果直接套 BDD rate，會錯過 spec 已 converge 的事實，導致 gold-plating
- **Fix**: 追蹤 `spec_diff_proposed_this_cycle: bool`。連續兩次 False → plateau（Pattern P-006）
- **Priority**: 高。直接影響 factory 能否乾淨停下

### G-008: Team 3 Cycle 1 validator FAIL 其實是假訊號（pre-existing）

- **Discovered**: Team 3 Cycle 2
- **Symptom**: Team 3 Cycle 1 baseline validator 4/5 FAIL，Team 3 Iterator 沒修結構而是做 behavioral diff；Cycle 2 時意外發現 5/5 PASS（P-015）。如果沒重跑一次 validator 就會誤以為 structural FAIL 還在
- **Fix**: 每 cycle 都重跑 validator baseline，不要假設「上次 FAIL → 這次也 FAIL」
- **Priority**: 低。Team 3 最終結果正確；但紀律原則是「每 cycle 都現場量測」

### G-009: Team 2 isolation rule 禁止改 spec，但 Cycle 1 diff 需 Commander 手動 apply

- **Discovered**: Team 2 Cycle 1
- **Symptom**: Team 2 的 workspace isolation rule 禁止改 `team-2-workspace/` 以外的檔案，包括 `mini-writer-agent.md`。Cycle 1 的 heading diff 只能 "propose" 不能自 apply，必須等 Commander 手動套用後 Cycle 2 才能驗證
- **Fix options**:
  - (a) 給 Team workspace 一個 "apply-to-target-spec" 例外許可
  - (b) Commander 在每個 cycle 間扮演 reviewer + applier
  - (c) 獨立 "Apply phase robot" 在每個 Iterator 之後跑
- **Priority**: 中。真正 scale 時如果每個 diff 都等 Commander 手動 apply，19 agent 會變成 bottleneck

### G-010: Cross-team data sharing 時 upstream 檔案未完成

- **Discovered**: Team 2 Cycle 1 + Cycle 2
- **Symptom**: Team 2 briefing 說要讀 `../team-1-workspace/deliverable-cycle-N.md`，但 Team 1 還沒產出時 Team 2 必須 fallback 到其他 upstream 檔案（例如 HSW-006 investigator notes）
- **Fix**: Team 間 dispatch 要有清楚依賴排序。若平行 dispatch，Iterator 接受 "upstream absent → fall back per briefing rule"
- **Priority**: 中。三隊並行時需明確 fallback 行為

---

## Surprising observations

### S-1: Harness learning 可以產生 spec-free improvement

Team 1 Cycle 3 最大的 lesson：`+17pp BDD 跳升 with 0 spec edits`。意味著有時候 iteration 的 lever 不在 spec 本身，而在執行環境。這是一個強烈訊號 → INT-004（harness 的學習應該內化到 skill）。

### S-2: Behavioral diff 意外修復結構 validator

Team 3 Cycle 2 發現自己 Cycle 1 的純 behavioral diff（改 S rules + Anti-patterns）意外讓 4/5 validator 從 FAIL 變 PASS。解釋不完全清楚，可能是 Anti-pattern section 新增讓 `check_skill_architecture.py` 找到了它要的 pattern。不要依賴這個效應，但也不用強迫自己先修結構。

### S-3: Cycle 3 replay mode 44 秒完成兩組 fixture 驗證

Team 3 Cycle 3 的執行時間是三隊裡最短的（44 秒 vs Team 1 的 360 秒、Team 2 的 420 秒）。因為 replay 不需要新研究，只做 reviewer 的判斷即可。Review 類 agent 的 iteration 可以比 research/writer 快一個量級。

### S-4: Pointer pattern 增加 char count 而非減少

P-005 的 negative finding：預期 `get_skills_for_role.sh` pointer 會縮 spec 20%，實際 +20%。這個「方向對但量相反」的結果，提醒未來 architecture change 要先實測 baseline 再 claim improvement，不能純靠 intuition。

### S-5: 三隊的 convergence path 完全不同

- **Team 1**: Cycle 1 結構修復 → Cycle 2 skill discovery → Cycle 3 harness learning（harness-driven convergence）
- **Team 2**: Cycle 1 單行 heading 修復 → Cycle 2 跨 topic 驗證 → Cycle 3 partial upstream 強制 behavioral evidence（fixture-driven convergence）
- **Team 3**: Cycle 1 behavioral S rule 修復 → Cycle 2 Skill map drift 修復 + escalation path → Cycle 3 replay 驗證（spec-driven convergence）

三條不同的 path 都到達 12/12 BDD PASS。這代表 factory 不需要 "一條對的路徑"，只需要堅守 "smallest diff + rotation + plateau" 三個紀律。

### S-6: `/ai-fallback` hang 是 config bug 不是 model flake

Team 1 在三個不同 input 重現同一個 hang，強烈證明這是 chain config 問題不是 Gemini API 間歇 flake。Config bug 可修，flake 不可修，這個區分值得記錄。

---

## Validator bugs to fix

以下是整理出的 validator 具體改動，依優先序：

| Priority | File | Bug | Fix |
|---|---|---|---|
| **High** | `scripts/validate_s_to_m_coverage.py` | Silent PASS on 0 parseable agents（G-002） | 加 assertion："at least 1 agent must be parsed, else exit 2 with explicit error" |
| **High** | `scripts/call_with_fallback.sh` (ai-fallback skill) | 不處理 hang，只處理 quota（G-001 / INT-001 Option A） | 加 per-model timeout（建議 90s），timeout 等同 advance 條件 |
| **Medium** | `scripts/check_skill_architecture.py` | 不接受 pointer-only Skill Invocation Map（G-004） | 接受 single pointer line 指向 `get_skills_for_role.sh <role>` 作為 full document section 的等效 |
| **Medium** | Iterator robot system prompt | 不追蹤 `spec_diff_proposed_this_cycle`（G-007） | 新增欄位，連續兩個 False 自動 plateau check |
| **Low** | `scripts/validate_ogsm_completeness.py` | 錯誤訊息不夠具體（三隊 Cycle 1 都看到同一個 "No agent sections detected" 要花時間 diagnose） | 錯誤訊息建議修法，例如提示 `### <emoji> <Agent>` heading 與 `**G（...）**` bold sub-label pattern |
| **Low** | Metric JSON schema | `script_executed_live` 欄位缺失（G-006） | 強制 iteration metric 包含所有 spec 引用 script 是否 live 執行 |

---

## Lessons we would embed if we ran this factory again

1. **Pre-flight validator run 是 Cycle 0，不是 Cycle 1 的一部分**。Factory 啟動前 harness 自動跑 validator；結構 FAIL 直接列為 Cycle 0 work，Cycle 1 專心做 behavioral
2. **Dispatch 前修 /ai-fallback 的 hang handling**。否則 research 類 agent 一定重現 G-001，每 cycle 浪費 6+ 分鐘
3. **BDD scenario 要明確區分 passing-by-absence vs passing-by-behavior**。Spec Verifier 的 scenario 設計指引加入此分類
4. **Plateau 規則改成 spec-diff-count 為主、BDD rate 為輔**。兩次 spec-diff=0 直接 stop，除非 Iterator 明確列出未解決 concern
5. **Harness 行為改動要紀錄為 "skill 內化候選"**。任何 harness 學到的 workaround 都寫到 integration-notes.md，Phase D 決定是否 promote 到 skill
6. **Team 間 upstream 依賴要有明確 fallback 順序**。Team N 可以接受 Team N-1 upstream absent → 用 seed dataset

---

## Summary

- **10 個 critical gotchas**（G-001 ~ G-010）
- **6 個 surprising observations**（S-1 ~ S-6）
- **6 個具體 validator bug fix**（3 high, 2 medium, 1 low）
- **6 條 embed-if-we-ran-again lessons**

下一次 factory run 的 pre-flight checklist 可直接抄用這份清單。

---

## Batch 1 scale-up findings (G-011, NEW-02)

### G-011: ICC/NFPA paywall workable via AHJ adoption
**Discovered**: Batch 1 Team B (Investigator B real agent) 2026-04-11
**Symptom**: ICC Digital Codes + NFPA LiNK are paywalled, verbatim quoting blocked
**Workaround**: Use public adoption channels:
- ada.gov (public domain ADA 2010)
- ICC ANSI free preview + city building department adoption notices (e.g., phila.gov)
- Industry commentary (idighardware.com, Lori Greene) quoting verbatim as secondary source
- BHMA free resources for standards
**When to apply**: Investigator B and any code-research agent
**Evidence**: Team B batch-1 cycle-1 iteration-log

### NEW-02: /ai-fallback wrapper vacuous success on Codex trust check
**Discovered**: Batch 1 Team A (Investigator A real agent) 2026-04-11
**Symptom**: Codex exits 0 with "Not inside a trusted directory" on stdout. Wrapper classifies as SUCCESS. Downstream agent receives error text as research data.
**Severity**: CRITICAL — silent data corruption
**Root cause**: wrapper only checked exit code, not stdout error patterns
**Fix applied**: 2026-04-11 — wrapper now detects trust-check error patterns + tries --skip-git-repo-check + general "output looks like error" heuristic
**File**: `~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh`

### G-012: Gemini 2.5 Pro hangs like Flash (G-001 extension)
**Discovered**: Batch 2 Team 2 (Compliance Reviewer) + Team 5 (Source Reviewer)
**Symptom**: `gemini-2.5-pro` hangs 150+ seconds without returning, same pattern as G-001 Flash hang
**Evidence**:
- Compliance Reviewer: Pro hung 150s, wrapper SIGTERM-killed, advanced to flash-lite successfully
- Source Reviewer: Pro hung in `codex,gemini-2.5-pro` chain, exit 3 triggered
**Mitigation**: INT-001 fix (per-model 150s timeout for Pro) works — wrapper catches and advances. Pro is no longer reliable as single-fallback; always have a 3rd tier.
**Recommendation**: Default reviewer chains should be `flash-lite,pro,codex` (not pro first), OR chain depth ≥ 3 including flash-lite

### G-013: Raw models don't autonomously apply spec anti-patterns
**Discovered**: Batch 2 Team 5 (Source Reviewer) 2026-04-11
**Symptom**: Gemini Flash-Lite (and Pro) correctly check mechanical completeness of citations but mark violations as `verified` when they conflict with spec priority-order rules or version-note requirements
**Example**: Source Reviewer sent "legal claim supported by academic paper citation" to raw model. Model returned "verified — has URL and date" but missed that spec requires court documents > academic papers for legal claims. Reviewer had to override.
**Impact**: Reviewer agents cannot blindly trust raw model output — must apply spec anti-patterns as post-processing layer
**Fix pattern**: P-017 (new) — Reviewer-override layer

### G-014: /ai-fallback wrapper misclassifies Pro quota as hang
**Discovered**: Batch 3 Team 3 (Fresh Eyes Reviewer)
**Symptom**: Gemini 2.5 Pro returns quota-exhausted error via stderr retry loop, but wrapper only inspects stdout → wrapper treats as hang and fires 150s timeout unnecessarily
**Fix**: wrapper needs stderr-aware quota detection distinct from hang detection
**Workaround until fixed**: operators can short-circuit Pro if quota status already known

### G-015: Flash-Lite 90s wrapper timeout too tight for long prompts
**Discovered**: Batch 3 Team 3 (Fresh Eyes Reviewer), 1000-word cold-read prompt
**Symptom**: `gemini-2.5-flash-lite` with default OGSM_LITE_TIMEOUT=90s killed while generating valid output on long prompts
**Mitigation**: Use `OGSM_LITE_TIMEOUT=180` for reviewer-class work with long prompts. Direct Flash-Lite call with 180s worked in ~15 seconds.
**Recommendation**: Default to 120-180s for reviewer roles; caller specifies override

### G-020: /ai-fallback full `pro,lite,codex` chain silently exits 3 when Pro quota is exhausted
**Discovered**: Polish Fresh Eyes Reviewer Cycle 2 (2026-04-11, 30 minutes after Batch 3 Cycle 1 discovered G-014)
**Symptom**: With Pro slot quota-exhausted AND `gemini-2.5-pro,gemini-2.5-flash-lite,codex` as chain argument, wrapper exits 3 with ZERO bytes on stdout and ZERO bytes on stderr — no "Attempt log", no "exhausted", no diagnostic. Re-running with `gemini-2.5-flash-lite` as single-element chain succeeds cleanly in ~8 s.
**Why this matters**: Operators cannot tell "chain exhausted" from "wrapper crashed" from the log. Agents relying on the full chain during sustained Pro quota exhaustion silently fail with no signal to fall back. G-014 (misdiagnosis) evolves into G-020 (silent failure) once Pro quota is persistent.
**Mitigation until wrapper is fixed**: For reviewer-archetype roles during known Pro quota exhaustion windows, pass `gemini-2.5-flash-lite` as the sole chain element to bypass the Pro slot entirely. Disclose in deliverable header: `pro_attempted: false (G-018 workaround)`.
**Proper fix**: wrapper must always emit an Attempt-log section to stderr regardless of exit code; wrapper should switch to Lite slot when Pro exits with REST API 429/quota before consuming additional slots.
**Who is affected**: Fresh Eyes Reviewer, Compliance Reviewer, Source Reviewer, any persona-simulation caller during Pro quota exhaustion.
**Precondition**: G-014 active (Pro quota persistent). Once Pro quota resets, G-020 does not reproduce.

### G-021: Raw cold-read model's self-assigned `BLINDSPOT CLASS` label is wrong ~100% of the time cross-topic
**Discovered**: Polish Fresh Eyes Reviewer Cycle 3 (2026-04-11, door-closer cross-topic verification)
**Symptom**: When Fresh Eyes prompt instructs Gemini Flash-Lite to self-label each challenge with `BLINDSPOT CLASS: 1|2|3`, the raw model confidently emits labels — BUT on a draft the model has NOT seen before (cross-topic), all 3 raw class labels were wrong: (a) one challenge misread a normal causal statement as "circular reasoning" (false positive on class 1); (b) one challenge correctly flagged a vendor-shaped frame but misclassified as class 2 (selective citation) instead of class 3 (default stance); (c) one challenge hallucinated a commercial incentive that did not exist in the draft to justify a class 3 label.
**Why this matters**: Without the reviewer-override `blindspot_class_validation` requirement (Polish Cycle 2 spec diff), Fresh Eyes would ship 3 class-labeled challenges that all miss the actual planted blindspots. Raw model class labels are structurally unreliable on unseen topics — same failure pattern as G-013 but specifically for taxonomy self-assignment.
**Mitigation**: Reviewer-override layer MUST re-classify every raw class label independently. Real class 3 requires verifying "author has commercial incentive tied to the claim" — missing citation alone is class 2. Hand-wave is a class-2 variant, not a class-3 pattern.
**Fix pattern**: P-018 extension — Polish Cycle 2 diff adds `blindspot_class_validation`, `vendor_frame_cross_check`, and `hand_wave_detection` sub-bullets to Fresh Eyes Reviewer M section.
**Who is affected**: Fresh Eyes Reviewer specifically; broader applicability to any reviewer that asks a raw model to self-label against a taxonomy (blindspot classes, compliance categories, citation tiers, etc.).

### NEW-03: Fabricated-count passes mechanical count check (post-NEW-02 dominant research failure mode)
**Discovered**: Polish Investigator A Cycle 1 (2026-04-11)
**Symptom**: After NEW-02 (wrapper vacuous success on codex trust-check) is patched, raw flash-lite via /ai-fallback succeeds in ~15s and returns N confident-looking cases to satisfy a `≥ N 案例` hard count. BUT 4 of 5 cases in the polish cycle 1 run were flagged-by-the-model-itself as fabricated: phrases like "hypothetical blog post", "example.gov", "search for X might yield", "discussion at DHI meeting" appeared inside the output. Mechanical case count = 5 (PASS), verifiable first-party URLs = 0 (silent FAIL). Worse than NEW-02 because the output parses cleanly and is not visually broken.
**Root cause**: Raw LLMs under "return exactly N cases" pressure will hallucinate to satisfy the count. Spec anti-patterns did not previously forbid placeholder phrasing, so this failure mode went undetected through smoke test + Batch 1 cycle 1 (where ai-fallback still had NEW-02 masking it).
**Fix pattern**: P-019 — spec anti-pattern must explicitly forbid placeholder phrases AND require ≥1 clickable first-party URL per entry AND require an explicit under-delivery note when count falls short
**Fix applied**: Polish Investigator A Cycle 1 diff — added anti-pattern bullet with forbidden-phrase list and "hard count reached at N verified cases (target M) — reason: ..." escape clause. Polish Cycle 2 replay confirmed +30 to +40 pp BDD improvement.
**Who is affected**: ALL research-archetype agents (Investigator A, Investigator B, Fact Checker, Source Reviewer) using raw LLM via /ai-fallback. Likely dominant failure mode now that NEW-02 is patched.
**Priority**: HIGH — silent data corruption, worse than NEW-02 because the output looks correct

### G-017: Spec text alone is insufficient — Direction Seed must copy rules verbatim
**Discovered**: Polish Investigator A Cycle 2 (2026-04-11)
**Symptom**: Polish Cycle 1 added anti-pattern text to v5.md Investigator A section. Polish Cycle 2 needed a hardened prompt (explicit hard rules copied into the dispatch call) to actually see the behavior change. Agent does not read v5.md at dispatch time unless the harness passes the relevant section.
**Implication**: Spec diffs are necessary but not sufficient. Dispatch Harness Tier 1 Direction Seed template must copy the anti-pattern rules verbatim into the dispatch message.
**Priority**: MEDIUM — documented, requires harness template update for Batch 2+

### G-016: validate_ogsm_completeness.py ANTI_START premature match (FIXED 2026-04-11)
**Discovered**: Batch 2 Team 3 (Copy Editor) 2026-04-11 — Copy Editor's M was truncated to 2 bullets when it had 5 because M contained "Anti-pattern #1" in a bullet that matched the loose ANTI_START regex.
**Root cause**: Regex matched "Anti-pattern" anywhere on any line, including inside list bullets
**Fix**: Anchor regex to line start + require `**` bold marker, so only actual `**Anti-patterns` headings trigger section transition. Also added `re.MULTILINE` flag to `check_antipatterns_block` and `extract_subsections` so `^` anchors work correctly on multi-line strings. The `NEW_SUBSECTION` fallback boundary check was also tightened from `r"Anti-pattern"` to `r"\*\*Anti-patterns"`.
**Lesson**: markdown section parsers should always anchor heading patterns to line start + structural markers (bold, hash)
**Status**: FIXED in validate_ogsm_completeness.py 2026-04-11

### G-022: Polish run scope creep temptation (writer archetype polish)
**Discovered**: Polish Writer A 2-cycle convergence run (2026-04-11)
**Symptom**: Polish runs have narrow scope ("2 cycles, single agent, 30 min timeout, no subagent dispatch"). During Cycle 2 iteration, the Iterator has visibility into other spec weaknesses adjacent to the targeted agent (Writer A's S section phrasing, Anti-patterns section coverage, Engagement Designer interaction checkpoint limits, etc.). The temptation is to pull fixes for adjacent issues into the same diff.
**Why this is bad**: A polish run is a **convergence** run, not an expansion run. Scope creep breaks the smallest-possible-diff discipline (P-008) and muddles the cross-fixture consistency signal — you cannot tell which behavior change came from which bullet.
**Mitigation**: Every polish cycle ends with an explicit "did any non-Writer-A issues surface?" log line. If yes, file each one as a Wave 1 follow-up ticket, do NOT pull into the current diff.
**Evidence**: Polish Writer A Cycle 2 identified (but deferred): (a) lack of a standing `/ai-fallback` entry on writer-a skill map, (b) Engagement Designer checkpoint count ≤ 3 is never validated in Writer A's M section. Both noted, neither pulled into the polish diff.
**Priority**: Medium — not catastrophic if missed, but breaks signal integrity for plateau detection under P-006
**Who is affected**: Any polish run on a mature agent that touches a well-factored spec; especially dangerous on writer/reviewer archetypes where adjacent agents share M section patterns

### G-019: Orchestrator rule scatter — works-if-thoughtful vs works-because-of-rules
**Discovered**: Polish Commander Cycle 2 (2026-04-11)
**Symptom**: Commander's v5 spec (post-Batch 4 Cycle 1, pre-SPEC-DIFF-CMD-002) passed all 5 hardest-task scenarios in Polish Cycle 2 — but 4 of 5 required Commander to **synthesize rules** from signals scattered across different sections:
- Conflict resolution logic lived in line 155 (external-priority only) but the producer-vs-reviewer case required cross-referencing the gate-question pattern from lines 159-160
- Escalation rubric lived nowhere — Commander had to assemble it from Principle 7 references + scaling-playbook preflight rules + gotchas-library pointer
- Pilot-FAIL reaction lived as prose in Dispatch Template section (lines 1180-1188), not as a checklist in Commander's own S block
- Commander's own LLM discipline was only implied (subagents must use wrapper → Commander is an agent → therefore Commander must too)

**Why this matters**: Each gap was individually answerable by a thoughtful operator reading the whole doc. Collectively they make the spec **fragile under time pressure** — a rushed Commander reads their own section first, skips cross-references, and invents weaker versions of the rules. The spec silently downgrades from "orchestrator follows rules" to "orchestrator has good instincts".

**Fix applied**: SPEC-DIFF-CMD-002 moved 4 runtime decision rules INLINE into Commander's own S block:
1. Three-layer conflict rule (a/b/c) as a single bullet (was: 1 bullet for CASE-A only, nothing for CASE-B/C)
2. 3-question escalation rubric as a single bullet (was: nowhere in Commander's section)
3. "Commander's own LLM calls go through wrapper too" as a single bullet (was: implied from Principle 7)
4. Pilot Dispatch bullet expanded with 5/5 fan-out checklist + 3-step FAIL reaction (was: prose in far-away Dispatch Template section)

**Verification**: Polish Cycle 3 ran the same 5 scenario categories on a 3rd distinct substrate (HSW-009) and got 5/5 pass with **zero synthesis** — each scenario directly mapped to a bullet Commander reads and applies.

**Lesson for future orchestrators**: When writing any orchestration-archetype agent spec, audit each S block bullet against the question "if this agent has to make a decision mid-run, does it need to cross-reference another section?" If yes, inline the rule. Scatter = fragile under time pressure. See P-022 for the structural pattern and P-024 for the specific case of wrapper discipline applying to the orchestrator's own LLM calls.

**Priority**: High — this failure mode silently degrades ALL orchestration specs, not just Commander. A君 variants, Task Mode coordinators, multi-agent wrappers all risk this.
**Who is affected**: Any orchestration archetype. Specifically: HSW fleet Commanders for HSW-00X courses, the A君 root agent (watersonusa.ai project root), and any future multi-agent coordinator
