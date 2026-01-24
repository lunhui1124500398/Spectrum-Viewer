# SpectrumViewer

荧光光谱数据查看和预处理工具，支持Hitachi F-7000光谱仪导出的xls文件。

## 功能特性

- 📂 拖拽导入xls文件
- 📊 自动检测并平均多组扫描数据
- 🎨 可视化叠加、分组、对比显示
- 💾 模板系统保存绘图配置
- 📤 导出CSV（单文件/合并）

## 安装

```bash
# 创建虚拟环境
python -m venv specview
specview\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
python -m specview.main
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+O | 打开文件 |
| Ctrl+Shift+O | 打开文件夹 |
| Ctrl+E | 导出CSV |
| Ctrl+Enter | 叠加选中曲线 |
| G | 切换网格 |
| L | 切换图例 |

## 许可证

MIT License
