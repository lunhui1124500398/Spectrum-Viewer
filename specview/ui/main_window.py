"""
主窗口 - SpectrumViewer应用主界面
"""

import sys
from pathlib import Path
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QFileDialog,
    QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from ..core.data_model import SpectrumData
from ..core.xls_reader import XLSReader
from ..core.origin_interface import OriginInterface
from .file_panel import FilePanel
from .plot_widget import PlotWidget
from .style_panel import StylePanel
from .info_panel import InfoPanel


class MainWindow(QMainWindow):
    """SpectrumViewer主窗口
    
    三栏布局：
    - 左侧：文件面板 + 信息面板
    - 中间：绑图区域
    - 右侧：样式面板
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SpectrumViewer - 荧光光谱查看器")
        self.setMinimumSize(1200, 700)
        
        # 当前显示的数据
        self.current_data: Optional[SpectrumData] = None
        self.overlay_data: List[SpectrumData] = []
        
        # Origin接口
        self.origin_interface = OriginInterface()
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_shortcuts()
        self._apply_stylesheet()
        self._connect_signals()
        
        # 状态栏初始信息
        self.statusBar().showMessage("就绪 - 拖拽光谱文件(XLS/SIF)到左侧面板开始")
    
    def _setup_ui(self):
        """设置UI布局"""
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧面板容器
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)
        
        # 文件面板
        self.file_panel = FilePanel()
        left_layout.addWidget(self.file_panel, 2)
        
        # 信息面板
        self.info_panel = InfoPanel()
        left_layout.addWidget(self.info_panel, 1)
        
        left_container.setMinimumWidth(250)
        left_container.setMaximumWidth(400)
        
        # 中间绘图区域
        self.plot_widget = PlotWidget()
        
        # 右侧样式面板
        self.style_panel = StylePanel()
        self.style_panel.setMinimumWidth(220)
        # 不设置最大宽度，允许用户拖拽调整
        
        # 添加到分割器
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(self.plot_widget)
        self.splitter.addWidget(self.style_panel)
        
        # 设置分割比例
        self.splitter.setSizes([280, 600, 280])
        
        main_layout.addWidget(self.splitter)
        
        # 状态栏
        self.setStatusBar(QStatusBar())
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        action_open = file_menu.addAction("打开文件(&O)")
        action_open.setShortcut(QKeySequence.StandardKey.Open)
        action_open.triggered.connect(self._on_open_files)
        
        action_open_folder = file_menu.addAction("打开文件夹...")
        action_open_folder.setShortcut("Ctrl+Shift+O")
        action_open_folder.triggered.connect(self._on_open_folder)
        
        file_menu.addSeparator()
        
        # 导出子菜单
        export_menu = file_menu.addMenu("导出")
        
        action_export_csv = export_menu.addAction("导出CSV (单文件)...")
        action_export_csv.setShortcut("Ctrl+E")
        action_export_csv.triggered.connect(self._on_export_csv_single)
        
        action_export_merged = export_menu.addAction("导出CSV (合并)...")
        action_export_merged.setShortcut("Ctrl+Shift+E")
        action_export_merged.triggered.connect(self._on_export_csv_merged)
        
        action_export_origin = export_menu.addAction("导出Origin格式...")
        action_export_origin.triggered.connect(self._on_export_origin)
        
        export_menu.addSeparator()
        
        action_save_figure = export_menu.addAction("保存图像...")
        action_save_figure.setShortcut("Ctrl+S")
        action_save_figure.triggered.connect(self._on_save_figure)
        
        file_menu.addSeparator()
        
        action_exit = file_menu.addAction("退出(&X)")
        action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        action_exit.triggered.connect(self.close)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        action_reset_view = view_menu.addAction("重置视图")
        action_reset_view.setShortcut("Ctrl+0")
        action_reset_view.triggered.connect(self.plot_widget.canvas.reset_view)
        
        view_menu.addSeparator()
        
        self.action_grid = view_menu.addAction("显示网格")
        self.action_grid.setCheckable(True)
        self.action_grid.setChecked(True)
        self.action_grid.setShortcut("G")
        self.action_grid.triggered.connect(self._on_toggle_grid)
        
        self.action_legend = view_menu.addAction("显示图例")
        self.action_legend.setCheckable(True)
        self.action_legend.setChecked(True)
        self.action_legend.setShortcut("L")
        self.action_legend.triggered.connect(self._on_toggle_legend)
        
        # 模板菜单
        template_menu = menubar.addMenu("模板(&T)")
        
        action_save_template = template_menu.addAction("保存模板...")
        action_save_template.setShortcut("Ctrl+T")
        action_save_template.triggered.connect(self.style_panel._save_template)
        
        action_load_template = template_menu.addAction("加载模板...")
        action_load_template.setShortcut("Ctrl+Shift+T")
        action_load_template.triggered.connect(self.style_panel._load_template)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        action_about = help_menu.addAction("关于")
        action_about.triggered.connect(self._show_about)
        
        action_shortcuts = help_menu.addAction("快捷键")
        action_shortcuts.triggered.connect(self._show_shortcuts)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # 添加工具按钮
        btn_open = toolbar.addAction("📂 导入")
        btn_open.setToolTip("打开文件 (Ctrl+O)")
        btn_open.triggered.connect(self._on_open_files)
        
        btn_export = toolbar.addAction("💾 导出")
        btn_export.setToolTip("导出CSV (Ctrl+E)")
        btn_export.triggered.connect(self._on_export_csv_single)
        
        toolbar.addSeparator()
        
        btn_reset = toolbar.addAction("🏠 重置")
        btn_reset.setToolTip("重置视图 (Ctrl+0)")
        btn_reset.triggered.connect(self.plot_widget.canvas.reset_view)
        
        # 使用已创建的action
        self.action_grid.setText("⊞ 网格")
        self.action_grid.setToolTip("切换网格 (G)")
        toolbar.addAction(self.action_grid)
        
        self.action_legend.setText("📋 图例")
        self.action_legend.setToolTip("切换图例 (L)")
        toolbar.addAction(self.action_legend)
        
        toolbar.addSeparator()
        
        btn_origin = toolbar.addAction("📊 Origin")
        btn_origin.setToolTip("导出Origin格式")
        btn_origin.triggered.connect(self._on_export_origin)
    
    def _setup_shortcuts(self):
        """设置额外快捷键"""
        # Delete键删除选中文件
        pass  # 大部分快捷键已在菜单中设置
    
    def _apply_stylesheet(self, theme: str = 'light'):
        """应用样式表

        Args:
            theme: 'dark' 或 'light'
        """
        self.current_theme = theme
        qss_filename = 'dark_theme.qss' if theme == 'dark' else 'light_theme.qss'
        base_path = Path(__file__).parent.parent / "resources"
        qss_path = base_path / "styles" / qss_filename
        
        if qss_path.exists():
            with open(qss_path, 'r', encoding='utf-8') as f:
                style_sheet = f.read()
                # 替换相对路径为绝对路径，解决图标加载问题
                # 使用 as_posix() 确保路径分隔符为 forward slash '/'
                resources_path = base_path.as_posix()
                style_sheet = style_sheet.replace('url(../', f'url({resources_path}/')
                self.setStyleSheet(style_sheet)
        
        # 同步绘图主题
        self.plot_widget.set_theme(theme == 'dark')
    
    def _connect_signals(self):
        """连接信号"""
        # 文件面板信号
        self.file_panel.file_selected.connect(self._on_file_selected)
        self.file_panel.overlay_requested.connect(self._on_overlay_requested)
        self.file_panel.files_checked_changed.connect(self._on_files_checked_changed)
        
        # 样式面板信号
        self.style_panel.style_changed.connect(self._on_style_changed)
        self.style_panel.theme_changed.connect(self._on_theme_changed)
        self.style_panel.line_style_changed.connect(self._on_line_style_changed)
        
        # 绘图鼠标位置
        self.plot_widget.canvas.mouse_moved.connect(self._update_status_coords)
        # 曲线点击
        self.plot_widget.curve_clicked.connect(self._on_curve_clicked)
    
    def _on_curve_clicked(self, filename: str):
        """处理曲线点击事件"""
        # 在叠加数据中查找对应的 SpectrumData
        target_data = next((d for d in self.overlay_data if d.filename == filename), None)
        
        if target_data:
            # 更新左侧文件面板选中(可选)
            # self.file_panel.select_file(filename) 
            
            # 更新信息面板显示该曲线详情
            self.info_panel.update_info(target_data)
            self.statusBar().showMessage(f"选中: {filename}")
    
    def _on_file_selected(self, data: SpectrumData):
        """文件被选中（单击）"""
        self.current_data = data
        self.overlay_data = [data]
        
        # 更新信息面板
        self.info_panel.update_info(data)
        
        # 绘制
        self.plot_widget.plot_spectrum(data)
        
        # 更新状态栏
        self.statusBar().showMessage(f"显示: {data.filename}")
    
    def _on_overlay_requested(self, data_list: List[SpectrumData]):
        """请求叠加显示"""
        if not data_list:
            return
        
        self.overlay_data = data_list
        self.current_data = data_list[0] if len(data_list) == 1 else None
        
        # 更新信息面板
        if len(data_list) == 1:
            self.info_panel.update_info(data_list[0])
        else:
            self.info_panel.update_multi_info(data_list)
        
        # 获取配色
        colors = self.style_panel.get_line_colors()
        
        # 绑制
        self.plot_widget.plot_multiple(data_list, colors=colors)
        
        # 更新样式面板的曲线列表
        self.style_panel.update_line_list([d.filename for d in data_list], colors)
        
        # 更新状态栏
        self.statusBar().showMessage(f"叠加显示: {len(data_list)} 个文件")
    
    def _on_files_checked_changed(self, data_list: List[SpectrumData]):
        """复选框状态改变"""
        # 可以在这里实时更新叠加显示，或者等用户点击叠加按钮
        pass
    
    def _on_style_changed(self, config: dict):
        """样式改变"""
        # 使用增强版的样式应用
        self.plot_widget.apply_style_config(config)
        
        # 同步显示选项状态
        display_config = config.get('display', {})
        if 'grid' in display_config:
            self.action_grid.setChecked(display_config['grid'])
        if 'legend' in display_config:
            self.action_legend.setChecked(display_config['legend'])
    
    def _on_theme_changed(self, theme: str):
        """主题改变"""
        self._apply_stylesheet(theme)
    
    def _on_line_style_changed(self, filename: str, style: dict):
        """单条曲线样式改变"""
        self.plot_widget.canvas.update_line_style(
            filename,
            color=style.get('color'),
            linewidth=style.get('linewidth'),
            linestyle=style.get('linestyle')
        )
    
    def _on_toggle_grid(self, checked: bool):
        """切换网格"""
        self.plot_widget.canvas.toggle_grid(checked)
        self.style_panel.check_grid.blockSignals(True)
        self.style_panel.check_grid.setChecked(checked)
        self.style_panel.check_grid.blockSignals(False)
    
    def _on_toggle_legend(self, checked: bool):
        """切换图例"""
        self.plot_widget.canvas.toggle_legend(checked)
        self.style_panel.check_legend.blockSignals(True)
        self.style_panel.check_legend.setChecked(checked)
        self.style_panel.check_legend.blockSignals(False)
    
    def _update_status_coords(self, x: float, y: float):
        """更新状态栏坐标"""
        current_msg = self.statusBar().currentMessage()
        # 保留主消息，只更新坐标
        base_msg = current_msg.split(" | ")[0] if " | " in current_msg else current_msg
        self.statusBar().showMessage(f"{base_msg} | λ={x:.1f} nm, I={y:.2f}")
    
    def _on_open_files(self):
        """打开文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择光谱文件", "",
            "光谱文件 (*.xls *.sif);;Excel文件 (*.xls);;SIF文件 (*.sif);;所有文件 (*.*)"
        )
        if files:
            self.file_panel.load_files(files)
    
    def _on_open_folder(self):
        """打开文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            folder_path = Path(folder)
            files = []
            for ext in ['*.xls', '*.sif']:
                files.extend([str(f) for f in folder_path.rglob(ext)])
            if files:
                self.file_panel.load_files(files)
            else:
                QMessageBox.information(self, "提示", "该文件夹中没有找到光谱文件 (XLS/SIF)")
    
    def _on_export_csv_single(self):
        """导出单文件CSV"""
        if not self.overlay_data:
            QMessageBox.warning(self, "提示", "请先选择或加载数据")
            return
        
        # 获取保存路径
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not folder:
            return
        
        folder_path = Path(folder)
        exported = 0
        
        for data in self.overlay_data:
            # 生成文件名
            csv_name = Path(data.filename).stem + ".csv"
            csv_path = folder_path / csv_name
            
            # 写入CSV
            import csv
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                
                # 表头
                headers = ['Wavelength (nm)']
                headers += [f'Scan_{i+1}' for i in range(data.num_scans)]
                headers.append('Average')
                writer.writerow(headers)
                
                # 数据
                for i, wl in enumerate(data.wavelength):
                    row = [f"{wl:.1f}"]
                    for scan in data.intensity_raw:
                        row.append(f"{scan[i]:.6f}")
                    row.append(f"{data.intensity_avg[i]:.6f}")
                    writer.writerow(row)
            
            exported += 1
        
        QMessageBox.information(self, "导出成功", f"已导出 {exported} 个CSV文件到:\n{folder}")
    
    def _on_export_csv_merged(self):
        """导出合并CSV"""
        if not self.overlay_data:
            QMessageBox.warning(self, "提示", "请先选择或加载数据")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存合并CSV", "merged_spectra.csv",
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if not filepath:
            return
        
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 表头
            headers = ['Wavelength (nm)']
            headers += [Path(d.filename).stem for d in self.overlay_data]
            writer.writerow(headers)
            
            # 使用第一个数据的波长
            wavelength = self.overlay_data[0].wavelength
            
            for i, wl in enumerate(wavelength):
                row = [f"{wl:.1f}"]
                for data in self.overlay_data:
                    if i < len(data.intensity_avg):
                        row.append(f"{data.intensity_avg[i]:.6f}")
                    else:
                        row.append("")
                writer.writerow(row)
        
        QMessageBox.information(self, "导出成功", f"已导出合并CSV到:\n{filepath}")
    
    def _on_export_origin(self):
        """导出Origin格式"""
        if not self.overlay_data:
            QMessageBox.warning(self, "提示", "请先选择或加载数据")
            return
        
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not folder:
            return
        
        try:
            result = self.origin_interface.export_for_origin(
                self.overlay_data, folder,
                include_raw=True, create_script=True
            )
            
            msg = "Origin格式导出成功！\n\n"
            msg += f"主数据文件: {result['main_csv']}\n"
            if 'script' in result:
                msg += f"Origin脚本: {result['script']}\n"
            if 'raw_dir' in result:
                msg += f"原始数据目录: {result['raw_dir']}\n"
            
            QMessageBox.information(self, "导出成功", msg)
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出失败:\n{e}")
    
    def _on_save_figure(self):
        """保存图像"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图像", "spectrum.png",
            "PNG图像 (*.png);;PDF文档 (*.pdf);;SVG矢量图 (*.svg);;所有文件 (*.*)"
        )
        if filepath:
            try:
                self.plot_widget.save_figure(filepath, dpi=300)
                QMessageBox.information(self, "保存成功", f"图像已保存到:\n{filepath}")
            except Exception as e:
                QMessageBox.warning(self, "保存失败", f"保存失败:\n{e}")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于 SpectrumViewer",
            "<h2>SpectrumViewer</h2>"
            "<p>版本: 0.1.0</p>"
            "<p>荧光光谱数据查看和预处理工具</p>"
            "<p>支持Hitachi F-7000光谱仪导出的XLS文件</p>"
            "<hr>"
            "<p>功能特性:</p>"
            "<ul>"
            "<li>拖拽导入XLS文件</li>"
            "<li>自动检测多组扫描数据并取平均</li>"
            "<li>曲线叠加和对比显示</li>"
            "<li>模板系统保存绘图配置</li>"
            "<li>导出CSV和Origin格式</li>"
            "</ul>"
        )
    
    def _show_shortcuts(self):
        """显示快捷键列表"""
        shortcuts_text = """
<h3>快捷键列表</h3>
<table>
<tr><td><b>Ctrl+O</b></td><td>打开文件</td></tr>
<tr><td><b>Ctrl+Shift+O</b></td><td>打开文件夹</td></tr>
<tr><td><b>Ctrl+E</b></td><td>导出CSV (单文件)</td></tr>
<tr><td><b>Ctrl+Shift+E</b></td><td>导出CSV (合并)</td></tr>
<tr><td><b>Ctrl+S</b></td><td>保存图像</td></tr>
<tr><td><b>Ctrl+0</b></td><td>重置视图</td></tr>
<tr><td><b>G</b></td><td>切换网格</td></tr>
<tr><td><b>L</b></td><td>切换图例</td></tr>
<tr><td><b>Ctrl+T</b></td><td>保存模板</td></tr>
<tr><td><b>Ctrl+Shift+T</b></td><td>加载模板</td></tr>
</table>
        """
        QMessageBox.information(self, "快捷键", shortcuts_text)
