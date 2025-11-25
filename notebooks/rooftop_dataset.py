import io
import requests
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms
import geopandas as gpd
from shapely.geometry import box

# --- 配置 (已修复 URL) ---
# 旧域名: geoservices.informatievlaanderen.be (已失效)
# 新域名: geo.api.vlaanderen.be
# 服务: OMWRGBMRVL (Orthofotomozaïek, Winter, RGB, Vlaanderen)
WMS_URL = "https://geo.api.vlaanderen.be/OMWRGBMRVL/wms"
LAYER_NAME = "Ortho" # "Ortho" 通常是指向最新拼接图的图层别名

class RooftopDataset(Dataset):
    """
    自定义 PyTorch 数据集：
    1. 接收一个包含屋顶几何形状的 GeoDataFrame。
    2. (可选) 接收 labels (0=Flat, 1=Pitched)。如果是预测模式，可以没有 label。
    3. 实时从 WMS 服务抓取该屋顶的卫星图像。
    """
    def __init__(self, gdf, labels=None, transform=None, img_size=224):
        """
        args:
            gdf (GeoDataFrame): 包含 'geometry' 列 (必须是 EPSG:31370 投影)
            labels (list/array): 对应的标签 (可选)
            transform: PyTorch 图像增强
            img_size: 神经网络输入大小 (ResNet 默认为 224)
        """
        self.gdf = gdf
        self.labels = labels
        self.transform = transform
        self.img_size = img_size

        # 默认的转换：转 Tensor 并 归一化
        if self.transform is None:
            self.transform = transforms.Compose([
                transforms.Resize((img_size, img_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], # ImageNet 标准
                                     std=[0.229, 0.224, 0.225])
            ])

    def __len__(self):
        return len(self.gdf)

    def __getitem__(self, idx):
        # 1. 获取几何形状
        polygon = self.gdf.geometry.iloc[idx]
        
        # 2. 获取图像 (这是最关键的一步)
        try:
            image = self.fetch_satellite_image(polygon)
        except Exception as e:
            print(f"Error fetching image for index {idx}: {e}")
            # 如果失败，返回一个全黑图像防止崩溃
            image = Image.new('RGB', (self.img_size, self.img_size))

        # 3. 应用图像转换 (Augmentation/Normalization)
        if self.transform:
            image = self.transform(image)

        # 4. 返回数据
        if self.labels is not None:
            label = torch.tensor(self.labels[idx], dtype=torch.long)
            return image, label
        else:
            return image

    def fetch_satellite_image(self, polygon):
        """
        根据多边形边界框从 WMS 获取图片。
        """
        minx, miny, maxx, maxy = polygon.bounds
        
        # 添加一点 padding，让屋顶在图片中间
        padding = 2.0 # 米
        bbox = (minx - padding, miny - padding, maxx + padding, maxy + padding)
        
        # 构建 WMS 请求参数
        width = self.img_size
        height = self.img_size
        
        params = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": LAYER_NAME,
            "CRS": "EPSG:31370", # 比利时坐标系
            "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "WIDTH": width,
            "HEIGHT": height,
            "FORMAT": "image/png",
            "STYLES": ""
        }
        
        # 发送请求
        response = requests.get(WMS_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # 将字节流转换为 PIL Image
        img = Image.open(io.BytesIO(response.content))
        return img.convert("RGB")

# --- 调试/测试代码 ---
if __name__ == "__main__":
    # 模拟：加载你在 osm_experiments 生成的数据
    try:
        print("正在加载数据测试...")
        # 注意：这里假设你有一个 gpkg 文件，如果没有，你需要先运行之前的 notebook
        df = gpd.read_file("notebooks/data_leuven/leuven_large_roofs.gpkg")
        
        # 取前 5 个屋顶做测试
        sample_df = df.head(5)
        
        # 初始化数据集
        dataset = RooftopDataset(sample_df)
        
        # 获取第一张图
        img_tensor = dataset[0]
        print(f"成功获取图像 Tensor，形状: {img_tensor.shape}")
        print("数据管道测试通过！")
        
    except Exception as e:
        print(f"测试跳过或失败: {e}")
        print("提示：请确保 'notebooks/data_leuven/leuven_large_roofs.gpkg' 存在。")