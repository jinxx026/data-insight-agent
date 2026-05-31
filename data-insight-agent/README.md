# DataInsight Agent

DataInsight Agent is an LLM-powered data analysis system in progress. The first milestone focuses on uploading structured datasets and showing a basic data preview.

## Day 1 MVP

- Streamlit app shell
- CSV and Excel upload
- Excel sheet selection
- pandas-based dataset loading
- First rows preview
- Basic dataset summary
- Per-column overview with dtype, missing rate, and unique rate

## Day 2 Smart Field Profiling

- Detects ID fields, numerical features, categorical features, datetime fields, text fields, and target variables
- Explains why each smart type was assigned
- Summarizes feature type counts for downstream EDA and agent planning

## Day 3 Data Quality Analysis

- Detects missing values, duplicate rows, empty fields, constant fields, ID fields, high-cardinality fields, numeric outliers, and target imbalance
- Assigns rule-based severity levels
- Produces recommendations that can be reused by the future Insight Agent and Report Agent

## Day 4 Automatic EDA

- Recommends EDA tasks from smart field types
- Renders numeric distributions, category counts, datetime trends, target distribution, target-by-category comparisons, and correlation heatmaps
- Uses pandas for computation and Altair for charts so the visualizations are based on real calculated statistics

## Day 5 Insight Agent

- Generates natural language insight summaries from structured profiling, quality, and EDA outputs
- Uses local rule-based insights by default so the app works without an API key
- Optionally calls an OpenAI-compatible chat completions API from sidebar inputs or environment variables

## Day 6 Markdown Reports

- Generates complete Markdown and HTML analysis reports from the same structured outputs shown in the app
- Includes dataset overview, smart field profile, data quality issues, automatic EDA plan, key insights, and recommended next steps
- Provides an in-app preview plus Markdown and HTML download buttons

## Version 2 Step 1 Multi-Agent Workflow

- Adds a workflow orchestrator that runs Data Loader, Data Profiler Agent, Data Quality Agent, EDA Agent, Insight Agent, and Report Agent in sequence
- Returns one shared `AnalysisWorkflowResult` object containing all intermediate outputs and the final Markdown report
- Shows workflow execution steps in the Streamlit UI so users can see which agent produced each stage
- Makes the same workflow reusable by the upcoming FastAPI backend, RAG QA layer, and Docker deployment

## Version 2 Step 2 RAG Knowledge Base

- Adds a built-in data analysis knowledge base under `knowledge_base/`
- Covers feature types, missing values, outlier detection, correlation analysis, visualization choices, class imbalance, and EDA methods
- Implements a local TF-IDF retrieval baseline that does not require external embedding APIs
- Adds a Streamlit Q&A section that retrieves relevant knowledge snippets and shows source documents
- Can be upgraded later to FAISS, Chroma, or another vector database with embeddings

## Version 2 Step 3 Natural Language Q&A

- Adds a QA Agent that combines current dataset analysis context with retrieved knowledge snippets
- Answers field-specific questions such as why an ID field should not be used for modeling
- Answers dataset-level questions such as major quality risks using the workflow output
- Uses local deterministic answers by default and optionally calls the configured LLM for more natural responses

## Version 2 Step 4 FastAPI Backend

- Adds a FastAPI backend entry point at `app/main.py`
- Exposes the reusable multi-agent workflow through HTTP APIs
- Supports uploaded CSV and Excel datasets, including Excel sheet lookup
- Returns dataset summary, field profile, quality issues, EDA recommendations, insights, workflow steps, and Markdown/HTML reports as JSON
- Exposes a Q&A endpoint that combines the current dataset analysis with the RAG knowledge base

Core API endpoints:

```text
GET  /api/health
GET  /api/llm/presets
POST /api/datasets/sheets
POST /api/analysis
POST /api/qa
```

## Version 2 Step 5 Docker Deployment

- Adds a `Dockerfile` for reproducible Python dependency installation
- Adds `docker-compose.yml` to run the Streamlit frontend and FastAPI backend together
- Exposes Streamlit on port `8501` and FastAPI docs on port `8000`
- Keeps API keys outside the image by reading optional environment variables at runtime

Recommended app workflow:

1. Choose `LLM if configured` in the sidebar.
2. Enter API Key, Base URL, and model name in the sidebar.
3. Run the analysis. The key is only used in the current Streamlit session and is not written to project files.

Optional local persistent configuration without PowerShell:

1. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`.
2. Fill in your real API key and preferred provider/model.
3. Start the app with `run_app.bat`; the sidebar will use these values by default.

Example `.streamlit/secrets.toml`:

```toml
[llm]
provider = "DeepSeek"
api_key = "your_api_key_here"
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
```

For Streamlit Community Cloud, add the same TOML content in the app's `Settings -> Secrets` panel.

Optional PowerShell environment variables:

```powershell
$env:LLM_API_KEY="your_api_key_here"
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
.\run_app.bat
```

## UI Language

- Supports Chinese and English display from the sidebar language selector
- Localizes UI text, smart feature types, quality issue types, severity labels, explanations, and recommendations

## Run Locally

Windows:

Double-click `run_app.bat`, or run it from the project folder. The script will create `.venv`, install dependencies when needed, start Streamlit, and open the browser automatically.

To run the FastAPI backend, double-click `run_api.bat`. It opens the interactive API docs at:

```text
http://127.0.0.1:8000/docs
```

macOS/Linux:

```bash
pip install -r requirements.txt
streamlit run frontend/streamlit_app.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run With Docker

Build and start both services:

```bash
docker compose up --build
```

On Windows, you can also double-click:

```text
run_docker.bat
```

Open the Streamlit app:

```text
http://127.0.0.1:8501
```

Open the FastAPI docs:

```text
http://127.0.0.1:8000/docs
```

Optional LLM environment variables:

```bash
LLM_API_KEY=your_api_key_here LLM_BASE_URL=https://api.deepseek.com/v1 LLM_MODEL=deepseek-chat docker compose up --build
```

## Deploy As A Website

For a public URL that does not require PowerShell or a local server, deploy the GitHub repo to Streamlit Community Cloud:

1. Go to Streamlit Community Cloud.
2. Create a new app from `jinxx026/data-insight-agent`.
3. Set the main file path to `frontend/streamlit_app.py`.
4. Keep Python dependencies in `requirements.txt`. A duplicate `frontend/requirements.txt` is included so Streamlit Community Cloud can find dependencies when the app entrypoint is deployed from the `frontend/` directory.
5. If using LLM mode, add secrets for `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`, or enter them in the app sidebar at runtime.

## Project Structure

```text
data-insight-agent/
├── app/
│   └── data/
│       └── loader.py
├── frontend/
│   └── streamlit_app.py
├── sample_data/
│   ├── customer_churn_sample.csv
│   └── customer_churn_quality_demo.csv
├── outputs/
│   ├── charts/
│   └── reports/
├── requirements.txt
└── README.md
```

## Next Milestone

Next Version 2 step: improve the Streamlit frontend so it can call the FastAPI backend instead of always running the workflow in-process.
