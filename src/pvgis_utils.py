import requests

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"

WP_PER_M2 = 190.0
FILL_FACTOR = 0.6
DEFAULT_TILT = 30
DEFAULT_AZIMUTH = 0
DEFAULT_LOSS = 14
CO2_KG_PER_KWH = 0.23

class PVGISError(Exception):
    pass

def get_pvgis_specific_yield(lat, lon,
                             peakpower_kw=1.0,
                             tilt_deg=DEFAULT_TILT,
                             azimuth_deg=DEFAULT_AZIMUTH,
                             loss_percent=DEFAULT_LOSS):
    params = {
        "lat": lat, "lon": lon,
        "peakpower": peakpower_kw,
        "loss": loss_percent,
        "angle": tilt_deg,
        "aspect": azimuth_deg,
        "outputformat": "json",
    }
    resp = requests.get(PVGIS_URL, params=params, timeout=30)
    if resp.status_code != 200:
        raise PVGISError(f"PVGIS error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        return float(data["outputs"]["totals"]["fixed"]["E_y"])
    except KeyError as e:
        raise PVGISError(f"Missing E_y in PVGIS response: {e}")

def estimate_potential(lat, lon, area_m2,
                       fill_factor=FILL_FACTOR,
                       wp_per_m2=WP_PER_M2,
                       tilt_deg=DEFAULT_TILT,
                       azimuth_deg=DEFAULT_AZIMUTH,
                       loss_percent=DEFAULT_LOSS,
                       co2_kg_per_kwh=CO2_KG_PER_KWH):
    if area_m2 <= 0:
        raise ValueError("area_m2 must be positive")
    specific_yield = get_pvgis_specific_yield(
        lat, lon,
        peakpower_kw=1.0,
        tilt_deg=tilt_deg,
        azimuth_deg=azimuth_deg,
        loss_percent=loss_percent,
    )
    usable_panel_area = area_m2 * fill_factor
    kwp = usable_panel_area * wp_per_m2 / 1000.0
    kwh_year = kwp * specific_yield
    co2_tons = kwh_year * co2_kg_per_kwh / 1000.0
    return {
        "roof_area_m2": float(area_m2),
        "usable_panel_area_m2": float(usable_panel_area),
        "kwp": float(kwp),
        "specific_yield_kwh_per_kwp": float(specific_yield),
        "kwh_year": float(kwh_year),
        "co2_tons": float(co2_tons),
    }
