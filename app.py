import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Personal Capital Allocator", layout="wide")

st.title("💼 Personal Capital Allocator")

# -------------------------------------------------
# CENTERED TABLE RENDER FUNCTION
# -------------------------------------------------

def centered_table(dataframe):
    styled = (
        dataframe.style
        .format("{:.2f}")
        .set_properties(**{'text-align': 'center'})
        .set_table_styles([
            {'selector': 'th',
             'props': [('text-align', 'center !important'),
                       ('font-weight', 'bold')]},
            {'selector': 'td',
             'props': [('text-align', 'center !important')]}
        ])
    )

    html = styled.to_html()

    st.markdown("""
        <style>
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: center !important;
        }
        th, td {
            text-align: center !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(html, unsafe_allow_html=True)

# -------------------------------------------------
# USER INPUT
# -------------------------------------------------

default_stocks = "HDFCBANK,ICICIBANK,RELIANCE,INFY,TCS"

stock_input = st.text_input(
    "Enter stock symbols (comma separated, NSE format without .NS)",
    default_stocks
)

capital = st.number_input(
    "Enter Total Capital (₹)",
    min_value=1000.0,
    value=1000000.0,
    step=10000.0
)

symbols = [s.strip().upper() + ".NS" for s in stock_input.split(",")]

# -------------------------------------------------
# MARKET REGIME DETECTION
# -------------------------------------------------

nifty = yf.Ticker("^NSEI")
nifty_hist = nifty.history(period="1y")

nifty_hist["MA50"] = nifty_hist["Close"].rolling(50).mean()
nifty_hist["MA200"] = nifty_hist["Close"].rolling(200).mean()

regime = "Bull" if nifty_hist["MA50"].iloc[-1] > nifty_hist["MA200"].iloc[-1] else "Defensive"

st.subheader(f"📈 Market Regime: {regime}")

# -------------------------------------------------
# DATA COLLECTION & SCORING
# -------------------------------------------------

data = []

for symbol in symbols:
    try:
        ticker = yf.Ticker(symbol)

        hist_2d = ticker.history(period="2d")
        price = hist_2d["Close"].iloc[-1]
        prev_close = hist_2d["Close"].iloc[-2]
        delta_pct = ((price - prev_close) / prev_close) * 100

        hist_1m = ticker.history(period="1mo")
        returns = hist_1m["Close"].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100

        financials = ticker.financials.T
        balance = ticker.balance_sheet.T

        revenue = financials["Total Revenue"].iloc[0]
        prev_revenue = financials["Total Revenue"].iloc[1]
        growth = (revenue - prev_revenue) / prev_revenue * 100

        net_income = financials["Net Income"].iloc[0]
        equity = balance["Stockholders Equity"].iloc[0]
        roe = (net_income / equity) * 100

        pe = ticker.info.get("trailingPE", 0)

        if regime == "Bull":
            score = (
                0.35 * growth +
                0.30 * delta_pct +
                0.15 * roe -
                0.10 * pe -
                0.10 * volatility
            )
        else:
            score = (
                0.30 * roe +
                0.25 * growth -
                0.20 * volatility -
                0.15 * pe +
                0.10 * delta_pct
            )

        data.append({
            "Stock": symbol.replace(".NS",""),
            "Price": price,
            "Δ %": delta_pct,
            "Growth %": growth,
            "ROE %": roe,
            "Volatility %": volatility,
            "PE": pe,
            "Score": score
        })

    except:
        continue

if len(data) == 0:
    st.warning("No valid stock data found.")
    st.stop()

df = pd.DataFrame(data).set_index("Stock")
df = df.sort_values("Score", ascending=False).round(2)

st.subheader("🔢 Ranked Universe")
centered_table(df)

# -------------------------------------------------
# RISK-ADJUSTED PORTFOLIO ALLOCATION
# -------------------------------------------------

st.subheader("📌 Capital Allocation (Monthly Rebalance)")

top_n = min(5, len(df))
portfolio = df.head(top_n).copy()

portfolio["InvVol"] = 1 / portfolio["Volatility %"]
portfolio["Weight %"] = (
    portfolio["InvVol"] / portfolio["InvVol"].sum() * 100
).round(2)

portfolio["Allocated ₹"] = (portfolio["Weight %"] / 100 * capital).round(2)
portfolio["Quantity"] = (portfolio["Allocated ₹"] / portfolio["Price"]).astype(int)
portfolio["Actual Invested ₹"] = (portfolio["Quantity"] * portfolio["Price"]).round(2)

portfolio = portfolio.drop(columns=["InvVol"])

centered_table(portfolio)

# -------------------------------------------------
# LIVE DAILY PORTFOLIO RETURN
# -------------------------------------------------

portfolio["Weighted Return"] = (
    portfolio["Δ %"] * portfolio["Weight %"] / 100
)

daily_return = portfolio["Weighted Return"].sum()

st.metric("📊 Today's Portfolio Return (%)", round(daily_return, 2))

# -------------------------------------------------
# 1-YEAR BACKTEST (Equal Weight Simplified)
# -------------------------------------------------

st.subheader("📈 1Y Equal Weight Backtest (Simplified)")

price_data = {}

for symbol in symbols[:10]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")["Close"]
        price_data[symbol] = hist
    except:
        continue

price_df = pd.DataFrame(price_data).dropna()

if not price_df.empty:
    monthly_returns = price_df.resample("M").last().pct_change()
    portfolio_returns = monthly_returns.mean(axis=1)
    cumulative = (1 + portfolio_returns).cumprod()
    st.line_chart(cumulative)
