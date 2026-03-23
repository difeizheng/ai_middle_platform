"""
场景 2: 合同文本比对服务
对比两份合同的差异，识别风险条款
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ...core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CompareRequest:
    """比对请求"""
    text1: str  # 原文本
    text2: str  # 比对文本
    compare_type: str = "full"  # full, clause, risk


@dataclass
class DiffResult:
    """差异结果"""
    position: str
    original: str
    modified: str
    diff_type: str  # added, removed, modified
    severity: str  # high, medium, low


@dataclass
class CompareResponse:
    """比对响应"""
    similarity: float  # 相似度
    diffs: List[DiffResult]
    risk_clauses: List[Dict[str, Any]]
    summary: str


class ContractCompareService:
    """
    合同文本比对服务

    功能:
    1. 文本预处理和分段
    2. 差异比对（新增、删除、修改）
    3. 风险条款识别
    4. 相似度计算
    """

    def __init__(self):
        # 常见合同条款类型
        self.clause_types = [
            "定义条款",
            "服务内容",
            "服务费用",
            "付款方式",
            "服务期限",
            "保密条款",
            "知识产权",
            "违约责任",
            "争议解决",
            "其他约定",
        ]

        # 风险关键词
        self.risk_keywords = {
            "high": ["无限责任", "连带责任", "永久保密", "单方解除", "排他性"],
            "medium": ["违约金", "赔偿金", "自动续期", "提前通知", "书面同意"],
            "low": ["协商", "尽量", "优先", "原则上", "一般"],
        }

    def compare(self, request: CompareRequest) -> CompareResponse:
        """
        执行合同比对

        Args:
            request: 比对请求

        Returns:
            CompareResponse: 比对结果
        """
        # Step 1: 文本预处理
        clauses1 = self._split_clauses(request.text1)
        clauses2 = self._split_clauses(request.text2)

        # Step 2: 条款比对
        diffs = self._compare_clauses(clauses1, clauses2)

        # Step 3: 计算相似度
        similarity = self._calculate_similarity(clauses1, clauses2, diffs)

        # Step 4: 识别风险条款
        risk_clauses = self._identify_risks(request.text2)

        # Step 5: 生成总结
        summary = self._generate_summary(similarity, diffs, risk_clauses)

        logger.info(f"合同比对完成：相似度 {similarity:.2f}%, 差异 {len(diffs)} 处")

        return CompareResponse(
            similarity=similarity,
            diffs=diffs,
            risk_clauses=risk_clauses,
            summary=summary,
        )

    def _split_clauses(self, text: str) -> Dict[str, str]:
        """将合同文本分割为条款"""
        clauses = {}

        # 按条款编号分割
        pattern = r'([第][\d 零一二三四五六七八九十百]+[条])[：:\s]*(.*?)(?=[第][\d 零一二三四五六七八九十百]+[条]|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        for clause_num, content in matches:
            clauses[clause_num] = content.strip()

        # 如果没有找到条款编号，按段落分割
        if not clauses:
            paragraphs = text.split('\n\n')
            for i, para in enumerate(paragraphs, 1):
                if para.strip():
                    clauses[f"段落{i}"] = para.strip()

        return clauses

    def _compare_clauses(
        self,
        clauses1: Dict[str, str],
        clauses2: Dict[str, str],
    ) -> List[DiffResult]:
        """比对条款差异"""
        diffs = []

        all_keys = set(clauses1.keys()) | set(clauses2.keys())

        for key in all_keys:
            if key not in clauses1:
                # 新增条款
                diffs.append(DiffResult(
                    position=key,
                    original="",
                    modified=clauses2.get(key, ""),
                    diff_type="added",
                    severity="medium",
                ))
            elif key not in clauses2:
                # 删除条款
                diffs.append(DiffResult(
                    position=key,
                    original=clauses1.get(key, ""),
                    modified="",
                    diff_type="removed",
                    severity="medium",
                ))
            elif clauses1[key] != clauses2[key]:
                # 修改条款
                diff_detail = self._text_diff(clauses1[key], clauses2[key])
                diffs.append(DiffResult(
                    position=key,
                    original=clauses1[key],
                    modified=clauses2[key],
                    diff_type="modified",
                    severity=diff_detail.get("severity", "low"),
                ))

        return diffs

    def _text_diff(self, text1: str, text2: str) -> Dict[str, Any]:
        """文本差异分析"""
        # 简单实现：计算编辑距离和变化比例
        len1, len2 = len(text1), len(text2)

        # 计算变化比例
        if len1 == 0 and len2 == 0:
            return {"severity": "low", "changes": []}

        if len1 == 0:
            return {"severity": "high", "changes": [("added", text2)]}

        if len2 == 0:
            return {"severity": "high", "changes": [("removed", text1)]}

        # 简单的单词/字符比对
        changes = []
        severity = "low"

        # 检查是否有重大变化
        change_ratio = abs(len1 - len2) / max(len1, len2)
        if change_ratio > 0.5:
            severity = "high"
        elif change_ratio > 0.2:
            severity = "medium"

        # 识别具体变化
        words1 = set(text1.split())
        words2 = set(text2.split())

        added = words2 - words1
        removed = words1 - words2

        if added:
            changes.append(("added", " ".join(added)))
        if removed:
            changes.append(("removed", " ".join(removed)))

        return {"severity": severity, "changes": changes}

    def _calculate_similarity(
        self,
        clauses1: Dict[str, str],
        clauses2: Dict[str, str],
        diffs: List[DiffResult],
    ) -> float:
        """计算相似度"""
        total_clauses = len(clauses1) + len(clauses2)
        if total_clauses == 0:
            return 100.0

        # 基于差异数量计算相似度
        diff_count = len(diffs)
        modified_count = sum(1 for d in diffs if d.diff_type == "modified")

        # 相似度 = 1 - (差异权重 / 总条款数)
        diff_weight = sum(
            1.0 if d.diff_type == "added" or d.diff_type == "removed" else 0.5
            for d in diffs
        )

        similarity = (1 - diff_weight / total_clauses) * 100
        return max(0, min(100, similarity))

    def _identify_risks(self, text: str) -> List[Dict[str, Any]]:
        """识别风险条款"""
        risks = []

        # 检查风险关键词
        for severity, keywords in self.risk_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    # 找到关键词所在的句子
                    sentences = re.split(r'[。！？.!?]', text)
                    for sentence in sentences:
                        if keyword in sentence:
                            risks.append({
                                "keyword": keyword,
                                "content": sentence.strip()[:200],
                                "severity": severity,
                                "suggestion": self._get_suggestion(keyword, severity),
                            })

        return risks

    def _get_suggestion(self, keyword: str, severity: str) -> str:
        """获取修改建议"""
        suggestions = {
            "无限责任": "建议明确责任上限，如合同金额的倍数",
            "连带责任": "建议修改为按份责任",
            "永久保密": "建议设置保密期限，如 3-5 年",
            "单方解除": "建议增加解除条件和通知期限",
            "排他性": "建议评估是否影响业务灵活性",
            "违约金": "建议明确违约金计算方式和上限",
            "自动续期": "建议改为到期协商续期",
        }
        return suggestions.get(keyword, f"建议审查该{severity}风险条款")

    def _generate_summary(
        self,
        similarity: float,
        diffs: List[DiffResult],
        risk_clauses: List[Dict[str, Any]],
    ) -> str:
        """生成比对总结"""
        parts = []

        # 相似度总结
        if similarity >= 90:
            parts.append("两份合同高度相似")
        elif similarity >= 70:
            parts.append("两份合同有较多相似之处")
        else:
            parts.append("两份合同差异较大")

        # 差异统计
        added = sum(1 for d in diffs if d.diff_type == "added")
        removed = sum(1 for d in diffs if d.diff_type == "removed")
        modified = sum(1 for d in diffs if d.diff_type == "modified")

        parts.append(f"新增{added}条，删除{removed}条，修改{modified}条")

        # 风险统计
        high_risks = sum(1 for r in risk_clauses if r["severity"] == "high")
        if high_risks > 0:
            parts.append(f"发现{high_risks}条高风险条款，请重点关注")

        return "，".join(parts) + "。"


# 全局服务实例
_compare_service: Optional[ContractCompareService] = None


def get_compare_service() -> ContractCompareService:
    """获取比对服务实例"""
    global _compare_service
    if _compare_service is None:
        _compare_service = ContractCompareService()
    return _compare_service
