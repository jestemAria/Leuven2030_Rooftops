import torch
import geopandas as gpd
from tqdm import tqdm
import os
import sys
import numpy as np

# 路径处理：确保能导入同一目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from rooftop_dataset import RooftopDataset
    from train_classifier import get_model
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保 rooftop_dataset.py 和 train_classifier.py 在 notebooks 目录下")
    sys.exit(1)

def predict():
    # --- 1. 配置路径 ---
    # 假设你在项目根目录运行 (Leuven2030_Rooftops/)
    # 或者在 notebooks 目录运行，这里尝试自动适配
    
    # 模型路径 (刚刚训练好的)
    model_path = "notebooks/rooftop_classifier_resnet18.pth"
    if not os.path.exists(model_path):
        # 尝试当前目录
        model_path = "rooftop_classifier_resnet18.pth"
    
    # 数据路径
    input_file = "notebooks/data/large_roofs_test.gpkg"
    if not os.path.exists(input_file):
        input_file = "data/large_roofs_test.gpkg" # 尝试相对路径
        
    # 输出路径 (生成的新文件)
    output_file = input_file.replace(".gpkg", "_enriched.gpkg")

    # --- 检查文件 ---
    if not os.path.exists(input_file):
        print(f"❌ 找不到输入数据: {input_file}")
        return
    if not os.path.exists(model_path):
        print(f"❌ 找不到模型文件: {model_path}")
        return

    # --- 2. 准备设备 ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    print(f"🚀 使用设备: {device}")

    # --- 3. 加载模型 ---
    print(f"🧠 加载模型: {model_path} ...")
    model = get_model(num_classes=2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval() # 开启评估模式

    # --- 4. 加载数据 ---
    print(f"📂 读取数据: {input_file} ...")
    gdf = gpd.read_file(input_file)
    print(f"   待处理屋顶数: {len(gdf)}")

    # 准备数据集 (自动下载图片)
    dataset = RooftopDataset(gdf)
    
    # --- 5. 开始推理 ---
    print("🔮 开始 AI 预测...")
    predictions = []
    probabilities = []
    
    with torch.no_grad(): # 不计算梯度，省内存
        for i in tqdm(range(len(dataset))):
            try:
                img, _ = dataset[i] if dataset.labels is not None else (dataset[i], None)
                # dataset[i] 返回 (img) 或者 (img, label)，这里做个兼容处理
                if isinstance(img, tuple): img = img[0]
                
                # 增加 batch 维度
                img_input = img.unsqueeze(0).to(device)
                
                # 预测
                outputs = model(img_input)
                probs = torch.nn.functional.softmax(outputs, dim=1)
                conf, pred = torch.max(probs, 1)
                
                predictions.append(pred.item())
                probabilities.append(conf.item())
            except Exception as e:
                print(f"   ⚠️ 跳过索引 {i}: {e}")
                predictions.append(0)
                probabilities.append(0.0)

    # --- 6. 保存结果 ---
    print("💾 保存结果...")
    label_map = {0: 'Flat', 1: 'Pitched'} # 确保跟训练时一致！
    
    gdf['roof_type_id'] = predictions
    gdf['roof_type'] = [label_map[p] for p in predictions]
    gdf['ai_confidence'] = probabilities
    
    gdf.to_file(output_file, driver="GPKG")
    print(f"✅ 完成！已生成增强数据: {output_file}")
    print("👉 现在去刷新你的 Streamlit 网页吧！")

if __name__ == "__main__":
    predict()