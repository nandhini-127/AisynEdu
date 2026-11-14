# EduNex AI — Codebase Audit Report

> **Audit Date:** 2026-11-12  
> **Auditor:** Senior AI/ML Engineer & Full-Stack Architect  
> **Target:** `d:\Skill Nexis Internship\Project - Chatbot\` (EduNex AI)  
> **Source Foundation:** [github.com/rakeshsoniiii/LLMs](https://github.com/rakeshsoniiii/LLMs) (NEXIS SOLUTIONS LLMs)

---

## 1. Project State Overview

| Attribute | Status |
|-----------|--------|
| Local Project Directory | ✅ Exists — `d:\Skill Nexis Internship\Project - Chatbot\` |
| Local Source Files | ⚠️ **Empty** — No source code present yet |
| GitHub Reference Repo | ✅ Fetched — `rakeshsoniiii/LLMs` |
| Previous Mini-Projects (Reusable) | ✅ 3 mini-projects inspected |
| Python Version | ✅ Python 3.10.11 |
| pip Version | ✅ pip 25.2 |

> **IMPORTANT:** The `Project - Chatbot` directory was **created today (2026-11-12)** and is currently empty. EduNex AI must be built from scratch, using the NEXIS SOLUTIONS LLMs repo as reference architecture and the three mini-projects as reusable component libraries.

---

## 2. GitHub Reference Repository — NEXIS SOLUTIONS LLMs

**Repository:** `https://github.com/rakeshsoniiii/LLMs`  
**Purpose:** Educational repository for learning LLMs from scratch — based on "Build a Large Language Model From Scratch" (Sebastian Raschka, Manning).

### 2.1 Repository Structure

```
LLMs/
├── README.md                        # Project overview
├── requirements.txt                 # Core dependencies
├── pyproject.toml                   # Package configuration
├── pixi.toml                        # Pixi environment manager config
├── conftest.py                      # Pytest configuration with link checking
├── ch01/                            # Ch 1: Understanding LLMs (no code)
├── ch02/                            # Ch 2: Working with Text Data
│   ├── 01_main-chapter-code/        # ch02.ipynb, dataloader.ipynb
│   └── 02-06_bonus/                 # BPE, embeddings, tokenizers
├── ch03/                            # Ch 3: Attention Mechanisms
│   └── 01_main-chapter-code/        # ch03.ipynb, multihead-attention.ipynb
├── ch04/                            # Ch 4: GPT Model From Scratch
│   ├── 01_main-chapter-code/        # gpt.py CORE MODEL
│   └── 02-10_bonus/                 # KV-cache, GQA, MLA, MoE, DeltaNet
├── ch05/                            # Ch 5: Pretraining on Unlabeled Data
│   ├── 01_main-chapter-code/        # gpt_train.py, gpt_generate.py
│   └── 06_user_interface/           # Chainlit UI with GPT-2
├── ch06/                            # Ch 6: Text Classification Finetuning
│   ├── 01_main-chapter-code/        # gpt_class_finetune.py
│   └── 04_user_interface/           # Chainlit UI for classifier
├── ch07/                            # Ch 7: Instruction Finetuning
│   ├── 01_main-chapter-code/        # gpt_instruction_finetuning.py
│   └── 06_user_interface/           # Chainlit chat UI
├── pkg/skill_nexis/                 # llms_from_scratch PyPI package
│   ├── ch02.py ... ch07.py          # Chapter module implementations
│   ├── generate.py                  # Generation utilities
│   ├── utils.py                     # Notebook import utilities
│   ├── llama3.py                    # Llama 3 support
│   └── qwen3.py                     # Qwen 3 support
└── appendix-A through E/            # PyTorch intro, DDP, references
```

### 2.2 LLM Architecture (from `ch04/gpt.py`)

The reference repo implements a **GPT-style Transformer** from scratch:

| Component | Implementation |
|-----------|---------------|
| Tokenizer | `tiktoken` (GPT-2 BPE tokenizer) |
| Embedding | Token + positional embeddings |
| Attention | `MultiHeadAttention` with causal masking |
| Feed-Forward | GELU activation, 2-layer MLP |
| Normalization | Layer Normalization |
| Output | Linear projection to vocabulary logits |
| Model Sizes | 124M (GPT-2 small) to 1558M (GPT-2 XL) |

### 2.3 Existing UI Implementations

| Location | Framework | Description |
|----------|-----------|-------------|
| `ch05/06_user_interface/app_orig.py` | Chainlit | GPT-2 chat with OpenAI weights |
| `ch05/06_user_interface/app_own.py` | Chainlit | GPT-2 chat with custom-trained weights |
| `ch06/04_user_interface/` | Chainlit | Text classification UI |
| `ch07/06_user_interface/app.py` | Chainlit | Instruction-following chat UI |

### 2.4 Key Python Components

- **`pkg/skill_nexis/generate.py`** — `trim_input_tensor()`: handles context window overflow  
- **`pkg/skill_nexis/utils.py`** — Notebook-to-module import utilities, definition extraction  
- **`ch07/ollama_evaluate.py`** — Ollama local LLM integration pattern  
- **`ch07/gpt_instruction_finetuning.py`** — Alpaca-format instruction fine-tuning pipeline

---

## 3. Local Mini-Projects Audit (Reusable Components)

### 3.1 Mini Project 1 — AI Text Summarizer
**Path:** `d:\Skill Nexis Internship\Mini Project-1\`  
**Tech:** HuggingFace Transformers, `distilbart-cnn-12-6`, PyTorch  

| Component | Detail |
|-----------|--------|
| Model | `sshleifer/distilbart-cnn-12-6` (distilled BART) |
| Framework | `transformers==4.46.3`, `torch`, `pandas` |
| Tokenizer | AutoTokenizer (Hugging Face) |
| Input Limit | 900 tokens max |
| Length Control | Short (20–60), Medium (40–100), Long (60–150) tokens |
| Evaluation | 5-scenario CSV evaluation (`evaluate.py`) |

**Reusable For EduNex AI:**
- `summarize_text()` function — reusable for content summarization
- Token counting & length validation logic
- Evaluation framework pattern (CSV scoring)

---

### 3.2 Mini Project 2 — Character-Level Text Generator
**Path:** `d:\Skill Nexis Internship\mini_project_2_character_generator\`  
**Tech:** PyTorch, Bigram Language Model, Matplotlib  

| Component | Detail |
|-----------|--------|
| Model | Bigram LM (character-level, single embedding table) |
| Dataset | Alice's Adventures in Wonderland (Project Gutenberg) |
| Training | 10,000 steps, AdamW optimizer, 90/10 train-val split |
| Output | Loss curves, generated text samples, model checkpoint |

**Reusable For EduNex AI:**
- Data pipeline structure (download → clean → encode → train)
- Training loop pattern with eval intervals
- Model checkpointing pattern (`torch.save`)

---

### 3.3 Mini Project 3 — IntelliResearch (Multi-Agent Research Assistant)
**Path:** `d:\Skill Nexis Internship\Mini Project 3 - IntelliResearch\`  
**Tech:** Gemini (Google GenAI), LangChain, LangGraph, Tavily, Gradio  

| Component | Detail |
|-----------|--------|
| LLM | Google Gemini via `langchain-google-genai` |
| Model | `gemini-3.5-flash` (WRONG — likely `gemini-1.5-flash`) |
| Search | Tavily API (web search) |
| Workflow | LangGraph `StateGraph` with 3 sequential agents |
| UI | Gradio `gr.Blocks` with tabbed outputs |
| Config | `.env` with `GOOGLE_API_KEY`, `TAVILY_API_KEY`, `GEMINI_MODEL` |

**Agent Pipeline (LangGraph):**
```
START → research_node → summarize_node → report_node → END
```

**Reusable For EduNex AI:**
- **Full LangGraph workflow pattern** — directly adaptable
- **LLM factory** (`get_llm()` in `config/settings.py`)
- **Multi-agent state management** (`ResearchState` TypedDict)
- **Gradio UI structure** — tabbed layout pattern
- **`extract_text_content()`** utility — LLM response parser
- **Retry logic** in `summarizer_agent.py` (503/504 handling)
- **System/User prompt pair** pattern
- **Source formatting** for citations

---

## 4. Installed Packages Inventory (System Python 3.10.11)

| Package | Version | Status |
|---------|---------|--------|
| `streamlit` | 1.50.0 | ✅ Available for UI |
| `gradio` | (not global) | ⚠️ Install needed |
| `langchain` | ❌ Not installed | Needs install |
| `langgraph` | ❌ Not installed | Needs install |
| `langchain-google-genai` | ❌ Not installed | Needs install |
| `tavily-python` | ❌ Not installed | Needs install |
| `fastapi` | 0.141.1 | ✅ Available |
| `torch` | 1.12.1 | ⚠️ VERY OUTDATED |
| `tensorflow` | 2.15.0 | ⚠️ Available but heavy |
| `transformers` | (venv only) | Needs venv |
| `tiktoken` | ❌ Not installed | Needs install |
| `flask` | 3.1.1 | ✅ Available |
| `python-dotenv` | 1.2.2 | ✅ Available |
| `httpx` | 0.28.1 | ✅ Available |
| `pydantic` | 2.13.4 | ✅ Available |
| `numpy` | 1.26.4 | ✅ Available |
| `pandas` | 1.5.3 | ⚠️ Old (2.x preferred) |
| `sqlalchemy` | 2.0.41 | ✅ Available |

---

## 5. Security Assessment

| Issue | Severity | Location | Detail |
|-------|----------|----------|--------|
| `.env` file in Mini Project 3 | MEDIUM | `Mini Project 3/.env` | Contains real API keys |
| `gemini-3.5-flash` invalid model name | HIGH | `config/settings.py` | Will fail at inference |
| No `.gitignore` in Project - Chatbot | HIGH | Root | Must add before first commit |
| No input sanitization | MEDIUM | `research_agent.py` | Raw user input to Tavily |
| No rate limiting | MEDIUM | `app.py` | Gradio has no throttling |
| torch 1.12.1 (global) | HIGH | System Python | 4-year-old version; CVEs exist |
| API keys default to `""` | LOW | Good — fails with `ValueError` |

---

## 6. Can the Reference Application Run?

### NEXIS SOLUTIONS LLMs repo:
- **Cannot run** — requires Jupyter, tiktoken, PyTorch ≥ 2.2.2
- System torch 1.12.1 is too old; no Jupyter globally installed
- Chainlit UIs need: `pip install chainlit` + GPT-2 weights download

### IntelliResearch (Mini Project 3):
- **Can run** in its own venv
- **WARNING:** `gemini-3.5-flash` model name is invalid — will fail at inference
- Fix: Set `GEMINI_MODEL=gemini-1.5-flash` in `.env`

### Mini Project 1 (Summarizer):
- **Can run** in its own venv
- Requires ~1GB model download on first run

### Mini Project 2 (Character Generator):
- **Can run** but torch 1.12.1 may have issues on Windows 11

---

## 7. Identified Issues Summary

| # | Issue | Category | Priority |
|---|-------|----------|----------|
| 1 | `gemini-3.5-flash` invalid model name | Bug | P0 |
| 2 | No EduNex AI source code exists yet | Missing | P0 |
| 3 | No `requirements.txt` for new project | Missing | P0 |
| 4 | No `.gitignore` for new project | Security | P1 |
| 5 | torch 1.12.1 globally (outdated) | Dependency | P1 |
| 6 | No RAG/vector store component | Missing | P1 |
| 7 | No authentication/user management | Missing | P2 |
| 8 | No document upload/processing module | Missing | P2 |
| 9 | No conversation history/memory | Missing | P2 |
| 10 | No subject-specific educational prompts | Missing | P2 |
| 11 | Gradio has no auth or rate limiting | Security | P2 |
| 12 | No logging/monitoring system | Missing | P3 |
| 13 | No error boundary UI | Missing | P3 |

