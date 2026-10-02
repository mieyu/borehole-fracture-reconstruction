# 数据接口与坐标约定

## 图像清单

清单内的图像路径相对于清单所在目录解析。每张图像必须具有唯一的 `image_id`，以及与钻孔表一致的 `borehole_id`。每张图像可覆盖公共标定参数。

```json
{
  "calibration": {"diameter_mm": 30, "interval_mm": 1000, "azimuth_offset_rad": 0},
  "images": [
    {
      "image_id": "scan_B01_1000",
      "borehole_id": "B01",
      "path": "images/scan_B01_1000.jpg",
      "calibration": {"start_depth_mm": 1000}
    }
  ]
}
```

图像横向从左到右覆盖一周，图像纵向从上到下对应深度递增。尺寸为 W×H 的图像按 `x_mm=列号×πD/W`、`depth_mm=起始深度+行号×区间长度/H` 转换。宽、高的物理比例分别计算，避免把纵向像素比例用于周向。

`azimuth_offset_rad` 是图像左边界在世界 XY 平面中的方位，绕 Z 轴从 +X 朝 +Y 正向旋转。零方位代表 +X。所有长度使用 mm，角度使用 rad；展示表中的倾角、倾向使用 deg。

## 钻孔位置

```json
{
  "boreholes": [
    {"borehole_id": "B01", "mouth_mm": [0, 0, 0], "depth_mm": 7000}
  ]
}
```

钻孔沿世界 -Z 方向延伸。中心点为 `孔口+[0,0,-中心深度]`。

## 裂隙参数表

几何参数遵循 `depth=C+R sin(2πx/P+β)`。

| 字段 | 含义 |
| --- | --- |
| `fracture_id` | 全局唯一实例标识 |
| `image_id`, `borehole_id` | 图像与钻孔标识 |
| `amplitude_mm`, `period_mm` | 振幅与固定孔周长 |
| `phase_rad`, `center_depth_mm` | 相位与绝对深度 |
| `diameter_mm`, `azimuth_offset_rad` | 实例使用的物理标定 |
| `fit_r2`, `rmse_mm`, `coverage` | 拟合质量与横向覆盖比例 |
| `area_mm2` | 二值实例的图像投影面积 |
| `profile_path` | 相对于参数表的轮廓文件路径 |
| `jrc`, `jrc_raw`, `z2`, `jrc_clipped` | 粗糙度及范围截断信息 |

每份轮廓文件有 `x_mm,depth_mm,baseline_mm,residual_mm` 四列。粗糙度阶段复制轮廓文件并保留相对路径，使它的参数表可独立归档和继续分析。

## 三维平面与连接评分

令 `φ=β-azimuth_offset_rad`，`r=D/2`，未归一化的平面法向量为 `(R/r×sinφ,R/r×cosφ,1)`。这一表达直接对应柱面展开曲线以及 Z 向上的世界坐标。法向量归一化后用于平面距离和姿态相似度。

连接评分为 `0.5×exp(-(d/尺度)²)+0.3×|n₁·n₂|+0.2×(1-|JRC₁-JRC₂|/20)`，范围为 0–1。`connection_score` 是排序评分，不表示经统计校准的事件概率。

## 示例数据

`examples/fracture_parameters.csv` 和 `generate_demo.py` 使用合成数据，供学习接口和演示命令。示例不包含实测效果指标。`training_manifest.example.json` 是数据清单结构模板，其路径应替换为自己的图像与标签路径。
