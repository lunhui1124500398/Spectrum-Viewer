"""
信息面板 - 显示当前选中数据的信息
支持 XLS 和 SIF 格式的元数据动态显示
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt

from ..core.data_model import SpectrumData


class InfoRow(QWidget):
    """信息行"""
    
    def __init__(self, label: str, value: str = "-", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        self.label_widget = QLabel(label)
        self.label_widget.setObjectName("infoLabel")
        self.label_widget.setMinimumWidth(70)
        layout.addWidget(self.label_widget)
        
        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("valueLabel")
        self.value_widget.setWordWrap(True)
        layout.addWidget(self.value_widget, 1)
    
    def set_value(self, value: str):
        self.value_widget.setText(value)
    
    def set_label(self, label: str):
        self.label_widget.setText(label)


class InfoPanel(QWidget):
    """数据信息显示面板
    
    显示当前选中文件的详细信息：
    - 文件名
    - 格式类型
    - 数据组数
    - 波长范围
    - 强度范围
    - 仪器参数（根据格式动态显示）
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPanel")
        self._setup_ui()
        self.clear_info()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # 标题
        title = QLabel("📋 数据信息")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 基本信息组
        basic_group = QFrame()
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setContentsMargins(0, 8, 0, 8)
        basic_layout.setSpacing(2)
        
        self.row_filename = InfoRow("文件名:")
        basic_layout.addWidget(self.row_filename)
        
        self.row_format = InfoRow("格式:")
        basic_layout.addWidget(self.row_format)
        
        self.row_scans = InfoRow("数据组数:")
        basic_layout.addWidget(self.row_scans)
        
        self.row_wavelength = InfoRow("波长范围:")
        basic_layout.addWidget(self.row_wavelength)
        
        self.row_intensity = InfoRow("强度范围:")
        basic_layout.addWidget(self.row_intensity)
        
        layout.addWidget(basic_group)
        
        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #0f3460;")
        layout.addWidget(sep)
        
        # 仪器参数组标题
        self.param_label = QLabel("仪器参数")
        self.param_label.setStyleSheet("color: #e94560; font-weight: bold; padding-top: 4px;")
        layout.addWidget(self.param_label)
        
        # 动态参数显示区域
        self.param_group = QFrame()
        self.param_layout = QVBoxLayout(self.param_group)
        self.param_layout.setContentsMargins(0, 4, 0, 4)
        self.param_layout.setSpacing(2)
        
        # 预创建参数行（最多5行通用参数）
        self.param_rows = []
        for _ in range(5):
            row = InfoRow("参数:")
            row.setVisible(False)
            self.param_layout.addWidget(row)
            self.param_rows.append(row)
        
        layout.addWidget(self.param_group)
        
        # 弹性空间
        layout.addStretch()
    
    def update_info(self, data: SpectrumData):
        """更新信息显示
        
        Args:
            data: 光谱数据对象
        """
        # 基本信息
        self.row_filename.set_value(data.filename)
        self.row_format.set_value(data.source_format.upper())
        self.row_scans.set_value(str(data.num_scans))
        
        wl_range = data.wavelength_range
        self.row_wavelength.set_value(f"{wl_range[0]:.1f} - {wl_range[1]:.1f} nm")
        
        int_range = data.intensity_range
        self.row_intensity.set_value(f"{int_range[0]:.2f} - {int_range[1]:.2f}")
        
        # 根据格式显示不同的参数
        self._update_params(data)
    
    def _update_params(self, data_or_list):
        """根据数据格式更新参数显示"""
        if isinstance(data_or_list, list):
            # 处理多文件
            data_list = data_or_list
            if not data_list:
                return

            # 检查格式一致性
            first_format = data_list[0].source_format
            if any(d.source_format != first_format for d in data_list):
                # 格式不一致，隐藏参数
                for row in self.param_rows:
                    row.setVisible(False)
                return
            
            # 使用第一个数据的格式定义映射
            source_format = first_format
            meta_list = [d.metadata for d in data_list]
        else:
            # 单文件
            source_format = data_or_list.source_format
            meta_list = [data_or_list.metadata]
        
        # 定义各格式的参数映射 (标签, 键)
        if source_format == 'xls':
            param_map = [
                ("激发波长:", 'EX WL'),
                ("激发狭缝:", 'EX Slit'),
                ("发射狭缝:", 'EM Slit'),
                ("PMT电压:", 'PMT Voltage'),
                ("扫描速度:", 'Scan speed'),
            ]
        elif source_format == 'sif':
            param_map = [
                ("曝光时间:", 'ExposureTime'),
                ("温度:", 'Temperature'),
                ("探测器:", 'DetectorType'),
                ("读出时间:", 'ReadoutTime'),
                ("帧数:", 'NumberOfFrames'),
            ]
        else:
            param_map = []
        
        # 更新参数行
        for i, row in enumerate(self.param_rows):
            if i < len(param_map):
                label, key = param_map[i]
                
                # 聚合值
                values = set()
                for meta in meta_list:
                    val = meta.get(key, '-')
                    values.add(str(val))
                
                if len(values) == 1:
                    display_value = list(values)[0]
                elif len(values) > 1:
                    display_value = "<多个值>" 
                    # 尝试显示范围 (如果是数字)
                    try:
                        nums = [float(v) for v in values if v != '-' and v.replace('.','',1).isdigit()]
                        if nums:
                            display_value = f"{min(nums)} - {max(nums)}"
                    except:
                        pass
                else:
                    display_value = '-'

                row.set_label(label)
                row.set_value(display_value)
                row.setVisible(True)
            else:
                row.setVisible(False)
    
    def clear_info(self):
        """清除信息显示"""
        self.row_filename.set_value("-")
        self.row_format.set_value("-")
        self.row_scans.set_value("-")
        self.row_wavelength.set_value("-")
        self.row_intensity.set_value("-")
        for row in self.param_rows:
            row.set_value("-")
            row.setVisible(False)
    
    def update_multi_info(self, data_list: list):
        """更新多文件信息（叠加模式）
        
        Args:
            data_list: 光谱数据列表
        """
        if not data_list:
            self.clear_info()
            return
        
        # 显示多文件统计
        self.row_filename.set_value(f"[{len(data_list)} 个文件]")
        
        # 格式统计
        formats = set(d.source_format for d in data_list)
        self.row_format.set_value(', '.join(f.upper() for f in formats))
        
        # 计算总扫描数
        total_scans = sum(d.num_scans for d in data_list)
        self.row_scans.set_value(f"共 {total_scans} 组")
        
        # 波长范围（取最大范围）
        wl_min = min(d.wavelength_range[0] for d in data_list)
        wl_max = max(d.wavelength_range[1] for d in data_list)
        self.row_wavelength.set_value(f"{wl_min:.1f} - {wl_max:.1f} nm")
        
        # 强度范围（取最大范围）
        int_min = min(d.intensity_range[0] for d in data_list)
        int_max = max(d.intensity_range[1] for d in data_list)
        self.row_intensity.set_value(f"{int_min:.2f} - {int_max:.2f}")
        
        # 尝试显示参数（如果格式一致）
        self._update_params(data_list)
