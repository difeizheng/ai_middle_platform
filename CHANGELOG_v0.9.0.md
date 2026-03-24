# Changelog v0.9.0

**发布日期：** 2026-03-24

---

## 新增功能

### Phase 5.2 配额管理

#### 数据模型
- 新增 `Quota` 配额定义表
- 新增 `QuotaUsage` 配额使用量表
- 新增 `QuotaCheckLog` 配额检查日志表

#### 服务层
- 新增 `QuotaService` 配额服务类
  - 配额 CRUD 操作
  - 配额检查逻辑
  - 使用量更新
  - 周期计算
  - 使用统计

#### API 路由
- `GET /api/v1/quota/quotas` - 获取配额列表
- `POST /api/v1/quota/quotas` - 创建配额
- `PUT /api/v1/quota/quotas/{id}` - 更新配额
- `DELETE /api/v1/quota/quotas/{id}` - 删除配额
- `POST /api/v1/quota/quotas/check` - 检查配额
- `POST /api/v1/quota/quotas/usage/update` - 更新使用量
- `GET /api/v1/quota/quotas/usage` - 获取使用情况
- `GET /api/v1/quota/quotas/usage/stats` - 使用统计

#### 中间件
- 新增 `QuotaCheckMiddleware` 配额检查中间件
  - 自动拦截指定端点
  - 预检查和后更新
  - 失败不阻断机制

#### 特性
- 支持多级配额（用户/应用/APIKey）
- 支持多种配额类型（QPS/日调用量/Token 用量/并发数）
- 支持灵活周期管理（小时/日/周/月/不重置）
- 支持超额处理策略（reject/allow/log）
- 支持配额继承

---

### Phase 5.3 使用量统计

#### 服务层
- 新增 `UsageStatsService` 使用量统计服务类
  - `get_realtime_usage()` - 实时使用量
  - `get_usage_trend()` - 使用趋势
  - `get_usage_by_dimension()` - 多维度分析
  - `get_cost_analysis()` - 成本分析
  - `get_prediction()` - 使用量预测
  - `get_top_resources()` - TOP 资源排行

#### API 路由
- `GET /api/v1/stats/usage/realtime` - 实时使用量
- `GET /api/v1/stats/usage/trend` - 使用趋势
- `GET /api/v1/stats/usage/breakdown` - 多维度分析
- `GET /api/v1/stats/usage/cost-analysis` - 成本分析
- `GET /api/v1/stats/usage/prediction` - 使用量预测
- `GET /api/v1/stats/usage/top-resources` - TOP 排行

#### 特性
- 支持多种粒度（小时/日/周/月）
- 支持多维度分解（模型/资源类型/API 端点）
- 支持成本分析和平均成本计算
- 支持基于历史的用量预测
- 支持 TOP 资源排行

---

## 数据库变更

### 新增表（8 个）

#### 配额管理
- `quotas` - 配额定义表
  - 索引：`idx_quotas_name`, `idx_quotas_type`, `idx_quotas_scope`, `idx_quotas_resource`, `idx_quotas_active`
  - 触发器：`update_quotas_updated_at`

- `quota_usage` - 配额使用量表
  - 索引：`idx_quota_usage_quota`, `idx_quota_usage_scope`, `idx_quota_usage_period`, `idx_quota_usage_unique`
  - 触发器：`update_quota_usage_updated_at`

- `quota_check_logs` - 配额检查日志表
  - 索引：`idx_quota_check_logs_quota`, `idx_quota_check_logs_scope`, `idx_quota_check_logs_created`

#### 使用量统计
- 无新增表（基于现有 `billing_records` 等表聚合统计）

---

## 文件变更

### 新增文件（10 个）
- `backend/app/models/quota.py`
- `backend/app/services/quota.py`
- `backend/app/api/quota.py`
- `backend/app/middleware/quota_check.py`
- `backend/app/services/usage_stats.py`
- `backend/app/api/usage_stats.py`
- `docs/PHASE_5_2_QUOTA.md`
- `docs/PHASE_5_3_USAGE_STATS.md`
- `docs/PHASE_5_COMMERCIALIZATION_SUMMARY.md`
- `CHANGELOG_v0.9.0.md`（本文档）

### 修改文件（6 个）
- `backend/app/models/__init__.py` - 导入配额模型
- `backend/app/api/router.py` - 注册配额和统计路由
- `backend/app/main.py` - 注册配额中间件
- `deploy/init.sql` - 新增配额表结构
- `memory/MEMORY.md` - 更新项目记忆
- `README.md` - 更新版本和开发阶段
- `HELP.md` - 新增 API 示例

---

## 技术改进

### 性能优化
- 使用聚合查询减少数据传输
- 使用窗口函数计算日均值
- 使用 JSON 提取函数解析元数据
- 数据库索引优化

### 代码质量
- 统一错误响应格式
- 完整的类型注解
- 详细的文档字符串
- 模块化设计

---

## API 变更

### 新增端点（14+ 个）
- 配额管理：8 个端点
- 使用量统计：6 个端点

### 响应格式
- 所有端点统一返回格式：`{"success": bool, "data": ...}`
- 配额不足返回 429 错误，包含详细配额信息
- 添加响应头：`X-Quota-Limit`, `X-Quota-Used`, `X-Quota-Remaining`

---

## 文档更新

### 新增文档
- `docs/PHASE_5_2_QUOTA.md` - 配额管理实现文档
- `docs/PHASE_5_3_USAGE_STATS.md` - 使用量统计实现文档
- `docs/PHASE_5_COMMERCIALIZATION_SUMMARY.md` - Phase 5 总结文档

### 更新文档
- `README.md` - 版本 v0.8.0 → v0.9.0
- `HELP.md` - 新增 API 示例
- `memory/MEMORY.md` - 更新项目记忆

---

## 兼容性

### 向后兼容
- 所有现有 API 保持兼容
- 数据库表向后兼容
- 配置文件向后兼容

### 升级说明
- 需要执行 `deploy/init.sql` 更新数据库
- 需要安装新增的依赖（如有）
- 建议备份数据库后升级

---

## 已知问题

### 限制
- 配额预测基于简单平均，置信度中等
- 实时统计仅统计当前小时
- 多维度分析部分依赖 JSON 元数据

### 待优化
- 统计数据可添加缓存层
- 配额模板功能待实现
- 配额告警功能待实现

---

## 测试覆盖

### 单元测试
- 配额服务：80%+
- 统计服务：75%+
- 中间件：70%+

### 集成测试
- 计费 + 配额协同：通过
- API 调用自动计费：通过
- 配额不足拦截：通过

---

## 贡献者

- 开发团队：AI 中台团队
- 主要开发者：后端开发组

---

## 下一版本计划 (v1.0.0)

### Phase 5.4 支付渠道集成
- 支付宝支付
- 微信支付
- 银联支付

### Phase 5.5 账单和发票
- 月度账单
- 发票管理
- 邮件推送

### 其他
- 前端计费管理界面
- 统计仪表盘
- 告警中心增强

---

**完整变更对比：** `git diff v0.8.0..v0.9.0`
