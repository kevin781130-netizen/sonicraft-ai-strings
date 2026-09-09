# StringCC × Sonicraft AI Strings 融合審核

審核日期：2026-09-09  
Sonicraft upstream：`kevin781130-netizen/sonicraft-ai-strings`  
審核基準 commit：`4f9f1915d6179ffb3d669bbb3a483c4e30643fbf`（2026-09-05，Q4 v7.0 RC2 source convergence）

## 結論

**適合融合，但目前不適合直接複製或靜態連結 Sonicraft 的原始碼進 StringCC MIT 核心。**

原因不是功能衝突，而是授權狀態：審核時 repository 根目錄沒有 `LICENSE`、`LICENSE.md` 或 `COPYING`；`licenses/THIRD_PARTY_NOTICES.txt` 是第三方元件 notice，不能自動視為 Sonicraft 自身 source license。

因此 StringCC v1.1 採：

1. **clean-room reimplementation**：只依公開架構與一般軟體工程概念，重新實作治理功能；
2. **process-boundary adapter**：如使用者另行安裝/獲授權 Sonicraft，可透過 JSON file protocol 呼叫外部 executable；
3. **零 Sonicraft source bundling**：本發行包沒有複製 Sonicraft `.h/.cpp`、模型或 asset。

若 upstream 日後明確加入 MIT / Apache-2.0 或其他相容授權，可再評估 direct library integration。

## 為什麼功能上適合

StringCC 與 Sonicraft 的核心層次不同，互補性高：

| 層 | StringCC 強項 | Sonicraft 公開架構強項 | v1.1 融合方式 |
|---|---|---|---|
| 演奏生成 | MIDI/MusicXML → phrase/bow/CC/vibrato | candidate take / phrase repair | 保留 StringCC generator |
| Render | REAPER warm worker、cache、parallel、VST3 groundwork | DAW/VST3 外部 audition | 共用外部 evidence 邊界 |
| Feedback | STRAdi / VioPTT / human A/B | performance critic / audio judge | StringCC feedback 作 critic evidence |
| 候選策略 | random/adaptive/local optimization | conductor candidate steering | 新增 `ConductorSteerer` |
| 候選排序 | objective / optimizer | candidate utility prediction | 新增 `CandidateUtilityPredictor` |
| 因果安全 | baseline + whole safety gate | counterfactual audit / intervention minimality | 新增 `CounterfactualAuditor` |
| 長期記憶 | preference JSONL / optimizer history | retained evidence / provenance | 新增 `EvidenceLedger` |
| Release | optimization report | release/provenance gates | 新增 governance report/evidence |

## 實際審閱的 Sonicraft 檔案

以下檔案只作**架構理解**，未複製 source：

- `README.md`
- `START_HERE.txt`
- `docs/ARCHITECTURE.md`
- `docs/AUDIO_JUDGE_REPAIR_ITERATION_V49.md`
- `src/conductor_intent_v53.h`
- `src/conductor_candidate_steering_v54.h`
- `src/candidate_utility_predictor_v55.h`
- `src/counterfactual_auditor_v56.h`
- `CMakeLists.txt`
- `licenses/THIRD_PARTY_NOTICES.txt`

## v1.1 已融合的 clean-room 功能

### Conductor Intent

全局意圖以 StringCC 自己的資料模型表示：

- energy
- tension
- continuity
- contrast
- vibrato character
- bow weight
- restraint
- section role（lead/support/transition/cadence）

不直接取代 phrase optimizer，而是**偏置候選生成**。

### Candidate Steering

每個 phrase 先建立四個可解釋候選 family：

- `shape`：apex + macro CC1 span
- `energy`：intensity + bow speed/pressure
- `connection`：CC11 + pre-roll + vibrato
- `restraint`：抑制過度表情/overfit

全部受 StringCC 原有 phrase-local parameter bounds 約束。

### Candidate Utility Predictor

利用 StringCC 自己累積的 evidence JSONL 估計：

- expected gain
- uncertainty
- intervention complexity
- acquisition score

有歷史資料時會偏向過去有效 family；沒資料仍保留 exploration。

### Counterfactual Auditor

候選不只看「這句 loss 低了沒」，還能檢查：

- local improvement 是否足夠
- whole-piece 是否 regression
- adjacent phrase spillover
- intervention 是否過廣
- causal confidence（透明 heuristic score，不冒充統計機率）

StringCC 原本的 final whole-piece safety gate 仍是最後權威。

### Evidence Ledger

append-only JSONL，保存：

- candidate ID / family
- phrase key
- overrides
- utility prediction
- actual feedback
- audit result
- accepted/rejected
- local gain / causal confidence

具有 idempotent evidence ID，resume job 不會重複計功。

### 外部 Sonicraft Adapter

`SonicraftExternalAdapter` 只透過 JSON input/output 呼叫另外安裝的 command，沒有 Python/C++ source import。

這是目前最安全的真 Sonicraft interoperability 邊界。

## 不建議融合的部分

### 1. 直接複製 Sonicraft C++ headers/sources

目前**不適合**。原因：沒有明確 project-level license。

### 2. 重做 StringCC 已有的 MIDI/CC renderer

不值得。StringCC 已有 MusicXML、bow/fingering、CC、local feedback、warm worker、cache/parallel；直接用 Sonicraft 類似低層 compiler 取代，收益小且增加整合風險。

### 3. 把 Sonicraft 大量 versioned training/release scaffolding 全搬入核心

不建議。StringCC 應吸收「治理原理」，不應讓音樂引擎被另一個專案的 release archaeology 綁死。

## 建議的產品架構

```text
MusicXML / MIDI
      ↓
StringCC phrase + bow + CC engine
      ↓
Conductor Intent
      ↓
Governed Candidate Families
      ↓
Utility Predictor ─── Evidence Ledger
      ↓
Render Cache / Warm Worker / VST3
      ↓
STRAdi + VioPTT + Human A/B
      ↓
Counterfactual Auditor
      ↓
Accept / Reject / Repair
      ↓
Whole-piece Safety Gate
      ↓
Best MIDI + Provenance
```

這個融合方式是目前最適合 StringCC 的做法。
