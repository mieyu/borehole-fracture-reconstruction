# Borehole Fracture Reconstruction

钻孔成像裂隙识别、几何表征与三维网络重构。项目把孔壁展开图转换为裂隙实例和物理参数，再结合多孔位置分析潜在连接关系，生成空间不确定性图及补充钻孔建议。

## 四项需求

| 需求 | 模块 | 主要能力 |
| --- | --- | --- |
| 需求 1 裂隙识别与连续性增强 | `segmentation` | 经典图像处理 / U-Net 推理、形态学与霍夫辅助连接、IoU/Dice 评价 |
| 需求 2 裂隙聚类与几何参数提取 | `geometry` | 实例聚类、中心线提取、稳健正弦拟合、像素到物理坐标转换 |
| 需求 3 粗糙度量化与采样分析 | `roughness` | 等间距 / 自适应 / 曲率采样、Z2/JRC、密度敏感性分析 |
| 需求 4 三维重构与勘探规划 | `reconstruction` | 裂隙平面映射、跨孔连接评分、不确定性场、贪心补孔排序 |

技术栈：Python、NumPy、SciPy、OpenCV、pandas、Matplotlib；U-Net 使用可选 TensorFlow 依赖。

## 安装

在当前目录执行，Python 版本为 3.10 或以上。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

需要训练或使用 U-Net 时，安装 `python -m pip install -e '.[training]'`。

## 从参数表重构三维网络

```bash
borehole-fracture reconstruct examples/fracture_parameters.csv \
  --boreholes examples/boreholes.json \
  --output outputs/network
```

示例参数使用合成数据。输出包含三维裂隙表、全部跨孔连接评分、高评分候选、体素不确定性、补孔排序和两张空间图。

## 从图像执行完整流程

先生成合成图像与清单，再调用四个功能模块：

```bash
python examples/generate_demo.py --output outputs/demo_input
borehole-fracture run outputs/demo_input/manifest.json \
  --boreholes outputs/demo_input/boreholes.json \
  --output outputs/analysis
```

自有图像按[数据接口](docs/data-contracts.md)编写清单。加入 `--model models/fracture_unet.keras` 即可选择 U-Net 推理路径。

## 按需求独立使用

```bash
borehole-fracture segment outputs/demo_input/manifest.json --output outputs/segmentation
borehole-fracture characterize outputs/demo_input/manifest.json \
  --masks outputs/segmentation/masks --output outputs/geometry
borehole-fracture roughness outputs/geometry/fracture_parameters.csv \
  --samples 50 --output outputs/roughness
borehole-fracture reconstruct outputs/roughness/fracture_parameters_with_roughness.csv \
  --boreholes outputs/demo_input/boreholes.json --output outputs/reconstruction
```

## 训练与评价

```bash
borehole-fracture train data/training_manifest.json --output models/unet
borehole-fracture evaluate outputs/segmentation/masks \
  --reference data/reference_masks --output outputs/evaluation.csv
```

训练清单格式见 [training_manifest.example.json](examples/training_manifest.example.json)。同一原图及其派生样本使用相同 `group_id`；掩码采用黑色裂隙、白色背景。训练输出保存最优模型、最终模型和分组记录。

## 输出结构

```text
outputs/analysis/
├── segmentation/     原始掩码、增强掩码、图像叠加与识别记录
├── geometry/         几何参数表与逐条中心线
├── roughness/        JRC、采样策略对比与密度敏感性表
├── reconstruction/   三维裂隙、连接评分、不确定性与补孔结果
└── run.json          本次流程的输入与配置
```

默认孔径为 30 mm，每张图像的深度范围通过清单设置。图像行号和钻孔深度向下增加，世界坐标采用 Z 向上；方向需要周向起点的方位标定。JRC 同时记录经验原始值和范围截断值。

连接评分用于候选关联排序；不确定性和补孔排序使用几何观测代理。它们帮助组织勘探资料及比较位置，需要结合地质判读和现场约束使用。

进一步阅读：[需求定义](docs/requirements.md) · [数据接口与坐标约定](docs/data-contracts.md) · [架构与处理流程](docs/architecture.md)
