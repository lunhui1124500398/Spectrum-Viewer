"""
处理链路管理核心模块
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Type
from datetime import datetime
from pathlib import Path
import importlib
import pkgutil
import inspect
from ..plugins.base import ProcessingPlugin

@dataclass
class ProcessingStep:
    """处理步骤记录"""
    step_type: str              # 插件名称 (plugin.name)
    timestamp: str              # ISO 格式的时间戳
    params: Dict[str, Any]      # 使用的参数
    plugin_version: str         # 插件版本
    description: str = ""       # 步骤描述（可选）
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingStep':
        return cls(**data)

class PluginRegistry:
    """插件注册表"""
    _plugins: Dict[str, ProcessingPlugin] = {}
    
    @classmethod
    def register(cls, plugin: ProcessingPlugin):
        """注册插件实例"""
        if plugin.name in cls._plugins:
            # 允许覆盖，但可以记录警告
            pass
        cls._plugins[plugin.name] = plugin
        
    @classmethod
    def get(cls, name: str) -> Optional[ProcessingPlugin]:
        """获取插件实例"""
        return cls._plugins.get(name)
        
    @classmethod
    def get_all(cls) -> Dict[str, ProcessingPlugin]:
        """获取所有已注册插件"""
        return cls._plugins.copy()
    
    @classmethod
    def discover_builtin(cls):
        """扫描并加载内置插件"""
        # 假设内置插件在 specview.plugins.builtin 包下
        import specview.plugins.builtin as builtin_pkg
        
        path = builtin_pkg.__path__
        prefix = builtin_pkg.__name__ + "."
        
        for _, name, _ in pkgutil.iter_modules(path, prefix):
            module = importlib.import_module(name)
            # 查找模块中的 ProcessingPlugin 子类
            for attr_name, attr_value in inspect.getmembers(module):
                if (inspect.isclass(attr_value) and 
                    issubclass(attr_value, ProcessingPlugin) and 
                    attr_value is not ProcessingPlugin):
                    # 实例化并注册
                    try:
                        plugin_instance = attr_value()
                        cls.register(plugin_instance)
                    except Exception as e:
                        print(f"Failed to register plugin from {name}: {e}")

class ProcessingChain:
    """处理链路管理器 - 记录数据的处理历史"""
    
    def __init__(self):
        # 键: data.filename (或唯一ID)，值: 处理步骤列表
        self._chains: Dict[str, List[ProcessingStep]] = {}
        
    def add_step(self, data_id: str, step: ProcessingStep):
        """添加处理步骤"""
        if data_id not in self._chains:
            self._chains[data_id] = []
        self._chains[data_id].append(step)
        
    def get_chain(self, data_id: str) -> List[ProcessingStep]:
        """获取指定数据的处理链路"""
        return self._chains.get(data_id, [])
        
    def clear_chain(self, data_id: str):
        """清除指定数据的处理链路"""
        if data_id in self._chains:
            del self._chains[data_id]
            
    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """序列化为字典"""
        result = {}
        for data_id, steps in self._chains.items():
            result[data_id] = [step.to_dict() for step in steps]
        return result
        
    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        
    @classmethod
    def from_dict(cls, data: Dict[str, List[Dict[str, Any]]]) -> 'ProcessingChain':
        """从字典反序列化"""
        chain = cls()
        for data_id, steps_data in data.items():
            steps = []
            for step_data in steps_data:
                steps.append(ProcessingStep.from_dict(step_data))
            chain._chains[data_id] = steps
        return chain
        
    @classmethod
    def from_json(cls, json_str: str) -> 'ProcessingChain':
        """从 JSON 反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)
