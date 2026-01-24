"""
数据处理模块 - 提供光谱数据的处理工具
"""

from typing import List, Optional, Literal
import numpy as np
from scipy import signal
from scipy import interpolate


class DataProcessor:
    """数据处理工具类
    
    提供光谱数据的各种处理方法，包括平均、归一化、平滑、基线校正等。
    所有方法都是静态方法，可以直接调用而无需实例化。
    
    Example:
        >>> intensity_norm = DataProcessor.normalize(intensity, method='max')
        >>> intensity_smooth = DataProcessor.smooth(intensity, window=5)
    """
    
    @staticmethod
    def average_spectra(spectra: List[np.ndarray]) -> np.ndarray:
        """计算多组光谱的平均值
        
        Args:
            spectra: 光谱强度数组列表，每个数组长度应相同
            
        Returns:
            np.ndarray: 平均后的强度数组
            
        Raises:
            ValueError: 如果输入列表为空或数组长度不一致
        """
        if not spectra:
            raise ValueError("输入列表不能为空")
        
        # 检查长度一致性
        lengths = [len(s) for s in spectra]
        if len(set(lengths)) > 1:
            raise ValueError(f"所有光谱长度必须相同，当前长度: {lengths}")
        
        return np.mean(spectra, axis=0)
    
    @staticmethod
    def normalize(intensity: np.ndarray, 
                  method: Literal['max', 'area', 'minmax', 'peak'] = 'max',
                  peak_wavelength: Optional[float] = None,
                  wavelength: Optional[np.ndarray] = None) -> np.ndarray:
        """归一化处理
        
        Args:
            intensity: 强度数组
            method: 归一化方法
                - 'max': 最大值归一化，最大值变为1
                - 'area': 面积归一化，曲线下面积为1
                - 'minmax': 最小-最大归一化，范围变为[0, 1]
                - 'peak': 在指定波长处归一化为1
            peak_wavelength: 当method='peak'时，指定归一化的波长位置
            wavelength: 波长数组，用于'area'和'peak'方法
            
        Returns:
            np.ndarray: 归一化后的强度数组
        """
        intensity = np.asarray(intensity, dtype=float)
        
        if method == 'max':
            max_val = np.max(np.abs(intensity))
            if max_val == 0:
                return intensity
            return intensity / max_val
        
        elif method == 'minmax':
            min_val = np.min(intensity)
            max_val = np.max(intensity)
            if max_val - min_val == 0:
                return np.zeros_like(intensity)
            return (intensity - min_val) / (max_val - min_val)
        
        elif method == 'area':
            if wavelength is None:
                # 假设等间距波长
                area = np.trapz(intensity)
            else:
                area = np.trapz(intensity, wavelength)
            if area == 0:
                return intensity
            return intensity / area
        
        elif method == 'peak':
            if wavelength is None or peak_wavelength is None:
                raise ValueError("'peak'方法需要提供wavelength和peak_wavelength参数")
            # 找到最接近指定波长的索引
            idx = np.argmin(np.abs(wavelength - peak_wavelength))
            peak_val = intensity[idx]
            if peak_val == 0:
                return intensity
            return intensity / peak_val
        
        else:
            raise ValueError(f"未知的归一化方法: {method}")
    
    @staticmethod
    def smooth(intensity: np.ndarray, 
               window: int = 5,
               method: Literal['savgol', 'moving_avg', 'gaussian'] = 'savgol',
               polyorder: int = 2) -> np.ndarray:
        """平滑处理
        
        Args:
            intensity: 强度数组
            window: 窗口大小（必须是奇数）
            method: 平滑方法
                - 'savgol': Savitzky-Golay滤波（默认，保持峰形）
                - 'moving_avg': 移动平均
                - 'gaussian': 高斯滤波
            polyorder: Savitzky-Golay滤波的多项式阶数
            
        Returns:
            np.ndarray: 平滑后的强度数组
        """
        intensity = np.asarray(intensity, dtype=float)
        
        # 确保窗口是奇数
        if window % 2 == 0:
            window += 1
        
        # 窗口不能超过数据长度
        window = min(window, len(intensity))
        if window < 3:
            return intensity
        
        if method == 'savgol':
            # Savitzky-Golay滤波
            polyorder = min(polyorder, window - 1)
            return signal.savgol_filter(intensity, window, polyorder)
        
        elif method == 'moving_avg':
            # 移动平均
            kernel = np.ones(window) / window
            return np.convolve(intensity, kernel, mode='same')
        
        elif method == 'gaussian':
            # 高斯滤波
            sigma = window / 6  # 经验值
            return signal.gaussian_filter1d(intensity, sigma)
        
        else:
            raise ValueError(f"未知的平滑方法: {method}")
    
    @staticmethod
    def baseline_correction(wavelength: np.ndarray, 
                           intensity: np.ndarray,
                           method: Literal['linear', 'polynomial', 'als'] = 'linear',
                           degree: int = 1,
                           regions: Optional[List[tuple]] = None) -> np.ndarray:
        """基线校正
        
        Args:
            wavelength: 波长数组
            intensity: 强度数组
            method: 校正方法
                - 'linear': 线性基线（使用两端点）
                - 'polynomial': 多项式拟合基线
                - 'als': 非对称最小二乘法（推荐）
            degree: 多项式阶数（用于'polynomial'方法）
            regions: 基线区域列表，每个元素是(start_wl, end_wl)元组
            
        Returns:
            np.ndarray: 基线校正后的强度数组
        """
        wavelength = np.asarray(wavelength, dtype=float)
        intensity = np.asarray(intensity, dtype=float)
        
        if method == 'linear':
            # 线性基线：连接首尾两点
            baseline = np.linspace(intensity[0], intensity[-1], len(intensity))
            return intensity - baseline
        
        elif method == 'polynomial':
            if regions is not None:
                # 使用指定区域拟合基线
                mask = np.zeros(len(wavelength), dtype=bool)
                for start, end in regions:
                    mask |= (wavelength >= start) & (wavelength <= end)
                wl_fit = wavelength[mask]
                int_fit = intensity[mask]
            else:
                # 使用所有点拟合
                wl_fit = wavelength
                int_fit = intensity
            
            coeffs = np.polyfit(wl_fit, int_fit, degree)
            baseline = np.polyval(coeffs, wavelength)
            return intensity - baseline
        
        elif method == 'als':
            # 非对称最小二乘法 (Asymmetric Least Squares)
            baseline = DataProcessor._als_baseline(intensity)
            return intensity - baseline
        
        else:
            raise ValueError(f"未知的基线校正方法: {method}")
    
    @staticmethod
    def _als_baseline(y: np.ndarray, lam: float = 1e5, p: float = 0.01, 
                      niter: int = 10) -> np.ndarray:
        """非对称最小二乘法计算基线
        
        Args:
            y: 输入信号
            lam: 平滑参数（越大越平滑）
            p: 不对称参数（越小基线越低）
            niter: 迭代次数
            
        Returns:
            np.ndarray: 基线
        """
        from scipy import sparse
        from scipy.sparse.linalg import spsolve
        
        L = len(y)
        D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L-2))
        w = np.ones(L)
        
        for _ in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.T)
            z = spsolve(Z, w * y)
            w = p * (y > z) + (1 - p) * (y < z)
        
        return z
    
    @staticmethod
    def interpolate_to_grid(wavelength: np.ndarray, 
                           intensity: np.ndarray,
                           new_wavelength: np.ndarray,
                           method: str = 'linear') -> np.ndarray:
        """将光谱插值到新的波长网格
        
        Args:
            wavelength: 原始波长数组
            intensity: 原始强度数组
            new_wavelength: 目标波长数组
            method: 插值方法 ('linear', 'cubic', 'nearest')
            
        Returns:
            np.ndarray: 插值后的强度数组
        """
        f = interpolate.interp1d(wavelength, intensity, kind=method, 
                                 fill_value='extrapolate')
        return f(new_wavelength)
    
    @staticmethod
    def find_peaks(wavelength: np.ndarray, 
                   intensity: np.ndarray,
                   threshold: float = 0.1,
                   min_distance: int = 5) -> List[dict]:
        """查找光谱峰
        
        Args:
            wavelength: 波长数组
            intensity: 强度数组
            threshold: 峰值阈值（相对于最大值的比例）
            min_distance: 峰之间的最小距离（数据点数）
            
        Returns:
            List[dict]: 峰信息列表，每个元素包含:
                - 'wavelength': 峰位波长
                - 'intensity': 峰强度
                - 'index': 峰位索引
        """
        # 计算阈值
        height = np.max(intensity) * threshold
        
        # 查找峰
        peaks, properties = signal.find_peaks(intensity, height=height, 
                                              distance=min_distance)
        
        results = []
        for idx in peaks:
            results.append({
                'wavelength': wavelength[idx],
                'intensity': intensity[idx],
                'index': idx
            })
        
        # 按强度排序
        results.sort(key=lambda x: x['intensity'], reverse=True)
        
        return results
    
    @staticmethod
    def subtract_spectrum(intensity1: np.ndarray, 
                         intensity2: np.ndarray,
                         factor: float = 1.0) -> np.ndarray:
        """光谱相减
        
        Args:
            intensity1: 被减光谱
            intensity2: 减去的光谱
            factor: 减法因子，result = intensity1 - factor * intensity2
            
        Returns:
            np.ndarray: 相减后的光谱
        """
        return intensity1 - factor * intensity2


# 便捷函数
def normalize(intensity: np.ndarray, method: str = 'max', **kwargs) -> np.ndarray:
    """便捷归一化函数"""
    return DataProcessor.normalize(intensity, method=method, **kwargs)


def smooth(intensity: np.ndarray, window: int = 5, **kwargs) -> np.ndarray:
    """便捷平滑函数"""
    return DataProcessor.smooth(intensity, window=window, **kwargs)


if __name__ == "__main__":
    # 测试代码
    # 创建测试数据
    wavelength = np.linspace(400, 700, 301)
    intensity = np.exp(-((wavelength - 500) ** 2) / (2 * 30 ** 2)) * 100
    intensity += np.random.normal(0, 2, len(intensity))  # 添加噪声
    
    # 测试归一化
    norm_max = DataProcessor.normalize(intensity, 'max')
    print(f"最大值归一化后最大值: {np.max(norm_max):.3f}")
    
    # 测试平滑
    smoothed = DataProcessor.smooth(intensity, window=11)
    print(f"平滑前后标准差: {np.std(intensity):.3f} -> {np.std(smoothed):.3f}")
    
    # 测试峰查找
    peaks = DataProcessor.find_peaks(wavelength, intensity)
    print(f"找到 {len(peaks)} 个峰")
    if peaks:
        print(f"最高峰位置: {peaks[0]['wavelength']:.1f} nm")
