# ContractGuardAgent — STAR Introduction

## Situation

Legal teams in enterprises often need to compare two versions of a contract (e.g., an original and a modified draft) to identify changes and assess legal risks. This process is manual, time-consuming, and error-prone — especially when dealing with high volumes of contracts across categories like purchase, service, lease, labor, and NDA. There was no lightweight, privacy-preserving tool that could automate this workflow while keeping sensitive legal data on-premises.

## Task

Build an intelligent contract comparison and review system that:
- Accepts two contract versions (text or file upload) and detects all differences
- Evaluates each change for legal risk (green / yellow / red)
- Supports human-in-the-loop review to approve or reject flagged items
- Generates a structured final report with recommendations
- Operates fully offline for data privacy, with optional cloud LLM support
- Persists task state so no work is lost on restart
- Is deployable via Docker and Kubernetes

## Action

I designed and built ContractGuardAgent, a full-stack application using:

- **FastAPI** for the backend REST API and static file serving
- **LangGraph** for a stateful, graph-based workflow pipeline with 5 nodes: retriever, analyzer, evaluator, human loop, and finalizer
- **RAG (Retrieval-Augmented Generation)** with SQLite FTS5 full-text search and optional OpenAI embeddings for semantic retrieval from contract templates and compliance playbook rules
- **LangChain + Ollama** for LLM-powered risk evaluation, with a fallback to rule-based heuristics when offline
- **SQLite** for task persistence, supporting retries (up to 3) and status polling
- **Vanilla HTML/CSS/JS** frontend with real-time polling, file upload, and interactive human review forms
- **Docker and Kubernetes** manifests for production deployment

Key implementation details:
- Used Python's `difflib.SequenceMatcher` for line-by-line diff analysis
- Built 16 compliance rules across 5 contract categories for rule-based evaluation
- Pauses the graph with a SQLite checkpointer when a change is yellow or red, then resumes after one human confirmation so the comment is written into the report
- Added automatic retry with configurable delay for fault tolerance

## Result

ContractGuardAgent delivers a local legal contract review workflow that:
- Reduces contract review time from hours to minutes
- Provides auditable, structured risk assessments with three-tier classification
- Supports both fully offline mode (Ollama) and cloud LLMs (OpenAI)
- Survives restarts with full task persistence in SQLite
- Passes all unit tests and is deployable via Docker or Kubernetes in one command
- Handles UTF-8 and GBK encoded Chinese documents, making it suitable for multilingual legal teams
