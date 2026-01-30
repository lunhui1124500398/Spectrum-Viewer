"""
光谱数据模型 - 通用数据结构
用于在不同读取器（XLS、SIF）和UI组件之间共享
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np


@dataclass
class SpectrumData:
    """光谱数据容器
    
    通用数据结构，用于存储从不同文件格式（XLS、SIF等）读取的光谱数据。
    
    Attributes:
        filepath: 文件完整路径
        filename: 文件名
        metadata: 元数据字典（仪器参数、扫描设置等，内容因文件格式而异）
        wavelength: 波长数组 (nm)
        intensity_raw: 原始各组强度数据（多帧/多扫描）
        intensity_avg: 平均后的强度数据
        num_scans: 扫描次数（数据组数/帧数）
        source_format: 数据来源格式 ('xls', 'sif', 等)
    """
    filepath: str
    filename: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    wavelength: np.ndarray = field(default_factory=lambda: np.array([]))
    intensity_raw: List[np.ndarray] = field(default_factory=list)
    intensity_avg: np.ndarray = field(default_factory=lambda: np.array([]))
    num_scans: int = 0
    source_format: str = 'unknown'
    
    @property
    def wavelength_range(self) -> Tuple[float, float]:
        """返回波长范围 (min, max)"""
        if len(self.wavelength) == 0:
            return (0.0, 0.0)
        return (float(self.wavelength.min()), float(self.wavelength.max()))
    
    @property
    def intensity_range(self) -> Tuple[float, float]:
        """返回平均强度范围 (min, max)"""
        if len(self.intensity_avg) == 0:
            return (0.0, 0.0)
        return (float(self.intensity_avg.min()), float(self.intensity_avg.max()))
    
    def get_info_text(self) -> str:
        """返回格式化的信息文本"""
        wl_range = self.wavelength_range
        int_range = self.intensity_range
        
        lines = [
            f"文件: {self.filename}",
            f"格式: {self.source_format.upper()}",
            f"数据组数: {self.num_scans}",
            f"波长范围: {wl_range[0]:.1f} - {wl_range[1]:.1f} nm",
            f"强度范围: {int_range[0]:.2f} - {int_range[1]:.2f}",
        ]
        
        # 根据来源格式添加不同的元数据信息
        if self.source_format == 'xls':
            # XLS 特有的元数据
            if 'EX WL' in self.metadata:
                lines.append(f"激发波长: {self.metadata['EX WL']}")
            if 'EX Slit' in self.metadata:
                lines.append(f"激发狭缝: {self.metadata['EX Slit']}")
            if 'EM Slit' in self.metadata:
                lines.append(f"发射狭缝: {self.metadata['EM Slit']}")
            if 'PMT Voltage' in self.metadata:
                lines.append(f"PMT电压: {self.metadata['PMT Voltage']}")
        elif self.source_format == 'sif':
            # SIF 特有的元数据
            if 'ExposureTime' in self.metadata:
                lines.append(f"曝光时间: {self.metadata['ExposureTime']}")
            if 'Temperature' in self.metadata:
                lines.append(f"温度: {self.metadata['Temperature']}")
            if 'DetectorType' in self.metadata:
                lines.append(f"探测器: {self.metadata['DetectorType']}")
            if 'ReadoutTime' in self.metadata:
                lines.append(f"读出时间: {self.metadata['ReadoutTime']}")
            
        return '\n'.join(lines)
