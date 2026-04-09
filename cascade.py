import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import numpy_financial as npf
import streamlit as st

# =============================================================================
# CASCADE — SMB Deal Analysis Tool | Built by Tyrus Burton
# Cascade Capital Partners / The Burton Group LLC
# =============================================================================

st.set_page_config(page_title="Cascade | SMB Deal Analyzer", layout="wide")

st.title("⚡ Cascade")
st.subheader("SMB Acquisition Deal Analysis Tool | RIC Capital Partners")
st.markdown("---")

# =============================================================================
# SIDEBAR INPUTS
# =============================================================================

st.sidebar.header("Deal Information")
deal_name = st.sidebar.text_input("Business Name", value="Target Company")
business_type = st.sidebar.text_input("Business Type / Industry", value="e.g. Bookkeeping Firm")

st.sidebar.markdown("---")
st.sidebar.header("Business Financials")
metric_type = st.sidebar.selectbox("Valuation Metric", ["SDE", "EBITDA", "Net Income", "Revenue"])
metric_value = st.sidebar.number_input(f"{metric_type} ($)", min_value=0, value=250000, step=5000)
revenue = st.sidebar.number_input("Gross Revenue ($)", min_value=0, value=500000, step=10000)
qoe_adjustment = st.sidebar.number_input("QoE Adjustment ($) — Enter negative to reduce SDE", value=0, step=5000)
adjusted_metric = metric_value + qoe_adjustment
st.sidebar.metric(f"Adjusted {metric_type}", f"${adjusted_metric:,.0f}")

st.sidebar.markdown("---")
st.sidebar.header("Purchase & Capital Structure")
purchase_price = st.sidebar.number_input("Purchase Price ($)", min_value=0, value=1000000, step=10000)
purchase_multiple = purchase_price / adjusted_metric if adjusted_metric > 0 else 0
st.sidebar.metric("Purchase Multiple", f"{purchase_multiple:.2f}x")

capital_infusion = st.sidebar.number_input("Equity / Capital Infusion ($)", min_value=0, value=200000, step=5000)
working_capital = st.sidebar.number_input("Working Capital Reserve ($)", min_value=0, value=25000, step=5000)
deal_costs = st.sidebar.number_input("Deal Costs — Legal, SBA Fees, Due Diligence ($)", min_value=0, value=20000, step=1000)
total_equity_required = capital_infusion + working_capital + deal_costs
st.sidebar.metric("Total Cash Required", f"${total_equity_required:,.0f}")

st.sidebar.markdown("---")
st.sidebar.header("SBA Loan")
loan_amount = st.sidebar.number_input("SBA Loan Amount ($)", min_value=0, value=800000, step=10000)
interest_rate = st.sidebar.number_input("SBA Interest Rate (%)", min_value=0.0, value=11.0, step=0.25)
loan_term = st.sidebar.number_input("SBA Loan Term (Years)", min_value=1, value=10, step=1)

st.sidebar.markdown("---")
st.sidebar.header("Seller Financing")
seller_financing = st.sidebar.checkbox("Include Seller Financing?")
if seller_financing:
    seller_loan = st.sidebar.number_input("Seller Loan Amount ($)", min_value=0, value=0, step=5000)
    seller_rate = st.sidebar.number_input("Seller Interest Rate (%)", min_value=0.0, value=6.0, step=0.25)
    seller_term = st.sidebar.number_input("Seller Loan Term (Years)", min_value=1, value=5, step=1)
else:
    seller_loan = 0
    seller_rate = 0
    seller_term = 1

st.sidebar.markdown("---")
st.sidebar.header("Deal Assumptions")
growth_label = f"Annual {metric_type} Growth Rate (%)"
sde_growth = st.sidebar.number_input(growth_label, min_value=-20.0, value=9.0, step=0.5)
exit_multiple = st.sidebar.number_input("Exit Multiple", min_value=0.0, value=4.0, step=0.25)
holding_period = st.sidebar.number_input("Holding Period (Years)", min_value=1, value=5, step=1)
tax_rate = st.sidebar.number_input("Income Tax Rate (%)", min_value=0.0, value=37.0, step=1.0)
cap_gains_rate = st.sidebar.number_input("Capital Gains Rate (%)", min_value=0.0, value=20.0, step=1.0)
cex_pct = st.sidebar.number_input("CapEx (% of SDE)", min_value=0.0, value=10.0, step=1.0)
distribution_pct = st.sidebar.number_input("Distribution (% of Cash Flow after DS)", min_value=0.0, value=40.0, step=5.0)

# =============================================================================
# DEBT SERVICE CALCULATIONS
# =============================================================================

monthly_rate_sba = (interest_rate / 100) / 12
n_payments_sba = int(loan_term * 12)
monthly_payment_sba = npf.pmt(monthly_rate_sba, n_payments_sba, -loan_amount) if loan_amount > 0 else 0
annual_debt_service_sba = monthly_payment_sba * 12

if seller_financing and seller_loan > 0:
    monthly_rate_seller = (seller_rate / 100) / 12
    n_payments_seller = int(seller_term * 12)
    monthly_payment_seller = npf.pmt(monthly_rate_seller, n_payments_seller, -seller_loan)
    annual_debt_service_seller = monthly_payment_seller * 12
else:
    annual_debt_service_seller = 0
    monthly_payment_seller = 0
    n_payments_seller = 0

total_debt_service = annual_debt_service_sba + annual_debt_service_seller

# =============================================================================
# BUILD SBA AMORTIZATION TABLE — used for accurate exit loan balance
# =============================================================================

def build_amort_table(principal, monthly_rate, n_payments, monthly_payment):
    table = []
    balance = principal
    for month in range(1, int(n_payments) + 1):
        interest_pmt = balance * monthly_rate
        principal_pmt = monthly_payment - interest_pmt
        opening = balance
        balance = max(balance - principal_pmt, 0)
        table.append({
            'Month': month,
            'Year': np.ceil(month / 12),
            'Payment': monthly_payment,
            'Principal': principal_pmt,
            'Interest': interest_pmt,
            'Opening Balance': opening,
            'Closing Balance': balance
        })
    return pd.DataFrame(table)

amort_sba_df = build_amort_table(loan_amount, monthly_rate_sba, n_payments_sba, monthly_payment_sba)

if seller_financing and seller_loan > 0:
    amort_seller_df = build_amort_table(seller_loan, monthly_rate_seller, n_payments_seller, monthly_payment_seller)
else:
    amort_seller_df = pd.DataFrame()

# Get accurate remaining loan balance at exit year
def get_balance_at_year(amort_df, year):
    if amort_df.empty:
        return 0
    year_data = amort_df[amort_df['Year'] == year]
    if year_data.empty:
        return 0
    return year_data['Closing Balance'].iloc[-1]

remaining_sba_at_exit = get_balance_at_year(amort_sba_df, holding_period)
remaining_seller_at_exit = get_balance_at_year(amort_seller_df, holding_period) if seller_financing else 0
total_remaining_debt = remaining_sba_at_exit + remaining_seller_at_exit

# =============================================================================
# YEAR BY YEAR PROJECTIONS
# =============================================================================

years = list(range(1, int(holding_period) + 1))
data = []

for year in years:
    metric_year = adjusted_metric * (1 + sde_growth / 100) ** year
    cash_flow = metric_year - total_debt_service
    cex = metric_year * (cex_pct / 100)
    distributions = cash_flow * (distribution_pct / 100)
    distro_after_cex = distributions - cex
    distro_after_tax = distro_after_cex * (1 - tax_rate / 100)
    dscr = metric_year / total_debt_service if total_debt_service > 0 else 0
    sba_bal = get_balance_at_year(amort_sba_df, year)
    seller_bal = get_balance_at_year(amort_seller_df, year) if seller_financing else 0

    data.append({
        'Year': year,
        f'{metric_type}': metric_year,
        'Debt Service': total_debt_service,
        'Cash Flow after DS': cash_flow,
        'DSCR': round(dscr, 2),
        'CapEx': cex,
        'Distributions': distributions,
        'Distro after CapEx & Tax': distro_after_tax,
        'SBA Balance': sba_bal,
        'Seller Balance': seller_bal,
        'Total Debt': sba_bal + seller_bal
    })

df = pd.DataFrame(data)
df = df.set_index('Year')

# =============================================================================
# EXIT CALCULATIONS — uses accurate amortization balance
# =============================================================================

exit_metric = adjusted_metric * (1 + sde_growth / 100) ** holding_period
exit_ev = exit_metric * exit_multiple
equity_at_exit = exit_ev - total_remaining_debt
profit = equity_at_exit - total_equity_required
cap_gains_tax = max(profit, 0) * (cap_gains_rate / 100)
adj_equity_at_exit = equity_at_exit - cap_gains_tax
moic = adj_equity_at_exit / total_equity_required if total_equity_required > 0 else 0

# IRR includes after-tax annual distributions + exit proceeds
annual_distros = df['Distro after CapEx & Tax'].tolist()
cash_flows_irr = [-total_equity_required] + annual_distros[:-1] + [annual_distros[-1] + adj_equity_at_exit]
irr_val = npf.irr(cash_flows_irr) * 100

# =============================================================================
# DISPLAY — CAPITAL STRUCTURE
# =============================================================================

st.header(f"Deal Summary — {deal_name}")
st.caption(f"Industry: {business_type}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Purchase Price", f"${purchase_price:,.0f}")
col2.metric("SBA Loan", f"${loan_amount:,.0f}")
col3.metric("Seller Note", f"${seller_loan:,.0f}")
col4.metric("Equity Check", f"${capital_infusion:,.0f}")
col5.metric("Total Cash Required", f"${total_equity_required:,.0f}")

total_sources = loan_amount + seller_loan + capital_infusion
gap = purchase_price - total_sources
if abs(gap) > 100:
    st.warning(f"⚠️ Sources ({total_sources:,.0f}) don't match Purchase Price (${purchase_price:,.0f}). Gap: ${gap:,.0f}")
else:
    st.success(f"✅ Capital structure balances. Total Sources: ${total_sources:,.0f}")

st.markdown("---")

# =============================================================================
# DEAL RETURNS
# =============================================================================

st.header("Deal Returns")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Exit EV", f"${exit_ev:,.0f}")
col2.metric("Remaining Debt at Exit", f"${total_remaining_debt:,.0f}")
col3.metric("Adj. Equity at Exit", f"${adj_equity_at_exit:,.0f}")
col4.metric("MOIC", f"{moic:.2f}x")
col5.metric("IRR", f"{irr_val:.1f}%")

st.markdown("---")

# =============================================================================
# DEAL HEALTH CHECK
# =============================================================================

st.header("Deal Health Check")
dscr_year1 = df['DSCR'].iloc[0]
leverage_ratio = (loan_amount + seller_loan) / adjusted_metric if adjusted_metric > 0 else 0

col1, col2 = st.columns(2)

with col1:
    if dscr_year1 < 1.25:
        st.error(f"⚠️ DSCR Year 1: {dscr_year1:.2f}x — Below SBA minimum 1.25x. Lender will likely decline.")
    elif dscr_year1 < 1.5:
        st.warning(f"⚠️ DSCR Year 1: {dscr_year1:.2f}x — Above minimum but tight.")
    else:
        st.success(f"✅ DSCR Year 1: {dscr_year1:.2f}x — Healthy.")

    if leverage_ratio > 6:
        st.error(f"⚠️ Leverage: {leverage_ratio:.1f}x — Highly leveraged.")
    elif leverage_ratio > 4:
        st.warning(f"⚠️ Leverage: {leverage_ratio:.1f}x — Moderately leveraged.")
    else:
        st.success(f"✅ Leverage: {leverage_ratio:.1f}x — Conservative.")

with col2:
    if irr_val < 15:
        st.warning(f"⚠️ IRR {irr_val:.1f}% — Below typical PE hurdle of 15-20%.")
    elif irr_val < 25:
        st.success(f"✅ IRR {irr_val:.1f}% — Meets PE hurdle rate.")
    else:
        st.success(f"✅ IRR {irr_val:.1f}% — Strong return. Verify assumptions.")

    if moic < 1.5:
        st.error(f"⚠️ MOIC {moic:.2f}x — Weak return on capital.")
    elif moic < 2.5:
        st.warning(f"⚠️ MOIC {moic:.2f}x — Acceptable but not compelling.")
    else:
        st.success(f"✅ MOIC {moic:.2f}x — Strong return on capital.")

st.markdown("---")

# =============================================================================
# YEAR BY YEAR PROJECTIONS
# =============================================================================

st.header("Year by Year Projections")
st.dataframe(df.style.format({
    f'{metric_type}': '${:,.0f}',
    'Debt Service': '${:,.0f}',
    'Cash Flow after DS': '${:,.0f}',
    'CapEx': '${:,.0f}',
    'Distributions': '${:,.0f}',
    'Distro after CapEx & Tax': '${:,.0f}',
    'SBA Balance': '${:,.0f}',
    'Seller Balance': '${:,.0f}',
    'Total Debt': '${:,.0f}',
    'DSCR': '{:.2f}x'
}), use_container_width=True)

st.markdown("---")

# =============================================================================
# VISUALIZATIONS
# =============================================================================

st.header("Visualizations")

col1, col2 = st.columns(2)

with col1:
    fig1, ax1 = plt.subplots(figsize=(8, 4))
    ax1.bar(df.index, df['Cash Flow after DS'], color='steelblue')
    ax1.set_title('Cash Flow after Debt Service by Year')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('Amount ($)')
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax1.set_xticks(df.index)
    st.pyplot(fig1)

with col2:
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.plot(df.index, df['DSCR'], marker='o', color='steelblue', linewidth=2)
    ax2.axhline(y=1.25, color='red', linestyle='--', label='SBA Minimum (1.25x)')
    ax2.set_title('DSCR by Year')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('DSCR')
    ax2.set_xticks(df.index)
    ax2.legend()
    st.pyplot(fig2)

col3, col4 = st.columns(2)

with col3:
    fig3, ax3 = plt.subplots(figsize=(8, 4))
    ax3.stackplot(df.index, df['SBA Balance'], df['Seller Balance'],
                  labels=['SBA Loan', 'Seller Note'], colors=['steelblue', 'orange'], alpha=0.8)
    ax3.set_title('Debt Paydown Over Holding Period')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('Remaining Balance ($)')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax3.set_xticks(df.index)
    ax3.legend()
    st.pyplot(fig3)

with col4:
    fig4, ax4 = plt.subplots(figsize=(8, 4))
    ax4.bar(df.index, df['Distro after CapEx & Tax'], color='green', alpha=0.8)
    ax4.set_title('After-Tax Distributions by Year')
    ax4.set_xlabel('Year')
    ax4.set_ylabel('Amount ($)')
    ax4.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    ax4.set_xticks(df.index)
    st.pyplot(fig4)

st.markdown("---")

# =============================================================================
# SENSITIVITY ANALYSIS
# =============================================================================

st.header("Sensitivity Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("IRR — Entry Multiple vs Exit Multiple")
    entry_multiples = [purchase_multiple - 1, purchase_multiple - 0.5, purchase_multiple,
                       purchase_multiple + 0.5, purchase_multiple + 1]
    exit_multiples = [exit_multiple - 1, exit_multiple - 0.5, exit_multiple,
                      exit_multiple + 0.5, exit_multiple + 1]

    sensitivity_data = []
    for em in entry_multiples:
        row = []
        for xm in exit_multiples:
            if em <= 0 or xm <= 0:
                row.append(0)
                continue
            entry_pp = adjusted_metric * em
            entry_eq = entry_pp * (capital_infusion / purchase_price) if purchase_price > 0 else capital_infusion
            exit_ev_s = adjusted_metric * (1 + sde_growth / 100) ** holding_period * xm
            equity_exit_s = exit_ev_s - total_remaining_debt
            adj_eq_s = equity_exit_s - max(equity_exit_s - entry_eq, 0) * (cap_gains_rate / 100)
            cf_s = [-entry_eq] + [0] * (int(holding_period) - 1) + [adj_eq_s]
            try:
                irr_s = npf.irr(cf_s) * 100
            except:
                irr_s = 0
            row.append(round(irr_s, 1))
        sensitivity_data.append(row)

    sensitivity_df = pd.DataFrame(
        sensitivity_data,
        index=[f"{e:.1f}x entry" for e in entry_multiples],
        columns=[f"{x:.1f}x exit" for x in exit_multiples]
    )
    st.dataframe(sensitivity_df.style.format("{:.1f}%").background_gradient(cmap='RdYlGn'),
                 use_container_width=True)

with col2:
    st.subheader(f"Year 1 Cash Flow — {metric_type} Decline vs CapEx Increase")
    sde_declines = [0, -5, -10, -15, -20]
    capex_increases = [0, 5, 10, 15, 20]

    cf_sensitivity = []
    for decline in sde_declines:
        row = []
        for capex_inc in capex_increases:
            stressed_sde = adjusted_metric * (1 + decline / 100)
            stressed_cex = stressed_sde * ((cex_pct + capex_inc) / 100)
            stressed_cf = stressed_sde - total_debt_service - stressed_cex
            row.append(round(stressed_cf, 0))
        cf_sensitivity.append(row)

    cf_sensitivity_df = pd.DataFrame(
        cf_sensitivity,
        index=[f"{d}% {metric_type}" for d in sde_declines],
        columns=[f"+{c}% CapEx" for c in capex_increases]
    )
    st.dataframe(cf_sensitivity_df.style.format("${:,.0f}").background_gradient(cmap='RdYlGn'),
                 use_container_width=True)
    st.caption("Pre-tax cash flow after debt service and CapEx. Negative = business cannot cover operating costs.")

st.markdown("---")

# =============================================================================
# AMORTIZATION SCHEDULE
# =============================================================================

st.header("Amortization Schedule")

tab1, tab2 = st.tabs(["SBA Loan", "Seller Note"])

with tab1:
    st.dataframe(amort_sba_df.style.format({
        'Payment': '${:,.0f}',
        'Principal': '${:,.0f}',
        'Interest': '${:,.0f}',
        'Opening Balance': '${:,.0f}',
        'Closing Balance': '${:,.0f}'
    }), use_container_width=True)

with tab2:
    if seller_financing and not amort_seller_df.empty:
        st.dataframe(amort_seller_df.style.format({
            'Payment': '${:,.0f}',
            'Principal': '${:,.0f}',
            'Interest': '${:,.0f}',
            'Opening Balance': '${:,.0f}',
            'Closing Balance': '${:,.0f}'
        }), use_container_width=True)
    else:
        st.info("No seller financing included in this deal.")

st.markdown("---")

# =============================================================================
# SBA INDUSTRY BENCHMARKS
# =============================================================================

st.header("SBA Industry Benchmarks")
st.caption("Powered by 1.7M+ SBA 7(a) loan records from FY1991 to present")

@st.cache_data
def load_sba_data():
    sba_1991 = pd.read_csv('7a-1991-1999.csv', low_memory=False)
    sba_2000 = pd.read_csv('7a-2000-2009.csv', low_memory=False)
    sba_2010 = pd.read_csv('7a-2010-2019.csv', low_memory=False)
    sba_2020 = pd.read_csv('7a Data.csv', low_memory=False)
    combined = pd.concat([sba_1991, sba_2000, sba_2010, sba_2020], ignore_index=True)
    combined['approvalfiscalyear'] = pd.to_numeric(combined['approvalfiscalyear'], errors='coerce')
    combined['charged_off'] = combined['chargeoffdate'].notna().astype(int)
    return combined

sba_data = load_sba_data()

industry_options = sorted(sba_data['naicsdescription'].dropna().unique().tolist())
selected_industry = st.selectbox("Select Industry to Benchmark Against Your Deal", industry_options)

industry_data = sba_data[sba_data['naicsdescription'] == selected_industry]

avg_loan = industry_data['grossapproval'].mean()
avg_loan = avg_loan if pd.notna(avg_loan) else 0
avg_term = industry_data['terminmonths'].mean() / 12
avg_term = avg_term if pd.notna(avg_term) else 0
total_loans = len(industry_data)
charge_off_rate = industry_data['charged_off'].mean() * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg SBA Loan Size", f"${avg_loan:,.0f}")
col2.metric("Avg Loan Term", f"{avg_term:.1f} years")
col3.metric("Total Loans (FY1991-Present)", f"{total_loans:,}")
col4.metric("Historical Charge-Off Rate", f"{charge_off_rate:.2f}%")

if charge_off_rate > 10:
    st.error(f"⚠️ {selected_industry} has a {charge_off_rate:.1f}% historical charge-off rate — high risk industry.")
elif charge_off_rate > 5:
    st.warning(f"⚠️ {selected_industry} has a {charge_off_rate:.1f}% historical charge-off rate — moderate risk.")
else:
    st.success(f"✅ {selected_industry} has a {charge_off_rate:.1f}% historical charge-off rate — lower risk industry.")

st.caption("Note: Recent loans (FY2020+) may show lower charge-off rates as defaults typically emerge 2-4 years post-origination.")

industry_by_year = industry_data.groupby('approvalfiscalyear').size()

fig5, ax5 = plt.subplots(figsize=(12, 4))
ax5.bar(industry_by_year.index, industry_by_year.values, color='steelblue')
ax5.set_title(f'SBA Loan Volume by Year — {selected_industry}')
ax5.set_xlabel('Year')
ax5.set_ylabel('Number of Loans')
st.pyplot(fig5)

st.markdown("---")
st.caption("Cascade | Built by Tyrus Burton of Cascade Capital Partners / The Burton Group LLC")
