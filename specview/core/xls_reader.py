"""
XLS文件读取模块 - 读取Hitachi F-7000光谱仪导出的xls文件
"""

from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd

from .data_model import SpectrumData


class XLSReader:
    """读取Hitachi F-7000导出的xls文件
    
    该类负责解析光谱仪导出的xls文件，自动检测多组Data Points数据并计算平均值。
    
    Example:
        >>> reader = XLSReader()
        >>> data = reader.read_file("spectrum.xls")
        >>> print(f"检测到 {data.num_scans} 组数据")
        >>> print(f"波长范围: {data.wavelength_range}")
    """
    
    # 元数据字段映射（xls中的字段名 -> 规范化字段名）
    METADATA_FIELDS = {
        'Sample:': 'Sample',
        'File name:': 'File name',
        'Run Date:': 'Run Date',
        'Operator:': 'Operator',
        'Comment:': 'Comment',
        'Model:': 'Model',
        'Serial Number:': 'Serial Number',
        'Measurement type:': 'Measurement type',
        'Scan mode:': 'Scan mode',
        'Data mode:': 'Data mode',
        'EX WL:': 'EX WL',
        'EM  Start WL:': 'EM Start WL',
        'EM  End WL:': 'EM End WL',
        'Scan speed:': 'Scan speed',
        'EX Slit:': 'EX Slit',
        'EM Slit:': 'EM Slit',
        'PMT Voltage:': 'PMT Voltage',
        'Response:': 'Response',
    }
    
    def read_file(self, filepath: str) -> SpectrumData:
        """读取单个xls文件
        
        Args:
            filepath: xls文件路径
            
        Returns:
            SpectrumData: 解析后的光谱数据对象
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不正确或无法解析
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        if path.suffix.lower() != '.xls':
            raise ValueError(f"不支持的文件格式: {path.suffix}")
        
        # 读取Excel文件
        try:
            df_dict = pd.read_excel(filepath, sheet_name=None)
        except Exception as e:
            raise ValueError(f"无法读取Excel文件: {e}")
        
        # 使用第一个sheet
        sheet_name = list(df_dict.keys())[0]
        df = df_dict[sheet_name]
        
        # 提取元数据
        metadata = self._extract_metadata(df)
        
        # 查找所有Data Points区块
        data_sections = self._find_data_sections(df)
        
        if not data_sections:
            raise ValueError("未找到有效的Data Points数据")
        
        # 解析每个数据区块
        wavelength = None
        intensity_raw = []
        
        for start_row in data_sections:
            wl, intensity = self._parse_spectrum_data(df, start_row)
            if wavelength is None:
                wavelength = wl
            intensity_raw.append(intensity)
        
        # 计算平均值
        intensity_avg = np.mean(intensity_raw, axis=0)
        
        return SpectrumData(
            filepath=str(path.absolute()),
            filename=path.name,
            metadata=metadata,
            wavelength=wavelength,
            intensity_raw=intensity_raw,
            intensity_avg=intensity_avg,
            num_scans=len(data_sections),
            source_format='xls'
        )
    
    def read_files(self, filepaths: List[str]) -> List[SpectrumData]:
        """批量读取多个xls文件
        
        Args:
            filepaths: xls文件路径列表
            
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
    
    def _extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """提取元数据
        
        Args:
            df: DataFrame对象
            
        Returns:
            Dict: 元数据字典
        """
        metadata = {}
        
        # 遍历前50行查找元数据字段
        for i in range(min(50, len(df))):
            row = df.iloc[i]
            # 第一列是字段名，第二列是值
            field_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            field_value = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else ''
            
            if field_name in self.METADATA_FIELDS:
                key = self.METADATA_FIELDS[field_name]
                metadata[key] = str(field_value).strip("'\" ")
        
        return metadata
    
    def _find_data_sections(self, df: pd.DataFrame) -> List[int]:
        """查找所有Data Points区块的起始行
        
        Args:
            df: DataFrame对象
            
        Returns:
            List[int]: Data Points区块的起始行索引列表
        """
        data_points_rows = []
        
        for i, row in df.iterrows():
            first_col = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            if first_col == 'Data Points':
                data_points_rows.append(i)
        
        return data_points_rows
    
    def _parse_spectrum_data(self, df: pd.DataFrame, start_row: int) -> Tuple[np.ndarray, np.ndarray]:
        """解析单个Data Points区块的光谱数据
        
        Args:
            df: DataFrame对象
            start_row: Data Points所在的行索引
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: (波长数组, 强度数组)
        """
        wavelengths = []
        intensities = []
        
        # 数据从 "Data Points" 行之后的第2行开始 (跳过 "nm" / "Data" 标题行)
        data_start = start_row + 2
        
        for i in range(data_start, len(df)):
            row = df.iloc[i]
            
            # 检查是否到达下一个区块或空行
            first_col = row.iloc[0]
            if pd.isna(first_col):
                break
            
            # 尝试解析为数值
            try:
                wl = float(first_col)
                intensity = float(row.iloc[1])
                wavelengths.append(wl)
                intensities.append(intensity)
            except (ValueError, TypeError):
                # 非数值行，可能是下一个区块的开始
                break
        
        return np.array(wavelengths), np.array(intensities)


def read_spectrum_file(filepath: str) -> SpectrumData:
    """便捷函数：读取单个光谱文件
    
    Args:
        filepath: 文件路径
        
    Returns:
        SpectrumData: 光谱数据对象
    """
    reader = XLSReader()
    return reader.read_file(filepath)


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        data = read_spectrum_file(filepath)
        print(data.get_info_text())
        print(f"\n波长数据点数: {len(data.wavelength)}")
        print(f"前5个数据点:")
        for i in range(min(5, len(data.wavelength))):
            print(f"  {data.wavelength[i]:.1f} nm: {data.intensity_avg[i]:.3f}")
