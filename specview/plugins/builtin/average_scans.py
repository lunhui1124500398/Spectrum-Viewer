"""
内置插件：扫描平均
"""

import numpy as np
from typing import List, Any
from ..base import ProcessingPlugin, ParamSpec
from ...core.data_model import SpectrumData

class AverageScansPlugin(ProcessingPlugin):
    """扫描平均插件
    
    将 intensity_raw 中的多组数据平均，并在 intensity_avg 中更新结果。
    """
    name = "average_scans"
    display_name = "扫描平均"
    version = "1.0.0"
    description = "计算多次扫描的平均光谱强度"
    category = "Preprocessing"
    
    def process(self, data: SpectrumData, **params) -> SpectrumData:
        """执行平均处理
        
        Args:
            data: 输入数据
            **params: 
                - method (str): 平均方法 ('mean', 'median'). Default: 'mean'
                
        Returns:
            SpectrumData: 更新后的数据对象（原地修改或返回新对象）
            注意：此处为了演示，我们假设直接修改 intensity_avg
        """
        if not data.intensity_raw or len(data.intensity_raw) == 0:
            return data
            
        method = params.get('method', 'mean')
        
        # 将 list[np.ndarray] 转换为 2D array: (num_scans, num_points)
        # 需确保所有扫描长度一致
        try:
            raw_matrix = np.vstack(data.intensity_raw)
            
            if method == 'median':
                data.intensity_avg = np.median(raw_matrix, axis=0)
            else:
                # default to mean
                data.intensity_avg = np.mean(raw_matrix, axis=0)
                
        except ValueError as e:
            # 维度不一致等问题
            print(f"Error averaging scans: {e}")
            # 如果失败，保持原样或抛出异常
            pass
            
        return data
        
    def get_params_schema(self) -> List[ParamSpec]:
        """参数定义"""
        return [
            ParamSpec(
                name="method",
                type="options",
                label="平均方法",
                default="mean",
                options=["mean", "median"],
                description="选择计算平均值还是中位数"
            )
        ]
