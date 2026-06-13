import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from io import StringIO

API_URL = "http://localhost:8001/api/v1/finance"

st.set_page_config(
    page_title="Finance Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Base */
    .stApp { background-color: #FAFAFA; }
    
    /* Hide default header */
    header[data-testid="stHeader"] { background: transparent; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #F0F0F0;
    }
    
    /* Main container */
    .main .block-container { padding-top: 2rem; max-width: 900px; }
    
    /* App header */
    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 0.5rem;
    }
    .app-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1A1A2E;
        margin: 0;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: #8A8A9A;
        margin-bottom: 2rem;
    }
    
    /* Metric cards */
    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border: 1px solid #F5F5F5;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #8A8A9A;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1A1A2E;
    }
    .metric-value.green { color: #00C9A7; }
    
    /* Answer card */
    .answer-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        border-left: 4px solid #00C9A7;
        margin: 1rem 0;
        font-size: 1rem;
        color: #1A1A2E;
        line-height: 1.6;
    }
    
    /* Insight cards */
    .insight-alert {
        background: #FFF5F5;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #FF6B6B;
        margin-bottom: 0.8rem;
    }
    .insight-warning {
        background: #FFFBF0;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #FFB347;
        margin-bottom: 0.8rem;
    }
    .insight-info {
        background: #F0FFFE;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border-left: 4px solid #00C9A7;
        margin-bottom: 0.8rem;
    }
    .insight-title {
        font-weight: 700;
        font-size: 0.9rem;
        color: #1A1A2E;
        margin-bottom: 0.2rem;
    }
    .insight-desc {
        font-size: 0.85rem;
        color: #5A5A7A;
    }
    
    /* Input */
    .stTextInput input {
        border-radius: 12px !important;
        border: 1.5px solid #E8E8F0 !important;
        padding: 0.8rem 1rem !important;
        font-size: 0.95rem !important;
        background: #FFFFFF !important;
    }
    .stTextInput input:focus {
        border-color: #00C9A7 !important;
        box-shadow: 0 0 0 3px rgba(0,201,167,0.1) !important;
    }
    
    /* Button */
    .stButton button {
        background: linear-gradient(135deg, #00C9A7, #00A896) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s !important;
    }
    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 15px rgba(0,201,167,0.3) !important;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #1A1A2E;
        margin: 1.5rem 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F0FFFE;
        color: #00C9A7;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #00C9A7;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💰 Finance Agent")
    st.markdown('<span class="status-badge">● Live</span>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Your Transactions**")
    st.caption("Paste CSV data below")

    sample = """date,description,amount,category
2024-01-01,Swiggy Food Order,850,Food
2024-01-02,Uber Ride,320,Transport
2024-01-03,Netflix,649,Entertainment
2024-01-04,Grocery Store,2100,Food
2024-01-05,Electricity Bill,1200,Utilities
2024-01-06,Zomato Order,450,Food
2024-01-07,Petrol,1500,Transport
2024-01-08,Amazon Purchase,3200,Shopping
2024-01-09,Gym Membership,999,Health
2024-01-10,Restaurant,1800,Food"""

    csv_input = st.text_area(
        "CSV Format",
        value=sample,
        height=280,
        label_visibility="collapsed"
    )

    st.markdown("---")
    use_memory = st.toggle("Remember conversation", value=True)

    if st.button("🗑️ Clear Memory", use_container_width=True):
        try:
            requests.delete("http://localhost:8000/api/v1/finance/memory")
            st.success("Memory cleared!")
        except:
            st.error("Could not connect to backend")

# ── Parse CSV ─────────────────────────────────────────────────────────────────
transactions = []
if csv_input:
    try:
        df_raw = pd.read_csv(StringIO(csv_input))
        for _, row in df_raw.iterrows():
            transactions.append({
                "date": str(row.get("date", "")),
                "description": str(row.get("description", "")),
                "amount": float(row.get("amount", 0)),
                "category": str(row.get("category", "Uncategorized"))
            })
    except Exception as e:
        st.sidebar.error(f"CSV error: {e}")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div>
        <div class="app-title">Personal Finance Agent</div>
    </div>
</div>
<div class="app-subtitle">Ask anything about your spending — powered by a real AI agent with tool calling</div>
""", unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
question = st.text_input(
    "Question",
    placeholder="How much did I spend on Netflix? Where am I overspending?",
    label_visibility="collapsed"
)

ask = st.button("Ask Agent →", use_container_width=True)

# ── Response ──────────────────────────────────────────────────────────────────
if ask and question:
    if not transactions:
        st.warning("Please add transactions in the sidebar first.")
    else:
        with st.spinner("Agent is thinking..."):
            try:
                response = requests.post(API_URL, json={
                    "question": question,
                    "transactions": transactions,
                    "use_memory": use_memory
                }, timeout=30)

                if response.status_code != 200:
                    st.error(f"Error {response.status_code}: {response.text}")
                else:
                    data = response.json()

                    # Answer
                    st.markdown('<div class="section-header">💬 Answer</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="answer-card">{data.get("answer", "No answer returned")}</div>', unsafe_allow_html=True)

                    # Metrics
                    st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns(3)
                    total = data.get("total_spent") or 0
                    with col1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Total Spent</div>
                            <div class="metric-value">₹{total:,.0f}</div>
                        </div>""", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Top Category</div>
                            <div class="metric-value green">{data.get("top_category") or "N/A"}</div>
                        </div>""", unsafe_allow_html=True)
                    with col3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-label">Transactions</div>
                            <div class="metric-value">{len(transactions)}</div>
                        </div>""", unsafe_allow_html=True)

                    # Insights
                    insights = data.get("insights", [])
                    if insights:
                        st.markdown('<div class="section-header">💡 Insights</div>', unsafe_allow_html=True)
                        for insight in insights:
                            severity = insight.get("severity", "info")
                            title = insight.get("title", "")
                            desc = insight.get("description", "")
                            css_class = f"insight-{severity}"
                            icon = "🚨" if severity == "alert" else "⚠️" if severity == "warning" else "💡"
                            st.markdown(f"""
                            <div class="{css_class}">
                                <div class="insight-title">{icon} {title}</div>
                                <div class="insight-desc">{desc}</div>
                            </div>""", unsafe_allow_html=True)

                    # Chart
                    if transactions:
                        st.markdown('<div class="section-header">📈 Spending Breakdown</div>', unsafe_allow_html=True)
                        df_chart = pd.DataFrame(transactions)
                        cat_spend = df_chart.groupby("category")["amount"].sum().reset_index()

                        col_chart1, col_chart2 = st.columns(2)

                        with col_chart1:
                            fig_pie = px.pie(
                                cat_spend,
                                names="category",
                                values="amount",
                                hole=0.5,
                                color_discrete_sequence=["#00C9A7", "#FFB347", "#FF6B6B", "#6C63FF", "#00A8E8", "#FF9A8B"]
                            )
                            fig_pie.update_layout(
                                showlegend=True,
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(t=20, b=20, l=20, r=20),
                                legend=dict(font=dict(size=11))
                            )
                            fig_pie.update_traces(textposition="inside", textinfo="percent")
                            st.plotly_chart(fig_pie, use_container_width=True)

                        with col_chart2:
                            cat_spend_sorted = cat_spend.sort_values("amount", ascending=True)
                            fig_bar = go.Figure(go.Bar(
                                x=cat_spend_sorted["amount"],
                                y=cat_spend_sorted["category"],
                                orientation="h",
                                marker=dict(
                                    color=cat_spend_sorted["amount"],
                                    colorscale=[[0, "#00C9A7"], [1, "#6C63FF"]]
                                )
                            ))
                            fig_bar.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(t=20, b=20, l=20, r=20),
                                xaxis=dict(showgrid=False, title="Amount (₹)"),
                                yaxis=dict(showgrid=False),
                                height=300
                            )
                            st.plotly_chart(fig_bar, use_container_width=True)

            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

elif ask and not question:
    st.warning("Please enter a question first.")