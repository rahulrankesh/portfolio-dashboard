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
spark_data = {}

for symbol in stocks:
    try:
        ticker = yf.Ticker(symbol)

        # --- Live price data ---
        hist = ticker.history(period="2d")
        price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        delta_pct = ((price - prev_close) / prev_close) * 100

        # --- Sparkline (30 days) ---
        spark = ticker.history(period="1mo")['Close']
        spark_data[symbol.replace(".NS", "")] = spark

        # --- Financials ---
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

        score = (roe * sales_growth) * 100

        data.append({
            "Stock": symbol.replace(".NS", ""),
            "Price": price,
            "Δ %": delta_pct,
            "Sales Growth (%)": sales_growth * 100,
            "ROE (%)": roe * 100,
            "PE": pe,
            "PB": pb,
            "Score": score
        })

    except Exception:
        st.error(f"Error loading {symbol}")

# ---- Create DataFrame ----
df = pd.DataFrame(data)
df = df.set_index("Stock")
df = df.sort_values(by="Score", ascending=False)

# ---- Auto Refresh Every 60 Seconds ----
st.markdown(
    '<meta http-equiv="refresh" content="60">',
    unsafe_allow_html=True
)

# ---- Identify Top Ranked Stock ----
top_stock = df.index[0]

def highlight_rows(row):
    styles = []
    for col in df.columns:
        style = "text-align: center !important;"

        # Green if positive delta
        if col == "Δ %" and row[col] > 0:
            style += "color: green; font-weight: bold;"
        if col == "Δ %" and row[col] < 0:
            style += "color: red; font-weight: bold;"

        # ROE highlight
        if col == "ROE (%)" and row[col] > 20:
            style += "color: green; font-weight: bold;"

        # PE warning
        if col == "PE" and row[col] and row[col] > 30:
            style += "color: red; font-weight: bold;"

        # Top ranked highlight
        if row.name == top_stock:
            style += "background-color: #1f2c56; color: white;"

        styles.append(style)

    return styles

styled_df = (
    df.style
    .format({
        "Price": "₹{:,.2f}",
        "Δ %": "{:.2f}%",
        "Sales Growth (%)": "{:.2f}%",
        "ROE (%)": "{:.2f}%",
        "PE": "{:.2f}",
        "PB": "{:.2f}",
        "Score": "{:.2f}"
    })
    .apply(highlight_rows, axis=1)
    .set_properties(**{'text-align': 'center'})
    .set_table_styles([
        {
            'selector': 'th',
            'props': [('text-align', 'center !important')]
        }
    ])
)

st.table(styled_df)

# ---- Sparkline Charts Section ----
st.subheader("📊 30-Day Trend")

cols = st.columns(len(df))

for i, stock in enumerate(df.index):
    with cols[i]:
        st.write(stock)
        st.line_chart(spark_data[stock])
