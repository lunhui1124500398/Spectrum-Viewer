"""
数据表格组件 - 仿 Origin 样式
"""

from typing import List, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QTabWidget,
                            QLabel, QHBoxLayout, QComboBox)
from PyQt6.QtCore import Qt
from ..core.data_model import SpectrumData

class DataTableWidget(QWidget):
    """数据表格组件
    
    Features:
    - 显示波长和强度数据
    - 支持多文件数据切换
    - 显示原始扫描和平均值
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.current_data: Optional[SpectrumData] = None
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部工具栏：文件选择
        self.combo_files = QComboBox()
        self.combo_files.currentIndexChanged.connect(self._on_file_changed)
        layout.addWidget(self.combo_files)
        
        # 表格控件
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(True) # 显示行号
        layout.addWidget(self.table)
        
        # 缓存当前的所有数据列表
        self.data_list: List[SpectrumData] = []
        
    def set_data_list(self, data_list: List[SpectrumData]):
        """设置数据列表"""
        self.data_list = data_list
        self.combo_files.blockSignals(True)
        self.combo_files.clear()
        
        if not data_list:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.combo_files.blockSignals(False)
            return
            
        for data in data_list:
            self.combo_files.addItem(data.filename)
            
        self.combo_files.blockSignals(False)
        
        # 默认选中第一个
        if data_list:
            self.combo_files.setCurrentIndex(0)
            self._update_table(data_list[0])
            
    def set_data(self, data: SpectrumData):
        """显示单个数据（会清空其他列表）"""
        self.set_data_list([data])
        
    def _on_file_changed(self, index: int):
        if 0 <= index < len(self.data_list):
            self._update_table(self.data_list[index])
            
    def _update_table(self, data: SpectrumData):
        """更新表格内容"""
        self.current_data = data
        self.table.blockSignals(True)
        self.table.clear()
        
        # 列头：Wavelength, Scan_1, Scan_2..., Average
        headers = ["Wavelength (nm)"]
        if data.intensity_raw:
            for i in range(len(data.intensity_raw)):
                headers.append(f"Scan {i+1}")
        headers.append("Average")
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        rows = len(data.wavelength)
        self.table.setRowCount(rows)
        
        # 填充数据
        # 为了性能，可以考虑使用 QAbstractTableModel，但这里为了简单先用 QTableWidget
        # 只要数据量不是特别大（几千行）通常没问题
        
        for r in range(rows):
            # Wavelength
            wl_item = QTableWidgetItem(f"{data.wavelength[r]:.2f}")
            wl_item.setFlags(wl_item.flags() ^ Qt.ItemFlag.ItemIsEditable) # 只读
            self.table.setItem(r, 0, wl_item)
            
            col = 1
            # Raw Scans
            if data.intensity_raw:
                for scan in data.intensity_raw:
                    if r < len(scan):
                        val_item = QTableWidgetItem(f"{scan[r]:.4f}")
                        val_item.setFlags(val_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                        self.table.setItem(r, col, val_item)
                    col += 1
            
            # Average
            if r < len(data.intensity_avg):
                avg_item = QTableWidgetItem(f"{data.intensity_avg[r]:.4f}")
                avg_item.setFlags(avg_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, col, avg_item)
                
        self.table.blockSignals(False)
