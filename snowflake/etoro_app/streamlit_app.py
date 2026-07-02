"""
eToro Portfolio Dashboard
Streamlit in Snowflake application.
Requires: Python 3.8+, snowflake-snowpark-python (provided by SiS runtime)
"""

import streamlit as st
import pandas as pd
import altair as alt
from snowflake.snowpark.context import get_active_session

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="eToro Portfolio",
    page_icon="📈",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* Metric card overrides */
[data-testid="stMetric"] {
    background: var(--background-color, #f8f9fa);
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 10px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"] { font-size: 0.75rem; opacity: 0.65; }
[data-testid="stMetricValue"] { font-family: monospace; font-size: 1.4rem; }

/* Tighten sidebar */
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }

/* Table font */
[data-testid="stDataFrame"] { font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ── Snowpark session ───────────────────────────────────────────────────────────

@st.cache_resource
def get_session():
    return get_active_session()

session = get_session()

# ── SQL queries ────────────────────────────────────────────────────────────────

SQL_CURRENT_POSITIONS = """
select
    lp.* 
from etoro_portfolio.etoro_portfolio_marts.profit_loss lp
join 
    (select instrument_id, max(price_timestamp) as max_timestamp from etoro_portfolio.etoro_portfolio_marts.profit_loss group by 1) lat
on lp.instrument_id = lat.instrument_id
where price_timestamp = max_timestamp
;
"""

SQL_CASH = """
SELECT 
    *
FROM ETORO_PORTFOLIO.ETORO_PORTFOLIO_MARTS.CASH_POSITIONS
;
"""

SQL_INSTRUMENTS = """
SELECT
    *
FROM ETORO_PORTFOLIO.ETORO_PORTFOLIO_MARTS.INSTRUMENTS
;
"""

SQL_TIME_SERIES = """
WITH portfolio AS
(
    SELECT 
        *
    FROM ETORO_PORTFOLIO.ETORO_PORTFOLIO_MARTS.PROFIT_LOSS
)
SELECT
    price_timestamp,
    SUM(opening_amount + profit_loss) AS total_value,
    SUM(opening_amount) AS total_opened
FROM portfolio p
GROUP BY price_timestamp
ORDER BY price_timestamp ASC;
"""

# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)   # refresh every 5 minutes
def load_data():
    pos_df   = session.sql(SQL_CURRENT_POSITIONS).to_pandas()
    cash_df  = session.sql(SQL_CASH).to_pandas()
    inst_df  = session.sql(SQL_INSTRUMENTS).to_pandas()
    ts_df    = session.sql(SQL_TIME_SERIES).to_pandas()
    return pos_df, cash_df, inst_df, ts_df

# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_currency(v: float, decimals: int = 0) -> str:
    if v is None:
        return "—"
    prefix = "-$" if v < 0 else "$"
    return prefix + f"{abs(v):,.{decimals}f}"

def fmt_pct(v: float, decimals: int = 1) -> str:
    return f"{v*100:.{decimals}f}%"

def delta_str(v: float, pct: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"{sign}{fmt_currency(v)} ({sign}{fmt_pct(pct)})"

# ── Main app ───────────────────────────────────────────────────────────────────

st.title("📈 eToro Portfolio Dashboard")

with st.spinner("Loading portfolio data…"):
    try:
        pos_df, cash_df, inst_df, ts_df = load_data()
    except Exception as e:
        st.error(f"Failed to load data from Snowflake: {e}")
        st.stop()

# Normalise column names to lower-case for safety
pos_df.columns   = [c.lower() for c in pos_df.columns]
cash_df.columns  = [c.lower() for c in cash_df.columns]
inst_df.columns  = [c.lower() for c in inst_df.columns]
ts_df.columns    = [c.lower() for c in ts_df.columns]

# Join instrument metadata onto positions
pos_df = pos_df.merge(inst_df, on="instrument_id", how="left")

# ── KPI calculations ───────────────────────────────────────────────────────────

total_invested = pos_df["opening_amount"].sum()
total_current  = pos_df["current_amount"].sum()
total_pl       = pos_df["profit_loss"].sum()
total_cash     = cash_df["amount"].sum()
grand_total    = total_current + total_cash
liquidity      = total_cash / grand_total if grand_total > 0 else 0
pl_pct         = total_pl / total_invested if total_invested > 0 else 0
last_refresh   = pd.to_datetime(pos_df["price_timestamp"].max()).strftime("%d %b %Y %H:%M")

# ── Hero banner ────────────────────────────────────────────────────────────────

col_val, col_pl, col_ts = st.columns([2, 2, 1])

with col_val:
    st.metric(
        label="Total portfolio value",
        value=fmt_currency(grand_total),
        help="Current invested value + available cash",
    )

with col_pl:
    pl_sign = "+" if total_pl >= 0 else ""
    st.metric(
        label="Unrealised P&L",
        value=f"{pl_sign}{fmt_currency(total_pl)}",
        delta=f"{pl_sign}{fmt_pct(pl_pct)} return on invested capital",
        delta_color="normal",
        help="Total returns on currently open positions",
    )

with col_ts:
    st.caption("Last refreshed")
    st.markdown(f"**{last_refresh}**")

st.divider()

# ── KPI strip ─────────────────────────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)

k1.metric("Invested capital",  fmt_currency(total_invested), help="Sum of all opening amounts")
k2.metric("Current value",     fmt_currency(total_current),  help="Mark-to-market value of open positions")
k3.metric("Cash available",    fmt_currency(total_cash),     help="Available credit across all mirrors")
k4.metric("Cash Liquidity",         fmt_pct(liquidity),           help="Cash ÷ total portfolio value")

st.divider()

# ── Time series chart ──────────────────────────────────────────────────────────

st.subheader("Portfolio value over time")

range_options = {"All": None, "30 days": 30, "7 days": 7}

ts_plot = ts_df.copy()
ts_plot["price_timestamp"] = pd.to_datetime(ts_plot["price_timestamp"])

# ── Controls row ───────────────────────────────────────────────────────────────
ctl_left, ctl_right = st.columns([3, 1])
with ctl_left:
    ts_range = st.radio(
        "Range",
        options=list(range_options.keys()),
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )
with ctl_right:
    show_invested = st.toggle("Show Amount Invested", value=False)

# ── Filter data ───────────────────────────────────────────────────────────────
if range_options[ts_range]:
    cutoff = ts_plot["price_timestamp"].max() - pd.Timedelta(days=range_options[ts_range])
    ts_plot = ts_plot[ts_plot["price_timestamp"] >= cutoff]

start_val = ts_plot["total_value"].iloc[0] if len(ts_plot) else 0
end_val   = ts_plot["total_value"].iloc[-1] if len(ts_plot) else 0
line_color = "#3B6D11" if end_val >= start_val else "#A32D2D"

# ── Chart ──────────────────────────────────────────────────────────────────────
area = (
    alt.Chart(ts_plot)
    .mark_area(
        line={"color": line_color, "strokeWidth": 1.5},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=line_color, offset=0),
                alt.GradientStop(color="white",    offset=1),
            ],
            x1=1, x2=1, y1=1, y2=0,
        ),
        opacity=0.12,
    )
    .encode(
        x=alt.X("price_timestamp:T", title=None, axis=alt.Axis(labelFontSize=11)),
        y=alt.Y("total_value:Q", title="Value ($)", axis=alt.Axis(labelFontSize=11, format="$,.0f")),
        tooltip=[
            alt.Tooltip("price_timestamp:T", title="Date", format="%d %b %Y %H:%M"),
            alt.Tooltip("total_value:Q", title="Value", format="$,.2f"),
        ],
    )
)

ts_chart = area

if show_invested:
    ts_plot["roi"] = (ts_plot["total_value"] / ts_plot["total_opened"]) - 1
    invested_line = (
        alt.Chart(ts_plot)
        .mark_line(strokeWidth=1.8, strokeDash=[4, 3], color="#888888")
        .encode(
            x=alt.X("price_timestamp:T"),
            y=alt.Y("total_opened:Q"),
            tooltip=[
                alt.Tooltip("price_timestamp:T", title="Date", format="%d %b %Y %H:%M"),
                alt.Tooltip("total_opened:Q", title="Invested", format="$,.2f"),
                alt.Tooltip("roi:Q", title="ROI", format = ".1%"),
            ],
        )
    )
    ts_chart = ts_chart + invested_line

ts_chart = ts_chart.properties(height=240).interactive()
st.altair_chart(ts_chart, use_container_width=True)

st.divider()

# ── Bottom row: exposure + positions ──────────────────────────────────────────

group_labels = {
    "Sector":     "sector_name",
    "Mirror":     "mirror_name",
    "Industry":   "industry_name",
    "Instrument": "symbol",
}
selected_label = st.segmented_control(
    "Group by",
    options=list(group_labels.keys()),
    default="Sector",
    label_visibility="collapsed",
)
group_col = group_labels[selected_label]
group_label = next(k for k, v in group_labels.items() if v == group_col)


left, right = st.columns([1, 1.7], gap="medium")

# ── Exposure donut ─────────────────────────────────────────────────────────────

with left:
    st.subheader("Exposure breakdown")

    exp_df = (
        pos_df.groupby(group_col, dropna=False)["current_amount"]
        .sum()
        .reset_index()
        .rename(columns={group_col: "group", "current_amount": "value"})
        .sort_values("value", ascending=False)
    )
    exp_df["group"]   = exp_df["group"].fillna("Unknown")
    exp_df["pct"]     = exp_df["value"] / exp_df["value"].sum()
    exp_df["label"]   = exp_df["group"] + " — " + (exp_df["pct"] * 100).round(1).astype(str) + "%"

    donut = (
        alt.Chart(exp_df)
        .mark_arc(innerRadius=70, outerRadius=110)
        .encode(
            theta=alt.Theta("value:Q"),
            color=alt.Color(
                "group:N",
                legend=alt.Legend(title=None, orient="bottom", columns=2, labelFontSize=11),
                scale=alt.Scale(scheme="tableau10"),
            ),
            tooltip=[
                alt.Tooltip("group:N",  title=selected_label),
                alt.Tooltip("value:Q",  title="Value",    format="$,.0f"),
                alt.Tooltip("pct:Q",    title="Exposure", format=".1%"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(donut, use_container_width=True)

# ── Positions table ────────────────────────────────────────────────────────────

with right:
    st.subheader("Current positions")

    tbl = pos_df[[
        "symbol", "display_name", "mirror_name", "is_buy",
        "opening_amount", "current_amount", "profit_loss", "gross_exposure",
        "leverage", "sector_name", "industry_name",
    ]].copy()

    tbl["direction"]     = tbl["is_buy"].map({True: "Buy", False: "Sell"})
    tbl["gross_exposure"] = (tbl["gross_exposure"] * 100).round(2)
    tbl["opening_amount"] = tbl["opening_amount"].round(2)
    tbl["current_amount"] = tbl["current_amount"].round(2)
    tbl["profit_loss"]    = tbl["profit_loss"].round(2)

    grouped_tbl = (
        tbl.groupby(group_col, dropna=False)[["opening_amount", "current_amount", "profit_loss", "gross_exposure"]]
        .sum()
        .reset_index()
        .rename(columns={
            group_col: group_label,
            "opening_amount": "Opened ($)",
            "current_amount": "Current ($)",
            "profit_loss": "P&L ($)",
            "gross_exposure": "Exposure (%)",
        })
        .sort_values("Current ($)", ascending=False)
        .reset_index(drop=True)
    )
    grouped_tbl[group_label] = grouped_tbl[group_label].fillna('Unknown')

    st.dataframe(
        grouped_tbl,
        use_container_width=True,
        height=380,
        column_config={
            "P&L ($)": st.column_config.NumberColumn(format="%.2f"),
            "Current ($)": st.column_config.NumberColumn(format="%.2f"),
            "Opened ($)":  st.column_config.NumberColumn(format="%.2f"),
            "Exposure (%)": st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.1f%%"
            ),
        },
        hide_index=True,
    )

# ── Cash breakdown (expandable) ────────────────────────────────────────────────

with st.expander("Cash positions by mirror"):
    cash_tbl = cash_df[["mirror_name", "display_name", "amount"]].copy()
    cash_tbl.columns = ["Mirror", "Display name", "Cash ($)"]
    cash_tbl["Cash ($)"] = cash_tbl["Cash ($)"].round(2)
    cash_tbl["% of total cash"] = (cash_tbl["Cash ($)"] / cash_tbl["Cash ($)"].sum() * 100).round(1)
    st.dataframe(cash_tbl, use_container_width=True, hide_index=True)

# ── Footer ─────────────────────────────────────────────────────────────────────

st.caption(
    f"Data cached for 5 minutes · Source: ETORO_PORTFOLIO.DBT_SYELLOPS01_MARTS · "
    f"Refreshed: {last_refresh}"
)
