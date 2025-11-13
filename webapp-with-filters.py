import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# --- 状态管理 (移至顶部) ---
# 1. 用于地图点击
if 'selected_rooftop_name' not in st.session_state:
    st.session_state.selected_rooftop_name = None
# 2. 用于过滤器
if 'min_area' not in st.session_state:
    st.session_state.min_area = 0

# --- 缓存的数据加载函数 ---
@st.cache_data
def load_data():
    """
    创建并缓存 *完整* 的 DataFrame。
    这个函数只会运行一次。
    """
    mock_rooftops = [
        {'rank': 1, 'name': "AB Inbev", 'area': 56691, 'co2': 3500, 'type': "EPDM", 'lat': 50.8930, 'lng': 4.7081},
        {'rank': 2, 'name': "UZ Gasthuisberg", 'area': 32149, 'co2': 2000, 'type': "Bitumen", 'lat': 50.8841, 'lng': 4.6788},
        {'rank': 3, 'name': "Commscope", 'area': 34308, 'co2': 2100, 'type': "EPDM", 'lat': 50.8870, 'lng': 4.6950},
        {'rank': 4, 'name': "Terumo Europe", 'area': 17971, 'co2': 1100, 'type': "Steel", 'lat': 50.8710, 'lng': 4.7200},
        {'rank': 5, 'name': "Depot Aveve", 'area': 14160, 'co2': 900, 'type': "Bitumen", 'lat': 50.9000, 'lng': 4.6650},
        {'rank': 6, 'name': "Beneo-Remy", 'area': 13190, 'co2': 850, 'type': "EPDM", 'lat': 50.8650, 'lng': 4.7100},
        # ... (其余的 14 个真实数据点)
        {'rank': 7, 'name': "Leuven Centrale Gevangenis", 'area': 10352, 'co2': 650, 'type': "Gravel", 'lat': 50.8720, 'lng': 4.6980},
        {'rank': 8, 'name': "Variapack", 'area': 10673, 'co2': 670, 'type': "EPDM", 'lat': 50.8900, 'lng': 4.6750},
        {'rank': 9, 'name': "TOMRA Food", 'area': 10254, 'co2': 640, 'type': "Steel", 'lat': 50.8855, 'lng': 4.7050},
        {'rank': 10, 'name': "Citydepot/Metaleuven", 'area': 7989, 'co2': 500, 'type': "Bitumen", 'lat': 50.8780, 'lng': 4.7150},
        {'rank': 11, 'name': "Heilig Hart Hospitaal", 'area': 7363, 'co2': 460, 'type': "EPDM", 'lat': 50.8750, 'lng': 4.7000},
        {'rank': 12, 'name': "VWR", 'area': 7218, 'co2': 450, 'type': "Gravel", 'lat': 50.8820, 'lng': 4.7250},
        {'rank': 13, 'name': "Bees Delivery", 'area': 7122, 'co2': 440, 'type': "EPDM", 'lat': 50.8690, 'lng': 4.6850},
        {'rank': 14, 'name': "KBC", 'area': 7531, 'co2': 470, 'type': "Bitumen", 'lat': 50.8755, 'lng': 4.7005},
        {'rank': 15, 'name': "Imec", 'area': 6634, 'co2': 410, 'type': "Steel", 'lat': 50.8655, 'lng': 4.6800},
        {'rank': 16, 'name': "Ecowerf", 'area': 6615, 'co2': 410, 'type': "EPDM", 'lat': 50.8980, 'lng': 4.7150},
        {'rank': 17, 'name': "Symeta Hybrid NV", 'area': 6044, 'co2': 380, 'type': "Bitumen", 'lat': 50.8800, 'lng': 4.6800},
        {'rank': 18, 'name': "Sportoase", 'area': 5534, 'co2': 350, 'type': "EPDM", 'lat': 50.8740, 'lng': 4.7090},
        {'rank': 19, 'name': "Yamazaki Mazak Europe", 'area': 6802, 'co2': 420, 'type': "Steel", 'lat': 50.8810, 'lng': 4.6900},
        {'rank': 20, 'name': "UCLL", 'area': 4957, 'co2': 310, 'type': "Gravel", 'lat': 50.8760, 'lng': 4.7200},
    ]

    # ... (模拟其余数据)
    for i in range(21, 201):
        mock_rooftops.append({
            'rank': i,
            'name': f"Other Large Site {i}",
            'area': np.random.randint(500, 4500),
            'co2': np.random.randint(30, 250),
            'type': np.random.choice(["Slate", "EPDM", "Tile"]),
            'lat': 50.85 + np.random.rand() * 0.1,
            'lng': 4.65 + np.random.rand() * 0.15,
        })

    df = pd.DataFrame(mock_rooftops)
    df = df.rename(columns={'lng': 'lon'})
    df['lat_lon'] = list(zip(df['lat'], df['lon']))
    return df

# --- 动态地图生成函数 ---
# @st.cache_data # <-- 关键改动：移除缓存！
# 移除缓存才能让地图在过滤器更改时重新生成
def get_map(_dataframe):
    """
    创建 Folium 地图并 *只为过滤后的数据* 添加标记。
    这个函数现在会在每次过滤器更改时重新运行。
    """
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=12, tiles="CartoDB positron")

    # 只遍历传入的 (可能已过滤的) _dataframe
    for index, row in _dataframe.iterrows():
        popup_html = f"""
        <div style="font-family: sans-serif; width: 200px;">
            <h4 style="margin: 0 0 5px 0; color: #15803d;">#{row['rank']}: {row['name']}</h4>
            <p style="margin: 2px 0;"><strong>Usable Area:</strong> {row['area']:,} m²</p>
            <p style="margin: 2px 0;"><strong>Est. CO₂ Reduction:</strong> {row['co2']:,} tons/yr</p>
            <p style="margin: 2px 0;"><strong>Rooftop Type:</strong> {row['type']}</p>
        </div>
        """
        
        folium.Marker(
            location=row['lat_lon'],
            tooltip=row['name'], # Tooltip 是地图点击交互的关键
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="green", icon="solar-panel", prefix="fa")
        ).add_to(m)
    return m

# --- Streamlit 应用配置 ---
st.set_page_config(layout="wide", page_title="Leuven 2030 Solar Rooftop Potential Analyzer", page_icon="☀️")
st.title("☀️ Leuven Rooftop Solar Potential Top 200")
st.markdown("Data-Driven Decision Support Tool - Prioritizing high-impact, high-feasibility large rooftops")

# --- 加载 *完整* 数据 (从缓存) ---
df = load_data()

# --- 新功能: 侧边栏过滤器 UI ---
st.sidebar.header("Filters")

def reset_area():
    """回调函数，用于将面积重置为 0"""
    st.session_state.min_area = 0

# --- 修复: 双向绑定回调 ---
# 1. 定义回调函数
# 当滑块更改时，更新 session_state.min_area
def sync_area_from_slider():
    st.session_state.min_area = st.session_state.min_area_slider

# 当数字输入更改时，更新 session_state.min_area
def sync_area_from_input():
    st.session_state.min_area = st.session_state.min_area_input

# 2. 创建 widgets，使用 *唯一的 key* 和 *on_change* 回调
# 两个 widgets 都从 st.session_state.min_area 读取它们的 *value*
st.sidebar.slider(
    "Minimum area (m²):",
    min_value=0, 
    max_value=int(df['area'].max()), # 动态设置最大值
    step=100,
    value=st.session_state.min_area,  # 从 "source of truth" 读取 value
    key='min_area_slider',            # 唯一的 key
    on_change=sync_area_from_slider   # on_change 回调
)
st.sidebar.number_input(
    "Or enter area:",
    min_value=0, 
    max_value=int(df['area'].max()),
    step=100,
    value=st.session_state.min_area,  # 从 "source of truth" 读取 value
    key='min_area_input',             # 唯一的 key
    on_change=sync_area_from_input,   # on_change 回调
    label_visibility="collapsed"
)
# 3. 重置按钮现在也只需更新 "source of truth"
st.sidebar.button("Reset Filter", on_click=reset_area, use_container_width=True)

# --- 数据过滤 ---
# 1. 应用过滤器
df_filtered = df[df['area'] >= st.session_state.min_area].sort_values(by='rank')

# 2. 更新侧边栏计数器
st.sidebar.info(f"Showing {len(df_filtered)} / {len(df)} sites")

# 3. 检查所选项是否已被过滤掉
if st.session_state.selected_rooftop_name:
    # 检查选中的 name 是否还存在于 *过滤后的* 列表中
    if st.session_state.selected_rooftop_name not in df_filtered['name'].values:
        st.session_state.selected_rooftop_name = None
        # st.rerun() # 不需要，让脚本自然流下去更新UI即可

# --- 主布局 ---
col1, col2 = st.columns([3, 2])

# Map display (first column)
with col1:
    st.subheader("Interactive Map Overview")
    
    # 1. 从 *过滤后的数据* (df_filtered) 生成地图
    m = get_map(df_filtered)
    
    # 2. 动态确定地图中心和缩放级别
    leuven_center = [50.8792, 4.7001]
    
    if st.session_state.selected_rooftop_name:
        # 注意：我们仍然从 *完整* 的 df 中查找坐标，以防万一
        selected_rows = df[df['name'] == st.session_state.selected_rooftop_name]
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
            map_center = selected_row['lat_lon']
            map_zoom = 16
        else:
            st.session_state.selected_rooftop_name = None
            map_center = leuven_center
            map_zoom = 12
    else:
        map_center = leuven_center
        map_zoom = 12

    # 3. 渲染 Folium 地图
    map_data = st_folium(m, 
                         width='100%', 
                         height=600,
                         center=map_center,
                         zoom=map_zoom
                        )

    # --- 交互逻辑：地图 -> 状态 ---
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
        # 从 *完整* 的 df 中获取数据以显示详情
        selected_rows = df[df['name'] == selected_name]
        if not selected_rows.empty:
            selected_rooftop = selected_rows.iloc[0]
            
            st.markdown(f"### 🎯 #{selected_rooftop['rank']} {selected_rooftop['name']}")
            
            metrics_col1, metrics_col2 = st.columns(2)
            with metrics_col1:
                st.metric(label="Usable Area (m²)", value=f"{selected_rooftop['area']:,}")
            with metrics_col2:
                st.metric(label="Est. CO₂ Reduction/yr (tons)", value=f"{selected_rooftop['co2']:,}")
            
            st.info(f"**Rooftop Type:** {selected_rooftop['type']}", icon="🏠")
        else:
            # 这种情况不应该发生，但作为保险
            st.session_state.selected_rooftop_name = None
            st.info("🗺️ **Click a marker or adjust filters.**", icon="👆")
    else:
        st.info("🗺️ **Click a green marker on the map** to see details.", icon="👆")

    # --- 列表现在也使用 *过滤后的* 数据 ---
    st.subheader(f"Potential Rooftops List ({len(df_filtered)} shown)")
    
    # 从 df_filtered 中选择列
    display_df = df_filtered[['rank', 'name', 'area', 'co2', 'type']]
    
    column_config = {
        'rank': st.column_config.NumberColumn("Rank", format="%d"),
        'name': "Name",
        'area': st.column_config.NumberColumn("Usable Area (m²)", format="%,.0f"),
        'co2': st.column_config.NumberColumn("Est. CO₂ Reduction/yr (tons)", format="%,.0f"),
        'type': "Rooftop Type",
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
*This app uses `streamlit-folium` for rich map interactions. Data is simulated for prototyping purposes.*
""")