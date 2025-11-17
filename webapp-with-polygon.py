import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import geopandas as gpd  # <-- 用于读取 GeoPackage 文件
from pyproj import Transformer # <-- 用于坐标转换

# --- 状态管理 (移至顶部) ---
# 1. 用于地图点击
if 'selected_rooftop_name' not in st.session_state:
    st.session_state.selected_rooftop_name = None
# 2. 用于过滤器
if 'min_area' not in st.session_state:
    st.session_state.min_area = 0

# --- 缓存的数据加载函数 (已更新) ---
@st.cache_data
def load_data():
    """
    从 notebook 生成的 GeoPackage 文件加载 *两个* GDF 并进行处理。
    返回: (df_top200, df_candidates)
    """
    top200_file = "notebooks/data_leuven/leuven_top200_roofs.gpkg"
    candidates_file = "notebooks/data_leuven/leuven_large_roofs.gpkg"
    
    try:
        # 1. 加载 Top 200 数据 (我们的主要数据)
        df_top200 = gpd.read_file(top200_file)
        
        # 2. 加载所有 Candidates (用于红色背景图层)
        df_candidates = gpd.read_file(candidates_file)
        
    except Exception as e:
        st.error(f"**错误：** 找不到数据文件。")
        st.error(f"请确保 `osm_experiments_Hang.ipynb` 已经成功运行，并且 `data_leuven` 文件夹中同时包含 `{top200_file}` 和 `{candidates_file}`。")
        st.error(f"**你可能还需要在你的环境中运行：** `pip install geopandas pyproj`")
        st.error(f"错误详情: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # --- 3. 处理 Top 200 (主要数据) ---
    df_top200 = df_top200.rename(columns={
        'area_m2': 'area', 
        'co2_tons': 'co2',
        'src_id': 'name' 
    })
    df_top200['centroid_x_31370'] = df_top200.geometry.centroid.x
    df_top200['centroid_y_31370'] = df_top200.geometry.centroid.y
    
    transformer = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)
    df_top200['lon'], df_top200['lat'] = transformer.transform(df_top200['centroid_x_31370'].values, df_top200['centroid_y_31370'].values)
    df_top200['lat_lon'] = list(zip(df_top200['lat'], df_top200['lon']))
    df_top200 = df_top200.to_crs(4326) # 转换主几何
    df_top200['area'] = df_top200['area'].astype(int)
    
    # --- 4. 处理 Candidates (背景图层) ---
    df_candidates = df_candidates.to_crs(4326) # 只需要转换几何
    
    return df_top200, df_candidates

# --- 动态地图生成函数 (已更新) ---
# @st.cache_data # <-- 移除缓存，以便地图可以随过滤器动态更新
def get_map(gdf_candidates, gdf_filtered):
    """
    创建 Folium 地图。
    1. 绘制所有大屋顶 *形状* (红色)。
    2. 绘制过滤后的 Top 200 *形状* (蓝色)。
    3. 绘制过滤后的 Top 200 *标记* (绿色)。
    """
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=12, tiles="CartoDB positron")

    # --- 1. 绘制所有大屋顶 (红色) ---
    if not gdf_candidates.empty:
        folium.GeoJson(
            data=gdf_candidates.geometry,
            name="All Large Roofs (>500 m²)",
            style_function=lambda f: {"color": "red", "weight": 1, "fillOpacity": 0.35, "fillColor": "red"},
            show=False # 默认关闭，使其不那么杂乱
        ).add_to(m)

    # --- 2. 绘制过滤后的 Top 200 (蓝色) ---
    if not gdf_filtered.empty:
        folium.GeoJson(
            data=gdf_filtered.geometry,
            name="Top 200 (Filtered)",
            style_function=lambda f: {"color": "blue", "weight": 2, "fillOpacity": 0.5, "fillColor": "blue"}
        ).add_to(m)

        # --- 3. 绘制可点击的标记 (绿色) ---
        # 我们仍然需要标记，因为 st_folium 的点击交互
        # 在处理单个标记时比处理大型 GeoJson 图层更可靠
        for index, row in gdf_filtered.iterrows():
            popup_html = f"""
            <div style="font-family: sans-serif; width: 200px;">
                <h4 style="margin: 0 0 5px 0; color: #15803d;">#{row['rank']}: {row['name']}</h4>
                <p style="margin: 2px 0;"><strong>Usable Area:</strong> {row['area']:,} m²</p>
                <p style="margin: 2px 0;"><strong>Est. CO₂ Reduction:</strong> {row['co2']:,.2f} tons/yr</p>
            </div>
            """
            
            folium.Marker(
                location=row['lat_lon'],
                tooltip=row['name'], # Tooltip 是地图点击交互的关键
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="green", icon="solar-panel", prefix="fa")
            ).add_to(m)
        
    folium.LayerControl().add_to(m) # <-- 新增：添加图层控制器
    return m

# --- Streamlit 应用配置 ---
st.set_page_config(layout="wide", page_title="Leuven 2030 Solar Rooftop Potential Analyzer", page_icon="☀️")
st.title("☀️ Leuven Rooftop Solar Potential Top 200")
st.markdown("Data-Driven Decision Support Tool - Prioritizing high-impact, high-feasibility large rooftops")

# --- 加载 *完整* GeoDataFrames (从缓存) ---
df_top200, df_candidates = load_data() # df_top200 是我们的主要数据

# 如果数据加载失败（例如文件未找到），则停止执行
if df_top200.empty or df_candidates.empty:
    st.stop()

# --- 侧边栏过滤器 UI ---
st.sidebar.header("Filters")

def reset_area():
    """回调函数，用于将面积重置为 0"""
    st.session_state.min_area = 0

# --- 修复: 双向绑定回调 ---
def sync_area_from_slider():
    st.session_state.min_area = st.session_state.min_area_slider

def sync_area_from_input():
    st.session_state.min_area = st.session_state.min_area_input

# 动态设置滑块的最大值
max_area_val = int(df_top200['area'].max())

st.sidebar.slider(
    "Minimum area (m²):",
    min_value=0, 
    max_value=max_area_val,
    step=100,
    value=st.session_state.min_area,  # 从 "source of truth" 读取 value
    key='min_area_slider',            # 唯一的 key
    on_change=sync_area_from_slider   # on_change 回调
)
st.sidebar.number_input(
    "Or enter area:",
    min_value=0, 
    max_value=max_area_val,
    step=100,
    value=st.session_state.min_area,  # 从 "source of truth" 读取 value
    key='min_area_input',             # 唯一的 key
    on_change=sync_area_from_input,   # on_change 回调
    label_visibility="collapsed"
)
st.sidebar.button("Reset Filter", on_click=reset_area, use_container_width=True)

# --- 数据过滤 ---
# 1. 应用过滤器 (只过滤 Top 200)
df_filtered = df_top200[df_top200['area'] >= st.session_state.min_area].sort_values(by='rank')

# 2. 更新侧边栏计数器
st.sidebar.info(f"Showing {len(df_filtered)} / {len(df_top200)} top sites")

# 3. 检查所选项是否已被过滤掉
if st.session_state.selected_rooftop_name:
    if st.session_state.selected_rooftop_name not in df_filtered['name'].values:
        st.session_state.selected_rooftop_name = None

# --- 主布局 ---
col1, col2 = st.columns([3, 2])

# Map display (first column)
with col1:
    st.subheader("Interactive Map Overview")
    
    # 1. 从 *过滤后的数据* (df_filtered) 和 *所有 candidates* 生成地图
    m = get_map(df_candidates, df_filtered)
    
    # 2. 动态确定地图中心和缩放级别
    leuven_center = [50.8792, 4.7001]
    map_center = leuven_center
    map_zoom = 12
    
    if st.session_state.selected_rooftop_name:
        # 从 *完整* 的 df_top200 中查找坐标
        selected_rows = df_top200[df_top200['name'] == st.session_state.selected_rooftop_name]
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
            map_center = selected_row['lat_lon']
            map_zoom = 16

    # 3. 渲染 Folium 地图
    map_data = st_folium(m, 
                         width='100%', 
                         height=600,
                         center=map_center, # 传递动态中心
                         zoom=map_zoom       # 传递动态缩放
                        )

    # --- 交互逻辑：地图 -> 状态 ---
    # 这将继续由标记的 tooltip 驱动
    if map_data and map_data.get("last_object_clicked_tooltip"):
        clicked_name = map_data["last_object_clicked_tooltip"]
        
        if st.session_state.selected_rooftop_name != clicked_name:
            st.session_state.selected_rooftop_name = clicked_name
            st.rerun() # 立即重新运行以更新右侧面板和地图缩放


# Information panel (second column) - 由 st.session_state 驱动
with col2:
    st.subheader("Rooftop Details")
    
    selected_name = st.session_state.selected_rooftop_name

    if selected_name:
        # 从 *完整* 的 df_top200 中获取数据以显示详情
        selected_rows = df_top200[df_top200['name'] == selected_name]
        if not selected_rows.empty:
            selected_rooftop = selected_rows.iloc[0]
            
            st.markdown(f"### 🎯 #{selected_rooftop['rank']} {selected_rooftop['name']}")
            
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric(label="Usable Area (m²)", value=f"{selected_rooftop['area']:,}")
            with metrics_col2:
                st.metric(label="Est. CO₂ Reduction/yr (tons)", value=f"{selected_rooftop['co2']:,.2f}")
            
            # 移除了 'type' 字段
        else:
            st.session_state.selected_rooftop_name = None
            st.info("🗺️ **Click a marker or adjust filters.**", icon="👆")
    else:
        st.info("🗺️ **Click a green marker on the map** to see details.", icon="👆")

    # --- 列表现在也使用 *过滤后的* 数据 ---
    st.subheader(f"Potential Rooftops List ({len(df_filtered)} shown)")
    
    # 从 df_filtered 中选择列 (移除了 'type' 和 'geometry')
    display_df = df_filtered[['rank', 'name', 'area', 'co2']].sort_values(by='rank')
    
    column_config = {
        'rank': st.column_config.NumberColumn("Rank", format="%d"),
        'name': "Name (src_id)",
        'area': st.column_config.NumberColumn("Usable Area (m²)", format="%,.0f"),
        'co2': st.column_config.NumberColumn("Est. CO₂ Reduction/yr (tons)", format="%,.2f"),
    }
    
    st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        height=450
    )

# Footer
st.markdown("""
---
*This app uses `streamlit-folium` for rich map interactions. Data is loaded from `data_leuven/` folder.*
""")