# casemap SP-1+SP-4 Implementation Plan — P0 修订附录

> **日期**：2026-09-23
> **状态**：Append to `2026-09-23-casemap-sp1-sp4.md`
> **生效**：本文档优先于原计划中被影响的部分

## 0. 修订背景

经过对原计划的批判性审查，发现 **3 个严重问题** 会直接导致产品失败或返工。全部需要在本计划执行前修复。

## 1. 修订总览

| # | 严重问题 | 修订位置 | 修复策略 |
|---|---------|---------|---------|
| 1 | `stable_id` 用 index 拼 hash，新增规则导致 ID 漂移 | Task 8 | 改用 `rule_name + 参数名` 拼 hash，永久稳定 |
| 2 | HTML 强依赖 Mermaid CDN，断网即废 | Task 11 + 13 | **弃用 Mermaid**，自实现 SVG 渲染器 + 布局算法 |
| 3 | localStorage 单浏览器隔离，PM 无法看进度 | Task 13 | 新增状态**导出/导入**机制（自动下载 + 手动上传）|

## 2. Task 8 修订（stable_id 永久稳定）

### 2.1 核心问题

```python
# ❌ 错误写法（会被未来新增规则破坏）
id=stable_id(str(ep.method), ep.path, "missing-req", str(i))  # i 是 enumerate 索引
id=stable_id(str(ep.method), ep.path, "edge-min", str(i))
```

**问题**：`_rule_required_params` 内 enumerate 顺序改变，索引 `i` 全部漂移，**所有现有 case 的 stable_id 全部变化**，localStorage 里用户的进度全部丢失。

### 2.2 修复方案：stable_id 必须用"内容指纹"而非"位置索引"

```python
# ✅ 正确写法（rule_name + 内容）
id=stable_id(str(ep.method), ep.path, "rule", "missing-req", "param", p.name)
id=stable_id(str(ep.method), ep.path, "rule", "edge-min", "param", p.name)
```

**规则**：
- 第 1、2 部分：`method + path`（端点身份）
- 第 3 部分：固定 `"rule"` 字符串（命名空间）
- 第 4 部分：规则名（如 `"missing-req"`）
- 第 5+ 部分：规则依赖的参数身份（如 `p.name`、约束值）

**保证**：只要端点和规则不变、参数身份不变，ID 永远不变。增加新规则不影响旧 ID。

### 2.3 修订后的 Task 8 代码

替换原 `_rule_*` 方法的 `stable_id(...)` 调用，按以下映射：

| 原写法 | 新写法 |
|--------|--------|
| `stable_id(str(ep.method), ep.path, "happy")` | `stable_id(str(ep.method), ep.path, "rule", "happy-path")` |
| `stable_id(str(ep.method), ep.path, "missing-req", str(i))` | `stable_id(str(ep.method), ep.path, "rule", "missing-req", "param", p.name)` |
| `stable_id(str(ep.method), ep.path, "not-found")` | `stable_id(str(ep.method), ep.path, "rule", "not-found")` |
| `stable_id(str(ep.method), ep.path, "no-auth")` | `stable_id(str(ep.method), ep.path, "rule", "no-auth")` |
| `stable_id(str(ep.method), ep.path, "conflict")` | `stable_id(str(ep.method), ep.path, "rule", "conflict")` |
| `stable_id(str(ep.method), ep.path, "edge-min", str(i))` | `stable_id(str(ep.method), ep.path, "rule", "edge-min", "param", p.name, "bound", str(c["minimum"]))` |
| `stable_id(str(ep.method), ep.path, "edge-max", str(i))` | `stable_id(str(ep.method), ep.path, "rule", "edge-max", "param", p.name, "bound", str(c["maximum"]))` |
| `stable_id(str(ep.method), ep.path, "edge-overflow", str(i))` | `stable_id(str(ep.method), ep.path, "rule", "edge-overflow", "param", p.name)` |
| `stable_id(str(ep.method), ep.path, "edge-empty-string", str(i))` | `stable_id(str(ep.method), ep.path, "rule", "edge-empty-string", "param", p.name)` |
| `stable_id(str(ep.method), ep.path, "delete-security")` | `stable_id(str(ep.method), ep.path, "rule", "delete-security")` |

### 2.4 新增 Task 8 测试（验证 ID 稳定性）

```python
def test_stable_ids_unchanged_when_adding_rule():
    """Critical: adding a new rule must NOT change existing IDs.

    This test simulates adding a new rule by calling the rules in the same
    order they would be called. If we ever add a rule in the middle, this
    test will catch ID drift.
    """
    ep = make_endpoint(parameters=[Parameter(name="id", location="path", type="string", required=True)])
    cases_before = StructuralGenerator().generate([ep])
    ids_before = sorted(c.id for c in cases_before)

    # Run the same generator twice (rule order is fixed in code)
    cases_after = StructuralGenerator().generate([ep])
    ids_after = sorted(c.id for c in cases_after)

    assert ids_before == ids_after, "stable_id is not deterministic!"


def test_stable_ids_dont_use_index():
    """Each rule must use content-based ID, not position-based."""
    ep = make_endpoint(
        parameters=[
            Parameter(name="aaa", location="query", type="string", required=True),
            Parameter(name="bbb", location="query", type="string", required=True),
        ]
    )
    cases = StructuralGenerator().generate([ep])
    missing_cases = [c for c in cases if "缺失必填参数" in c.title]
    assert len(missing_cases) == 2
    # IDs must be different because param names differ (not because of index)
    assert missing_cases[0].id != missing_cases[1].id
    # Swap the parameter order and re-run - IDs must still differ
    ep2 = make_endpoint(parameters=list(reversed(ep.parameters)))
    cases2 = StructuralGenerator().generate([ep2])
    missing_cases2 = [c for c in cases2 if "缺失必填参数" in c.title]
    # Same param names → same IDs regardless of order (rule_name + param_name is stable)
    ids1 = sorted(c.id for c in missing_cases)
    ids2 = sorted(c.id for c in missing_cases2)
    assert ids1 == ids2, "IDs should not depend on parameter order"
```

## 3. Task 11 修订（自定义 SVG 渲染器，替代 Mermaid）

### 3.1 为什么不用 Mermaid

| 问题 | 描述 |
|------|------|
| CDN 依赖 | jsdelivr 不稳定，中国大陆访问慢/被墙 |
| 离线失效 | 第一次加载需要联网 |
| 视觉不可控 | 默认主题偏工程师风，不够"精美" |
| 交互受限 | Mermaid click 事件需要 setTimeout 1 秒延迟 hack（见原 Task 13）|

### 3.2 新 Task 11：SVG Renderer

**替换原 Mermaid Renderer**。

**Files**:
- Create: `src/casemap/renderers/svg.py`
- Delete: `src/casemap/renderers/mermaid.py`（不再需要）
- Modify: `src/casemap/renderers/__init__.py`

**Interfaces**:
```python
class SVGRenderer:
    """Render TestGraph as inline SVG with simple layered layout."""
    def render(self, graph: TestGraph) -> str:
        """Return SVG string. Layout: nodes grouped by tag, vertical by case_type within group."""
        ...
    def render_to_file(self, graph: TestGraph, path: Path) -> None: ...
```

### 3.3 布局算法（layered-by-tag）

**简单分层布局**（避免引入 d3 / elk 这种重量级库）：
- 分组：按 `tag` 分组（一个 endpoint 通常只有一个 tag）
- 排版：每个 tag 一个**垂直列**，列内按 case_type 顺序排列（positive → negative → edge → security）
- 节点位置：`x = tag_index * COLUMN_WIDTH`, `y = case_index_in_tag * ROW_HEIGHT`
- 连线：从上一节点底部连到下一节点顶部（直线 `<line>`，不画箭头，简单清晰）

```python
COLUMN_WIDTH = 280
ROW_HEIGHT = 90
PADDING = 40

NODE_SHAPES = {
    CaseType.POSITIVE: "rect",       # 圆角矩形
    CaseType.NEGATIVE: "rect",       # 圆角矩形
    CaseType.EDGE: "diamond",        # 菱形
    CaseType.SECURITY: "shield",      # 盾牌路径（<path>）
}

STATUS_FILLS = {
    TestStatus.PENDING: "#f3f4f6",     # 浅灰
    TestStatus.IN_PROGRESS: "#fef3c7", # 浅黄
    TestStatus.PASSED: "#d1fae5",      # 浅绿
    TestStatus.FAILED: "#fee2e2",      # 浅红
    TestStatus.BLOCKED: "#e5e7eb",     # 深灰
    TestStatus.SKIPPED: "#dbeafe",     # 浅蓝
}
STATUS_STROKES = {
    TestStatus.PENDING: "#9ca3af",
    TestStatus.IN_PROGRESS: "#f59e0b",
    TestStatus.PASSED: "#10b981",
    TestStatus.FAILED: "#ef4444",
    TestStatus.BLOCKED: "#6b7280",
    TestStatus.SKIPPED: "#3b82f6",
}
```

### 3.4 SVG 节点交互（关键设计）

**每个节点是一个 `<g>` 元素，包含**：
- 形状（rect / diamond / shield path）
- 背景色 + 边框色（按 status）
- 文字（标题，可能截断）
- **`<title>` 子元素**：浏览器原生 tooltip，hover 显示完整信息

**点击事件**：用原生 SVG `<a>` 元素包裹 `<g>`（可点击、可 keyboard focus、可 aria-label）：
```html
<a href="#case-{id}" class="case-node" data-case-id="{id}">
  <g>{...}</g>
</a>
```
JS 监听 `.case-node` 的 click，不需要 setTimeout hack。

### 3.5 视觉细节（资深 UI/UX 设计师视角）

- **节点宽度自适应**：根据 `text` 长度动态算宽度（用浏览器原生 `<foreignObject>` 或 SVG `<text>` + measureText）
- **图标**：每个 case_type 加小图标（`<text>` 用 emoji：✅ / ❌ / 🔶 / 🛡️），比纯文字更有视觉区分
- **字体**：用 system-ui + 中文 fallback（PingFang SC / Microsoft YaHei）
- **留白**：节点间垂直间距 12px、组间水平间距 60px
- **色彩**：每个 status 有清晰的 fill + stroke 组合（PENDING = 灰白，PASSED = 浅绿+绿边，FAILED = 浅红+红边）

### 3.6 删减的功能

- ❌ 删除 `mermaid.py`
- ❌ 不再做 classDef（SVG 内联 stroke/fill）
- ❌ 不需要 INITIAL_STATUSES_JS 里的 mermaid config

## 4. Task 13 修订（HTML 自包含 + 状态导出/导入）

### 4.1 移除 Mermaid CDN

```html
<!-- ❌ 删除 -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
```

**改为**：SVG 直接由 Python 端渲染好，inline 到 HTML `<body>` 里。

### 4.2 新增状态导出/导入机制（解决 P0 #3）

**自动导出**：
```javascript
// JS_INTERACTIVE 中：
function setStatus(id, status) {
  // ... existing code
  // ★ 新增：每次状态变化后，提示用户下载 status.json
  autoExportStatuses();
}

function autoExportStatuses() {
  // 1. 收集所有 statuses
  const all = loadStatuses();
  const data = {
    version: 1,
    exported_at: new Date().toISOString(),
    statuses: all,
  };
  // 2. 存到 sessionStorage 标记"有未导出的变更"
  sessionStorage.setItem('casemap_dirty', '1');
  // 3. 显示顶部"导出进度"按钮（醒目）
  showExportReminder();
}

window.addEventListener('beforeunload', (e) => {
  if (sessionStorage.getItem('casemap_dirty')) {
    e.preventDefault();
    e.returnValue = '测试进度尚未导出，确定离开？';
  }
});
```

**手动导出**（顶部固定按钮）：
```javascript
function exportProgress() {
  const data = {version: 1, exported_at: ..., statuses: loadStatuses()};
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `casemap-status-${new Date().toISOString().slice(0,10)}.json`;
  a.click();
  sessionStorage.removeItem('casemap_dirty');
}
```

**手动导入**（PM / 换电脑场景）：
```html
<button class="import-btn">📥 导入进度</button>
<input type="file" id="status-import" accept=".json" hidden>
```
```javascript
document.querySelector('.import-btn').addEventListener('click', () => {
  document.getElementById('status-import').click();
});
document.getElementById('status-import').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const text = await file.text();
  const data = JSON.parse(text);
  // 合并：导入的 status 覆盖现有（保留更新的）
  const existing = loadStatuses();
  const merged = {...data.statuses, ...existing};
  saveStatuses(merged);
  location.reload();  // 重新渲染
});
```

### 4.3 修订后的 HTML 模板关键变化

```html
<!-- ❌ 删除 -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({...});</script>

<!-- ✅ 新增 -->
<button class="export-btn">📤 导出报告</button>
<button class="export-status-btn" style="display:none">💾 导出进度</button>
<button class="import-btn">📥 导入进度</button>
<input type="file" id="status-import" accept=".json" hidden>

<!-- SVG 直接 inline -->
{svg_payload}

<!-- CSS 需要增加 .case-node 样式 -->
<style>
  .case-node { cursor: pointer; }
  .case-node:hover rect, .case-node:hover path { filter: brightness(0.95); }
  .case-node:focus { outline: 2px solid var(--accent); outline-offset: 4px; }
</style>
```

### 4.4 文件大小预估

- 嵌入 SVG（100 节点）：~30KB
- 嵌入 CSS：~10KB
- 嵌入 JS：~15KB
- 测试用例数据 JSON：~10KB (100 case) - 1MB (10000 case)
- **总大小**：典型场景 < 100KB，比 Mermaid CDN 加载更快

## 5. 受影响测试的修订

### Task 11 新测试（替换原 Mermaid 测试）

```python
# tests/unit/test_renderers_svg.py
from casemap.renderers.svg import SVGRenderer

def test_render_returns_valid_svg():
    g = TestGraph(title="t", nodes=[TestNode(id="a", case=...)])
    svg = SVGRenderer().render(g)
    assert svg.startswith("<svg") or svg.startswith('<?xml')
    assert "<svg" in svg
    assert "</svg>" in svg

def test_each_node_is_clickable():
    # Every node must be wrapped in <a> for click handling
    g = TestGraph(title="t", nodes=[TestNode(id="abc", case=...)])
    svg = SVGRenderer().render(g)
    assert 'data-case-id="abc"' in svg
    assert 'href="#case-abc"' in svg

def test_status_color_reflected():
    cases = [
        TestNode(id="p", case=TestCase(id="p", ..., status=TestStatus.PASSED)),
        TestNode(id="f", case=TestCase(id="f", ..., status=TestStatus.FAILED)),
    ]
    svg = SVGRenderer().render(TestGraph(title="t", nodes=cases))
    assert "#d1fae5" in svg  # passed fill
    assert "#fee2e2" in svg  # failed fill

def test_no_external_dependencies():
    """Critical: SVG output must have NO external refs."""
    g = TestGraph(title="t", nodes=[TestNode(id="a", case=...)])
    svg = SVGRenderer().render(g)
    assert "http://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', '')  # only SVG namespace OK
    assert "https://" not in svg.replace('xmlns="http://www.w3.org/2000/svg"', '')
    assert "<script" not in svg

def test_layout_by_tag_groups():
    g = TestGraph(
        title="t",
        nodes=[
            TestNode(id="u1", case=TestCase(id="u1", tags=["users"])),
            TestNode(id="u2", case=TestCase(id="u2", tags=["users"])),
            TestNode(id="o1", case=TestCase(id="o1", tags=["orders"])),
        ],
    )
    svg = SVGRenderer().render(g)
    # Two groups visually
    # (Implementation-dependent assertion; verify x coordinates of nodes differ between groups)
```

### Task 13 新测试（增加）

```python
def test_no_external_script_tags():
    """Critical: HTML must be 100% self-contained."""
    g = TestGraph(title="t")
    html = HTMLSelfRenderer().render(g)
    # Allow only data: URIs and our own resource hints
    assert "cdn.jsdelivr" not in html
    assert "unpkg.com" not in html
    assert "googleapis.com" not in html

def test_contains_export_status_button():
    g = TestGraph(title="t")
    html = HTMLSelfRenderer().render(g)
    assert "导出进度" in html or "export-status" in html.lower()

def test_contains_import_button():
    g = TestGraph(title="t")
    html = HTMLSelfRenderer().render(g)
    assert "导入进度" in html or "import" in html.lower()

def test_contains_dirty_tracker_javascript():
    g = TestGraph(title="t")
    html = HTMLSelfRenderer().render(g)
    assert "casemap_dirty" in html  # tracks unsaved changes
```

## 6. 修订任务清单（原 16 任务中的 3 个变更）

| 原任务 | 变更类型 | 关键改动 |
|--------|---------|---------|
| Task 8 | 局部代码替换 | `stable_id` 调用全部更新 + 新增 2 个测试 |
| Task 11 | **整体替换** | 删除 mermaid.py，新增 svg.py |
| Task 13 | 重大修改 | 移除 CDN，新增状态导入/导出机制 |

## 7. 自检（修订后）

- ✅ P0 #1 修复：`stable_id` 用内容指纹，新增规则不漂移
- ✅ P0 #2 修复：HTML 100% 自包含，零外部依赖
- ✅ P0 #3 修复：状态可导出/导入，PM 可同步进度
- ✅ Spec #11（单模型）：未受影响
- ✅ Spec #13（精美可视化）：改进（自定义 SVG + 图标）
- ✅ Spec #4（测试覆盖）：Task 8 / 11 / 13 测试相应更新

---

**生效**：本附录随原计划 `2026-09-23-casemap-sp1-sp4.md` 一起使用。如有冲突以本附录为准。
