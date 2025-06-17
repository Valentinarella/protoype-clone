import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(page_title="Environmental Nonprofit Insights", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {background-color: #f5f9f5;}
    .stSidebar {background-color: #e8f0e8;}
    .stMetric {background-color: #ffffff; border-radius: 8px; padding: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    .stButton>button {background-color: #2e7d32; color: white; border-radius: 5px;}
    h1, h2, h3 {color: #1b5e20;}
    </style>
""", unsafe_allow_html=True)

# Cache data loading
@st.cache_data
def load_data(filepath, usecols=None):
    try:
        return pd.read_csv(filepath, usecols=usecols, low_memory=False)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Define dataset paths
file_paths = {
    "EOBMF": "https://undivideprojectdata.blob.core.windows.net/seed/Updated%20Regional%20Giving%20Data%20IRS%20eo1.csv?sp=racw&st=2025-06-07T20:33:32Z&se=3000-06-08T04:33:32Z&spr=https&sv=2024-11-04&sr=b&sig=BXUnVCyoMn0IKkOxHB8NjdWhJMMuPvPzYWMHleH6D60%3D",
    "Form990": "https://undivideprojectdata.blob.core.windows.net/seed/23eoextract990_1.csv?sp=r&st=2025-06-07T21:22:51Z&se=3000-06-08T05:22:51Z&spr=https&sv=2024-11-04&sr=b&sig=2QFpGrnt7ZiSSS%2B6frNp1h%2BxflyHhnleAgcqk%2BY72lw%3D",
}

# Load data with essential columns
usecols = {
    "EOBMF": ["EIN", "NTEE_CD", "STATE", "REVENUE_AMT"],
    "Form990": ["ein", "totassetsend", "totrevenue", "totfuncexpns", "payrolltx"],
}

df_bmf = load_data(file_paths["EOBMF"], usecols["EOBMF"])
df_990 = load_data(file_paths["Form990"], usecols["Form990"])

# Filter environmental nonprofits (NTEE codes C30-C60)
env_ntee_codes = [f"C{i}" for i in range(30, 61)]
df_env_bmf = df_bmf[df_bmf["NTEE_CD"].astype(str).str.startswith(tuple(env_ntee_codes), na=False)]
env_eins = set(df_env_bmf["EIN"].astype(str))
df_env_990 = df_990[df_990["ein"].astype(str).isin(env_eins)]

# Ensure numeric columns
for col in ["totassetsend", "totrevenue", "totfuncexpns", "payrolltx"]:
    df_env_990[col] = pd.to_numeric(df_env_990[col], errors="coerce")

# Sidebar
with st.sidebar:
    st.header("🔍 Filter Options")
    nonprofit_size = st.selectbox(
        "Nonprofit Size",
        ["All", "Small (<$1M)", "Medium ($1M-$10M)", "Large (>$10M)"],
        help="Filter by total assets"
    )
    state_filter = st.multiselect(
        "Select States",
        options=sorted(df_env_bmf["STATE"].dropna().unique()),
        default=[],
        help="Filter by state (leave empty for all)"
    )
    st.markdown("---")
    st.markdown("**Data Source**: IRS 2023 Filings")

# Apply filters
df_filtered = df_env_990
if nonprofit_size == "Small (<$1M)":
    df_filtered = df_env_990[df_env_990["totassetsend"] < 1_000_000]
elif nonprofit_size == "Medium ($1M-$10M)":
    df_filtered = df_env_990[(df_env_990["totassetsend"] >= 1_000_000) & (df_env_990["totassetsend"] <= 10_000_000)]
elif nonprofit_size == "Large (>$10M)":
    df_filtered = df_env_990[df_env_990["totassetsend"] > 10_000_000]

if state_filter:
    df_filtered = df_filtered[df_filtered["ein"].isin(df_env_bmf[df_env_bmf["STATE"].isin(state_filter)]["EIN"].astype(str))]

# Main content
st.title("🌍 Environmental Nonprofit Insights (2023)")

# Summary statistics
def compute_summary_stats(df):
    return {
        "Total Nonprofits": len(df),
        "Average Assets ($)": df["totassetsend"].mean() if not df["totassetsend"].isna().all() else 0,
        "Average Revenue ($)": df["totrevenue"].mean() if not df["totrevenue"].isna().all() else 0,
        "Average Expenses ($)": df["totfuncexpns"].mean() if not df["totfuncexpns"].isna().all() else 0,
    }

stats = compute_summary_stats(df_filtered)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Nonprofits", f"{stats['Total Nonprofits']:,}")
col2.metric("Avg. Assets", f"${stats['Average Assets ($)']:,.0f}")
col3.metric("Avg. Revenue", f"${stats['Average Revenue ($)']:,.0f}")
col4.metric("Avg. Expenses", f"${stats['Average Expenses ($)']:,.0f}")

# Visualizations in tabs
tab1, tab2, tab3 = st.tabs(["📊 Funding by State", "💰 Spending Breakdown", "📈 Financial Trends"])

with tab1:
    st.subheader("Funding by State")
    state_funding = df_env_bmf[df_env_bmf["STATE"].isin(state_filter) if state_filter else df_env_bmf["STATE"].notna()].groupby("STATE")["REVENUE_AMT"].sum().reset_index()
    state_funding.columns = ["State", "Total Revenue"]
    top_states = state_funding.sort_values("Total Revenue", ascending=False).head(10)
    fig_bar = px.bar(
        top_states,
        x="Total Revenue",
        y="State",
        orientation="h",
        color="Total Revenue",
        color_continuous_scale="Viridis",
        text="Total Revenue",
        height=400,
    )
    fig_bar.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_bar.update_layout(
        xaxis_title="Total Revenue (USD)",
        yaxis_title="State",
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.subheader("Program vs. Administrative Spending")
    df_expenses = pd.DataFrame({
        "Expense Type": ["Program Expenses", "Administrative Expenses"],
        "Amount ($)": [df_filtered["totfuncexpns"].sum(), df_filtered["payrolltx"].sum()]
    })
    fig_pie = px.pie(
        df_expenses,
        names="Expense Type",
        values="Amount ($)",
        color="Expense Type",
        color_discrete_map={"Program Expenses": "#2e7d32", "Administrative Expenses": "#81c784"},
        height=400,
    )
    fig_pie.update_traces(textinfo="percent+label", pull=[0.1, 0])
    fig_pie.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)
    program_pct = (df_expenses["Amount ($)"][0] / df_expenses["Amount ($)"].sum() * 100) if df_expenses["Amount ($)"].sum() > 0 else 0
    st.markdown(f"**Insight**: {program_pct:.1f}% of spending supports programs, reflecting a strong mission focus.")

with tab3:
    st.subheader("Financial Metrics Comparison")
    metrics = ["totassetsend", "totrevenue", "totfuncexpns"]
    fig_radar = go.Figure()
    for size in ["Small (<$1M)", "Medium ($1M-$10M)", "Large (>$10M)"]:
        temp_df = df_env_990
        if size == "Small (<$1M)":
            temp_df = df_env_990[df_env_990["totassetsend"] < 1_000_000]
        elif size == "Medium ($1M-$10M)":
            temp_df = df_env_990[(df_env_990["totassetsend"] >= 1_000_000) & (df_env_990["totassetsend"] <= 10_000_000)]
        elif size == "Large (>$10M)":
            temp_df = df_env_990[df_env_990["totassetsend"] > 10_000_000]
        values = [temp_df[m].mean() / 1_000_000 for m in metrics]
        fig_radar.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=["Assets", "Revenue", "Expenses"] + ["Assets"],
            name=size,
            line=dict(width=2)
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max([df_env_990[m].mean() / 1_000_000 for m in metrics]) * 1.2])),
        showlegend=True,
        height=400,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# About the data
with st.expander("📖 About the Data", expanded=False):
    st.markdown("""
        This dashboard analyzes environmental nonprofits (NTEE codes C30-C60) using IRS Form 990 and EOBMF data.
        - **EOBMF**: Nonprofit classifications and revenue.
        - **Form 990**: Financials including assets, revenue, and expenses.
        **Source**: IRS 2023 filings.
    """)
