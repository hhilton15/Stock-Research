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
    peg_ratio = info.get('pegRatio')
    debt_to_equity = info.get('debtToEquity')
    
    # Robust Dividend Yield Calculation
    div_rate = info.get('dividendRate')
    raw_div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield')
    
    if div_rate and current_price and current_price > 0:
        dividend_yield = (div_rate / current_price) * 100
    elif raw_div_yield is not None:
        dividend_yield = raw_div_yield * 100 if raw_div_yield < 1 else raw_div_yield
    else:
        dividend_yield = None

    # Payout Ratio Calculation
    raw_payout = info.get('payoutRatio')
    if raw_payout is not None:
        payout_ratio = raw_payout * 100 if raw_payout < 1 else raw_payout
    else:
        payout_ratio = None

    fifty_two_low = info.get('fiftyTwoWeekLow')
    fifty_two_high = info.get('fiftyTwoWeekHigh')
    analyst_target = info.get('targetMeanPrice')
    
    # Growth metrics extraction
    rev_growth_current = info.get('revenueGrowth')
    eps_growth_current = info.get('earningsGrowth')
    
    profit_margins = info.get('profitMargins')
    gross_margins = info.get('grossMargins')
    operating_margins = info.get('operatingMargins')

    # Estimations (Revenue & EPS 1Y / 2Y)
    rev_growth_1y = None
    rev_growth_2y = None
    eps_growth_1y = None
    eps_growth_2y = None
    eps_2y_avg = None

    try:
        rev_est = ticker.revenue_estimate
        if rev_est is not None and not rev_est.empty:
            if '+1y' in rev_est.columns and 'growth' in rev_est.index:
                rev_growth_1y = rev_est.loc['growth', '+1y']
            if '+2y' in rev_est.columns and 'growth' in rev_est.index:
                rev_growth_2y = rev_est.loc['growth', '+2y']
    except Exception:
        pass

    try:
        earn_est = ticker.earnings_estimate
        if earn_est is not None and not earn_est.empty:
            if '+1y' in earn_est.columns and 'growth' in earn_est.index:
                eps_growth_1y = earn_est.loc['growth', '+1y']
            if '+2y' in earn_est.columns and 'growth' in earn_est.index:
                eps_growth_2y = earn_est.loc['growth', '+2y']
            if '+2y' in earn_est.index and 'avg' in earn_est.columns:
                eps_2y_avg = earn_est.loc['+2y', 'avg']
    except Exception:
        pass

    forward_pe_2y = (current_price / eps_2y_avg) if (current_price and eps_2y_avg and eps_2y_avg > 0) else None

    # Streamlined Tabbed Layout
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Valuation & Income", 
        "📈 Growth Metrics",
        "💰 Profitability & Cash Flow", 
        "📉 Quarterly Trends (4Q)",
        "🎯 Bull & Bear Insights"
    ])

    with tab1:
        st.subheader("Valuation & Pricing")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Trailing P/E", f"{trailing_pe:.2f}x" if trailing_pe else "N/A")
        m2.metric("1-Yr Forward P/E", f"{forward_pe_1y:.2f}x" if forward_pe_1y else "N/A")
        m3.metric("2-Yr Forward P/E", f"{forward_pe_2y:.2f}x" if forward_pe_2y else "N/A")
        m4.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio else "N/A")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("52-Week Range", f"${fifty_two_low:,.2f} - ${fifty_two_high:,.2f}" if fifty_two_low and fifty_two_high else "N/A")
        c2.metric("Analyst Target", f"${analyst_target:,.2f}" if analyst_target else "N/A")
        c3.metric("Dividend Yield", f"{dividend_yield:.2f}%" if dividend_yield is not None else "N/A")
        c4.metric("Payout Ratio", f"{payout_ratio:.2f}%" if payout_ratio is not None else "N/A")

    with tab2:
        st.subheader("Revenue & EPS Growth Projections")
        
        st.markdown("##### Revenue Growth")
        g1, g2, g3 = st.columns(3)
        g1.metric("Current Rev Growth (YoY)", f"{rev_growth_current * 100:.2f}%" if rev_growth_current else "N/A")
        g2.metric("1-Yr Expected Rev Growth", f"{rev_growth_1y * 100:.2f}%" if rev_growth_1y else "N/A")
        g3.metric("2-Yr Expected Rev Growth", f"{rev_growth_2y * 100:.2f}%" if rev_growth_2y else "N/A")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Earnings Per Share (EPS) Growth")
        g4, g5, g6 = st.columns(3)
        g4.metric("Current EPS Growth (YoY)", f"{eps_growth_current * 100:.2f}%" if eps_growth_current else "N/A")
        g5.metric("1-Yr Expected EPS Growth", f"{eps_growth_1y * 100:.2f}%" if eps_growth_1y else "N/A")
        g6.metric("2-Yr Expected EPS Growth", f"{eps_growth_2y * 100:.2f}%" if eps_growth_2y else "N/A")

    with tab3:
        st.subheader("Profitability & Leverage")
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Gross Margin", f"{gross_margins * 100:.2f}%" if gross_margins else "N/A")
        m6.metric("Operating Margin", f"{operating_margins * 100:.2f}%" if operating_margins else "N/A")
        m7.metric("Net Profit Margin", f"{profit_margins * 100:.2f}%" if profit_margins else "N/A")
        m8.metric("Debt-to-Equity", f"{debt_to_equity:.2f}%" if debt_to_equity else "N/A")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Free Cash Flow Table (Last 4 Quarters)
        st.markdown("##### Free Cash Flow (FCF) Trend (Last 4 Quarters)")
        q_fcf_data = []
        try:
            q_cf = ticker.quarterly_cashflow
            if q_cf is not None and not q_cf.empty:
                fcf_row = find_row_flexible(q_cf, ['free cash flow'])
                op_row = find_row_flexible(q_cf, ['operating cash flow', 'total cash from operating activities'])
                capex_row = find_row_flexible(q_cf, ['capital expenditures', 'capital expenditure'])
                
                for date in q_cf.columns[:4]:
                    q_date_str = pd.to_datetime(date).strftime('%b %Y')
                    fcf_val = None
                    if fcf_row:
                        fcf_val = q_cf.loc[fcf_row, date]
                    elif op_row and capex_row:
                        op = q_cf.loc[op_row, date]
                        cap = q_cf.loc[capex_row, date]
                        if pd.notna(op) and pd.notna(cap):
                            fcf_val = op + cap if cap < 0 else op - cap
                            
                    if pd.notna(fcf_val):
                        q_fcf_data.append({
                            'Quarter Ending': q_date_str,
                            'Free Cash Flow': smart_format(fcf_val)
                        })
        except Exception:
            pass

        if q_fcf_data:
            df_fcf = pd.DataFrame(q_fcf_data)
            st.dataframe(df_fcf, width='stretch', hide_index=True)
        else:
            st.info("Quarterly Free Cash Flow data unavailable.")

    with tab4:
        st.subheader("Net Margin % Trend (Last 4 Quarters)")
        q_margins_data = []
        try:
            q_fin = ticker.quarterly_financials
            if q_fin is not None and not q_fin.empty:
                ni_row = find_row_flexible(q_fin, ['net income'])
                rev_row = find_row_flexible(q_fin, ['total revenue', 'revenue'])
                if ni_row and rev_row:
                    for date in q_fin.columns[:4]:
                        ni = q_fin.loc[ni_row, date]
                        rev = q_fin.loc[rev_row, date]
                        if pd.notna(ni) and pd.notna(rev) and rev != 0:
                            q_margins_data.append({
                                'Quarter Ending': pd.to_datetime(date).strftime('%b %Y'),
                                'Net Margin (%)': round((ni / rev) * 100, 2)
                            })
        except Exception:
            pass

        if q_margins_data:
            df_m = pd.DataFrame(q_margins_data)
            st.dataframe(df_m, width='stretch', hide_index=True)
        else:
            st.info("Quarterly net margin data unavailable.")

    with tab5:
        # Automated Bull & Bear Insights
        bulls, bears = [], []
        if profit_margins and profit_margins > 0.15:
            bulls.append(f"Strong profitability with a net profit margin of {profit_margins*100:.1f}%.")
        elif profit_margins and profit_margins > 0:
            bulls.append(f"Positive net profit margin of {profit_margins*100:.1f}%.")
        else:
            bears.append("Thin or negative net profit margins indicate potential earnings pressure.")

        if rev_growth_current and rev_growth_current > 0.05:
            bulls.append(f"Solid year-over-year revenue growth of {rev_growth_current*100:.1f}%.")
        elif rev_growth_current and rev_growth_current < 0:
            bears.append(f"Year-over-year revenue contraction of {rev_growth_current*100:.1f}%.")

        if debt_to_equity and debt_to_equity > 150:
            bears.append(f"Elevated financial leverage with a debt-to-equity ratio of {debt_to_equity:.1f}%.")
        elif debt_to_equity:
            bulls.append(f"Manageable debt load relative to equity (Debt/Equity: {debt_to_equity:.1f}%).")

        col_bull, col_bear = st.columns(2)
        with col_bull:
            st.subheader("🟢 Bull Case Tailwinds")
            if bulls:
                for b in bulls:
                    st.success(f"• {b}")
            else:
                st.info("No specific bullish flags triggered.")
                
        with col_bear:
            st.subheader("🔴 Bear Case Headwinds")
            if bears:
                for b in bears:
                    st.error(f"• {b}")
            else:
                st.info("No specific bearish flags triggered.")
