# 功能测试用例图管理系统 — SP-1 & SP-4 设计文档

> **日期**：2026-09-23
> **作者**：casemap team
> **范围**：SP-1 核心引擎 + SP-4 文档解析器
> **状态**：Draft，待用户 review

## 1. 项目定义

**功能测试用例图管理系统（casemap）** —— 一个面向**非技术用户**（测试人员 + 产品人员）的工具。核心能力：

> **将 API 接口列表（默认 Swagger）逆向生成精美的可视化功能测试用例脑图**，测试人员对照脑图执行人工功能测试，测完标记状态。

**核心约束**：
- 用户**不懂技术接口**
- 需要**正向 + 逆向 + 边界**用例
- 需要看到**全貌图**（不是干列表）
- 零安装、零后端、单 HTML 文件即可用

## 2. 整体架构

### 2.1 分层架构

```
┌─────────────────────────────────────────┐
│  CLI Layer (cli.py)                     │  ← 用户入口
├─────────────────────────────────────────┤
│  Orchestration (pipeline.py)           │  ← 编排，无业务逻辑
├─────────────────────────────────────────┤
│  Generators (structural/functional)     │  ← 用例生成（业务逻辑）
├─────────────────────────────────────────┤
│  Parsers (swagger/apifox/...)           │  ← 输入解析
├─────────────────────────────────────────┤
│  LLM Abstraction (single-model)         │  ← 可选 LLM 增强
├─────────────────────────────────────────┤
│  Renderers (mermaid/html/json/md)       │  ← 输出格式化
├─────────────────────────────────────────┤
│  Models (endpoint/testcase/graph)       │  ← 纯数据，零依赖
└─────────────────────────────────────────┘
```

**分层原则**：
- 每一层只依赖下一层（不跨层）
- Models 层完全独立，可单独测试
- 任何一层可以被替换/扩展，不影响其他层

### 2.2 目录结构

```
casemap/
├── pyproject.toml              # uv 管理
├── README.md
├── src/casemap/
│   ├── __init__.py
│   ├── models/                 # 数据模型层（纯数据，零依赖）
│   │   ├── __init__.py
│   │   ├── endpoint.py        # Endpoint, Parameter, Response, Method
│   │   ├── testcase.py        # TestCase, TestStep, CaseType, TestStatus
│   │   ├── graph.py           # TestGraph, TestNode, Edge
│   │   └── parser_config.py   # ParserConfig
│   ├── parsers/                # SP-4 文档解析（协议模式）
│   │   ├── __init__.py
│   │   ├── base.py            # Parser Protocol + Registry
│   │   ├── openapi.py         # OpenAPI 3.x / Swagger 2.0（合并）
│   │   ├── postman.py         # Postman v2.1 collection
│   │   └── apifox.py          # apifox export
│   ├── generators/             # 用例生成
│   │   ├── __init__.py
│   │   ├── structural.py      # 启发式（确定，无依赖）
│   │   ├── functional.py      # LLM 增强（可选）
│   │   └── pipeline.py        # 编排结构层 + 业务层
│   ├── llm/                    # LLM 抽象
│   │   ├── __init__.py
│   │   ├── provider.py        # LLMProvider Protocol
│   │   ├── openai_compat.py   # OpenAI 兼容（覆盖 90% provider）
│   │   ├── config.py          # 单模型配置（pydantic）
│   │   └── cache.py           # 响应缓存（hash-based）
│   ├── renderers/              # 输出格式化
│   │   ├── __init__.py
│   │   ├── mermaid.py         # Mermaid 文本
│   │   ├── html_self.py       # ★ 自包含 HTML（带交互 + localStorage）
│   │   ├── report_html.py     # 测试报告 HTML
│   │   ├── json_export.py     # JSON 状态持久化
│   │   └── markdown.py        # 决策表
│   ├── cli.py                  # CLI 入口（casemap 命令）
│   └── _internal/              # 内部工具，不导出
│       ├── logger.py
│       └── exceptions.py
└── tests/
    ├── conftest.py             # 共享 fixtures
    ├── unit/
    │   ├── test_models.py      # 数据模型
    │   ├── test_parsers.py     # 解析器
    │   ├── test_structural.py  # 结构层生成
    │   ├── test_pipeline.py    # 编排
    │   ├── test_llm.py         # LLM 抽象（mock）
    │   ├── test_renderers.py   # 输出
    │   └── test_cli.py         # CLI
    ├── property/               # Hypothesis 属性测试
    │   └── test_invariants.py
    ├── integration/            # 端到端
    │   ├── test_swagger_to_html.py
    │   └── test_llm_pipeline.py
    └── fixtures/
        ├── swagger/            # Pet Store, GitHub API
        ├── postman/
        └── apifox/
```

## 3. 数据模型

### 3.1 核心模型（`models/`）

```python
# models/endpoint.py
from enum import Enum
from pydantic import BaseModel, Field

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class Parameter(BaseModel):
    name: str
    location: str  # "path" | "query" | "header" | "body" | "formData"
    type: str      # "string" | "integer" | "boolean" | "array" | "object"
    required: bool
    description: str = ""
    example: Any | None = None
    # 启发式生成边界用例时用
    constraints: dict = Field(default_factory=dict)
    # 例: {"min": 0, "max": 100, "enum": [...], "pattern": "..."}

class Response(BaseModel):
    status_code: str  # "200", "4XX", "default" 等
    description: str = ""

class Endpoint(BaseModel):
    path: str                    # "/api/users/{id}"
    method: HttpMethod
    summary: str = ""            # OpenAPI 里的 summary
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    operation_id: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    request_body: Parameter | None = None
    responses: list[Response] = Field(default_factory=list)
    # 用于业务层 LLM 增强
    raw: dict = Field(default_factory=dict, exclude=True)
```

```python
# models/testcase.py
from enum import Enum

class CaseType(str, Enum):
    POSITIVE = "positive"     # 正向：正常路径
    NEGATIVE = "negative"     # 逆向：异常路径（鉴权失败、参数错误等）
    EDGE = "edge"             # 边界：min/max、empty、特殊字符
    SECURITY = "security"     # 安全（注入、越权等）

class TestStatus(str, Enum):
    PENDING = "pending"        # ⚪ 待测
    IN_PROGRESS = "in_progress"# 🟡 进行中
    PASSED = "passed"         # 🟢 通过
    FAILED = "failed"         # 🔴 失败
    BLOCKED = "blocked"       # ⚫ 阻塞
    SKIPPED = "skipped"       # 🔵 跳过

class TestStep(BaseModel):
    order: int
    action: str                # 自然语言动作
    expected: str              # 预期结果

class TestCase(BaseModel):
    id: str                     # 稳定 hash（用于 localStorage）
    type: CaseType
    status: TestStatus = TestStatus.PENDING
    title: str                  # ★ 业务语言（LLM 生成时强制）
    description: str
    steps: list[TestStep]
    endpoint_ref: str | None    # 关联到 endpoint.path+method
    tags: list[str] = Field(default_factory=list)
    failure_note: str = ""      # 失败时用户填的备注
```

```python
# models/graph.py
class TestNode(BaseModel):
    id: str                # = testcase.id
    case: TestCase

class Edge(BaseModel):
    source: str            # 源 node id
    target: str            # 目标 node id
    label: str = ""

class TestGraph(BaseModel):
    title: str                       # 项目名
    nodes: list[TestNode]
    edges: list[Edge]
    metadata: dict = Field(default_factory=dict)
    # 例：metadata = {"source": "swagger", "version": "3.0", "generated_at": "..."}

    @property
    def progress(self) -> dict:
        """统计状态分布，给前端展示进度条用"""
        ...
```

### 3.2 模型设计原则

- **零业务逻辑**：model 只定义 schema，不写方法（除 `@property`）
- **稳定 hash ID**：testcase.id 基于 endpoint+type+index，保证可复现
- **可序列化**：所有 model 都支持 `.model_dump_json()` / `.model_validate_json()`

## 4. 解析器层（SP-4）

### 4.1 接口定义

```python
# parsers/base.py
from typing import Protocol

class Parser(Protocol):
    """所有文档解析器必须实现这个接口"""
    name: str          # "openapi" | "postman" | "apifox"
    version: str       # 解析器版本

    def can_parse(self, data: dict | str) -> bool:
        """嗅探输入，判断是否能解析"""
        ...

    def parse(self, data: dict | str) -> list[Endpoint]:
        """解析为统一 Endpoint 列表"""
        ...

class ParserRegistry:
    _parsers: list[Parser] = []

    @classmethod
    def register(cls, parser: Parser): ...

    @classmethod
    def auto_detect(cls, data) -> Parser: ...

    @classmethod
    def get(cls, name: str) -> Parser: ...
```

### 4.2 OpenAPI 解析器（默认）

**输入支持**：
- OpenAPI 3.0 / 3.1
- Swagger 2.0（向后兼容）

**复用开源库**（不造轮子）：
- `openapi-spec-validator`：验证 spec 合法性
- `openapi-schema-validator`：验证 schema
- `prance`：合并 `$ref` 引用（处理 components/schemas）

**转换逻辑**：
```
OpenAPI paths dict
  ↓ for each (path, methods_dict)
    ↓ for each (method, operation)
      ↓ 提取 parameters / requestBody / responses
        ↓ 构造 Endpoint（统一 schema）
```

### 4.3 Postman / Apifox 解析器

**Postman v2.1 collection**：
- 用 `item[].request` 提取 method/url/headers/body
- 用 `item[].response` 推断响应码

**Apifox**：
- 直接支持 OpenAPI 导出，复用 `openapi.py`
- 仅在 header/metadata 上有差别

### 4.4 注册机制

```python
# 用户自定义 parser
from casemap.parsers import ParserRegistry, Parser

class MyParser:
    name = "myformat"
    ...

ParserRegistry.register(MyParser())

# casemap 自动嗅探
casemap generate unknown.json  # 自动选合适的 parser
```

## 5. 生成器层

### 5.1 结构层（永远启用，启发式）

**输入**：`list[Endpoint]`
**输出**：`list[TestCase]`（确定性，无外部依赖）

**核心规则**：

| 启发式 | 规则 | 生成的用例类型 |
|--------|------|--------------|
| **必填参数校验** | 每个 required=true 参数生成"缺失必填"用例 | NEGATIVE |
| **HTTP 401/403** | 接口需要鉴权时（OpenAPI security） | NEGATIVE |
| **HTTP 404** | path 含 `{id}` 参数时 | NEGATIVE |
| **HTTP 409** | POST 接口响应码包含 409 | NEGATIVE |
| **HTTP 5xx** | 任何 5xx 响应码 | NEGATIVE |
| **Boundary - min/max** | 参数含 min/max 约束 | EDGE |
| **Boundary - empty** | string/array 参数 | EDGE |
| **Boundary - null** | nullable=true 参数 | EDGE |
| **Happy path** | 每个 endpoint 至少 1 个正向用例 | POSITIVE |
| **DELETE 无 body** | method=DELETE | POSITIVE（确认资源被删除） |
| **危险操作** | method=DELETE | SECURITY（需额外权限） |

**实现原则**：
- 每个规则独立函数 `def rule_required_params(ep) -> list[TestCase]`
- 在 `pipeline.py` 里顺序调用
- 每个规则可单独测试

### 5.2 业务层（可选，LLM 增强）

**输入**：结构层生成的 `list[TestCase]` + `list[Endpoint]`
**输出**：增强后的 `list[TestCase]`（**业务语言 title/description**）

**LLM 调用策略**：
- 单 prompt，包含所有 endpoints + 结构层生成的 cases
- 一次性生成所有增强（避免 N+1）
- 强制 system prompt：

```python
SYSTEM_PROMPT = """你是一个功能测试用例设计专家。
用户是非技术人员（产品/测试），他们不懂技术术语。
请把每个接口的 OpenAPI 技术描述翻译成：
1. 一句业务语言的功能描述（例：「用户可以重置自己的密码」而不是「POST /reset-password」）
2. 该功能下用户能做的所有事（正向用例）
3. 用户做错/系统异常时的预期行为（逆向用例）
4. 边界情况（最大/最小/为空/特殊字符）

【绝对禁止】输出任何 HTTP 方法、状态码、参数名等术语。
【必须】输出用「用户能做什么」「系统应该/不应该」的自然语言。"""
```

### 5.3 Pipeline 编排

```python
# generators/pipeline.py
class GenerationPipeline:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        cache: LLMCache | None = None,
    ): ...

    def run(self, endpoints: list[Endpoint]) -> TestGraph:
        # 1. 结构层（永远）
        structural_cases = self.structural.generate(endpoints)

        # 2. 业务层（如果 LLM 可用）
        if self.llm:
            functional_cases = self.functional.enhance(
                endpoints, structural_cases
            )
            # 合并：LLM 输出覆盖结构层的 title/description
            cases = self._merge(structural_cases, functional_cases)
        else:
            cases = structural_cases

        # 3. 构造图（节点 + 依赖边）
        graph = self._build_graph(endpoints, cases)
        return graph
```

## 6. LLM 抽象层

### 6.1 单模型配置（严格遵守需求 #11）

```python
# llm/config.py
class LLMConfig(BaseModel):
    provider: str          # "openai" | "anthropic" | "ollama" | ...
    base_url: str | None   # 默认 None，OpenAI 官方
    model: str             # 严格只一个模型
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3

    # ★ 禁止 models: list[str] 多模型配置
```

### 6.2 协议模式

```python
# llm/provider.py
class LLMProvider(Protocol):
    async def complete(self, prompt: str, *, system: str | None = None) -> str:
        """单次补全"""
        ...

    async def complete_json(self, prompt: str, *, schema: type[T]) -> T:
        """结构化输出（带 JSON 校验）"""
        ...
```

### 6.3 OpenAI 兼容实现

**默认实现**覆盖 90% provider（OpenAI / Anthropic / Ollama / vLLM / 各种国内模型）：
- 用 `openai` SDK
- 配置 `base_url` 即可切换
- 这是 LLM 抽象层的**唯一**内置实现

### 6.4 缓存

- Key = hash(endpoint.summary + structural_cases_signature)
- 避免重复调用（同一 spec 重跑时秒级返回）
- 持久化到 `.casemap_cache.json`（可禁用）

## 7. 渲染器层

### 7.1 HTML 自包含渲染器（★ 核心产出）

**目标**：双击 `cases.html` 即可在浏览器使用，零后端。

**关键设计**：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>测试用例脑图</title>
  <!-- 内嵌 CSS（设计系统变量） -->
  <!-- 内嵌 Mermaid JS（CDN，离线友好可选内嵌） -->
</head>
<body>
  <header><!-- 进度条 / 模块导航 --></header>
  <main>
    <div id="graph"><!-- Mermaid 渲染区 --></div>
    <aside id="detail-panel"><!-- 用例详情（点节点弹出）--></aside>
  </main>
  <footer><!-- 导出按钮 / 状态汇总 --></footer>
  <script>
    // ★ 关键 JS（vanilla，无依赖）：
    // 1. 从 Mermaid 点击事件获取 node id
    // 2. 加载 localStorage 中的状态
    // 3. 状态变更时保存回 localStorage
    // 4. 进度条实时更新
    // 5. 失败备注输入框
  </script>
</body>
</html>
```

**设计原则**：
- **CSS 变量**驱动，方便后期换主题
- **响应式**：mobile 端折叠右侧面板为底部抽屉
- **无障碍**：键盘导航、ARIA、对比度 ≥ 4.5:1
- **性能**：Mermaid 渲染在 50 节点以下秒级；超过时分模块折叠

### 7.2 Mermaid 渲染器

**输出**：纯 Mermaid 文本（给开发者调试用）

**图类型选择**：
- ≤ 30 nodes：`flowchart`
- 30-100 nodes：`flowchart` with subgraphs（按 tag 分组）
- 复杂依赖：分层渲染

**节点编码**：
- 形状：按 CaseType（`[ ]`=positive, `( )`=negative, `{}`=edge, `[/ /\]`=security）
- 颜色：按 status（CSS class 映射）

### 7.3 JSON 导出器

**目的**：状态持久化格式，可用于：
- 跨设备迁移（导出 → 导入）
- CI 集成（自动跑测试 → 更新状态 → 重渲染）
- 报告生成

```json
{
  "version": 1,
  "graph": { /* TestGraph dump */ },
  "statuses": {
    "case-id-1": {"status": "passed", "note": "", "updated_at": "..."},
    "case-id-2": {"status": "failed", "note": "按钮无反应", "updated_at": "..."}
  }
}
```

### 7.4 测试报告 HTML

**输入**：原始 TestGraph + 状态 JSON
**输出**：单 HTML 报告（不可编辑，只读）

**内容**：
- 项目元信息（生成时间、来源 spec）
- 整体进度条
- 模块分布（按 tag）
- 失败用例列表（按 note 排序）
- 全部用例表格（可搜索）

## 8. CLI 设计

```bash
# 基本生成
casemap generate interfaces.json -o cases.html

# 指定 parser
casemap generate interfaces.json --parser openapi -o cases.html

# 启用 LLM 增强
casemap generate interfaces.json --llm openai --model gpt-4o-mini

# 从 JSON 状态恢复 + 重渲染
casemap resume cases.html statuses.json -o cases-resumed.html

# 列出支持的 parsers
casemap parsers list

# 验证 spec 合法性
casemap validate interfaces.json
```

**CLI 库选择**：用 `click`（比 argparse 强，比 typer 简单）。

## 9. 测试策略

### 9.1 测试分层

| 层 | 工具 | 目标 |
|----|------|------|
| 单元 | pytest | 每个函数/方法 |
| 属性 | hypothesis | 不变量 |
| 集成 | pytest | 端到端流程 |
| 快照 | syrupy | 渲染输出稳定 |

### 9.2 必须测试的核心理论

1. **模型序列化往返**：`model_dump_json()` → `model_validate_json()` 不丢字段
2. **解析器正确性**：真实 spec（Pet Store / GitHub API）解析结果与手算一致
3. **生成器覆盖性**：每个 endpoint 至少产生 ≥ 1 个正向 + ≥ 1 个逆向
4. **ID 稳定性**：同一 endpoint 生成的 ID 永远不变
5. **状态机完整性**：每个 case 都有 status，6 个状态都可达
6. **HTML 自包含性**：生成的 HTML 包含所有 CSS/JS（无 CDN 依赖）

### 9.3 覆盖率目标

- 核心模块（models/parsers/generators/renderers）：≥ 90% line coverage
- 边界模块（cli/_internal）：≥ 70% line coverage
- 关键函数（merge/pipeline/registry）：100% branch coverage

## 10. 性能约束

| 操作 | 目标 |
|------|------|
| 解析 100 endpoint spec | < 100ms |
| 结构层生成 100 endpoint 的 cases | < 50ms |
| LLM 增强 100 endpoint | < 30s（含网络，单 prompt） |
| HTML 渲染 100 节点 | < 500ms（首次） |
| 重复加载（localStorage） | < 50ms |

**性能保证措施**：
- 用 `orjson` 替代 stdlib json
- LLM 响应缓存（hash key）
- Mermaid 渲染分页（> 100 节点折叠）
- **避免**：N+1 LLM 调用（一次性 prompt）

## 11. 扩展性设计

### 11.1 扩展点

| 想加什么 | 怎么做 |
|---------|--------|
| 新文档格式（Postman/YApi/Rap） | 实现 `Parser` Protocol，注册到 `ParserRegistry` |
| 新生成规则 | 在 `structural.py` 加新函数，pipeline 自动调用 |
| 新 LLM provider | 实现 `LLMProvider` Protocol（用 OpenAI 兼容协议即可覆盖 90%） |
| 新输出格式 | 实现新 Renderer（不需要改其他模块） |
| 新状态字段 | 加到 `TestStatus` enum + 更新 HTML CSS class 映射 |

### 11.2 严禁的设计

- ❌ 硬编码文档格式名（用 Registry）
- ❌ 直接调用 LLM（必须走 Provider Protocol）
- ❌ 在 model 里写业务方法（model 只定义 schema）
- ❌ Generator 直接生成字符串（必须返回 data，让 Renderer 格式化）
- ❌ 跨层调用（如 Generator 直接调用 Renderer）

## 12. 关键依赖（用现成的，不造轮子）

```toml
[dependencies]
pydantic = ">=2.6"          # 数据验证 / 模型
openapi-spec-validator = "*" # OpenAPI spec 验证
openapi-schema-validator = "*"
prance = "*"                # OpenAPI $ref 合并
openai = ">=1.30"           # LLM 客户端（兼容模式）
httpx = ">=0.27"            # 异步 HTTP（备用）
orjson = ">=3.9"            # JSON 解析
click = ">=8.1"             # CLI
jinja2 = ">=3.1"            # HTML 模板（用于 Renderer）

[dependency-groups]
dev = [
    "pytest >=8.0",
    "pytest-cov",
    "pytest-asyncio",
    "hypothesis >=6.0",
    "syrupy >=4.0",
    "ruff",
    "mypy",
]
```

**包管理**：uv（Astral 出品，比 poetry 快 10x，PEP 621 标准）

## 13. 项目结构（最终）

```
casemap/                      # 项目根目录
├── pyproject.toml
├── README.md
├── LICENSE                    # MIT
├── src/casemap/               # 主包
│   └── ...（见 §2.2）
├── tests/                     # 测试
├── docs/
│   └── ...（用户文档）
└── examples/                  # 示例 JSON + 生成结果
    ├── swagger-petstore.json
    └── output-petstore.html
```

## 14. 风险与缓解

| 风险 | 缓解 |
|------|------|
| LLM 幻觉导致用例不准 | 严格 prompt + JSON schema 校验 + 用户可编辑 |
| LLM 成本 | 缓存 + 增量 + 便宜模型默认 |
| 不同 spec 格式兼容 | ParserRegistry 嗅探 |
| Mermaid 渲染慢 | 分模块 + 折叠 |
| 浏览器版本差异 | 标准化到 ES2020+，目标现代浏览器 |

## 15. 不做的事（避免范围蔓延）

- ❌ 不做 HTTP 服务（推到 SP-2）
- ❌ 不做完整 Web 前端（推到 SP-3）
- ❌ 不做多用户协作 / 权限（推到未来）
- ❌ 不做 CI 集成（推到 SP-2）
- ❌ 不做自定义 brain map 编辑器（脑图只读，状态在 localStorage）
- ❌ 不做国际化（默认中文）

## 16. 用户验收标准

完成时，PM/测试人员应能：

1. `pip install casemap` 安装（一次性）
2. `casemap generate petstore.json -o cases.html` 生成脑图（一次性，10秒）
3. 双击 `cases.html` 浏览器打开（无需服务器）
4. 看到脑图（每个节点是一个测试用例）
5. 点击节点看业务语言描述（无 HTTP 术语）
6. 标记 ✅/❌/🚫/⏭️ 状态，颜色立即变化
7. 进度自动统计
8. 关掉浏览器再打开，状态还在
9. 导出报告 HTML，发邮件/IM 给开发
10. 全程无报错，无需要懂的技术操作

## 17. 验收后下一步

- **SP-2**：FastAPI 服务（多设备同步、CI 集成）
- **SP-3**：响应式 Web 前端（替代自包含 HTML）
- **SP-5**：生产环境调试审查

---

## 变更日志

- 2026-09-23 初版（待 user review）
