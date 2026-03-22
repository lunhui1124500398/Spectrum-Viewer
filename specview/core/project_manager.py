"""
项目文件管理器 - 负责 .svproj 文件的保存与加载
"""

import json
import zipfile
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import csv
import io

from .data_model import SpectrumData
from .processing_chain import ProcessingChain, ProcessingStep

class ProjectManager:
    """项目文件管理器
    
    采用 ZIP 包格式存储项目文件：
    - manifest.json: 项目元数据
    - raw/: 原始数据文件副本
    - processed/processing_log.json: 处理链路记录
    - processed/data/: 处理后数据 (JSON/CSV)
    - portable/plot_data.csv: 如果需要，可以存储便于绘图的数据
    - figures/: 导出的图像
    - session.json: 会话状态
    - style.json: 样式配置
    """
    
    VERSION = "1.0"
    
    def __init__(self):
        pass
        
    def save_project(self, path: str, 
                     data_list: List[SpectrumData],
                     processing_chain: ProcessingChain,
                     style_config: Dict = None,
                     figures: List[str] = None,
                     description: str = "") -> None:
        """保存项目到 .svproj (.zip) 文件
        
        Args:
            path: 保存路径
            data_list: 光谱数据列表
            processing_chain: 处理链路管理器
            style_config: 当前样式配置
            figures: 图像文件路径列表
            description: 项目描述
        """
        path = Path(path)
        
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. 保存元数据 (manifest.json)
            manifest = {
                "version": self.VERSION,
                "created_at": datetime.now().isoformat(),
                "description": description,
                "file_count": len(data_list)
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            
            # 2. 保存样式配置 (style.json)
            if style_config:
                zf.writestr("style.json", json.dumps(style_config, indent=2))
            
            # 3. 保存原始文件 (raw/) 和处理后数据
            # 同时也生成 processed/data/ 下的数据文件
            self._save_data_and_raw(zf, data_list)
            
            # 4. 保存处理链路 (processed/processing_log.json)
            zf.writestr("processed/processing_log.json", processing_chain.to_json())
            
            # 5. 保存图像 (figures/)
            if figures:
                for fig_path in figures:
                    p = Path(fig_path)
                    if p.exists():
                        zf.write(p, f"figures/{p.name}")
                        
            # 6. 生成 Portable 数据 (portable/plot_data.csv)
            self._save_portable_data(zf, data_list)

    def load_project(self, path: str, temp_dir: str = None) -> Dict[str, Any]:
        """加载项目
        
        Args:
            path: 项目文件路径
            temp_dir: 临时解压目录（如果为 None，则使用系统临时目录）
            
        Returns:
            Dict 包含:
            - data_list: List[SpectrumData]
            - processing_chain: ProcessingChain
            - style_config: Dict
            - manifest: Dict
        """
        project_path = Path(path)
        if not project_path.exists():
            raise FileNotFoundError(f"Project file not found: {path}")
            
        # 如果没有指定解压目录，创建一个临时目录
        # 注意：这个临时目录的生命周期由调用者管理，或者我们在 SpectrumData 中记录路径
        # 这里为了简单，我们读取数据后不依赖解压的文件（除了 raw 用于溯源）
        # 但 SpectrumData 通常需要 filepath。
        # 策略：不完全解压，而是按需读取。
        # 为了兼容现有的 load_file 逻辑和 SpectrumData 结构，
        # 我们重新构建 SpectrumData 对象。
        
        data_list = []
        processing_chain = ProcessingChain()
        style_config = {}
        manifest = {}
        
        with zipfile.ZipFile(project_path, 'r') as zf:
            # 1. 读取 Manifest
            if "manifest.json" in zf.namelist():
                manifest = json.loads(zf.read("manifest.json").decode('utf-8'))
                
            # 2. 读取 Style
            if "style.json" in zf.namelist():
                style_config = json.loads(zf.read("style.json").decode('utf-8'))
                
            # 3. 读取 Processing Log
            if "processed/processing_log.json" in zf.namelist():
                processing_chain = ProcessingChain.from_json(zf.read("processed/processing_log.json").decode('utf-8'))
            
            # 4. 恢复 SpectrumData
            # 我们需要遍历 manifest 或者 processed/data 里的文件列表
            # 这里我们通过遍历 processed/data/ 目录下的 json 文件来恢复
            # 文件名：processed/data/{filename}.json
            
            for file_in_zip in zf.namelist():
                if file_in_zip.startswith("processed/data/") and file_in_zip.endswith(".json"):
                    data_json = json.loads(zf.read(file_in_zip).decode('utf-8'))
                    
                    # 重建 SpectrumData
                    spec_data = SpectrumData(
                        filepath=data_json.get('original_filepath', 'unknown'), # 记录原始路径
                        filename=data_json.get('filename', 'unknown'),
                        metadata=data_json.get('metadata', {}),
                        source_format=data_json.get('source_format', 'unknown'),
                        num_scans=data_json.get('num_scans', 0)
                    )
                    
                    # 恢复数据数组
                    # 注意：JSON 中列表转回 numpy array
                    if 'wavelength' in data_json:
                        spec_data.wavelength = np.array(data_json['wavelength'])
                    
                    if 'intensity_avg' in data_json:
                        spec_data.intensity_avg = np.array(data_json['intensity_avg'])
                        
                    if 'intensity_raw' in data_json:
                        spec_data.intensity_raw = [np.array(scan) for scan in data_json['intensity_raw']]
                        
                    data_list.append(spec_data)
                    
        return {
            "data_list": data_list,
            "processing_chain": processing_chain,
            "style_config": style_config,
            "manifest": manifest
        }

    def _save_data_and_raw(self, zf: zipfile.ZipFile, data_list: List[SpectrumData]):
        """保存数据文件和原始文件"""
        
        processed_files = set() # 处理同名文件
        
        for data in data_list:
            # 1. 尝试保存原始文件 (Raw)
            # 只有当原始文件存在时才保存
            if data.filepath and Path(data.filepath).exists():
                # 为了避免文件名冲突，如果同名可能需要处理
                # 这里简单处理：直接用 filename。假设项目中 filename 唯一。
                arcname = f"raw/{data.filename}"
                zf.write(data.filepath, arcname)
                
            # 2. 保存处理后的数据对象 (Processed) -> JSON
            # 将 SpectrumData 序列化为 JSON
            # 同样假设 filename 唯一
            
            safe_filename = data.filename
            if safe_filename in processed_files:
                # 简单防重：添加 index (实际应用应更健壮)
                count = 1
                base_name = Path(safe_filename).stem
                ext = Path(safe_filename).suffix
                while f"{base_name}_{count}{ext}" in processed_files:
                    count += 1
                safe_filename = f"{base_name}_{count}{ext}"
            
            processed_files.add(safe_filename)
            
            data_dict = {
                "filename": data.filename, # 保持原始文件名
                "original_filepath": data.filepath,
                "metadata": data.metadata,
                "source_format": data.source_format,
                "num_scans": data.num_scans,
                "wavelength": data.wavelength.tolist() if hasattr(data.wavelength, 'tolist') else list(data.wavelength),
                "intensity_avg": data.intensity_avg.tolist() if hasattr(data.intensity_avg, 'tolist') else list(data.intensity_avg),
                # 可选：保存 raw intensity，如果不保存可以减小体积，但这里为了完整性保存
                "intensity_raw": [scan.tolist() for scan in data.intensity_raw] if data.intensity_raw else []
            }
            
            zf.writestr(f"processed/data/{safe_filename}.json", json.dumps(data_dict))

    def _save_portable_data(self, zf: zipfile.ZipFile, data_list: List[SpectrumData]):
        """保存 Portable 数据 (CSV) - 类似 Origin 导出"""
        if not data_list:
            return

        # 使用 io.StringIO 在内存中构建 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 假设所有数据波长一致（简单情况），如果不一致需要对齐（复杂情况）
        # 这里使用第一个数据的波长
        base_wavelength = data_list[0].wavelength
        
        # Header
        header = ["Wavelength"] + [d.filename for d in data_list]
        writer.writerow(header)
        
        # Data
        for i, wl in enumerate(base_wavelength):
            row = [wl]
            for data in data_list:
                if i < len(data.intensity_avg):
                    row.append(data.intensity_avg[i])
                else:
                    row.append("")
            writer.writerow(row)
            
        zf.writestr("portable/plot_data.csv", output.getvalue())

# 需要导入 numpy
import numpy as np
