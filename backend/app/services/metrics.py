"""
监控指标服务

用于采集、存储和查询系统监控指标
"""
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.logger import get_logger

logger = get_logger(__name__)


class MetricCollector:
    """
    指标采集器

    支持指标类型:
    - counter: 计数器（只增不减）
    - gauge: 仪表盘（可增可减）
    - histogram: 直方图（分布统计）
    """

    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._labels: Dict[str, Dict] = {}

    def inc(self, name: str, value: float = 1, labels: Optional[Dict] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        self._counters[key] += value
        if labels:
            self._labels[key] = labels
        logger.debug(f"Metric counter {key} incremented by {value}")

    def dec(self, name: str, value: float = 1, labels: Optional[Dict] = None):
        """减少计数器（用于 gauge）"""
        key = self._make_key(name, labels)
        self._counters[key] -= value
        if labels:
            self._labels[key] = labels

    def set(self, name: str, value: float, labels: Optional[Dict] = None):
        """设置仪表盘值"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
        if labels:
            self._labels[key] = labels
        logger.debug(f"Metric gauge {key} set to {value}")

    def observe(self, name: str, value: float, labels: Optional[Dict] = None):
        """观察值（用于直方图）"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
        # 限制存储数量，避免内存溢出
        if len(self._histograms[key]) > 10000:
            self._histograms[key] = self._histograms[key][-5000:]
        if labels:
            self._labels[key] = labels

    def get(self, name: str, labels: Optional[Dict] = None) -> Optional[float]:
        """获取指标值"""
        key = self._make_key(name, labels)
        if key in self._gauges:
            return self._gauges[key]
        if key in self._counters:
            return self._counters[key]
        return None

    def get_histogram_stats(self, name: str, labels: Optional[Dict] = None) -> Dict[str, Any]:
        """获取直方图统计"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {"count": 0, "sum": 0, "mean": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "sum": sum(sorted_values),
            "mean": sum(sorted_values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": self._percentile(sorted_values, 50),
            "p95": self._percentile(sorted_values, 95),
            "p99": self._percentile(sorted_values, 99),
        }

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not sorted_values:
            return 0
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f
        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)

    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """获取所有指标"""
        metrics = []

        for key, value in self._counters.items():
            metrics.append({
                "name": key.split("{")[0] if "{" in key else key,
                "type": "counter",
                "value": value,
                "labels": self._labels.get(key, {}),
            })

        for key, value in self._gauges.items():
            metrics.append({
                "name": key.split("{")[0] if "{" in key else key,
                "type": "gauge",
                "value": value,
                "labels": self._labels.get(key, {}),
            })

        for key in self._histograms.keys():
            metrics.append({
                "name": key.split("{")[0] if "{" in key else key,
                "type": "histogram",
                "stats": self.get_histogram_stats(key),
                "labels": self._labels.get(key, {}),
            })

        return metrics

    def clear(self):
        """清空所有指标"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._labels.clear()


# 全局指标采集器实例
_global_collector: Optional[MetricCollector] = None


def get_metric_collector() -> MetricCollector:
    """获取全局指标采集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricCollector()
    return _global_collector


# 便捷函数
def inc_metric(name: str, value: float = 1, labels: Optional[Dict] = None):
    """增加计数器指标"""
    get_metric_collector().inc(name, value, labels)


def set_metric(name: str, value: float, labels: Optional[Dict] = None):
    """设置仪表盘指标"""
    get_metric_collector().set(name, value, labels)


def observe_metric(name: str, value: float, labels: Optional[Dict] = None):
    """观察直方图指标"""
    get_metric_collector().observe(name, value, labels)


def get_metric(name: str, labels: Optional[Dict] = None) -> Optional[float]:
    """获取指标值"""
    return get_metric_collector().get(name, labels)


# 请求中间件辅助函数
class RequestMetrics:
    """请求指标采集"""

    def __init__(self):
        self._request_start_times: Dict[str, float] = {}

    def start_request(self, request_id: str):
        """开始请求计时"""
        self._request_start_times[request_id] = time.time()

    def end_request(self, request_id: str, path: str, method: str, status_code: int):
        """结束请求并记录指标"""
        start_time = self._request_start_times.pop(request_id, None)
        if start_time is None:
            return

        duration_ms = (time.time() - start_time) * 1000

        # 记录请求计数
        inc_metric("http_requests_total", labels={
            "path": path,
            "method": method,
            "status": str(status_code),
        })

        # 记录请求延迟
        observe_metric("http_request_duration_ms", duration_ms, labels={
            "path": path,
            "method": method,
        })

        # 记录当前活跃请求数
        active_requests = len(self._request_start_times)
        set_metric("http_requests_active", active_requests)


# 全局请求指标实例
_request_metrics = RequestMetrics()


def get_request_metrics() -> RequestMetrics:
    """获取请求指标采集器"""
    return _request_metrics
