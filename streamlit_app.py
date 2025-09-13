# streamlit_app.py
# Reinforcement Calculator — Canadian rebar sizes (10M, 15M, 20M, 25M, 30M)
# Author: ChatGPT (for Arman)
# Notes:
# - Inputs mirror your Calcpad script defaults and units.
# - Outputs include spacing (in O.C.), development add-on length l_add (mm),
#   required bar length L_req (ft), 0.3*ln length L_03ln (ft), and governing length (ft).
# - All calculations follow the relationships shown in your snippet:
#     d = t_slab - d_b/2 - 40 mm
#     l_db = 16*d_b
#     l_span = L_s/16
#     l_add = max(d, l_db, l_span)
#     L_req = l_inf + t_wall + l_h - d_c + l_add
#     L_03ln = 0.3*L_s + t_wall + l_h - d_c
# - Rebar areas use CSA nominal mm²: 10M=100, 15M=200, 20M=300, 25M=500, 30M=700
# - Diameters (mm) used here: 10M=11.3, 15M=16.0, 20M=19.5, 25M=25.2, 30M=29.9
# - Hook lengths (mm) matched to your script: 10M=200, 15M=250, 20M=300, 25M=400, 30M=500
# - Spacing formula from your script: s = L_wall/(Nbars-1) with L_wall in feet → inches

import math
import pandas as pd
import streamlit as st

MM_PER_IN = 25.4
MM_PER_FT = 304.8

st.set_page_config(page_title="Reinforcement Calculator", layout="wide")

st.markdown("""
# Reinforcement Calculator
Configure the inputs in the sidebar. Results are computed for **10M, 15M, 20M, 25M, 30M** per your formulas.

**Key formulas**
- d = t_slab − d_b/2 − 40 mm  
- l_db = 16·d_b  
- l_span = L_s/16  
- l_add = max(d, l_db, l_span)  
- L_req = l_inf + t_wall + l_h − d_c + l_add  
- L_03ln = 0.3·L_s + t_wall + l_h − d_c

_Note: Units are mixed to match your workflow; conversions handled automatically._
""")

with st.sidebar:
    st.header("Inputs")
    # Main inputs (defaults from your snippet in braces)
    A_s = st.number_input("Area required for the wall length, A_s (mm²)", min_value=0.0, value=7416.0, step=1.0, format="%0.3f")
    L_wall_ft = st.number_input("Wall length, L_wall (ft)", min_value=0.0, value=13.6, step=0.1, format="%0.3f")
    t_wall_mm = st.number_input("Wall thickness, t_wall (mm)", min_value=0.0, value=254.0, step=1.0, format="%0.1f")

    st.divider()
    d_c_mm = st.number_input("Clear cover, d_c (mm)", min_value=0.0, value=38.0, step=1.0, format="%0.1f")
    l_inf_m = st.number_input("Inflection point distance beyond support, l_inf (m)", min_value=0.0, value=2.0, step=0.1, format="%0.3f")

    st.divider()
    st.caption("Check against code-specified 0.3·ln criterion")
    L_s_mm = st.number_input("Clear span, L_s (mm)", min_value=0.0, value=5700.0, step=10.0, format="%0.1f")
    t_slab_mm = st.number_input("Slab thickness, t_slab (mm)", min_value=0.0, value=300.0, step=1.0, format="%0.1f")

    st.divider()
    st.subheader("Rebar presets (CSA)")
    st.caption("Override if needed.")

    # Allow override of bar properties
    col_a, col_b = st.columns(2)
    with col_a:
        d10 = st.number_input("10M diameter (mm)", min_value=0.0, value=11.3, step=0.1)
        d20 = st.number_input("20M diameter (mm)", min_value=0.0, value=19.5, step=0.1)
        d30 = st.number_input("30M diameter (mm)", min_value=0.0, value=29.9, step=0.1)
    with col_b:
        d15 = st.number_input("15M diameter (mm)", min_value=0.0, value=16.0, step=0.1)
        d25 = st.number_input("25M diameter (mm)", min_value=0.0, value=25.2, step=0.1)

    col_c, col_d = st.columns(2)
    with col_c:
        A10 = st.number_input("10M area (mm²)", min_value=0.0, value=100.0, step=5.0)
        A20 = st.number_input("20M area (mm²)", min_value=0.0, value=300.0, step=5.0)
        A30 = st.number_input("30M area (mm²)", min_value=0.0, value=700.0, step=5.0)
    with col_d:
        A15 = st.number_input("15M area (mm²)", min_value=0.0, value=200.0, step=5.0)
        A25 = st.number_input("25M area (mm²)", min_value=0.0, value=500.0, step=5.0)

    col_e, col_f = st.columns(2)
    with col_e:
        h10 = st.number_input("10M hook length (mm)", min_value=0.0, value=200.0, step=10.0)
        h20 = st.number_input("20M hook length (mm)", min_value=0.0, value=300.0, step=10.0)
        h30 = st.number_input("30M hook length (mm)", min_value=0.0, value=500.0, step=10.0)
    with col_f:
        h15 = st.number_input("15M hook length (mm)", min_value=0.0, value=250.0, step=10.0)
        h25 = st.number_input("25M hook length (mm)", min_value=0.0, value=400.0, step=10.0)


# Pack bar data
bars = [
    {"label": "10M", "dia": d10, "area": A10, "hook": h10},
    {"label": "15M", "dia": d15, "area": A15, "hook": h15},
    {"label": "20M", "dia": d20, "area": A20, "hook": h20},
    {"label": "25M", "dia": d25, "area": A25, "hook": h25},
    {"label": "30M", "dia": d30, "area": A30, "hook": h30},
]

# Helpers

def calc_for_bar(A_s_mm2: float, L_wall_ft: float, t_wall_mm: float, d_c_mm: float,
                 l_inf_m: float, L_s_mm: float, t_slab_mm: float,
                 bar_label: str, dia_mm: float, area_per_bar_mm2: float, hook_len_mm: float):
    """Compute spacing, l_add, L_req, L_03ln for one bar size."""
    # Number of bars
    n_bars = math.ceil(A_s_mm2 / max(area_per_bar_mm2, 1e-9)) if A_s_mm2 > 0 else 0

    # Spacing in inches (O.C.) based on wall length in feet
    if n_bars >= 2:
        spacing_in = (L_wall_ft * 12.0) / (n_bars - 1)
    else:
        spacing_in = float("nan")

    # Development add-on calculations (all mm)
    d_effective_mm = t_slab_mm - dia_mm/2.0 - 40.0
    l_db_mm = 16.0 * dia_mm
    l_span_mm = L_s_mm / 16.0
    l_add_mm = max(d_effective_mm, l_db_mm, l_span_mm)

    # Required lengths (mm)
    L_req_mm = (l_inf_m * 1000.0) + t_wall_mm + hook_len_mm - d_c_mm + l_add_mm
    L_03ln_mm = 0.3 * L_s_mm + t_wall_mm + hook_len_mm - d_c_mm

    # Convert to feet
    L_req_ft = L_req_mm / MM_PER_FT
    L_03ln_ft = L_03ln_mm / MM_PER_FT
    governing_ft = max(L_req_ft, L_03ln_ft)

    return {
        "Bar": bar_label,
        "Dia (mm)": round(dia_mm, 2),
        "Area/bar (mm²)": round(area_per_bar_mm2, 1),
        "Bars (#)": n_bars,
        "Spacing (in O.C.)": None if math.isnan(spacing_in) else round(spacing_in, 2),
        "d (mm)": round(d_effective_mm, 1),
        "l_db (mm)": round(l_db_mm, 1),
        "l_span (mm)": round(l_span_mm, 1),
        "l_add (mm)": round(l_add_mm, 1),
        "L_req (ft)": round(L_req_ft, 3),
        "L_03ln (ft)": round(L_03ln_ft, 3),
        "Governing length (ft)": round(governing_ft, 3),
    }

# Compute results
rows = []
for b in bars:
    rows.append(
        calc_for_bar(
            A_s, L_wall_ft, t_wall_mm, d_c_mm,
            l_inf_m, L_s_mm, t_slab_mm,
            b["label"], b["dia"], b["area"], b["hook"]
        )
    )

# Create table
results_df = pd.DataFrame(rows)

# Highlight governing column
st.subheader("Results")
st.dataframe(results_df, use_container_width=True)

# Download CSV
csv = results_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download results as CSV",
    data=csv,
    file_name="reinforcement_calculator_results.csv",
    mime="text/csv",
)

# Quick cards per bar (optional nice summary)
with st.expander("Per-bar quick summary"):
    c1, c2, c3 = st.columns(3)
    cols = [c1, c2, c3]
    for i, (_, r) in enumerate(results_df.iterrows()):
        with cols[i % 3]:
            st.metric(
                label=f"{r['Bar']} — Governing length (ft)",
                value=f"{r['Governing length (ft)']}",
                delta=f"Req {r['L_req (ft)']}, 0.3ln {r['L_03ln (ft)']}"
            )

# Warnings & sanity checks
warns = []
for r in rows:
    if r["Bars (#)"] <= 1:
        warns.append(f"{r['Bar']}: Only {r['Bars (#)']} bar computed; spacing O.C. is undefined.")
    if r["d (mm)"] < 0:
        warns.append(f"{r['Bar']}: Effective depth d is negative ({r['d (mm)']} mm). Check t_slab / bar size / cover.")

if warns:
    st.warning("\n".join(warns))

st.caption("This tool follows your provided relationships. Always verify against current CSA A23.3 and project requirements.")
