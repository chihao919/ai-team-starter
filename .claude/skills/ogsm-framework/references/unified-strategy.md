# Unified Strategy — Factory Cross-Team Consolidation

**Document Type:** Phase D Integration Synthesis
**Created:** 2026-04-11
**Source data:** `team-1-workspace/`, `team-2-workspace/`, `team-3-workspace/`, `integration-notes.md`
**Scope:** Consolidated learnings from 3 parallel Iteration Teams (Mini-Research, Mini-Writer, Mini-Reviewer), 3 cycles each, 9 total cycles, all converged at 12/12 BDD PASS.

---

## Methodology

每個在 iteration 期間出現的 pattern，依照「有多少隊獨立重現」分類，作為未來 factory run 時的信心指標：

- **UNIVERSAL (3/3 teams)** — 高信心，應直接納入 factory core（ogsm-framework skill 預設套入）
- **LIKELY UNIVERSAL (2/3 teams)** — 中信心，納入 factory 時附註 "evidence partial"
- **ARCHETYPE-SPECIFIC (1/3 team)** — 保留作為知識資產，未來碰到相同 archetype 時再套用

Evidence citations follow the format `Team-N Cycle-M` so downstream readers can trace back to `iteration-log.md` of the relevant team workspace.

---

## UNIVERSAL Patterns (3/3 convergence)

### U-1: Cycle 1 structural header fix（mini-agent spec format → validator-compatible single-agent OGSM）

- **Description**: 三支 mini-agent 初稿都使用 `## G — Goal / ## S — Strategy / ## M — Measurement` 的 level-2 heading。Phase A validator suite 是為多 agent OGSM plan 設計的，預期 `### <emoji> <agent-name>` 加上 `**G（...）**` 的 bold sub-label。結果：baseline 所有隊的 4-5 個 validator 全部 FAIL，錯誤訊息一致 `"no '### ' agent headings found"` 或 `"No agent sections detected"`。
- **Evidence**:
  - Team 1 Cycle 1: 4 validators FAIL → Cycle 1 diff 新增 `### 🔬 Mini-Research Agent` heading + 三個 document-level section（Skill Invocation Map / Model Invocation Map / Brief Layering），4/4 PASS
  - Team 2 Cycle 1: 5 validators FAIL with identical error → Cycle 1 diff 插入 `### Mini-Writer Agent` heading，Cycle 2 時 5/5 PASS
  - Team 3 Cycle 1: 4/5 validators FAIL（same root cause）→ Cycle 1 diff 走 behavioral path（S-rule 修訂）；Cycle 2 時驚喜發現 5/5 PASS（behavioral 修訂順便觸發了結構符合）
- **Metric impact**: 每隊都從 0/4 或 0/5 validator PASS → 4/4 或 5/5 PASS，一次 diff 解鎖所有結構性驗證。屬於 step function，不是漸進改善。
- **Scaling recommendation**: 19-agent production fleet 的 agent 檔案如果已經符合 `### <emoji> <agent>` + OGSM 格式（HSW-002/006/007 等既有 agent），Cycle 1 不需要結構 diff。但只要是 **新寫的 mini-spec** 或 **單 agent 檔**，都要預先用 validator 跑過一次，否則會浪費整個 Cycle 1。建議在 factory 啟動前由 harness 自動跑 `validate_ogsm_completeness.py` 做 pre-flight，結構不符直接跳過 Cycle 1 只做結構 fix。

### U-2: 三層架構中央查詢（get_skills_for_role.sh）而非 spec 內嵌 skill 指令

- **Description**: 原 mini-agent spec 在 S 段嵌入完整 `/ai-fallback` 指令字串與 model 鏈，造成（a）多 agent 同步維護成本、（b）Tier 1 summary bloat、（c）central skill map 與各 agent spec drift。統一改為指向 `~/.claude/skills/ogsm-framework/scripts/get_skills_for_role.sh <role>` 查詢。
- **Evidence**:
  - Team 1 Cycle 2: 驗證 script exit 0，返回 2 個 skill 指令；新增 S11（map discovery before action）+ S12（no drift between map and execution）兩個 BDD scenario，兩者都 PASS
  - Team 2 Cycle 2: 新增 W-11（skill discovery via central map）；Cycle 2 驗證 `get_skills_for_role.sh mini-writer-agent` 返回 role-specific 內容；Cycle 3 時 skill discovery 真的幫 writer 找到 /ai-fallback path 並觸發 2 次 fallback
  - Team 3 Cycle 2: 新增 SCN-R-011（skill discovery）+ SCN-R-012（no drift between map and spec）。Cycle 2 時 SCN-R-012 FAIL（central map 有 /ai-fallback，spec 寫 "None" → drift），Cycle 2 diff 把 spec Skill Invocation Map 同步到 central map，Cycle 3 PASS
- **Metric impact**: 三隊都在 S11/S12/SCN-R-011/SCN-R-012 這類 scenario 上觀察到「成本最低、訊號最強」的效果。Team 3 更進一步用 SCN-R-012 發現並修復了 spec drift bug。
- **Scaling recommendation**: 未來新 agent 一律預設使用 central skill map 查詢，**嚴禁** 在 Tier 1 Summary 內嵌完整 skill 指令。Cycle 1 BDD 應該直接內建 "S11/S12 skill-discovery-discipline" 兩個 scenario，因為成本低、訊號強。

### U-3: Input 輪替 + topic-agnostic 驗證（A → B → C 三輪輸入）

- **Description**: 每隊 3 cycle 都輪替不同 input，刻意選擇 **substrate 差異大** 的題目，以確認 spec 不會把 Cycle 1 的框架 leak 到 Cycle 2 輸出。Team 1: multifamily self-closers → fire door spring hinges → ADA opening force。Team 2: Twin Parks fire → NFPA 80 spring hinge → ADA closing force。Team 3: promo + pedagogical → wrong section number + brand bias → replay。
- **Evidence**:
  - Team 1: Cycles 1/2/3 同一份 spec 處理 architectural code research / inspection regime research / ADA civil rights enforcement research，格式不變，零 leakage
  - Team 2: Cycle 2 deliverable 明確檢查 "zero occurrences of Twin Parks / Bronx / 333 East 181st / January 9, 2022 / 17 fatalities" 並通過（W-12）
  - Team 3: Cycle 2 輪替 Input-B，證明 Cycle 1 的 behavioral fix 不只是 replay-on-same-input 的 hack；FPs 4 → 1 是 cross-input 的真改善
- **Metric impact**: 提供「topic-agnostic generalization」的行為證據，是阻止 overfitting 的唯一方法。Team 2 的 W-12 之後應該被抄到所有 agent 的 BDD template。
- **Scaling recommendation**: 19-agent factory run 每隊最少準備 3 個 structurally-different input。Batch 的同類型 agent 應該刻意選擇 input 涵蓋不同 sub-domain（例如 Investigator A/B 就要一個看歷史 case、一個看 code + cost tradeoff）。

### U-4: Spec-diff-count 作為真正的 plateau 訊號（不是 BDD pass rate）

- **Description**: 三隊都發現「BDD pass rate 還在漲」不代表 spec 還在改善。三隊 Cycle 3 的大多數改善來自 harness 層（Team 1 skip Gemini primary）、fixture 層（Team 2 partial upstream）、或 replay 層（Team 3 同 spec 重跑），**spec 檔案本身已經 byte-identical 或只有空白行差異**。正確的 plateau 訊號是「連續兩個 cycle 沒有 spec diff 產生」而非「BDD pass rate 增幅 < 5%」。
- **Evidence**:
  - Team 1 STOP.txt: "The spec file is byte-identical to the end-of-Cycle-1 applied state (8776 chars, 136 lines, version 1.1)." BDD 70% → 83% → 100%，但 Cycles 2/3 spec diffs = 0
  - Team 2 Cycle 3: "No Cycle 4 spec edit proposed. Further iteration would be gold-plating."
  - Team 3 STOP.txt: "Cycle 3 was a REPLAY test... the Cycle 2 behavioral diff holds across both rotating inputs." Cycle 3 本身沒有 diff
- **Metric impact**: 用 spec-diff-count = 0 作為 plateau，可以把 Team 1 的 plateau 偵測從 Cycle 3 提前到 Cycle 2 尾段；Team 2 可以省掉 Cycle 3 的重跑（如果不是為了 W-09 behavioral evidence）。
- **Scaling recommendation**: 在 Iterator robot 的 scratchpad 加入 `spec_diff_proposed_this_cycle: bool` 欄位。連續兩次 False → 自動觸發 plateau check，除非 Iterator 明確列出還有 outstanding behavioral concerns（如 Team 2 的 W-09 vacuum）。

### U-5: Smallest-possible diff 紀律（一次改一個 root cause）

- **Description**: 三隊的 Iterator 都嚴守 "smallest-possible diff" 原則。Team 1 Cycle 1 只改 heading 不改 writer rule；Team 2 Cycle 1 只加一行 `### Mini-Writer Agent`；Team 3 Cycle 1 的 3 個 FAIL（SCN-R-005/006/010）全部指向同一個 root cause（S rule 未明確），用一組 localized edit 處理。Team 3 Cycle 1 明確拒絕同時修結構 validator issue，因為那屬於 global 決策。
- **Evidence**:
  - Team 1 Cycle 1 patch: 96 lines，全部是 additive（插入 heading、sub-label、3 個 document section），零刪除
  - Team 2 Cycle 1 patch: 單 heading line 插入
  - Team 3 Cycle 1 patch: `"All three FAILs share a single root cause... and are addressed by ONE localized S edit + one Anti-pattern addition."`
- **Metric impact**: 零 regression、容易 review、容易 rollback。三隊的 regression check 都是 "previously-passing scenarios all remain PASS"。
- **Scaling recommendation**: Iterator 每個 cycle 強制回答兩個問題：(1) 這個 diff 的 root cause 是什麼？(2) 有沒有其他 FAIL 被同一 root cause 解決？如果答 "順便修其他的"，cycle 越界了，應拆成下個 cycle。

---

## LIKELY UNIVERSAL (2/3 convergence)

### L-1: `/ai-fallback` 行為證據應由 harness 強制觸發（而非等 upstream 自然缺口）

- **Description**: Mini-Writer 的 W-09（fallback wiring）在 Cycle 1/2 都 "passing by vacuum"——upstream research 完整，writer 根本沒需要 fallback，metric 是誠實的 `fallback_events=0` 但屬於無證據 PASS。Cycle 3 harness 故意提供 partial upstream（3 個 bare section 編號、零 case、零 URL），強制 writer 選（a）halt 或（b）invoke fallback，拿到真正的 behavioral evidence（fallback_events=2）。Team 3 也用類似設計：Cycle 2 植入「NFPA 80 §6.1.5 wrong section」這種 reviewer 無法靠 native judgment 查的 planted issue，強制走 /ai-fallback escalation。
- **Evidence**:
  - Team 2 Cycle 3: `upstream-partial-cycle-3.md` fixture + INT-002 harness instruction → W-09 real evidence
  - Team 3 Cycle 2 Input-B: 植入 wrong-section-number → 觀察到 native judgment 查不到 → Cycle 2 diff 把 /ai-fallback 列入 Skill Invocation Map；Cycle 3 replay 真的觸發 escalation
  - Team 1 沒用這個模式（/ai-fallback 本來就是 research agent 主路徑，不需要故意強制）
- **Metric impact**: 把 vacuous-PASS 轉成 behavioral-PASS。區分「spec 允許但從未用到」vs「spec 允許且真正驗證過」。
- **Scaling recommendation**: 任何「agent 在 happy path 不會觸發」的 skill 或 fallback 路徑，harness 應該在 Cycle 2 或 Cycle 3 設計一個 broken fixture 強制觸發。建議在 ogsm-framework 加入 `fixtures/partial-upstream-template.md` 作為樣板。

### L-2: Harness 層的學習（非 spec 改動）可產生顯著加速

- **Description**: 三隊之中兩隊（Team 1 + Team 3）在 Cycle 3 用 harness 層的改動獲得顯著加速或解鎖：Team 1 harness 學會跳過 Gemini 2.5 Flash primary，wall-clock 從 720s → 360s（-50%）且零 spec 改動；Team 3 Cycle 3 replay mode（重跑 Cycle 1/2 fixture 而非 rotate 新 input），44s 完成 combined replay。
- **Evidence**:
  - Team 1 Cycle 3: "The +17pp BDD jump from Cycle 2 to Cycle 3 required zero spec edits. This is the first cycle where the harness outperformed the spec as an improvement lever."
  - Team 3 Cycle 3: REPLAY test mode，不 rotate 新 input，44 秒內驗證兩組 fixture 修復
  - Team 2 沒用這個模式（Team 2 Cycle 3 是新 input 而非 replay）
- **Metric impact**: Cycle 3 wall-clock 大幅下降，同時維持 converge 訊號。
- **Scaling recommendation**: 給 Dispatch Harness 明確 license 在 Cycle 2/3 進行非 spec 的行為優化，包括 (a) 跳過已知有 bug 的 model、(b) 使用 replay mode、(c) 設計 stress-test fixture。這些改動應自動記錄到 integration-notes.md 作為未來 skill 內化的候選。

### L-3: Pointer 模式是 additive 而非 substitutive（需要 validator 配合才能真的縮 spec）

- **Description**: Team 1 Cycle 1 的原始想法是：用 `get_skills_for_role.sh` pointer 替換 spec 內嵌 skill 指令，**預期 briefing char count 會下降**。實際結果：char count 從 7331 升到 8776（+19.7%），因為 `check_skill_architecture.py` validator 仍然要求 document-level `## Skill Invocation Map` section 存在，所以 pointer 只能 append 不能 replace。這是 negative finding，但是很重要的架構教訓。
- **Evidence**:
  - Team 1 Cycle 2 log: `"Pointer pattern is additive, not substitutive. Briefing char count grew (+19.7%) because the pointer was added on top of the existing map, not in place of it. A true pointer-only pattern requires validator updates in Phase D."`
  - Team 2 Cycle 1 diff: 直接 append 三個 document-level section（Skill Invocation Map / Model Invocation Map / Brief Layering）以滿足 validator
  - Team 3: 僅改表格內容不涉及 reduction
- **Metric impact**: 預期的 char reduction 未發生。真正要達成 reduction 需要 **先改 validator**，讓它接受 "single pointer line 等同於 full section"。
- **Scaling recommendation**: 不要對 pointer 模式抱有縮減 spec size 的期待，除非同時有 validator 改動。應在 ogsm-framework-updates.md 中加入 "allow pointer-only Skill Invocation Map" 作為 validator 修改項目。

### L-4: BDD scenario 版本化（cycle-N BDD file）

- **Description**: Team 2 和 Team 3 都用 `bdd-scenarios-cycle-2.md` / `bdd-scenarios-cycle-3.md` 的命名把每個 cycle 的 BDD 版本固定下來。Cycle 2 新增 scenario（W-11/W-12、SCN-R-011/SCN-R-012、S11/S12）時，舊 cycle 檔案保持不動，新增項目在新檔案。這讓 "scenario 數量從 10 增加到 12" 的數字可稽核。
- **Evidence**:
  - Team 2: `bdd-scenarios.md`（C1 10 個）→ `bdd-scenarios-cycle-2.md`（C2 12 個）→ `bdd-scenarios-cycle-3.md`（C3 12 個，"Changes vs cycle 2: NONE"）
  - Team 3: 同樣三版檔案
  - Team 1 iteration-log 有清楚記錄 S11/S12 新增，但沒有獨立檔案化
- **Scaling recommendation**: 強制每隊 per-cycle BDD 版本化。Spec Verifier 每個 cycle 開新檔案，即使內容沒變也要寫一份 `"Changes vs cycle N-1: NONE"` 的 header。這是未來 reproduce 的關鍵。

---

## ARCHETYPE-SPECIFIC (1/3)

### A-1: `/ai-fallback` hang（Gemini 2.5 Flash 非 quota 失敗）

- **Description**: Team 1 獨有的生產觀察。Gemini 2.5 Flash 在 research prompt 下會 hang 360+ 秒無輸出、無 error。`call_with_fallback.sh` 只在 explicit quota error 時 advance，無法辨識 hang。Input-A / Input-B / Input-C 三種不同 research 題目都重現，非 topic-dependent。
- **Evidence**: Team 1 Cycle 1 (360s hang on Input-A), Cycle 2 (90s hang on Input-B), Cycle 3 (harness 主動跳過)。已登記為 INT-001。Team 2/3 沒有重現——因為 Writer 和 Reviewer 都是 Claude-native 主路徑，/ai-fallback 只在 edge case 使用，沒大量打 Gemini Flash 所以沒觸發 hang pattern。
- **Scaling recommendation**: 只影響 "重度使用 Gemini Flash primary" 的 agent，例如 Investigator A / Investigator B / Fact Checker。其他 agent 不受影響。INT-001 Option A（內化到 call_with_fallback.sh per-model timeout）是最乾淨的修法，一次解決所有使用 fallback 的 agent。

### A-2: `flag_candidate.sh` 受 wall-clock budget 壓縮從未實測

- **Description**: Team 1 three cycles 的 content-scout `flag_candidate.sh` 都沒有真的 live 執行（都是 metric `content_scout_flag_executed_via_script: false`）。Team 1 的 content scout flag 是 spec 正確記錄但 script 未被跑——這屬於 harness budget 問題不是 spec 問題。Team 2/3 沒用到 content-scout。
- **Evidence**: Team 1 metrics-cycle-1.json / -2 / -3；team-1 STOP.txt 明確列為 INT-003 候選
- **Scaling recommendation**: 任何有 "optional side-effect script" 的 agent（content-scout flag、metric reporter 等）都要給 15 分鐘以上的 cycle budget，或者把這些 script 列為 async post-cycle step。

### A-3: Granular vs consolidated flag strategy（reviewer）

- **Description**: Team 3 Cycle 1 Input-A 時 reviewer 把 Waterson promo 那個 planted issue 拆成 4 個 granular AIA HSW 子項目 + 1 個 tone brand-bias flag（共 5 個 flag）。Cycle 3 replay 同一個 fixture 時，v1.2 spec 行為改成 single consolidated flag。這是 reviewer archetype 獨有的設計決定：granular 有助於 mechanical fixing，consolidated 有助於 reviewer-to-writer feedback loop。
- **Evidence**: Team 3 Cycle 3 replay log `"AIA HSW Compliance flag, single consolidated flag (not split granular like Cycle 1)"`
- **Scaling recommendation**: Review 類 agent（Content Director, Compliance Reviewer, Copy Editor 等）應在 BDD 中明確指定「granular 或 consolidated」預期，避免 iteration 時 oscillation。

### A-4: 中央 validator suite 的 silent-pass false positive

- **Description**: Team 1 Cycle 1 發現 `validate_s_to_m_coverage.py` 在 0 parseable agent 的情況下返回 exit 0 PASS（silent skip）。這是 latent false positive，其他隊雖然也碰到了結構 FAIL，但沒獨立觀察到 silent-pass——因為其他 validator 有明確 FAIL 訊息蓋掉了這個 PASS。
- **Evidence**: Team 1 iteration-log Cycle 1 surprising findings #1
- **Scaling recommendation**: 立即修 validator（加入 "at least 1 agent must be parsed" assertion），參考 gotchas-and-lessons.md G-002。屬於 ogsm-framework-updates.md 必改項目。

### A-5: Behavioral diff accidentally unblocks structural validators

- **Description**: Team 3 Cycle 2 發現他們的 behavioral diff（只改 S rules + Anti-patterns）結果讓原本 4/5 FAIL 的 validator 變成 5/5 PASS。`"previous 4/5 FAIL was pre-existing structural issue; Cycle 1 behavioral diff somehow aligned with structural expectations, verified by running"`。這是正向意外。
- **Evidence**: Team 3 Cycle 2 iteration-log
- **Scaling recommendation**: 記錄為正向意外，不主動複製；但如果未來某隊 Cycle 1 拒絕做結構 diff 也沒關係，Cycle 2 的 behavioral diff 可能順便修掉。這降低了 Cycle 1 結構 diff 的急迫性。

---

## Summary

| Category | Count | Confidence | Action |
|---|---|---|---|
| UNIVERSAL (3/3) | 5 | High | 納入 ogsm-framework core，新 factory run 預設套用 |
| LIKELY UNIVERSAL (2/3) | 4 | Medium | 納入 ogsm-framework 但附 "partial evidence" 注記 |
| ARCHETYPE-SPECIFIC (1/3) | 5 | Low | 保留在 patterns-library 作為知識資產，遇到相同 archetype 再套用 |
| **Total patterns** | **14** | — | 見 `patterns-library.md` 的 ID 對應 |

**Key takeaway**: 三隊的結構 FAIL 都源於同一個 mini-spec format vs 多 agent validator 格式落差（U-1）。這代表未來寫新 agent spec 時，**Pre-flight validator run 是零成本的 Cycle 0**。光這個改動就能把 19-agent factory run 的 Cycle 1 從 "全部處理結構 FAIL" 提前到 "全部開始做 behavioral work"，省下一整輪 wall-clock。
