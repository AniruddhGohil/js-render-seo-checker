import io
import json
import subprocess
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image


@st.cache_resource(show_spinner=False)
def _install_playwright_browsers():
    """Install Playwright's Chromium browser once per server session (needed on cloud)."""
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
    except Exception:
        pass  # Already installed or will surface as a render error


_install_playwright_browsers()

from analyzer.comparator import compare_elements
from analyzer.extractor import extract_seo_elements
from analyzer.raw_fetcher import fetch_raw_html
from analyzer.renderer import render_page

st.set_page_config(
    page_title="JS Render SEO Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 8px; }
    div[data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 JS Rendering SEO Checker")
st.caption(
    "Compare raw vs rendered HTML to detect JavaScript SEO issues affecting crawlability and indexation."
)

# ── Input form ──────────────────────────────────────────────────────────────
with st.form("analysis_form"):
    url_input = st.text_input(
        "URL to Analyze",
        placeholder="https://example.com",
        help="Enter the full URL (https:// will be added automatically if missing).",
    )
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        render_mode = st.selectbox(
            "Render Mode",
            ["Normal Browser", "Googlebot Simulation"],
            help="Googlebot mode uses the official Googlebot user-agent string.",
        )
    with col2:
        wait_ms = st.slider(
            "JS Wait Time (ms)",
            min_value=1000,
            max_value=10000,
            value=3000,
            step=500,
            help="Extra time to wait after page load for JavaScript frameworks to hydrate.",
        )
    with col3:
        st.write("")
        st.write("")
        submitted = st.form_submit_button("🚀 Analyze", type="primary", use_container_width=True)

# ── Analysis ─────────────────────────────────────────────────────────────────
if submitted:
    if not url_input:
        st.warning("Please enter a URL.")
        st.stop()

    url = url_input.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    use_googlebot = render_mode == "Googlebot Simulation"

    progress = st.progress(0, text="Fetching raw HTML…")
    raw_result = fetch_raw_html(url, use_googlebot=use_googlebot)

    if "error" in raw_result:
        st.error(f"Failed to fetch URL: {raw_result['error']}")
        st.stop()

    progress.progress(33, text="Rendering page with JavaScript…")
    render_result = render_page(url, use_googlebot=use_googlebot, wait_ms=wait_ms)

    if "error" in render_result:
        st.error(f"Rendering failed: {render_result['error']}")
        st.stop()

    progress.progress(66, text="Comparing SEO elements…")
    raw_seo = extract_seo_elements(raw_result["html"], base_url=url)
    rendered_seo = extract_seo_elements(render_result["html"], base_url=url)
    comparison = compare_elements(raw_seo, rendered_seo)
    progress.progress(100, text="Done!")
    progress.empty()

    st.success(f"Analysis complete — **{url}**  |  Mode: **{render_mode}**")
    st.divider()

    # ── Summary metrics ──────────────────────────────────────────────────────
    score = comparison["seo_score"]
    score_delta = "Good" if score >= 80 else ("Needs attention" if score >= 50 else "Critical issues")
    js_dep = comparison["js_dependency_score"]

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("SEO Score", f"{score} / 100", delta=score_delta,
              delta_color="normal" if score >= 70 else "inverse")
    m2.metric("JS Dependency", f"{js_dep:.1f}%",
              delta="High" if js_dep > 40 else ("Moderate" if js_dep > 20 else "Low"),
              delta_color="inverse" if js_dep > 40 else "normal")
    m3.metric("Issues Found", comparison["issue_count"])
    m4.metric("Render Time", f"{render_result['render_time']}s")
    m5.metric("JS Files Loaded", render_result["js_resource_count"])

    st.divider()

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_issues, tab_content, tab_links, tab_charts, tab_screenshot = st.tabs([
        "🚨 SEO Issues",
        "📝 Content Analysis",
        "🔗 Internal Links",
        "📊 Charts",
        "📸 Screenshot",
    ])

    # ── Tab 1: SEO Issues ────────────────────────────────────────────────────
    with tab_issues:
        st.subheader("JavaScript Rendering Issues")

        if comparison["issues"]:
            severity_icon = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
            issues_df = pd.DataFrame(comparison["issues"])
            issues_df["severity"] = issues_df["severity"].apply(
                lambda s: f"{severity_icon.get(s, '')} {s}"
            )
            st.dataframe(
                issues_df[["severity", "element", "issue", "raw", "rendered"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "severity": st.column_config.TextColumn("Severity", width="small"),
                    "element": st.column_config.TextColumn("SEO Element", width="small"),
                    "issue": st.column_config.TextColumn("Issue"),
                    "raw": st.column_config.TextColumn("Raw HTML"),
                    "rendered": st.column_config.TextColumn("Rendered HTML"),
                },
            )
        else:
            st.success("No JavaScript rendering issues detected. The page renders cleanly.")

        st.subheader("Full SEO Elements Comparison")
        elements = [
            ("Title", raw_seo.get("title"), rendered_seo.get("title")),
            ("Meta Description", raw_seo.get("meta_description"), rendered_seo.get("meta_description")),
            ("Canonical URL", raw_seo.get("canonical"), rendered_seo.get("canonical")),
            ("Robots Meta", raw_seo.get("robots"), rendered_seo.get("robots")),
            ("H1 Count", len(raw_seo.get("h1", [])), len(rendered_seo.get("h1", []))),
            ("H2 Count", len(raw_seo.get("h2", [])), len(rendered_seo.get("h2", []))),
            ("H3 Count", len(raw_seo.get("h3", [])), len(rendered_seo.get("h3", []))),
            ("Internal Links", raw_seo["internal_link_count"], rendered_seo["internal_link_count"]),
            ("External Links", raw_seo["external_link_count"], rendered_seo["external_link_count"]),
            ("Structured Data", len(raw_seo.get("structured_data", [])), len(rendered_seo.get("structured_data", []))),
            ("Images", raw_seo["image_count"], rendered_seo["image_count"]),
            ("Images Missing Alt", raw_seo["images_without_alt"], rendered_seo["images_without_alt"]),
            ("Word Count", raw_seo["word_count"], rendered_seo["word_count"]),
        ]
        comp_df = pd.DataFrame(elements, columns=["Element", "Raw HTML", "Rendered HTML"])
        comp_df["Match"] = comp_df.apply(
            lambda r: "✅" if str(r["Raw HTML"]) == str(r["Rendered HTML"]) else "⚠️ Differs",
            axis=1,
        )
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # ── Tab 2: Content Analysis ──────────────────────────────────────────────
    with tab_content:
        st.subheader("Content Comparison")

        col_raw, col_rend = st.columns(2)

        with col_raw:
            st.markdown("#### Raw HTML")
            st.metric("Word Count", f"{raw_seo['word_count']:,}")
            if raw_seo.get("title"):
                st.markdown(f"**Title:** {raw_seo['title']}")
            else:
                st.warning("No `<title>` tag found")
            if raw_seo.get("h1"):
                st.markdown("**H1 Tags:**")
                for h in raw_seo["h1"]:
                    st.write(f"• {h}")
            else:
                st.warning("No H1 found")
            if raw_seo.get("meta_description"):
                st.markdown(f"**Meta Description:** {raw_seo['meta_description']}")
            else:
                st.warning("No meta description found")

        with col_rend:
            st.markdown("#### Rendered HTML")
            st.metric("Word Count", f"{rendered_seo['word_count']:,}")
            if rendered_seo.get("title"):
                st.markdown(f"**Title:** {rendered_seo['title']}")
            else:
                st.warning("No `<title>` tag found")
            if rendered_seo.get("h1"):
                st.markdown("**H1 Tags:**")
                for h in rendered_seo["h1"]:
                    st.write(f"• {h}")
            else:
                st.warning("No H1 found")
            if rendered_seo.get("meta_description"):
                st.markdown(f"**Meta Description:** {rendered_seo['meta_description']}")
            else:
                st.warning("No meta description found")

        st.divider()
        st.subheader("JavaScript Content Dependency Score")
        raw_w = raw_seo["word_count"]
        rend_w = rendered_seo["word_count"]
        js_only_w = max(0, rend_w - raw_w)

        if js_dep > 20:
            msg = f"⚠️ **{js_dep:.1f}% of page content depends on JavaScript**"
            if js_dep > 60:
                st.error(msg)
            else:
                st.warning(msg)
            st.write(f"- Raw HTML: **{raw_w:,} words**")
            st.write(f"- Rendered HTML: **{rend_w:,} words**")
            st.write(f"- JS-only content: **{js_only_w:,} additional words** appear after rendering")
        else:
            st.success("✅ Content is substantially present in raw HTML — low JavaScript dependency.")

        if rendered_seo.get("structured_data"):
            st.divider()
            st.subheader("Structured Data (JSON-LD)")
            for i, schema in enumerate(rendered_seo["structured_data"][:5]):
                schema_type = schema.get("@type", "Unknown") if isinstance(schema, dict) else "Schema"
                with st.expander(f"Schema {i + 1}: {schema_type}"):
                    st.json(schema)

        if rendered_seo.get("og_tags"):
            st.divider()
            st.subheader("Open Graph Tags")
            og_df = pd.DataFrame(
                [{"Property": k, "Content": v} for k, v in rendered_seo["og_tags"].items()]
            )
            st.dataframe(og_df, use_container_width=True, hide_index=True)

    # ── Tab 3: Internal Links ────────────────────────────────────────────────
    with tab_links:
        st.subheader("Internal Links Analysis")

        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("Raw HTML Links", raw_seo["internal_link_count"])
        lc2.metric("Rendered HTML Links", rendered_seo["internal_link_count"])
        lc3.metric("JS-Only Links", len(comparison["new_internal_links"]))

        if comparison["new_internal_links"]:
            st.warning(
                f"⚠️ {len(comparison['new_internal_links'])} internal link(s) "
                "are only discoverable after JavaScript rendering — Googlebot may miss these."
            )
            js_df = pd.DataFrame(comparison["new_internal_links"])
            st.dataframe(
                js_df[["url", "anchor"]].rename(columns={"url": "URL", "anchor": "Anchor Text"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("All internal links are present in raw HTML.")

        if rendered_seo.get("internal_links"):
            with st.expander(f"All Internal Links ({rendered_seo['internal_link_count']})"):
                all_df = pd.DataFrame(rendered_seo["internal_links"])
                if not all_df.empty:
                    st.dataframe(
                        all_df[["url", "anchor"]].rename(columns={"url": "URL", "anchor": "Anchor Text"}),
                        use_container_width=True,
                        hide_index=True,
                    )

        if render_result.get("js_resources"):
            with st.expander(f"JavaScript Files Loaded ({render_result['js_resource_count']})"):
                for js_url in render_result["js_resources"][:60]:
                    st.code(js_url, language=None)

    # ── Tab 4: Charts ────────────────────────────────────────────────────────
    with tab_charts:
        st.subheader("Visualizations")

        # SEO Score Gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "JS Rendering SEO Score", "font": {"size": 16}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1},
                "bar": {"color": "#4e79a7"},
                "steps": [
                    {"range": [0, 40], "color": "#fee2e2"},
                    {"range": [40, 70], "color": "#fef3c7"},
                    {"range": [70, 100], "color": "#dcfce7"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 3},
                    "thickness": 0.75,
                    "value": 70,
                },
            },
        ))
        fig_gauge.update_layout(height=280, margin={"t": 40, "b": 0})
        st.plotly_chart(fig_gauge, use_container_width=True)

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Word count comparison
            fig_words = go.Figure(data=[
                go.Bar(name="Raw HTML", x=["Word Count"], y=[raw_seo["word_count"]],
                       marker_color="#4e79a7"),
                go.Bar(name="Rendered HTML", x=["Word Count"], y=[rendered_seo["word_count"]],
                       marker_color="#59a14f"),
            ])
            fig_words.update_layout(
                title="Word Count: Raw vs Rendered",
                barmode="group",
                height=320,
                margin={"t": 40, "b": 0},
            )
            st.plotly_chart(fig_words, use_container_width=True)

        with chart_col2:
            # Links comparison
            fig_links = go.Figure(data=[
                go.Bar(
                    name="Raw HTML",
                    x=["Internal Links", "External Links"],
                    y=[raw_seo["internal_link_count"], raw_seo["external_link_count"]],
                    marker_color="#4e79a7",
                ),
                go.Bar(
                    name="Rendered HTML",
                    x=["Internal Links", "External Links"],
                    y=[rendered_seo["internal_link_count"], rendered_seo["external_link_count"]],
                    marker_color="#59a14f",
                ),
            ])
            fig_links.update_layout(
                title="Links: Raw vs Rendered",
                barmode="group",
                height=320,
                margin={"t": 40, "b": 0},
            )
            st.plotly_chart(fig_links, use_container_width=True)

        if comparison["issues"]:
            sev_counts: dict[str, int] = {}
            for issue in comparison["issues"]:
                sev = issue["severity"]
                sev_counts[sev] = sev_counts.get(sev, 0) + 1

            fig_sev = go.Figure(data=[go.Pie(
                labels=list(sev_counts.keys()),
                values=list(sev_counts.values()),
                hole=0.45,
                marker_colors=["#dc3545", "#fd7e14", "#ffc107", "#28a745"],
            )])
            fig_sev.update_layout(
                title="Issues by Severity",
                height=300,
                margin={"t": 40, "b": 0},
            )
            st.plotly_chart(fig_sev, use_container_width=True)

    # ── Tab 5: Screenshot ────────────────────────────────────────────────────
    with tab_screenshot:
        st.subheader("Rendered Page Screenshot")
        st.caption(f"Mode: **{render_mode}** — JS wait: **{wait_ms}ms** — Render time: **{render_result['render_time']}s**")

        if render_result.get("screenshot"):
            image = Image.open(io.BytesIO(render_result["screenshot"]))
            st.image(image, caption=url, use_container_width=True)
        else:
            st.info("Screenshot not available.")

elif submitted:
    st.warning("Please enter a URL to analyze.")
