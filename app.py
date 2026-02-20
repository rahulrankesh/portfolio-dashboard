import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

st.set_page_config(page_title="Personal Capital Allocator", layout="wide")
st.title("💼 Production-Ready Personal Capital Allocator")

# -------------------------------------------------
# MARKET HOURS CONTROL (IST)
# -------------------------------------------------

ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)

market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

is_market_open = market_open <= now <= market_close

if is_market_open:
    st.markdown(
        "<p style='font-size:13px; color:green;'>● LIVE</p>",
        unsafe_allow_html=True
    )
    st.markdown(
        '<meta http-equiv="refresh" content="60">',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<p style='font-size:13px; color:red;'>● Market Closed</p>",
        unsafe_allow_html=True
    )

last_refresh = now.strftime("%d %b %Y | %H:%M:%S IST")

st.markdown(
    f"<p style='font-size:11px; color:gray;'>Last updated: {last_refresh}</p>",
    unsafe_allow_html=True
)

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
# COMPACT USER INPUT ROW
# -------------------------------------------------

col1, col2 = st.columns([3,1])

with col1:
    stock_input = st.text_input(
        "Stocks (comma separated, NSE format without .NS)",
        "HDFCBANK,ICICIBANK,RELIANCE,INFY,TCS,LT,SBIN,ITC,HCLTECH,BHARTIARTL"
    )

with col2:
    capital = st.number_input(
        "Capital (₹)",
        min_value=1000.0,
        value=1000000.0,
        step=10000.0
    )

symbols = [s.strip().upper() + ".NS" for s in stock_input.split(",")]

if len(symbols) < 10:
    st.warning("Minimum 10 stocks required.")
    st.stop()

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
    st.warning("No valid stock data.")
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
# LIVE DAILY RETURN
# -------------------------------------------------

portfolio["Weighted Return"] = (
    portfolio["Δ %"] * portfolio["Weight %"] / 100
)

daily_return = portfolio["Weighted Return"].sum()

st.metric("📊 Today's Portfolio Return (%)", round(daily_return, 2))

# -------------------------------------------------
# PERFORMANCE SUMMARY (1Y)
# -------------------------------------------------

st.subheader("📊 Strategy Performance Summary (1Y)")

price_data = {}

for symbol in symbols[:15]:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")["Close"]
        price_data[symbol] = hist
    except:
        continue

price_df = pd.DataFrame(price_data).dropna()

if not price_df.empty:

    monthly_returns = price_df.resample("M").last().pct_change()
    strategy_returns = monthly_returns.mean(axis=1)

    cumulative = (1 + strategy_returns).cumprod()

    total_return = cumulative.iloc[-1] - 1
    annual_vol = strategy_returns.std() * np.sqrt(12)
    sharpe = total_return / annual_vol if annual_vol != 0 else 0

    running_max = cumulative.cummax()
    drawdown = (cumulative / running_max) - 1
    max_drawdown = drawdown.min()

    nifty = yf.Ticker("^NSEI").history(period="1y")["Close"]
    nifty_monthly = nifty.resample("M").last().pct_change()
    nifty_cum = (1 + nifty_monthly).cumprod()
    nifty_return = nifty_cum.iloc[-1] - 1

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Strategy Return", f"{total_return*100:.2f}%")
    col2.metric("NIFTY Return", f"{nifty_return*100:.2f}%")
    col3.metric("Volatility", f"{annual_vol*100:.2f}%")
    col4.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col5.metric("Max Drawdown", f"{max_drawdown*100:.2f}%")
