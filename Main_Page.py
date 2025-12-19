import streamlit as st

st.set_page_config(
    page_title="Leuven 2030 Solar Dashboard",
    page_icon="☀️",
    layout="wide"
)

st.title("☀️ Leuven 2030: Solar Rooftop Dashboard")

st.markdown("""
### Welcome to the Decision Support System

This dashboard integrates data from multiple analysis pipelines to help prioritize solar installations in Leuven.

#### 👈 Please select a view from the sidebar:

* **01 Top 200 Priorities (Hang's Analysis)**: 
    * Detailed view of the largest potential roofs (>500m²).
    * Includes **AI-based Roof Type Classification**.
    * High-precision WFS geometry.

* **02 Full City Scan (Ha Van & Alex's Analysis)**:
    * Comprehensive view of **~56,000 buildings**.
    * Broad potentiality calculation.
    * Based on latest rooftop potentiality algorithms.

---
*Project Built by Emergent Leuven for Leuven 2030. Front-end developed by Yuxuan (Antonio) Kang. Based on Hang, Ha and Alex's Data Analysis.*
""")