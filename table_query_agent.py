from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from app.llm.model import LLMConfig, generate_chat_completion


DATASET_TABLE_NAME = "dataset"
MAX_RESULT_ROWS = 500

FORBIDDEN_SQL_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bCOPY\b",
    r"\bEXPORT\b",
    r"\bIMPORT\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bINSTALL\b",
    r"\bLOAD\b",
    r"\bPRAGMA\b",
    r"\bCALL\b",
    r"\bSET\b",
    r"\bRESET\b",
    r"\bMERGE\b",
    r"\bTRUNCATE\b",
    r"\bVACUUM\b",
    r"\bREAD_CSV\b",
    r"\bREAD_JSON\b",
    r"\bREAD_PARQUET\b",
    r"\bREAD_TEXT\b",
    r"\bHTTPFS\b",
    r"\bSECRET\b",
]


@dataclass(frozen=True)
class TableQueryResult:
    mode: str
    sql: str
    result_df: pd.DataFrame
    error: str | None = None
    truncated: bool = False


def generate_sql_from_question(
    question: str,
    df: pd.DataFrame,
    profile_df: pd.DataFrame,
    llm_config: LLMConfig | None,
    language: str,
) -> str:
    """Generate a read-only DuckDB SQL query from a natural-language request."""
    if llm_config is None:
        raise ValueError("LLM config is required for natural-language SQL generation.")

    sql = generate_chat_completion(
        config=llm_config,
        system_prompt=_sql_system_prompt(language),
        user_prompt=_sql_user_prompt(question, df, profile_df, language),
    )
    return _extract_sql(sql)


def run_table_query(df: pd.DataFrame, sql: str, max_rows: int = MAX_RESULT_ROWS) -> TableQueryResult:
    """Validate and execute a read-only SQL query against the uploaded dataframe."""
    normalized_sql = normalize_sql(sql)
    validation_error = validate_read_only_sql(normalized_sql)
    if validation_error:
        return TableQueryResult(mode="error", sql=normalized_sql, result_df=pd.DataFrame(), error=validation_error)

    try:
        import duckdb

        connection = duckdb.connect(database=":memory:")
        connection.register(DATASET_TABLE_NAME, df)
        result_df = connection.execute(
            f"SELECT * FROM ({normalized_sql}) AS table_query_result LIMIT {int(max_rows) + 1}"
        ).df()
    except Exception as exc:
        return TableQueryResult(mode="error", sql=normalized_sql, result_df=pd.DataFrame(), error=str(exc))
    finally:
        try:
            connection.close()
        except Exception:
            pass

    truncated = len(result_df) > max_rows
    if truncated:
        result_df = result_df.head(max_rows)

    return TableQueryResult(mode="sql", sql=normalized_sql, result_df=result_df, truncated=truncated)


def normalize_sql(sql: str) -> str:
    cleaned = sql.strip()
    cleaned = re.sub(r"^```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return cleaned.rstrip(";").strip()


def validate_read_only_sql(sql: str) -> str | None:
    if not sql:
        return "SQL query cannot be empty."

    if ";" in sql:
        return "Only one SQL statement is allowed."

    first_token = sql.lstrip().split(None, 1)[0].upper()
    if first_token not in {"SELECT", "WITH"}:
        return "Only SELECT or WITH read-only queries are allowed."

    compact_sql = re.sub(r"\s+", " ", sql.upper())
    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, compact_sql):
            return "This SQL contains a blocked keyword or function. Only read-only table queries are allowed."

    return None


def _extract_sql(text: str) -> str:
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return normalize_sql(fenced.group(1))

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line.upper().startswith(("SELECT", "WITH")):
            return normalize_sql("\n".join(lines[index:]))
    return normalize_sql(text)


def _sql_system_prompt(language: str) -> str:
    if language == "zh":
        return (
            "你是一个严谨的数据分析 SQL 生成器。只能输出一条 DuckDB 只读 SQL。"
            "数据表名固定为 dataset。只能使用 SELECT 或 WITH。不要输出解释，不要使用 Markdown。"
            "不要生成 INSERT、UPDATE、DELETE、DROP、CREATE、COPY、INSTALL、LOAD、PRAGMA 或读取外部文件的函数。"
        )
    return (
        "You are a rigorous data-analysis SQL generator. Output exactly one read-only DuckDB SQL query. "
        "The table name is dataset. Use only SELECT or WITH. Do not explain. Do not use Markdown. "
        "Do not generate INSERT, UPDATE, DELETE, DROP, CREATE, COPY, INSTALL, LOAD, PRAGMA, or external file functions."
    )


def _sql_user_prompt(question: str, df: pd.DataFrame, profile_df: pd.DataFrame, language: str) -> str:
    columns = [
        {
            "column": column,
            "dtype": str(df[column].dtype),
            "examples": [str(value) for value in df[column].dropna().head(3).tolist()],
        }
        for column in df.columns
    ]
    profile_records = (
        profile_df[["column", "smart_type", "reason"]].to_dict("records")
        if not profile_df.empty and {"column", "smart_type", "reason"}.issubset(profile_df.columns)
        else []
    )

    if language == "zh":
        return (
            f"用户问题：{question}\n\n"
            f"表名：dataset\n"
            f"字段信息：{columns}\n"
            f"字段语义画像：{profile_records}\n\n"
            "请生成一条可以回答用户问题的 DuckDB SQL。"
            "如果需要引用包含空格、中文或特殊字符的列名，请使用双引号。"
            f"结果最多保留 {MAX_RESULT_ROWS} 行。"
        )

    return (
        f"User question: {question}\n\n"
        f"Table name: dataset\n"
        f"Columns: {columns}\n"
        f"Semantic profile: {profile_records}\n\n"
        "Generate one DuckDB SQL query that answers the question. "
        "Use double quotes for column names with spaces, non-English characters, or special characters. "
        f"Keep the result within {MAX_RESULT_ROWS} rows."
    )
