# ContractGuardAgent

法务合同对比系统。上传或粘贴两份合同，系统用规则和可选的本地模型标出差异风险；黄灯和红灯会停下来等人工确认，确认意见写进最终报告。

合同文本默认留在本机。模型默认关闭，打开后走 Ollama。需要云端模型时，把 `llm.provider` 设为 `openai`。

## 技术栈

- 后端：FastAPI
- 任务与规则：SQLite（规则全文索引为 FTS5，审查图检查点为 SQLite）
- 工作流：LangGraph，在人工节点用 `interrupt` 暂停
- 模型：Ollama（`langchain-community`）或 OpenAI（`langchain-openai`）
- 前端：HTML / CSS / JavaScript

当前没有登录和鉴权。不要把服务直接暴露到公网。

## 本地运行

需要 Python 3.10+。要用模型时再安装并启动 [Ollama](https://ollama.com/)。

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

浏览器打开 `http://localhost:8000`。

默认 `config.yaml` 里 `use_llm: false`，只走关键词规则，不要求 Ollama 已启动。要启用本地模型：

```yaml
llm:
  provider: "ollama"
  model: "llama3.2"
  base_url: "http://localhost:11434"
  use_llm: true
```

```bash
ollama serve
ollama pull llama3.2
```

环境变量会覆盖配置文件，见 `.env.example`。常用的有 `USE_LLM`、`LLM_PROVIDER`、`LLM_MODEL`、`LLM_BASE_URL`、`DATABASE_PATH`、`OPENAI_API_KEY`。

## Docker

```bash
docker build -t contract-guard:latest .
docker run -p 8000:8000 contract-guard:latest
```

镜像是单阶段构建。容器里的数据库路径以镜像内的 `config.yaml` 为准。

## Kubernetes

```bash
chmod +x k8s/deploy.sh
./k8s/deploy.sh
```

清单把数据库写到 `/data/contracts.db`，持久卷挂在 `/data`。审查图的检查点文件也在这个目录。就绪探针是 `/ready`：开启模型时，Ollama 不可达会返回 503。存活探针仍是 `/health`。

## 接口

这些接口都没有认证。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 进程存活，并附带模型状态 |
| GET | `/ready` | 就绪。模型已开启但连不上时返回 503 |
| POST | `/api/contracts/compare` | JSON：`original_text`、`modified_text`、可选 `category` |
| POST | `/api/contracts/upload` | 表单文件 `original_file`、`modified_file`，可选 `category`。支持 `.txt`、`.md`、`.docx`、`.pdf`，单文件 10MB |
| GET | `/api/contracts/status/{task_id}` | 任务状态 |
| GET | `/api/contracts/result/{task_id}` | 差异、评估和报告 |
| POST | `/api/contracts/review` | 人工确认。仅当状态为 `waiting_human` |
| POST | `/api/contracts/retry/{task_id}` | 只重试 `failed` 任务 |

状态：`pending`、`in_progress`、`waiting_human`、`completed`、`failed`。

有黄灯或红灯时，图会停在人工节点，状态保持 `waiting_human`，重启后仍可提交审核。审核通过后生成报告，意见会出现在对应条目下。全部为绿灯时直接完成。

## 配置

`config.yaml` 是行为配置。数据库路径、是否调用模型、重试次数都从这里读，可用上面的环境变量覆盖。

```yaml
database:
  path: "app/data/contracts.db"

llm:
  provider: "ollama"
  model: "llama3.2"
  temperature: 0.1
  base_url: "http://localhost:11434"
  use_llm: false

embeddings:
  model: "text-embedding-3-small"
  use_embeddings: false

task:
  max_retries: 3
  retry_delay: 2
```

`provider: openai` 时需要 `OPENAI_API_KEY`，模型名用 OpenAI 的模型，例如 `gpt-4o-mini`。

## 项目结构

```text
ContractGuardAgent/
├── app/
│   ├── api/           # 路由
│   ├── config.py      # 配置加载与环境变量覆盖
│   ├── graph/         # LangGraph 状态、节点、中断恢复
│   ├── models/        # 请求和响应模型
│   ├── rag/           # SQLite、FTS 检索、任务表
│   ├── services/      # 模型、报告、文档解析
│   └── main.py
├── docs/            # 历史评估等存档
├── k8s/
├── static/
├── tests/
├── config.yaml
└── requirements.txt
```

## 测试

```bash
pytest
```

## 历史文档

[2026-10-06 架构评估](docs/architecture-review-2026-10-06.md) 是当天源码审阅的存档，记录的是修改前的判断。当前行为以本文和代码为准。

## 许可

MIT，见 `LICENSE`。
