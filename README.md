# casemap

> 功能测试用例图管理系统 · 从接口列表逆向生成可视化测试用例脑图，给非技术测试人员 / 产品人员使用。

## 一句话简介

把 Swagger / OpenAPI / Postman / Apifox 导出的接口列表 → 一键生成精美的可视化测试用例脑图（**单个自包含 HTML 文件**）。
测试人员 / PM 打开脑图 → 手动测试 → 点按钮标记状态 → 导出 Markdown 报告或 JSON 进度。
**零安装前端、零后端、零 CDN，单 HTML 文件双击即可用。**

## 安装

当前版本为 **v0.1.0**，尚未发布到 PyPI。从源码运行：

```bash
git clone https://github.com/anomalyco/casemap
cd casemap
uv sync
uv run casemap --help
```

或临时使用（无需 clone）：

```bash
uv run --from /path/to/casemap casemap generate swagger.json -o cases.html
```

## 快速使用

### 1. 准备接口列表

从你常用的接口文档工具导出一份 JSON：

| 来源 | 导出方法 |
|------|----------|
| SwaggerUI | 页面顶部 "Download JSON" → `swagger.json` |
| OpenAPI 3.x | 同上，或 `redocly bundle` 合并多文件 |
| Postman | Export → Collection v2.1 → `postman.json` |
| Apifox | 项目设置 → 导出 OpenAPI 格式 → `apifox.json` |

### 2. 生成脑图（一次）

```bash
uv run casemap generate swagger.json -o cases.html
```

打开 `cases.html`：

- 左侧：**SVG 脑图**，按 `tags` 分列，按 `CaseType` 着色（✅正向 / ❌逆向 / 🔶边界 / 🛡安全）
- 右侧：选中节点后查看用例详情（步骤 + 备注）
- 顶栏：**进度条** + 「💾 导出进度」「📥 导入进度」「📤 导出报告」三个按钮

### 3. 测试（重复）

- 点击节点 → 看用例详情
- 去业务系统手动执行
- 回到脑图，点状态按钮：`✅ 通过` / `❌ 失败` / `🚫 阻塞` / `⏭️ 跳过`
- 状态自动保存到浏览器 **localStorage**（无需登录、无需后端）
- 进度条实时更新

### 4. 跨设备 / 跨浏览器同步

- 顶栏「💾 导出进度」→ 下载 `casemap-status-YYYY-MM-DD.json`
- 换电脑 / 换浏览器 → 打开同一份 HTML → 顶栏「📥 导入进度」→ 选择刚才的 JSON
- 用例 ID 用 BLAKE2b 内容指纹生成，重新生成同一份接口列表后**状态自动对得上**

### 5. 导出报告

顶栏「📤 导出报告」→ 下载 `test-report.md`（Markdown 表格）→ 邮件 / 钉钉 / 飞书发给开发。

## 可选：AI 增强（业务语言用例）

默认用例是**启发式生成**的（含 "正向路径 / 缺失必填参数" 这类技术语）。
启用 LLM 后，标题与描述会被改写为纯业务语言（"用户可以重置自己的密码"）：

```bash
export CASEMAP_LLM_API_KEY=sk-...
uv run casemap generate swagger.json -o cases.html --llm --model gpt-4o-mini
```

任何 **OpenAI 兼容**服务都可以（OpenAI、DeepSeek、Moonshot、Qwen、Zhipu、Ollama 等）：

```bash
export CASEMAP_LLM_BASE_URL=https://api.deepseek.com/v1
export CASEMAP_LLM_API_KEY=sk-...
uv run casemap generate swagger.json -o cases.html --llm --model deepseek-chat
```

**LLM 失败时自动回退**到结构化用例，脑图照常可用 — 永远不会被卡住。

## 支持的接口文档格式

| 格式 | 说明 |
|------|------|
| OpenAPI 3.x / Swagger 2.0 | 通过 `prance` 自动解析 `$ref` |
| Postman v2.1 collection | 标准 Postman 导出 |
| Apifox | 委托给 OpenAPI 解析器（Apifox 导出本身就是 OpenAPI 格式） |

自动识别（无需指定），也可以显式 `--parser openapi|postman|apifox`：

```bash
uv run casemap parsers list   # 看当前已注册的解析器
```

## CLI 子命令

```bash
uv run casemap generate  spec.json -o cases.html     # 生成脑图
uv run casemap validate  spec.json                   # 只解析，不生成
uv run casemap parsers   list                        # 列出已注册的解析器
uv run casemap serve     --port 8765 --db ./casemap.db   # 启动 REST API 服务
```

`resume` 子命令已注册但暂未实现（没有 HTML→spec 的回程），
重新生成时只要接口列表不变，状态会自动接上。

## Server 模式（v0.2+ · SP-2）

`casemap serve` 启动一个 FastAPI + SQLite 的 REST 服务，方便多设备实时同步、CI 集成与报告存档。
核心思路与单机模式一致：上传接口列表 → 自动生成脑图 → 状态持久化到 DB，
不再依赖浏览器 localStorage。 同一份 spec 可多人协作、CI 注入自动更新进度。

```bash
uv run casemap serve --host 0.0.0.0 --port 8765 --db ./casemap.db
# 然后用 `curl` 或浏览器访问 http://127.0.0.1:8765/docs
```

主要 endpoint（全部 `/api/v1/...`）：

| Endpoint | 说明 |
|----------|------|
| `POST /projects` | 创建项目，返回一次性 `project_api_key`（后续请求用作 Bearer token） |
| `POST /projects/{id}/specs` | 上传 spec 文件（multipart），同步生成脑图 |
| `GET /projects/{id}/graphs/{graph_id}/{svg,html,report,graph.json}` | 渲染产物 |
| `GET /projects/{id}/cases` / `PATCH .../cases/{id}/status` | 列出 / 更新用例状态 |
| `GET /projects/{id}/progress` | 聚合进度（与单机脑图 `progress` 字段同源） |
| `POST/GET /projects/{id}/statuses/{import,export}` | 跨设备状态同步 |
| `POST /projects/{id}/ci/report` | CI 集成 — 传入 `matched_case_id` 自动更新状态（标 `source=ci`） |

管理类接口需要 `CASEMAP_SERVER_ADMIN_TOKEN`（用于 `GET /projects` 列出所有项目）。
OpenAPI 自动文档：`/docs`、`/openapi.json`。CORS 默认 `*`，部署时按需收敛。

## 架构（SP-1 + SP-4 + SP-2）

```
parsers  (OpenAPI / Postman / apifox)
  ↓ list[Endpoint]
generators.structural   (7 条启发式规则：happy / required / 404 / auth / conflict / boundary / delete-security)
  ↓ list[TestCase]  (positive / negative / edge / security)
generators.functional   (LLM 业务语言改写，可选)
  ↓ enriched cases
generators.pipeline     (编排器；LLM 失败 → 回退结构化)
  ↓ TestGraph
renderers  (SVG / JSON / Markdown / 自包含 HTML / 只读报告 HTML)
  └─→ casemap.server.*  (FastAPI + SQLAlchemy + Bearer tokens + CI webhook)
```

每一层都可以单独替换或扩展：

- **新解析器**：实现 `Parser` Protocol + `ParserRegistry.register(...)`
- **新 LLM**：实现 `LLMProvider` Protocol，注入到 `GenerationPipeline(llm=...)`
- **新渲染器**：实现 `render(graph) -> str`

## 关键设计决策

| 决策 | 取舍 |
|------|------|
| **自包含 HTML**（不是 SPA） | 浏览器双击即可用，零依赖，零 CDN。可邮件 / U 盘分发 |
| **内联 SVG**（不是 Mermaid） | 不依赖 CDN，离线可用，文件更小（~30 KB） |
| **稳定 ID**（BLAKE2b 内容指纹） | 重新生成同一份接口列表，状态接得上；不依赖输入顺序 |
| **localStorage + JSON 导入导出** | 单浏览器零成本；跨设备用文件搬运（隐私优先于便利） |
| **LLM 失败 → 回退** | 闭循环永远不出错；网络抖动 / 配额用完都不阻塞 |
| **接口文档直接消费** | 不要求业务方提供额外元数据 |

## 项目状态

当前 release：**v0.2.0**（SP-1 + SP-2 + SP-4）
- ✅ 核心引擎（stable_id、structural + functional、pipeline）
- ✅ 文档解析器（OpenAPI / Postman / apifox）
- ✅ 5 个渲染器（SVG / JSON / Markdown / 自包含 HTML / 只读报告 HTML）
- ✅ CLI（generate / validate / parsers list / serve）
- ✅ Server 模式（FastAPI + SQLite + Bearer 鉴权 + CI webhook）
- ✅ 226 个测试（unit + property + integration + server）

未来计划：
- **SP-3**：响应式 Web 前端（替代自包含 HTML）
- **SP-5**：生产环境调试审查 / 性能调优

## 开发

```bash
uv sync                    # 安装依赖
uv run pytest              # 跑测试（带覆盖率）
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run mypy src/casemap
```

仓库内所有样本在 `examples/` 下，集成测试在 `tests/integration/` 下。

## License

MIT
