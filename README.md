
---


# ContractGuardAgent - Intelligent Legal Contract Comparison System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com/)

ContractGuardAgent is an intelligent legal contract comparison and review system built on top of **RAG (Retrieval-Augmented Generation)** and **LangGraph**. It leverages locally deployed privacy-safe Large Language Models (via Ollama) to analyze contract clauses, evaluate legal risks, and streamline the legal review workflow.

---

## 🚀 Key Features

*   **Intelligent Contract Comparison**: Upload two versions of a contract (e.g., Original vs. Modified) to instantly pinpoint and isolate modified, added, or deleted clauses.
*   **Automated Risk Assessment**: AI-driven legal risk classification (🟢 Low / 🟡 Medium / 🔴 High) with structured reasoning for every modification.
*   **Actionable Revision Suggestions**: Provides professional, context-aware modification recommendations based on your local legal knowledge base.
*   **Stateful Review Workflow**: Powered by LangGraph, supporting human-in-the-loop (HITL) manual confirmations, multi-stage audits, and re-evaluation.
*   **RAG-Enhanced Precision**: Integrates semantic retrieval over corporate playbooks and standard templates to eliminate LLM hallucinations and align with corporate standards.
*   **Privacy-First & Local**: Process sensitive legal data completely offline using local Ollama models.



---

## 🛠️ Tech Stack

*   **Backend Framework**: FastAPI (Asynchronous Python)
*   **Database**: SQLite (Metadata & Task State), Chroma/FAISS (Vector Store for RAG)
*   **AI & Agent Framework**: LangChain, LangGraph
*   **LLM Provider**: Ollama (Default: `llama3.2`)
*   **UI**: Clean, lightweight native HTML5 / CSS3 / JavaScript

---

## 🏁 Getting Started

### Prerequisites

*   Python 3.10 or higher
*   [Ollama](https://ollama.com/) installed and running

### 1. Local Setup

**Clone the repository:**
```bash
git clone [https://github.com/your-username/ContractGuardAgent.git](https://github.com/your-username/ContractGuardAgent.git)
cd ContractGuardAgent

```

**Install dependencies:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

```

**Set up the LLM:**
Make sure Ollama is running in the background, then pull the required model:

```bash
ollama serve
ollama pull llama3.2

```

**Run the Application:**

```bash
python -m app.main

```

The server will start at `http://localhost:8000`. Open your browser and navigate to this URL to access the UI.

---

### 2. Running with Docker

Easily containerize and run the application without manual environment setup:

```bash
# Build the Docker image
docker build -t contract-guard:latest .

# Run the container mapping port 8000
docker run -p 8000:8000 contract-guard:latest

```

---

### 3. Production Deployment (Kubernetes)

For enterprise environment deployment, pre-configured manifests are available under the `k8s/` directory.

```bash
chmod +x k8s/deploy.sh
./k8s/deploy.sh

```

---

## 🔌 API Endpoints Reference

| Endpoint | Method | Authentication | Description |
| --- | --- | --- | --- |
| `/health` | `GET` | None | System health check and LLM connection status. |
| `/api/contracts/upload` | `POST` | Required | Uploads a contract file (`.docx`, `.pdf`, `.txt`). |
| `/api/contracts/compare` | `POST` | Required | Triggers the LangGraph comparison workflow for two files. |
| `/api/tasks/{task_id}` | `GET` | Required | Fetches the current execution state of a background task. |
| `/api/tasks/{task_id}/review` | `POST` | Required | Submits human auditor feedback to advance the workflow state. |

---

## ⚙️ Configuration

The system behavior can be customized by editing the `config.yaml` file in the root directory:

```yaml
app:
  host: "0.0.0.0"
  port: 8000
  log_level: "info"

llm:
  provider: "ollama"
  model: "llama3.2"
  base_url: "http://localhost:11434"
  use_llm: true
  temperature: 0.1  # Lower temperature guarantees more deterministic legal analyses

database:
  path: "app/data/contracts.db"
  vector_store_path: "app/data/vector_store"

```

---

## 📂 Project Structure

```text
ContractGuardAgent/
├── app/
│   ├── api/           # Router endpoints and request/response schemas
│   ├── config.py      # Pydantic-based configuration loader
│   ├── graph/         # LangGraph state definitions, nodes, and conditional edges
│   ├── models/        # SQLAlchemy database models 
│   ├── rag/           # Document embedding, chunking, and semantic retrieval
│   ├── services/      # LLM invocation wrapper and prompts
│   └── main.py        # FastAPI app initialization and middleware config
├── k8s/               # Kubernetes deployment manifests & scripts
├── static/            # Frontend assets (HTML, CSS, JS)
├── tests/             # PyTest suite for graphs and APIs
├── Dockerfile         # Multi-stage build configuration
├── config.yaml        # Local configuration file
└── requirements.txt   # Python project dependencies

```

---

## 🗺️ Roadmap & Agent Specs

For detailed specifications regarding planned agent capabilities, tools abstraction, and future features, please refer to [AGENTS.md](https://www.google.com/search?q=./AGENTS.md).

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps to contribute:

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

