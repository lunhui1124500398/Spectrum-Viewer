"""
文件管理面板 - 支持拖拽导入和文件列表管理
"""

from pathlib import Path
from typing import List, Optional, Set
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction

from ..core.data_model import SpectrumData
from ..core.xls_reader import XLSReader
from ..core.sif_reader import SIFReader, SIF_AVAILABLE

# Supported file extensions
SUPPORTED_EXTENSIONS = {'.xls', '.sif'}


class DropZone(QWidget):
    """文件拖拽区域"""
    
    files_dropped = pyqtSignal(list)  # 发送文件路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("📂 拖拽光谱文件到此处\n支持 XLS / SIF 格式")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #a0a0a0; font-size: 12px;")
        layout.addWidget(self.label)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            # 检查是否有支持的文件格式
            for url in event.mimeData().urls():
                suffix = Path(url.toLocalFile()).suffix.lower()
                if suffix in SUPPORTED_EXTENSIONS:
                    event.acceptProposedAction()
                    self.setStyleSheet("border-color: #e94560; background-color: #1e1e3e;")
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            path_obj = Path(path)
            if path_obj.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
            elif path_obj.is_dir():
                # 如果是文件夹，搜索其中的光谱文件
                for ext in SUPPORTED_EXTENSIONS:
                    for found_file in path_obj.rglob(f'*{ext}'):
                        files.append(str(found_file))
        
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()


class FileListItem(QListWidgetItem):
    """自定义文件列表项"""
    
    def __init__(self, data: SpectrumData, parent=None):
        super().__init__(parent)
        self.spectrum_data = data
        self.setText(data.filename)
        self.setCheckState(Qt.CheckState.Unchecked)
        self.setToolTip(f"路径: {data.filepath}\n"
                       f"数据组数: {data.num_scans}\n"
                       f"波长范围: {data.wavelength_range[0]:.1f}-{data.wavelength_range[1]:.1f} nm")


class FilePanel(QWidget):
    """文件管理面板
    
    支持：
    - 拖拽导入xls文件
    - 点击按钮选择文件/文件夹
    - 文件列表管理（复选框选择）
    - 右键菜单（移除、查看详情等）
    
    Signals:
        file_selected: 当单击选择文件时发出，传递SpectrumData
        files_checked_changed: 当复选框状态改变时发出，传递选中的SpectrumData列表
        overlay_requested: 当请求叠加显示时发出
    """
    
    file_selected = pyqtSignal(object)  # SpectrumData
    files_checked_changed = pyqtSignal(list)  # List[SpectrumData]
    overlay_requested = pyqtSignal(list)  # List[SpectrumData]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FilePanel")
        self.xls_reader = XLSReader()
        self.sif_reader = SIFReader() if SIF_AVAILABLE else None
        self.loaded_files: Set[str] = set()  # 已加载的文件路径集合
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("📁 文件列表")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        
        # 拖拽区域
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)
        
        # 按钮行
        btn_layout = QHBoxLayout()
        
        self.btn_open_files = QPushButton("📄 选择文件")
        self.btn_open_files.setToolTip("选择光谱文件 (XLS/SIF) (Ctrl+O)")
        btn_layout.addWidget(self.btn_open_files)
        
        self.btn_open_folder = QPushButton("📁 选择文件夹")
        self.btn_open_folder.setToolTip("选择文件夹，导入其中所有光谱文件 (Ctrl+Shift+O)")
        btn_layout.addWidget(self.btn_open_folder)
        
        layout.addLayout(btn_layout)
        
        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.file_list, 1)  # 占据剩余空间
        
        # 操作按钮行
        action_layout = QHBoxLayout()
        
        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setMaximumWidth(60)
        action_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton("取消")
        self.btn_deselect_all.setMaximumWidth(60)
        action_layout.addWidget(self.btn_deselect_all)
        
        action_layout.addStretch()
        
        self.btn_overlay = QPushButton("📊 叠加选中")
        self.btn_overlay.setObjectName("primary")
        self.btn_overlay.setToolTip("将选中的曲线叠加显示 (Ctrl+Enter)")
        action_layout.addWidget(self.btn_overlay)
        
        layout.addLayout(action_layout)
        
        # 统计信息
        self.label_stats = QLabel("已加载: 0 个文件")
        self.label_stats.setObjectName("infoLabel")
        layout.addWidget(self.label_stats)
    
    def _connect_signals(self):
        """连接信号"""
        self.drop_zone.files_dropped.connect(self.load_files)
        self.btn_open_files.clicked.connect(self._on_open_files)
        self.btn_open_folder.clicked.connect(self._on_open_folder)
        self.btn_select_all.clicked.connect(self._select_all)
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        self.btn_overlay.clicked.connect(self._on_overlay)
        self.file_list.itemClicked.connect(self._on_item_clicked)
        self.file_list.itemChanged.connect(self._on_item_changed)
        self.file_list.customContextMenuRequested.connect(self._show_context_menu)
    
    def _on_open_files(self):
        """打开文件对话框"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择光谱文件", "",
            "光谱文件 (*.xls *.sif);;Excel文件 (*.xls);;SIF文件 (*.sif);;所有文件 (*.*)"
        )
        if files:
            self.load_files(files)
    
    def _on_open_folder(self):
        """打开文件夹对话框"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            files = []
            folder_path = Path(folder)
            for ext in SUPPORTED_EXTENSIONS:
                files.extend([str(f) for f in folder_path.rglob(f'*{ext}')])
            if files:
                self.load_files(files)
            else:
                QMessageBox.information(self, "提示", "该文件夹中没有找到光谱文件 (XLS/SIF)")
    
    def load_files(self, filepaths: List[str]):
        """加载文件列表
        
        Args:
            filepaths: 文件路径列表
        """
        loaded_count = 0
        error_count = 0
        
        for filepath in filepaths:
            # 跳过已加载的文件
            if filepath in self.loaded_files:
                continue
            
            try:
                # 根据扩展名选择读取器
                suffix = Path(filepath).suffix.lower()
                if suffix == '.sif':
                    if self.sif_reader is None:
                        raise ImportError("SIF读取器不可用，请安装 sif_parser: pip install sif_parser")
                    data = self.sif_reader.read_file(filepath)
                elif suffix == '.xls':
                    data = self.xls_reader.read_file(filepath)
                else:
                    raise ValueError(f"不支持的文件格式: {suffix}")
                
                item = FileListItem(data)
                self.file_list.addItem(item)
                self.loaded_files.add(filepath)
                loaded_count += 1
            except Exception as e:
                print(f"加载失败: {filepath}: {e}")
                error_count += 1
        
        self._update_stats()
        
        if error_count > 0:
            QMessageBox.warning(
                self, "加载警告",
                f"成功加载 {loaded_count} 个文件\n"
                f"失败 {error_count} 个文件"
            )
        
        # 自然排序
        self._sort_file_list()

    def _sort_file_list(self):
        """对文件列表进行自然排序"""
        import re
        
        def natural_key(text):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
        
        # 获取并移除所有项目，保留对象
        items = []
        while self.file_list.count() > 0:
            items.append(self.file_list.takeItem(0))
        
        # 排序
        items.sort(key=lambda item: natural_key(item.spectrum_data.filename))
        
        # 重新添加
        for item in items:
            self.file_list.addItem(item)

    
    def _update_stats(self):
        """更新统计信息"""
        total = self.file_list.count()
        checked = sum(1 for i in range(total) 
                     if self.file_list.item(i).checkState() == Qt.CheckState.Checked)
        self.label_stats.setText(f"已加载: {total} 个文件 | 已选中: {checked} 个")
    
    def _select_all(self):
        """全选"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.CheckState.Checked)
        self._update_stats()
        self._emit_checked_changed()
    
    def _deselect_all(self):
        """取消全选"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._update_stats()
        self._emit_checked_changed()
    
    def _on_item_clicked(self, item: FileListItem):
        """单击项目时"""
        if isinstance(item, FileListItem):
            self.file_selected.emit(item.spectrum_data)
    
    def _on_item_changed(self, item: QListWidgetItem):
        """项目状态改变时"""
        self._update_stats()
        self._emit_checked_changed()
    
    def _emit_checked_changed(self):
        """发送选中状态改变信号"""
        checked_data = self.get_checked_data()
        self.files_checked_changed.emit(checked_data)
    
    def _on_overlay(self):
        """叠加显示"""
        checked_data = self.get_checked_data()
        if checked_data:
            self.overlay_requested.emit(checked_data)
        else:
            QMessageBox.information(self, "提示", "请先勾选要叠加显示的文件")
    
    def get_checked_data(self) -> List[SpectrumData]:
        """获取所有勾选的数据"""
        result = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if isinstance(item, FileListItem) and item.checkState() == Qt.CheckState.Checked:
                result.append(item.spectrum_data)
        return result
    
    def get_all_data(self) -> List[SpectrumData]:
        """获取所有已加载的数据"""
        result = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if isinstance(item, FileListItem):
                result.append(item.spectrum_data)
        return result
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self.file_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        action_view = menu.addAction("📊 单独显示")
        action_view.triggered.connect(lambda: self.file_selected.emit(item.spectrum_data))
        
        action_info = menu.addAction("ℹ️ 查看详情")
        action_info.triggered.connect(lambda: self._show_file_info(item))
        
        menu.addSeparator()
        
        action_remove = menu.addAction("🗑️ 移除")
        action_remove.triggered.connect(lambda: self._remove_item(item))
        
        action_remove_all = menu.addAction("🗑️ 移除所有")
        action_remove_all.triggered.connect(self._remove_all)
        
        menu.exec(self.file_list.mapToGlobal(pos))
    
    def _show_file_info(self, item: FileListItem):
        """显示文件详细信息"""
        data = item.spectrum_data
        info_text = data.get_info_text()
        
        # 添加更多详细信息
        info_text += f"\n\n完整路径: {data.filepath}"
        
        QMessageBox.information(self, "文件详情", info_text)
    
    def _remove_item(self, item: FileListItem):
        """移除单个项目"""
        filepath = item.spectrum_data.filepath
        self.loaded_files.discard(filepath)
        row = self.file_list.row(item)
        self.file_list.takeItem(row)
        self._update_stats()
        self._emit_checked_changed()
    
    def _remove_all(self):
        """移除所有项目"""
        reply = QMessageBox.question(
            self, "确认",
            "确定要移除所有文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.file_list.clear()
            self.loaded_files.clear()
            self._update_stats()
            self._emit_checked_changed()
