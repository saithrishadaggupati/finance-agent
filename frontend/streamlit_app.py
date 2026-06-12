import streamlit as st
import requests
import plotly.express as px
import pandas as pd

API_URL = "http://localhost:8000/api/v1/finance"

st.set_page_config(
    page_title="Finance Agent",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Personal Finance Agent")
st.caption("Upload your transactions and ask anything about your spending")

# ── Sidebar — Transaction Input ───────────────────────────────────────────────
with st.sidebar:
    st.header("Your Transactions")
    st.caption("Paste your transactions below")

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
        "CSV Format (date, description, amount, category)",
        value=sample,
        height=300
    )

    use_memory = st.toggle("Remember conversation", value=True)

    if st.button("Clear Memory", use_container_width=True):
        requests.delete("http://localhost:8000/api/v1/finance/memory")
        st.success("Memory cleared!")

# ── Parse CSV ─────────────────────────────────────────────────────────────────
transactions = []
if csv_input:
    try:
        from io import StringIO
        df = pd.read_csv(StringIO(csv_input))
        for _, row in df.iterrows():
            transactions.append({
                "date": str(row.get("date", "")),
                "description": str(row.get("description", "")),
                "amount": float(row.get("amount", 0)),
                "category": str(row.get("category", "Uncategorized"))
            })
    except Exception as e:
        st.sidebar.error(f"CSV parse error: {e}")

# ── Main — Question Input ─────────────────────────────────────────────────────
question = st.text_input(
    "Ask about your finances",
    placeholder="Where am I spending the most? Am I overspending on food?"
)

if st.button("Ask", use_container_width=True) and question:
    with st.spinner("Analyzing your finances..."):
        try:
            response = requests.post(API_URL, json={
                "question": question,
                "transactions": transactions,
                "use_memory": use_memory
            })
            data = response.json()

            # ── Answer ────────────────────────────────────────────────────────
            st.markdown("### Answer")
            st.write(data["answer"])

            # ── Summary Metrics ───────────────────────────────────────────────
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Spent", f"₹{data.get('total_spent', 0):,.2f}")
            with col2:
                st.metric("Top Category", data.get("top_category", "N/A"))
            with col3:
                st.metric("Transactions", len(transactions))

            # ── Insights ──────────────────────────────────────────────────────
            if data.get("insights"):
                st.markdown("### Insights")
                for insight in data["insights"]:
                    severity = insight["severity"]
                    if severity == "alert":
                        st.error(f"🚨 **{insight['title']}** — {insight['description']}")
                    elif severity == "warning":
                        st.warning(f"⚠️ **{insight['title']}** — {insight['description']}")
                    else:
                        st.info(f"💡 **{insight['title']}** — {insight['description']}")

            # ── Spending Chart ────────────────────────────────────────────────
            if transactions:
                st.markdown("### Spending by Category")
                df = pd.DataFrame(transactions)
                category_spend = df.groupby("category")["amount"].sum().reset_index()
                fig = px.pie(
                    category_spend,
                    names="category",
                    values="amount",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Something went wrong: {e}")