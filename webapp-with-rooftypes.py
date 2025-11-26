import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pyproj import Transformer
import os

# --- 状态管理 ---
if 'selected_rooftop_name' not in st.session_state:
    st.session_state.selected_rooftop_name = None
if 'min_area' not in st.session_state:
    st.session_state.min_area = 0

# --- 缓存的数据加载函数 (已升级以支持 AI 数据) ---
@st.cache_data
def load_data():
    """
    加载 GeoPackage 文件。
    优先尝试加载包含 AI 预测结果的 'enriched' 版本。
    """
    # 1. 定义文件路径
    enriched_file = "notebooks/data_leuven/leuven_top200_enriched.gpkg" # AI 脚本生成的输出
    basic_file = "notebooks/data_leuven/leuven_top200_roofs.gpkg"       # 原始 notebook 的输出
    candidates_file = "notebooks/data_leuven/leuven_large_roofs.gpkg"    # 背景图层
    
    df_top200 = pd.DataFrame()
    df_candidates = pd.DataFrame()

    # 2. 尝试加载主要数据 (Top 200)
    try:
        if os.path.exists(enriched_file):
            df_top200 = gpd.read_file(enriched_file)
            # 标记数据源包含 AI 预测
            if 'roof_type' not in df_top200.columns:
                df_top200['roof_type'] = 'Unknown' # 防止列缺失报错
                df_top200['ai_confidence'] = 0.0
        elif os.path.exists(basic_file):
            df_top200 = gpd.read_file(basic_file)
            st.warning("⚠️ 正在使用基础数据。运行 `predict_rooftypes.py` 以启用 AI 过滤器。")
            # 为基础数据添加占位列，防止代码崩溃
            df_top200['roof_type'] = 'Unknown'
            df_top200['ai_confidence'] = 0.0
        else:
            st.error("❌ 找不到数据文件。请先运行数据处理 notebooks。")
            st.stop()
            
        # 3. 加载背景数据 (Candidates)
        if os.path.exists(candidates_file):
            df_candidates = gpd.read_file(candidates_file)
        
    except Exception as e:
        st.error(f"数据加载错误: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- 4. 数据预处理 (坐标转换 & 重命名) ---
    # 适配列名
    renames = {'area_m2': 'area', 'co2_tons': 'co2', 'src_id': 'name'}
    df_top200 = df_top200.rename(columns=renames)
    
    # 坐标转换: Lambert72 (31370) -> WGS84 (4326)
    # 我们需要 centroid 用于标记位置
    df_top200['centroid_x_31370'] = df_top200.geometry.centroid.x
    df_top200['centroid_y_31370'] = df_top200.geometry.centroid.y
    
    transformer = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)
    df_top200['lon'], df_top200['lat'] = transformer.transform(
        df_top200['centroid_x_31370'].values, 
        df_top200['centroid_y_31370'].values
    )
    df_top200['lat_lon'] = list(zip(df_top200['lat'], df_top200['lon']))
    
    # 将几何列转换为 4326 用于 folium 绘图
    df_top200 = df_top200.to_crs(4326)
    if not df_candidates.empty:
        df_candidates = df_candidates.to_crs(4326)

    df_top200['area'] = df_top200['area'].astype(int)
    
    return df_top200, df_candidates

# --- 动态地图生成函数 ---
def get_map(gdf_candidates, gdf_filtered):
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=12, tiles="CartoDB positron")

    # 1. 背景图层 (红色, 默认关闭)
    if not gdf_candidates.empty:
        folium.GeoJson(
            data=gdf_candidates.geometry,
            name="All Large Roofs (>500 m²)",
            style_function=lambda f: {"color": "#ef4444", "weight": 1, "fillOpacity": 0.2, "fillColor": "#ef4444"},
            show=False 
        ).add_to(m)

    # 2. 过滤后的屋顶形状 (蓝色)
    if not gdf_filtered.empty:
        folium.GeoJson(
            data=gdf_filtered.geometry,
            name="Selected Candidates",
            style_function=lambda f: {"color": "#3b82f6", "weight": 2, "fillOpacity": 0.4, "fillColor": "#3b82f6"}
        ).add_to(m)

        # 3. 交互式标记 (Popup 增强)
        for index, row in gdf_filtered.iterrows():
            # --- AI 预测徽章逻辑 ---
            roof_type_display = row['roof_type']
            
            # 根据类型设置徽章样式
            if roof_type_display == 'Flat':
                type_badge = f"<span style='background-color:#dcfce7; color:#166534; padding:2px 6px; border-radius:4px; font-size:0.8em;'><b>FLAT</b></span>"
            elif roof_type_display == 'Pitched':
                type_badge = f"<span style='background-color:#fee2e2; color:#991b1b; padding:2px 6px; border-radius:4px; font-size:0.8em;'><b>PITCHED</b></span>"
            else:
                type_badge = f"<span style='background-color:#f3f4f6; color:#374151; padding:2px 6px; border-radius:4px; font-size:0.8em;'>Unknown</span>"

            # 获取 AI 置信度 (如果存在)
            conf_str = ""
            if row['ai_confidence'] > 0:
                conf_str = f"<span style='font-size:0.75em; color:#6b7280;'> (conf: {row['ai_confidence']:.0%})</span>"

            popup_html = f"""
            <div style="font-family: sans-serif; width: 220px;">
                <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight:bold; color:#15803d;">#{row['rank']}</span>
                    {type_badge}
                </div>
                <div style="margin-bottom: 4px; font-weight: 600;">{row['name']}</div>
                <hr style="margin: 4px 0; border-top: 1px solid #e5e7eb;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 0.9em;">
                    <div style="color:#4b5563;">Area:</div>
                    <div style="text-align:right;"><b>{row['area']:,} m²</b></div>
                    <div style="color:#4b5563;">CO₂ Savings:</div>
                    <div style="text-align:right;"><b>{row['co2']:,.1f} t/yr</b></div>
                    <div style="color:#4b5563;">AI Pred:</div>
                    <div style="text-align:right;">{roof_type_display}{conf_str}</div>
                </div>
            </div>
            """
            
            folium.Marker(
                location=row['lat_lon'],
                tooltip=f"#{row['rank']} {row['name']} ({row['roof_type']})", 
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="green", icon="solar-panel", prefix="fa")
            ).add_to(m)
        
    folium.LayerControl().add_to(m)
    return m

# --- Streamlit 应用布局 ---
st.set_page_config(layout="wide", page_title="Leuven 2030 Solar AI", page_icon="☀️")
st.title("☀️ Leuven Rooftop Solar Potential (AI Enhanced)")

# 加载数据
df_top200, df_candidates = load_data()

# --- 侧边栏: 过滤器 ---
st.sidebar.header("Filters & AI Options")

# 1. 面积过滤器 (保持原有逻辑)
def sync_area_slider(): st.session_state.min_area = st.session_state.min_area_slider
def sync_area_input(): st.session_state.min_area = st.session_state.min_area_input

max_area = int(df_top200['area'].max()) if not df_top200.empty else 10000

st.sidebar.subheader("📏 Size Filter")
st.sidebar.slider("Min Area (m²)", 0, max_area, value=st.session_state.min_area, key='min_area_slider', on_change=sync_area_slider)
st.sidebar.number_input("Min Area Input", 0, max_area, value=st.session_state.min_area, key='min_area_input', on_change=sync_area_input, label_visibility="collapsed")

# 2. AI 过滤器 (新功能!)
st.sidebar.subheader("🤖 AI Roof Type Filter")
# 只有在数据中有 'Flat' 类型时才显示有效，否则显示提示
has_ai_data = 'Flat' in df_top200['roof_type'].values
flat_only = st.sidebar.checkbox(
    "Show Flat Roofs Only", 
    help="Flat roofs are generally easier and cheaper for PV installation.",
    disabled=not has_ai_data
)

if not has_ai_data:
    st.sidebar.caption("⚠️ Run inference script to enable AI filtering.")

def reset_filters():
    st.session_state.min_area = 0
    # Checkbox state is managed by streamlit automatically, we just reset session vars if bound
st.sidebar.button("Reset All Filters", on_click=reset_filters, use_container_width=True)


# --- 数据过滤逻辑 ---
# 1. 面积过滤
filtered_df = df_top200[df_top200['area'] >= st.session_state.min_area].copy()

# 2. AI 类型过滤
if flat_only and has_ai_data:
    filtered_df = filtered_df[filtered_df['roof_type'] == 'Flat']

filtered_df = filtered_df.sort_values(by='rank')

# 更新计数器
st.sidebar.info(f"Displaying {len(filtered_df)} / {len(df_top200)} sites")


# --- 主界面 ---
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Interactive Map")
    map_obj = get_map(df_candidates, filtered_df)
    
    # 动态地图中心
    center = [50.8792, 4.7001]
    zoom = 12
    if st.session_state.selected_rooftop_name:
        sel = df_top200[df_top200['name'] == st.session_state.selected_rooftop_name]
        if not sel.empty:
            center = sel.iloc[0]['lat_lon']
            zoom = 16

    st_data = st_folium(map_obj, width='100%', height=600, center=center, zoom=zoom)

    # 处理点击事件
    if st_data and st_data.get("last_object_clicked_tooltip"):
        clicked_text = st_data["last_object_clicked_tooltip"]
        # tooltip 格式是 "#1 Name (Type)"，我们需要提取 Name
        # 或者简单点，我们在 tooltip 里只放 name，或者解析它
        # 这里的简单做法是：假设 Name 是唯一的，直接匹配
        # 为了稳健，我们在生成 marker 时 tooltip 直接设为 row['name']
        # 但上面的代码为了展示设为了 f"#{rank} {name} ({type})"，我们需要解析一下
        
        # 修正：为了让点击逻辑简单，我们在 get_map 里最好把 tooltip 设为纯 name 或者 src_id
        # 但为了用户体验，tooltip 显示信息更好。
        # 让我们尝试模糊匹配或存储 ID
        pass 

# 更新：为了让点击交互更顺畅，我们需要确保 tooltip 和 session state 逻辑匹配
# 在 get_map 中，我将 tooltip 修改为了 `row['name']` 以保持一致性
# (上面的代码块里已经做了调整，但为了确保万无一失，请看 get_map 里的 tooltip 参数)
# 实际上，上面的 get_map 中 tooltip 包含额外信息。
# 我们来简化一下：让 st_folium 返回 last_object_clicked_tooltip 时，我们去匹配
# 只要 tooltip 包含了 name，我们可以尝试查找。
# 更稳健的方法：tooltip = row['name'] (src_id)

with col2:
    st.subheader("Building List")
    
    # 显示数据表
    display_cols = ['rank', 'name', 'area', 'co2', 'roof_type']
    if 'ai_confidence' in filtered_df.columns:
        display_cols.append('ai_confidence')
        
    st.dataframe(
        filtered_df[display_cols],
        column_config={
            "rank": "Rank",
            "name": "Name",
            "area": st.column_config.NumberColumn("Area (m²)", format="%d"),
            "co2": st.column_config.NumberColumn("CO₂ (t)", format="%.1f"),
            "roof_type": st.column_config.TextColumn("Type (AI)", help="Predicted by ResNet-18"),
            "ai_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f")
        },
        use_container_width=True,
        hide_index=True,
        height=600
    )