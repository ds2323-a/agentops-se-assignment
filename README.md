# AgentOps · AI Agent 分级规划与失效分析平台

> 软件工程课程大作业 Demo —— 生成式软件工程实践
>
> 一个含**前端 + 后端 + 数据库**的全栈 Demo 系统。系统将 AI Agent 贯穿软件工程全流程，
> 核心演示 **L1/L2/L3 三级分级规划机制** 与 **Agent 失效评分 / 监管闭环**。

## 1. 功能特性

| 模块 | 说明 |
|------|------|
| 工作台概览 | 任务统计、分级分布、Agent 可靠性评级、最近任务 |
| 任务管理 | 任务增删改查、状态跟踪、按等级/状态/关键字筛选 |
| 分级规划 | 输入任务描述 → 风险评分 → L1/L2/L3 分级 → 层级子任务拆解 |
| 失效分析 | 缺陷帕累托分析、失效评分排行、失效复盘与升级建议 |
| Agent 执行 | 模拟 Agent 执行；失败自动升级为 L3 人工介入 |
| 基础设施 | 集中配置校验、类型化错误、结构化 JSON 日志、健康检查、CORS、安全头 |

## 2. 技术栈

- **后端**：Python 3.10+ 标准库 `http.server`（ThreadingHTTPServer，零第三方 Web 依赖）
- **数据库**：SQLite（WAL 模式，外键约束，可回滚迁移 + 幂等种子数据）
- **前端**：原生 HTML5 + CSS3 + ES6（无构建步骤，类型化 fetch 封装 + 统一错误映射）
- **架构**：按功能组织 + 三层架构（Controller → Service → Repository）

## 3. 目录结构

```
agentops/
├── run.py                  # 启动入口
├── app/
│   ├── config.py           # 集中配置与启动校验
│   ├── errors.py           # 类型化错误体系
│   ├── logging_util.py     # 结构化 JSON 日志（含 request_id，脱敏）
│   ├── db.py               # 连接池 / 迁移 / 种子数据 / 事务
│   ├── services.py         # 业务层：分级规划、失效评分、帕累托分析
│   ├── controllers.py      # 控制器层：路由分发
│   └── server.py           # HTTP 服务 / 中间件 / 静态资源
├── web/                    # 前端单页应用
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
│   ├── test_services.py    # 模块单元测试（5 项）
│   └── test_api.py         # API 集成测试（9 项，真实服务+真实 DB）
├── tools/gen_diagrams.py   # 报告图表生成脚本
├── data/                   # SQLite 数据库（.gitignore 忽略）
├── .env.example            # 配置模板（仅占位值）
└── README.md
```

## 4. 启动与验证

```bash
# 可选：复制配置模板并按需修改
cp .env.example .env

# 启动服务（首次启动自动建库 + 迁移 + 种子数据）
python run.py
# 访问 http://127.0.0.1:8787

# 健康检查
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/ready

# 运行测试
python tests/test_services.py
python tests/test_api.py
```

## 5. API 端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 存活探针 |
| GET | `/ready` | 就绪探针（含数据库检查） |
| POST | `/api/auth/login` | 演示登录 |
| GET | `/api/tasks` | 任务列表（支持 status/level/project 过滤） |
| POST | `/api/tasks` | 创建任务（自动分级 + 生成规划树） |
| GET | `/api/tasks/{id}` | 任务详情 |
| PATCH | `/api/tasks/{id}` | 更新任务 |
| DELETE | `/api/tasks/{id}` | 删除任务 |
| GET | `/api/tasks/{id}/plan` | 获取层级规划树 |
| GET/POST | `/api/tasks/{id}/runs` | 查询/记录 Agent 执行 |
| POST | `/api/planning/classify` | AI 分级规划（风险评分 + 分级依据） |
| GET | `/api/analysis/overview` | 全局统计 |
| GET | `/api/analysis/pareto` | 缺陷帕累托 |
| GET | `/api/analysis/failure-scores` | 失效评分列表 |
| GET | `/api/analysis/reliability` | 可靠性评级分布 |

## 6. 分级机制（核心）

- **L1 自动完成**：低风险、边界清晰（批量清洗 / 报表导出 / 日志检索），Agent 全自动。
- **L2 人机协作**：AI 生成候选方案 + 人工评审闸口（设计 / 接口 / 前端 / 文档）。
- **L3 纯人工**：高风险决策（支付 / 风控 / 合规 / 签署），AI 仅辅助检索，人工主导并强制复盘。

风险评分公式：`score = 14 + 6×L2关键词 + 20×L3关键词 − 4×L1关键词`
判定阈值：`≥55 → L3`，`25–54 → L2`，`<25 → L1`。

## 7. 失效评分（核心）

`Score = 96 − Σ(严重度权重 × 归因系数)`

- 严重度权重：critical=18，major=9，minor=3
- 归因系数：agent=1.0，tool=0.7，requirement=0.6，human=0.5
- 评级：A(≥90) 稳定 / B(80–89) 可用 / C(70–79) 预警 / D(<70) 失效
- 监管闭环：D 级 → 升级 L3 人工；C 级 → 保持 L2 并补回归用例；复盘结论回流分级规则库。

## 8. 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| alice | alice123 | 工程师 |
| bob | bob123 | 工程师 |

> 演示用途的明文凭据仅存在于代码常量中，生产环境应改用哈希存储 + OAuth/JWT。
