# AppealOS · 4 分钟演示视频脚本大纲

> 用途：交设计师做分镜与剪辑。总时长 **≤ 4:00**（评审硬性要求）。
> 事实边界：仅展示「已实现（本地 MockDrop）」与「部署后已核验（deployed）」的内容；任何未部署组件必须配 `planned` 标注，不得误导为已上线。
> 待回填：`[GEMINI_MODEL_ID]`、`[ADK_VERSION]`、`[DEPLOYED_APPEALOS_URL]`、`[DEPLOYED_MOCKDROP_URL]`。

## 全片主线 / Narrative spine

一次授权 → 完整外部行动闭环：提交申诉 → 收到补证 → 在授权内自动补证 → 直接核验账户恢复。每段结尾都点「模型解释，代码授权」的安全边界。

---

## 01 · 问题 / Problem（0:00–0:30，30s）

**画面 / Visuals**
- 黑屏快速切入手机通知：`Your account has been suspended`。
- 切到骑手/创作者站在空荡接单界面前，收入归零的紧张感。
- 三张碎片卡片：邮件通知、帮助页条款、乱糟糟的证据文件夹。
- 屏幕文案大字：`You lost income. Now prove you didn't do it.`

**旁白 / Narration cue（EN）**
"One automated decision can suspend your account and cut off your income — before you even understand the allegation, the deadline, or which evidence matters. And you are expected to rebuild that case through a contextless form."

**中文提示**
"一次自动化决定就能冻结你的账户、切断收入——而你还不知道指控是什么、期限是什么、哪些证据重要。你只能靠一张脱离上下文的表单重头拼装案情。"

**安全注记 / Safety note**
- 不出现任何真实平台 Logo 或名称；仅出现「MockDrop（模拟平台）」。
- 如用真实截图，必须打码平台名与个人信息。

---

## 02 · 价值主张 / Value proposition（0:30–1:00，30s）

**画面 / Visuals**
- 一个居中线框/界面轮廓，四周自动拼上：通知、证据、政策、期限、授权、回执。
- 显示一句产品标语：`After one approval, the agent finishes the loop.`
- 三个关键词依次弹出：`Scoped autonomy` / `Durable state` / `Verified outcome`。

**旁白 / Narration cue（EN）**
"AppealOS is a user-owned appeal workflow. You grant one scoped mandate — and the agent submits the appeal, handles one authorized evidence request, tracks the response, and verifies the final account state. Not a better letter generator. A persistent case that finishes the job."

**中文提示**
"AppealOS 是用户拥有的申诉工作流。你只授予一次受限授权，代理就完成提交、补证、追踪与最终账户状态核验。它不是更好的申诉信生成器，而是一个把案件跑完的持久工作流。"

**安全注记 / Safety note**
- `one scoped mandate` 必须与画面中「授权范围」卡片呼应，避免被理解成无限权限。

---

## 03 · App 在行动 / App in action（1:00–3:00，120s）

> 这一段是核心，按产品六步信息层级推进。建议使用 `docs/assets/appealos-runtime-wireframe.png` 的线框风格做关键界面占位。

### 3.1 接入 / Notice intake（约 0:15）

**画面 / Visuals**
- 顶部状态条：`NOTICE_RECEIVED → PARSED`。
- 左侧展示合成停权通知；右侧是解析出的字段卡：`allegation: ABNORMAL_LOCATION`、`deadline`、`incident window`、`confidence`。

**旁白 / Narration cue（EN）**
"First, AppealOS reads the allowlisted synthetic notice and extracts the allegation, incident window, and deadline into a typed result. Uncertain parses pause for user review."

**中文提示**
"AppealOS 先读取白名单内的合成通知，把指控、事件窗口和期限解析成结构化结果。不确定的解析会暂停等待用户复核。"

### 3.2 证据同意 / Analysis consent（约 0:15）

**画面 / Visuals**
- 三张证据卡：`delivery receipt`、`GPS trace`、`device log`，均标注 hash 与 `synthetic`。
- 用户点击 `Approve analysis only`；画面明确出现红色边界：`Analysis ≠ disclosure`。

**旁白 / Narration cue（EN）**
"You approve analysis of exactly three synthetic artifacts. This consent allows internal processing only — it cannot disclose evidence or contact a platform."

**中文提示**
"你同意分析恰好三份合成证据。这个同意只允许内部处理——不能披露证据，也不能联系平台。"

### 3.3 时间线与主张 / Timeline & claims（约 0:20）

**画面 / Visuals**
- 自动生成带引用的事实时间线；每条主张旁显示 `artifact ID + exact span`。
- 一条 `CAUSAL_EXPLANATION` 主张弹出 `Requires user confirmation`。

**旁白 / Narration cue（EN）**
"AppealOS builds a citation-backed timeline and maps the facts to a frozen policy profile. Causal and low-confidence claims must be confirmed by you."

**中文提示**
"AppealOS 构建带引用的事实时间线，并把事实映射到冻结的政策档案。因果与低置信主张必须由你确认。"

### 3.4 授权 / Appeal Mandate（约 0:20）

**画面 / Visuals**
- 授权预览卡列出：`destination: mockdrop`、`approved claims`、`evidence rules`、`supplement limit: 1`、`expiry: 72h`。
- 用户点击 `Approve mandate`；一次明显的手势，代表「唯一一次外部行动授权」。

**旁白 / Narration cue（EN）**
"Now you approve one bounded AppealMandate: one destination, named claims, three evidence rules, one supplement cycle, and an expiry. New recipients, new claims, or new evidence require a new mandate."

**中文提示**
"现在你批准一份受限的 AppealMandate：一个目标、已命名主张、三份证据规则、一次补证周期和一个有效期。新的收件方、新主张或新证据都需要新的授权。"

### 3.5 提交与回执 / Submit & receipts（约 0:15）

**画面 / Visuals**
- 状态条推进：`SUBMISSION_PENDING → ACKNOWLEDGED`。
- 弹出 `PlatformReceipt`：`receipt ID`、`request hash`、`idempotency key`、`timestamp`。

**旁白 / Narration cue（EN）**
"The agent submits through the typed MockDrop adapter with an idempotency key. Submission and acknowledgement are recorded as separate, receipt-backed events."

**中文提示**
"代理通过类型化的 MockDrop 适配器提交，并携带幂等键。提交与平台确认被记录为两个独立、带回执的事件。"

### 3.6 补证闭环 / Asynchronous supplement（约 0:20）

**画面 / Visuals**
- 右下角弹出 Pub/Sub 事件：`SUPPLEMENT_REQUESTED`（请求设备日志）。
- 系统自动检查授权约束后显示 `AUTO_SUPPLEMENT_ALLOWED`，无需再次点击。
- 状态条推进到 `SUPPLEMENTED`。

**旁白 / Narration cue（EN）**
"MockDrop requests one supplement: the device log. Because it is inside the mandate, AppealOS responds without another prompt. Replaying the same event never produces a duplicate action."

**中文提示**
"MockDrop 请求一次补证：设备日志。因为它在授权范围内，AppealOS 无需再次提示即可响应。重放同一事件不会产生重复动作。"

### 3.7 直接核验 / Verified outcome（约 0:15）

**画面 / Visuals**
- 状态条：`DECIDED_APPROVED`，但画面故意停顿——还未庆祝。
- 出现独立调用 `GET /v1/accounts/{accountId}` 返回 `ACTIVE` 的镜头。
- 只有此时才显示 `ACCOUNT_ACTIVE` + 绿色完成态。

**旁白 / Narration cue（EN）**
"Approval text is not restored access. AppealOS calls MockDrop's account-status endpoint directly, and only closes the case when it observes ACTIVE."

**中文提示**
"批准文案不等于账户恢复。AppealOS 直接调用 MockDrop 的账户状态接口，只有观察到 ACTIVE 才会结案。"

---

## 04 · Google Cloud 证据 / Google Cloud evidence（3:00–3:30，30s）

**画面 / Visuals**
- Cloud Run 控制台：两个服务 `appealos` 与 `mockdrop`，各自独立 origin 与 service identity。
- `/health` 返回卡片：`model: [GEMINI_MODEL_ID]`、`region: [REGION]`、`ADK: [ADK_VERSION]`。
- Pub/Sub 主题 `mockdrop-platform-events` 与补证事件时间线同屏。
- 结构日志卡片：`caseId`、`correlationId`、`receiptId`，无原始证据/密钥。

**旁白 / Narration cue（EN）**
"The working path runs on two separate Cloud Run services. Gemini proposes structured facts; deterministic code authorizes every write. The synchronous demo receives a typed supplement request from MockDrop, while the Pub/Sub consumer is code-complete but not deployed. Structured logs carry IDs and hashes, never raw evidence or secrets."

**中文提示**
"可跑通的路径部署在两个 Cloud Run 服务上。Gemini 提出结构化事实，确定性代码授权每一次写入。同步演示从 MockDrop 收到类型化补证请求；Pub/Sub consumer 已代码完成但尚未部署。结构化日志只含 ID 与哈希，不记录原始证据或密钥。"

**回填 / Backfill**
- 所有 `[BRACKETED]` 字段由工程师在部署 smoke test 后替换为真实截图/录屏。

---

## 05 · 收尾 / Close（3:30–4:00，30s）

**画面 / Visuals**
- 回放三个关键词：`Scoped autonomy` / `Receipts before celebration` / `Failure is still an outcome`。
- 末尾定格在项目名 `AppealOS Runtime` + tagline `A user-owned appeal workflow runtime for an algorithmic world.`。
- 底部小字：`Synthetic MockDrop simulation only. No live-platform integration.`

**旁白 / Narration cue（EN）**
"AppealOS gives ordinary people a tireless digital advocate — one bounded approval, one complete case, one verified outcome. Models interpret. Code authorizes. The user stays in control."

**中文提示**
"AppealOS 给普通人一个永不疲倦的数字辩护人——一次受限授权、一个完整案件、一个可核验的结果。模型解释，代码授权，用户始终掌握控制权。"

---

## 制作检查清单 / Production checklist

- [ ] 总时长 ≤ 4:00，五段时长核对：30s / 30s / 120s / 30s / 30s。
- [ ] 全片任何界面均标注 MockDrop 为合成模拟平台，不出现真实平台集成声明。
- [ ] 至少出现一次「模型解释，代码授权 / Models interpret; code authorizes」的字幕或旁白。
- [ ] 展示 Gemini、ADK、Cloud Run、Pub/Sub 与直接账户状态核验五类证据。
- [ ] 不展示原始证据、坐标、设备标识、密钥、token 或完整提示词。
- [ ] 若画面暂用线框，标注 `UI mockup`，避免被误认为已部署 UI。
- [ ] 结尾保留小字安全声明：合成数据、非真实平台集成、非法律服务。
