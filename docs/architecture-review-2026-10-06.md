# ContractGuardAgent 架构评估

存档日期：2026-10-06

本文保存自当天的 Architecture Review 画布，内容是通读仓库源码、配置、测试、前端和 Kubernetes 清单之后的判断。分数是审阅评分，满分 100，不是覆盖率或性能测量。70 分参考线表示可以交给法务同事试用。

本文记录的是评估当时的代码。同日随后的修改处理了文中列出的缺陷。当前行为以 `README.md` 和代码为准，本文不再更新。

## 结论

演示原型成立，生产法务系统尚未成立。

分层方向适合这个产品：FastAPI 接任务，LangGraph 串审查步骤，SQLite 存规则和任务，静态页做对比。当时真正卡住上线的是三件事：人工审核没有挂起工作流、模型配置互相矛盾、文档描述的能力大多没有接到代码上。

四个维度的主观完成度。横轴是分数（0–100），纵轴是评估维度。70 分竖线是「可以交给法务同事试用」的参考线。来源：2026-10-06 源码审阅。

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 220" role="img" aria-label="四个维度的主观完成度：架构合理性 54 分，文档准确完整 32 分，产品完成度 40 分，工程可维护性 44 分。试用门槛 70 分。">
  <title>四个维度的主观完成度</title>
  <desc>横轴：主观完成度（分，0–100）。纵轴：评估维度。70 分参考线表示可以交给法务同事试用。来源：2026-10-06 源码审阅。</desc>
  <style>
    .label, .tick, .caption { fill: currentColor; font-family: sans-serif; }
    .label { font-size: 13px; }
    .tick { font-size: 11px; opacity: 0.7; }
    .caption { font-size: 11px; opacity: 0.65; }
    .axis { stroke: currentColor; stroke-opacity: 0.25; }
    .bar { fill: #c48a2a; }
    .ref { stroke: #3b82c4; stroke-dasharray: 4 3; }
    .ref-label { fill: #3b82c4; font-size: 11px; font-family: sans-serif; }
  </style>
  <line x1="148" y1="28" x2="148" y2="176" class="axis"/>
  <line x1="148" y1="176" x2="588" y2="176" class="axis"/>
  <line x1="456" y1="28" x2="456" y2="176" class="ref"/>
  <text x="460" y="22" class="ref-label">试用门槛 70</text>
  <text x="28" y="58" class="label">架构合理性</text>
  <rect x="148" y="42" width="237.6" height="22" class="bar"/>
  <text x="392" y="58" class="label">54</text>
  <text x="28" y="96" class="label">文档准确完整</text>
  <rect x="148" y="80" width="140.8" height="22" class="bar"/>
  <text x="296" y="96" class="label">32</text>
  <text x="28" y="134" class="label">产品完成度</text>
  <rect x="148" y="118" width="176" height="22" class="bar"/>
  <text x="332" y="134" class="label">40</text>
  <text x="28" y="172" class="label">工程可维护性</text>
  <rect x="148" y="156" width="193.6" height="22" class="bar"/>
  <text x="348" y="172" class="label">44</text>
  <text x="148" y="196" class="tick">0</text>
  <text x="360" y="196" class="tick">50</text>
  <text x="568" y="196" class="tick">100</text>
  <text x="148" y="214" class="caption">横轴：主观完成度（分）</text>
</svg>

| 维度 | 审阅评分 |
| --- | --- |
| 架构合理性 | 54 |
| 文档准确完整 | 32 |
| 产品完成度 | 40 |
| 工程可维护性 | 44 |

## 优先处理的问题

| 优先级 | 问题 | 用户会看到什么 | 落点 |
| --- | --- | --- | --- |
| P0 | 人工审核闭环断裂 | 黄/红项直接出最终报告，审核表单到不了 | `graph/nodes.py`、`routes.py` |
| P0 | 模型开关和提供方不一致 | 打开 LLM 后可能去调一个 Ollama 上不存在的 `gpt-4o-mini` | `config.yaml`、`nodes.py`、`llm.py` |
| P0 | 上传声称支持 Word/PDF | docx、pdf 会被当成乱码文本解析 | `routes.py` upload |
| P1 | 数据库路径写死 | Kubernetes 的数据卷挂上了，重启后任务仍可能丢 | `rag/db.py` 与 k8s PVC |
| P1 | 文档与接口不一致 | 按 README 调 `/api/tasks` 会 404，认证也不存在 | `README.md` |
| P1 | 图在请求线程里同步跑完 | 一份长合同会堵住整个进程的其他请求 | `routes.py` 与 `workflow.invoke` |
| P2 | 检索到的模板没有参与评估 | RAG 召回了模板，风险判断仍只看关键词或 LLM | `nodes.py` evaluator |
| P2 | 依赖声明和代码脱节 | 缺 pyyaml、numpy；SQLAlchemy 声明了却没用 | `requirements.txt` |

## 已经站住的部分

任务会写入 SQLite，进程重启后已完成的记录还在。规则库预置了 5 类合同、16 条合规规则，关键词打分在关闭 LLM 时能跑通。前端有文本对比、示例合同、状态轮询和结果页。Docker 与 Kubernetes 清单齐全，健康检查探针已接上。这些足够支撑一场演示。

## 架构

目录划分是合理的：`app/api` 对外，`app/graph` 管审查步骤，`app/rag` 管规则和全文检索，`app/services` 管模型，`static` 管页面。对「两份合同进、一份风险报告出」这个范围，LangGraph 的五节点流水线比一个大函数更清楚。问题出在节点之间的数据没有形成闭环，以及配置、持久化、部署各说各话。

| 层 | 代码现状 | 判断 |
| --- | --- | --- |
| API | 对比、上传、状态、结果、重试、提交审核 | 接口面够用，审核提交后会整图重跑 |
| LangGraph | retriever → analyzer → evaluator → human 或 finalizer | 一次 invoke 跑完，没有中断和检查点 |
| RAG | SQLite FTS5，可选逐条 OpenAI 向量 | 没有向量库；召回的模板未进入评估 |
| LLM | 只封装了 ChatOllama | 配置文件里的模型名和开关没有被评估节点读取 |
| 持久化 | tasks 表把差异和评估存成 JSON | 已落库的任务能恢复；进行中的协程不能恢复 |
| 部署 | Dockerfile + Deployment/Service/Ingress/Ollama | 探针可用；数据卷路径与代码不一致 |

### 工作流实际怎么跑

`run_contract_review` 每次都从空的 `human_reviews` 启动。评估节点若看到黄灯或红灯，会把内存状态标成 `waiting_human`，随即进入人工节点。人工节点发现没有任何审核意见，就把 `continue_review` 设为真，轮次加一，回到评估。三轮之后直接进入收尾，状态写成 `completed`。数据库只在开始时写成 `in_progress`，结束时写成最终状态，中间的 `waiting_human` 不会落库。结果页只在状态为 `waiting_human` 时渲染审核表单，所以正常路径下审核表单不会出现。`POST /api/contracts/review` 又要求当前状态必须是 `waiting_human`，因此这条接口在正常运行中到不了。即便强行写入审核意见，下一次 `invoke` 也不会把这些意见放进初始状态。

### 模型与数据库配置

评估节点用环境变量 `USE_LLM` 决定是否调用模型，不读 `config.yaml` 的 `use_llm`。模型客户端只创建 `ChatOllama`，模型名却来自配置。本地 `config.yaml` 把模型写成 `gpt-4o-mini`、`use_llm: false`。代码默认值是 Ollama 的 `llama3.2` 且默认开启。Kubernetes ConfigMap 又是 `llama3.2`，并把数据库指到 `/data/contracts.db`。`rag/db.py` 把库路径写死在 `app/data/contracts.db`，配置里的 `database.path` 从未被读取，持久卷因此接不住任务数据。

| 来源 | 模型 | 是否调用 LLM | 数据库路径 |
| --- | --- | --- | --- |
| `config.py` 默认 | llama3.2 / Ollama | true | `app/data/contracts.db` |
| `config.yaml` | gpt-4o-mini | false（节点不读） | `app/data/contracts.db` |
| k8s ConfigMap | llama3.2 | true（节点不读） | `/data/contracts.db` |
| 运行时实际 | yaml 覆盖后的名字 + ChatOllama | 只看 `USE_LLM` | 写死 `app/data` |

### RAG 在图里的位置

检索节点用修改稿前 500 字做全文检索，取出模板和规则。评估节点只用规则做关键词计分，模板字段之后没有读者。语义检索在 `USE_EMBEDDINGS=true` 时对每条规则现场嵌入，没有索引、没有缓存。默认关闭。对 16 条规则，全文检索足够；把它称为向量库（README 写了 Chroma/FAISS）会让后续的人按错误的存储去改。

## 文档

仓库里有三份说明：`README.md`（英文产品介绍和部署）、`AGENTS.md`（中文开发清单）、`STAR_introduction.md`（项目陈述）。没有架构说明、没有数据字典、没有运维排障、没有 `LICENSE` 文件。`AGENTS.md` 里的任务大多勾选完成，其中「优化 playbook 规则匹配」和「集成测试 / 覆盖率 > 60%」仍未完成。README 末尾指向 `AGENTS.md` 的链接写成了一个搜索引擎 URL。

### README 与代码的差异

| 文档表述 | 代码实际 | 影响 |
| --- | --- | --- |
| 接口需要认证 | 没有任何鉴权中间件 | 敏感合同文本对能访问端口的人开放 |
| `POST /api/tasks/{id}/review` | `POST /api/contracts/review` | 按文档集成会 404 |
| `GET /api/tasks/{id}` | `GET /api/contracts/status` 与 `/result` | 状态和结果是两条路径 |
| 向量库 Chroma 或 FAISS | SQLite FTS5 | 检索方案被写错 |
| 健康检查包含 LLM 连通性 | `/health` 只返回固定 JSON | 探针绿不代表模型可用 |
| Dockerfile 多阶段构建 | 单阶段 `python:3.10-slim` | 镜像说明失真 |
| 默认模型 llama3.2，温度 0.1 | yaml 为 gpt-4o-mini，温度 0.3，且默认不调用 | 按文档配环境会对不上 |
| MIT 许可证，见 LICENSE | 仓库中没有 LICENSE | 对外分发时许可不清 |

README 的 AI 栈是 LangChain + Ollama。`AGENTS.md` 写成 LangChain + OpenAI，并把 `OPENAI_API_KEY` 标成已完成。`STAR_introduction.md` 同时承诺离线 Ollama 和可选 OpenAI，还写了「通过全部单元测试」。测试当时是健康检查、创建任务、404，没有断言差异内容、风险等级或人工审核。陈述稿适合对外介绍意图，不适合当作实现规格。

补文档时先改 README：把接口表、配置示例和项目结构改成与 `routes.py`、`config.yaml`、`db.py` 一致。架构图和数据流可以后补。在代码行为稳定之前，单独再写一份长设计文档会很快再次过期。

## 产品

用户可以粘贴两段合同或点「加载示例合同」，选择采购、服务、租赁、劳动、保密五类之一，提交后轮询状态，在结果页看到绿 / 黄 / 红计数和一份 Markdown 报告。关闭模型时，报告来自 16 条关键词规则和相似度启发式。这个路径对演示是完整的。

上传框接受 `.docx` 和 `.pdf`，服务端只按 UTF-8 或 GBK 解码，二进制合同会变成乱码再去做行级 diff。对比粒度是非空行，合同排版一变就会拆出大量「修改」，条款号、表格和跨行句子对不上。结果页把原文截到约 100 字，没有并排对照，也没有导出。任务没有列表，做完只能靠 URL 上的 `task_id` 找回。

产品说明把人工确认写成主流程：黄灯和红灯要法务点批准或拒绝，意见写进报告。实现里工作流不会停在人工节点，结果页也不会露出审核表单。法务无法留下「谁在何时同意了哪一条」的记录。对合同场景，这比模型文采更关键。

### 产品上值得做的顺序

| 顺序 | 能力 | 为什么先做 |
| --- | --- | --- |
| 1 | 真正停下并恢复人工审核 | 没有这一步，风险灯只是自动结论，不能进法务流程 |
| 2 | Word / PDF 解析，或先从界面去掉这两种格式 | 当前入口会让用户以为复杂合同已支持 |
| 3 | 条款级对照，而不是按行截断 | 法务要看整段原文和修改文，以及改动类型 |
| 4 | 规则库可增删改，并在报告里引用命中的规则 | 16 条种子规则覆盖不了公司自己的 playbook |
| 5 | 任务历史、筛选、失败重试入口 | 重试 API 已有，首页没有任务列表 |
| 6 | 登录、按人隔离合同、导出报告 | 合同文本是敏感数据，演示之后才会成为阻塞项 |

差异检测仍用 `difflib` 按行比对，这作为第一版可以保留。先把解析、停顿审核和对照阅读做好，再考虑版式还原或红线对比。

## 技术

| 项 | 现状 | 改法 | 收益 |
| --- | --- | --- | --- |
| 图的持久化与中断 | `compile()` 无 checkpointer，invoke 一次到 END | 检查点落到 SQLite，在人工节点前 interrupt，审核接口用同一 thread_id resume，并把已提交意见写入 state | 审核闭环、进程重启可续跑 |
| 单一配置入口 | yaml、环境变量、代码默认值三套 | 节点和数据库都读 `get_config()`；模型提供方按 provider 选择 Ollama 或 OpenAI | 本地、Docker、集群行为一致 |
| 后台执行 | `asyncio.create_task` 里同步 invoke，审核接口直接阻塞 | 放到线程池或独立 worker；失败区分可重试错误和输入错误 | 长合同不再堵住健康检查和其他任务 |
| 结构化模型输出 | 手剥 Markdown 代码块再 `json.loads`，失败吞掉 | 用 schema 约束 risk_level / explanation / suggestion，解析失败记入任务 error | 风险等级不会静默掉回黄灯 |
| 检索 | 前 500 字 FTS；向量对 16 条规则逐条现算 | 规则量小就强化关键词和类别过滤；变大再引入本地嵌入和持久向量 | 避免为 16 条规则付嵌入延迟 |
| 依赖与测试 | 无版本钉死；pyyaml、numpy 未声明；SQLAlchemy、aiosqlite 未使用 | 钉版本，补解析与图结果的测试，覆盖人工恢复 | 换机器能装上，改图时能发现回归 |

评估节点和收尾节点在模型调用失败时使用空的 `except`，调用失败和「不该调用」看起来一样。`logging.basicConfig` 在 `main.py` 和 `routes.py` 各调一次。FastAPI 仍使用已弃用的 `on_event("startup")`。重试次数写死在路由里，没有读配置中的 `task.max_retries`。上传没有大小限制。合同原文整段进库，没有脱敏和访问控制。`/health` 不探测 Ollama，Kubernetes 会把一个模型不可用的 Pod 标成就绪。

在规则仍是 16 条、模板仍是 5 篇时，换 Chroma、上重排序模型、或把前端改成 React，对审查质量帮助很小。行级 `difflib` 在纯文本演示里够用；等 Word 解析稳定后，再按条款切块。覆盖率数字可以后补，先补「黄灯必须停在人工节点」和「审核意见出现在最终报告」这两件断言。

保持 FastAPI + LangGraph + SQLite 这套骨架。先把配置、中断恢复和文档对齐，再加文件解析和规则管理。骨架不用推倒。
