"""
SIF文件读取模块 - 读取Andor SIF格式的光谱数据
基于 sif_parser 库实现波长校准和多帧处理
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np

from .data_model import SpectrumData

# 尝试导入sif_parser，如果不存在则标记为不可用
try:
    import sif_parser
    SIF_AVAILABLE = True
except ImportError:
    SIF_AVAILABLE = False


class SIFReader:
    """Andor SIF文件读取器
    
    使用 sif_parser 库读取 SIF 格式的光谱数据。
    支持多帧数据的平均处理和多项式波长校准。
    
    Attributes:
        available: 是否可用（依赖是否安装）
    """
    
    def __init__(self):
        self.available = SIF_AVAILABLE
    
    def read_file(self, filepath: str) -> SpectrumData:
        """读取SIF文件
        
        Args:
            filepath: SIF文件路径
            
        Returns:
            SpectrumData: 解析后的光谱数据对象
            
        Raises:
            ImportError: 缺少必要的依赖
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不正确或无法解析
        """
        if not self.available:
            raise ImportError(
                "SIF读取功能需要安装sif_parser包。\n"
                "请运行: pip install sif_parser"
            )
        
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        if path.suffix.lower() != '.sif':
            raise ValueError(f"不支持的文件格式: {path.suffix}")
        
        try:
            data, info = sif_parser.np_open(filepath)
            
            # 维度处理：确保数据是2D (frames, pixels)
            data = np.squeeze(data)
            if data.ndim == 1:
                # 单帧数据，扩展为 (1, pixels)
                data = data[np.newaxis, :]
            
            num_pixels = data.shape[-1]
            num_frames = data.shape[0]
            
            # 波长校准
            wavelength = self._calculate_wavelength(info, num_pixels)
            
            # 提取元数据
            metadata = self._extract_metadata(info)
            
            # 构造强度数据列表（每帧一个数组）
            intensity_raw = [data[i] for i in range(num_frames)]
            
            # 计算平均值
            intensity_avg = np.mean(data, axis=0)
            
            return SpectrumData(
                filepath=str(path.absolute()),
                filename=path.name,
                metadata=metadata,
                wavelength=wavelength,
                intensity_raw=intensity_raw,
                intensity_avg=intensity_avg,
                num_scans=num_frames,
                source_format='sif'
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise ValueError(f"无法读取SIF文件: {e}")
    
    def _calculate_wavelength(self, info: Dict[str, Any], num_pixels: int) -> np.ndarray:
        """从校准数据计算波长轴
        
        Args:
            info: SIF文件信息字典
            num_pixels: 像素数量
            
        Returns:
            波长数组（nm），如果无校准数据则返回像素索引
        """
        wavelength = None
        
        # 尝试从 Calibration_data 提取多项式系数
        if 'Calibration_data' in info:
            cal_data = info['Calibration_data']
            
            if isinstance(cal_data, (list, np.ndarray)) and len(cal_data) >= 2:
                pixels = np.arange(num_pixels)
                wavelength = np.zeros(num_pixels)
                
                # 应用多项式校准: wavelength = sum(coeff[i] * pixel^i)
                for i, coeff in enumerate(cal_data):
                    if i < 4:  # 通常最多使用4阶多项式
                        wavelength += coeff * (pixels ** i)
                
                # 检查波长是否有效（非零且单调）
                if np.all(wavelength == 0) or not (np.all(np.diff(wavelength) > 0) or np.all(np.diff(wavelength) < 0)):
                    wavelength = None
        
        # 如果没有有效的校准数据，使用像素索引
        if wavelength is None:
            wavelength = np.arange(num_pixels, dtype=float)
        
        return wavelength
    
    def _extract_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """从SIF信息中提取元数据
        
        Args:
            info: SIF文件信息字典
            
        Returns:
            规范化的元数据字典
        """
        metadata = {}
        
        # SIF常见元数据字段映射
        field_mapping = {
            'ExposureTime': 'ExposureTime',
            'Temperature': 'Temperature',
            'DetectorType': 'DetectorType',
            'CycleTime': 'CycleTime',
            'AccumulateCycles': 'AccumulateCycles',
            'KineticCycleTime': 'KineticCycleTime',
            'ReadoutTime': 'ReadoutTime',
            'GateDelay': 'GateDelay',
            'GateWidth': 'GateWidth',
            'BackgroundFile': 'BackgroundFile',
            'NumberOfFrames': 'NumberOfFrames',
            'xbin': 'XBin',
            'ybin': 'YBin',
            'VerticalShiftSpeed': 'VerticalShiftSpeed',
            'HorizontalShiftSpeed': 'HorizontalShiftSpeed',
            'OutputAmplifier': 'OutputAmplifier',
            'PreAmpGain': 'PreAmpGain',
            'EMGain': 'EMGain',
        }
        
        for sif_key, meta_key in field_mapping.items():
            if sif_key in info:
                value = info[sif_key]
                # 格式化数值
                if isinstance(value, float):
                    if abs(value) < 0.001 or abs(value) > 10000:
                        metadata[meta_key] = f"{value:.2e}"
                    else:
                        metadata[meta_key] = f"{value:.4g}"
                else:
                    metadata[meta_key] = str(value)
        
        return metadata
    
    def read_files(self, filepaths: List[str]) -> List[SpectrumData]:
        """批量读取多个SIF文件
        
        Args:
            filepaths: SIF文件路径列表
            
        Returns:
            List[SpectrumData]: 光谱数据对象列表
        """
        results = []
        for fp in filepaths:
            try:
                data = self.read_file(fp)
                results.append(data)
            except Exception as e:
                print(f"警告: 无法读取文件 {fp}: {e}")
        return results
    
    def is_available(self) -> bool:
        """检查SIF读取功能是否可用"""
        return self.available
    
    @staticmethod
    def get_install_instructions() -> str:
        """获取安装说明"""
        return (
            "SIF文件读取需要安装 sif_parser 包。\n"
            "请运行: pip install sif_parser"
        )


def read_sif_file(filepath: str) -> SpectrumData:
    """便捷函数：读取单个SIF文件
    
    Args:
        filepath: SIF文件路径
        
    Returns:
        SpectrumData: 光谱数据对象
    """
    reader = SIFReader()
    return reader.read_file(filepath)


if __name__ == "__main__":
    reader = SIFReader()
    print(f"SIF读取功能可用: {reader.is_available()}")
    if not reader.is_available():
        print(reader.get_install_instructions())
