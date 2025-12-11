import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pyproj import Transformer
import os

st.set_page_config(layout="wide", page_title="Top 200 Analysis", page_icon="🎯")

# --- 1. 数据加载逻辑 (Hang's Data) ---
@st.cache_data
def load_hang_data():
    # 更新：直接指向存在的 large_roofs_test.gpkg 文件
    # 我们假设这个文件包含了所有的候选屋顶
    data_path = "notebooks/data/large_roofs_test.gpkg"
    
    df_main = pd.DataFrame()
    df_bg = pd.DataFrame()

    try:
        if not os.path.exists(data_path):
            # 尝试找一下 GeoJSON 作为备选
            data_path = "notebooks/data/large_roofs_test.geojson"
            if not os.path.exists(data_path):
                st.error(f"❌ Critical Error: Could not find data file at `{data_path}`")
                return pd.DataFrame(), pd.DataFrame()

        # 加载数据
        gdf = gpd.read_file(data_path)
        
        # 检查必要的列是否存在，防止报错
        if 'roof_type' not in gdf.columns: 
            gdf['roof_type'] = 'Unknown'
        if 'ai_confidence' not in gdf.columns: 
            gdf['ai_confidence'] = 0.0

        # 坐标转换 & 重命名 (适配之前的逻辑)
        # 你的 notebook 生成的列名可能是 'area_m2', 'co2_tons', 'src_id'
        # 我们这里做一个安全的重命名
        rename_map = {
            'area_m2': 'area', 
            'co2_tons': 'co2', 
            'src_id': 'name',
            'oppervlakte': 'area' # 以防万一使用荷兰语列名
        }
        gdf = gdf.rename(columns=rename_map)
        
        # 确保有 co2 列 (如果没有，基于面积简单估算用于排序)
        if 'co2' not in gdf.columns and 'area' in gdf.columns:
            gdf['co2'] = gdf['area'] * 0.2 * 0.9 * 0.23 / 1000 # 简单的 fallback 计算

        # 处理几何和坐标
        # 计算 WGS84 坐标用于标记 (Markers)
        # 如果原始 CRS 不是 4326 (通常是 31370)，先转换重心
        if gdf.crs and gdf.crs.to_epsg() != 4326:
             # 先保留原始投影计算重心（更准）
            gdf['c_x'] = gdf.geometry.centroid.x
            gdf['c_y'] = gdf.geometry.centroid.y
            transformer = Transformer.from_crs(gdf.crs, "EPSG:4326", always_xy=True)
            gdf['lon'], gdf['lat'] = transformer.transform(gdf['c_x'].values, gdf['c_y'].values)
            # 然后转换几何本身
            gdf = gdf.to_crs(4326)
        else:
            # 已经是 4326
            gdf['lon'] = gdf.geometry.centroid.x
            gdf['lat'] = gdf.geometry.centroid.y

        gdf['lat_lon'] = list(zip(gdf['lat'], gdf['lon']))
        
        if 'area' in gdf.columns:
            gdf['area'] = gdf['area'].astype(int)

        # --- 拆分数据 ---
        # 1. 背景层 (Candidates): 所有的屋顶
        df_bg = gdf.copy()
        
        # 2. 前景层 (Top 200): 按 CO2 排序取前 200
        if 'co2' in gdf.columns:
            df_main = gdf.sort_values(by='co2', ascending=False).head(200)
        else:
            df_main = gdf.head(200)

    except Exception as e:
        st.error(f"Data loading error: {e}")
        st.info("💡 Tip: Ensure `large_roofs_test.gpkg` exists in `notebooks/data/`")
    
    return df_main, df_bg

# --- 2. 地图绘制 ---
def get_hang_map(gdf_bg, gdf_main):
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=13, tiles="CartoDB positron")
    
    # 红色背景层 (所有候选)
    if not gdf_bg.empty:
        folium.GeoJson(
            gdf_bg.geometry, 
            name="All Large Roofs",
            style_function=lambda x: {'color': '#ef4444', 'weight': 1, 'opacity': 0.3, 'fillOpacity': 0.1},
            show=False # 默认隐藏背景层，避免太乱
        ).add_to(m)

    # 蓝色 Top 200 层 (高优先级)
    if not gdf_main.empty:
        folium.GeoJson(
            gdf_main.geometry,
            name="Top 200 Candidates",
            style_function=lambda x: {'color': '#3b82f6', 'weight': 2, 'fillOpacity': 0.4}
        ).add_to(m)
        
        # 绿色交互标记
        for _, row in gdf_main.iterrows():
            badge_color = "#dcfce7" if row.get('roof_type') == 'Flat' else "#fee2e2" if row.get('roof_type') == 'Pitched' else "#f3f4f6"
            
            # 安全获取值
            r_name = row.get('name', 'Unknown')
            r_rank = row.get('rank', 'N/A')
            r_area = row.get('area', 0)
            r_co2 = row.get('co2', 0)
            
            popup_html = f"""
            <div style="font-family:sans-serif; width:180px;">
                <div style="background:{badge_color}; padding:2px 5px; border-radius:3px; display:inline-block; font-size:0.8em; font-weight:bold;">{row.get('roof_type', 'Unknown')}</div>
                <b>#{r_rank} {r_name}</b><br>
                Area: {r_area:,} m²<br>
                CO₂: {r_co2:.1f} t/yr
            </div>
            """
            folium.Marker(
                location=row['lat_lon'],
                tooltip=f"#{r_rank} {r_name}",
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color="green", icon="star", prefix="fa")
            ).add_to(m)
            
    folium.LayerControl().add_to(m)
    return m

# --- 3. 页面布局 ---
st.title("🎯 Top 200 Priority Roofs")
st.caption("Based on Hang's WFS Analysis (Data Source: `large_roofs_test.gpkg`)")

df_top, df_candidates = load_hang_data()

if df_top.empty:
    st.error("Could not load data. Please check file paths.")
    st.stop()

# 侧边栏
with st.sidebar:
    st.header("🔍 Filters")
    # 动态获取面积最大值，如果数据为空或为0则给默认值5000
    # 防止 Slider min_value (0) == max_value (0) 的崩溃
    calculated_max = int(df_top.area.max()) if 'area' in df_top.columns and not df_top.empty else 0
    max_area = max(calculated_max, 500)
    
    # 调试信息：显示数据范围
    st.info(f"Loaded {len(df_top)} roofs. Max Area: {max_area} m²")
    
    # 修改：默认值改为 0，确保测试数据能显示
    min_area = st.slider("Min Area (m²)", 0, max_area, 0)
    flat_only = st.checkbox("Show Flat Roofs Only (AI)", value=False)

# 过滤
filtered = df_top.copy()
if 'area' in filtered.columns:
    filtered = filtered[filtered.area >= min_area]

if flat_only and 'roof_type' in filtered.columns:
    filtered = filtered[filtered.roof_type == 'Flat']

# 显示
c1, c2 = st.columns([3, 2])
with c1:
    st_folium(get_hang_map(df_candidates, filtered), height=600, width="100%")
with c2:
    st.subheader(f"Building List ({len(filtered)})") # 显示过滤后的数量
    
    # 准备显示的列
    cols_to_show = ['name', 'area', 'co2']
    if 'rank' in filtered.columns: cols_to_show.insert(0, 'rank')
    if 'roof_type' in filtered.columns: cols_to_show.append('roof_type')
    if 'ai_confidence' in filtered.columns: cols_to_show.append('ai_confidence')
    
    st.dataframe(
        filtered[cols_to_show],
        column_config={
            "ai_confidence": st.column_config.ProgressColumn("Conf.", format="%.2f"),
            "area": st.column_config.NumberColumn("Area (m²)", format="%d"),
            "co2": st.column_config.NumberColumn("CO₂ (t)", format="%.1f")
        },
        height=600,
        use_container_width=True
    )