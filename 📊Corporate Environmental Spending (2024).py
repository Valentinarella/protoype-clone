import streamlit as st

# ✅ Must be the very first Streamlit command
st.set_page_config(
    page_title="Corporate Environmental Spending (2024)",
    layout="wide"
)

import pandas as pd
import numpy as np
from scipy.stats import skew
import os, sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import plotly.express as px
import folium
from streamlit_folium import st_folium
from Home import read_logos

# Load data
@st.cache_data
def load_data():
    return pd.read_csv("https://undivideprojectdata.blob.core.windows.net/seed/financial-statement-and-notes-2024-preprocessed.csv?sp=racw&st=2025-06-08T00:43:19Z&se=3000-06-08T08:43:19Z&spr=https&sv=2024-11-04&sr=b&sig=07rWeAcMwNjzc4yBkos7elqwLuQn2%2Famw8o95Ssoo1g%3D")

df = load_data()

# Page title
st.title("📊Corporate Environmental Spending (2024)")

# About the Data
with st.expander("📖 About the Data"):
    st.markdown("""
    ## 📂 Data Sources & Importance  
    This dashboard tracks corporate spending to environmental causes using financial statements filed with the SEC.

    **1️⃣ Financial Statement and Notes Submission Dataset (2024)**  
    - Contains qualitative company data like names and locations  
    - Useful for identifying patterns in corporate environmental efforts  

    **2️⃣ Financial Statement and Notes Numeric Dataset (2024)**  
    - Includes figures on revenue, environmental spending, and liabilities  
    - Supports deeper analysis of environmental investment trends  

    🔗 [More Info](https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets)
    """)

# Corporate Actors Section
st.header("Who Are the Corporate Actors?")

actor_metrics = ["Total Environmental Expenditures", "Charitable Contributions"]
actor_metric = st.radio("Choose a metric to explore:", ["Environmental Expenditures", "Charitable Contributions"], index=0, horizontal=True)

if actor_metric == "Environmental Expenditures":
    actor_metric = st.radio("Be more specific...", ["Total Environmental Expenditures", "Mandated Environmental Expenditures", "Charitable Environmental Expenditures"], key="actor", index=0, horizontal=True)

actor_df = df[df[actor_metric].notna()].copy()
actor_df["Revenues"] = actor_df["Revenues"].replace(0, np.nan)

# Summary Stats
def compute_summary_statistics():
    companies = actor_df["Name"].nunique()
    sectors = actor_df["Business Sector"].nunique()
    median_revenues = f"${actor_df['Revenues'].median():,.0f}"
    return {
        "Companies": companies,
        "Business Sectors": sectors,
        "Median Revenues": median_revenues,
    }

stats = compute_summary_statistics()
col1, col2, col3 = st.columns(3)
col1.metric("Companies", stats["Companies"])
col2.metric("Business Sectors", stats["Business Sectors"])
col3.metric("Median Revenues", stats["Median Revenues"])

# Tabs
tab1, tab2, tab3 = st.tabs(["📍 Geographic Distribution", "🏗️ Business Sector Breakdown", "🥇 Top Companies"])

# Tab 1: Geographic
with tab1:
    st.subheader(f"Geographic Distribution of {actor_metric}")
    col1, col2 = st.columns([2, 1])

    state_df = actor_df.groupby("State").agg({actor_metric: ["count", "sum"]}).reset_index()
    state_df.columns = ["State", "Count", actor_metric]

    with col1:
        fmap = folium.Map(location=[40, -100], zoom_start=3.5)
        geojson_url = "https://raw.githubusercontent.com/python-visualization/folium-example-data/main/us_states.json"

        folium.Choropleth(
            geo_data=geojson_url,
            data=state_df,
            columns=["State", actor_metric],
            key_on="feature.id",
            legend_name=actor_metric,
            bins=4
        ).add_to(fmap)

        st_folium(fmap, height=500, width="100%")

    with col2:
        st.plotly_chart(px.bar(
            state_df.nlargest(5, actor_metric),
            x=actor_metric, y="State", orientation="h",
            title=f"Top 5 States by {actor_metric}"
        ).update_layout(height=250))

        st.plotly_chart(px.bar(
            state_df.nsmallest(5, actor_metric),
            x=actor_metric, y="State", orientation="h",
            title=f"Bottom 5 States by {actor_metric}"
        ).update_layout(height=250))

    with st.expander("💡 Geographic Insights"):
        st.markdown(f"""
        - **{state_df['State'].nunique()}** states reported this metric  
        - Top 5 states = **{round(state_df.nlargest(5, actor_metric)[actor_metric].sum() / state_df[actor_metric].sum() * 100, 2)}%** of total  
        - Bottom 5 states = **{round(state_df.nsmallest(5, actor_metric)[actor_metric].sum() / state_df[actor_metric].sum() * 100, 2)}%** of total  
        - **{state_df.nlargest(1, actor_metric)['State'].iloc[0]}** reported the highest at **${state_df.nlargest(1, actor_metric)[actor_metric].iloc[0]:,.0f}**
        """)

# Tab 2: Sectors
with tab2:
    st.subheader(f"Business Sector Breakdown of {actor_metric}")

    sector_df = actor_df.groupby("Business Sector").agg({actor_metric: ["count", "sum"]}).reset_index()
    sector_df.columns = ["Business Sector", "Count", actor_metric]

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(
            sector_df.nlargest(5, actor_metric),
            x="Business Sector", y=actor_metric,
            title=f"Top 5 Sectors by {actor_metric}"
        ))

    with col2:
        st.plotly_chart(px.pie(
            sector_df.nlargest(5, actor_metric),
            values=actor_metric, names="Business Sector"
        ))

    with st.expander("💡 Sector Insights"):
        st.markdown(f"""
        - **{sector_df['Business Sector'].nunique()}** sectors total  
        - Top 5 = **{round(sector_df.nlargest(5, actor_metric)[actor_metric].sum() / sector_df[actor_metric].sum() * 100)}%**  
        - Bottom 5 = **{round(sector_df.nsmallest(5, actor_metric)[actor_metric].sum() / sector_df[actor_metric].sum() * 100)}%**  
        - Leader: **{sector_df.nlargest(1, actor_metric)['Business Sector'].iloc[0]}**  
        """)

# Tab 3: Top Companies
with tab3:
    st.subheader(f"Top Companies by {actor_metric}")

    actor_df[f"{actor_metric} % of Revenues"] = actor_df[actor_metric] / actor_df["Revenues"] * 100
    method = st.radio("Ranking Method", [actor_metric, f"{actor_metric} % of Revenues"], horizontal=True)

    top_companies = actor_df.nlargest(5, method)

    st.plotly_chart(px.bar(
        top_companies, x="Name", y=method,
        title=f"Top 5 Companies by {method}"
    ))

    with st.expander("💡 Company Insights"):
        st.markdown(f"""
        - Total companies: **{actor_df['Name'].nunique()}**  
        - Top 5 = **{round(top_companies[method].sum() / actor_df[method].sum() * 100, 2)}%** of total  
        - Highest spender: **{top_companies['Name'].iloc[0]}**
        """)

# Sidebar: TUP Logo and About
TUPLogo = read_logos()
st.sidebar.image(TUPLogo)

with st.sidebar.expander("About TUP"):
    st.markdown("""
    The Undivide Project focuses on the intersection of the climate crisis and the digital divide.  
    We uplift underserved voices and help communities build their own solutions through data, design, and storytelling.
    """)
