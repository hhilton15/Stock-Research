import altair as alt
import pandas as pd
import requests
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


def get_yf_session():
  """Returns a requests.Session with custom headers to prevent 401/429 blocks."""
  session = requests.Session()
  session.headers.update(
      {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
  )
  return session


@st.cache_data(ttl=3600)
def fetch_ticker_info(symbol):
  """Fetch ticker info dictionary with caching and custom session headers."""
  try:
    session = get_yf_session()
    t = yf.Ticker(symbol, session=session)
    info = t.info
    if not info or not isinstance(info, dict) or info.get("quoteType") is None:
      return None
    return info
  except Exception:
    return None


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


def format_rev_3dec(val):
  if pd.isna(val) or val is None:
    return "N/A"
  abs_val = abs(val)
  if abs_val >= 1e9:
    return f"${val / 1e9:,.3f}B"
  elif abs_val >= 1e6:
    return f"${val / 1e6:,.2f}M"
  else:
    return f"${val:,.0f}"


def find_revenue_row(df):
  """Specifically targets Total Revenue while ignoring Cost of Revenue, Tax, etc."""
  for row in df.index:
    r_low = str(row).lower()
    if any(bad in r_low for bad in ["cost", "tax", "other", "operating expense"]):
      continue
    if (
        "total revenue" in r_low
        or r_low == "revenue"
        or "operating revenue" in r_low
    ):
      return row
  for row in df.index:
    r_low = str(row).lower()
    if "revenue" in r_low and "cost" not in r_low:
      return row
  return None


def find_row_flexible(df, keywords):
  for row in df.index:
    r_low = str(row).lower()
    if any(kw in r_low for kw in keywords):
      return row
  return None


# Sidebar Ticker Input
st.sidebar.title("🔍 Stock Lookup")
ticker_input = (
    st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").strip().upper()
)
st.sidebar.markdown("---")
st.sidebar.caption("Data provided via Yahoo Finance (`yfinance`)")

if ticker_input:
  info = fetch_ticker_info(ticker_input)

  if not info:
    st.error(
        f"Unable to retrieve data for ticker **'{ticker_input}'**. Please verify"
        " the symbol and try again."
    )
  else:
    session = get_yf_session()
    ticker = yf.Ticker(ticker_input, session=session)

    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    name_str = info.get("longName", ticker_input)
    fifty_two_low = info.get("fiftyTwoWeekLow")
    fifty_two_high = info.get("fiftyTwoWeekHigh")

    # Daily change calculation
    daily_change_pct = info.get("regularMarketChangePercent")
    if daily_change_pct is None:
      try:
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
          p_close = hist["Close"].iloc[-2]
          c_close = hist["Close"].iloc[-1]
          daily_change_pct = ((c_close - p_close) / p_close) * 100
      except Exception:
        pass

    # YTD change calculation
    ytd_change_pct = None
    try:
      current_year = pd.Timestamp.now().year
      ytd_start = f"{current_year}-01-01"
      hist_ytd = ticker.history(start=ytd_start)
      if not hist_ytd.empty:
        start_price = hist_ytd["Close"].iloc[0]
        end_price = hist_ytd["Close"].iloc[-1]
        ytd_change_pct = ((end_price - start_price) / start_price) * 100
    except Exception:
      pass

    # Top Header Banner
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
      delta_val = (
          f"{daily_change_pct:+.2f}% Today"
          if daily_change_pct is not None
          else None
      )
      ytd_str = (
          f"{ytd_change_pct:+.2f}% YTD"
          if ytd_change_pct is not None
          else "N/A"
      )

      st.metric(
          label="Current Price",
          value=price_str,
          delta=delta_val,
      )
      st.caption(f"52-Wk Range: {range_str} | YTD: {ytd_str}")

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
    profit_margins = info.get("profitMargins") or info.get("profitmargins")
    gross_margins = info.get("grossMargins") or info.get("grossmargins")
    operating_margins = info.get("operatingMargins") or info.get(
        "operatingmargins"
    )
    free_cashflow = info.get("freeCashflow")

    # Forward Estimates
    rev_growth_1y, rev_growth_2y = None, None
    eps_growth_1y, eps_growth_2y = None, None
    eps_2y_avg = None

    try:
      rev_est = ticker.revenue_estimate
      if rev_est is not None and not rev_est.empty:
        for idx in rev_est.index:
          if "growth" in str(idx).lower():
            for col in rev_est.columns:
              c_lower = str(col).lower()
              val = rev_est.loc[idx, col]
              if pd.notna(val):
                if "+1y" in c_lower or c_lower == "1y":
                  rev_growth_1y = float(val)
                elif "+2y" in c_lower or c_lower == "2y":
                  rev_growth_2y = float(val)
        if rev_growth_1y is None and "+1y" in rev_est.index:
          val = rev_est.loc["+1y"].get("growth")
          if pd.notna(val):
            rev_growth_1y = float(val)
        if rev_growth_2y is None and "+2y" in rev_est.index:
          val = rev_est.loc["+2y"].get("growth")
          if pd.notna(val):
            rev_growth_2y = float(val)
    except Exception:
      pass

    try:
      earn_est = ticker.earnings_estimate
      if earn_est is not None and not earn_est.empty:
        for idx in earn_est.index:
          idx_lower = str(idx).lower()
          if "growth" in idx_lower:
            for col in earn_est.columns:
              c_lower = str(col).lower()
              val = earn_est.loc[idx, col]
              if pd.notna(val):
                if "+1y" in c_lower or c_lower == "1y":
                  eps_growth_1y = float(val)
                elif "+2y" in c_lower or c_lower == "2y":
                  eps_growth_2y = float(val)
          if "avg" in idx_lower or "mean" in idx_lower:
            for col in earn_est.columns:
              c_lower = str(col).lower()
              val = earn_est.loc[idx, col]
              if pd.notna(val):
                if "+2y" in c_lower or c_lower == "2y":
                  eps_2y_avg = float(val)

        if eps_growth_1y is None and "+1y" in earn_est.index:
          val = earn_est.loc["+1y"].get("growth")
          if pd.notna(val):
            eps_growth_1y = float(val)
        if eps_growth_2y is None and "+2y" in earn_est.index:
          val = earn_est.loc["+2y"].get("growth")
          if pd.notna(val):
            eps_growth_2y = float(val)
        if eps_2y_avg is None and "+2y" in earn_est.index:
          val = earn_est.loc["+2y"].get("avg") or earn_est.loc["+2y"].get(
              "mean"
          )
          if pd.notna(val):
            eps_2y_avg = float(val)
    except Exception:
      pass

    forward_pe_2y = (
        (current_price / eps_2y_avg)
        if (current_price and eps_2y_avg and eps_2y_avg > 0)
        else None
    )

    # Calculate Analyst Target Upside/Downside
    target_upside = None
    if analyst_target and current_price and current_price > 0:
      target_upside = ((analyst_target - current_price) / current_price) * 100

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
      m1.metric("Trailing P/E", f"{trailing_pe:.2f}x" if trailing_pe else "N/A")
      m2.metric(
          "1-Yr Forward P/E", f"{forward_pe_1y:.2f}x" if forward_pe_1y else "N/A"
      )
      m3.metric(
          "2-Yr Forward P/E", f"{forward_pe_2y:.2f}x" if forward_pe_2y else "N/A"
      )
      m4.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio else "N/A")

      st.markdown("<br>", unsafe_allow_html=True)
      c1, c2, c3 = st.columns(3)
      c1.metric(
          "Analyst Target",
          f"${analyst_target:,.2f}" if analyst_target else "N/A",
          delta=f"{target_upside:+.2f}% Potential"
          if target_upside is not None
          else None,
      )
      c2.metric(
          "Dividend Yield",
          f"{dividend_yield:.2f}%" if dividend_yield is not None else "N/A",
      )
      c3.metric(
          "Payout Ratio",
          f"{payout_ratio:.2f}%" if payout_ratio is not None else "N/A",
      )

    with tab2:
      st.subheader("Annual Financial Trends & Forward Expectations")

      annual_table_rows = []
      try:
        annual_fin = ticker.financials
        if annual_fin is not None and not annual_fin.empty:
          rev_row_a = find_revenue_row(annual_fin)
          eps_row_a = find_row_flexible(
              annual_fin, ["basic eps", "diluted eps"]
          )
          ni_row_a = find_row_flexible(annual_fin, ["net income"])
          shares_row_a = find_row_flexible(
              annual_fin, ["basic average shares", "diluted average shares"]
          )

          sorted_annual_cols = sorted(list(annual_fin.columns))
          a_dates, a_revs, a_eps = [], [], []

          for col in sorted_annual_cols:
            date_dt = pd.to_datetime(col)
            a_dates.append(date_dt.strftime("%Y"))

            r_val = (
                annual_fin.loc[rev_row_a, col]
                if rev_row_a and pd.notna(annual_fin.loc[rev_row_a, col])
                else None
            )
            a_revs.append(r_val)

            e_val = None
            if eps_row_a and pd.notna(annual_fin.loc[eps_row_a, col]):
              e_val = annual_fin.loc[eps_row_a, col]
            elif ni_row_a and shares_row_a:
              ni = annual_fin.loc[ni_row_a, col]
              sh = annual_fin.loc[shares_row_a, col]
              if pd.notna(ni) and pd.notna(sh) and sh > 0:
                e_val = ni / sh
            a_eps.append(e_val)

          for i in range(len(sorted_annual_cols)):
            curr_yr = a_dates[i]
            r_curr = a_revs[i]
            e_curr = a_eps[i]

            rev_growth_yoy = "N/A"
            if (
                i > 0
                and a_revs[i - 1] is not None
                and a_revs[i - 1] != 0
                and r_curr is not None
            ):
              g = (r_curr - a_revs[i - 1]) / abs(a_revs[i - 1])
              rev_growth_yoy = f"{g * 100:.2f}%"

            eps_growth_yoy = "N/A"
            if (
                i > 0
                and a_eps[i - 1] is not None
                and a_eps[i - 1] != 0
                and e_curr is not None
            ):
              g_eps = (e_curr - a_eps[i - 1]) / abs(a_eps[i - 1])
              eps_growth_yoy = f"{g_eps * 100:.2f}%"

            annual_table_rows.append({
                "Fiscal Year": curr_yr,
                "Revenue": format_rev_3dec(r_curr),
                "Revenue Growth": rev_growth_yoy,
                "EPS": f"${e_curr:,.2f}" if e_curr is not None else "N/A",
                "EPS Growth": eps_growth_yoy,
            })
          annual_table_rows.reverse()
      except Exception:
        pass

      st.markdown("##### Multi-Year Annual Financial Performance")
      if annual_table_rows:
        df_annual = pd.DataFrame(annual_table_rows)
        st.dataframe(df_annual, use_container_width=True, hide_index=True)
      else:
        st.info("Annual financial trends data unavailable.")

      st.markdown("<br>", unsafe_allow_html=True)
      st.markdown("##### Forward Analyst Expectations")
      g1, g2, g3, g4 = st.columns(4)
      g1.metric(
          "1-Yr Expected Rev Growth",
          f"{rev_growth_1y * 100:.2f}%" if rev_growth_1y is not None else "N/A",
      )
      g2.metric(
          "2-Yr Expected Rev Growth",
          f"{rev_growth_2y * 100:.2f}%" if rev_growth_2y is not None else "N/A",
      )
      g3.metric(
          "1-Yr Expected EPS Growth",
          f"{eps_growth_1y * 100:.2f}%" if eps_growth_1y is not None else "N/A",
      )
      g4.metric(
          "2-Yr Expected EPS Growth",
          f"{eps_growth_2y * 100:.2f}%" if eps_growth_2y is not None else "N/A",
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
          f"{operating_margins * 100:.2f}%" if operating_margins else "N/A",
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

      st.markdown("##### Free Cash Flow (FCF) Trend (Last 4 Quarters)")
      q_fcf_data = []
      try:
        q_cf = ticker.quarterly_cashflow
        if q_cf is not None and not q_cf.empty:
          fcf_row = find_row_flexible(q_cf, ["free cash flow"])
          op_row = find_row_flexible(
              q_cf,
              ["operating cash flow", "total cash from operating activities"],
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
        df_fcf = pd.DataFrame(
            q_fcf_data, columns=["Quarter Ending", "Free Cash Flow"]
        )
        st.dataframe(df_fcf, use_container_width=True, hide_index=True)
      else:
        st.info("Quarterly Free Cash Flow data unavailable.")

    with tab4:
      st.subheader("Quarterly Data & Performance Trends")

      rev_table_rows = []
      eps_table_rows = []

      try:
        q_fin = ticker.quarterly_financials
        if q_fin is not None and not q_fin.empty:
          rev_row = find_revenue_row(q_fin)
          eps_row = find_row_flexible(q_fin, ["basic eps", "diluted eps"])
          ni_row = find_row_flexible(q_fin, ["net income"])
          shares_row = find_row_flexible(
              q_fin, ["basic average shares", "diluted average shares"]
          )

          sorted_cols = sorted(list(q_fin.columns))
          rev_vals = []
          eps_vals = []
          dates_list = []

          for col in sorted_cols:
            date_dt = pd.to_datetime(col)
            dates_list.append(date_dt.strftime("%b %Y"))

            r_val = (
                q_fin.loc[rev_row, col]
                if rev_row and pd.notna(q_fin.loc[rev_row, col])
                else None
            )
            rev_vals.append(r_val)

            e_val = None
            if eps_row and pd.notna(q_fin.loc[eps_row, col]):
              e_val = q_fin.loc[eps_row, col]
            elif ni_row and shares_row:
              ni = q_fin.loc[ni_row, col]
              sh = q_fin.loc[shares_row, col]
              if pd.notna(ni) and pd.notna(sh) and sh > 0:
                e_val = ni / sh
            eps_vals.append(e_val)

          num_periods = len(sorted_cols)
          for i in range(num_periods):
            curr_date = dates_list[i]

            # Revenue Row
            r_curr = rev_vals[i]
            qoq_rev_str = "N/A"
            if r_curr is not None and pd.notna(r_curr):
              if (
                  i > 0
                  and rev_vals[i - 1] is not None
                  and rev_vals[i - 1] != 0
              ):
                q_val = (r_curr - rev_vals[i - 1]) / abs(rev_vals[i - 1])
                qoq_rev_str = f"{q_val * 100:.2f}%"

              rev_table_rows.append({
                  "Quarter Ending": curr_date,
                  "Revenue": format_rev_3dec(r_curr),
                  "QoQ Growth": qoq_rev_str,
              })

            # EPS Row
            e_curr = eps_vals[i]
            qoq_eps_str = "N/A"
            if e_curr is not None and pd.notna(e_curr):
              if (
                  i > 0
                  and eps_vals[i - 1] is not None
                  and eps_vals[i - 1] != 0
              ):
                q_eps = (e_curr - eps_vals[i - 1]) / abs(eps_vals[i - 1])
                qoq_eps_str = f"{q_eps * 100:.2f}%"

              eps_table_rows.append({
                  "Quarter Ending": curr_date,
                  "EPS": f"${e_curr:,.2f}",
                  "QoQ Growth": qoq_eps_str,
              })

          rev_table_rows.reverse()
          eps_table_rows.reverse()
          rev_table_rows = rev_table_rows[:4]
          eps_table_rows = eps_table_rows[:4]
      except Exception:
        pass

      st.markdown("##### Recent Quarterly Revenue Performance")
      if rev_table_rows:
        df_rev = pd.DataFrame(rev_table_rows)[
            ["Quarter Ending", "Revenue", "QoQ Growth"]
        ]
        st.dataframe(df_rev, use_container_width=True, hide_index=True)
      else:
        st.info("Quarterly revenue data unavailable.")

      st.markdown("<br>", unsafe_allow_html=True)
      st.markdown("##### Recent Quarterly EPS Performance")
      if eps_table_rows:
        df_eps = pd.DataFrame(eps_table_rows)[
            ["Quarter Ending", "EPS", "QoQ Growth"]
        ]
        st.dataframe(df_eps, use_container_width=True, hide_index=True)
      else:
        st.info("Quarterly EPS data unavailable.")

      st.markdown("<br>", unsafe_allow_html=True)
      st.markdown("##### Net Margin % Trend (Last 4 Quarters)")
      q_margins_data = []
      try:
        q_fin = ticker.quarterly_financials
        if q_fin is not None and not q_fin.empty:
          ni_row = find_row_flexible(q_fin, ["net income"])
          rev_row = find_revenue_row(q_fin)
          if ni_row and rev_row:
            for date in q_fin.columns[:4]:
              ni = q_fin.loc[ni_row, date]
              rev = q_fin.loc[rev_row, date]
              if pd.notna(ni) and pd.notna(rev) and rev != 0:
                q_margins_data.append({
                    "Quarter Ending": pd.to_datetime(date).strftime("%b %Y"),
                    "Net Margin (%)": f"{((ni / rev) * 100):.2f}%",
                })
      except Exception:
        pass

      if q_margins_data:
        df_m = pd.DataFrame(
            q_margins_data, columns=["Quarter Ending", "Net Margin (%)"]
        )
        st.dataframe(df_m, use_container_width=True, hide_index=True)
      else:
        st.info("Quarterly net margin data unavailable.")

    with tab5:
      st.subheader("Historical P/E Ratio (Last 3 Years)")
      pe_history_data = []
      chart_data = []

      try:
        income_stmt = ticker.financials
        history_prices = ticker.history(period="5y")

        if (
            income_stmt is not None
            and not income_stmt.empty
            and not history_prices.empty
        ):
          eps_row = find_row_flexible(
              income_stmt, ["basic eps", "diluted eps"]
          )
          ni_row = find_row_flexible(income_stmt, ["net income"])
          shares_row = find_row_flexible(
              income_stmt, ["basic average shares", "diluted average shares"]
          )

          if history_prices.index.tz is not None:
            history_prices.index = history_prices.index.tz_localize(None)

          for col_date in income_stmt.columns[:3]:
            date_dt = pd.to_datetime(col_date)
            if hasattr(date_dt, "tz") and date_dt.tz is not None:
              date_dt = date_dt.tz_localize(None)

            year_str = date_dt.strftime("%Y")

            eps_val = None
            if eps_row and pd.notna(income_stmt.loc[eps_row, col_date]):
              eps_val = income_stmt.loc[eps_row, col_date]
            elif ni_row and shares_row:
              ni = income_stmt.loc[ni_row, col_date]
              sh = income_stmt.loc[shares_row, col_date]
              if pd.notna(ni) and pd.notna(sh) and sh > 0:
                eps_val = ni / sh

            if eps_val and abs(eps_val) > 1000 and shares_row:
              sh = income_stmt.loc[shares_row, col_date]
              if sh and sh > 0:
                eps_val = eps_val / sh

            hist_sub = history_prices.loc[:date_dt]
            if not hist_sub.empty and eps_val and eps_val > 0:
              close_p = hist_sub["Close"].iloc[-1]
              hist_pe = close_p / eps_val
              pe_history_data.append({
                  "Fiscal Year": year_str,
                  "Fiscal Year End": date_dt.strftime("%b %d, %Y"),
                  "Year-End Price": f"${close_p:,.2f}",
                  "Historical P/E": f"{hist_pe:.2f}x",
              })
              chart_data.append({"Fiscal Year": year_str, "P/E": hist_pe})
      except Exception:
        pass

      if pe_history_data:
        df_pe = pd.DataFrame(pe_history_data)
        st.dataframe(df_pe, use_container_width=True, hide_index=True)

        if chart_data:
          st.markdown("##### Historical P/E Multiple Trend")
          df_chart = pd.DataFrame(chart_data).sort_values(by="Fiscal Year")

          # Altair chart with interactivity disabled so touch-scrolling works smoothly
          chart = (
              alt.Chart(df_chart)
              .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
              .encode(
                  x=alt.X("Fiscal Year:N", title="Fiscal Year"),
                  y=alt.Y("P/E:Q", title="P/E Multiple"),
                  tooltip=["Fiscal Year", "P/E"],
              )
              .properties(height=300)
              .interactive(False)
          )
          st.altair_chart(chart, use_container_width=True)
      else:
        st.info(
            "Historical P/E data is currently unavailable for this ticker's"
            " annual filings."
        )

    with tab6:
      bulls, bears = [], []

      if profit_margins:
        if profit_margins > 0.15:
          bulls.append(
              "Strong bottom-line profitability with a net profit margin of"
              f" {profit_margins * 100:.1f}%."
          )
        elif profit_margins < 0.05:
          bears.append(
              "Compressed profitability with a low net profit margin of"
              f" {profit_margins * 100:.1f}%."
          )

      if rev_growth_1y:
        if rev_growth_1y > 0.05:
          bulls.append(
              "Solid 1-Yr expected revenue growth of"
              f" {rev_growth_1y * 100:.1f}%."
          )
        elif rev_growth_1y < 0:
          bears.append(
              "Projected 1-Yr revenue contraction of"
              f" {rev_growth_1y * 100:.1f}%."
          )

      if peg_ratio:
        if peg_ratio > 2.5:
          bears.append(
              f"Elevated PEG ratio of {peg_ratio:.2f} indicates potential"
              " growth-adjusted overvaluation."
          )
        elif peg_ratio < 1.2:
          bulls.append(
              f"Attractive PEG ratio of {peg_ratio:.2f} relative to growth"
              " rate."
          )

      if trailing_pe and trailing_pe > 35:
        bears.append(
            "Trading at a premium multiple with a trailing P/E of"
            f" {trailing_pe:.1f}x."
        )

      if debt_to_equity:
        if debt_to_equity > 150:
          bears.append(
              "Elevated debt exposure with a debt-to-equity ratio of"
              f" {debt_to_equity:.1f}%."
          )
        elif debt_to_equity < 50:
          bulls.append(
              "Conservative balance sheet with low leverage (Debt/Equity:"
              f" {debt_to_equity:.1f}%)."
          )

      if free_cashflow:
        if free_cashflow > 0:
          bulls.append(
              "Strong cash generation with annual FCF of"
              f" {smart_format(free_cashflow)}."
          )
        else:
          bears.append(
              "Negative cash generation; burning free cash flow over the"
              " period."
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
