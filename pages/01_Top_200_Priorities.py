import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pyproj import Transformer
import os

st.set_page_config(layout="wide", page_title="Top 200 Analysis", page_icon="🎯")

# --- 1. 数据加载逻辑 ---
@st.cache_data
def load_hang_data():
    enriched_top200 = "notebooks/data/200_large_with_pv_enriched.gpkg" 
    basic_top200 = "notebooks/data/200_large_with_pv.gpkg"
    candidates_file = "notebooks/data/500_large_with_pv.gpkg"
    
    df_main = pd.DataFrame()
    df_bg = pd.DataFrame()

    try:
        if os.path.exists(enriched_top200):
            df_main = gpd.read_file(enriched_top200)
            if 'roof_type' not in df_main.columns: df_main['roof_type'] = 'Unknown'
            if 'ai_confidence' not in df_main.columns: df_main['ai_confidence'] = 0.0  
        elif os.path.exists(basic_top200):
            df_main = gpd.read_file(basic_top200)
            st.warning("⚠️ Loading raw PVGIS data (No AI classification yet).")
            df_main['roof_type'] = 'Unknown'
            df_main['ai_confidence'] = 0.0
        else:
            st.error(f"❌ Critical: Could not find Top 200 data.")
            return pd.DataFrame(), pd.DataFrame()

        if os.path.exists(candidates_file):
            df_bg = gpd.read_file(candidates_file).to_crs(4326)

        rename_map = {
            'area_m2': 'area', 'src_id': 'name',
            'best_co2_tons_year': 'co2', 'best_layout': 'orientation',
            'best_kwh_year': 'kwh'
        }
        df_main = df_main.rename(columns=rename_map)
        
        if 'orientation' not in df_main.columns: df_main['orientation'] = 'N/A'
        if 'kwh' not in df_main.columns: df_main['kwh'] = 0
        if 'rank' not in df_main.columns:
            df_main = df_main.sort_values(by='co2', ascending=False).reset_index(drop=True)
            df_main['rank'] = df_main.index + 1

        if df_main.crs and df_main.crs.to_epsg() != 4326:
            df_main['c_x'] = df_main.geometry.centroid.x
            df_main['c_y'] = df_main.geometry.centroid.y
            transformer = Transformer.from_crs(df_main.crs, "EPSG:4326", always_xy=True)
            df_main['lon'], df_main['lat'] = transformer.transform(df_main['c_x'].values, df_main['c_y'].values)
            df_main = df_main.to_crs(4326)
        else:
            df_main['lon'] = df_main.geometry.centroid.x
            df_main['lat'] = df_main.geometry.centroid.y

        df_main['lat_lon'] = list(zip(df_main['lat'], df_main['lon']))
        if 'area' in df_main.columns: df_main['area'] = df_main['area'].astype(int)

    except Exception as e:
        st.error(f"Data processing error: {e}")
    
    return df_main, df_bg

# --- 2. 地图绘制 ---
def get_hang_map(gdf_bg, gdf_main):
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=13, tiles="CartoDB positron")
    
    if not gdf_bg.empty:
        folium.GeoJson(
            gdf_bg.geometry, 
            name="500 Largest Roofs",
            style_function=lambda x: {'color': '#ef4444', 'weight': 1, 'opacity': 0.3, 'fillOpacity': 0.1},
            show=False
        ).add_to(m)

    if not gdf_main.empty:
        folium.GeoJson(
            gdf_main.geometry,
            name="Top 200 (PVGIS Analyzed)",
            style_function=lambda x: {'color': '#3b82f6', 'weight': 2, 'fillOpacity': 0.5}
        ).add_to(m)
        
        for _, row in gdf_main.iterrows():
            rtype = row.get('roof_type', 'Unknown')
            ori = row.get('orientation', 'N/A')
            badge_color = "#dcfce7" if rtype == 'Flat' else "#fee2e2" if rtype == 'Pitched' else "#f3f4f6"
            ori_display = str(ori).replace("_", "-").title()
            ori_badge = f"<span style='background-color:#e0f2fe; color:#0369a1; padding:1px 4px; border-radius:3px; margin-left:4px; font-size:0.7em;'>{ori_display}</span>"

            popup_html = f"""
            <div style="font-family:sans-serif; width:220px;">
                <div style="margin-bottom:5px;">
                    <span style="background:{badge_color}; padding:2px 5px; border-radius:3px; font-size:0.8em; font-weight:bold;">{rtype}</span>
                    {ori_badge}
                </div>
                <b>#{row.get('rank', '')} {row.get('name', 'Unknown')}</b><br>
                <hr style="margin:5px 0;">
                Area: {row.get('area', 0):,} m²<br>
                <b>CO₂ Savings: {row.get('co2', 0):.1f} t/yr</b><br>
                <span style="color:#666;">Energy: {row.get('kwh', 0):,.0f} kWh/yr</span>
            </div>
            """
            folium.Marker(
                location=row['lat_lon'],
                tooltip=f"#{row.get('rank', '')} {row.get('name', '')}",
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color="green", icon="star", prefix="fa")
            ).add_to(m)
            
    folium.LayerControl().add_to(m)
    return m

# --- 3. 页面逻辑 ---
st.title("🎯 Top 200 Priority Roofs (PVGIS Integrated)")
st.caption("Data Source: PVGIS Estimates (Ha Van) + AI Classification (Antonio)")

df_top, df_candidates = load_hang_data()

if df_top.empty:
    st.stop()

# --- 侧边栏 ---
with st.sidebar:
    st.header("🔍 Filters")
    calc_max = int(df_top.area.max()) if 'area' in df_top.columns and not df_top.empty else 0
    max_area = calc_max if calc_max > 0 else 5000
    min_area = st.slider("Min Area (m²)", 0, max_area, 0)
    
    has_ai = 'Flat' in df_top['roof_type'].values
    flat_only = st.checkbox("Show Flat Roofs Only (AI)", value=False, disabled=not has_ai)

    selected_ori = []
    if 'orientation' in df_top.columns:
        valid_oris = [x for x in df_top['orientation'].unique() if pd.notna(x)]
        if valid_oris:
            selected_ori = st.multiselect("Best Orientation", valid_oris, default=valid_oris)

# --- 过滤数据 ---
filtered = df_top.copy()
if 'area' in filtered.columns:
    filtered = filtered[filtered.area >= min_area]
if flat_only:
    filtered = filtered[filtered.roof_type == 'Flat']
if selected_ori and 'orientation' in filtered.columns:
    filtered = filtered[filtered['orientation'].isin(selected_ori)]

filtered = filtered.sort_values(by='rank').reset_index(drop=True)

# --- 布局与交互 (修复不灵敏问题) ---
c1, c2 = st.columns([3, 2])

# [关键修复]: 先在代码中定义默认地图参数
map_center = [50.8792, 4.7001]
map_zoom = 13

# [关键修复]: 优先渲染右侧表格（逻辑上），捕获点击事件
with c2:
    st.subheader(f"Building List ({len(filtered)})")
    
    cols = ['rank', 'name', 'area', 'co2', 'kwh', 'orientation', 'roof_type']
    cols = [c for c in cols if c in filtered.columns]
    
    # 渲染表格并捕获事件
    event = st.dataframe(
        filtered[cols],
        column_config={
            "area": st.column_config.NumberColumn("Area", format="%d m²"),
            "co2": st.column_config.NumberColumn("CO₂", format="%.1f t"),
            "kwh": st.column_config.NumberColumn("Energy", format="%,.0f kWh"),
            "roof_type": "Type",
            "orientation": "Ori."
        },
        height=600,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="building_table"
    )
    
    # [关键修复]: 立即处理点击，更新本次运行的地图参数
    if len(event.selection.rows) > 0:
        idx = event.selection.rows[0]
        if idx < len(filtered):
            selected_row = filtered.iloc[idx]
            map_center = selected_row['lat_lon']
            map_zoom = 18

# [关键修复]: 最后渲染左侧地图，此时 map_center 已经是更新后的了
with c1:
    st.subheader("Interactive Map") # 新增：添加标题以对齐右侧表格
    st_folium(
        get_hang_map(df_candidates, filtered), 
        height=600, 
        width="100%",
        center=map_center, # 这里用的是刚刚从表格点击里更新出的坐标
        zoom=map_zoom,
        key="folium_map"
    )