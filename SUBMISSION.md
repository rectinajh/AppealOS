# AppealOS — Devpost Submission Draft

> All Things Agentic Hackathon · Primary track: **The Taskmaster**
> 提交主版本为英文（English is the master submission copy）；中文为留档版本（Chinese copy is for archive only）。
> 本文件以仓库内 `README.md`、`docs/PRD.md`、`docs/TECHNICAL_DESIGN.md` 为事实基线；只写「已实现（implemented）」或「明确 planned」的事实，不把未部署组件写成已实现。

---

## 0. 项目标识 / Project identity

| 字段 / Field | 值 / Value | 状态 / Status |
|---|---|---|
| Project name | `AppealOS Runtime` | ✅ 直接使用 |
| Tagline (EN) | `A user-owned appeal workflow runtime for an algorithmic world.` | ✅ 直接使用 |
| 一句话简介 (中文) | 一个用户拥有的算法申诉工作流运行时：一次授权后，代理完成提交、补证、追踪与账户状态核验。 | ✅ 留档 |
| Primary track | `The Taskmaster` | ✅ 直接使用 |
| Repository | `[REPOSITORY_URL]`（提交前由用户/工程师回填公开仓库地址） | ⚠️ 待回填 |
| Demo video URL | `[DEMO_VIDEO_URL]`（YouTube/Vimeo/Drive 外链，提交前由用户上传后回填） | ⚠️ 待回填 |

---

## 1. Devpost 文本字段 · English master copy

以下内容可直接粘贴到 Devpost。所有 `[BRACKETED]` 项为待工程师/设计师/用户回填的占位项。

### 1.1 Short problem overview

Automated platform decisions can suspend a delivery rider's account and cut off income before the person understands the allegation, the deadline, or which evidence matters. The affected person is then expected to reconstruct the case through a short notice and a contextless appeal form. AppealOS turns that fragmented, deadline-driven process into one durable, user-owned workflow with a bounded autonomous agent.

### 1.2 Value proposition

AppealOS is a user-owned appeal workflow runtime. After one scoped `AppealMandate`, the agent submits the appeal, responds to one authorized evidence request, tracks the platform response, and verifies the final account state directly — so a person gets a clear outcome without rebuilding the case at every step.

### 1.3 Text description

**The problem**

A delivery rider, seller, creator, or developer can lose an account, income, audience, or funds because of an automated fraud signal, identity failure, unexplained complaint, or moderation mistake. The information needed to respond — the allegation, policy rules, deadlines, receipts, GPS traces, and device logs — is fragmented across email, help pages, and account history. The missing product is not a better appeal-letter generator; it is a persistent workflow that carries one case from notice to a verified outcome.

**What AppealOS does**

AppealOS joins a platform suspension notice, user-directed evidence, policy rules, deadlines, and scoped authorization into an executable `AppealCase`. After one bounded approval, the agent performs the full external action loop: submit the appeal, handle one authorized supplement request, track the response, and verify the final account state.

**The 48-hour proof**

The hackathon scope is deliberately narrow and fully synthetic. A fictional delivery platform called **MockDrop** suspends Rider R-2048 for `ABNORMAL_LOCATION`. AppealOS parses the notice, asks the user to consent to analyzing exactly three evidence artifacts (one delivery receipt, one GPS trace, one device log), builds a citation-backed timeline, maps it to a frozen policy profile, and asks the user to approve a bounded `AppealMandate`. The deterministic demo reveals that a cellular-network handoff was mistaken for location fraud. AppealOS submits the appeal, receives one asynchronous request for the device log, supplies it within the mandate, then calls MockDrop's account-status endpoint separately before declaring success: `SUSPENDED → SUPPLEMENT_REQUESTED → APPROVED → ACTIVE`.

**Why it is agentic**

AppealOS is not organized around a chat box. Its value comes from durable state and external action: background execution after approval, ADK tools that read approved artifacts and write to MockDrop, Firestore as the durable workflow authority, a scoped `AppealMandate` that limits destination, evidence, actions, supplement count, and expiry, and distinct events for submission, acknowledgement, decision, and verified account state.

**Safety model: models interpret, code authorizes**

AppealOS separates internal analysis from external action. `AnalysisConsent` allows processing selected artifacts; it cannot disclose evidence or contact a platform. `AppealMandate` allows one named destination and evidence set; it cannot contact a new recipient, add a new claim, or disclose a new evidence class. Gemini proposes structured facts and tools, while deterministic code controls deadlines, permissions, transitions, idempotency, and writes. Revocation blocks actions that have not started dispatching.

**Status and honesty**

The rescue slice is live on Google Cloud: MockDrop provides a Node.js HTTP API with deterministic appeal/account transitions, stable request and response hashes, idempotent replay, receipt recovery, and seven passing integration tests; the AppealOS FastAPI service runs a real Google ADK root agent over `gemini-3.5-flash` and completes `reset → notice → consent → mandate → submit → supplement → verify ACTIVE` against the deployed MockDrop. Firestore persistence, Pub/Sub connection, the Evidence Vault, and the UI are explicitly **planned**. Nothing in this submission claims a live DoorDash, Uber, TikTok, Amazon, GitHub, or other platform integration.

### 1.4 Features and functionality

- **Structured notice intake**: parses only the allowlisted synthetic notice into allegation type, incident window, normalized deadline, and confidence; uncertain parses pause for user review.
- **Two-level user consent**: `AnalysisConsent` for internal evidence processing; a separate scoped `AppealMandate` for external action.
- **Encrypted Evidence Vault prototype**: three synthetic artifacts stored as AES-256-GCM ciphertext with plaintext/ciphertext hashes, nonce, and AAD; hash mismatch quarantines the artifact.
- **Citation-backed timeline**: every drafted claim references an artifact ID, plaintext hash, and exact source span; causal and low-confidence claims require user confirmation.
- **Versioned policy profile**: appeal claims map to a frozen MockDrop policy profile with clause IDs.
- **Bounded external action**: one initial appeal submission, one authorized supplement, polling, and direct account-state verification under a single mandate.
- **Asynchronous supplement handling**: reacts to one Pub/Sub supplement event without another user prompt when it fits the mandate; replay does not produce a duplicate platform action.
- **Receipt-before-celebration state machine**: distinguishes `SUBMITTED`, `ACKNOWLEDGED`, `DECIDED_APPROVED`, and directly verified `ACCOUNT_ACTIVE`.
- **Action timeline**: records actor, time, correlation ID, case version, event hash, and receipt references without exposing raw evidence or tokens.
- **Due Process Audit Export**: downloads a redacted, hash-consistent JSON case record for human escalation.
- **Deterministic safety guards**: model output cannot authorize actions or write case state; destination, method, path, evidence fields, byte limits, deadlines, and idempotency are enforced in code.
- **Local verified slice today**: MockDrop reset/account/appeal/supplement/decision/receipt APIs with seven HTTP integration tests and an optional local bearer-token write guard.

### 1.5 Technologies used

- **Gemini 3.5+** (`gemini-3.5-flash`, Vertex AI `global` endpoint): structured notice extraction, evidence relevance, policy-to-fact matching, response classification, and grounded drafting. The model interprets; it does not authorize actions or write case state.
- **Google ADK**: root agent, typed tools, before-tool authorization callbacks, and after-tool receipt capture.
- **Cloud Run**: two deployed rescue services — `appealos` (https://appealos-agrdlgr4ea-uc.a.run.app) and `mockdrop` (https://mockdrop-agrdlgr4ea-uc.a.run.app) — each with separate service identities. The compiled UI is planned.
- **Firestore**: durable workflow authority for the case, mandate, receipts, and event history (planned for cloud).
- **Cloud Storage + Secret Manager**: encrypted synthetic evidence and demo key storage (planned for cloud).
- **Cloud Pub/Sub**: `mockdrop-platform-events` for the P0 supplement/decision event path (planned).
- **Cloud Logging**: redacted metadata and structured logs without raw evidence or secrets.
- **Node.js**: implemented local MockDrop API and integration tests.
- **Python FastAPI + React**: FastAPI/ADK service implemented; React UI planned.
- **MockDrop**: a synthetic simulation platform, not a real integration or independent adjudicator.

### 1.6 Other data sources used

AppealOS uses only synthetic fixtures and public references. It does not ingest real user data.

- Synthetic fixtures: one packaged suspension notice, one frozen MockDrop policy profile, and three synthetic evidence artifacts.
- All Things Agentic Hackathon official rules.
- Seattle App-Based Worker Deactivation Rights Ordinance and Seattle Office of Labor Standards deactivation intake.
- DoorDash deactivation appeal guide (public product-documentation reference).
- Human Rights Watch, *The Gig Trap* (2025) — public report informing the problem.
- Google Cloud documentation on hosting AI agents on Cloud Run and deploying an ADK agent to Cloud Run.

### 1.7 Findings and learnings

- The hardest part is not drafting a persuasive appeal; it is durable case state and a trustworthy authorization boundary.
- Splitting `AnalysisConsent` from `AppealMandate` made the product safe to demonstrate: internal reading and external writing are separable, revocable permissions.
- Deterministic authorization matters more than model prompt engineering: deadlines, mandate scope, idempotency, and receipts must live in code, not in the model's memory.
- Exactly-once external action requires an idempotency key created before dispatch plus receipt recovery by key after an uncertain write.
- Platform acknowledgement, approval text, and restored account access are different facts; the demo only declares success after a direct account-status call returns `ACTIVE`.
- A cooperative synthetic platform is a legitimate way to prove an external state machine while being explicit that it is not a live-platform integration.

---

## 2. 中文留档底稿 / Chinese archive copy

> 以下为中文留档版本，非 Devpost 提交主版本。

### 2.1 问题概述（短）

平台算法可以在当事人还没弄清楚指控、期限与关键证据之前，就冻结外卖骑手账户、切断收入。当事人只能通过一段简短通知和一张脱离上下文的申诉表单重建案情。AppealOS 把这个碎片化、被期限驱动的过程，变成一个有边界代理的用户拥有的持久工作流。

### 2.2 价值主张

AppealOS 是用户拥有的申诉工作流运行时。用户只需签发一次受限的 `AppealMandate`，代理就会完成申诉提交、处理一次已授权的补证请求、追踪平台回复，并直接核验最终账户状态——用户不必在每一步都重新拼装案情。

### 2.3 项目详细描述

**问题**

外卖骑手、卖家、创作者或开发者可能因为自动化风控信号、身份校验失败、未解释的投诉或审核误判，失去账户、收入、受众或资金。而申诉所需的信息——指控、政策、期限、收据、GPS 轨迹、设备日志——散落在邮件、帮助页与账户历史中。缺的不是一封更好的申诉信生成器，而是一个能把一个案件从通知推进到可核验结果的持久工作流。

**AppealOS 做什么**

AppealOS 把平台停权通知、用户指定证据、政策规则、期限和受限授权，组合成可执行的 `AppealCase`。在一次性边界授权之后，代理完成完整外部行动闭环：提交申诉、处理一次已授权补证、追踪回复、直接核验最终账户状态。

**48 小时验证**

黑客松范围刻意收窄且完全使用合成数据。虚构配送平台 **MockDrop** 以 `ABNORMAL_LOCATION` 冻结骑手 R-2048。AppealOS 解析通知，请求用户同意分析恰好三份证据（配送收据、GPS 轨迹、设备日志），构建带引用的事实时间线，匹配冻结的政策档案，并请用户批准受限的 `AppealMandate`。确定性演示揭示：一次蜂窝网络切换被误判为位置欺诈。AppealOS 提交申诉、收到一次设备日志补证请求、在授权范围内提交补证，再单独调用 MockDrop 的账户状态接口核验后才宣布成功：`SUSPENDED → SUPPLEMENT_REQUESTED → APPROVED → ACTIVE`。

**为什么是代理**

AppealOS 不围绕聊天框组织。其价值来自持久状态与外部行动：授权后的后台执行、读写 MockDrop 的 ADK 工具、作为持久工作流权威的 Firestore、限定目标/证据/动作/补证次数/有效期的 `AppealMandate`，以及区分提交、确认、决策与已核验账户状态的不同事件。

**安全模型：模型解释，代码授权**

AppealOS 把内部分析与外部行动分离。`AnalysisConsent` 只能处理已选证据，不能披露证据或联系平台；`AppealMandate` 只能写入指定目标与证据集，不能新增收件方、新增主张或披露新证据类别。Gemini 提出结构化事实与工具调用，确定性代码控制期限、权限、状态迁移、幂等与写入。撤销授权会阻止尚未进入派发状态的动作。

**状态与诚实声明**

救援切片已在 Google Cloud 跑通：MockDrop 提供 Node.js HTTP API，包含确定性申诉/账户状态流转、稳定请求与响应哈希、幂等重放、回执恢复，以及 7 个通过的集成测试；AppealOS FastAPI 服务通过 Google ADK 根代理与 `gemini-3.5-flash` 完成 `reset → notice → consent → mandate → submit → supplement → verify ACTIVE`，并调用已部署的 MockDrop。Firestore 持久化、Pub/Sub 连接、Evidence Vault 与 UI 明确标记为 **planned**。本提交不声称存在 DoorDash、Uber、TikTok、Amazon、GitHub 或任何真实平台集成。

### 2.4 功能与能力

- **结构化通知解析**：仅解析白名单内的合成通知，产出指控类型、事件窗口、标准化期限与置信度；不确定时暂停待用户复核。
- **两级用户同意**：`AnalysisConsent` 用于内部证据处理；独立的受限 `AppealMandate` 用于外部行动。
- **加密证据库原型**：三份合成证据以 AES-256-GCM 密文保存，含明文/密文哈希、nonce 与 AAD；哈希不匹配即隔离。
- **带引用的事实时间线**：每一条草拟主张都引用证据 ID、明文哈希与精确来源片段；因果与低置信主张需用户确认。
- **版本化政策档案**：申诉主张映射到冻结的 MockDrop 政策条款 ID。
- **受限外部行动**：单次申诉提交、单次已授权补证、轮询与账户状态直接核验，全部在同一授权下完成。
- **异步补证处理**：在授权范围内，无需再次提示即可响应一次 Pub/Sub 补证事件；重放不会产生重复平台动作。
- **先有回执再庆祝**：区分 `SUBMITTED`、`ACKNOWLEDGED`、`DECIDED_APPROVED` 与直接核验的 `ACCOUNT_ACTIVE`。
- **行动时间线**：记录行为主体、时间、关联 ID、案件版本、事件哈希与回执引用，不暴露原始证据或令牌。
- **Due Process 审计导出**：下载脱敏、哈希一致的 JSON 案件记录，用于人工升级。
- **确定性安全护栏**：模型输出不能授权动作或写案件状态；目标、方法、路径、证据字段、字节上限、期限与幂等由代码强制。
- **当前本地已验证切片**：MockDrop 的 reset/account/appeal/supplement/decision/receipt API、7 个 HTTP 集成测试与可选本地 bearer-token 写保护。

### 2.5 使用技术

- **Gemini 3.5+**（`gemini-3.5-flash`，Vertex AI `global` endpoint）：结构化通知抽取、证据相关性、政策与事实匹配、回复分类与有依据的起草。模型只解释，不授权动作或写案件状态。
- **Google ADK**：根代理、类型化工具、工具调用前授权回调、工具调用后回执捕获。
- **Cloud Run**：两个已部署救援服务——`appealos`（https://appealos-agrdlgr4ea-uc.a.run.app）与 `mockdrop`（https://mockdrop-agrdlgr4ea-uc.a.run.app），各自使用独立服务身份；编译后 UI 仍为 planned。
- **Firestore**：案件、授权、回执与事件历史的持久工作流权威（cloud 阶段 planned）。
- **Cloud Storage + Secret Manager**：加密合成证据与演示密钥存储（cloud 阶段 planned）。
- **Cloud Pub/Sub**：P0 补证/决策事件路径的 `mockdrop-platform-events`（planned）。
- **Cloud Logging**：脱敏元数据与结构化日志，不含原始证据或密钥。
- **Node.js**：已实现的本地 MockDrop API 与集成测试。
- **Python FastAPI + React**：FastAPI/ADK 服务已实现；React UI 仍为 planned。
- **MockDrop**：合成模拟平台，不是真实集成，也不是独立裁决者。

### 2.6 使用的其他数据源

AppealOS 只使用合成 fixture 与公开参考资料，不摄取真实用户数据。

- 合成 fixture：一份打包的停权通知、一份冻结的 MockDrop 政策档案、三份合成证据。
- All Things Agentic Hackathon 官方规则。
- 西雅图 App-Based Worker Deactivation Rights Ordinance 与西雅图劳工标准办公室停权受理页面。
- DoorDash 停权申诉指南（公开产品文档参考）。
- 人权观察《The Gig Trap》（2025）：用于理解问题的公开报告。
- Google Cloud 关于在 Cloud Run 上托管 AI 代理与部署 ADK 代理的官方文档。

### 2.7 发现与心得

- 最难的不是写一封有说服力的申诉信，而是持久的案件状态与可信的授权边界。
- 把 `AnalysisConsent` 与 `AppealMandate` 分开，让产品可安全演示：内部读取与外部写入是可分离、可撤销的权限。
- 确定性授权比模型提示词工程更重要：期限、授权范围、幂等与回执必须放在代码里，而不是模型的记忆里。
- 精确一次的外部动作，需要派发前生成的幂等键，以及在不确定写入后按幂等键恢复回执。
- 平台确认、批准文案与账户恢复是不同的事实；演示只有在账户状态接口直接返回 `ACTIVE` 后才宣布成功。
- 合作式合成平台是证明外部状态机的合法方式，同时要明确它不是真实平台集成。

---

## 3. 提交 checklist / Submission checklist

### 提交前必查 / Must-do before submit

- [ ] `SUBMISSION.md` 已与 `README.md`、`docs/PRD.md`、`docs/TECHNICAL_DESIGN.md` 对齐，无未实现组件被写成已实现。
- [ ] Devpost 七个文本字段已从 English master copy 粘贴：Short problem overview、Value proposition、Text description、Features and functionality、Technologies used、Other data sources used、Findings and learnings。
- [ ] `Technologies used` 已点名 Gemini 3.5+、Google ADK、Cloud Run；MockDrop 已标注为合成模拟平台。
- [ ] 工程师回填 `[DEPLOYED_APPEALOS_URL]` 与 `[DEPLOYED_MOCKDROP_URL]` 后再更新 Cloud Run 相关文案。
- [ ] 工程师回填确切 Gemini model ID、endpoint、region 与 ADK version（部署 smoke test 后）。
- [ ] 用户回填 `[REPOSITORY_URL]` 与 `[DEMO_VIDEO_URL]`。
- [ ] 仓库公开可见且未提交 `.env`、`.pem`、`.key` 或任何 API key。
- [ ] 演示视频 ≤ 4 分钟，且展示 Gemini、ADK、Cloud Run、Pub/Sub 与外部状态变化证据。
- [ ] README 的 `Submission / Devpost` 小节与 `SUBMISSION.md` 一致；如与工程师 README 改动冲突，以本 `SUBMISSION.md` 为准。

### 回填项 / Placeholders to backfill

| 占位项 / Placeholder | 责任方 / Owner | 位置 / Where |
|---|---|---|
| `[REPOSITORY_URL]` | 用户/工程师 | `SUBMISSION.md` §0 |
| `[DEMO_VIDEO_URL]` | 用户/设计师 | `SUBMISSION.md` §0、§1.5 |
| `[DEPLOYED_APPEALOS_URL]` | 工程师 | 已回填：https://appealos-agrdlgr4ea-uc.a.run.app |
| `[DEPLOYED_MOCKDROP_URL]` | 工程师 | 已回填：https://mockdrop-agrdlgr4ea-uc.a.run.app |
| `[GEMINI_MODEL_ID]` + endpoint/region | 工程师 | 已回填：`gemini-3.5-flash` / Vertex AI `global` |
| `[ADK_VERSION]` | 工程师 | 已回填：`google-adk==2.8.0` |

---

## 4. 链接汇总 / Link summary

| 材料 / Material | 路径或链接 / Path or URL | 状态 / Status |
|---|---|---|
| Devpost 全字段底稿 | `SUBMISSION.md`（本文件） | ✅ 已产出 |
| 产品需求 | `docs/PRD.md` | ✅ 已存在 |
| 技术设计 | `docs/TECHNICAL_DESIGN.md` | ✅ 已存在 |
| 项目 README | `README.md` | ✅ 已存在，本次补充 Submission 小节 |
| 4 分钟演示视频脚本大纲 | `docs/DEMO_SCRIPT.md` | ✅ 本次产出 |
| 加分项公开内容 / 社交帖 | `docs/SOCIAL_POSTS.md` | ✅ 本次产出 |
| MIT License | `LICENSE` | ✅ 本次新增 |
| 已实现本地切片 | `apps/mockdrop/` | ✅ 已存在 |
| 交互线框 | `docs/assets/appealos-runtime-wireframe.png` | ✅ 已存在 |
| 公开仓库 / 视频外链 | 见 §3 回填项 | ⚠️ 待回填 |
