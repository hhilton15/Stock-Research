import pandas as pd
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling for metric card highlights
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=1800)
def fetch_ticker_data(symbol):
    """Fetch ticker object and info dictionary with caching to prevent Yahoo Finance rate limits."""
    try:
        t = yf.Ticker(symbol)
        info = t.info
        if not info or info.get("quoteType") is None:
            return None, None
        return t, info
    except Exception:
        return None, None


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


def extract_estimate_growth(df, period_key):
    """Safely extracts forward growth decimal from yfinance estimate DataFrames."""
    if df is not None and not df.empty:
        if period_key in df.columns and "growth" in df.index:
            val = df.loc["growth", period_key]
            if pd.notna(val):
                return float(val)
        elif period_key in df.index and "growth" in df.columns:
            val = df.loc[period_key, "growth"]
            if pd.notna(val):
                return float(val)
    return None


# Sidebar Ticker Input
st.sidebar.title("🔍 Stock Lookup")
ticker_input = (
    st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").strip().upper()
)
st.sidebar.markdown("---")
st.sidebar.caption("Data provided via Yahoo Finance (`yfinance`)")

if ticker_input:
    ticker, info = fetch_ticker_data(ticker_input)

    if not info:
        st.error(
            f"Unable to retrieve data for ticker **'{ticker_input}'**. Please verify the symbol and try again."
        )
    else:
        current_price = info.get("currentPrice") or info.get(
            "regularMarketPrice"
        )
        name_str = info.get("longName", ticker_input)
        fifty_two_low = info.get("fiftyTwoWeekLow")
        fifty_two_high = info.get("fiftyTwoWeekHigh")

        # Top Header Banner with combined Current Price & 52-Week Range
        col_head1, col_head2 = st.columns([2.5, 1.5])
        with col_head1:
            st.title(f"{name_str} ({ticker_input})")
            st.caption("Fundamental Analysis Dashboard")
        with col_head2:
            price_str = f"${current_price:,.2f}" if current_price else "N/A"
            range_str = (
                f"${fifty_two_low:,.2f} - ${fifty_two_high:,.2f}"
                if (fifty_two_low and fifty_two_high)
                else "N/A"
            )
            st.metric(
                label="Current Price",
                value=price_str,
                delta=f"52-Wk Range: {range_str}",
                delta_color="off",
            )

        st.markdown("---")

        # Key Financial Metrics
        trailing_pe = info.get("trailingPE")
        forward_pe_1y = info.get("forwardPE")
        peg_ratio = info.get("pegRatio")
        debt_to_equity = info.get("debtToEquity")

        # Dividend Yield
        div_rate = info.get("dividendRate")
        raw_div_yield = info.get("dividendYield") or info.get(
            "trailingAnnualDividendYield"
        )
        if div_rate and current_price and current_price > 0:
            dividend_yield = (div_rate / current_price) * 100
        elif raw_div_yield is not None:
            dividend_yield = (
                raw_div_yield * 100 if raw_div_yield < 1 else raw_div_yield
            )
        else:
            dividend_yield = None

        # Payout Ratio
        raw_payout = info.get("payoutRatio")
        payout_ratio = (
            (raw_payout * 100 if raw_payout < 1 else raw_payout)
            if raw_payout is not None
            else None
        )

        analyst_target = info.get("targetMeanPrice")

        # Current/Past Reported Quarterly Growth
        rev_growth_current = info.get("revenueGrowth")
        eps_growth_current = info.get("earningsGrowth")

        profit_margins = info.get("profitMargins")
        gross_margins = info.get("grossMargins")
        operating_margins = info.get("operatingMargins")
        free_cashflow = info.get("freeCashflow")

        # Forward Estimates extraction
        rev_growth_1y, rev_growth_2y = None, None
        eps_growth_1y, eps_growth_2y = None, None
        eps_2y_avg = None

        try:
            rev_est = ticker.revenue_estimate
            rev_growth_1y = extract_estimate_growth(rev_est, "+1y")
            rev_growth_2y = extract_estimate_growth(rev_est, "+2y")
        except Exception:
            pass

        try:
            earn_est = ticker.earnings_estimate
            eps_growth_1y = extract_estimate_growth(earn_est, "+1y")
            eps_growth_2y = extract_estimate_growth(earn_est, "+2y")
            if (
                earn_est is not None
                and not earn_est.empty
                and "+2y" in earn_est.columns
                and "avg" in earn_est.index
            ):
                eps_2y_avg = earn_est.loc["avg", "+2y"]
        except Exception:
            pass

        forward_pe_2y = (
            (current_price / eps_2y_avg)
            if (current_price and eps_2y_avg and eps_2y_avg > 0)
            else None
        )

        # Tabbed Layout
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Valuation & Income",
            "📈 Growth Metrics",
            "💰 Profitability & Cash Flow",
            "📉 Quarterly Trends (4Q)",
            "📉 Historical P/E",
            "🎯 Bull & Bear Insights",
        ])

        with tab1:
            st.subheader("Valuation & Pricing")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                "Trailing P/E",
                f"{trailing_pe:.2f}x" if trailing_pe else "N/A",
            )
            m2.metric(
                "1-Yr Forward P/E",
                f"{forward_pe_1y:.2f}x" if forward_pe_1y else "N/A",
            )
            m3.metric(
                "2-Yr Forward P/E",
                f"{forward_pe_2y:.2f}x" if forward_pe_2y else "N/A",
            )
            m4.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio else "N/A")

            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric(
                "Analyst Target",
                f"${analyst_target:,.2f}" if analyst_target else "N/A",
            )
            c2.metric(
                "Dividend Yield",
                f"{dividend_yield:.2f}%"
                if dividend_yield is not None
                else "N/A",
            )
            c3.metric(
                "Payout Ratio",
                f"{payout_ratio:.2f}%" if payout_ratio is not None else "N/A",
            )

        with tab2:
            st.subheader("Revenue & EPS Growth Projections")

            st.markdown("##### Revenue Growth")
            g1, g2, g3 = st.columns(3)
            g1.metric(
                "Most Recent Quarter Growth (YoY)",
                f"{rev_growth_current * 100:.2f}%"
                if rev_growth_current is not None
                else "N/A",
            )
            g2.metric(
                "1-Yr Expected Rev Growth",
                f"{rev_growth_1y * 100:.2f}%"
                if rev_growth_1y is not None
                else "N/A",
            )
            g3.metric(
                "2-Yr Expected Rev Growth",
                f"{rev_growth_2y * 100:.2f}%"
                if rev_growth_2y is not None
                else "N/A",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Earnings Per Share (EPS) Growth")
            g4, g5, g6 = st.columns(3)
            g4.metric(
                "Most Recent Quarter EPS Growth (YoY)",
                f"{eps_growth_current * 100:.2f}%"
                if eps_growth_current is not None
                else "N/A",
            )
            g5.metric(
                "1-Yr Expected EPS Growth",
                f"{eps_growth_1y * 100:.2f}%"
                if eps_growth_1y is not None
                else "N/A",
            )
            g6.metric(
                "2-Yr Expected EPS Growth",
                f"{eps_growth_2y * 100:.2f}%"
                if eps_growth_2y is not None
                else "N/A",
            )

        with tab3:
            st.subheader("Profitability & Leverage")
            m5, m6, m7, m8 = st.columns(4)
            m5.metric(
                "Gross Margin",
                f"{gross_margins * 100:.2f}%" if gross_margins else "N/A",
            )
            m6.metric(
                "Operating Margin",
                f"{operating_margins * 100:.2f}%"
                if operating_margins
                else "N/A",
            )
            m7.metric(
                "Net Profit Margin",
                f"{profit_margins * 100:.2f}%" if profit_margins else "N/A",
            )
            m8.metric(
                "Debt-to-Equity",
                f"{debt_to_equity:.2f}%" if debt_to_equity else "N/A",
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # Free Cash Flow Table
            st.markdown("##### Free Cash Flow (FCF) Trend (Last 4 Quarters)")
            q_fcf_data = []
            try:
                q_cf = ticker.quarterly_cashflow
                if q_cf is not None and not q_cf.empty:
                    fcf_row = find_row_flexible(q_cf, ["free cash flow"])
                    op_row = find_row_flexible(
                        q_cf,
                        [
                            "operating cash flow",
                            "total cash from operating activities",
                        ],
                    )
                    capex_row = find_row_flexible(
                        q_cf, ["capital expenditures", "capital expenditure"]
                    )

                    for date in q_cf.columns[:4]:
                        q_date_str = pd.to_datetime(date).strftime("%b %Y")
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
                                "Quarter Ending": q_date_str,
                                "Free Cash Flow": smart_format(fcf_val),
                            })
            except Exception:
                pass

            if q_fcf_data:
                df_fcf = pd.DataFrame(q_fcf_data)
                st.dataframe(df_fcf, use_container_width=True, hide_index=True)
            else:
                st.info("Quarterly Free Cash Flow data unavailable.")

        with tab4:
            st.subheader("Net Margin % Trend (Last 4 Quarters)")
            q_margins_data = []
            try:
                q_fin = ticker.quarterly_financials
                if q_fin is not None and not q_fin.empty:
                    ni_row = find_row_flexible(q_fin, ["net income"])
                    rev_row = find_row_flexible(q_fin, ["total revenue", "revenue"])
                    if ni_row and rev_row:
                        for date in q_fin.columns[:4]:
                            ni = q_fin.loc[ni_row, date]
                            rev = q_fin.loc[rev_row, date]
                            if pd.notna(ni) and pd.notna(rev) and rev != 0:
                                q_margins_data.append({
                                    "Quarter Ending": pd.to_datetime(
                                        date
                                    ).strftime("%b %Y"),
                                    "Net Margin (%)": f"{((ni / rev) * 100):.2f}%",
                                })
            except Exception:
                pass

            if q_margins_data:
                df_m = pd.DataFrame(q_margins_data)
                st.dataframe(df_m, use_container_width=True, hide_index=True)
            else:
                st.info("Quarterly net margin data unavailable.")

        with tab5:
            st.subheader("Historical P/E Ratio (Last 3 Years)")
            pe_history_data = []
            try:
                income_stmt = ticker.financials
                history_prices = ticker.history(period="max")

                if (
                    income_stmt is not None
                    and not income_stmt.empty
                    and not history_prices.empty
                ):
                    eps_row = find_row_flexible(
                        income_stmt, ["basic eps", "diluted eps", "net income"]
                    )
                    shares_row = find_row_flexible(
                        income_stmt, ["basic average shares", "diluted average shares"]
                    )
                    ni_row = find_row_flexible(income_stmt, ["net income"])

                    for col_date in income_stmt.columns[:3]:
                        date_dt = pd.to_datetime(col_date)
                        year_str = date_dt.strftime("%Y")

                        eps_val = None
                        if eps_row and pd.notna(income_stmt.loc[eps_row, col_date]):
                            val = income_stmt.loc[eps_row, col_date]
                            if eps_row == ni_row and shares_row:
                                sh = income_stmt.loc[shares_row, col_date]
                                if pd.notna(sh) and sh > 0:
                                    eps_val = val / sh
                            else:
                                eps_val = val
                        elif ni_row and shares_row:
                            ni = income_stmt.loc[ni_row, col_date]
                            sh = income_stmt.loc[shares_row, col_date]
                            if pd.notna(ni) and pd.notna(sh) and sh > 0:
                                eps_val = ni / sh

                        if eps_val and eps_val > 50:
                            sh = (
                                income_stmt.loc[shares_row, col_date]
                                if shares_row
                                else None
                            )
                            if sh and sh > 0:
                                eps_val = eps_val / sh

                        hist_sub = history_prices.loc[:date_dt]
                        if hist_sub.empty:
                            hist_sub = history_prices

                        if not hist_sub.empty and eps_val and eps_val > 0:
                            close_p = hist_sub["Close"].iloc[-1]
                            hist_pe = close_p / eps_val
                            pe_history_data.append({
                                "Fiscal Year": year_str,
                                "Fiscal Year End": date_dt.strftime("%b %d, %Y"),
                                "Year-End Price": f"${close_p:,.2f}",
                                "EPS": f"${eps_val:,.2f}",
                                "Historical P/E": f"{hist_pe:.2f}x",
                            })
            except Exception:
                pass

            if pe_history_data:
                df_pe = pd.DataFrame(pe_history_data)
                st.dataframe(df_pe, use_container_width=True, hide_index=True)
            else:
                st.info(
                    "Historical P/E data is currently unavailable for this ticker's annual filings."
                )

        with tab6:
            bulls, bears = [], []

            if profit_margins:
                if profit_margins > 0.15:
                    bulls.append(
                        f"Strong bottom-line profitability with a net profit margin of {profit_margins * 100:.1f}%."
                    )
                elif profit_margins < 0.05:
                    bears.append(
                        f"Compressed profitability with a low net profit margin of {profit_margins * 100:.1f}%."
                    )

            if rev_growth_current:
                if rev_growth_current > 0.05:
                    bulls.append(
                        f"Solid YoY revenue growth momentum of {rev_growth_current * 100:.1f}%."
                    )
                elif rev_growth_current < 0:
                    bears.append(
                        f"Recent YoY revenue contraction of {rev_growth_current * 100:.1f}%."
                    )

            if peg_ratio:
                if peg_ratio > 2.5:
                    bears.append(
                        f"Elevated PEG ratio of {peg_ratio:.2f} indicates potential growth-adjusted overvaluation."
                    )
                elif peg_ratio < 1.2:
                    bulls.append(
                        f"Attractive PEG ratio of {peg_ratio:.2f} relative to growth rate."
                    )

            if trailing_pe and trailing_pe > 35:
                bears.append(
                    f"Trading at a premium multiple with a trailing P/E of {trailing_pe:.1f}x."
                )

            if debt_to_equity:
                if debt_to_equity > 150:
                    bears.append(
                        f"Elevated debt exposure with a debt-to-equity ratio of {debt_to_equity:.1f}%."
                    )
                elif debt_to_equity < 50:
                    bulls.append(
                        f"Conservative balance sheet with low leverage (Debt/Equity: {debt_to_equity:.1f}%)."
                    )

            if free_cashflow:
                if free_cashflow > 0:
                    bulls.append(
                        f"Strong cash generation with annual FCF of {smart_format(free_cashflow)}."
                    )
                else:
                    bears.append(
                        "Negative cash generation; burning free cash flow over the period."
                    )

            col_bull, col_bear = st.columns(2)
            with col_bull:
                st.subheader("🟢 Bull Case Tailwinds")
                if bulls:
                    for b in bulls:
                        st.success(f"• {b}")
                else:
                    st.info("No specific bullish metrics triggered.")

            with col_bear:
                st.subheader("🔴 Bear Case Headwinds")
                if bears:
                    for b in bears:
                        st.error(f"• {b}")
                else:
                    st.info("No specific bearish metrics triggered.")
