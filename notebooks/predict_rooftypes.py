import torch
import geopandas as gpd
from tqdm import tqdm  # 进度条库，如果没有请 pip install tqdm
from rooftop_dataset import RooftopDataset
from train_classifier import get_model

def predict():
    # --- 配置 ---
    MODEL_PATH = "rooftop_classifier_resnet18.pth"
    # 输入文件：我们希望给 Top 200 列表加上标签
    INPUT_FILE = "notebooks/data_leuven/leuven_top200_roofs.gpkg"
    # 输出文件：包含预测结果的新文件
    OUTPUT_FILE = "notebooks/data_leuven/leuven_top200_enriched.gpkg"
    
    # 检查设备 (Mac M1/M2 使用 mps, Nvidia 使用 cuda, 否则 cpu)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if torch.backends.mps.is_available():
        device = torch.device("mps")
    
    print(f"1. 加载模型: {MODEL_PATH} ...")
    # 初始化模型架构 (必须与训练时一致)
    model = get_model(num_classes=2)
    # 加载训练好的权重
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval() # 切换到评估模式 (关闭 Dropout 等)
    
    print(f"2. 加载数据: {INPUT_FILE} ...")
    gdf = gpd.read_file(INPUT_FILE)
    print(f"   共 {len(gdf)} 个屋顶待分类")
    
    # 创建数据集 (推理模式不需要标签)
    dataset = RooftopDataset(gdf)
    
    print("3. 开始推理 (Inference)...")
    predictions = []
    probabilities = []
    
    # 禁用梯度计算，节省显存并加速
    with torch.no_grad():
        for i in tqdm(range(len(dataset))):
            # 1. 获取图像 tensor
            img_tensor = dataset[i]
            
            # 2. 增加 batch 维度 [3, 224, 224] -> [1, 3, 224, 224]
            img_input = img_tensor.unsqueeze(0).to(device)
            
            # 3. 前向传播
            outputs = model(img_input)
            
            # 4. 获取预测结果
            # 使用 Softmax 获取概率
            probs = torch.nn.functional.softmax(outputs, dim=1)
            confidence, pred_class = torch.max(probs, 1)
            
            predictions.append(pred_class.item())
            probabilities.append(confidence.item())
            
    # --- 4. 保存结果 ---
    print("4. 处理结果并保存...")
    
    # 映射：0 -> Flat (平顶), 1 -> Pitched (斜顶)
    # 注意：这取决于你在训练时的定义，要保持一致！
    label_map = {0: 'Flat', 1: 'Pitched'}
    
    gdf['roof_type_id'] = predictions
    gdf['roof_type'] = [label_map[p] for p in predictions]
    gdf['ai_confidence'] = probabilities
    
    gdf.to_file(OUTPUT_FILE, driver="GPKG")
    print(f"成功! 已保存至: {OUTPUT_FILE}")
    print("现在你可以更新 webapp.py 来读取这个新文件了。")

if __name__ == "__main__":
    predict()