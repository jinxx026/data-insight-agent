# DataInsight Agent

DataInsight Agent 是一个基于 LLM + RAG + 多 Agent 工作流的智能数据分析系统。用户上传 CSV 或 Excel 数据集后，系统可以自动完成字段类型识别、数据质量检测、探索性数据分析、图表推荐、自然语言洞察生成、RAG 问答、SQL 表格查询和 Markdown/HTML 报告导出。

这个项目的目标不是做一个普通 dashboard，而是把数据分析流程拆成多个可复用 Agent，让系统能够自动理解数据、选择分析方法，并用自然语言解释结果。

## Demo Flow

1. 上传 CSV 或 Excel 文件。
2. 如果是 Excel，选择需要分析的 Sheet。
3. 系统自动运行多 Agent 分析流程。
4. 查看字段画像、数据质量问题、EDA 图表和洞察总结。
5. 使用 RAG Q&A 询问数据分析方法或当前数据集问题。
6. 使用 Table Query Agent 对上传表格执行 SQL 查询。
7. 下载 Markdown 或 HTML 分析报告。

## Key Features

- CSV / Excel 上传，支持 Excel Sheet 选择
- 智能字段类型识别：ID、数值、类别、时间、文本、目标变量
- 数据质量分析：缺失值、重复行、空字段、常量字段、高基数字段、异常值、目标类别不平衡
- 自动 EDA：数值分布、类别分布、时间趋势、目标变量分布、目标变量分组对比、相关性分析
- Insight Agent：基于本地规则或 LLM 生成自然语言数据洞察
- RAG Q&A：基于内置数据分析知识库回答问题
- Table Query Agent：用 DuckDB 对上传数据执行只读 SQL 查询
- Natural Language to SQL：配置 LLM 后，可用自然语言生成 SQL
- Report Agent：生成 Markdown 和 HTML 分析报告
- FastAPI 后端：封装分析、问答、Sheet 读取和表格查询接口
- Docker Compose：同时启动 Streamlit 前端和 FastAPI 后端
- 中英文界面切换

## Tech Stack

| Layer | Tech |
| --- | --- |
| Frontend | Streamlit |
| Backend | FastAPI |
| Data Processing | pandas, numpy |
| SQL Engine | DuckDB |
| Visualization | Altair |
| LLM API | OpenAI-compatible API, DeepSeek, GPT, Gemini, Kimi |
| RAG | Local TF-IDF retriever, Markdown knowledge base |
| Deployment | Docker, Docker Compose, Streamlit Community Cloud |

## Architecture

```text
User
  |
  v
Streamlit Frontend
  |
  +-- Upload CSV / Excel
  +-- Display analysis results
  +-- Run RAG Q&A
  +-- Run SQL table queries
  |
  v
Multi-Agent Workflow
  |
  +-- Data Loader
  +-- Data Profiler Agent
  +-- Data Quality Agent
  +-- EDA Agent
  +-- Insight Agent
  +-- Report Agent
  +-- RAG QA Agent
  +-- Table Query Agent
  |
  v
Data Layer
  |
  +-- pandas
  +-- DuckDB
  +-- Altair
  |
  v
RAG Knowledge Base + Optional LLM API
```

## Multi-Agent Workflow

| Agent | Responsibility |
| --- | --- |
| Data Loader | 读取 CSV / Excel，生成数据集概览 |
| Data Profiler Agent | 识别字段的语义类型和分析角色 |
| Data Quality Agent | 检测缺失值、重复值、异常值、高基数字段等质量问题 |
| EDA Agent | 根据字段类型自动推荐分析方法和图表 |
| Insight Agent | 基于统计结果生成自然语言洞察 |
| Report Agent | 生成 Markdown / HTML 分析报告 |
| RAG QA Agent | 结合当前数据集和知识库回答自然语言问题 |
| Table Query Agent | 将数据表注册为 DuckDB 内存表并执行只读 SQL |

## Project Structure

```text
data-insight-agent/
├── app/
│   ├── agents/
│   │   ├── insight_agent.py
│   │   ├── qa_agent.py
│   │   ├── report_agent.py
│   │   ├── table_query_agent.py
│   │   └── workflow_agent.py
│   ├── api/
│   │   └── routes.py
│   ├── data/
│   │   ├── eda.py
│   │   ├── loader.py
│   │   ├── profiler.py
│   │   └── quality.py
│   ├── llm/
│   │   ├── model.py
│   │   └── presets.py
│   ├── rag/
│   │   └── retriever.py
│   ├── ui/
│   │   └── i18n.py
│   └── main.py
├── frontend/
│   ├── requirements.txt
│   └── streamlit_app.py
├── knowledge_base/
├── sample_data/
├── outputs/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run_app.bat
├── run_api.bat
└── run_docker.bat
```

## Quick Start

### Windows

启动 Streamlit 前端：

```text
run_app.bat
```

打开浏览器：

```text
http://127.0.0.1:8501
```

启动 FastAPI 后端：

```text
run_api.bat
```

后端入口页：

```text
http://127.0.0.1:8000/
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

### macOS / Linux

```bash
pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
```

另开一个终端启动 API：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Docker

启动 Streamlit 前端和 FastAPI 后端：

```bash
docker compose up --build
```

访问地址：

```text
Streamlit Frontend: http://127.0.0.1:8501
Backend Entry:      http://127.0.0.1:8000/
FastAPI Docs:       http://127.0.0.1:8000/docs
```

Windows 也可以直接双击：

```text
run_docker.bat
```

## LLM Configuration

系统默认可以不配置 LLM，使用本地规则生成分析结果。配置 LLM 后，可以启用：

- LLM 洞察生成
- RAG 问答增强回答
- 自然语言生成 SQL

支持的预设提供商：

- DeepSeek
- OpenAI GPT
- Google Gemini
- Kimi
- Custom OpenAI-compatible API

### Sidebar Runtime Config

在 Streamlit 侧边栏选择：

```text
Insight mode -> LLM if configured
Provider -> DeepSeek / OpenAI GPT / Google Gemini / Kimi / Custom
API Key -> your_api_key
Base URL -> provider base url
Model -> model name
```

API Key 只会保存在当前 Streamlit session 中，不会写入项目文件。

### Local Secrets

复制示例文件：

```text
.streamlit/secrets.example.toml -> .streamlit/secrets.toml
```

填写：

```toml
[llm]
provider = "DeepSeek"
api_key = "your_api_key_here"
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

`.streamlit/secrets.toml` 已被 `.gitignore` 忽略，不应该提交到 GitHub。

## Table Query Agent

Table Query Agent 会把当前上传的数据注册成 DuckDB 内存表：

```text
dataset
```

你可以直接写 SQL：

```sql
SELECT contract_type, COUNT(*) AS customers
FROM dataset
GROUP BY contract_type
ORDER BY customers DESC;
```

也可以在配置 LLM 后输入自然语言：

```text
按合同类型统计客户数量，并按客户数量降序排列
```

系统会生成 SQL，再由 DuckDB 执行并输出表格。

### SQL Safety

为了避免执行危险操作，系统只允许：

```text
SELECT
WITH
```

禁止：

```text
INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, INSTALL, LOAD, PRAGMA
```

LLM 只负责生成 SQL，真正执行和安全校验由系统完成。

## RAG Knowledge Base

内置知识库位于：

```text
knowledge_base/
```

包含：

- feature_types.md
- missing_values.md
- outlier_detection.md
- correlation_analysis.md
- visualization_guide.md
- class_imbalance.md
- eda_methods.md

用户可以询问：

```text
为什么 customer_id 不适合建模？
为什么要看缺失值？
类别不平衡有什么影响？
什么时候用柱状图，什么时候用折线图？
```

系统会结合当前数据集分析结果和知识库片段回答。

## FastAPI Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/llm/presets` | 获取 LLM provider 和 model 预设 |
| POST | `/api/datasets/sheets` | 读取 Excel Sheet 名称 |
| POST | `/api/analysis` | 上传数据集并返回完整分析结果 |
| POST | `/api/qa` | 基于当前数据集和知识库问答 |
| POST | `/api/table-query` | 对上传数据执行 SQL 查询 |

## Streamlit Community Cloud Deployment

如果仓库结构是：

```text
datainsight/
└── data-insight-agent/
    ├── frontend/
    │   └── streamlit_app.py
    └── requirements.txt
```

Streamlit Cloud 的 Main file path 应填写：

```text
data-insight-agent/frontend/streamlit_app.py
```

仓库根目录也建议放一个 `requirements.txt`，内容至少包含：

```txt
streamlit==1.45.1
altair==5.5.0
duckdb==1.1.3
pandas==2.2.3
numpy==2.2.6
openpyxl==3.1.5
requests==2.34.2
```

如果部署时可选择 Python 版本，建议选择 Python 3.12。

## Example Questions

数据分析问答：

```text
这个数据集有哪些主要质量风险？
为什么某个字段被识别成 ID？
缺失值应该删除还是填充？
目标变量是否存在类别不平衡？
```

SQL 查询：

```text
筛选出 monthly_charges 大于 80 的客户
按 contract_type 统计客户数量
计算不同 payment_method 的平均 monthly_charges
找出 total_charges 最高的前 10 个客户
```

## Resume Highlights

- Built an LLM-powered data analysis system with Streamlit and FastAPI for CSV/Excel profiling, data quality checks, EDA automation, insight generation, and report export.
- Designed a multi-agent workflow including Profiler, Quality, EDA, Insight, Report, RAG QA, and Table Query agents.
- Implemented RAG-based data analysis Q&A with a local knowledge base and TF-IDF retrieval.
- Built a DuckDB-powered Table Query Agent supporting read-only SQL and natural-language-to-SQL over uploaded datasets.
- Containerized the Streamlit frontend and FastAPI backend with Docker Compose.

## License

This project is intended for learning, portfolio, and internship application use.
