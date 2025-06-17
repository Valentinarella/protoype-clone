import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration
st.set_page_config(page_title="Nonprofit IRS 990 Dashboard", layout="wide")

# Cache data loading
@st.cache_data
def load_data(filepath, usecols=None):
    try:
        return pd.read_csv(filepath, usecols=usecols, low_memory=False)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Define dataset paths (only Form 990 and EOBMF)
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

# Sidebar filter for nonprofit size
st.sidebar.title("Filters")
nonprofit_size = st.sidebar.selectbox("Nonprofit Size", ["All", "Small (<$1M)", "Medium ($1M-$10M)", "Large (>$10M)"])

# Apply size filter
df_filtered = df_env_990
if nonprofit_size == "Small (<$1M)":
    df_filtered = df_env_990[df_env_990["totassetsend"] < 1_000_000]
elif nonprofit_size == "Medium ($1M-$10M)":
    df_filtered = df_env_990[(df_env_990["totassetsend"] >= 1_000_000) & (df_env_990["totassetsend"] <= 10_000_000)]
elif nonprofit_size == "Large (>$10M)":
    df_filtered = df_env_990[df_env_990["totassetsend"] > 10_000_000]

# Title
st.title("🌱 Environmental Nonprofit Dashboard (2023)")

# Summary statistics
def compute_summary_stats(df):
    return {
        "Total Nonprofits": len(df),
        "Average Assets ($)": df["totassetsend"].mean() if not df["totassetsend"].isna().all() else 0,
        "Average Revenue ($)": df["totrevenue"].mean() if not df["totrevenue"].isna().all() else 0,
        "Average Expenses ($)": df["totfuncexpns"].mean() if not df["totfuncexpns"].isna().all() else 0,
    }

stats = compute_summary_stats(df_filtered)
col1, col2, col3 = st.columns(3)
col1.metric("Total Nonprofits", f"{stats['Total Nonprofits']:,}")
col2.metric("Average Revenue", f"${stats['Average Revenue ($)']:,.2f}")
col3.metric("Average Expenses", f"${stats['Average Expenses ($)']:,.2f}")

# Funding by state (bar chart)
st.subheader("Funding by State")
state_funding = df_env_bmf.groupby("STATE")["REVENUE_AMT"].sum().reset_index().dropna()
state_funding.columns = ["State", "Total Revenue"]
top_states = state_funding.sort_values("Total Revenue", ascending=False).head(5)
fig_bar = px.bar(
    top_states,
    x="Total Revenue",
    y="State",
    orientation="h",
    title="Top 5 States by Nonprofit Revenue",
    color="Total Revenue",
    color_continuous_scale="Greens",
    text="Total Revenue",
)
fig_bar.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
fig_bar.update_layout(xaxis_title="Total Revenue (USD)", yaxis_title="State")
st.plotly_chart(fig_bar)

# Financial health (program vs. admin spending)
st.subheader("Program vs. Administrative Spending")
df_expenses = pd.DataFrame({
    "Expense Type": ["Program Expenses", "Administrative Expenses"],
    "Amount ($)": [df_filtered["totfuncexpns"].sum(), df_filtered["payrolltx"].sum()]
})
fig_exp = px.bar(
    df_expenses,
    x="Expense Type",
    y="Amount ($)",
    title=f"Spending Breakdown ({nonprofit_size})",
    color="Expense Type",
    text="Amount ($)",
)
fig_exp.update_traces(texttemplate="$%{text:,.0f}", textposition="auto")
fig_exp.update_layout(yaxis_title="Amount (USD)", showlegend=False)
st.plotly_chart(fig_exp)

# Insight
program_pct = (df_expenses["Amount ($)"][0] / df_expenses["Amount ($)"].sum() * 100) if df_expenses["Amount ($)"].sum() > 0 else 0
st.markdown(f"**Insight**: {program_pct:.1f}% of spending goes to programs, indicating a focus on mission-driven activities.")

# About the data
with st.expander("📖 About the Data"):
    st.markdown("""
        This dashboard uses IRS Form 990 and EOBMF data to analyze environmental nonprofits (NTEE codes C30-C60).
        - **EOBMF**: Lists registered nonprofits and their classifications.
        - **Form 990**: Provides financial details like revenue, expenses, and assets.
        Data source: IRS (2023 filings).
    """)

# Sidebar: About TUP
st.sidebar.subheader("About TUP")
st.sidebar.markdown("""
    The Undivide Project addresses the climate crisis and digital divide, focusing on poor and BIPOC communities.
    We empower communities to create solutions and uplift underserved voices.
""")