import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
import geopandas as gpd
from pyproj import Transformer
import os
import glob

st.set_page_config(layout="wide", page_title="Full City Scan", page_icon="🏙️")

# --- 1. 数据加载逻辑 (Ha Van/Alex's Data) ---
@st.cache_data
def load_full_city_data():
    # 路径指向 Ha Van 提到的 notebook 数据目录
    search_path = "notebooks/data"
    
    # 既然我们知道具体文件名，就直接指定优先级
    # 优先加载 GPKG (包含几何信息且读取快)，其次 GeoJSON，最后 CSV
    priority_files = [
        "large_roofs_test.gpkg",
        "large_roofs_test.geojson",
        "large_roofs_test.csv"
    ]
    
    target_file = None
    for fname in priority_files:
        fpath = os.path.join(search_path, fname)
        if os.path.exists(fpath):
            target_file = fpath
            break
    
    if not target_file:
        # 如果指定文件都没找到，列出目录下有什么，方便调试
        if os.path.exists(search_path):
            found = os.listdir(search_path)
            return None, f"Could not find 'large_roofs_test.*' in `{search_path}`. Found: {found}"
        else:
            return None, f"Directory not found: `{search_path}`."
    
    try:
        # 加载数据
        if target_file.endswith(".csv"):
            df = pd.read_csv(target_file)
            # 假设 CSV 里有坐标，如果不标准可能需要转换
            # 检查是否有 lat/lon，或者 x/y (Lambert72)
            if 'lat' not in df.columns and 'x' in df.columns:
                 transformer = Transformer.from_crs("EPSG:31370", "EPSG:4326", always_xy=True)
                 df['lon'], df['lat'] = transformer.transform(df['x'].values, df['y'].values)
        else:
            # GPKG 或 GeoJSON
            df = gpd.read_file(target_file).to_crs(4326)
            # 计算几何中心点用于 MarkerCluster
            df['lon'] = df.geometry.centroid.x
            df['lat'] = df.geometry.centroid.y
            
        return df, None
    except Exception as e:
        return None, str(e)

# --- 2. 页面布局 ---
st.title("🏙️ Full City Solar Scan")
st.caption("Analysis of buildings (Ha Van & Alex)")

df, error = load_full_city_data()

if error:
    st.error(f"Data Loading Error: {error}")
    st.info("💡 Tip: Ensure `large_roofs_test.gpkg` (or .csv/.geojson) is in `notebooks/data/`")
    st.stop()

# --- 3. 性能优化提示 ---
st.info(f"Loaded **{len(df):,}** buildings from `{os.path.basename('large_roofs_test')}`. Using Clustering for performance.")

# --- 4. 地图绘制 (使用 MarkerCluster) ---
# 修改：将 tiles 从 "CartoDB dark_matter" 改为 "CartoDB positron" (浅色风格)
m = folium.Map(location=[50.8792, 4.7001], zoom_start=13, tiles="CartoDB positron")

# 使用 FastMarkerCluster 处理大量数据点
marker_cluster = MarkerCluster(name="All Buildings").add_to(m)

# 准备数据用于批量添加
subset = df # 如果数据量非常大导致卡顿，可以使用 df.head(10000)

for idx, row in subset.iterrows():
    # 尝试获取一些通用列名，防止报错
    # 你的数据可能有 'area_m2', 'oppervlakte' 或 'Shape_Area' 等不同列名
    area_val = row.get('area_m2', row.get('area', row.get('oppervlakte', 'N/A')))
    
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=3,
        color="#3b82f6",
        fill=True,
        fill_opacity=0.6,
        popup=f"ID: {idx}<br>Area: {area_val}"
    ).add_to(marker_cluster)

st_folium(m, height=700, width="100%")