# GenAI Wealth Advisor App with Azure OpenAI

import streamlit as st
import plotly.express as px
from openai import AzureOpenAI
import yfinance as yf
import pandas as pd
from fpdf import FPDF
from datetime import datetime, timedelta

# ========== Azure OpenAI API Setup ==========
client = AzureOpenAI(
    api_key=st.secrets["azure_openai_api_key"],
    azure_endpoint=st.secrets["azure_openai_endpoint"],
    api_version="2023-07-01-preview",
)
model_name = st.secrets["azure_openai_deployment"]

# ========== Demo Login Simulation ==========
def login_section():
    st.sidebar.subheader("🔐 Simulated Login")
    email = st.sidebar.text_input("Enter your email")
    if st.sidebar.button("Login"):
        st.session_state['user'] = {"email": email}
        st.success(f"✅ Logged in as {email}")

# ========== Portfolio Allocation Logic ==========
def get_portfolio_allocation(risk):
    if risk == "Low":
        return {"Equity": 30, "Debt": 60, "Gold": 10}
    elif risk == "Medium":
        return {"Equity": 50, "Debt": 40, "Gold": 10}
    else:
        return {"Equity": 70, "Debt": 20, "Gold": 10}

# ========== GPT Explanation ==========
def explain_portfolio(allocation, age, risk, goal):
    prompt = f"""
    Act like a professional financial advisor. Explain this portfolio allocation for a {age}-year-old user with {risk} risk tolerance and goal: {goal}.
    The allocation is: Equity: {allocation['Equity']}%, Debt: {allocation['Debt']}%, Gold: {allocation['Gold']}%.
    """
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful and expert financial advisor."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ========== SIP Calculator ==========
def calculate_sip(goal_amount, years, annual_return):
    monthly_rate = (annual_return / 100) / 12
    months = years * 12
    sip = goal_amount * monthly_rate / ((1 + monthly_rate) ** months - 1)
    return round(sip, 2)

# ========== Real-Time Return Estimates ==========
def fetch_cagr(ticker, years=5):
    end = datetime.now()
    start = end - timedelta(days=years * 365)
    data = yf.download(ticker, start=start, end=end)
    if data.empty:
        return "❌ No data"
    if "Adj Close" not in data.columns:
        return "❌ 'Adj Close' not found"
    start_price = data["Adj Close"].iloc[0]
    end_price = data["Adj Close"].iloc[-1]
    cagr = ((end_price / start_price) ** (1 / years)) - 1
    return round(cagr * 100, 2)

# ========== PDF Export ==========
def generate_pdf(name, age, income, risk, goal, allocation, explanation, sip_info=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Wealth Advisor Report", ln=True, align="C")

    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Name: {name} | Age: {age} | Income: ₹{income:,}", ln=True)
    pdf.cell(200, 10, f"Risk Tolerance: {risk} | Goal: {goal}", ln=True)

    pdf.ln(10)
    pdf.cell(200, 10, txt="Portfolio Allocation:", ln=True)
    for asset, percent in allocation.items():
        pdf.cell(200, 10, f"{asset}: {percent}%", ln=True)

    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Advisor's Explanation:\n{explanation}")

    if sip_info:
        pdf.ln(5)
        pdf.multi_cell(0, 10, f"\nGoal: ₹{sip_info['amount']} in {sip_info['years']} years.\nMonthly SIP Needed: ₹{sip_info['sip']}")

    pdf.output("/mnt/data/wealth_report.pdf")

# ========== Main Streamlit App ==========
st.set_page_config(page_title="GenAI Wealth Advisor", page_icon="💼")
st.title("💼 GenAI-Based Wealth Advisor Chatbot")

login_section()
if 'user' not in st.session_state:
    st.stop()

# User Inputs
st.subheader("👤 Profile Details")
age = st.slider("Age", 18, 70, 30)
income = st.number_input("Monthly Income (₹)", value=50000)
risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"])
goal = st.text_input("Primary Goal (e.g., retirement, house)")

if st.button("🔍 Generate Portfolio"):
    allocation = get_portfolio_allocation(risk_tolerance)

    fig = px.pie(
        names=list(allocation.keys()),
        values=list(allocation.values()),
        title="Your Investment Allocation",
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig)

    explanation = explain_portfolio(allocation, age, risk_tolerance, goal)
    st.markdown("### 📘 Advisor's Explanation")
    st.write(explanation)

    st.subheader("🎯 SIP Calculator")
    goal_amount = st.number_input("Goal Amount (₹)", value=1000000)
    goal_years = st.number_input("Years", value=10)
    expected_return = st.slider("Expected Return (%)", 6.0, 15.0, 12.0)

    sip = calculate_sip(goal_amount, goal_years, expected_return)
    st.success(f"Invest ₹{sip:,}/month to achieve ₹{goal_amount:,} in {goal_years} years")

    st.subheader("📉 Real-Time Return Estimates")
    returns = {
        "Equity": fetch_cagr("AAPL"),
        "Debt": fetch_cagr("BND"),
        "Gold": fetch_cagr("GLD")
    }
    st.dataframe(pd.DataFrame({"Asset": returns.keys(), "CAGR (%)": returns.values()}))

    if st.button("📄 Generate PDF Report"):
        generate_pdf("User", age, income, risk_tolerance, goal, allocation, explanation, {"amount": goal_amount, "years": goal_years, "sip": sip})
        st.download_button("📥 Download PDF", open("/mnt/data/wealth_report.pdf", "rb"), "Wealth_Report.pdf")

    # LLM Q&A
    st.subheader("💬 Ask About Your Portfolio")
    user_question = st.text_input("Type your question")
    if st.button("Ask GPT"):
        prompt = f"The user has a portfolio: {allocation}, age {age}, goal: {goal}. Question: {user_question}"
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a financial advisor."},
                {"role": "user", "content": prompt}
            ]
        )
        st.write(response.choices[0].message.content)
