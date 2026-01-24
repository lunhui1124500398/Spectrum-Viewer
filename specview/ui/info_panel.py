"""
信息面板 - 显示当前选中数据的信息
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt

from ..core.xls_reader import SpectrumData


class InfoRow(QWidget):
    """信息行"""
    
    def __init__(self, label: str, value: str = "-", parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        self.label = QLabel(label)
        self.label.setObjectName("infoLabel")
        self.label.setMinimumWidth(70)
        layout.addWidget(self.label)
        
        self.value = QLabel(value)
        self.value.setObjectName("valueLabel")
        self.value.setWordWrap(True)
        layout.addWidget(self.value, 1)
    
    def set_value(self, value: str):
        self.value.setText(value)


from PyQt6.QtWidgets import QHBoxLayout


class InfoPanel(QWidget):
    """数据信息显示面板
    
    显示当前选中文件的详细信息：
    - 文件名
    - 数据组数
    - 波长范围
    - 强度范围
    - 仪器参数（激发波长、狭缝等）
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
        
        # 仪器参数组
        param_label = QLabel("仪器参数")
        param_label.setStyleSheet("color: #e94560; font-weight: bold; padding-top: 4px;")
        layout.addWidget(param_label)
        
        param_group = QFrame()
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(0, 4, 0, 4)
        param_layout.setSpacing(2)
        
        self.row_ex_wl = InfoRow("激发波长:")
        param_layout.addWidget(self.row_ex_wl)
        
        self.row_ex_slit = InfoRow("激发狭缝:")
        param_layout.addWidget(self.row_ex_slit)
        
        self.row_em_slit = InfoRow("发射狭缝:")
        param_layout.addWidget(self.row_em_slit)
        
        self.row_pmt = InfoRow("PMT电压:")
        param_layout.addWidget(self.row_pmt)
        
        self.row_scan_speed = InfoRow("扫描速度:")
        param_layout.addWidget(self.row_scan_speed)
        
        layout.addWidget(param_group)
        
        # 弹性空间
        layout.addStretch()
    
    def update_info(self, data: SpectrumData):
        """更新信息显示
        
        Args:
            data: 光谱数据对象
        """
        # 基本信息
        self.row_filename.set_value(data.filename)
        self.row_scans.set_value(str(data.num_scans))
        
        wl_range = data.wavelength_range
        self.row_wavelength.set_value(f"{wl_range[0]:.1f} - {wl_range[1]:.1f} nm")
        
        int_range = data.intensity_range
        self.row_intensity.set_value(f"{int_range[0]:.2f} - {int_range[1]:.2f}")
        
        # 仪器参数
        meta = data.metadata
        self.row_ex_wl.set_value(meta.get('EX WL', '-'))
        self.row_ex_slit.set_value(meta.get('EX Slit', '-'))
        self.row_em_slit.set_value(meta.get('EM Slit', '-'))
        self.row_pmt.set_value(meta.get('PMT Voltage', '-'))
        self.row_scan_speed.set_value(meta.get('Scan speed', '-'))
    
    def clear_info(self):
        """清除信息显示"""
        self.row_filename.set_value("-")
        self.row_scans.set_value("-")
        self.row_wavelength.set_value("-")
        self.row_intensity.set_value("-")
        self.row_ex_wl.set_value("-")
        self.row_ex_slit.set_value("-")
        self.row_em_slit.set_value("-")
        self.row_pmt.set_value("-")
        self.row_scan_speed.set_value("-")
    
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
        
        # 仪器参数（如果相同则显示，不同则显示"多种"）
        first = data_list[0].metadata
        
        def get_common_value(key: str) -> str:
            values = set(d.metadata.get(key, '-') for d in data_list)
            if len(values) == 1:
                return values.pop()
            return f"[{len(values)}种不同值]"
        
        self.row_ex_wl.set_value(get_common_value('EX WL'))
        self.row_ex_slit.set_value(get_common_value('EX Slit'))
        self.row_em_slit.set_value(get_common_value('EM Slit'))
        self.row_pmt.set_value(get_common_value('PMT Voltage'))
        self.row_scan_speed.set_value(get_common_value('Scan speed'))
