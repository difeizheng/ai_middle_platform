"""
场景 4: 报告生成服务
自动生成数据分析报告、会议纪要等
"""
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ...core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReportRequest:
    """报告生成请求"""
    report_type: str  # analysis, meeting, weekly, monthly
    title: str
    data: Dict[str, Any]
    template: Optional[str] = None
    format: str = "markdown"  # markdown, html, docx


@dataclass
class ReportResponse:
    """报告生成响应"""
    report_id: str
    title: str
    content: str
    format: str
    created_at: datetime
    sections: List[str]


class ReportGenerateService:
    """
    报告生成服务

    功能:
    1. 数据分析报告
    2. 会议纪要
    3. 周报/月报
    4. 自定义报告
    """

    def __init__(self):
        self.llm_service = None
        self.report_templates = {
            "analysis": self._analysis_template,
            "meeting": self._meeting_template,
            "weekly": self._weekly_template,
            "monthly": self._monthly_template,
        }

    async def initialize(self):
        """初始化"""
        from ..llm import get_llm_service
        self.llm_service = get_llm_service()

    async def generate(self, request: ReportRequest) -> ReportResponse:
        """
        生成报告

        Args:
            request: 报告请求

        Returns:
            ReportResponse: 报告响应
        """
        import uuid

        # 获取模板
        template_func = self.report_templates.get(
            request.report_type,
            self._default_template
        )

        # 生成报告大纲
        outline = template_func(request.data)

        # 调用 LLM 生成内容
        content = await self._generate_content(
            title=request.title,
            outline=outline,
            data=request.data,
        )

        # 解析章节
        sections = self._parse_sections(content)

        logger.info(f"报告生成完成：{request.title}")

        return ReportResponse(
            report_id=f"report_{uuid.uuid4().hex[:12]}",
            title=request.title,
            content=content,
            format=request.format,
            created_at=datetime.now(),
            sections=sections,
        )

    def _analysis_template(self, data: Dict[str, Any]) -> str:
        """数据分析报告模板"""
        return f"""
# {data.get('title', '数据分析报告')}

## 一、数据概览
- 数据时间范围：{data.get('date_range', '待填写')}
- 数据来源：{data.get('source', '待填写')}
- 核心指标：{data.get('metrics', [])}

## 二、关键发现
[待生成]

## 三、趋势分析
[待生成]

## 四、问题识别
[待生成]

## 五、建议措施
[待生成]
"""

    def _meeting_template(self, data: Dict[str, Any]) -> str:
        """会议纪要模板"""
        return f"""
# {data.get('title', '会议纪要')}

## 基本信息
- 会议时间：{data.get('date', '待填写')}
- 会议地点：{data.get('location', '待填写')}
- 参会人员：{data.get('attendees', [])}

## 会议议题
{chr(10).join(f"- {topic}" for topic in data.get('topics', []))}

## 讨论内容
[待生成]

## 决议事项
[待生成]

## 待办任务
[待生成]
"""

    def _weekly_template(self, data: Dict[str, Any]) -> str:
        """周报模板"""
        return f"""
# {data.get('title', '工作周报')}

## 本周工作总结
[待生成]

## 重点工作进展
[待生成]

## 问题与风险
[待生成]

## 下周工作计划
[待生成]
"""

    def _monthly_template(self, data: Dict[str, Any]) -> str:
        """月报模板"""
        return f"""
# {data.get('title', '工作月报')}

## 本月工作目标完成情况
[待生成]

## 重点项目进展
[待生成]

## 数据分析
[待生成]

## 问题与挑战
[待生成]

## 下月工作计划
[待生成]
"""

    def _default_template(self, data: Dict[str, Any]) -> str:
        """默认模板"""
        return f"""
# {data.get('title', '报告')}

## 概述
[待生成]

## 正文
[待生成]

## 总结
[待生成]
"""

    async def _generate_content(
        self,
        title: str,
        outline: str,
        data: Dict[str, Any],
    ) -> str:
        """调用 LLM 生成报告内容"""
        prompt = f"""请根据以下信息生成一份完整的报告：

报告标题：{title}

报告大纲：
{outline}

相关数据：
{self._format_data(data)}

要求：
1. 内容专业、条理清晰
2. 数据准确、分析深入
3. 语言简洁、重点突出
4. 格式规范、层次分明

请生成完整的报告内容：
"""

        if not self.llm_service:
            await self.initialize()

        response = await self.llm_service.generate(
            prompt=prompt,
            max_tokens=4096,
        )

        return response.content

    def _format_data(self, data: Dict[str, Any]) -> str:
        """格式化数据"""
        parts = []
        for key, value in data.items():
            if isinstance(value, list):
                parts.append(f"{key}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, dict):
                parts.append(f"{key}: {self._format_data(value)}")
            else:
                parts.append(f"{key}: {value}")
        return "\n".join(parts)

    def _parse_sections(self, content: str) -> List[str]:
        """解析章节"""
        sections = []
        lines = content.split("\n")

        for line in lines:
            if line.startswith("#"):
                section = line.lstrip("#").strip()
                sections.append(section)

        return sections

    async def generate_meeting_summary(
        self,
        title: str,
        transcript: str,
        date: str = None,
        attendees: List[str] = None,
    ) -> ReportResponse:
        """
        生成会议纪要

        Args:
            title: 会议标题
            transcript: 会议记录
            date: 会议日期
            attendees: 参会人员

        Returns:
            ReportResponse: 会议纪要
        """
        request = ReportRequest(
            report_type="meeting",
            title=title,
            data={
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "attendees": attendees or [],
                "transcript": transcript,
            },
        )
        return await self.generate(request)

    async def generate_analysis_report(
        self,
        title: str,
        data: Dict[str, Any],
        metrics: List[str] = None,
    ) -> ReportResponse:
        """
        生成数据分析报告

        Args:
            title: 报告标题
            data: 数据
            metrics: 核心指标

        Returns:
            ReportResponse: 分析报告
        """
        request = ReportRequest(
            report_type="analysis",
            title=title,
            data={
                **data,
                "metrics": metrics or [],
            },
        )
        return await self.generate(request)


# 全局服务实例
_report_service: Optional[ReportGenerateService] = None


def get_report_service() -> ReportGenerateService:
    """获取报告生成服务实例"""
    global _report_service
    if _report_service is None:
        _report_service = ReportGenerateService()
    return _report_service
