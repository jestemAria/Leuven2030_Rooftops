import pandas as pd

def calculate_combined_score(df,
                     area_col="area_m2",
                     yield_col="specific_yield_kwh_per_kwp",
                     weight_area=0.4,
                     weight_yield=0.4,
                     weight_orient=0.2):
    g = df.copy()
    g["area_score"] = g[area_col] / g[area_col].max()
    if yield_col in g:
        g["yield_score"] = g[yield_col] / g[yield_col].max()
    else:
        g["yield_score"] = 1.0
    g["orientation_score"] = 1.0
    g["score"] = (
        weight_area   * g["area_score"] +
        weight_yield  * g["yield_score"] +
        weight_orient * g["orientation_score"]
    )
    g["score_rank"] = g["score"].rank(ascending=False, method="dense").astype(int)
    return g
