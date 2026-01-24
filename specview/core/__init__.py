"""Core module for data processing"""
from .xls_reader import XLSReader, SpectrumData
from .data_processor import DataProcessor

__all__ = ['XLSReader', 'SpectrumData', 'DataProcessor']
