# Scaling Playbook — From 3 Mini-Agents to 19-Agent Production Fleet

**Document Type:** Phase D Integration — Operational Handbook
**Created:** 2026-04-11
**Purpose:** 基於 mini-agent factory run（Team 1/2/3 × 3 cycles）的實測證據，說明如何把 factory 套用到真正的 HSW-002/006/007 19-agent production fleet。

這份 playbook 告訴你 HOW：把 factory 帶到真正的生產 agent 上時，該依照什麼順序、什麼批次、什麼預算執行，哪些 risk 要先擋掉。

---

## Prerequisites

在啟動 scaled factory run 之前必須完成：

1. **INT-001 修復**：`~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh` 加 per-model timeout（Option A 推薦）。不修會讓所有 research 類 agent 重現 G-001 Gemini Flash hang
2. **ogsm-framework skill 更新**：把 `patterns-library.md`、`gotchas-and-lessons.md`、`scaling-playbook.md` 複製到 `~/.claude/skills/ogsm-framework/references/`，讓下個 Iterator robot 能查詢
3. **Validator 修 G-002**：`validate_s_to_m_coverage.py` 加 "at least 1 agent parsed" assertion
4. **Target agents 識別並分 archetype**（見下）
5. **Budget 核定**（見 Budget estimation）
6. **3 input pool / agent**：每隊必須準備 3 個 substrate 差異大的 input（P-007）

---

## Phase 1: Pre-flight checks

Factory 啟動前的 checklist：

- [ ] `ls ~/.claude/skills/ai-fallback/scripts/call_with_fallback.sh` 且確認 `grep -q 'timeout' call_with_fallback.sh` 有結果（INT-001 已修）
- [ ] `bash ~/.claude/skills/ogsm-framework/scripts/validate_s_to_m_coverage.py --help` 會列出 `--min-agents` 或等效 assertion
- [ ] `ls ~/.claude/skills/ogsm-framework/references/patterns-library.md` 存在
- [ ] `bash ~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh --list` 可列出所有已登記 role
- [ ] 每個 target agent 都跑過一次 validator baseline（**pre-flight 不是 Cycle 1 的一部分**）
- [ ] 每個 target agent 的 3 個 input pool 已準備、已分類（structurally different）
- [ ] Team workspace 的 write-isolation rule 與 apply-to-target 例外已規劃（避免 G-009 bottleneck）
- [ ] integration-notes.md 空白以待新 items
- [ ] 3 input pool 至少有一個刻意設計成 "partial upstream" 或 "planted wrong clause" 以強制觸發 fallback path（P-004 / G-005）

### Pre-flight 結構 fix（Cycle 0）

如果 pre-flight validator run 發現某個 agent 結構 FAIL（"no '### ' agent headings found"），直接在 Cycle 0 套 P-002 結構 diff，**不要**浪費 Cycle 1 去發現同樣的事：

1. 插入 `### <emoji> <Agent Name>` heading
2. 把 `## G/S/M` 轉 bold sub-label `**G（...）** / **S（...）** / **M（...）**`
3. 視情況 append `## Skill Invocation Map` / `## Model Invocation Map` / `## Brief Layering`
4. 重跑 validator 確認 PASS
5. 這個 Cycle 0 diff 不算 iteration cycle，不計入 plateau 計算

對於既有 OGSM plan（HSW-002/006/007 等多 agent plan）格式本來就符合，可以跳過 Cycle 0。

---

## Phase 2: Archetype-grouped batches

不要把 19 agent 一次全部下去跑。按 archetype 分批，每批有一致的 failure mode 與 pattern 預期：

### Batch 1 — Research + Writing core（4 agents）

- Investigator A（historical cases）
- Investigator B（codes + cost tradeoff）
- Writer A（narrative slides）
- Writer B（mechanism slides）

**Estimated time**: 4 × (5 min setup + 15 min/cycle × 3 cycles + 10 min integration) ≈ 約 4 小時 parallel，實際約 60–80 分鐘 wall-clock（4 平行 + 共享 apply phase）
**Estimated cost**: 4 × mini-agent baseline × 3（實際 agent 比 mini 大 3–5 倍）
**Key risks**: G-001 Gemini Flash hang（research agent 是最嚴重受害者）。必須確認 INT-001 已修
**Pattern preload**: P-001, P-002, P-003, P-004, P-007, P-008, P-011

### Batch 2 — Internal Review layer（5 agents）

- Content Director
- Compliance Reviewer
- Copy Editor
- Fact Checker
- Source Reviewer

**Estimated time**: 5 × (replay mode 可用) ≈ 30–50 分鐘 parallel（Team 3 Cycle 3 用 replay mode 只花 44 秒，本批可大幅縮短）
**Estimated cost**: 5 × mini-reviewer baseline × 2（replay 攤薄）
**Key risks**: G-005 vacuous PASS on escalation path；P-014 granular vs consolidated 設計決定
**Pattern preload**: P-003, P-004（for Fact Checker）, P-013, P-014

### Batch 3 — External reviewers（3 agents）

- 外審專家 A（architect peer）
- 外審專家 B（compliance specialist）
- 外審專家 C（user experience angle）

**Estimated time**: 3 × ~40 分鐘 parallel ≈ 40 分鐘 wall-clock
**Estimated cost**: 3 × mini-reviewer × 2
**Key risks**: Persona fidelity；用 `/ai-fallback` 做 persona simulation 可能再次觸發 G-001
**Pattern preload**: P-003, P-007, P-011

### Batch 4 — Orchestration + QA + misc（7 agents）

- Commander
- Performance Supervisor
- Quality Auditor
- Learning Validator
- Engineer HTML
- Engagement Designer
- Candidate Collector

**Estimated time**: 7 × variable（Commander / Performance Supervisor 通常複雜；Engineer HTML / Candidate Collector 較簡單）≈ 90–120 分鐘 parallel
**Estimated cost**: 7 × mini baseline × 2–4 變動
**Key risks**: Commander / Quality Auditor 的 BDD scenario 難設計（需要評估「是否正確分派」這類 meta 行為）
**Pattern preload**: P-003, P-006, P-007, P-008, P-010

---

## Phase 3: Per-batch factory run

每個 batch 內部重複以下步驟：

1. **建立 N 個 team workspace**（N = batch 大小），例如 `docs/iteration-team/batch-1-team-A-workspace/`
2. **Commander 派 N 個平行 Iteration Team**（同時 dispatch 以利用 parallelism）
3. **Cycle 0**：pre-flight validator；如有結構 FAIL 套 P-002
4. **Cycle 1**：
   - Spec Verifier 寫 BDD scenario（內建 P-003 skill discovery scenarios、P-007 topic rotation、P-009 BDD versioning）
   - Dispatch Harness 跑 Input-A
   - Iterator 提 smallest-possible diff（P-008）
   - Commander review + apply（或 apply phase robot）
5. **Cycle 2**：rotate 到 Input-B
   - 若 Cycle 1 發現 skill drift → Cycle 2 修
   - 若 fallback scenario passing-by-absence → Cycle 2 或 3 設計 stress fixture（P-004）
6. **Cycle 3**：rotate 到 Input-C（或 replay mode 若 review archetype）
   - Plateau check：若連續兩個 spec-diff=0（P-006），emit STOP signal
7. **Per-batch integration phase**：batch 內 Commander 跑 mini-integration 收集 patterns

### Plateau 規則（修訂版）

原規則是 "improvement < 5% across 3 cycles = plateau"。根據 G-007 / P-006 修訂：

**主要訊號**：`spec_diff_proposed_this_cycle` 連續兩次 False → STOP
**次要訊號**：BDD pass rate 增幅 < 5% 三個 cycle → STOP
**例外**：若 Iterator 明確列出 outstanding behavioral concern（例如 W-09 vacuous PASS），可延一 cycle 做 stress fixture，但必須明確寫在 iteration-log.md

---

## Phase 4: Cross-batch integration

所有 batch 結束後，一個 meta-integration phase：

1. 收集 batch 1–4 的 per-batch integration 輸出
2. 比對 4 個 batch 間的 pattern 共性
3. 更新 `patterns-library.md`：
   - Batch 間都看到的 pattern → 升級為 "CROSS-ARCHETYPE UNIVERSAL"
   - Batch 內獨有的 pattern → 標記為 "ARCHETYPE-BOUND"
4. 更新 `ogsm-framework` skill 的 reference
5. 寫一份 production-deploy 的 go/no-go 報告
6. 如有 `STOP signal with outstanding concerns`，把每個 concern 變成 Phase E 工作項目

---

## Budget estimation

根據 mini-agent factory run 實測：

### Mini-agent baseline

| Metric | Team 1 | Team 2 | Team 3 | Median |
|---|---|---|---|---|
| Cycle 1 wall-clock | 540s | 1024s | 82s | ~550s |
| Cycle 2 wall-clock | 720s | 612s | 20s | ~600s |
| Cycle 3 wall-clock | 360s | 420s | 44s | ~400s |
| Total per agent, 3 cycles | ~1620s (27 min) | ~2056s (34 min) | ~146s (2.5 min) | ~1300s (22 min) |

**Review archetype 比 research/writer archetype 快一個量級**（Team 3 2.5 min vs Team 1/2 30 min），原因：
- Review 不需要新產內容，只判斷既有 draft
- Review 可用 replay mode（P-013）
- Review 不需要 `/ai-fallback`（除了 edge case 的 exact-clause verification）

### Scaling factor（mini → real）

Real agent 比 mini-agent 複雜的倍數：

- **Input size**: mini-spec ~3KB–8KB，real agent plan ~15KB–40KB → 2–5× 輸入
- **Output complexity**: mini deliverable ~3KB，real deliverable ~10KB–25KB → 3–8× 輸出
- **Validator runs**: 相同，不 scale
- **Fallback events**: 可能更多（real agent 有更多 clause 要驗）→ 1–3× fallback time

**合理 scaling factor：3–5×**

### Per-agent wall-clock estimate（real agent）

- Research / Writer: median 22 min × 4 = **~90 min** / agent (3 cycles)
- Review（replay 可用）: 2.5 min × 3 = **~8 min** / agent (3 cycles)
- Orchestration / QA: 22 min × 5 = **~110 min** / agent（較難，BDD scenario 設計成本高）

### Parallelism

- 同 batch 內最多 4–5 個 agent 平行（超過會打到 Claude API rate limit + git 寫衝突）
- Batch 間 sequential（需要 meta integration）

### Total budget estimate（full 19-agent factory run）

假設 4 batch × 平均 4 agent/batch：

| Batch | Agents | Parallelism | Per-agent time | Batch wall-clock |
|---|---|---|---|---|
| Batch 1 (Research + Writer) | 4 | 4-wide | ~90 min | ~90 min |
| Batch 2 (Internal Review) | 5 | 4-wide（5th sequential） | ~8 min (replay) | ~15 min |
| Batch 3 (External Review) | 3 | 3-wide | ~40 min | ~40 min |
| Batch 4 (Orchestration + misc) | 7 | 4-wide（2 sequential rounds） | ~110 min | ~220 min |
| **Meta integration** | — | — | ~30 min | ~30 min |
| **Total wall-clock** | **19** | — | — | **~6.5 hours** |

**Cost estimate**: mini-agent 一個 cycle 約 0.5–1.5 USD Claude API 成本；real agent 約 2–7 USD/cycle × 3 cycles × 19 agents ≈ **110–400 USD API cost** for full factory run

**Practical planning**: 分 2 天跑比較安全。Day 1 跑 Batch 1 + 2（4 小時），當日 Cycle 0 + Cycle 1；Day 2 跑 Batch 3 + 4 + Meta（3 小時）。中間可 reviews integration notes。

---

## Risk points

### R-1: Apply phase bottleneck（G-009）

**Risk**: Team workspace 寫 isolation，每個 cycle diff 要 Commander 手動 apply，19 agent × 3 cycle = 57 次 apply
**Mitigation**: 授權 "Apply phase robot" 專門做 apply；或給每個 team 明確的 apply-to-target 例外許可；或 Cycle 1 批次 apply（把 N 個 team 的 Cycle 1 diff 一起 review）

### R-2: Gemini Flash hang 未修就 launch

**Risk**: 所有 research agent cycle 浪費 6+ 分鐘 × 3 cycles × 4 agents = 超過 1 小時 wall-clock 在 hang 上
**Mitigation**: **INT-001 是 blocker**。未修不 launch

### R-3: BDD scenario 設計品質不一致

**Risk**: 19 agent 不同人寫的 BDD scenario 品質參差，有的抓不到 bug，有的過度嚴格
**Mitigation**: Spec Verifier robot 共用 template；每 team Cycle 1 強制內建 P-003 skill discovery scenarios 與 P-007 topic-agnostic check；Commander Cycle 1 後 spot-check

### R-4: Cross-team upstream 依賴順序

**Risk**: 4 agent 並行時 Writer 需要 Investigator 的 output，但兩者同時跑 → Writer 拿不到上游
**Mitigation**: Batch 內有依賴關係的先跑 upstream（Investigator A/B），再跑 downstream（Writer A/B）。Writer Cycle 1 用 seed dataset；Cycle 2 用 Investigator Cycle 1 產出

### R-5: Plateau rule 被誤判繼續 iterate

**Risk**: 團隊看到 BDD rate 還在漲就繼續 iterate，spec 其實已收斂（G-007）
**Mitigation**: Iterator robot 強制追蹤 `spec_diff_proposed_this_cycle` 欄位；連續兩次 False 自動 plateau assertion；Commander review 時看這個欄位不看 BDD rate

### R-6: 新 batch 的 pattern 沒 transfer 到舊 batch

**Risk**: Batch 1 發現新 gotcha，Batch 2 還沒套用 → 重複踩坑
**Mitigation**: Per-batch integration 必做，不要等到 Meta phase 才同步 patterns-library

### R-7: Content scout 類 side-effect script 從未 live 執行

**Risk**: G-006 / P-012 — 生產 agent 的 flag_candidate.sh 或 metric reporter 仍然被 budget 擠掉
**Mitigation**: 這類 script 預設改為 async post-cycle，或強制 live timeout ≥15 min

---

## Known good patterns to apply proactively

從 `patterns-library.md` 挑出 universal/likely-universal patterns，這些應在**第一個 cycle 前**就套用，不要等 FAIL 才發現：

| Pattern | When to apply | How |
|---|---|---|
| **P-001** Skill discovery via central map | Cycle 0 / pre-flight | 確認所有 agent 都用 `get_skills_for_role.sh` pointer，不內嵌 skill 指令 |
| **P-002** Structural header injection | Cycle 0 | Pre-flight 如果 validator 結構 FAIL，立即套 |
| **P-003** Skill map drift BDD scenario | Cycle 1 Spec Verifier | 所有 BDD template 內建 "skill discovery + no drift" 兩個 scenario |
| **P-004** Forced fallback via partial upstream | Cycle 1 Harness preparation | 任何有 fallback/escalation path 的 agent，預備一份 partial fixture 給 Cycle 2 或 3 |
| **P-006** Spec-diff-count plateau | 全流程 | Iterator robot 強制追蹤欄位 |
| **P-007** Topic rotation | Cycle 1 Harness preparation | 3 個 structurally-different input 準備齊全 |
| **P-008** Smallest-possible diff | 每 cycle | Iterator system prompt 寫死 |
| **P-009** Per-cycle BDD versioning | 每 cycle | Spec Verifier 強制開新檔案 |
| **P-010** Harness learning | Cycle 2+ | 發現 model-level friction 時授權 harness 跳過 |
| **P-011** Gemini Flash hang workaround | 所有 research agent | 若 INT-001 未修，harness 預設跳過 Gemini primary |

---

## Go / No-go checklist for scaled launch

Factory run 啟動前，以下每個條目都必須打勾：

- [ ] INT-001（/ai-fallback hang）已修並驗證
- [ ] G-002（validate_s_to_m_coverage silent PASS）已修
- [ ] `patterns-library.md` / `gotchas-and-lessons.md` / `scaling-playbook.md` 已複製到 ogsm-framework skill references
- [ ] 19 agent 名單 + archetype 分類已 finalized
- [ ] 每個 agent 的 pre-flight validator run 完成；結構 FAIL 已 Cycle 0 修復
- [ ] 每個 agent 的 3 個 input pool 準備完成
- [ ] Budget 核定（6.5 hours wall-clock, 110–400 USD API）
- [ ] Apply phase bottleneck 方案確定（R-1）
- [ ] Commander 明確知道 plateau rule 是 spec-diff-count 不是 BDD rate（R-5）
- [ ] Meta integration phase 的 slot 已保留（~30 分鐘）

以上全部 OK 才 launch。

---

## Summary

- **19 agent 分 4 batch**，按 archetype 排序
- **Total wall-clock ~6.5 小時**（分 2 天跑比較安全）
- **Total cost ~110–400 USD** Claude API
- **Blocker**: INT-001 Gemini Flash hang 必須先修
- **Critical pattern preload**: P-001, P-002, P-003, P-006, P-008
- **Fastest archetype**: review（~8 min/agent with replay mode）
- **Slowest archetype**: orchestration + QA（~110 min/agent）
