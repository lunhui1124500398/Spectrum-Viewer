"""
绘图组件 - 基于Matplotlib的光谱绑图（增强版）
支持：主题切换、字体设置、每条曲线独立样式
"""

from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QSizePolicy, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator, NullLocator
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.text import Text

from ..core.data_model import SpectrumData


class SafeNavigationToolbar(NavigationToolbar):
    """自定义导航工具栏，修复 QFont 警告问题 并 自动适配图标颜色
    
    问题原因：
    1. NavigationToolbar2QT 内部的 _message_label 及其他控件在鼠标悬停时可能使用未正确初始化的字体（大小为 -1）。
    2. Matplotlib 默认图标通常是黑色或白色，需要根据深色/亮色主题自动反转。
    
    解决方案：
    1. 初始化时为所有子控件设置安全字体
    2. 安装事件过滤器，在 ToolTip 事件前确保字体正确
    3. 覆盖 set_message 方法确保消息标签字体正确
    4. 添加 update_icons 方法，根据背景色自动反转图标颜色
    """
    
    def __init__(self, canvas, parent, coordinates=True):
        # 安全字体定义
        self._safe_font = QFont("Segoe UI", 10)
        
        super().__init__(canvas, parent, coordinates=coordinates)
        
        # 设置工具栏自身的字体
        self.setFont(self._safe_font)
        
        # 为所有子控件设置字体并安装事件过滤器
        self._fix_all_child_fonts()
    
    def _fix_all_child_fonts(self):
        """修复所有子控件的字体"""
        from PyQt6.QtWidgets import QWidget
        
        # 遍历所有子控件
        for child in self.findChildren(QWidget):
            # 设置安全字体
            child.setFont(self._safe_font)
            # 安装事件过滤器
            child.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 在 ToolTip 事件前确保字体正确"""
        from PyQt6.QtCore import QEvent
        
        # 在 ToolTip 事件或 Enter/Leave 事件前修复字体
        if event.type() in (QEvent.Type.ToolTip, QEvent.Type.Enter, QEvent.Type.Leave):
            # 确保对象的字体大小为正数
            current_font = obj.font()
            if current_font.pointSize() <= 0:
                obj.setFont(self._safe_font)
        
        return super().eventFilter(obj, event)
    
    def set_message(self, s):
        """覆盖 set_message 方法，确保消息标签使用正确的字体"""
        # 先确保 _message_label 有正确的字体设置
        if hasattr(self, '_message_label') and self._message_label is not None:
            current_font = self._message_label.font()
            if current_font.pointSize() <= 0:
                self._message_label.setFont(self._safe_font)
        
        # 调用父类方法
        super().set_message(s)
    
    def childEvent(self, event):
        """当有新的子控件添加时，确保其字体正确"""
        super().childEvent(event)
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.ChildAdded:
            child = event.child()
            if hasattr(child, 'setFont'):
                child.setFont(self._safe_font)
            if hasattr(child, 'installEventFilter'):
                child.installEventFilter(self)

    def update_icons(self, dark_mode: bool):
        """
        根据主题更新图标颜色
        Matplotlib 的默认图标是一组 PNG 图像。
        如果是深色模式 (dark_mode=True)，我们需要白色图标。
        如果是亮色模式 (dark_mode=False)，我们需要黑色图标。
        
        简单的逻辑：
        检查某个图标像素，如果需要反转则反转。
        这里使用 QIcon 重新生成的策略。
        """
        from PyQt6.QtGui import QIcon, QPixmap, QImage, QPainter, QColor
        from PyQt6.QtCore import Qt

        target_color = Qt.GlobalColor.white if dark_mode else Qt.GlobalColor.black
        
        for action in self.actions():
            icon = action.icon()
            if icon.isNull():
                continue
            
            # 获取不同尺寸的 pixmap 并处理
            # 通常工具栏图标大小为 24x24 或类似
            sizes = icon.availableSizes()
            if not sizes:
                continue
                
            new_icon = QIcon()
            
            for size in sizes:
                pixmap = icon.pixmap(size)
                image = pixmap.toImage()
                
                # 简单的反色处理：将非透明像素设置为目标颜色
                # 这是一个简化的假设，假设图标是单色的
                if image.format() != QImage.Format.Format_ARGB32:
                    image = image.convertToFormat(QImage.Format.Format_ARGB32)
                
                width = image.width()
                height = image.height()
                
                # 检查中心点像素看看是否需要处理 (优化性能)
                # 但由于我们需要确保颜色正确，最好是重新着色
                
                for y in range(height):
                    for x in range(width):
                        pixel = image.pixelColor(x, y)
                        if pixel.alpha() > 0:
                            # 保留 alpha 通道，修改 RGB
                            new_color = QColor(target_color)
                            new_color.setAlpha(pixel.alpha())
                            image.setPixelColor(x, y, new_color)
                
                new_icon.addPixmap(QPixmap.fromImage(image))
            
            action.setIcon(new_icon)


class PlotCanvas(FigureCanvas):
    """Matplotlib画布组件（增强版）"""
    
    # 鼠标位置信号
    mouse_moved = pyqtSignal(float, float)  # wavelength, intensity
    
    # 曲线点击信号
    curve_clicked = pyqtSignal(str)  # filename
    
    # 学术配色 - 与style_panel保持一致
    ACADEMIC_PALETTES = {
        'Nature': ['#E64B35', '#4DBBD5', '#00A087', '#3C5488', '#F39B7F', '#8491B4', '#91D1C2'],
        'Science': ['#3B4992', '#EE0000', '#008B45', '#631879', '#008280', '#BB0021', '#5F559B'],
        'NEJM': ['#BC3C29', '#0072B5', '#E18727', '#20854E', '#7876B1', '#6F99AD', '#FFDC91'],
        'Lancet': ['#00468B', '#ED0000', '#42B540', '#0099B4', '#925E9F', '#FDAF91', '#AD002A'],
        '灰度': ['#000000', '#333333', '#666666', '#999999', '#CCCCCC'],
        '彩虹': ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3'],
    }
    
    def __init__(self, parent=None, dark_mode=True):
        # 创建Figure
        self.fig = Figure(figsize=(8, 6), dpi=100)
        super().__init__(self.fig)
        
        self.dark_mode = dark_mode
        self.current_palette = 'Nature'
        
        # 字体设置
        self.font_family = 'Arial'
        self.label_size = 12
        self.tick_size = 10
        self.title_size = 14
        self.legend_size = 10  # 新增图例字体大小
        self.axis_linewidth = 1.0
        
        # 检测可用的中文字体（缓存结果）
        self._chinese_font = self._detect_chinese_font()
        
        # 配置支持中文字体
        self._configure_chinese_fonts()
        
        self._setup_style()
        
        # 创建Axes
        self.ax = self.fig.add_subplot(111)
        self._setup_axes()
        
        # 存储绑制的线条
        self.lines: Dict[str, Line2D] = {}  # filename -> Line2D
        self.data_map: Dict[str, SpectrumData] = {}  # filename -> SpectrumData
        
        # 鼠标跟踪
        self.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.mpl_connect('button_press_event', self._on_mouse_click)
        self.mpl_connect('pick_event', self._on_pick)
        
        # 设置尺寸策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _on_mouse_click(self, event):
        """鼠标点击事件"""
        # 处理双击 - 图例编辑
        if event.dblclick and event.inaxes == self.ax:
            legend = self.ax.get_legend()
            if legend and legend.get_visible():
                try:
                    # 检查点击是否在图例范围内
                    bbox = legend.get_window_extent()
                    if bbox.contains(event.x, event.y):
                        self._edit_legend_label()
                except:
                    pass

    # def _on_double_click(self, event): # Removed invalid signal handler
    
    def _edit_legend_label(self):
        """编辑图例标签对话框"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QDialogButtonBox, QAbstractItemView, QInputDialog
        
        # 弹出一个列表让用户选择要重命名的曲线，或者如果只有一个直接弹输入框
        if not self.lines:
            return
            
        filenames = list(self.lines.keys())
        current_labels = [line.get_label() for line in self.lines.values()]
        
        item, ok = QInputDialog.getItem(self, "编辑图例", "选择要重命名的曲线:", 
                                      [f"{l} ({f})" for l, f in zip(current_labels, filenames)], 0, False)
        
        if ok and item:
            # 找到选中的索引
            idx = [f"{l} ({f})" for l, f in zip(current_labels, filenames)].index(item)
            filename = filenames[idx]
            current_label = current_labels[idx]
            
            new_label, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=current_label)
            if ok:
                line = self.lines[filename]
                line.set_label(new_label)
                # 刷新图例
                self.ax.legend(loc='best', framealpha=0.8, fontsize=self.tick_size)
                self.draw()

    def _on_pick(self, event):
        """处理拾取事件 (点击曲线)"""
        if isinstance(event.artist, Line2D):
            # 查找对应的文件名
            for filename, line in self.lines.items():
                if line == event.artist:
                    self.curve_clicked.emit(filename)
                    break 

    def _configure_chinese_fonts(self):
        """配置Matplotlib以支持中文显示"""
        import platform
        system = platform.system()
        
        # 常见中文字体列表 (按优先级)
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'PingFang SC', 'WenQuanYi Micro Hei', 'SimSun']
        
        # 查找系统可用字体
        from matplotlib.font_manager import fontManager
        available_fonts = set(f.name for f in fontManager.ttflist)
        
        found_font = None
        for font in chinese_fonts:
            if font in available_fonts:
                found_font = font
                break
        
        # 设置全局字体回退，确保中文不乱码
        if found_font:
            # 优先使用用户设定的字体，然后是中文字体作为fallback
            matplotlib.rcParams['font.sans-serif'] = [self.font_family, found_font, 'Arial', 'DejaVu Sans']
            matplotlib.rcParams['axes.unicode_minus'] = False # 解决负号显示为方块的问题
    
    def _setup_style(self):
        """设置样式"""
        if self.dark_mode:
            self.fig.patch.set_facecolor('#1a1a2e')
        else:
            self.fig.patch.set_facecolor('white')
    
    def _setup_axes(self):
        """设置坐标轴样式"""
        if self.dark_mode:
            self.ax.set_facecolor('#16213e')
            spine_color = '#0f3460'
            text_color = '#e0e0e0'
            grid_color = '#0f3460'
        else:
            self.ax.set_facecolor('white')
            spine_color = '#333333'
            text_color = '#333333'
            grid_color = '#cccccc'
        
        for spine in self.ax.spines.values():
            spine.set_color(spine_color)
            spine.set_linewidth(self.axis_linewidth)
        
        self.ax.tick_params(colors=text_color, labelsize=self.tick_size)
        self.ax.xaxis.label.set_color(text_color)
        self.ax.yaxis.label.set_color(text_color)
        self.ax.title.set_color(text_color)
        
        # 设置字体
        # 设置字体 (不强制fontfamily，允许回退)
        self.ax.set_xlabel('Wavelength (nm)', fontsize=self.label_size)
        self.ax.set_ylabel('Intensity (a.u.)', fontsize=self.label_size)
        self.ax.grid(True, alpha=0.3, color=grid_color)
        
        # 强制设置刻度字体大小，防止QFont warning
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontsize(self.tick_size)
    
    def set_theme(self, dark_mode: bool):
        """切换主题"""
        self.dark_mode = dark_mode
        self._setup_style()
        
        # 需要重新设置axes
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xlabel = self.ax.get_xlabel()
        ylabel = self.ax.get_ylabel()
        title = self.ax.get_title()
        
        # 保存线条数据
        line_data = {}
        for filename, line in self.lines.items():
            line_data[filename] = {
                'color': line.get_color(),
                'linewidth': line.get_linewidth(),
                'linestyle': line.get_linestyle(),
            }
        
        # 清除并重建
        self.ax.clear()
        self._setup_axes()
        
        # 重新绘制线条
        for filename, data in self.data_map.items():
            style = line_data.get(filename, {})
            line, = self.ax.plot(
                data.wavelength, data.intensity_avg,
                color=style.get('color'),
                linewidth=style.get('linewidth', 1.5),
                linestyle=style.get('linestyle', '-'),
                label=filename.replace('.xls', ''),
                picker=5  # 确保重建时保留picker
            )
            self.lines[filename] = line
        
        # 恢复设置
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.ax.set_xlabel(xlabel, fontsize=self.label_size)
        self.ax.set_ylabel(ylabel, fontsize=self.label_size)
        self.ax.set_title(title, fontsize=self.title_size)
        
        if self.lines:
            self.ax.legend(loc='best', framealpha=0.8)
        
        self.draw()
    
    def _get_font_list(self, user_font: str) -> List[str]:
        """获取字体回退列表"""
        # 常见中文字体列表 (按优先级)
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'PingFang SC', 'WenQuanYi Micro Hei', 'SimSun']
        
        # 构造列表：用户字体 -> 中文字体 -> 通用字体
        font_list = [user_font]
        font_list.extend(chinese_fonts)
        font_list.extend(['Arial', 'DejaVu Sans', 'sans-serif'])
        
        # 移除重复项并保持顺序
        seen = set()
        final_list = []
        for f in font_list:
            if f not in seen:
                seen.add(f)
                final_list.append(f)
        return final_list
    
    def _detect_chinese_font(self) -> str:
        """检测系统中可用的中文字体
        
        Returns:
            第一个可用的中文字体名称，如果没有则返回None
        """
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'PingFang SC', 
                         'WenQuanYi Micro Hei', 'SimSun', 'FangSong', 'KaiTi']
        
        from matplotlib.font_manager import fontManager
        available_fonts = set(f.name for f in fontManager.ttflist)
        
        for font in chinese_fonts:
            if font in available_fonts:
                return font
        
        return None

    def _update_font_rcparams(self, font_family: str):
        """更新matplotlib rcParams以确保中文字体回退正常工作
        
        此方法在预览和应用样式时都会调用，确保中文字符能正确显示。
        
        关键设置:
        - font.family = 'sans-serif' 让matplotlib使用sans-serif字体族
        - font.sans-serif = [用户字体, 中文字体, 通用字体] 定义回退顺序
        """
        # 常见中文字体列表 (按优先级)
        chinese_fonts = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'PingFang SC', 'WenQuanYi Micro Hei', 'SimSun']
        
        # 查找系统可用的中文字体
        from matplotlib.font_manager import fontManager
        available_fonts = set(f.name for f in fontManager.ttflist)
        
        # 找到所有可用的中文字体
        available_chinese = [f for f in chinese_fonts if f in available_fonts]
        
        # 构建字体回退列表
        font_list = [font_family]
        font_list.extend(available_chinese)  # 只添加可用的中文字体
        font_list.extend(['Arial', 'DejaVu Sans', 'sans-serif'])
        
        # 移除重复项
        seen = set()
        unique_list = []
        for f in font_list:
            if f not in seen:
                seen.add(f)
                unique_list.append(f)
        
        # 设置rcParams - 关键是设置font.family为'sans-serif'
        # 这样matplotlib会使用font.sans-serif列表进行字体查找和回退
        matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['font.sans-serif'] = unique_list
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        # 强制重新构建font cache以确保新设置生效
        try:
            from matplotlib.font_manager import _rebuild
            _rebuild()
        except:
            pass  # 旧版本可能没有这个函数

    def apply_style_config(self, config: Dict[str, Any]):
        """应用完整的样式配置
        
        支持:
        - 全局字体设置 (font.family)
        - 每个元素可独立覆盖字体 (font.title_font, font.label_font, font.tick_font, font.legend_font)
        - 中文字体回退始终生效
        """
        # 字体设置
        font_config = config.get('font', {})
        if 'family' in font_config:
            self.font_family = font_config['family']
        if 'label_size' in font_config:
            self.label_size = max(1, font_config['label_size'])  # 确保至少为1
        if 'tick_size' in font_config:
            self.tick_size = max(1, font_config['tick_size'])
        if 'title_size' in font_config:
            self.title_size = max(1, font_config['title_size'])
        if 'legend_size' in font_config:
            self.legend_size = max(1, font_config['legend_size'])
        
        # 更新rcParams确保中文字体回退正常工作（修复预览时中文不显示的问题）
        self._update_font_rcparams(self.font_family)
        
        # 获取每个元素的字体（支持独立覆盖）
        # 如果未设置独立字体，则使用全局字体
        title_font = font_config.get('title_font') or self.font_family
        label_font = font_config.get('label_font') or self.font_family
        tick_font = font_config.get('tick_font') or self.font_family
        legend_font = font_config.get('legend_font') or self.font_family
        
        # 为了让中文字体回退正常工作，我们需要更新rcParams并且在设置字体时使用'sans-serif'
        # 这样matplotlib会根据rcParams['font.sans-serif']列表进行字体查找和回退
        # 用户指定的字体在该列表中排在最前面，所以会优先使用
        
        # 如果用户选择了独立字体，更新rcParams以该字体为最高优先级
        # 注意：这里我们使用字体名称列表，但matplotlib对列表的回退支持有限
        # 因此我们依赖rcParams全局设置来确保中文回退
        
        # 字体样式 (分别获取)
        title_weight = 'bold' if font_config.get('title_bold', False) else 'normal'
        title_style = 'italic' if font_config.get('title_italic', False) else 'normal'
        
        label_weight = 'bold' if font_config.get('label_bold', False) else 'normal'
        label_style = 'italic' if font_config.get('label_italic', False) else 'normal'
        
        tick_weight = 'bold' if font_config.get('tick_bold', False) else 'normal'
        tick_style = 'italic' if font_config.get('tick_italic', False) else 'normal'

        legend_weight = 'bold' if font_config.get('legend_bold', False) else 'normal'
        legend_style = 'italic' if font_config.get('legend_italic', False) else 'normal'
        
        # 坐标轴设置
        axes_config = config.get('axes', {})
        if 'linewidth' in axes_config:
            self.axis_linewidth = axes_config['linewidth']
        
        # 更新坐标轴样式
        for spine in self.ax.spines.values():
            spine.set_linewidth(self.axis_linewidth)
        
        # 更新刻度样式 (包括大小和宽度)
        self.ax.tick_params(labelsize=self.tick_size, width=self.axis_linewidth)
        # 更新次刻度宽度 (通常比主刻度细一点，或者设为相同)
        self.ax.tick_params(which='minor', width=self.axis_linewidth * 0.6)
        
        # 确定每个元素使用的字体
        # 优先使用用户指定的per-element字体，然后是全局字体
        # 如果指定的字体不支持中文且文本包含中文，则使用中文字体
        def get_font_for_text(user_font: str, text: str = "") -> str:
            """为文本选择合适的字体
            
            Args:
                user_font: 用户指定的字体
                text: 要显示的文本
            
            Returns:
                应该使用的字体名称
            """
            # 检查文本是否包含中文字符
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            
            # 如果文本包含中文且用户选择的不是中文字体
            chinese_capable_fonts = {'Microsoft YaHei', 'SimHei', 'SimSun', 'FangSong', 
                                     'KaiTi', 'Heiti TC', 'PingFang SC', 'WenQuanYi Micro Hei'}
            
            if has_chinese and user_font not in chinese_capable_fonts:
                # 返回中文字体以确保正确显示
                return self._chinese_font or user_font
            
            return user_font
        
        if 'xlabel' in axes_config:
            xlabel_text = axes_config['xlabel']
            xlabel_font = get_font_for_text(label_font, xlabel_text)
            self.ax.set_xlabel(xlabel_text, fontsize=self.label_size, 
                              fontweight=label_weight, fontstyle=label_style, fontname=xlabel_font)
        if 'ylabel' in axes_config:
            ylabel_text = axes_config['ylabel']
            ylabel_font = get_font_for_text(label_font, ylabel_text)
            self.ax.set_ylabel(ylabel_text, fontsize=self.label_size, 
                              fontweight=label_weight, fontstyle=label_style, fontname=ylabel_font)
        if 'title' in axes_config:
            title_text = axes_config['title']
            title_font_name = get_font_for_text(title_font, title_text)
            self.ax.set_title(title_text, fontsize=self.title_size, 
                             fontweight=title_weight, fontstyle=title_style, fontname=title_font_name)
        
        # 应用字体样式到刻度标签（通常是数字，不需要中文字体）
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_fontsize(self.tick_size)  # 必须设置fontsize，否则可能为-1导致QFont警告
            label.set_fontweight(tick_weight)
            label.set_fontstyle(tick_style)
            # 刻度标签使用用户指定的字体
            label.set_fontname(tick_font)
            
        if axes_config.get('xlim'):
            self.ax.set_xlim(axes_config['xlim'])
        if axes_config.get('ylim'):
            self.ax.set_ylim(axes_config['ylim'])
            
        # 应用曲线样式 (颜色/线宽/线型)
        lines_config = config.get('lines', {})
        for filename, style in lines_config.items():
            if filename in self.lines:
                line = self.lines[filename]
                if 'color' in style:
                    line.set_color(style['color'])
                if 'linewidth' in style:
                    line.set_linewidth(style['linewidth'])
                if 'linestyle' in style:
                    line.set_linestyle(style['linestyle'])
        
        # 显示选项 - 修复网格控制
        display_config = config.get('display', {})
        show_grid = display_config.get('grid', True)
        self.toggle_grid(show_grid)

        # 次刻度控制
        if display_config.get('minor_ticks'):
            self.ax.xaxis.set_minor_locator(AutoMinorLocator())
            self.ax.yaxis.set_minor_locator(AutoMinorLocator())
        else:
            self.ax.xaxis.set_minor_locator(NullLocator())
            self.ax.yaxis.set_minor_locator(NullLocator())
        
        # 图例显示
        show_legend = display_config.get('legend', True)
        
        if show_legend:
            # 总是重新创建图例以确保颜色和样式同步
            if self.lines:
                frameon = display_config.get('legend_frame', True)
                legend = self.ax.legend(loc='best', frameon=frameon, framealpha=0.8, fontsize=self.legend_size)
                legend.set_visible(True)
                legend.set_draggable(True)
                # 更新图例字体样式
                # 使用用户指定的legend_font，如果文件名包含中文则自动使用中文字体
                for text in legend.get_texts():
                    legend_text = text.get_text()
                    legend_font_name = get_font_for_text(legend_font, legend_text)
                    text.set_fontsize(self.legend_size)
                    text.set_fontweight(legend_weight)
                    text.set_fontstyle(legend_style)
                    text.set_fontname(legend_font_name)

        else:
            legend = self.ax.get_legend()
            if legend:
                legend.set_visible(False)
            
        self.draw()

    def toggle_grid(self, show: Optional[bool] = None):
        """切换网格显示 (带颜色修正)"""
        # 如果未指定，则切换状态
        if show is None:
            try:
                gridlines = self.ax.xaxis.get_gridlines()
                show = not gridlines[0].get_visible() if gridlines else True
            except:
                show = True
                
        # 强制清除再设置，确保颜色正确
        self.ax.grid(False)
        if show:
            grid_color = '#0f3460' if self.dark_mode else '#cccccc'
            self.ax.grid(True, alpha=0.3, color=grid_color)
        self.draw()
    
    def toggle_legend(self, show: Optional[bool] = None):
        """切换图例显示"""
        legend = self.ax.get_legend()
        if legend is not None:
            if show is None:
                show = not legend.get_visible()
            legend.set_visible(show)
            self.draw()
    
    def _on_mouse_move(self, event):
        """鼠标移动事件"""
        if event.inaxes == self.ax:
            self.mouse_moved.emit(event.xdata, event.ydata)
    
    def clear_plot(self):
        """清除所有绑制内容"""
        self.ax.clear()
        self._setup_axes()
        self.lines.clear()
        self.data_map.clear()
        self.draw()
    
    def plot_spectrum(self, data: SpectrumData, 
                      color: Optional[str] = None,
                      linewidth: float = 1.5,
                      linestyle: str = '-',
                      label: Optional[str] = None,
                      clear_first: bool = True) -> Line2D:
        """绑制单个光谱"""
        if clear_first:
            self.clear_plot()
        
        label = label or data.filename.replace('.xls', '')
        
        line, = self.ax.plot(
            data.wavelength, 
            data.intensity_avg,
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            label=label,
            picker=5  # 启用拾取，容差5点
        )
        
        self.lines[data.filename] = line
        self.data_map[data.filename] = data
        
        # 更新图例
        if len(self.lines) > 0:
            self.ax.legend(loc='best', framealpha=0.8)
        
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()
        
        return line
    
    def plot_multiple(self, data_list: List[SpectrumData],
                      colors: Optional[List[str]] = None,
                      linewidth: float = 1.5,
                      linestyle: str = '-'):
        """绑制多个光谱（叠加）"""
        self.clear_plot()
        
        # 默认颜色循环
        if colors is None:
            colors = self.get_color_cycle(len(data_list))
        
        for i, data in enumerate(data_list):
            color = colors[i] if i < len(colors) else None
            self.plot_spectrum(
                data, 
                color=color, 
                linewidth=linewidth,
                linestyle=linestyle,
                clear_first=False
            )
        
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()
        
        return list(self.lines.keys())
    
    def get_color_cycle(self, n: int, palette_name: str = None) -> List[str]:
        """获取颜色循环"""
        if palette_name is None:
            palette_name = self.current_palette
        
        palette = self.ACADEMIC_PALETTES.get(palette_name, self.ACADEMIC_PALETTES['Nature'])
        
        if n <= len(palette):
            return palette[:n]
        else:
            # 循环使用
            return [palette[i % len(palette)] for i in range(n)]
    
    def set_palette(self, palette_name: str):
        """设置当前配色方案"""
        self.current_palette = palette_name
    
    def set_xlim(self, xmin: Optional[float] = None, xmax: Optional[float] = None):
        """设置X轴范围"""
        current = self.ax.get_xlim()
        xmin = xmin if xmin is not None else current[0]
        xmax = xmax if xmax is not None else current[1]
        self.ax.set_xlim(xmin, xmax)
        self.draw()
    
    def set_ylim(self, ymin: Optional[float] = None, ymax: Optional[float] = None):
        """设置Y轴范围"""
        current = self.ax.get_ylim()
        ymin = ymin if ymin is not None else current[0]
        ymax = ymax if ymax is not None else current[1]
        self.ax.set_ylim(ymin, ymax)
        self.draw()
    
    def set_xlabel(self, label: str):
        """设置X轴标签"""
        self.ax.set_xlabel(label, fontsize=self.label_size, fontfamily=self.font_family)
        self.draw()
    
    def set_ylabel(self, label: str):
        """设置Y轴标签"""
        self.ax.set_ylabel(label, fontsize=self.label_size, fontfamily=self.font_family)
        self.draw()
    
    def get_current_xlim(self) -> Tuple[float, float]:
        """获取当前X轴范围"""
        return self.ax.get_xlim()
    
    def get_current_ylim(self) -> Tuple[float, float]:
        """获取当前Y轴范围"""
        return self.ax.get_ylim()
    
    def reset_view(self):
        """重置视图到自动范围"""
        self.ax.relim()
        self.ax.autoscale_view()
        self.draw()
    
    def save_figure(self, filepath: str, dpi: int = 300, transparent: bool = False):
        """保存图像"""
        if transparent:
            self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight',
                            facecolor='none', edgecolor='none', transparent=True)
        else:
            self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight',
                            facecolor=self.fig.get_facecolor(), edgecolor='none')

    def update_line_style(self, filename: str, color: Optional[str] = None, 
                          linewidth: Optional[float] = None, linestyle: Optional[str] = None):
        """更新单条曲线样式"""
        if filename in self.lines:
            line = self.lines[filename]
            if color:
                line.set_color(color)
            if linewidth:
                line.set_linewidth(linewidth)
            if linestyle:
                line.set_linestyle(linestyle)
            
            # 只有当图例已经存在且可见时，才更新图例
            legend = self.ax.get_legend()
            if legend and legend.get_visible():
                new_legend = self.ax.legend(loc='best', framealpha=0.8, fontsize=self.tick_size)
                new_legend.set_draggable(True)
                # 恢复可见性（虽然默认是可见的，但为了安全）
                new_legend.set_visible(True)
                # 更新字体
                plt.setp(new_legend.get_texts(), fontsize=self.tick_size, fontfamily=self.font_family)
            
            self.draw()


class PlotWidget(QWidget):
    """绑图组件（包含画布和工具栏）"""
    
    curve_clicked = pyqtSignal(str) # 转发信号
    
    def __init__(self, parent=None, dark_mode=True):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        
        # 创建画布
        self.canvas = PlotCanvas(self, dark_mode=self.dark_mode)
        self.canvas.curve_clicked.connect(self.curve_clicked) # 转发信号
        
        # 添加matplotlib导航工具栏（用于缩放平移）- 使用安全版本避免QFont警告
        self.toolbar = SafeNavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        
        # 添加画布
        layout.addWidget(self.canvas, 1)
        
        # 连接鼠标移动信号（仅用于主窗口状态栏更新）
        # self.canvas.mouse_moved.connect(self._update_coords)
        
        # 初始化样式和图标
        self._update_toolbar_style()
    
    def _update_toolbar_style(self):
        """更新工具栏样式"""
        from PyQt6.QtGui import QFont
        from PyQt6.QtWidgets import QToolButton, QLabel, QWidget
        
        bg_color = "#16213e" if self.dark_mode else "#f5f5f5"
        text_color = "#e0e0e0" if self.dark_mode else "#333333"
        tooltip_bg = "#2d3a4f" if self.dark_mode else "#ffffdc"
        tooltip_text = "#e0e0e0" if self.dark_mode else "#333333"
        
        # 设置工具栏整体样式，包括 tooltip 样式
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {bg_color}; 
                border: none;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: {'#3d4d6f' if self.dark_mode else '#e0e0e0'};
            }}
            QToolTip {{
                background-color: {tooltip_bg};
                color: {tooltip_text};
                border: 1px solid {'#4a5a7a' if self.dark_mode else '#cccccc'};
                font-size: 10pt;
                font-family: 'Segoe UI';
                padding: 4px;
            }}
        """)
        
        # 强制设置工具栏内所有子控件的字体，防止QFont警告
        toolbar_font = QFont("Segoe UI", 10)
        
        for child in self.toolbar.findChildren(QToolButton):
            child.setFont(toolbar_font)
        
        for child in self.toolbar.findChildren(QLabel):
            child.setFont(toolbar_font)
            child.setStyleSheet(f"color: {text_color}; font-size: 10pt;")
        
        # 遍历所有子控件，确保字体正确设置
        for child in self.toolbar.findChildren(QWidget):
            child.setFont(toolbar_font)
            
        # 自动反转图标颜色
        self.toolbar.update_icons(self.dark_mode)
    
    def set_theme(self, dark_mode: bool):
        """设置主题"""
        self.dark_mode = dark_mode
        self.canvas.set_theme(dark_mode)
        self._update_toolbar_style()
    
    def plot_spectrum(self, data: SpectrumData, **kwargs):
        """绘制单个光谱"""
        return self.canvas.plot_spectrum(data, **kwargs)
    
    def plot_multiple(self, data_list: List[SpectrumData], **kwargs):
        """绘制多个光谱"""
        return self.canvas.plot_multiple(data_list, **kwargs)
    
    def clear_plot(self):
        """清除绘图"""
        self.canvas.clear_plot()
    
    def save_figure(self, filepath: str, dpi: int = 300, transparent: bool = False):
        """保存图像"""
        self.canvas.save_figure(filepath, dpi, transparent)
    
    def apply_style_config(self, config: Dict[str, Any]):
        """应用样式配置"""
        self.canvas.apply_style_config(config)
    
    def get_line_filenames(self) -> List[str]:
        """获取当前绑制的曲线文件名列表"""
        return list(self.canvas.lines.keys())
