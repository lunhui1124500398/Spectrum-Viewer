"""Core module for data processing"""
from .data_model import SpectrumData
from .xls_reader import XLSReader
from .sif_reader import SIFReader, SIF_AVAILABLE
from .data_processor import DataProcessor

__all__ = ['SpectrumData', 'XLSReader', 'SIFReader', 'SIF_AVAILABLE', 'DataProcessor']
