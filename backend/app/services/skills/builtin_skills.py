"""
Skills 市场内置 Skills
"""
from typing import Dict, Any, List
import asyncio
from datetime import datetime

from ...core.logger import get_logger
from .base import BaseSkill, SkillDefinition

logger = get_logger(__name__)


class DataAnalysisSkill(BaseSkill):
    """
    数据分析 Skill

    提供基础的数据分析功能
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据分析

        Args:
            params: {
                "data": List[Dict],  # 数据列表
                "operation": str,  # 操作类型：statistic, group, aggregate, filter
                "config": Dict,  # 操作配置
            }

        Returns:
            分析结果
        """
        data = params.get("data", [])
        operation = params.get("operation", "statistic")
        config = params.get("config", {})

        self._increment_execution_count()

        try:
            if operation == "statistic":
                return self._calculate_statistics(data, config)
            elif operation == "group":
                return self._group_data(data, config)
            elif operation == "aggregate":
                return self._aggregate_data(data, config)
            elif operation == "filter":
                return self._filter_data(data, config)
            else:
                return {"error": f"不支持的操作：{operation}"}
        except Exception as e:
            logger.error(f"Data analysis error: {e}")
            return {"error": str(e)}

    def _calculate_statistics(self, data: List[Dict], config: Dict) -> Dict[str, Any]:
        """计算统计数据"""
        if not data:
            return {"count": 0, "statistics": {}}

        numeric_fields = config.get("fields", [])
        if not numeric_fields:
            # 自动检测数值字段
            if data and isinstance(data[0], dict):
                sample = data[0]
                numeric_fields = [k for k, v in sample.items() if isinstance(v, (int, float))]

        statistics = {}
        for field in numeric_fields:
            values = [row.get(field) for row in data if isinstance(row.get(field), (int, float))]
            if values:
                statistics[field] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return {"count": len(data), "statistics": statistics}

    def _group_data(self, data: List[Dict], config: Dict) -> Dict[str, Any]:
        """分组数据"""
        group_by = config.get("group_by", [])
        if not group_by or not data:
            return {"groups": {}}

        groups = {}
        for row in data:
            key = tuple(row.get(g) for g in group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        # 转换元组键为字符串
        result = {str(k): v for k, v in groups.items()}
        return {"groups": result, "group_count": len(groups)}

    def _aggregate_data(self, data: List[Dict], config: Dict) -> Dict[str, Any]:
        """聚合数据"""
        group_by = config.get("group_by", [])
        aggregations = config.get("aggregations", [])

        if not data:
            return {"result": {}}

        # 先分组
        if group_by:
            grouped = self._group_data(data, {"group_by": group_by})["groups"]
        else:
            grouped = {"all": data}

        result = {}
        for key, rows in grouped.items():
            agg_result = {}
            for agg in aggregations:
                field = agg.get("field")
                func = agg.get("function", "count")
                values = [r.get(field) for r in rows if isinstance(r.get(field), (int, float))]

                if func == "count":
                    agg_result[f"{field}_count"] = len(values) if values else len(rows)
                elif func == "sum":
                    agg_result[f"{field}_sum"] = sum(values) if values else 0
                elif func == "avg":
                    agg_result[f"{field}_avg"] = sum(values) / len(values) if values else 0
                elif func == "min":
                    agg_result[f"{field}_min"] = min(values) if values else None
                elif func == "max":
                    agg_result[f"{field}_max"] = max(values) if values else None

            result[key] = agg_result

        return {"result": result}

    def _filter_data(self, data: List[Dict], config: Dict) -> Dict[str, Any]:
        """过滤数据"""
        conditions = config.get("conditions", [])
        if not conditions or not data:
            return {"data": data, "count": len(data)}

        filtered = data
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator", "=")
            value = cond.get("value")

            if operator == "=":
                filtered = [r for r in filtered if r.get(field) == value]
            elif operator == "!=":
                filtered = [r for r in filtered if r.get(field) != value]
            elif operator == ">":
                filtered = [r for r in filtered if isinstance(r.get(field), (int, float)) and r.get(field) > value]
            elif operator == "<":
                filtered = [r for r in filtered if isinstance(r.get(field), (int, float)) and r.get(field) < value]
            elif operator == "contains":
                filtered = [r for r in filtered if value in str(r.get(field, ""))]

        return {"data": filtered, "count": len(filtered)}

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="data_analysis",
            description="数据分析技能 - 支持统计、分组、聚合、过滤等操作",
            category="analytics",
            version="1.0.0",
            author="AI Middle Platform",
            inputs=[
                {"name": "data", "type": "array", "required": True, "description": "数据列表"},
                {"name": "operation", "type": "string", "required": True, "description": "操作类型：statistic, group, aggregate, filter"},
                {"name": "config", "type": "object", "required": False, "description": "操作配置"},
            ],
            outputs=[{"name": "result", "type": "object", "description": "分析结果"}],
            config_schema={},
            tags=["数据分析", "统计", "聚合"],
        )


class ReportGeneratorSkill(BaseSkill):
    """
    报告生成 Skill

    生成结构化的报告文档
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成报告

        Args:
            params: {
                "title": str,  # 报告标题
                "sections": List[Dict],  # 章节列表
                "data": Dict,  # 报告数据
                "template": str,  # 模板类型：markdown, json, html
            }

        Returns:
            生成的报告
        """
        title = params.get("title", "分析报告")
        sections = params.get("sections", [])
        data = params.get("data", {})
        template = params.get("template", "markdown")

        self._increment_execution_count()

        try:
            if template == "markdown":
                return self._generate_markdown(title, sections, data)
            elif template == "json":
                return self._generate_json(title, sections, data)
            elif template == "html":
                return self._generate_html(title, sections, data)
            else:
                return {"error": f"不支持的模板：{template}"}
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return {"error": str(e)}

    def _generate_markdown(self, title: str, sections: List[Dict], data: Dict) -> Dict[str, Any]:
        """生成 Markdown 格式报告"""
        content = f"# {title}\n\n"
        content += f"*生成时间：{datetime.now().isoformat()}*\n\n"

        for section in sections:
            section_title = section.get("title", "")
            section_type = section.get("type", "text")
            section_data = section.get("data", {})

            content += f"## {section_title}\n\n"

            if section_type == "text":
                content += section_data.get("text", "") + "\n\n"
            elif section_type == "table":
                content += self._generate_markdown_table(section_data.get("headers", []), section_data.get("rows", []))
            elif section_type == "list":
                for item in section_data.get("items", []):
                    content += f"- {item}\n"
                content += "\n"
            elif section_type == "summary":
                for key, value in section_data.get("metrics", {}).items():
                    content += f"**{key}**: {value}\n\n"

        return {"content": content, "format": "markdown", "title": title}

    def _generate_markdown_table(self, headers: List[str], rows: List[List]) -> str:
        """生成 Markdown 表格"""
        if not headers:
            return ""

        table = "| " + " | ".join(str(h) for h in headers) + " |\n"
        table += "|" + "|".join("---" for _ in headers) + "|\n"
        for row in rows:
            table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        table += "\n"
        return table

    def _generate_json(self, title: str, sections: List[Dict], data: Dict) -> Dict[str, Any]:
        """生成 JSON 格式报告"""
        report = {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "sections": [],
        }

        for section in sections:
            report["sections"].append({
                "title": section.get("title", ""),
                "type": section.get("type", "text"),
                "content": section.get("data", {}),
            })

        report["data"] = data
        return {"content": report, "format": "json", "title": title}

    def _generate_html(self, title: str, sections: List[Dict], data: Dict) -> Dict[str, Any]:
        """生成 HTML 格式报告"""
        html = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p><em>生成时间：{datetime.now().isoformat()}</em></p>
"""

        for section in sections:
            section_title = section.get("title", "")
            section_type = section.get("type", "text")
            section_data = section.get("data", {})

            html += f"<h2>{section_title}</h2>\n"

            if section_type == "text":
                html += f"<p>{section_data.get('text', '')}</p>\n"
            elif section_type == "list":
                html += "<ul>\n"
                for item in section_data.get("items", []):
                    html += f"<li>{item}</li>\n"
                html += "</ul>\n"

        html += """
</body>
</html>
"""
        return {"content": html, "format": "html", "title": title}

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="report_generator",
            description="报告生成技能 - 支持 Markdown/JSON/HTML 格式",
            category="document",
            version="1.0.0",
            author="AI Middle Platform",
            inputs=[
                {"name": "title", "type": "string", "required": True, "description": "报告标题"},
                {"name": "sections", "type": "array", "required": True, "description": "章节列表"},
                {"name": "data", "type": "object", "required": False, "description": "报告数据"},
                {"name": "template", "type": "string", "required": False, "description": "模板类型", "default": "markdown"},
            ],
            outputs=[{"name": "report", "type": "object", "description": "生成的报告"}],
            config_schema={},
            tags=["报告生成", "文档", "Markdown"],
        )


class CodeReviewSkill(BaseSkill):
    """
    代码审查 Skill

    分析代码并提供改进建议
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行代码审查

        Args:
            params: {
                "code": str,  # 代码内容
                "language": str,  # 编程语言
                "rules": List[str],  # 审查规则
            }

        Returns:
            审查结果
        """
        code = params.get("code", "")
        language = params.get("language", "python")
        rules = params.get("rules", ["style", "security", "performance"])

        self._increment_execution_count()

        if not code:
            return {"error": "代码不能为空"}

        issues = []

        # 简化实现：基于规则的静态分析
        if language == "python":
            issues = self._review_python_code(code, rules)

        return {
            "issues": issues,
            "issue_count": len(issues),
            "language": language,
            "rules_applied": rules,
        }

    def _review_python_code(self, code: str, rules: List[str]) -> List[Dict]:
        """审查 Python 代码"""
        issues = []
        lines = code.split("\n")

        if "style" in rules:
            # 检查代码风格
            for i, line in enumerate(lines, 1):
                if len(line) > 100:
                    issues.append({
                        "line": i,
                        "type": "style",
                        "severity": "low",
                        "message": "行长度超过 100 字符",
                        "suggestion": "考虑将长行拆分",
                    })
                if line.endswith(" ") or line.endswith("\t"):
                    issues.append({
                        "line": i,
                        "type": "style",
                        "severity": "low",
                        "message": "行尾有多余空白",
                        "suggestion": "删除行尾空白",
                    })

        if "security" in rules:
            # 检查安全问题
            if "eval(" in code or "exec(" in code:
                issues.append({
                    "line": 0,
                    "type": "security",
                    "severity": "high",
                    "message": "使用 eval/exec 可能存在安全风险",
                    "suggestion": "使用 ast.literal_eval 或其他安全替代方案",
                })
            if "pickle" in code:
                issues.append({
                    "line": 0,
                    "type": "security",
                    "severity": "medium",
                    "message": "使用 pickle 可能存在反序列化风险",
                    "suggestion": "考虑使用 JSON 或其他安全序列化格式",
                })

        if "performance" in rules:
            # 检查性能问题
            if "for " in code and " in " in code:
                # 简单检查是否有列表推导式优化机会
                pass  # 可以添加更复杂的分析

        return issues

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="code_review",
            description="代码审查技能 - 分析代码并提供风格、安全、性能建议",
            category="development",
            version="1.0.0",
            author="AI Middle Platform",
            inputs=[
                {"name": "code", "type": "string", "required": True, "description": "代码内容"},
                {"name": "language", "type": "string", "required": False, "description": "编程语言", "default": "python"},
                {"name": "rules", "type": "array", "required": False, "description": "审查规则列表"},
            ],
            outputs=[{"name": "review", "type": "object", "description": "审查结果"}],
            config_schema={},
            tags=["代码审查", "静态分析", "Python"],
        )


class NotificationSkill(BaseSkill):
    """
    通知发送 Skill

    支持多种通知渠道
    """

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送通知

        Args:
            params: {
                "channel": str,  # 通知渠道：email, webhook, log
                "recipients": List[str],  # 接收者列表
                "subject": str,  # 主题
                "message": str,  # 消息内容
                "config": Dict,  # 渠道配置
            }

        Returns:
            发送结果
        """
        channel = params.get("channel", "log")
        recipients = params.get("recipients", [])
        subject = params.get("subject", "通知")
        message = params.get("message", "")
        config = params.get("config", {})

        self._increment_execution_count()

        try:
            if channel == "log":
                return self._send_log(subject, message, recipients)
            elif channel == "webhook":
                return await self._send_webhook(recipients, message, config)
            elif channel == "email":
                return await self._send_email(recipients, subject, message, config)
            else:
                return {"error": f"不支持的通知渠道：{channel}"}
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return {"error": str(e)}

    def _send_log(self, subject: str, message: str, recipients: List[str]) -> Dict[str, Any]:
        """发送日志通知"""
        logger.info(f"[Notification] {subject}: {message}")
        return {
            "success": True,
            "channel": "log",
            "subject": subject,
            "recipients_count": len(recipients),
        }

    async def _send_webhook(self, recipients: List[str], message: str, config: Dict) -> Dict[str, Any]:
        """发送 Webhook 通知"""
        import aiohttp

        results = []
        timeout = config.get("timeout", 10)

        async with aiohttp.ClientSession() as session:
            for url in recipients:
                try:
                    async with session.post(
                        url,
                        json={"message": message},
                        timeout=aiohttp.ClientTimeout(total=timeout),
                    ) as response:
                        results.append({
                            "url": url,
                            "status": response.status,
                            "success": response.status == 200,
                        })
                except Exception as e:
                    results.append({"url": url, "success": False, "error": str(e)})

        return {"channel": "webhook", "results": results}

    async def _send_email(self, recipients: List[str], subject: str, message: str, config: Dict) -> Dict[str, Any]:
        """发送邮件通知（简化实现）"""
        # 实际应该使用 SMTP 或邮件服务 API
        logger.info(f"Would send email to {recipients}: {subject}")
        return {
            "channel": "email",
            "recipients": recipients,
            "subject": subject,
            "simulated": True,
        }

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="notification",
            description="通知发送技能 - 支持日志/Webhook/Email 等渠道",
            category="communication",
            version="1.0.0",
            author="AI Middle Platform",
            inputs=[
                {"name": "channel", "type": "string", "required": True, "description": "通知渠道"},
                {"name": "recipients", "type": "array", "required": True, "description": "接收者列表"},
                {"name": "subject", "type": "string", "required": True, "description": "主题"},
                {"name": "message", "type": "string", "required": True, "description": "消息内容"},
                {"name": "config", "type": "object", "required": False, "description": "渠道配置"},
            ],
            outputs=[{"name": "result", "type": "object", "description": "发送结果"}],
            config_schema={},
            tags=["通知", "消息", "Email", "Webhook"],
        )


def register_builtin_skills(skill_registry) -> None:
    """注册所有内置 Skills"""
    skill_registry.register("data_analysis", DataAnalysisSkill(), {"category": "analytics"})
    skill_registry.register("report_generator", ReportGeneratorSkill(), {"category": "document"})
    skill_registry.register("code_review", CodeReviewSkill(), {"category": "development"})
    skill_registry.register("notification", NotificationSkill(), {"category": "communication"})

    logger.info("4 built-in skills registered")
