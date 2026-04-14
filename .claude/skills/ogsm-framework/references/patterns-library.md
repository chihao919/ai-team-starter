# Patterns Library — Factory Knowledge Base

**Document Type:** Phase D Integration — Pattern Reference
**Created:** 2026-04-11
**Purpose:** 可查詢的 agent optimization pattern 中央資料庫，供未來 Iteration Team 開始 cycle 前查詢已知 pattern。

這是 mini-agent factory run（Team 1/2/3 × 3 cycles）中實際觀察到的 pattern 結構化索引。每個 pattern 都有明確 evidence（哪隊、哪 cycle、什麼 metric 變動），可以追溯到對應的 iteration-log.md / diff patch / STOP.txt。

---

## Query usage

未來 Iterator robot 碰到 FAIL 時，先到這裡查詢對應 pattern：

```bash
# 以後可由 ogsm-framework skill 提供：
bash ~/.claude/skills/ogsm-framework/scripts/get_patterns_for_failure.sh <failure-type>
```

Failure type 範例：
- `structural-validator-fail` → P-002
- `skill-drift` → P-003
- `fallback-vacuous-pass` → P-004
- `spec-bloat` → P-005
- `plateau-detection` → P-006
- `ai-fallback-hang` → P-011
- `content-scout-budget` → P-012

---

## Pattern Index

| ID | Name | Category | When to apply | Evidence count |
|---|---|---|---|---|
| P-001 | Skill discovery via central map | Architecture | 當 agent spec 在 Tier 1 內嵌完整 skill 指令 | 3 teams |
| P-002 | Structural header injection for single-agent spec | Format | 當 validator 報 `no '### ' agent headings found` | 3 teams |
| P-003 | Skill map drift detection via BDD scenario | BDD design | 任何引用 `/ai-fallback` 或外部 skill 的 agent | 3 teams |
| P-004 | Forced fallback via partial upstream fixture | Fixture design | 當 BDD 的 fallback scenario 是 passing-by-absence | 2 teams |
| P-005 | Pointer pattern is additive not substitutive | Architecture (negative finding) | 預期透過 pointer 縮 spec size 時 | 1 team (Team 1) |
| P-006 | Spec-diff-count as plateau signal | Process / plateau | 任何 iteration run 的 plateau 決策 | 3 teams |
| P-007 | Topic rotation across 3 structurally-different inputs | Test design | 任何 iteration run | 3 teams |
| P-008 | Smallest-possible-diff discipline | Iterator process | 每次 Iterator 提 diff | 3 teams |
| P-009 | Per-cycle BDD versioning（bdd-scenarios-cycle-N.md） | Process | 每次新增 scenario 時 | 2 teams |
| P-010 | Harness layer learning（skip known-bad model） | Harness process | 當 model 層有重複 friction | 2 teams |
| P-011 | Gemini 2.5 Flash hang workaround | Production workaround | 任何用 /ai-fallback 且 Gemini Flash 是 primary 的 agent | 1 team (Team 1) |
| P-012 | Content scout async flag_candidate pattern | Harness scheduling | Research agent 需要 flag candidate topic 時 | 1 team (Team 1) |
| P-013 | Cycle 3 replay mode（不 rotate 新 input） | Convergence test | Cycle 2 的 diff 需要 cross-fixture 驗證時 | 1 team (Team 3) |
| P-014 | Granular-vs-consolidated flag strategy | Reviewer spec design | Reviewer 類 agent 的 BDD 設計 | 1 team (Team 3) |
| P-015 | Behavioral diff accidentally unblocks validator | Positive accident | 觀察到即可，不主動複製 | 1 team (Team 3) |

---

## Pattern Details

### P-001: Skill discovery via central map

**Category**: Architecture / Tier 1 reduction
**When to apply**: 當 agent 的 Tier 1 summary 或 S section 內嵌完整 skill 指令字串，造成多 agent drift 與維護成本。
**Solution**: 用單行 pointer 取代內嵌指令，由 skill 側中央檔案維護：

```bash
bash ~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh <role-name>
```

**Evidence**:
- Team 1 Cycle 2: 新增 `get_skills_for_role.sh mini-research-agent` 呼叫，exit 0，返回 2 個 skill entry；BDD S11/S12 PASS
- Team 2 Cycle 2: `get_skills_for_role.sh mini-writer-agent` 返回 role-specific guidance；W-11 PASS；Cycle 3 真的幫 writer 找到 /ai-fallback path 並觸發 2 次 real fallback
- Team 3 Cycle 2: 發現 SCN-R-012 drift（central map 有 /ai-fallback，spec 寫 "None"），Cycle 2 diff 同步後 Cycle 3 PASS

**Metric impact**: 維護點從 N（每 agent 一份）降到 1（central map）。注意：並不直接縮 spec size，見 P-005。
**Scaling recommendation**: 所有新 agent 預設使用此模式。BDD 預設內建「skill discovery before action」與「no drift between map and execution」兩個 scenario（見 P-003）。

---

### P-002: Structural header injection for single-agent spec

**Category**: Format / validator compatibility
**When to apply**: 當 Phase A validator 報 `"no '### ' agent headings found"` 或 `"No agent sections detected"`。
**Solution**: 在 Purpose block 之後插入 `### <emoji> <Agent Name>` heading，並把 `## G / ## S / ## M` 轉成 bold sub-label `**G（...）** / **S（...）** / **M（...）**`。視情況 append 三個 document-level section：`## Skill Invocation Map` / `## Model Invocation Map` / `## Brief Layering`。

**Evidence**:
- Team 1 Cycle 1: 96-line patch，4 validator 從 FAIL 變 PASS
- Team 2 Cycle 1: 單行 heading 插入，Cycle 2 時 5/5 validator PASS
- Team 3 Cycle 2: 意外發現自己的 behavioral diff 順便修了結構（見 P-015）

**Metric impact**: validator 從 0/4 或 0/5 PASS 直接 step function 到 4/4 或 5/5 PASS。
**Scaling recommendation**: Pre-flight 階段先跑 validator；如果 baseline 全 FAIL 而且訊息都是 heading-related，Cycle 1 直接做結構 fix，不要做 behavioral diff。結構 FAIL 不 fix 的話 behavioral 改動無法被 validator 驗證，浪費 cycle。

---

### P-003: Skill map drift detection via BDD scenario

**Category**: BDD design
**When to apply**: 任何引用 `/ai-fallback`、`/content-scout`、`/ogsm-framework` 等外部 skill 的 agent。
**Solution**: 新增兩個低成本高訊號 BDD scenario：
1. "Given the spec references skill X, When the harness runs `get_skills_for_role.sh <role>`, Then the script exits 0 and returns a non-empty section"
2. "Given the script returns skill commands, When the agent deliverable logs skill invocations, Then the invoked commands are a subset of the returned commands"

**Evidence**:
- Team 1 S11 + S12（Cycle 2 新增）
- Team 2 W-11（Cycle 2 新增）
- Team 3 SCN-R-011 + SCN-R-012（Cycle 2 新增，SCN-R-012 實際抓到 drift）

**Metric impact**: 成本最低（一個 bash call 加一個 set 比對），訊號最強（能抓到 spec/central drift、未執行 skill discovery、hardcoded command string 等三種 class 的 bug）。Team 1 Cycle 2 iteration-log 直接稱這兩個為 "cheapest, highest-confidence BDD scenarios"。
**Scaling recommendation**: 加入 Spec Verifier robot 的 BDD template 預設條目。所有 factory cycle 從 Cycle 1 就內建。

---

### P-004: Forced fallback via partial upstream fixture

**Category**: Fixture design
**When to apply**: 當 BDD 的 fallback/escalation scenario 會因為 happy-path upstream 完整而變成 passing-by-absence（vacuous PASS）。
**Solution**: Harness 自己產一個 deliberately broken upstream fixture：
- Writer archetype: 保留大多數實質內容但故意抽掉關鍵 citation，讓 writer 必須 halt 或 fallback
- Reviewer archetype: 植入 plausible but wrong 的 clause 編號（NFPA 80 §6.1.5 when real is §6.1.4）
- Research agent: 不需要（/ai-fallback 本來就是 research 主路徑）

**Evidence**:
- Team 2 Cycle 3: `upstream-partial-cycle-3.md` 帶 3 個 bare section 編號 + 零 case + 零 URL + 明確 gap list → writer 真的觸發 `/ai-fallback` 2 次
- Team 3 Cycle 2: Input-B 植入 §6.1.5 wrong section → reviewer 無法靠 native 抓到 → Cycle 2 diff 加 escalation path → Cycle 3 replay 觸發 escalation
- INT-002 記錄了這個 fixture 設計決策

**Metric impact**: W-09 / SCN-R fallback scenario 從 "vacuously PASS" 轉為 "behaviorally PASS with 2 fallback_events logged"。
**Scaling recommendation**: 在 ogsm-framework 加入 `fixtures/partial-upstream-template.md` 與 `fixtures/planted-wrong-clause-template.md` 作為 Dispatch Harness 的標準 stress-test。

---

### P-005: Pointer pattern is additive not substitutive（negative finding）

**Category**: Architecture (negative finding)
**When to apply**: 若預期透過 pointer 模式（P-001）縮減 spec file 字數。
**Solution**: **不要抱持 size reduction 期待**。要真的縮 size，需要同時修改 `check_skill_architecture.py` 以接受 "single pointer line 等同於 full Skill Invocation Map section"。在 validator 改動前，pointer 只能 append 到既有 document-level section 旁邊。

**Evidence**:
- Team 1 Cycle 2 log: briefing char count 7331 → 8776（+19.7%），因為 document-level Skill Invocation Map 必須保留以過 validator
- Team 2 / Team 3 沒遇到這個 issue——他們都 additively 加入 Skill Invocation Map section

**Metric impact**: 預期 -20%、實際 +20%。負向訊號，教訓意義大於可用性。
**Scaling recommendation**: 在 ogsm-framework-updates.md 登記 `"allow pointer-only Skill Invocation Map"` 作為 validator upgrade 項目。在此之前所有 agent 都要同時保留 inline map + pointer line。

---

### P-006: Spec-diff-count as plateau signal

**Category**: Process / plateau detection
**When to apply**: 任何 iteration run 的 plateau 決策。
**Solution**: 追蹤 `spec_diff_proposed_this_cycle: bool` 欄位。連續兩個 False → 自動 plateau check（優先順序高於 BDD pass rate 的 <5% 規則）。除非 Iterator 明確列出未解決的 behavioral concern（如 Team 2 Cycle 2 的 W-09 vacuous PASS），否則 spec-diff=0 兩次 = stop。

**Evidence**:
- Team 1: BDD 70% → 83% → 100%，但 Cycles 2/3 spec-diff=0；STOP.txt 明確討論此區分
- Team 2: Cycles 2/3 spec-diff=0（Cycle 3 只改 fixture 與 harness），converge
- Team 3: Cycle 3 REPLAY mode，spec 不變，converge

**Metric impact**: 更早偵測 plateau；避免 gold-plating。Team 1 Cycle 3 BDD jump +17pp 其實是 harness 層改善，不該誤判為 spec 還在進步。
**Scaling recommendation**: Iterator robot scratchpad 強制新增 `spec_diff_proposed_this_cycle` 欄位；連續兩次 False 觸發 plateau assertion。若 Iterator 要跳過 plateau 必須明確寫出未解決的 outstanding concern。

---

### P-007: Topic rotation across 3 structurally-different inputs

**Category**: Test design
**When to apply**: 任何 iteration run（3-cycle baseline）。
**Solution**: 準備 3 個 **substrate 差異大** 的 input（不是同 topic 的變種），每 cycle rotate 一次：
- Team 1: multifamily self-closers → fire door spring hinges → ADA opening force（code types 跨越）
- Team 2: Twin Parks fire case → NFPA 80 mechanism → ADA section（narrative vs mechanism vs compliance）
- Team 3: promo+pedagogical → wrong clause + brand bias → replay（不同 failure class）

**Evidence**: 三隊都採用 3-input rotation；三隊都在 Cycle 2 或 Cycle 3 的 iteration-log 明確驗證 topic-agnosticism，無 substrate leakage。
**Metric impact**: 提供 generalization 行為證據（而非只有 replay-on-same-input）。Team 3 觀察到 4 FP → 1 FP 是 cross-input 而非 replay 的效果。
**Scaling recommendation**: Factory 啟動前 harness 必須準備好 3 個 input，且三者應刻意選擇不同 sub-domain。Batch dispatch 時 harness 預備 input pool 是 pre-flight checklist 項目。

---

### P-008: Smallest-possible-diff discipline

**Category**: Iterator process
**When to apply**: 每次 Iterator 提 diff。
**Solution**: Iterator 每 cycle 被迫回答兩個問題：
1. 這個 diff 的 root cause 是什麼？
2. 有沒有其他 FAIL 被同一 root cause 解決？

如果發現「順便修其他東西」，拆成下個 cycle。

**Evidence**:
- Team 1 Cycle 1: 96 lines 全 additive（插入 heading、sub-label、3 個 document section）
- Team 2 Cycle 1: 單行 `### Mini-Writer Agent` 插入
- Team 3 Cycle 1: 3 個 BDD FAIL 共享一個 root cause（S rule 未明確），用一次 localized edit 處理並且明確拒絕同時修結構 issue（"Structural fix belongs in a separate cycle"）

**Metric impact**: 零 regression、容易 review、容易 rollback。三隊 regression check 一致 "all previously-passing scenarios remain PASS"。
**Scaling recommendation**: 建入 Iterator robot 的 system prompt。每 cycle strict 限制。

---

### P-009: Per-cycle BDD versioning

**Category**: Process / auditability
**When to apply**: 每次新增 scenario 或修改 BDD 時。
**Solution**: 為每 cycle 開獨立 BDD 檔案 `bdd-scenarios-cycle-N.md`，即使內容沒變也寫一份 header `"Changes vs cycle N-1: NONE"`。

**Evidence**:
- Team 2: `bdd-scenarios.md` (C1, 10) → `bdd-scenarios-cycle-2.md` (C2, 12) → `bdd-scenarios-cycle-3.md` (C3, 12, "Changes vs cycle 2: NONE")
- Team 3: 同樣模式
- Team 1 只用 iteration-log 紀錄，沒有獨立檔案化（較不易 reproduce）

**Metric impact**: "scenario count 從 10 到 12" 的 evidence trail 可稽核。未來 debug 更容易追溯。
**Scaling recommendation**: 強制 Spec Verifier 每 cycle 產獨立檔案。

---

### P-010: Harness layer learning（skip known-bad model）

**Category**: Harness process
**When to apply**: Model 層有重複 friction（如 P-011 的 Gemini Flash hang）。
**Solution**: 給 Dispatch Harness 明確 license 進行非 spec 的行為優化，包括：
- 跳過已知有 bug 的 primary model
- 使用 replay mode（P-013）
- 設計 stress-test fixture（P-004）

這些改動自動記錄到 integration-notes.md 作為 skill 內化候選。

**Evidence**:
- Team 1 Cycle 3: harness 主動跳過 Gemini Flash primary，wall-clock 720s → 360s（-50%），零 spec 改動
- Team 3 Cycle 3: replay mode 44s 完成兩組 fixture 驗證
- Team 2 沒用這個模式（Cycle 3 是新 input）

**Metric impact**: Cycle 3 wall-clock 顯著下降；維持 convergence 訊號。
**Scaling recommendation**: Harness 的行為改動要記到 integration-notes.md，並在 Phase D 決定是否內化到 skill（例如 INT-004：Team 1 harness skip 邏輯應搬進 `call_with_fallback.sh`）。

---

### P-011: Gemini 2.5 Flash hang workaround

**Category**: Production workaround / ai-fallback bug
**When to apply**: 任何用 `/ai-fallback` 且 Gemini Flash 是 primary 的 agent，especially research agents。
**Solution**: 短期：harness 層跳過 Gemini Flash primary（Team 1 Cycle 3 做法）。長期：修 `call_with_fallback.sh` 加 per-model timeout（INT-001 Option A，推薦）。
**Evidence**:
- Team 1 Cycle 1: Input-A Gemini Flash hang 360+ 秒，無 output 無 error
- Team 1 Cycle 2: Input-B 同 pattern 重現（90s 後 kill）
- Team 1 Cycle 3: harness 主動避開，360s 完成 cycle
- Team 2/3 沒重現——因為 writer/reviewer 都是 Claude-native 主路徑

**Metric impact**: 未修會造成 wall-clock 翻倍；harness workaround 可救回 -50% wall-clock。
**Scaling recommendation**: factory run **啟動前** 必須先修 INT-001（Option A 內化 timeout），否則所有使用 `/ai-fallback` 的 research 類 agent 會重現此 pattern。參考 gotchas-and-lessons.md G-001。

---

### P-012: Content scout async flag_candidate pattern

**Category**: Harness scheduling
**When to apply**: Research agent 需要 flag candidate topic 的 agent，有 side-effect script 要跑。
**Solution**: 把 `flag_candidate.sh` 移到 async post-cycle step 或放寬 wall-clock budget 到 ≥15 分鐘，否則 script 會被 cycle 時間擠掉而從未真實執行。

**Evidence**: Team 1 cycles 1/2/3 的 metrics JSON 都記 `content_scout_flag_executed_via_script: false`；STOP.txt 列為 INT-003 候選。
**Metric impact**: 不影響 BDD pass，但 spec 中的「呼叫 content scout」就從未被真實驗證。
**Scaling recommendation**: 任何 optional side-effect script 都應：(a) 提供 async mode、(b) budget ≥15 min、(c) 在 iteration metric 追蹤 `script_executed_live` 以避免 silent skip。

---

### P-013: Cycle 3 replay mode

**Category**: Convergence test / wall-clock optimization
**When to apply**: 當 Cycle 2 的 diff 需要 cross-fixture 驗證，且不需要新 substrate 測試時。
**Solution**: Cycle 3 不 rotate 新 input，而是 REPLAY 先前 cycle 的 fixture，驗證 diff 真的解決了原 failure mode 且不破壞既有行為。

**Evidence**: Team 3 Cycle 3: replay Input-A（C1 fixture）+ Input-B（C2 fixture），44s 完成，catch rate 從 50% → 100%，FP 從 5 → 0。Team 1/2 沒用 replay，但 Team 1 STOP.txt 稱讚 Team 3 的速度。
**Metric impact**: Cycle 3 wall-clock 顯著降低；cross-fixture 驗證避免 over-fit 單一 input。
**Scaling recommendation**: Review / compliance 類 agent 優先考慮此模式；Research / Writer 類仍建議新 input（避免 over-fit）。

---

### P-014: Granular-vs-consolidated flag strategy

**Category**: Reviewer spec design
**When to apply**: Reviewer 類 agent 的 BDD 設計。
**Solution**: BDD 明確指定「granular 或 consolidated」預期。Granular 有助於機械式修復；consolidated 有助於 reviewer-to-writer feedback loop。避免在不同 cycle 之間 oscillate。

**Evidence**: Team 3 Cycle 1 把單一 promo issue 拆成 4 個 granular AIA HSW flag；Cycle 3 replay 同 fixture 時改成 single consolidated flag。兩者都正確但預期不同。
**Scaling recommendation**: Content Director / Compliance Reviewer / Copy Editor / Fact Checker / Source Reviewer 這類 agent 的 BDD 預設寫清楚期望 flag granularity。

---

### P-015: Behavioral diff accidentally unblocks validator

**Category**: Positive accident（觀察即可，不主動複製）
**When to apply**: N/A（非可執行 pattern，純紀錄）
**Solution**: 無——只是記錄這個可能性存在。
**Evidence**: Team 3 Cycle 2 發現 Cycle 1 的純 behavioral diff（改 S rules + Anti-patterns）意外讓 4/5 validator FAIL 變成 5/5 PASS。`"Cycle 1 behavioral diff somehow aligned with structural expectations"`。
**Metric impact**: Team 3 跳過了結構 diff 仍然到達 5/5 validator PASS；但這是巧合。
**Scaling recommendation**: 不要依賴此 pattern。Cycle 1 還是應該做結構 pre-flight。但如果 Cycle 1 跳過結構修而 Cycle 2 validator 意外 pass，也是合法結果。

---

## Summary

16 個 pattern 分為三個信心層：

- **3/3 universal** (5 patterns): P-001, P-002, P-003（可算 P-001 的 BDD 配套）, P-006, P-007, P-008
- **2/3 likely** (3 patterns): P-004, P-009, P-010
- **1/3 archetype-specific** (5 patterns): P-005, P-011, P-012, P-013, P-014
- **Positive accident** (1): P-015
- **Batch 1 new** (2 patterns): P-015 (see above), P-016

未來 scale 到 19-agent 時：
- 所有 universal pattern 在 Cycle 0（pre-flight）就套用，不等 Cycle 1 發現 FAIL
- Likely universal 放在 Cycle 1 Iterator 的「優先檢查清單」
- Archetype-specific 只在遇到對應 agent 類型時查詢

對 ogsm-framework skill 的具體 bake-in 建議見 `ogsm-framework-updates.md`。

---

## Batch 1 scale-up patterns (P-015, P-016)

### P-015: WebSearch as tool-level escape hatch for research archetype
**Category**: Research resilience
**When to apply**: When `/ai-fallback` exits 3 (all models exhausted) OR silently fails (NEW-02)
**Solution**: Research-archetype subagents should treat their WebSearch tool as the final fallback after /ai-fallback. Brief: "If ai-fallback exit 3, OR output looks like error, use WebSearch with same query, extract sources manually from results."
**Evidence**:
- Smoke test (Investigator A): manual pivot to WebSearch when codex failed
- Batch 1 Team B (Investigator B): 5/5 /ai-fallback failures, WebSearch saved all 5 queries
- Batch 1 Team A (Investigator A): WebSearch pivot when NEW-02 vacuous success detected
**Metric impact**: Without WebSearch fallback, 3+ real-agent runs would have produced silent garbage or empty deliverables
**Scaling recommendation**: Include "If exit 3 or vacuous success, use WebSearch" in every research-archetype agent's Direction Seed briefing

---

### P-016: Paywall workaround via AHJ adoption channels
**Category**: Code research / citation
**When to apply**: When primary code source (ICC Digital Codes, NFPA LiNK) is paywalled
**Solution**: Use public adoption channels — ada.gov (public domain), city building department adoption notices, industry commentary citing verbatim, BHMA free standards
**Evidence**: Team B Batch 1 Cycle 1 — successfully cited 4 code sources despite no ICC/NFPA paid access
**Scaling recommendation**: Build into Investigator B's Tier 1 briefing as default research path

### P-014: Pre-dispatch granular flag format pinning in BDD
**Category**: Reviewer BDD quality
**When to apply**: Writing BDD scenarios for any reviewer-archetype agent (Content Director, Compliance Reviewer, Copy Editor, Fact Checker, Source Reviewer)
**Solution**: Pin the exact flag format (how the reviewer outputs a flag — category, severity, location, rationale) in the BDD scenario BEFORE dispatch, so the iterator can verify format compliance, not just catch-rate
**Evidence**: Batch 2 Team 3 (Copy Editor) — CE-13 vacuous-PASS guard prevented a "PASS-by-silence" outcome
**Scaling recommendation**: apply to all 5 reviewer agents' BDD suites before Wave 1 real production

### P-017: Reviewer-override post-processing layer
**Category**: Review resilience
**When to apply**: Any reviewer agent using `/ai-fallback` to validate facts, sources, or compliance
**Solution**: Do NOT trust raw model's verified/approved marks as final. Reviewer agent must apply spec anti-patterns as a post-processing layer on top of raw model output. Treat raw model as "mechanical completeness check", not "spec compliance check".
**Evidence**: Batch 2 Team 5 (Source Reviewer) — raw model marked 2 of 4 planted issues as verified; reviewer overrode via spec anti-pattern rules
**Scaling recommendation**: add to every reviewer's S section as explicit post-processing bullet

### P-018: Fresh Eyes Reviewer-override post-processing (extends P-017)
**Category**: Review resilience
**When to apply**: External cold-read reviewers using raw model (Gemini Pro/Flash-Lite) for persona simulation
**Solution**: Beyond the P-017 general override pattern, Fresh Eyes override must specifically score each challenge on 3 axes: (a) planted issue coverage, (b) outside voice discipline, (c) actionable fix language. Reject raw output that returns well-formed challenges without matching blindspot class (vacuous-PASS risk).

**Polish Cycle 2/3 extension (2026-04-11)**: Initial P-018 passed BDD on the same-topic replay but BROKE DOWN on cross-topic. Raw model's self-assigned `BLINDSPOT CLASS` labels were 3/3 wrong on a door-closer draft after being 3/3 "correct-looking" on a hinge draft. Three mandatory sub-layers added to the spec's M-section reviewer-override bullet:

1. **blindspot_class_validation** — reviewer must independently re-classify every raw class label. Real class 3 requires verifying "author has commercial incentive tied to the claim"; missing citation alone is class 2. Override layer publishes `raw_class_reassignment_count` metric.
2. **vendor_frame_cross_check** — reviewer must cross-reference any section that names a manufacturer against any section that elevates that manufacturer's product category as "most important," "fastest-growing," "industry standard," etc. Raw model does NOT make this connection autonomously.
3. **hand_wave_detection** — reviewer must scan for "X may vary," "X is not consistent," "depends on your relationship" language that raises a problem without a next step. Raw model treats these as neutral context. Override layer must flag as class-2 variant and supply a concrete resolution path (contact whom, consult which artifact).

**Evidence**:
- Batch 3 Team 3 Cycle 1 (hinge topic) — override caught 3 gaps raw Flash-Lite missed
- Polish Cycle 2 (hinge topic, explicit class labels in prompt) — raw model catches circular clue but still miscategorizes "missing source" as class 3; vendor frame still only surfaces via override
- Polish Cycle 3 (door-closer cross-topic) — raw class labels were 3/3 wrong; 1 planted caught at wrong class, 2 planted missed entirely; override REPLACED all 3 raw challenges to land 3/3 planted coverage

**Scaling recommendation**: Apply the 3-sub-layer expansion to ANY reviewer that asks a raw model to self-label against a taxonomy (Project Architect Advisor, Sales Rep Advisor, Compliance Reviewer all have same structural risk). Reviewer-override layer is what makes the spec survive topic rotation.

---

### P-019: Forbid-placeholder anti-pattern for hard-count research (post-NEW-02)
**Category**: Research resilience / anti-hallucination
**When to apply**: Any research-archetype agent with a hard numeric deliverable count (≥ N cases, ≥ N citations) using raw LLM via /ai-fallback. Becomes dominant failure mode AFTER NEW-02 (vacuous success) is patched.
**Symptom**: Raw model generates N confident-looking entries with placeholder phrases ("hypothetical blog post", "example.gov", "search for X might yield", "discussion at DHI meeting") to satisfy the count, passing mechanical count check silently.
**Solution**: Spec Anti-patterns must explicitly forbid the placeholder phrasing AND require at least 1 clickable first-party URL or document ID per entry, AND require explicit under-delivery note format ("hard count reached at N verified cases (target M) — reason: ...") when the count falls short. Honest under-delivery beats fabricated count.
**Evidence**:
- Polish Investigator A Cycle 1 (2026-04-11) — raw flash-lite returned 5 hallucinated spring-hinge cases with "hypothetical" sources; zero verifiable URLs; mechanical count check PASS, verification check FAIL
- Polish Investigator A Cycle 2 (replay with hardened Direction Seed + spec diff) — agent returned 4 cases with first-party URL attempts and explicit "HARD COUNT REACHED AT 4 VERIFIED CASES (TARGET 5)" note; +30 to +40 pp BDD improvement
**Scaling recommendation**: apply to Investigator A, Investigator B, Fact Checker, Source Reviewer — any agent with a numeric case/citation minimum. Add the anti-pattern bullet at spec-diff time, AND copy the hard rules into the Dispatch Harness Tier 1 Direction Seed template (spec text alone is insufficient — harness must pass the rules explicitly).

---

### P-020: Pattern execution without literal phrase tag
**Category**: Research / positive observation
**When to apply**: Observation — don't force magic phrases in spec text if the described substrate list is specific enough.
**Symptom**: Spec describes a fallback pattern with a literal tag ("per P-016") and a list of acceptable substrate types. Agent self-aligns to the substrate types (idighardware, BHMA, AHJ adoption) without speaking the literal tag.
**Solution**: Accept pattern-execution-without-literal-phrase as a soft PASS. If downstream gate review needs machine-readable tags, add a Quality Auditor post-processing check rather than forcing the agent to emit the literal phrase.
**Evidence**: Polish Investigator A Cycle 2 — agent pivoted from fabricated DHI references to idighardware.com Allegion bulletin (on the P-016 chain) without using the phrase "per P-016"
**Scaling recommendation**: Spec tags are for human readers / gate reviewers; agent behavior tracks substrate lists.

---

### P-021: Conditional M bullet regression probe (writer archetype)
**Category**: Iterator discipline / conditional protocol verification
**When to apply**: When any cycle adds a conditional M bullet to an agent's spec (e.g., "do X **when** Y is true"), the very next cycle MUST include a regression probe on a fixture where the condition is **false**.
**Solution**: The Spec Verifier writes one BDD scenario explicitly named as a "conditional inert probe" and the Dispatch Harness runs a fixture where the triggering condition does not hold. The Iterator then verifies:
1. The protocol is silently inert (no dutiful compliance beat added)
2. The slide / deliverable does NOT contain any artificial disclaimer born of the bullet
3. The bullet's conditional language is actually conditional (not accidental unconditional phrasing)
**Evidence**:
- Polish Writer A Cycle 2 added the "Brand-neutral reframe protocol" bullet (conditional on brand name in brief)
- Polish Writer A Cycle 3 ran Slide 12 clean-prompt fixture as the WA-20 regression probe
- Result: the bullet was correctly inert — no artificial brand-neutral disclaimer, no invented reframe beat; the G-statement reflective question appeared without any protocol contamination
- Same regression probe also confirmed the Cycle 1 substrate gap protocol is correctly inert when no gap exists
**Metric impact**: Catches the failure mode where a writer adds dutiful-but-unneeded protocol language on clean inputs, which would otherwise drift the archetype over multiple slides.
**Scaling recommendation**: Add a "protocol inert on negative condition" probe to the Spec Verifier checklist every time an M bullet contains conditional language. Cheap probe, high signal. Stack with P-014 (pre-dispatch granular flag format pinning) for reviewer agents.

---

### P-022: Rules at the decision point (orchestration archetype)
**Category**: Spec architecture / orchestration discipline
**When to apply**: Any orchestration-archetype agent (meta/coordinator) whose behaviors depend on runtime decision rules (conflict resolution, escalation, dispatch choice, LLM discipline)
**Solution**: Write runtime decision rules AT the orchestrator's own S block bullet level — NOT in separate sections the orchestrator is supposed to read and remember. Time-pressured operators read their own section first; if the rule lives in another section, it is effectively not there. Cross-section pointers are legitimate for DETAIL but insufficient for RULES that must fire on a specific decision.

Concrete structural pattern (from Polish Commander Cycle 2/3):

1. **Decision layered inline**: three-layer conflict rule (external-vs-internal / internal-vs-internal / producer-vs-reviewer) written as a single bullet with (a)(b)(c) sub-rules, rather than scattered across 3 different paragraphs.
2. **Rubric as bullet, not prose**: escalation decision becomes a numbered 3-question rubric inside one bullet — "any YES → escalate, all NO → self-resolve" — rather than a narrative.
3. **Checklist for multi-step reaction**: pilot-FAIL reaction becomes Step 1 / Step 2 / Step 3 bullets inside the Pilot Dispatch bullet, not a prose description in a far-away Template section.
4. **Rules about the orchestrator's OWN behavior**: Principle 7 (wrapper discipline) applies to orchestrator too, written at orchestrator's own S block, not inferred from subagent sections.

**Evidence**:
- Polish Commander Cycle 2 (HSW-008 substrate): 4/5 hardest-task scenarios passed but required rule **synthesis** from scattered spec signals — spec worked if operator was thoughtful, not if operator was rushed
- Polish Commander Cycle 3 (HSW-009 substrate, post-SPEC-DIFF-CMD-002): same 5 scenarios passed by **direct rule application** — operator reads bullet, applies bullet, done
- Zero synthesis required after the diff landed the rules inside the orchestrator's own S block

**Metric impact**: The metric is not BDD pass rate (both cycles passed) — it's **synthesis vs spec-directed** mode. Cycle 2: pass-with-synthesis. Cycle 3: pass-spec-directed. This converts time-pressure resilience from operator-skill-dependent to spec-dependent.

**Scaling recommendation**: Apply to any future orchestrator archetype. Specifically: when a new orchestrator is being written, audit the S block bullets and ask for each runtime decision the orchestrator must make, "is there a bullet in THIS section that tells me what to do, or am I expected to cross-reference?" If cross-reference, rewrite the bullet to contain the rule inline. Applies to any HSW fleet Commander, to any Task Mode coordinator, to any multi-agent A君 variant.

**Related**: P-008 (smallest-possible-diff) — P-022 does not contradict P-008 because each new inline bullet is still small; the total diff is a few bullets, not a restructure.

---

### P-023: 3-substrate topic rotation for orchestration archetype

**Category**: Test design (orchestration specialization of P-007)
**When to apply**: Any orchestration agent polish run
**Solution**: P-007 says 3 structurally-different inputs per iteration run. For orchestration archetype, "substrate" means **course topic for which the orchestrator must produce a dispatch briefing**, not "content substrate for the subagent to research". Each cycle's substrate should be structurally different at the **code regime** level: HSW-007 (electronic access / UL 294 / NFPA 72 egress) → HSW-008 (preservation / ADA / IBC Ch 34 existing buildings) → HSW-009 (NFPA 72 ch 24 / ADA visual / state K-12 mandates / fire marshal). Each triggers a different persona, different hard-constraint language, different anti-pattern customizations.

**Why**: The orchestrator's risk isn't research quality (that's subagents') — it's **topic-leakage**: carrying over persona/constraint language from one course to the next, producing dispatch briefings that are technically complete but semantically wrong for the current course. 3-substrate rotation surfaces leakage in 1 cycle.

**Evidence**:
- Polish Commander Cycle 1 (HSW-007), Cycle 2 (HSW-008), Cycle 3 (HSW-009): zero persona/constraint carryover on spot check. 3 completely different personas written from scratch in each cycle, each anchored to course-specific regulatory triples.
- If the spec had been topic-leaky, Cycle 2 would have produced an HSW-008 briefing with HSW-007 electronic-access language, surfacing immediately.

**Scaling recommendation**: For orchestrator-archetype polish, pick substrates from DIFFERENT HSW course families (electronic access / historic / K-12 / accessibility / fire). Avoid rotating within the same course family.

---

### P-024: Wrapper discipline applies to orchestrator's OWN LLM calls

**Category**: LLM governance
**When to apply**: Any multi-agent fleet using `/ai-fallback` where the orchestrator also needs LLM opinions
**Solution**: Principle 7 (embedded skill + model invocations via `call_with_fallback.sh`) is typically written for subagents. It must be **explicitly extended** to the orchestrator's own LLM calls. Otherwise the orchestrator falls back to direct `gemini`/`codex` CLI for "just a quick question" and trips G-001 (Flash hang), G-012 (Pro hang), G-014 (quota-vs-hang misclassification), or NEW-02 (Codex trust-check vacuous success).

Additional: on wrapper exit 3 (chain exhausted), the orchestrator falls through to **its own session's Claude-native reasoning**, NOT to another CLI retry. The orchestrator IS the final tier — this is the one unique capability the orchestrator has that no subagent does.

**Evidence**:
- Polish Commander Cycle 2: live wrapper call (`gemini-2.5-flash-lite,gemini-2.5-pro`) executed successfully, confirming Commander can honor the rule
- Polish Commander Cycle 3 SCN-CMD-C3-005: exit 3 → Claude-native fallthrough rule defined and applied on paper
- Matches G-001 / G-012 / G-014 / NEW-02 — same failure modes that already bit subagents would have bitten Commander if not bound to the wrapper

**Scaling recommendation**: Every orchestrator spec (future HSW fleets, A君 variants, Task Mode coordinators) must include an explicit "Commander's own LLM calls go through the wrapper too" bullet in its S block with the exit-3 fallthrough clause.
