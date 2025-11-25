import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from torch.utils.data import DataLoader, random_split
import geopandas as gpd
import pandas as pd

# 引入我们刚才定义的 Dataset 类
# 注意：如果在同一个 notebook 运行，可以直接用；如果在不同文件，需要 import
try:
    from rooftop_dataset import RooftopDataset
except ImportError:
    # Fallback for demonstration if running in a single context
    pass 

def get_model(num_classes=2):
    """
    加载预训练的 ResNet-18 并修改最后一层。
    Classes: 0 = Flat (平顶), 1 = Pitched (斜顶)
    """
    # 1. 加载预训练模型 (ImageNet 权重)
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    
    # 2. 冻结前面的层 (可选，如果数据量少建议冻结)
    # for param in model.parameters():
    #     param.requires_grad = False
        
    # 3. 修改全连接层 (Fully Connected Layer)
    # ResNet18 的 fc 输入是 512，我们需要输出 2 类
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)
    
    return model

def train_loop():
    # --- 1. 准备数据 ---
    print("1. Loading Data...")
    # 读取 GeoPackage
    gdf = gpd.read_file("notebooks/data_leuven/leuven_large_roofs.gpkg")
    
    # !!! 关键步骤：你需要标签 !!!
    # 在现实中，你需要先手动标注一部分数据（比如在 CSV 里加一列 'roof_type'）
    # 这里我们模拟生成一些随机标签用于代码演示
    import numpy as np
    fake_labels = np.random.randint(0, 2, size=len(gdf)) # 0 或 1
    
    # 创建 Dataset
    full_dataset = RooftopDataset(gdf, labels=fake_labels)
    
    # 划分 训练集 / 验证集
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True, num_workers=0) # Mac/Windows 上 num_workers=0 更稳定
    val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    # --- 2. 准备模型 ---
    print("2. Initializing Model...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if torch.backends.mps.is_available(): # Mac M1/M2/M3 加速
        device = torch.device("mps")
        
    model = get_model().to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # --- 3. 训练循环 ---
    print(f"3. Starting Training on {device}...")
    num_epochs = 5 # 演示用，实际可能需要更多
    
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        print(f"Epoch {epoch+1}/{num_epochs} - Loss: {running_loss/len(train_loader):.4f} - Acc: {100 * correct / total:.2f}%")
        
    print("Training Complete!")
    
    # --- 4. 保存模型 ---
    torch.save(model.state_dict(), "rooftop_classifier_resnet18.pth")
    print("Model saved as rooftop_classifier_resnet18.pth")

if __name__ == "__main__":
    # 注意：你需要先确保 'notebooks/data_leuven/leuven_large_roofs.gpkg' 存在
    # 并且 RooftopDataset 类被正确定义
    try:
        train_loop()
    except Exception as e:
        print(f"运行时错误: {e}")
        print("提示：这通常是因为找不到数据文件，或者没有安装 pytorch/torchvision")