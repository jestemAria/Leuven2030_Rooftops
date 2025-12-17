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
    meta_csv = "notebooks/data/500_large_with_pv_geocoded.csv"
    candidates_file = "notebooks/data/500_large_with_pv.gpkg"
    
    df_main = pd.DataFrame()
    df_bg = pd.DataFrame()

    try:
        # A. 加载主数据
        if os.path.exists(enriched_top200):
            df_main = gpd.read_file(enriched_top200)
            if 'roof_type' not in df_main.columns: df_main['roof_type'] = 'Unknown'
            if 'ai_confidence' not in df_main.columns: df_main['ai_confidence'] = 0.0  
        elif os.path.exists(basic_top200):
            df_main = gpd.read_file(basic_top200)
            st.warning("⚠️ Using raw data (Run AI script to see roof types)")
            df_main['roof_type'] = 'Unknown'
            df_main['ai_confidence'] = 0.0
        else:
            st.error("❌ Critical: Top 200 data file not found.")
            return pd.DataFrame(), pd.DataFrame()

        # B. 加载背景
        if os.path.exists(candidates_file):
            df_bg = gpd.read_file(candidates_file).to_crs(4326)

        # C. 合并 CSV 元数据
        if os.path.exists(meta_csv):
            try:
                df_meta = pd.read_csv(meta_csv)
                df_main['src_id'] = df_main['src_id'].astype(str)
                df_meta['src_id'] = df_meta['src_id'].astype(str)
                
                cols_to_merge = ['src_id']
                if 'address' in df_meta.columns: cols_to_merge.append('address')
                if 'type of building' in df_meta.columns: cols_to_merge.append('type of building')
                
                df_main = df_main.merge(df_meta[cols_to_merge], on='src_id', how='left')
            except Exception as e:
                st.warning(f"Metadata merge failed: {e}")
        
        # D. 清洗与重命名
        rename_map = {
            'area_m2': 'area', 'src_id': 'name',
            'best_co2_tons_year': 'co2', 'best_layout': 'orientation',
            'best_kwh_year': 'kwh',
            'type of building': 'building_type'
        }
        df_main = df_main.rename(columns=rename_map)
        
        # E. 填充缺失值 & 类型转换 (关键修复)
        if 'orientation' not in df_main.columns: df_main['orientation'] = 'Unknown'
        df_main['orientation'] = df_main['orientation'].fillna('Unknown')
        
        if 'building_type' not in df_main.columns: df_main['building_type'] = 'Unknown'
        df_main['building_type'] = df_main['building_type'].fillna('Unknown')
        
        if 'address' not in df_main.columns: df_main['address'] = 'Unknown'
        df_main['address'] = df_main['address'].fillna('Unknown')

        # 强制转换面积为数值，防止字符串导致过滤失效
        if 'area' in df_main.columns:
            df_main['area'] = pd.to_numeric(df_main['area'], errors='coerce').fillna(0).astype(int)

        # 排序
        if 'rank' not in df_main.columns:
            # 确保 co2 也是数值
            if 'co2' in df_main.columns:
                df_main['co2'] = pd.to_numeric(df_main['co2'], errors='coerce').fillna(0)
                df_main = df_main.sort_values(by='co2', ascending=False).reset_index(drop=True)
            df_main['rank'] = df_main.index + 1

        # F. 坐标转换
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

    except Exception as e:
        st.error(f"Data Processing Error: {e}")
    
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
            name="Top 200 Candidates",
            style_function=lambda x: {'color': '#3b82f6', 'weight': 2, 'fillOpacity': 0.5}
        ).add_to(m)
        
        for _, row in gdf_main.iterrows():
            rtype = row.get('roof_type', 'Unknown')
            btype = row.get('building_type', 'Unknown')
            ori = row.get('orientation', 'Unknown')
            addr = str(row.get('address', '')).replace(", Belgium", "")
            
            badge_color = "#dcfce7" if rtype == 'Flat' else "#fee2e2" if rtype == 'Pitched' else "#f3f4f6"
            ori_display = str(ori).replace("_", "-").title()
            
            # Popup 中的 AI Confidence
            conf_val = row.get('ai_confidence', 0.0)
            conf_str = f"({conf_val:.0%})" if conf_val > 0 else ""

            popup_html = f"""
            <div style="font-family:sans-serif; width:250px;">
                <div style="margin-bottom:5px;">
                    <span style="background:{badge_color}; padding:2px 5px; border-radius:3px; font-size:0.8em; font-weight:bold;">{rtype} {conf_str}</span>
                    <span style="background:#e0f2fe; color:#0369a1; padding:2px 5px; border-radius:3px; font-size:0.8em; margin-left:4px;">{ori_display}</span>
                </div>
                <div style="font-size:1.1em; font-weight:bold; margin-bottom:2px;">#{row.get('rank', '')} {row.get('name', 'Unknown')}</div>
                <div style="font-size:0.85em; color:#666; margin-bottom:8px;">📍 {addr}</div>
                
                <div style="background:#f9fafb; padding:8px; border-radius:4px; font-size:0.9em;">
                    <div style="display:flex; justify-content:space-between;"><span>Type:</span> <b>{btype}</b></div>
                    <div style="display:flex; justify-content:space-between;"><span>Area:</span> <b>{row.get('area', 0):,} m²</b></div>
                    <div style="display:flex; justify-content:space-between;"><span>Energy:</span> <b>{row.get('kwh', 0):,.0f} kWh</b></div>
                    <div style="margin-top:4px; border-top:1px solid #ddd; padding-top:4px; font-weight:bold; color:#15803d; display:flex; justify-content:space-between;">
                        <span>CO₂ Savings:</span> <span>{row.get('co2', 0):.1f} t/yr</span>
                    </div>
                </div>
            </div>
            """
            folium.Marker(
                location=row['lat_lon'],
                tooltip=f"#{row.get('rank', '')} {addr[:30]}...",
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="green", icon="star", prefix="fa")
            ).add_to(m)
            
    folium.LayerControl().add_to(m)
    return m

# --- 3. 页面逻辑 ---
st.title("🎯 Top 200 Priority Roofs")

df_top, df_candidates = load_hang_data()

if df_top.empty:
    st.stop()

# --- 侧边栏 ---
with st.sidebar:
    st.header("🔍 Filters")
    
    # 1. 面积过滤器 (修复: 增加数字输入，确保最大值正确)
    max_val = int(df_top.area.max()) if not df_top.empty else 5000
    if max_val < 500: max_val = 5000
    
    # 使用 session state 同步 slider 和 number input
    if 'min_area_val' not in st.session_state:
        st.session_state.min_area_val = 0
        
    def update_slider(): st.session_state.min_area_val = st.session_state.slider_key
    def update_input(): st.session_state.min_area_val = st.session_state.input_key
    
    st.slider("Min Area (m²)", 0, max_val, key='slider_key', value=st.session_state.min_area_val, on_change=update_slider)
    st.number_input("Enter exact area:", 0, max_val, key='input_key', value=st.session_state.min_area_val, on_change=update_input)
    min_area = st.session_state.min_area_val

    # 2. 建筑类型过滤器 (修复: 默认全选/不选即全选)
    all_btypes = sorted(list(df_top['building_type'].unique()))
    # 默认不选，逻辑上视为"All"
    selected_btypes = st.multiselect("Building Type", all_btypes, default=[], placeholder="All types (select to filter)")
    
    # 3. AI 屋顶类型
    has_ai = 'Flat' in df_top['roof_type'].values
    flat_only = st.checkbox("Show Flat Roofs Only (AI)", value=False, disabled=not has_ai)

    # 4. 朝向过滤器
    all_oris = sorted(list(df_top['orientation'].unique()))
    selected_ori = st.multiselect("Best Orientation", all_oris, default=[])

# --- 过滤逻辑 ---
filtered = df_top.copy()

# A. 面积 (确保类型匹配)
filtered = filtered[filtered['area'] >= min_area]

# B. 建筑类型 (关键修复: 如果 selected_btypes 为空，则不进行过滤，即显示所有)
if selected_btypes:
    filtered = filtered[filtered['building_type'].isin(selected_btypes)]

# C. AI Flat
if flat_only:
    filtered = filtered[filtered.roof_type == 'Flat']

# D. 朝向 (同样，为空则不从过滤)
if selected_ori:
    filtered = filtered[filtered['orientation'].isin(selected_ori)]

filtered = filtered.sort_values(by='rank').reset_index(drop=True)

# --- 选中逻辑 ---
map_center = [50.8792, 4.7001]
map_zoom = 13

if 'selected_row_index' in st.session_state and st.session_state.selected_row_index is not None:
    idx = st.session_state.selected_row_index
    if idx < len(filtered):
        try:
            sel = filtered.iloc[idx]
            map_center = sel['lat_lon']
            map_zoom = 18 
            st.toast(f"📍 Selected: {sel['address']}", icon="🏢")
        except: pass
    else:
        st.session_state.selected_row_index = None

# --- 布局 ---
c1, c2 = st.columns([3, 2])

# 先渲染表格以捕获点击
with c2:
    st.subheader(f"Building List ({len(filtered)})")
    
    if filtered.empty:
        st.warning("No buildings match your filters.")
        st.info("Try resetting the filters or lowering the Min Area.")
    else:
        # 显示列配置 (修复: 加回 ai_confidence)
        cols = ['rank', 'address', 'building_type', 'area', 'co2', 'roof_type']
        if 'ai_confidence' in filtered.columns:
            cols.append('ai_confidence')
        
        cols = [c for c in cols if c in filtered.columns]
        
        event = st.dataframe(
            filtered[cols],
            column_config={
                "address": st.column_config.TextColumn("Address", width="medium"),
                "building_type": "Type",
                "area": st.column_config.NumberColumn("Area", format="%d m²"),
                "co2": st.column_config.NumberColumn("CO₂", format="%.1f t"),
                "roof_type": "Roof",
                "ai_confidence": st.column_config.ProgressColumn("Conf.", format="%.2f", min_value=0, max_value=1)
            },
            height=600,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="building_table"
        )
        
        if len(event.selection.rows) > 0:
            st.session_state.selected_row_index = event.selection.rows[0]
        else:
            st.session_state.selected_row_index = None

with c1:
    st.subheader("Interactive Map")
    st_folium(
        get_hang_map(df_candidates, filtered), 
        height=600, 
        width="100%",
        center=map_center,
        zoom=map_zoom,
        key="folium_map"
    )