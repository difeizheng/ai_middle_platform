"""
试点场景服务模块
"""
from .document_qa import DocumentQAService
from .contract_compare import ContractCompareService
from .smart客服 import SmartCustomerService
from .report_generate import ReportGenerateService

__all__ = [
    "DocumentQAService",
    "ContractCompareService",
    "SmartCustomerService",
    "ReportGenerateService",
]
