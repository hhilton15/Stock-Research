import streamlit as st
import yfinance as yf
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Stock Analysis Dashboard", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for metric card highlights and cleaner spacing
st.markdown("""
<style>
    .stMetric {
        background-color: rgba(150, 150, 150, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(150, 150, 150, 0.1);
    }
    div[data-testid="stSidebar"] {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def smart_format(val):
    if pd.isna(val) or val is None:
        return "N/A"
    abs_val = abs(val)
    if abs_val >= 1e9:
        return f"${val / 1e9:,.2f}B"
    elif abs_val >= 1e6:
        return f"${val / 1e6:,.1f}M"
    else:
        return f"${val:,.0f}"

def find_row_flexible(df, keywords):
    for row in df.index:
        r_low = str(row).lower()
        if any(kw in r_low for kw in keywords):
            return row
    return None

# Sidebar Ticker Input
st.sidebar.title("🔍 Stock Lookup")
ticker_input = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").upper()
st.sidebar.markdown("---")
st.sidebar.caption("Data provided via Yahoo Finance (`yfinance`)")

if ticker_input:
    ticker = yf.Ticker(ticker_input)
    info = ticker.info

    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
    name_str = info.get('longName', ticker_input)

    # Top Header Banner
    col_head1, col_head2 = st.columns([3, 1])
    with col_head1:
        st.title(f"{name_str} ({ticker_input})")
        st.caption("Fundamental Analysis Dashboard")
    with col_head2:
        price_str = f"${current_price:,.2f}" if current_price else "N/A"
        st.metric(label="Current Price", value=price_str)

    st.markdown("---")

    # Key Financial Metrics
    trailing_pe = info.get('trailingPE')
    forward_pe_1y = info.get('forwardPE')
    trailing_eps = info.get('trailingEps')
    forward_eps_1y = info.get('forwardEps')
    peg_ratio = info.get('pegRatio')
    debt_to_equity = info.get('debtToEquity')
    dividend_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
    payout_ratio = info.get('payoutRatio')
    fifty_two_low = info.get('fiftyTwoWeekLow')
    fifty_two_high = info.get('fiftyTwoWeekHigh')
    analyst_target = info.get('targetMeanPrice')
    rev_growth_current = info.get('revenueGrowth')
    eps_growth_current = info.get('earningsGrowth')
    profit_margins = info.get('profitMargins')
    gross_margins = info.get('grossMargins')
    operating_margins = info.get('operatingMargins')

    # Estimations
    eps_2y_avg = None
    try:
        earn_est = ticker.earnings_estimate
        if earn_est is not None and not earn_est.empty and '+2y' in earn_est.index:
            eps_2y_avg = earn_est.loc['+2y', 'avg']
    except Exception:
        pass

    forward_pe_2y = (current_price / eps_2y_avg) if (current_price and eps_2y_avg and eps_2y_avg > 0) else None

    # Tabbed Dashboard Layout
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Key Valuation", 
        "💰 Profitability & Debt", 
        "🎯 Bull & Bear Insights", 
        "📈 Quarterly Trends"
    ])

    with tab1:
        st.subheader("Valuation Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Trailing P/E", f"{trailing_pe:.2f}x" if trailing_pe else "N/A")
        m2.metric("1-Yr Forward P/E", f"{forward_pe_1y:.2f}x" if forward_pe_1y else "N/A")
        m3.metric("2-Yr Forward P/E", f"{forward_pe_2y:.2f}x" if forward_pe_2y else "N/A")
        m4.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio else "N/A")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("52-Week Range", f"${fifty_two_low:,.2f} - ${fifty_two_high:,.2f}" if fifty_two_low and fifty_two_high else "N/A")
        c2.metric("Analyst Target Price", f"${analyst_target:,.2f}" if analyst_target else "N/A")
        c3.metric("Dividend Yield", f"{dividend_yield * 100:.2f}%" if dividend_yield else "N/A")

    with tab2:
        st.subheader("Profitability & Leverage")
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Gross Margin", f"{gross_margins * 100:.2f}%" if gross_margins else "N/A")
        m6.metric("Operating Margin", f"{operating_margins * 100:.2f}%" if operating_margins else "N/A")
        m7.metric("Net Profit Margin", f"{profit_margins * 100:.2f}%" if profit_margins else "N/A")
        m8.metric("Debt-to-Equity", f"{debt_to_equity:.2f}%" if debt_to_equity else "N/A")

    with tab3:
        # Automated Bull & Bear Insights
        bulls, bears = [], []
        if profit_margins and profit_margins > 0.15:
            bulls.append(f"High bottom-line profitability with a net margin of {profit_margins*100:.1f}%.")
        elif profit_margins and profit_margins > 0:
            bulls.append(f"Positive net profit margin of {profit_margins*100:.1f}%.")
        else:
            bears.append("Thin or negative net profit margins indicate earnings pressure.")

        if rev_growth_current and rev_growth_current > 0.08:
            bulls.append(f"Healthy YoY revenue growth of {rev_growth_current*100:.1f}%.")
        elif rev_growth_current and rev_growth_current < 0:
            bears.append(f"Negative YoY revenue contraction of {rev_growth_current*100:.1f}%.")

        if debt_to_equity and debt_to_equity > 150:
            bears.append(f"Elevated debt ratio of {debt_to_equity:.1f}%.")
        else:
            bulls.append("Manageable debt load relative to equity.")

        while len(bulls) < 3: bulls.append("Consistent core operational performance.")
        while len(bears) < 3: bears.append("Macroeconomic headwinds could impact guidance.")

        col_bull, col_bear = st.columns(2)
        with col_bull:
            st.subheader("🟢 Bull Case Tailwinds")
            for b in bulls[:3]:
                st.success(f"• {b}")
                
        with col_bear:
            st.subheader("🔴 Bear Case Headwinds")
            for b in bears[:3]:
                st.error(f"• {b}")

    with tab4:
        st.subheader("Recent Quarterly Net Margin Trend")
        quarterly_net_margins = []
        try:
            q_financials = ticker.quarterly_financials
            if q_financials is not None and not q_financials.empty:
                net_income_row = find_row_flexible(q_financials, ['net income'])
                revenue_row = find_row_flexible(q_financials, ['total revenue', 'revenue'])
                if net_income_row is not None and revenue_row is not None:
                    for date in q_financials.columns[:8]:
                        ni = q_financials.loc[net_income_row, date]
                        rev = q_financials.loc[revenue_row, date]
                        if pd.notna(ni) and pd.notna(rev) and rev != 0:
                            quarterly_net_margins.append({
                                'Quarter Ending': pd.to_datetime(date).strftime('%b %Y'),
                                'Net Margin (%)': round((ni / rev) * 100, 2)
                            })
        except Exception:
            st.warning("Could not retrieve quarterly margins.")

        if quarterly_net_margins:
            df_margins = pd.DataFrame(quarterly_net_margins)
            
            # Displays the line chart and table cleanly side by side
            col_chart, col_table = st.columns([2, 1])
            with col_chart:
                chart_data = df_margins.set_index('Quarter Ending')
                st.line_chart(chart_data)
            with col_table:
                # Replaced deprecated use_container_width with width='stretch'
                st.dataframe(df_margins, width='stretch')

