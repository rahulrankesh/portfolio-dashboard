import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Adaptive Quant Engine", layout="wide")

st.title("📊 Adaptive Growth + Regime Quant Engine")

# ---------------------------------------
# 1️⃣ Market Regime Detection (NIFTY)
# ---------------------------------------
nifty = yf.Ticker("^NSEI")
nifty_hist = nifty.history(period="1y")

nifty_hist["MA50"] = nifty_hist["Close"].rolling(50).mean()
nifty_hist["MA200"] = nifty_hist["Close"].rolling(200).mean()

if nifty_hist["MA50"].iloc[-1] > nifty_hist["MA200"].iloc[-1]:
    regime = "Bull"
else:
    regime = "Defensive"

st.subheader(f"Market Regime: {regime}")

# ---------------------------------------
# 2️⃣ Universe (Top 20 NIFTY for stability)
# ---------------------------------------
stocks = [
    "HDFCBANK.NS","ICICIBANK.NS","RELIANCE.NS","INFY.NS","TCS.NS",
    "LT.NS","SBIN.NS","ITC.NS","HINDUNILVR.NS","BHARTIARTL.NS",
    "KOTAKBANK.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
    "BAJFINANCE.NS","HCLTECH.NS","WIPRO.NS","ONGC.NS","NTPC.NS","SUNPHARMA.NS"
]

data = []
spark_data = {}

for symbol in stocks:
    try:
        ticker = yf.Ticker(symbol)

        hist_2d = ticker.history(period="2d")
        price = hist_2d["Close"].iloc[-1]
        prev_close = hist_2d["Close"].iloc[-2]
        delta_pct = ((price - prev_close) / prev_close) * 100

        hist_1m = ticker.history(period="1mo")
        spark = hist_1m["Close"]
        spark_data[symbol] = spark

        returns = spark.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100

        financials = ticker.financials.T
        balance = ticker.balance_sheet.T

        revenue = financials["Total Revenue"].iloc[0]
        prev_revenue = financials["Total Revenue"].iloc[1]
        growth = (revenue - prev_revenue) / prev_revenue * 100

        net_income = financials["Net Income"].iloc[0]
        equity = balance["Stockholders Equity"].iloc[0]
        roe = (net_income / equity) * 100

        info = ticker.info
        pe = info.get("trailingPE", 0)

        # Adaptive scoring
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

df = pd.DataFrame(data).set_index("Stock")
df = df.sort_values("Score", ascending=False).round(2)

st.subheader("🔢 Daily Ranking")
st.dataframe(df, use_container_width=True)

# ---------------------------------------
# 3️⃣ Monthly Rebalance (Top 5)
# ---------------------------------------
st.subheader("📌 Model Portfolio (Monthly Rebalance)")
top_n = 5
portfolio = df.head(top_n).copy()

portfolio["InvVol"] = 1 / portfolio["Volatility %"]
portfolio["Weight %"] = (
    portfolio["InvVol"] / portfolio["InvVol"].sum() * 100
).round(2)

portfolio = portfolio.drop(columns=["InvVol"])

st.dataframe(portfolio, use_container_width=True)

# ---------------------------------------
# 4️⃣ Live Model Return
# ---------------------------------------
portfolio["Weighted Return"] = (
    portfolio["Δ %"] * portfolio["Weight %"] / 100
)

daily_return = portfolio["Weighted Return"].sum()

st.metric("Today's Model Return (%)", round(daily_return, 2))

# ---------------------------------------
# 5️⃣ Backtest (1 Year Monthly Equal Weight)
# ---------------------------------------
st.subheader("📈 Backtest (1Y Monthly Rebalance - Simplified)")

price_data = {}

for symbol in stocks[:15]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")["Close"]
        price_data[symbol] = hist
    except:
        continue

price_df = pd.DataFrame(price_data).dropna()

monthly_returns = price_df.resample("M").last().pct_change()
portfolio_returns = monthly_returns.mean(axis=1)

cumulative = (1 + portfolio_returns).cumprod()

st.line_chart(cumulative)
