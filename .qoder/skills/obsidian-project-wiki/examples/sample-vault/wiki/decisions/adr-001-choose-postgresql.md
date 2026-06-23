# ADR-001: 数据库选型 — 选择 MySQL 8

> 状态：**已决定**  
> 日期：2026-06-22  
> 决策者：技术负责人、后端工程师

## 背景

社区养老平台 MVP 需要存储用户、打卡记录、服务工单等结构化数据，预估日活 500-1000 用户，数据量在百万级以内。

## 考虑的选项

### 选项 A：MySQL 8.0

**优势**：
- 团队有 3 年以上运维经验
- 阿里云 RDS MySQL 价格合理（2C4G 约 ¥300/月）
- 社区生态成熟，文档丰富

**劣势**：
- JSON 支持不如 PostgreSQL JSONB
- 无向量搜索原生扩展

### 选项 B：PostgreSQL 16

**优势**：
- 查询优化器更智能
- JSONB 类型支持索引
- 扩展生态丰富（pgvector、PostGIS）

**劣势**：
- 团队经验不足，学习成本高
- 云服务价格略高于 MySQL

## 最终决策

**选择 MySQL 8.0**。

## 理由

1. MVP 阶段以快速交付为优先，团队熟悉度是最大优势
2. 当前数据规模和查询复杂度不需要 PostgreSQL 的高级特性
3. 如果项目增长到需要向量搜索（AI 健康分析）或地理信息（就近服务站），可以在后续版本评估迁移

## 影响范围

- 后端 TypeORM 配置使用 MySQL 驱动
- 数据库初始化脚本使用 MySQL 语法
- 部署脚本中 MySQL 容器配置

## 相关链接

- 来源：[[source-kickoff-meeting]]
- 调研：[[raw/research/2026-06-22-database-comparison.md]]
- 架构：[[system-overview]]

## 标签

#decision #database #mysql
