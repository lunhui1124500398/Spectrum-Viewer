"""
Origin接口模块 - 用于与Origin软件交互
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import csv
from datetime import datetime

# 尝试导入originpro
try:
    import originpro as op
    ORIGIN_AVAILABLE = True
except ImportError:
    ORIGIN_AVAILABLE = False


class OriginInterface:
    """Origin交互接口
    
    提供与OriginLab软件的交互功能：
    1. 导出Origin友好格式的数据文件
    2. 生成Origin导入脚本
    3. [预留] 直接通过originpro包控制Origin
    
    Attributes:
        available: originpro包是否可用
    """
    
    def __init__(self):
        self.available = ORIGIN_AVAILABLE
    
    def export_for_origin(self, 
                          data_list: List[Any],  # List[SpectrumData]
                          output_dir: str,
                          include_raw: bool = True,
                          create_script: bool = True) -> Dict[str, str]:
        """导出Origin友好格式的数据文件
        
        Args:
            data_list: SpectrumData对象列表
            output_dir: 输出目录
            include_raw: 是否包含原始数据（每组扫描的独立数据）
            create_script: 是否创建Origin导入脚本
            
        Returns:
            Dict[str, str]: 创建的文件路径字典:
                - 'main_csv': 主数据文件路径
                - 'script': Origin脚本路径（如果create_script=True）
                - 'raw_dir': 原始数据目录（如果include_raw=True）
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 创建时间戳子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = output_path / f"origin_export_{timestamp}"
        export_dir.mkdir(exist_ok=True)
        
        result = {}
        
        # 1. 导出主数据CSV（合并所有光谱）
        main_csv_path = export_dir / "spectra_data.csv"
        self._export_merged_csv(data_list, main_csv_path)
        result['main_csv'] = str(main_csv_path)
        
        # 2. 导出原始数据
        if include_raw:
            raw_dir = export_dir / "raw"
            raw_dir.mkdir(exist_ok=True)
            for data in data_list:
                self._export_single_raw(data, raw_dir)
            result['raw_dir'] = str(raw_dir)
        
        # 3. 创建Origin导入脚本
        if create_script:
            script_path = export_dir / "import_to_origin.ogs"
            self._create_origin_script(data_list, main_csv_path, script_path)
            result['script'] = str(script_path)
            
            # 同时创建一个说明文件
            readme_path = export_dir / "README.txt"
            self._create_readme(data_list, readme_path)
            result['readme'] = str(readme_path)
        
        return result
    
    def _export_merged_csv(self, data_list: List[Any], filepath: Path):
        """导出合并的CSV文件"""
        if not data_list:
            return
        
        # 使用第一个光谱的波长作为参考
        wavelength = data_list[0].wavelength
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 写入表头
            headers = ['Wavelength (nm)'] + [d.filename.replace('.xls', '') for d in data_list]
            writer.writerow(headers)
            
            # 写入数据
            for i, wl in enumerate(wavelength):
                row = [f"{wl:.1f}"]
                for data in data_list:
                    if i < len(data.intensity_avg):
                        row.append(f"{data.intensity_avg[i]:.6f}")
                    else:
                        row.append("")
                writer.writerow(row)
    
    def _export_single_raw(self, data: Any, output_dir: Path):
        """导出单个文件的原始数据"""
        filename = Path(data.filename).stem
        filepath = output_dir / f"{filename}_raw.csv"
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # 表头：波长 + 每组扫描 + 平均值
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
    
    def _create_origin_script(self, data_list: List[Any], csv_path: Path, script_path: Path):
        """创建Origin LabTalk脚本用于导入数据"""
        script = f'''// SpectrumViewer Auto-generated Origin Script
// Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
// Files: {len(data_list)} spectra

// Import CSV data
string filepath$ = "{csv_path.as_posix()}";
impASC fname:=filepath$ options.Sparklines:=0;

// Set column designations
// First column (Wavelength) as X
wks.col1.type = 4;  // X

// Remaining columns as Y
for (int i = 2; i <= wks.ncols; i++)
{{
    wks.col$(i).type = 1;  // Y
}}

// Create line plot
plotxy iy:=(1,2:end) plot:=200 ogl:=[<new template:=line>];

// Format axes
xaxis.label.show = 1;
xaxis.label.text$ = "Wavelength (nm)";
yaxis.label.show = 1;
yaxis.label.text$ = "Intensity (a.u.)";

// Add legend
legendupdate dest:=0 mode:=1;

// Auto rescale
rescale;

type "Data imported successfully!";
'''
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
    
    def _create_readme(self, data_list: List[Any], filepath: Path):
        """创建说明文件"""
        content = f"""SpectrumViewer Origin Export
============================
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Files included:
- spectra_data.csv: Combined spectrum data
- import_to_origin.ogs: Origin LabTalk script for quick import
- raw/: Individual raw data files with all scan data

Usage in Origin:
1. Open Origin
2. File -> Open -> Select import_to_origin.ogs
3. Or manually import spectra_data.csv

Data Summary:
"""
        for data in data_list:
            wl_range = data.wavelength_range
            int_range = data.intensity_range
            content += f"""
- {data.filename}
  Scans: {data.num_scans}
  Wavelength: {wl_range[0]:.1f} - {wl_range[1]:.1f} nm
  Intensity: {int_range[0]:.2f} - {int_range[1]:.2f}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def apply_origin_template(self, template_path: str):
        """[预留] 通过originpro包应用Origin模板
        
        需要Origin 2019+版本，并且需要Origin在后台运行。
        
        Args:
            template_path: Origin模板文件(.otp)路径
            
        Raises:
            NotImplementedError: 功能尚未实现
            ImportError: originpro包不可用
        """
        if not self.available:
            raise ImportError(
                "此功能需要安装originpro包并运行Origin 2019+。\n"
                "请参考: https://www.originlab.com/doc/python/Python-in-Origin"
            )
        
        # TODO: 实现通过originpro应用模板
        raise NotImplementedError(
            "Origin模板应用功能将在后续版本实现。\n"
            "目前请使用导出的CSV和OGS脚本手动导入Origin。"
        )
    
    def is_available(self) -> bool:
        """检查originpro是否可用"""
        return self.available
    
    @staticmethod
    def get_install_instructions() -> str:
        """获取安装说明"""
        return (
            "Origin Python集成使用说明：\n"
            "1. 需要Origin 2019或更高版本\n"
            "2. 在Origin中启用Python支持\n"
            "3. 使用Origin内置的Python环境\n"
            "详情请参考: https://www.originlab.com/doc/python/Python-in-Origin"
        )


if __name__ == "__main__":
    interface = OriginInterface()
    print(f"Origin Python接口可用: {interface.is_available()}")
    if not interface.is_available():
        print(interface.get_install_instructions())
