"""
插件系统基类定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from ..core.data_model import SpectrumData

@dataclass
class ParamSpec:
    """参数规格，用于 UI 自动生成"""
    name: str
    type: str  # 'int', 'float', 'str', 'bool', 'range', 'options'
    label: str
    default: Any = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    step: Optional[float] = None
    options: List[str] = field(default_factory=list)  # 用于下拉选择
    description: str = ""

class ProcessingPlugin(ABC):
    """处理插件基类
    
    用户可继承此类创建自定义处理步骤
    """
    name: str = "undefined"          # 插件内部名称（唯一标识符）
    display_name: str = "Undefined"  # 显示名称
    version: str = "1.0.0"          # 版本号
    description: str = ""           # 功能描述
    category: str = "General"       # 分类（如 Baseline, Smoothing, etc.）
    
    @abstractmethod
    def process(self, data: SpectrumData, **params) -> SpectrumData:
        """执行处理，返回处理后的 SpectrumData 对象
        
        Args:
            data: 输入的光谱数据
            **params: 插件参数
            
        Returns:
            SpectrumData: 处理后的新数据对象
        """
        pass
        
    @abstractmethod
    def get_params_schema(self) -> List[ParamSpec]:
        """返回参数规格列表，用于 UI 自动生成
        
        Returns:
            List[ParamSpec]: 参数定义列表
        """
        pass
        
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数合法性
        
        默认实现根据 get_params_schema 简单检查类型
        """
        schema = {p.name: p for p in self.get_params_schema()}
        
        for key, value in params.items():
            if key not in schema:
                # 允许传入额外参数，但记录日志可能更好
                continue
                
            spec = schema[key]
            # 简单的类型检查（可扩展）
            if spec.type == 'int' and not isinstance(value, int):
                # 尝试转换
                try:
                    int(value)
                except:
                    return False
            elif spec.type == 'float' and not isinstance(value, (int, float)):
                try:
                    float(value)
                except:
                    return False
        
        return True
