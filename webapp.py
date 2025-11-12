import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# --- 状态管理 (移至顶部) ---
if 'selected_rooftop_name' not in st.session_state:
    st.session_state.selected_rooftop_name = None

# --- 缓存的数据加载函数 (修复关键) ---
@st.cache_data
def load_data():
    """
    创建并缓存 DataFrame。
    这个函数只会运行一次。
    """
    # st.write("... (1. 正在加载并缓存数据) ...") # 调试信息 - 已移除
    
    mock_rooftops = [
        {'rank': 1, 'name': "AB Inbev", 'area': 56691, 'co2': 3500, 'type': "EPDM", 'lat': 50.8930, 'lng': 4.7081},
        {'rank': 2, 'name': "UZ Gasthuisberg", 'area': 32149, 'co2': 2000, 'type': "Bitumen", 'lat': 50.8841, 'lng': 4.6788},
        {'rank': 3, 'name': "Commscope", 'area': 34308, 'co2': 2100, 'type': "EPDM", 'lat': 50.8870, 'lng': 4.6950},
        {'rank': 4, 'name': "Terumo Europe", 'area': 17971, 'co2': 1100, 'type': "Steel", 'lat': 50.8710, 'lng': 4.7200},
        {'rank': 5, 'name': "Depot Aveve", 'area': 14160, 'co2': 900, 'type': "Bitumen", 'lat': 50.9000, 'lng': 4.6650},
        {'rank': 6, 'name': "Beneo-Remy", 'area': 13190, 'co2': 850, 'type': "EPDM", 'lat': 50.8650, 'lng': 4.7100},
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

# --- 缓存的地图生成函数 ---
@st.cache_data
def get_map(_dataframe):
    """
    创建 Folium 地图并添加所有标记。
    这个函数现在也只会被执行一次，因为它依赖于被缓存的 _dataframe。
    """
    # st.write("... (2. G正在创建并缓存地图对象) ...") # 调试信息 - 已移除
    m = folium.Map(location=[50.8792, 4.7001], zoom_start=12, tiles="CartoDB positron")

    for index, row in _dataframe.iterrows():
        # HTML Popup in English
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
            tooltip=row['name'],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="green", icon="solar-panel", prefix="fa")
        ).add_to(m)
    return m

# --- Streamlit 应用配置 ---
st.set_page_config(layout="wide", page_title="Leuven 2030 Solar Rooftop Potential Analyzer", page_icon="☀️")

# Header in English
st.title("☀️ Leuven Rooftop Solar Potential Top 200")
st.markdown("Data-Driven Decision Support Tool - Prioritizing high-impact, high-feasibility large rooftops")

# --- 加载数据 (从缓存) ---
df = load_data()

# --- 主布局 ---
col1, col2 = st.columns([3, 2])

# Map display (first column)
with col1:
    st.subheader("Interactive Map Overview")
    
    # 1. 从缓存中获取地图
    m = get_map(df)
    
    # 2. 动态确定地图中心和缩放级别
    leuven_center = [50.8792, 4.7001]
    
    if st.session_state.selected_rooftop_name:
        # 确保在 df 中找到了选中的屋顶
        selected_rows = df[df['name'] == st.session_state.selected_rooftop_name]
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
            map_center = selected_row['lat_lon']
            map_zoom = 16
        else:
            # 如果没找到（以防万一），重置
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
                         center=map_center, # 传递动态中心
                         zoom=map_zoom       # 传递动态缩放
                        )

    # --- 交互逻辑：地图 -> 状态 ---
    if map_data and map_data.get("last_object_clicked_tooltip"):
        clicked_name = map_data["last_object_clicked_tooltip"]
        
        if st.session_state.selected_rooftop_name != clicked_name:
            st.session_state.selected_rooftop_name = clicked_name
            st.rerun() # 立即重新运行以更新右侧面板


# Information panel (second column) - 由 st.session_state 驱动
with col2:
    st.subheader("Rooftop Details")
    
    selected_name = st.session_state.selected_rooftop_name

    if selected_name:
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
            # 数据可能已更改，重置状态
            st.session_state.selected_rooftop_name = None
            st.info("🗺️ **Click a green marker on the map** to see details.", icon="👆")

    else:
        st.info("🗺️ **Click a green marker on the map** to see details.", icon="👆")

    # 始终显示数据列表以便参考
    st.subheader("Potential Rooftops List (Top 200)")
    
    display_df = df[['rank', 'name', 'area', 'co2', 'type']].sort_values(by='rank')
    # Column config in English
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

# Footer in English
st.markdown("""
---
*This app uses `streamlit-folium` for rich map interactions. Data is simulated for prototyping purposes.*
""")