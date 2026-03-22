"""
插件参数自动生成对话框
"""

from typing import Dict, Any, List
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QSpinBox, QDoubleSpinBox, 
                            QLineEdit, QCheckBox, QComboBox, 
                            QPushButton, QFormLayout)
from PyQt6.QtCore import Qt

from ..plugins.base import ProcessingPlugin, ParamSpec

class PluginParamDialog(QDialog):
    """根据 ParamSpec 自动生成参数输入界面的对话框"""
    
    def __init__(self, plugin: ProcessingPlugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setWindowTitle(f"处理: {plugin.display_name}")
        self.resize(400, 300)
        
        self.param_widgets = {} # name -> widget
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 描述
        if self.plugin.description:
            desc_label = QLabel(self.plugin.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: gray; margin-bottom: 10px;")
            layout.addWidget(desc_label)
            
        # 表单区域
        form_layout = QFormLayout()
        schema = self.plugin.get_params_schema()
        
        if not schema:
            no_param_label = QLabel("此操作不需要额外参数。")
            no_param_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_param_label)
        else:
            for spec in schema:
                widget = self._create_widget_for_spec(spec)
                if widget:
                    self.param_widgets[spec.name] = widget
                    form_layout.addRow(f"{spec.label}:", widget)
                    # 添加 tooltip
                    if spec.description:
                        widget.setToolTip(spec.description)
                        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_ok = QPushButton("确定")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        
        layout.addLayout(btn_layout)
        
    def _create_widget_for_spec(self, spec: ParamSpec):
        """根据规格创建控件"""
        if spec.type == 'int':
            w = QSpinBox()
            if spec.min_val is not None: w.setMinimum(int(spec.min_val))
            else: w.setMinimum(-999999)
            
            if spec.max_val is not None: w.setMaximum(int(spec.max_val))
            else: w.setMaximum(999999)
            
            if spec.default is not None: w.setValue(int(spec.default))
            if spec.step is not None: w.setSingleStep(int(spec.step))
            return w
            
        elif spec.type == 'float':
            w = QDoubleSpinBox()
            if spec.min_val is not None: w.setMinimum(float(spec.min_val))
            else: w.setMinimum(-999999.0)
            
            if spec.max_val is not None: w.setMaximum(float(spec.max_val))
            else: w.setMaximum(999999.0)
            
            if spec.default is not None: w.setValue(float(spec.default))
            if spec.step is not None: w.setSingleStep(float(spec.step))
            return w
            
        elif spec.type == 'str':
            w = QLineEdit()
            if spec.default is not None: w.setText(str(spec.default))
            return w
            
        elif spec.type == 'bool':
            w = QCheckBox()
            if spec.default is not None: w.setChecked(bool(spec.default))
            return w
            
        elif spec.type == 'options':
            w = QComboBox()
            if spec.options:
                w.addItems(spec.options)
            if spec.default is not None and spec.default in spec.options:
                w.setCurrentText(spec.default)
            return w
            
        # TODO: range type (e.g. for baseline correction range)
        
        return None
        
    def get_params(self) -> Dict[str, Any]:
        """获取用户输入的参数"""
        params = {}
        for name, widget in self.param_widgets.items():
            if isinstance(widget, QSpinBox):
                params[name] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                params[name] = widget.value()
            elif isinstance(widget, QLineEdit):
                params[name] = widget.text()
            elif isinstance(widget, QCheckBox):
                params[name] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                params[name] = widget.currentText()
                
        return params
