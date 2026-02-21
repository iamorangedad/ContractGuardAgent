# ContractGuardAgent - 法务合同智能对比系统

基于 RAG + LangGraph 的法务合同智能对比系统，采用本地 Ollama 大模型进行合同条款分析。

## 功能特性

- **合同对比分析**: 上传两份合同文本，智能识别差异条款
- **风险评估**: AI 自动评估每项修改的法律风险等级（绿/黄/红）
- **修改建议**: 针对风险条款提供具体的修改建议
- **法务审查工作流**: 支持人工确认和复审流程
- **RAG 知识增强**: 基于法务知识库进行语义检索增强

## 技术架构

- **后端**: FastAPI + SQLite
- **AI 框架**: LangChain + LangGraph
- **LLM**: Ollama (本地部署)
- **工作流**: 状态机驱动的审查流程
- **前端**: 原生 HTML/CSS/JS

## 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Ollama (确保已安装)
ollama serve
ollama pull llama3.2

# 启动应用
python -m app.main
```

访问 http://localhost:8000

### Docker 运行

```bash
docker build -t contract-guard:latest .
docker run -p 8000:8000 contract-guard:latest
```

### Kubernetes 部署

```bash
# 部署到 K8s
chmod +x k8s/deploy.sh
./k8s/deploy.sh
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/contracts/upload` | POST | 上传合同文件 |
| `/api/contracts/compare` | POST | 对比两份合同 |
| `/api/tasks/{task_id}` | GET | 查询任务状态 |
| `/api/tasks/{task_id}/review` | POST | 提交审查意见 |

## 配置说明

配置文件: `config.yaml`

```yaml
app:
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "ollama"
  model: "llama3.2"
  base_url: "http://localhost:11434"
  use_llm: true

database:
  path: "app/data/contracts.db"
```

## 项目结构

```
ContractGuardAgent/
├── app/
│   ├── api/           # API 路由
│   ├── config.py      # 配置管理
│   ├── graph/         # LangGraph 工作流
│   ├── models/        # 数据模型
│   ├── rag/           # RAG 检索模块
│   ├── services/      # LLM 服务
│   └── main.py        # 应用入口
├── k8s/               # K8s 部署配置
├── static/            # 前端静态文件
├── tests/             # 单元测试
├── Dockerfile         # Docker 镜像
└── config.yaml        # 配置文件
```

## 开发计划

See [AGENTS.md](./AGENTS.md)

## 许可证

MIT
