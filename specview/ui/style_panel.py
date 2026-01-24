"""
样式面板 - 调整绑图样式（增强版）
支持：实时预览、字体设置、主题切换、每条曲线独立样式
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDoubleSpinBox, QCheckBox, QColorDialog,
    QGroupBox, QFormLayout, QSlider, QLineEdit, QFileDialog,
    QMessageBox, QSpinBox, QTabWidget, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import json
from pathlib import Path


class ColorButton(QPushButton):
    """颜色选择按钮"""
    
    color_changed = pyqtSignal(str)  # 颜色字符串
    
    def __init__(self, color: str = "#e94560", parent=None):
        super().__init__(parent)
        self.setObjectName("colorButton")
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)
    
    def _update_style(self):
        # 计算对比色用于边框
        c = QColor(self._color)
        brightness = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        border_color = "#333333" if brightness > 128 else "#cccccc"
        
        self.setStyleSheet(f"""
            QPushButton#colorButton {{
                background-color: {self._color};
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                border-radius: 14px;
                border: 2px solid {border_color};
            }}
            QPushButton#colorButton:hover {{
                border-color: #e94560;
            }}
        """)
    
    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color), self, "选择颜色")
        if color.isValid():
            self._color = color.name()
            self._update_style()
            self.color_changed.emit(self._color)
    
    def get_color(self) -> str:
        return self._color
    
    def set_color(self, color: str):
        self._color = color
        self._update_style()


class LineStyleWidget(QWidget):
    """单条曲线样式控制"""
    
    style_changed = pyqtSignal(str, dict)  # filename, style_dict
    
    LINE_STYLES = {'实线': '-', '虚线': '--', '点线': ':', '点划线': '-.'}
    MARKER_STYLES = {'无': '', '圆形': 'o', '方形': 's', '三角': '^', '菱形': 'D'}
    
    def __init__(self, filename: str, color: str = "#e94560", parent=None):
        super().__init__(parent)
        self.filename = filename
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # 文件名标签
        self.label = QLabel(filename[:20] + "..." if len(filename) > 20 else filename)
        self.label.setToolTip(filename)
        self.label.setMinimumWidth(100)
        layout.addWidget(self.label)
        
        # 颜色按钮
        self.btn_color = ColorButton(color)
        self.btn_color.color_changed.connect(self._on_style_changed)
        layout.addWidget(self.btn_color)
        
        # 线宽
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(0.5, 5.0)
        self.spin_width.setSingleStep(0.5)
        self.spin_width.setValue(1.5)
        self.spin_width.setMaximumWidth(70)
        self.spin_width.valueChanged.connect(self._on_style_changed)
        layout.addWidget(self.spin_width)
        
        # 线型
        self.combo_style = QComboBox()
        self.combo_style.addItems(self.LINE_STYLES.keys())
        self.combo_style.setMaximumWidth(75)
        self.combo_style.currentTextChanged.connect(self._on_style_changed)
        layout.addWidget(self.combo_style)
    
    def _on_style_changed(self):
        style = {
            'color': self.btn_color.get_color(),
            'linewidth': self.spin_width.value(),
            'linestyle': self.LINE_STYLES[self.combo_style.currentText()]
        }
        self.style_changed.emit(self.filename, style)
    
    def get_style(self) -> dict:
        return {
            'color': self.btn_color.get_color(),
            'linewidth': self.spin_width.value(),
            'linestyle': self.LINE_STYLES[self.combo_style.currentText()]
        }
    
    def set_style(self, color: str = None, linewidth: float = None, linestyle: str = None):
        if color:
            self.btn_color.set_color(color)
        if linewidth:
            self.spin_width.setValue(linewidth)
        if linestyle:
            for name, style in self.LINE_STYLES.items():
                if style == linestyle:
                    self.combo_style.setCurrentText(name)
                    break


class StylePanel(QWidget):
    """样式调整面板（增强版）
    
    新功能：
    - 实时预览（修改即应用）
    - 字体样式和大小设置
    - 主题切换（暗色/亮色）
    - 每条曲线独立样式控制
    - 学术风配色方案
    
    Signals:
        style_changed: 当样式改变时发出
        theme_changed: 当主题改变时发出
        line_style_changed: 单条曲线样式改变
    """
    
    style_changed = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)  # 'dark' or 'light'
    line_style_changed = pyqtSignal(str, dict)  # filename, style
    
    # 学术风配色方案
    ACADEMIC_PALETTES = {
        'Nature': ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4', '#91D1C2'],
        'Science': ['#3B4992', '#EE0000', '#008B45', '#631879', '#008280', '#BB0021', '#5F559B'],
        'NEJM': ['#BC3C29', '#0072B5', '#E18727', '#20854E', '#7876B1', '#6F99AD', '#FFDC91'],
        'Lancet': ['#00468B', '#ED0000', '#42B540', '#0099B4', '#925E9F', '#FDAF91', '#AD002A'],
        '灰度': ['#000000', '#333333', '#666666', '#999999', '#CCCCCC'],
        '彩虹': ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3'],
    }
    
    # 字体选项
    FONT_FAMILIES = ['Arial', 'Times New Roman', 'Helvetica', 'Calibri', 'Microsoft YaHei']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StylePanel")
        self.live_preview = True  # 实时预览开关
        self.line_widgets: Dict[str, LineStyleWidget] = {}
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 标题和主题切换
        header_layout = QHBoxLayout()
        title = QLabel("🎨 样式设置")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 主题切换按钮
        self.btn_theme = QPushButton("🌙 暗色")
        self.btn_theme.setMaximumWidth(70)
        self.btn_theme.setCheckable(True)
        self.btn_theme.setChecked(True)  # 默认亮色，按下为暗色
        self.btn_theme.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.btn_theme)
        
        layout.addLayout(header_layout)
        
        # 实时预览开关
        self.check_live = QCheckBox("🔄 实时预览")
        self.check_live.setChecked(True)
        self.check_live.toggled.connect(lambda x: setattr(self, 'live_preview', x))
        layout.addWidget(self.check_live)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # ===== 全局样式标签页 =====
        global_tab = QScrollArea()
        global_tab.setWidgetResizable(True)
        global_widget = QWidget()
        global_layout = QVBoxLayout(global_widget)
        global_layout.setSpacing(6)
        
        # 配色方案
        palette_group = QGroupBox("配色方案")
        palette_layout = QFormLayout(palette_group)
        
        self.combo_palette = QComboBox()
        self.combo_palette.addItems(self.ACADEMIC_PALETTES.keys())
        self.combo_palette.currentTextChanged.connect(self._on_palette_changed)
        palette_layout.addRow("学术配色:", self.combo_palette)
        
        # 配色预览
        self.palette_preview = QLabel()
        self._update_palette_preview('Nature')
        palette_layout.addRow("", self.palette_preview)
        
        global_layout.addWidget(palette_group)
        
        # 字体设置
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QVBoxLayout(font_group)
        
        # 字体选择
        font_sel_layout = QHBoxLayout()
        font_sel_layout.addWidget(QLabel("字体族:"))
        self.combo_font = QComboBox()
        self.combo_font.addItems(self.FONT_FAMILIES)
        self.combo_font.currentTextChanged.connect(self._emit_if_live)
        font_sel_layout.addWidget(self.combo_font, 1)
        font_layout.addLayout(font_sel_layout)
        
        # 详细设置表格 (网格布局)
        grid = QGridLayout()
        grid.addWidget(QLabel("元素"), 0, 0)
        grid.addWidget(QLabel("大小"), 0, 1)
        grid.addWidget(QLabel("加粗"), 0, 2)
        grid.addWidget(QLabel("斜体"), 0, 3)
        
        # 1. 标题
        grid.addWidget(QLabel("标题"), 1, 0)
        self.spin_title_size = QSpinBox()
        self.spin_title_size.setRange(10, 28)
        self.spin_title_size.setValue(14)
        self.spin_title_size.valueChanged.connect(self._emit_if_live)
        grid.addWidget(self.spin_title_size, 1, 1)
        
        self.check_title_bold = QCheckBox()
        self.check_title_bold.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_title_bold, 1, 2)
        
        self.check_title_italic = QCheckBox()
        self.check_title_italic.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_title_italic, 1, 3)
        
        # 2. 轴标签 (X/Y Label)
        grid.addWidget(QLabel("轴标签"), 2, 0)
        self.spin_label_size = QSpinBox()
        self.spin_label_size.setRange(8, 24)
        self.spin_label_size.setValue(12)
        self.spin_label_size.valueChanged.connect(self._emit_if_live)
        grid.addWidget(self.spin_label_size, 2, 1)
        
        self.check_label_bold = QCheckBox()
        self.check_label_bold.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_label_bold, 2, 2)
        
        self.check_label_italic = QCheckBox()
        self.check_label_italic.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_label_italic, 2, 3)
        
        # 3. 刻度 (Ticks)
        grid.addWidget(QLabel("刻度"), 3, 0)
        self.spin_tick_size = QSpinBox()
        self.spin_tick_size.setRange(6, 20)
        self.spin_tick_size.setValue(10)
        self.spin_tick_size.valueChanged.connect(self._emit_if_live)
        grid.addWidget(self.spin_tick_size, 3, 1)
        
        self.check_tick_bold = QCheckBox()
        self.check_tick_bold.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_tick_bold, 3, 2)
        
        self.check_tick_italic = QCheckBox()
        self.check_tick_italic.toggled.connect(self._emit_if_live)
        grid.addWidget(self.check_tick_italic, 3, 3)
        
        font_layout.addLayout(grid)
        global_layout.addWidget(font_group)
        
        # 坐标轴设置
        axis_group = QGroupBox("坐标轴")
        axis_layout = QFormLayout(axis_group)
        
        self.edit_xlabel = QLineEdit("Wavelength (nm)")
        self.edit_xlabel.textChanged.connect(self._emit_if_live)
        axis_layout.addRow("X标签:", self.edit_xlabel)
        
        self.edit_ylabel = QLineEdit("Intensity (a.u.)")
        self.edit_ylabel.textChanged.connect(self._emit_if_live)
        axis_layout.addRow("Y标签:", self.edit_ylabel)
        
        self.edit_title = QLineEdit("")
        self.edit_title.setPlaceholderText("可选标题")
        self.edit_title.textChanged.connect(self._emit_if_live)
        axis_layout.addRow("标题:", self.edit_title)
        
        # X轴范围
        xlim_layout = QHBoxLayout()
        self.spin_xmin = QDoubleSpinBox()
        self.spin_xmin.setRange(0, 10000)
        self.spin_xmin.setDecimals(1)
        self.spin_xmin.valueChanged.connect(self._emit_if_live)
        xlim_layout.addWidget(self.spin_xmin)
        xlim_layout.addWidget(QLabel("-"))
        self.spin_xmax = QDoubleSpinBox()
        self.spin_xmax.setRange(0, 10000)
        self.spin_xmax.setDecimals(1)
        self.spin_xmax.valueChanged.connect(self._emit_if_live)
        xlim_layout.addWidget(self.spin_xmax)
        self.check_auto_x = QCheckBox("自动")
        self.check_auto_x.setChecked(True)
        self.check_auto_x.toggled.connect(self._on_auto_x_toggled)
        xlim_layout.addWidget(self.check_auto_x)
        axis_layout.addRow("X范围:", xlim_layout)
        
        # Y轴范围
        ylim_layout = QHBoxLayout()
        self.spin_ymin = QDoubleSpinBox()
        self.spin_ymin.setRange(-100000, 100000)
        self.spin_ymin.setDecimals(2)
        self.spin_ymin.valueChanged.connect(self._emit_if_live)
        ylim_layout.addWidget(self.spin_ymin)
        ylim_layout.addWidget(QLabel("-"))
        self.spin_ymax = QDoubleSpinBox()
        self.spin_ymax.setRange(-100000, 100000)
        self.spin_ymax.setDecimals(2)
        self.spin_ymax.valueChanged.connect(self._emit_if_live)
        ylim_layout.addWidget(self.spin_ymax)
        self.check_auto_y = QCheckBox("自动")
        self.check_auto_y.setChecked(True)
        self.check_auto_y.toggled.connect(self._on_auto_y_toggled)
        ylim_layout.addWidget(self.check_auto_y)
        axis_layout.addRow("Y范围:", ylim_layout)
        
        # 坐标轴线宽
        self.spin_axis_width = QDoubleSpinBox()
        self.spin_axis_width.setRange(0.5, 3.0)
        self.spin_axis_width.setSingleStep(0.5)
        self.spin_axis_width.setValue(1.0)
        self.spin_axis_width.valueChanged.connect(self._emit_if_live)
        axis_layout.addRow("轴线宽:", self.spin_axis_width)
        
        global_layout.addWidget(axis_group)
        
        # 显示选项
        display_group = QGroupBox("显示选项")
        display_layout = QVBoxLayout(display_group)
        
        self.check_grid = QCheckBox("显示网格")
        self.check_grid.setChecked(True)
        self.check_grid.toggled.connect(self._emit_if_live)
        display_layout.addWidget(self.check_grid)
        
        self.check_legend = QCheckBox("显示图例")
        self.check_legend.setChecked(True)
        self.check_legend.toggled.connect(self._emit_if_live)
        display_layout.addWidget(self.check_legend)
        
        self.check_minor_ticks = QCheckBox("显示次刻度")
        self.check_minor_ticks.setChecked(False)
        self.check_minor_ticks.toggled.connect(self._emit_if_live)
        display_layout.addWidget(self.check_minor_ticks)
        
        global_layout.addWidget(display_group)
        global_layout.addStretch()
        
        global_tab.setWidget(global_widget)
        self.tabs.addTab(global_tab, "全局")
        
        # ===== 曲线样式标签页 =====
        lines_tab = QWidget()
        lines_layout = QVBoxLayout(lines_tab)
        
        lines_header = QLabel("每条曲线独立设置")
        lines_header.setStyleSheet("font-weight: bold; padding: 4px;")
        lines_layout.addWidget(lines_header)
        
        # 曲线列表容器
        self.lines_container = QVBoxLayout()
        self.lines_container.setSpacing(2)
        lines_layout.addLayout(self.lines_container)
        
        # 无曲线提示
        self.no_lines_label = QLabel("请先导入并显示曲线")
        self.no_lines_label.setStyleSheet("color: #888; padding: 20px;")
        self.no_lines_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lines_layout.addWidget(self.no_lines_label)
        
        lines_layout.addStretch()
        
        self.tabs.addTab(lines_tab, "曲线")
        
        # ===== 模板标签页 =====
        template_tab = QWidget()
        template_layout = QVBoxLayout(template_tab)
        
        # 快速模板
        quick_group = QGroupBox("快速模板")
        quick_layout = QVBoxLayout(quick_group)
        
        for name in ['默认暗色', '发表级(白底)', '演示级', 'PPT友好']:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self._apply_quick_template(n))
            quick_layout.addWidget(btn)
        
        template_layout.addWidget(quick_group)
        
        # 保存/加载
        io_group = QGroupBox("模板文件")
        io_layout = QVBoxLayout(io_group)
        
        self.btn_save_template = QPushButton("💾 保存模板")
        self.btn_save_template.clicked.connect(self._save_template)
        io_layout.addWidget(self.btn_save_template)
        
        self.btn_load_template = QPushButton("📂 加载模板")
        self.btn_load_template.clicked.connect(self._load_template)
        io_layout.addWidget(self.btn_load_template)
        
        template_layout.addWidget(io_group)
        template_layout.addStretch()
        
        self.tabs.addTab(template_tab, "模板")
        
        layout.addWidget(self.tabs, 1)
        
        # 应用按钮（非实时预览时使用）
        self.btn_apply = QPushButton("✓ 应用样式")
        self.btn_apply.setObjectName("primary")
        self.btn_apply.clicked.connect(self._emit_style_changed)
        layout.addWidget(self.btn_apply)
        
        # 初始禁用范围输入
        self.spin_xmin.setEnabled(False)
        self.spin_xmax.setEnabled(False)
        self.spin_ymin.setEnabled(False)
        self.spin_ymax.setEnabled(False)
    
    def _connect_signals(self):
        """连接信号"""
        pass  # 大部分信号在创建时已连接
    
    def _toggle_theme(self):
        """切换主题"""
        if self.btn_theme.isChecked():
            self.btn_theme.setText("🌙 暗色")
            self.theme_changed.emit('light')
        else:
            self.btn_theme.setText("☀️ 亮色")
            self.theme_changed.emit('dark')
    
    def _update_palette_preview(self, name: str):
        """更新配色预览"""
        colors = self.ACADEMIC_PALETTES.get(name, [])
        html = ""
        for c in colors[:7]:
            html += f'<span style="background-color:{c}; color:{c};">██</span> '
        self.palette_preview.setText(html)
    
    def _on_palette_changed(self, name: str):
        """配色方案改变"""
        self._update_palette_preview(name)
        self._apply_palette_to_lines(name)
        self._emit_if_live()
    
    def _apply_palette_to_lines(self, palette_name: str):
        """将配色应用到所有曲线"""
        colors = self.ACADEMIC_PALETTES.get(palette_name, [])
        for i, (filename, widget) in enumerate(self.line_widgets.items()):
            if i < len(colors):
                widget.set_style(color=colors[i])
    
    def _on_auto_x_toggled(self, checked: bool):
        self.spin_xmin.setEnabled(not checked)
        self.spin_xmax.setEnabled(not checked)
        self._emit_if_live()
    
    def _on_auto_y_toggled(self, checked: bool):
        self.spin_ymin.setEnabled(not checked)
        self.spin_ymax.setEnabled(not checked)
        self._emit_if_live()
    
    def _emit_if_live(self):
        """如果实时预览开启则发送信号"""
        if self.live_preview:
            self._emit_style_changed()
    
    def _emit_style_changed(self):
        """发送样式改变信号"""
        config = self.get_style_config()
        self.style_changed.emit(config)
    
    def get_style_config(self) -> Dict[str, Any]:
        """获取当前样式配置"""
        # 收集每条曲线的样式
        line_styles = {}
        for filename, widget in self.line_widgets.items():
            line_styles[filename] = widget.get_style()
        
        # 确保字体大小至少为1，防止QFont警告
        label_size = max(1, self.spin_label_size.value())
        tick_size = max(1, self.spin_tick_size.value())
        title_size = max(1, self.spin_title_size.value())
        
        config = {
            'palette': self.combo_palette.currentText(),
            'font': {
                'family': self.combo_font.currentText(),
                'label_size': label_size,
                'tick_size': tick_size,
                'title_size': title_size,
                'title_bold': self.check_title_bold.isChecked(),
                'title_italic': self.check_title_italic.isChecked(),
                'label_bold': self.check_label_bold.isChecked(),
                'label_italic': self.check_label_italic.isChecked(),
                'tick_bold': self.check_tick_bold.isChecked(),
                'tick_italic': self.check_tick_italic.isChecked(),
            },
            'axes': {
                'xlabel': self.edit_xlabel.text(),
                'ylabel': self.edit_ylabel.text(),
                'title': self.edit_title.text(),
                'xlim': None if self.check_auto_x.isChecked() else (self.spin_xmin.value(), self.spin_xmax.value()),
                'ylim': None if self.check_auto_y.isChecked() else (self.spin_ymin.value(), self.spin_ymax.value()),
                'linewidth': self.spin_axis_width.value(),
            },
            'display': {
                'grid': self.check_grid.isChecked(),
                'legend': self.check_legend.isChecked(),
                'minor_ticks': self.check_minor_ticks.isChecked(),
            },
            'lines': line_styles,
        }
        return config
    
    def set_style_config(self, config: Dict[str, Any]):
        """设置样式配置"""
        # 暂时禁用实时预览以避免触发多次更新
        old_live = self.live_preview
        self.live_preview = False
        
        if 'palette' in config:
            self.combo_palette.setCurrentText(config['palette'])
        
        font = config.get('font', {})
        if 'family' in font:
            self.combo_font.setCurrentText(font['family'])
        if 'label_size' in font:
            self.spin_label_size.setValue(font['label_size'])
        if 'tick_size' in font:
            self.spin_tick_size.setValue(font['tick_size'])
        if 'title_size' in font:
            self.spin_title_size.setValue(font['title_size'])
            
        self.check_title_bold.setChecked(font.get('title_bold', False))
        self.check_title_italic.setChecked(font.get('title_italic', False))
        self.check_label_bold.setChecked(font.get('label_bold', False))
        self.check_label_italic.setChecked(font.get('label_italic', False))
        self.check_tick_bold.setChecked(font.get('tick_bold', False))
        self.check_tick_italic.setChecked(font.get('tick_italic', False))
        
        axes = config.get('axes', {})
        if 'xlabel' in axes:
            self.edit_xlabel.setText(axes['xlabel'])
        if 'ylabel' in axes:
            self.edit_ylabel.setText(axes['ylabel'])
        if 'title' in axes:
            self.edit_title.setText(axes['title'])
        if axes.get('xlim') is None:
            self.check_auto_x.setChecked(True)
        else:
            self.check_auto_x.setChecked(False)
            self.spin_xmin.setValue(axes['xlim'][0])
            self.spin_xmax.setValue(axes['xlim'][1])
        if axes.get('ylim') is None:
            self.check_auto_y.setChecked(True)
        else:
            self.check_auto_y.setChecked(False)
            self.spin_ymin.setValue(axes['ylim'][0])
            self.spin_ymax.setValue(axes['ylim'][1])
        if 'linewidth' in axes:
            self.spin_axis_width.setValue(axes['linewidth'])
        
        display = config.get('display', {})
        if 'grid' in display:
            self.check_grid.setChecked(display['grid'])
        if 'legend' in display:
            self.check_legend.setChecked(display['legend'])
        if 'minor_ticks' in display:
            self.check_minor_ticks.setChecked(display['minor_ticks'])
        
        self.live_preview = old_live
    
    def update_line_list(self, filenames: List[str], colors: List[str] = None):
        """更新曲线列表
        
        Args:
            filenames: 文件名列表
            colors: 对应的颜色列表
        """
        # 清除旧的
        for widget in self.line_widgets.values():
            widget.deleteLater()
        self.line_widgets.clear()
        
        # 清除布局中的控件
        while self.lines_container.count():
            item = self.lines_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not filenames:
            self.no_lines_label.show()
            return
        
        self.no_lines_label.hide()
        
        # 使用当前配色
        palette = self.ACADEMIC_PALETTES.get(self.combo_palette.currentText(), [])
        if colors is None:
            colors = palette
        
        for i, filename in enumerate(filenames):
            color = colors[i % len(colors)] if colors else '#e94560'
            widget = LineStyleWidget(filename, color)
            widget.style_changed.connect(self._on_line_style_changed)
            self.lines_container.addWidget(widget)
            self.line_widgets[filename] = widget
    
    def _on_line_style_changed(self, filename: str, style: dict):
        """单条曲线样式改变"""
        self.line_style_changed.emit(filename, style)
    
    def get_line_colors(self) -> List[str]:
        """获取当前配色方案的颜色列表"""
        return self.ACADEMIC_PALETTES.get(self.combo_palette.currentText(), ['#e94560'])
    
    def _apply_quick_template(self, name: str):
        """应用快速模板"""
        templates = {
            '默认暗色': {
                'palette': 'Nature',
                'font': {'family': 'Arial', 'label_size': 12, 'tick_size': 10, 'title_size': 14},
                'axes': {'xlabel': 'Wavelength (nm)', 'ylabel': 'Intensity (a.u.)', 'title': '', 'xlim': None, 'ylim': None, 'linewidth': 1.0},
                'display': {'grid': True, 'legend': True, 'minor_ticks': False},
            },
            '发表级(白底)': {
                'palette': '灰度',
                'font': {'family': 'Arial', 'label_size': 14, 'tick_size': 12, 'title_size': 16},
                'axes': {'xlabel': 'Wavelength (nm)', 'ylabel': 'Intensity (a.u.)', 'title': '', 'xlim': None, 'ylim': None, 'linewidth': 1.5},
                'display': {'grid': False, 'legend': True, 'minor_ticks': True},
            },
            '演示级': {
                'palette': 'Science',
                'font': {'family': 'Arial', 'label_size': 16, 'tick_size': 14, 'title_size': 20},
                'axes': {'xlabel': 'Wavelength (nm)', 'ylabel': 'Intensity (a.u.)', 'title': '', 'xlim': None, 'ylim': None, 'linewidth': 1.5},
                'display': {'grid': True, 'legend': True, 'minor_ticks': False},
            },
            'PPT友好': {
                'palette': 'NEJM',
                'font': {
                    'family': 'Calibri', 'label_size': 18, 'tick_size': 14, 'title_size': 22,
                    'title_bold': True, 'label_bold': True, 'tick_bold': True
                },
                'axes': {'xlabel': 'Wavelength (nm)', 'ylabel': 'Intensity (a.u.)', 'title': '', 'xlim': None, 'ylim': None, 'linewidth': 2.0},
                'display': {'grid': False, 'legend': True, 'minor_ticks': False},
            },
        }
        
        if name in templates:
            self.set_style_config(templates[name])
            # 如果是白底模板，切换到亮色主题
            if '白底' in name or 'PPT' in name:
                self.btn_theme.setChecked(True)
                self._toggle_theme()
            self._emit_style_changed()
    
    def _save_template(self):
        """保存模板"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存模板", "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        if filepath:
            if not filepath.endswith('.json'):
                filepath += '.json'
            
            config = self.get_style_config()
            config['_meta'] = {
                'name': Path(filepath).stem,
                'version': '2.0'
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(self, "保存成功", f"模板已保存到:\n{filepath}")
    
    def _load_template(self):
        """加载模板"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载模板", "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.set_style_config(config)
                self._emit_style_changed()
                QMessageBox.information(self, "加载成功", "模板已应用")
            except Exception as e:
                QMessageBox.warning(self, "加载失败", f"无法加载模板:\n{e}")
    
    def update_axis_ranges(self, xlim: tuple, ylim: tuple):
        """更新坐标轴范围显示（从绑图同步）"""
        self.spin_xmin.setValue(xlim[0])
        self.spin_xmax.setValue(xlim[1])
        self.spin_ymin.setValue(ylim[0])
        self.spin_ymax.setValue(ylim[1])
