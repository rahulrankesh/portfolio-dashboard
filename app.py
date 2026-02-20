import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Portfolio Dashboard", layout="wide")

st.title("📈 Portfolio Dashboard")

stocks = [
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "RELIANCE.NS",
    "INFY.NS"
]

data = []

for symbol in stocks:
    try:
        ticker = yf.Ticker(symbol)

        price = ticker.history(period="1d")['Close'].iloc[-1]

        financials = ticker.financials.T
        balance_sheet = ticker.balance_sheet.T

        revenue = financials['Total Revenue'].iloc[0]
        prev_revenue = financials['Total Revenue'].iloc[1]
        sales_growth = (revenue - prev_revenue) / prev_revenue

        net_income = financials['Net Income'].iloc[0]
        equity = balance_sheet['Stockholders Equity'].iloc[0]
        roe = net_income / equity

        info = ticker.info
        pe = info.get('trailingPE')
        pb = info.get('priceToBook')

        # Calculate score safely
        score = (roe * sales_growth) / pe if pe else None
        
        data.append({
            "Stock": symbol.replace(".NS", ""),
            "Price": round(price, 2),
            "Sales Growth (%)": round(sales_growth * 100, 2),
            "ROE (%)": round(roe * 100, 2),
            "PE": pe,
            "PB": pb,
            "Score": round(score, 4) if score else None
        })

    except Exception as e:
        st.error(f"Error loading {symbol}")

df = pd.DataFrame(data)

df = df.set_index("Stock")   # optional but cleaner

df = df.sort_values(by="Score", ascending=False)

st.dataframe(df, use_container_width=True)


