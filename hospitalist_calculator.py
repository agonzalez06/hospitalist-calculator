#!/usr/bin/env python3
"""
Hospitalist Compensation Calculator - Web Version (Streamlit)

FY27 (July 2026 - June 2027)
A+B Component salary model for hospitalists

Run locally: streamlit run hospitalist_calculator.py
"""

import streamlit as st
from datetime import date
from dataclasses import dataclass

# =============================================================================
# CONSTANTS
# =============================================================================

FISCAL_YEAR_START = date(2026, 7, 1)
FISCAL_YEAR_END = date(2027, 6, 30)
TOTAL_FY_DAYS = (FISCAL_YEAR_END - FISCAL_YEAR_START).days + 1

BASE_SHIFT_EQUIVALENTS = 183
STRENGTH_OF_SCHEDULE_BASE = 198500
EXPERIENCE_ADJUSTMENT_PER_YEAR = 2000
A_BASE_FOR_B_CALC = 105000  # Always uses Assistant base for B subtraction
OTHER_DEPT_RATE = 240000  # Rate per FTE for Addiction/Other Dept
ADDICTION_BOARD_BONUS = 20000

A_COMPONENT_BY_RANK = {
    "Assistant Professor": 105000,
    "Associate Professor": 120750,
    "Professor": 136500,
    "TFP NFP Physician": 105000,
}

SHIFT_TYPES = {
    "Teaching": {"ratio": 1.0, "sos": 1.0},
    "Direct Care Days": {"ratio": 1.0, "sos": 1.25},
    "Women & Families Days": {"ratio": 1.2, "sos": 1.25},
    "Episcopal": {"ratio": 0.75, "sos": 1.05},
    "Clinic": {"ratio": 0.9, "sos": 1.125},
    "Addiction": {"ratio": 1.0, "sos": 1.0},
}

NIGHT_STANDARD_THRESHOLD = 21
NIGHT_STANDARD_SOS = 1.5
NIGHT_PREMIUM_SOS = 1.75


@dataclass
class CalculationResult:
    """Holds all calculated compensation values"""
    time_fraction: float
    hm_fte: float
    hospitalist_fte: float
    clinical_fte: float
    shift_equivalents: float
    addiction_fte: float
    shift_breakdown: dict
    total_sos_value: float
    sos_multiplier: float
    a_component: float
    a_fte_adjusted: float
    b_base: float
    b_adjusted: float
    experience_years: int
    experience_adjustment: float
    b_with_experience: float
    b_fte_adjusted: float
    other_dept_comp: float
    addiction_board_bonus: float
    other_stipend: float
    total_compensation: float


def calculate_compensation(
    start_date: date,
    leave_days: int,
    status_fte: float,
    non_clinical_fte: float,
    other_dept_fte: float,
    academic_rank: str,
    shift_days: dict,
    graduation_year: int,
    addiction_board_certified: bool,
    other_stipend: float,
) -> CalculationResult:
    """Calculate hospitalist compensation based on A+B model."""

    # Time fraction
    if start_date <= FISCAL_YEAR_START:
        days_in_fy = TOTAL_FY_DAYS
    elif start_date > FISCAL_YEAR_END:
        days_in_fy = 0
    else:
        days_in_fy = (FISCAL_YEAR_END - start_date).days + 1
    effective_days = max(0, days_in_fy - leave_days)
    time_fraction = effective_days / TOTAL_FY_DAYS

    # Calculate Addiction FTE from shifts
    addiction_shifts = shift_days.get("Addiction", 0)
    addiction_fte = addiction_shifts / BASE_SHIFT_EQUIVALENTS

    # HM FTE (for B calc) = Status - Other - Addiction (NOT non-clinical)
    hm_fte = max(0, status_fte - other_dept_fte - addiction_fte)

    # Actual HM FTE (for shifts) = Status - NonClinical - Other - Addiction
    actual_hm_fte = max(0, status_fte - non_clinical_fte - other_dept_fte - addiction_fte)
    hospitalist_fte = actual_hm_fte
    clinical_fte = actual_hm_fte * time_fraction
    # Round shift equivalents to integer using Excel-style round-half-up
    # (Python's round() uses banker's rounding which rounds 0.5 to even)
    shift_equivalents = int(clinical_fte * BASE_SHIFT_EQUIVALENTS + 0.5)

    # Calculate shift breakdown and SoS
    shift_breakdown = {}
    total_sos_value = 0
    total_shift_eq = 0

    for shift_type, days in shift_days.items():
        if shift_type == "Nights" or shift_type == "Addiction":
            continue

        if shift_type in SHIFT_TYPES:
            config = SHIFT_TYPES[shift_type]
            shift_eq = days * config["ratio"]
            sos_value = shift_eq * config["sos"]
            shift_breakdown[shift_type] = {
                "days": days,
                "shift_eq": shift_eq,
                "sos_value": sos_value,
            }
            total_sos_value += sos_value
            total_shift_eq += shift_eq

    # Process nights (tiered)
    night_days = shift_days.get("Nights", 0)
    if night_days > 0:
        standard_nights = min(night_days, NIGHT_STANDARD_THRESHOLD)
        premium_nights = max(0, night_days - NIGHT_STANDARD_THRESHOLD)
        standard_sos = standard_nights * NIGHT_STANDARD_SOS
        premium_sos = premium_nights * NIGHT_PREMIUM_SOS
        shift_breakdown["Standard Nights (first 21)"] = {
            "days": standard_nights,
            "shift_eq": standard_nights,
            "sos_value": standard_sos,
        }
        shift_breakdown["Premium Nights (after 21)"] = {
            "days": premium_nights,
            "shift_eq": premium_nights,
            "sos_value": premium_sos,
        }
        total_sos_value += standard_sos + premium_sos
        total_shift_eq += night_days

    # SoS multiplier
    sos_multiplier = total_sos_value / shift_equivalents if shift_equivalents > 0 else 1.0

    # A Component - ANNUAL (not prorated by time)
    # Time fraction affects shift equivalents/SoS but A is annual amount
    a_component = A_COMPONENT_BY_RANK.get(academic_rank, 105000)
    a_fte_adjusted = a_component * status_fte

    # B Component - ANNUAL (not prorated by time)
    b_base = STRENGTH_OF_SCHEDULE_BASE
    b_adjusted = b_base * sos_multiplier

    current_year = FISCAL_YEAR_START.year
    experience_years = max(0, current_year - graduation_year)
    experience_adjustment = experience_years * EXPERIENCE_ADJUSTMENT_PER_YEAR

    # B formula: (SoS_Base × SOS + Experience) × HM_FTE - 105000 × Status_FTE
    # This is ANNUAL - time_fraction already affected shift_equivalents which affects SoS
    b_with_experience = b_adjusted + experience_adjustment
    b_fte_adjusted = round((b_with_experience * hm_fte - A_BASE_FOR_B_CALC * status_fte) / 100) * 100

    # Other Dept Comp: Addiction FTE × $240k + Other FTE × $240k
    other_dept_comp = (addiction_fte + other_dept_fte) * OTHER_DEPT_RATE * time_fraction

    # Addiction Board Bonus
    addiction_board_bonus_val = ADDICTION_BOARD_BONUS * status_fte * time_fraction if addiction_board_certified else 0

    # Total
    total_compensation = a_fte_adjusted + b_fte_adjusted + other_dept_comp + addiction_board_bonus_val + other_stipend

    return CalculationResult(
        time_fraction=time_fraction,
        hm_fte=hm_fte,
        hospitalist_fte=hospitalist_fte,
        clinical_fte=clinical_fte,
        shift_equivalents=shift_equivalents,
        addiction_fte=addiction_fte,
        shift_breakdown=shift_breakdown,
        total_sos_value=total_sos_value,
        sos_multiplier=sos_multiplier,
        a_component=a_component,
        a_fte_adjusted=a_fte_adjusted,
        b_base=b_base,
        b_adjusted=b_adjusted,
        experience_years=experience_years,
        experience_adjustment=experience_adjustment,
        b_with_experience=b_with_experience,
        b_fte_adjusted=b_fte_adjusted,
        other_dept_comp=other_dept_comp,
        addiction_board_bonus=addiction_board_bonus_val,
        other_stipend=other_stipend,
        total_compensation=total_compensation,
    )


# =============================================================================
# STREAMLIT UI
# =============================================================================

st.set_page_config(
    page_title="Hospitalist Compensation Calculator",
    page_icon=":hospital:",
    layout="wide"
)

st.markdown("""
<style>
    .stButton > button[kind="primary"] {
        background-color: #9D2235;
        border-color: #9D2235;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #7A1A2A;
        border-color: #7A1A2A;
    }
    .big-number {
        font-size: 4rem;
        font-weight: 700;
        color: #28a745;
        line-height: 1.2;
        margin: 0.5rem 0;
    }
    .row-label {
        padding-top: 8px;
        font-weight: 500;
        text-align: right;
    }
    [data-testid="stNumberInput"] {
        max-width: 120px;
    }
    [data-baseweb="select"] {
        max-width: 100%;
    }
    [data-testid="stDateInput"] {
        max-width: 150px;
    }
    [data-testid="stSlider"] {
        padding-top: 8px;
    }
    .stNumberInput button:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    .stNumberInput button:focus-visible {
        outline: none !important;
        box-shadow: none !important;
    }
    [data-baseweb="input"]:focus-within {
        border-color: #ccc !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("Hospitalist Compensation Calculator")
st.markdown("**FY 27** (July 1, 2026 - June 30, 2027)")
st.markdown("*Estimates only. Final numbers confirmed when schedule is published.*")
st.markdown("---")

col_input, col_results = st.columns([1, 1])

# =============================================================================
# INPUTS
# =============================================================================

with col_input:
    st.markdown("### Employment Status")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Start Date</p>', unsafe_allow_html=True)
    start_date = c2.date_input("Start Date", value=FISCAL_YEAR_START, min_value=date(2020, 1, 1), max_value=date(2030, 12, 31), format="MM/DD/YYYY", label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Leave Days</p>', unsafe_allow_html=True)
    leave_days = c2.number_input("Leave Days", min_value=0, max_value=365, value=0, label_visibility="collapsed")

    st.markdown("### FTE Allocation")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Status FTE</p>', unsafe_allow_html=True)
    status_fte = c2.slider("Status FTE", min_value=0.0, max_value=1.0, value=1.0, step=0.05, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Non-Clinical FTE</p>', unsafe_allow_html=True)
    non_clinical_fte = c2.slider("Non-Clinical FTE", min_value=0.0, max_value=1.0, value=0.0, step=0.01, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Other Dept FTE</p>', unsafe_allow_html=True)
    other_dept_fte = c2.slider("Other Dept FTE", min_value=0.0, max_value=1.0, value=0.0, step=0.01, label_visibility="collapsed")

    st.markdown("### Rank & Experience")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Academic Rank</p>', unsafe_allow_html=True)
    academic_rank = c2.selectbox("Academic Rank", options=list(A_COMPONENT_BY_RANK.keys()), index=0, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Graduation Year</p>', unsafe_allow_html=True)
    graduation_year = c2.number_input("Graduation Year", min_value=1980, max_value=2026, value=2026, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Addiction Board Certified</p>', unsafe_allow_html=True)
    addiction_board_certified = c2.checkbox("Addiction Board Certified", value=False, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Other Stipend ($)</p>', unsafe_allow_html=True)
    other_stipend = c2.number_input("Other Stipend", min_value=0, max_value=200000, value=0, step=1000, label_visibility="collapsed")

    st.markdown("### Shift Mix (Calendar Days)")

    with st.expander("Shift Type Reference"):
        ref_text = """
Shift Type                  Shift Eq   SoS Value   Notes
--------------------------  --------   ---------   ------------------
Teaching                    1.0        1.0
Direct Care Days            1.0        1.25        Standard day shifts
Women & Families            1.2        1.25
Standard Nights (first 21)  1.0        1.5         Night premium
Premium Nights (after 21)   1.0        1.75        Extra night premium
Episcopal                   0.75       1.05
Clinic                      0.9        1.125       Outpatient
Addiction                   1.0        --          Separate compensation

1.0 FTE = 183 shift equivalents/year
Addiction/Other Dept: $240,000 per FTE
Addiction Board Bonus: $20,000
        """
        st.code(ref_text, language=None)

    shift_days = {}

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Teaching</p>', unsafe_allow_html=True)
    teaching_options = {f"{w} week{'s' if w != 1 else ''} ({w * 7} days)": w * 7 for w in range(0, 17)}
    teaching_selection = c2.selectbox("Teaching", options=list(teaching_options.keys()), index=6, label_visibility="collapsed")
    shift_days["Teaching"] = teaching_options[teaching_selection]

    # Placeholder for Direct Care Days
    direct_care_placeholder = st.empty()

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Women & Families</p>', unsafe_allow_html=True)
    shift_days["Women & Families Days"] = c2.number_input("W&F", min_value=0, max_value=365, value=0, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Nights</p>', unsafe_allow_html=True)
    shift_days["Nights"] = c2.number_input("Nights", min_value=0, max_value=365, value=28, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Episcopal</p>', unsafe_allow_html=True)
    shift_days["Episcopal"] = c2.number_input("Episcopal", min_value=0, max_value=365, value=0, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Clinic</p>', unsafe_allow_html=True)
    shift_days["Clinic"] = c2.number_input("Clinic", min_value=0, max_value=365, value=0, label_visibility="collapsed")

    _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
    c1.markdown('<p class="row-label">Addiction Medicine</p>', unsafe_allow_html=True)
    shift_days["Addiction"] = c2.number_input("Addiction", min_value=0, max_value=365, value=0, label_visibility="collapsed")

    # Calculate Addiction FTE for display
    addiction_fte_calc = shift_days["Addiction"] / BASE_SHIFT_EQUIVALENTS

    # Calculate Direct Care Days
    actual_hm_fte = max(0, status_fte - non_clinical_fte - other_dept_fte - addiction_fte_calc)
    target_shift_eq = int(actual_hm_fte * BASE_SHIFT_EQUIVALENTS)

    other_shifts = (
        shift_days["Teaching"] * SHIFT_TYPES["Teaching"]["ratio"] +
        shift_days["Women & Families Days"] * SHIFT_TYPES["Women & Families Days"]["ratio"] +
        shift_days["Nights"] +
        shift_days["Episcopal"] * SHIFT_TYPES["Episcopal"]["ratio"] +
        shift_days["Clinic"] * SHIFT_TYPES["Clinic"]["ratio"]
    )
    direct_care_days = max(0, int(target_shift_eq - other_shifts))
    shift_days["Direct Care Days"] = direct_care_days

    with direct_care_placeholder.container():
        _, c1, c2, _ = st.columns([0.3, 1.2, 1, 0.3])
        c1.markdown('<p class="row-label">Direct Care Days</p>', unsafe_allow_html=True)
        c2.markdown(f"**{direct_care_days}** *(auto)*")

# =============================================================================
# RESULTS
# =============================================================================

with col_results:
    result = calculate_compensation(
        start_date=start_date,
        leave_days=leave_days,
        status_fte=status_fte,
        non_clinical_fte=non_clinical_fte,
        other_dept_fte=other_dept_fte,
        academic_rank=academic_rank,
        shift_days=shift_days,
        graduation_year=graduation_year,
        addiction_board_certified=addiction_board_certified,
        other_stipend=other_stipend,
    )

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.markdown("### Total Compensation")
        st.markdown(f'<div class="big-number">${result.total_compensation:,.0f}</div>', unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        m1.metric("A Component", f"${result.a_fte_adjusted:,.0f}")
        m2.metric("B Component", f"${result.b_fte_adjusted:,.0f}")

        if result.other_dept_comp > 0 or result.addiction_board_bonus > 0:
            m1, m2 = st.columns(2)
            if result.other_dept_comp > 0:
                m1.metric("Other Dept Comp", f"${result.other_dept_comp:,.0f}")
            if result.addiction_board_bonus > 0:
                m2.metric("Addiction Board Bonus", f"${result.addiction_board_bonus:,.0f}")

        if result.other_stipend > 0:
            st.metric("Other Stipend", f"${result.other_stipend:,.0f}")

    with right_col:
        st.markdown("### FTE Summary")
        total_calendar_days = sum(v for k, v in shift_days.items() if k != "Addiction") + shift_days.get("Addiction", 0)
        other_dept_fte_total = result.addiction_fte + other_dept_fte
        st.markdown(f"""
| Metric | Value |
|--------|-------|
| Status FTE | {status_fte:.2f} |
| Hospitalist FTE | {result.hospitalist_fte:.2f} |
| Other Dept FTE | {other_dept_fte_total:.2f} |
| Clinical FTE | {result.clinical_fte:.2f} |
| Shift Equivalents | {result.shift_equivalents:.0f} |
| Calendar Days | {total_calendar_days} |
        """)

    st.markdown("---")

    st.markdown("### A Component (Base Salary)")
    st.markdown(f"""
- **Rank:** {academic_rank}
- **Base A:** ${result.a_component:,}
- **FTE Adjusted:** ${result.a_fte_adjusted:,.0f}
    """)

    st.markdown("---")

    st.markdown("### B Component (Strength of Schedule)")

    if result.shift_breakdown:
        st.markdown("**Shift Breakdown:**")
        breakdown_md = "| Shift Type | Days | Shift Eq | SoS Value |\n|------------|------|----------|----------|\n"
        total_days = 0
        total_shift_eq = 0
        for shift_type, data in result.shift_breakdown.items():
            if data["days"] > 0:
                breakdown_md += f"| {shift_type} | {data['days']} | {data['shift_eq']:.1f} | {data['sos_value']:.2f} |\n"
                total_days += data["days"]
                total_shift_eq += data["shift_eq"]
        breakdown_md += f"| **Total** | **{total_days}** | **{total_shift_eq:.1f}** | **{result.total_sos_value:.2f}** |"
        st.markdown(breakdown_md)

    st.markdown(f"""
- **SoS Multiplier:** {result.sos_multiplier:.4f}
- **SoS Base:** ${result.b_base:,}
- **SoS Adjusted:** ${result.b_adjusted:,.0f}
- **Experience:** {result.experience_years} years (+${result.experience_adjustment:,})
- **B FTE Adjusted:** ${result.b_fte_adjusted:,.0f}
    """)

    if result.other_dept_comp > 0 or result.addiction_board_bonus > 0:
        st.markdown("---")
        st.markdown("### Other Compensation")
        if result.addiction_fte > 0:
            st.markdown(f"- **Addiction FTE:** {result.addiction_fte:.2f} × $240,000 = ${result.addiction_fte * OTHER_DEPT_RATE:,.0f}")
        if other_dept_fte > 0:
            st.markdown(f"- **Other Dept FTE:** {other_dept_fte:.2f} × $240,000 = ${other_dept_fte * OTHER_DEPT_RATE:,.0f}")
        if result.addiction_board_bonus > 0:
            st.markdown(f"- **Addiction Board Bonus:** ${result.addiction_board_bonus:,.0f}")
