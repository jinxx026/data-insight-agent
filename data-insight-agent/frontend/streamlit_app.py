from __future__ import annotations

import sys
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.agents.workflow_agent import (
    WorkflowConfig,
    run_analysis_workflow,
    workflow_steps_to_dataframe,
)
from app.agents.qa_agent import answer_user_question
from app.data.loader import (
    is_excel_file,
    list_excel_sheets,
    load_dataset,
)
from app.data.eda import (
    build_category_counts,
    build_correlation_pairs,
    build_target_by_category,
    build_time_trend,
)
from app.data.profiler import summarize_feature_types
from app.data.quality import (
    build_quality_summary,
    summarize_issue_types,
)
from app.llm.model import build_llm_config
from app.llm.presets import CUSTOM_PROVIDER, LLM_PROVIDER_PRESETS
from app.ui.i18n import LANGUAGE_OPTIONS, localize_dataframe, t


st.set_page_config(
    page_title="DataInsight Agent",
    page_icon="DA",
    layout="wide",
)


def load_llm_secret_defaults() -> dict[str, str]:
    try:
        llm_secrets = st.secrets.get("llm", {})
    except Exception:
        llm_secrets = {}

    return {
        "provider": str(llm_secrets.get("provider", "DeepSeek")),
        "api_key": str(llm_secrets.get("api_key", "")),
        "base_url": str(llm_secrets.get("base_url", "https://api.deepseek.com/v1")),
        "model": str(llm_secrets.get("model", "deepseek-chat")),
    }


llm_secret_defaults = load_llm_secret_defaults()

language = st.sidebar.selectbox(
    "Language / 语言",
    options=list(LANGUAGE_OPTIONS.keys()),
    format_func=lambda option: LANGUAGE_OPTIONS[option],
)
insight_mode = st.sidebar.selectbox(
    t(language, "insight_mode"),
    options=["local", "llm"],
    format_func=lambda option: (
        t(language, "insight_mode_local")
        if option == "local"
        else t(language, "insight_mode_llm")
    ),
)
runtime_llm_config = None
if insight_mode == "llm":
    st.sidebar.caption(t(language, "llm_config_help"))
    llm_api_key = st.sidebar.text_input(
        t(language, "llm_api_key"),
        type="password",
        placeholder="sk-...",
        value=llm_secret_defaults["api_key"],
    )
    provider_options = [*LLM_PROVIDER_PRESETS.keys(), CUSTOM_PROVIDER]
    default_provider = (
        llm_secret_defaults["provider"]
        if llm_secret_defaults["provider"] in provider_options
        else CUSTOM_PROVIDER
    )
    llm_provider = st.sidebar.selectbox(
        t(language, "llm_provider"),
        options=provider_options,
        index=provider_options.index(default_provider),
    )
    if llm_provider == CUSTOM_PROVIDER:
        llm_base_url = st.sidebar.text_input(
            t(language, "llm_custom_base_url"),
            value=llm_secret_defaults["base_url"],
        )
        llm_model = st.sidebar.text_input(
            t(language, "llm_custom_model"),
            value=llm_secret_defaults["model"],
        )
    else:
        provider_preset = LLM_PROVIDER_PRESETS[llm_provider]
        default_base_url = (
            llm_secret_defaults["base_url"]
            if llm_secret_defaults["base_url"] in provider_preset["base_urls"]
            else provider_preset["base_urls"][0]
        )
        default_model = (
            llm_secret_defaults["model"]
            if llm_secret_defaults["model"] in provider_preset["models"]
            else provider_preset["models"][0]
        )
        llm_base_url = st.sidebar.selectbox(
            t(language, "llm_base_url"),
            options=provider_preset["base_urls"],
            index=provider_preset["base_urls"].index(default_base_url),
        )
        llm_model = st.sidebar.selectbox(
            t(language, "llm_model"),
            options=provider_preset["models"],
            index=provider_preset["models"].index(default_model),
        )
    runtime_llm_config = build_llm_config(
        api_key=llm_api_key,
        base_url=llm_base_url,
        model=llm_model,
    )

st.title("DataInsight Agent")
st.caption(t(language, "caption"))

uploaded_file = st.file_uploader(
    t(language, "upload_dataset"),
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=False,
)

sample_options = {
    "Customer churn sample": ROOT_DIR / "sample_data" / "customer_churn_sample.csv",
    "Customer churn quality demo": ROOT_DIR / "sample_data" / "customer_churn_quality_demo.csv",
}
selected_sample = None
if uploaded_file is None:
    selected_sample = st.selectbox(
        t(language, "sample_dataset"),
        [t(language, "none")] + [name for name, path in sample_options.items() if path.exists()],
    )


def render_summary(summary: dict[str, object]) -> None:
    metric_columns = st.columns(5)
    metric_columns[0].metric(t(language, "rows"), f"{summary['rows']:,}")
    metric_columns[1].metric(t(language, "columns"), f"{summary['columns']:,}")
    metric_columns[2].metric(t(language, "missing_cells"), f"{summary['missing_cells']:,}")
    metric_columns[3].metric(t(language, "duplicate_rows"), f"{summary['duplicate_rows']:,}")
    metric_columns[4].metric(t(language, "memory"), f"{summary['memory_usage_mb']} MB")


def render_profiler(profile_df: pd.DataFrame) -> None:
    st.subheader(t(language, "smart_field_detection"))

    type_summary = summarize_feature_types(profile_df)
    if not type_summary.empty:
        st.dataframe(localize_dataframe(type_summary, language), use_container_width=True, hide_index=True)

    target_columns = profile_df.loc[
        profile_df["smart_type"] == "target_variable", "column"
    ].tolist()
    if target_columns:
        st.success(t(language, "detected_target", columns=", ".join(target_columns)))
    else:
        st.warning(t(language, "no_target"))

    visible_columns = [
        "column",
        "pandas_dtype",
        "smart_type",
        "analysis_role",
        "reason",
        "missing_rate",
        "unique_count",
        "unique_rate",
        "example_values",
    ]
    st.dataframe(
        localize_dataframe(profile_df[visible_columns], language),
        use_container_width=True,
        hide_index=True,
    )


def render_quality_report(df: pd.DataFrame, quality_df: pd.DataFrame) -> None:
    st.subheader(t(language, "quality_report"))

    quality_summary = build_quality_summary(df, quality_df)
    metric_columns = st.columns(4)
    metric_columns[0].metric(t(language, "quality_issues"), f"{quality_summary['quality_issues']:,}")
    metric_columns[1].metric(t(language, "high_severity"), f"{quality_summary['high_severity']:,}")
    metric_columns[2].metric(t(language, "columns_with_missing"), f"{quality_summary['columns_with_missing']:,}")
    metric_columns[3].metric(t(language, "duplicate_rows"), f"{quality_summary['duplicate_rows']:,}")

    if quality_df.empty:
        st.success(t(language, "no_quality_issues"))
        return

    issue_summary = summarize_issue_types(quality_df)
    st.dataframe(localize_dataframe(issue_summary, language), use_container_width=True, hide_index=True)

    st.caption(t(language, "severity_caption"))
    st.dataframe(localize_dataframe(quality_df, language), use_container_width=True, hide_index=True)


def render_eda_report(df: pd.DataFrame, eda_df: pd.DataFrame) -> None:
    st.subheader(t(language, "eda_report"))

    if eda_df.empty:
        st.warning(t(language, "no_eda_recommendations"))
        return

    display_eda_df = eda_df.copy()
    if language == "zh":
        localized_titles = []
        localized_rationales = []
        for recommendation in eda_df.to_dict("records"):
            localized_titles.append(_localized_recommendation_title(recommendation))
            localized_rationales.append(_localized_recommendation_rationale(recommendation))
        display_eda_df["title"] = localized_titles
        display_eda_df["rationale"] = localized_rationales

    st.dataframe(localize_dataframe(display_eda_df, language), use_container_width=True, hide_index=True)

    for recommendation in eda_df.to_dict("records"):
        with st.container(border=True):
            st.markdown(f"**{_localized_recommendation_title(recommendation)}**")
            st.caption(_localized_recommendation_rationale(recommendation))
            _render_recommended_chart(df, recommendation)


def _render_recommended_chart(df: pd.DataFrame, recommendation: dict[str, object]) -> None:
    analysis_type = str(recommendation["analysis_type"])
    columns = recommendation["columns"]

    if analysis_type == "numeric_distribution":
        column = columns[0]
        chart_df = pd.DataFrame({column: pd.to_numeric(df[column], errors="coerce")}).dropna()
        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(f"{column}:Q", bin=alt.Bin(maxbins=30), title=column),
                y=alt.Y("count():Q", title=t(language, "count")),
                tooltip=[alt.Tooltip(f"{column}:Q", bin=True), alt.Tooltip("count():Q")],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    if analysis_type in {"category_distribution", "target_distribution"}:
        column = columns[0]
        chart_df = build_category_counts(df, column)
        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title=t(language, "count")),
                y=alt.Y(f"{column}:N", sort="-x", title=column),
                tooltip=[column, "count"],
            )
            .properties(height=max(260, min(520, len(chart_df) * 28)))
        )
        st.altair_chart(chart, use_container_width=True)
        return

    if analysis_type == "time_trend":
        column = columns[0]
        chart_df = build_time_trend(df, column)
        if chart_df.empty:
            st.info(t(language, "no_valid_datetime_values"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{column}:T", title=column),
                y=alt.Y("count:Q", title=t(language, "count")),
                tooltip=[column, "count"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    if analysis_type == "target_by_category":
        category_column, target_column = columns
        chart_df = build_target_by_category(df, category_column, target_column)
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        if "target_rate" in chart_df.columns:
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{category_column}:N", sort="-y", title=category_column),
                    y=alt.Y("target_rate:Q", title=t(language, "target_rate"), axis=alt.Axis(format="%")),
                    tooltip=[category_column, "count", alt.Tooltip("target_rate:Q", format=".1%")],
                )
                .properties(height=300)
            )
        else:
            chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X(f"{category_column}:N", title=category_column),
                    y=alt.Y("count:Q", title=t(language, "count")),
                    color=alt.Color(f"{target_column}:N", title=target_column),
                    tooltip=[category_column, target_column, "count"],
                )
                .properties(height=300)
            )
        st.altair_chart(chart, use_container_width=True)
        return

    if analysis_type == "correlation_heatmap":
        chart_df = build_correlation_pairs(df, columns)
        if chart_df.empty:
            st.info(t(language, "not_enough_data_for_chart"))
            return

        chart = (
            alt.Chart(chart_df)
            .mark_rect()
            .encode(
                x=alt.X("feature_x:N", title=""),
                y=alt.Y("feature_y:N", title=""),
                color=alt.Color("correlation:Q", scale=alt.Scale(scheme="redblue", domain=[-1, 1])),
                tooltip=["feature_x", "feature_y", "correlation"],
            )
            .properties(height=340)
        )
        st.altair_chart(chart, use_container_width=True)
        return

    st.info(t(language, "unsupported_chart"))


def _localized_recommendation_title(recommendation: dict[str, object]) -> str:
    if language == "en":
        return str(recommendation["title"])

    analysis_type = str(recommendation["analysis_type"])
    columns = recommendation["columns"]
    if analysis_type == "numeric_distribution":
        return f"{columns[0]} 的数值分布"
    if analysis_type == "category_distribution":
        return f"{columns[0]} 的主要类别"
    if analysis_type == "time_trend":
        return f"按 {columns[0]} 的记录趋势"
    if analysis_type == "target_distribution":
        return f"{columns[0]} 的目标变量分布"
    if analysis_type == "target_by_category":
        return f"{columns[1]} 按 {columns[0]} 分组对比"
    if analysis_type == "correlation_heatmap":
        return "数值特征相关性"
    return str(recommendation["title"])


def _localized_recommendation_rationale(recommendation: dict[str, object]) -> str:
    if language == "en":
        return str(recommendation["rationale"])

    rationales = {
        "numeric_distribution": "数值特征需要检查分布范围、偏态以及是否存在不寻常取值。",
        "category_distribution": "类别特征需要检查是否存在占比很高的主导类别或长尾类别。",
        "time_trend": "时间字段可以用于趋势分析和季节性检查。",
        "target_distribution": "目标变量在建模前需要检查类别是否平衡。",
        "target_by_category": "按类别对比目标变量，可以发现不同用户分组或业务分组的差异。",
        "correlation_heatmap": "相关性分析可以发现数值特征之间的关系和潜在冗余。",
    }
    return rationales.get(str(recommendation["analysis_type"]), str(recommendation["rationale"]))


def render_insight_report(result: object) -> None:
    st.subheader(t(language, "insight_report"))

    st.info(result.summary)
    if result.llm_error:
        st.warning(result.llm_error)

    st.dataframe(localize_dataframe(result.insights, language), use_container_width=True, hide_index=True)

    if result.llm_output:
        st.markdown(f"### {t(language, 'llm_report')}")
        st.markdown(result.llm_output)


def render_markdown_report(
    dataset_name: str,
    markdown_report: str,
    html_report: str,
) -> None:
    st.subheader(t(language, "report_section"))

    download_columns = st.columns(2)
    download_columns[0].download_button(
        label=t(language, "download_report"),
        data=markdown_report.encode("utf-8"),
        file_name=f"{_slugify_filename(dataset_name)}_analysis_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    download_columns[1].download_button(
        label=t(language, "download_html_report"),
        data=html_report.encode("utf-8"),
        file_name=f"{_slugify_filename(dataset_name)}_analysis_report.html",
        mime="text/html",
        use_container_width=True,
    )

    with st.expander(t(language, "report_preview"), expanded=False):
        st.markdown(markdown_report)


def render_workflow_steps(workflow_result: object) -> None:
    st.subheader(t(language, "workflow_steps"))
    st.dataframe(
        localize_dataframe(workflow_steps_to_dataframe(workflow_result.steps), language),
        use_container_width=True,
        hide_index=True,
    )


def render_rag_qa(workflow_result: object) -> None:
    st.subheader(t(language, "rag_qa"))
    question = st.text_input(
        t(language, "rag_question"),
        placeholder=t(language, "rag_question_placeholder"),
    )
    if not question.strip():
        return

    qa_result = answer_user_question(
        question=question,
        workflow_result=workflow_result,
        knowledge_dir=ROOT_DIR / "knowledge_base",
        language=language,
        use_llm=insight_mode == "llm",
        llm_config=runtime_llm_config,
    )
    if qa_result.error:
        st.warning(qa_result.error)
    st.markdown(f"### {t(language, 'rag_answer')}")
    st.markdown(qa_result.answer)

    with st.expander(t(language, "rag_sources"), expanded=False):
        st.dataframe(localize_dataframe(qa_result.retrieved_df, language), use_container_width=True, hide_index=True)


def _slugify_filename(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_").lower()
    return slug or "dataset"


if uploaded_file is None and selected_sample == t(language, "none"):
    st.info(t(language, "start_upload"))

    sample_path = ROOT_DIR / "sample_data" / "customer_churn_sample.csv"
    if sample_path.exists():
        st.subheader(t(language, "sample_preview"))
        sample_df = pd.read_csv(sample_path)
        st.dataframe(sample_df.head(), use_container_width=True)
else:
    try:
        if uploaded_file is not None:
            dataset_name = uploaded_file.name
            selected_sheet = None
            if is_excel_file(uploaded_file.name):
                sheet_names = list_excel_sheets(uploaded_file)
                selected_sheet = st.selectbox(t(language, "select_excel_sheet"), sheet_names)

            df = load_dataset(uploaded_file, uploaded_file.name, sheet_name=selected_sheet)
        else:
            dataset_name = f"{selected_sample}.csv"
            df = pd.read_csv(sample_options[selected_sample])
    except Exception as exc:
        st.error(t(language, "load_error", error=exc))
        st.stop()

    workflow_result = run_analysis_workflow(
        df=df,
        config=WorkflowConfig(
            dataset_name=dataset_name,
            language=language,
            use_llm=insight_mode == "llm",
            llm_config=runtime_llm_config,
        ),
    )

    render_workflow_steps(workflow_result)

    st.subheader(t(language, "dataset_overview"))
    render_summary(workflow_result.dataset_summary)

    profile_df = workflow_result.profile_df
    render_profiler(profile_df)

    quality_df = workflow_result.quality_df
    render_quality_report(df, quality_df)

    eda_df = workflow_result.eda_df
    render_eda_report(df, eda_df)

    insight_result = workflow_result.insight_result
    render_insight_report(insight_result)

    render_markdown_report(
        dataset_name=dataset_name,
        markdown_report=workflow_result.markdown_report,
        html_report=workflow_result.html_report,
    )

    render_rag_qa(workflow_result)

    st.subheader(t(language, "data_preview"))
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader(t(language, "column_overview"))
    st.dataframe(localize_dataframe(workflow_result.column_overview, language), use_container_width=True)
