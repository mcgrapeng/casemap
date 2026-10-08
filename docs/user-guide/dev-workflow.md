# 开发怎么用 casemap

> 本文档面向「开发工程师 / DevOps / SRE」。如果你只测不管代码，请看 [QA 工作流](./tester-workflow.md) 或 [PM 工作流](./pm-workflow.md)。

---

## 开发在 casemap 里扮演两个角色

1. **脑图生成者**：从接口文档生成测试用例脑图，给 QA 用
2. **CI 接入者**：让自动化测试结果自动出现在 casemap 脑图上

---

## 0. CASEMAP CLI 命令速查

| 命令 | 别名 | 干什么 |
|------|------|--------|
| `casemap generate` | `casemap brain`、`casemap html` | 从接口文档生成离线脑图 HTML |
| `casemap serve` | `casemap ui`、`casemap start` | 启动 casemap 服务器（含 Web UI） |
| `casemap init` | （无） | 交互式首次部署向导 |
| `casemap validate` | （无） | 验证接口文档格式（不生成） |
| `casemap parsers list` | （无） | 列出支持的 spec 解析器 |

> 💡 本文档里看到 `casemap generate` / `casemap serve`，都可以替换成对应的友好别名 — 同一个命令，多个名字是 Click 注册的别名。

---

## 1. 从 Swagger.json 生成测试用例脑图

### 命令行（最常用）

```bash
uv run casemap brain examples/petstore_swagger.json -o cases.html
```

会得到 `cases.html` 文件，**双击用浏览器打开**即可 — 零依赖、零安装。

### 命令参数

| 参数 | 作用 |
|------|------|
| `INPUT` | 接口文档路径（必填） |
| `-o OUTPUT` | 输出 HTML 路径 |
| `--parser` | 强制指定解析器（可选：openapi / postman / apifox）。不指定就自动检测 |
| `--llm` | 开启 LLM 重写（中文友好翻译，需要 API key） |
| `--llm-provider` | LLM 提供商（openai / anthropic / ollama，默认 openai） |
| `--model` | LLM 模型（与 `--llm` 配合） |

### 离线模式（生成 `.html` 给 QA）

QA 在没有服务器时直接打开这个 HTML 文件就能测。

### 推送到服务器（团队模式）

如果你已经有 casemap 服务器在跑，可以**直接推 spec**。注意：项目类接口（列项目、创建项目）需要 `管理员令牌`（不是项目 API Key），上传 spec 用项目 API Key。

```bash
# 1. 准备凭据
PROJECT_ID="..."
PROJECT_API_KEY="sk-casemap-..."
ADMIN_TOKEN="$CASEMAP_SERVER_ADMIN_TOKEN"   # 跟部署时设置的一致

# 2. 上传 spec 到服务器
curl -X POST "http://服务器IP:8765/api/v1/projects/$PROJECT_ID/specs" \
  -H "Authorization: Bearer $PROJECT_API_KEY" \
  -F "file=@examples/petstore_swagger.json" \
  -F "format=openapi"
```

服务器自动生成脑图并存到数据库，QA 立刻在浏览器看到。

### 自动检测格式

casemap 会自动判断你的 spec 是 OpenAPI / Swagger / Postman / Apifox：

```bash
uv run casemap brain path/to/spec.json   # 不指定 --parser
```

如果你知道格式，可以 `--parser=openapi` 强制指定，加快解析。

### LLM 友好翻译（可选）

接口文档里的描述一般是英文 + 程序员术语（比如「missing required param」）。QA 看着头大。

开启 LLM 重写后，casemap 会调用 LLM 把用例描述翻译/改写成业务语言：

- 输入：「—」→「用户能提交订单时不填收货地址（必填项缺失）」
- 输入：「returns 404」 →「调用一个不存在的订单 ID 时，系统应该报「找不到」」

```bash
# 设置 LLM API key（环境变量）
export CASEMAP_LLM_API_KEY=sk-...
export CASEMAP_LLM_BASE_URL=https://api.deepseek.com/v1  # 或 OpenAI / Qwen / 任意 OpenAI 兼容
export CASEMAP_LLM_MODEL=deepseek-chat

# 开启 LLM 重写
uv run casemap brain spec.json -o cases.html --llm --model deepseek-chat
```

**支持的 LLM 提供商（任何 OpenAI 兼容接口都行）：**

- OpenAI
- DeepSeek
- Moonshot（月之暗面）
- Qwen（通义千问）
- Zhipu（智谱）
- Ollama（本地部署）

---

## 2. CI 自动上报测试结果（让自动化测试「喂」给 casemap）

**目标**：你跑完自动化测试，casemap 脑图上对应节点自动变绿。

### 工作原理

```
CI 跑自动化测试
    ↓
拿到测试结果（哪些用例通过、哪些失败）
    ↓
每个用例匹配 casemap 的 stable_id
    ↓
调用 casemap 服务器的 CI 上报接口
    ↓
服务器更新脑图节点状态（来源标注为 CI）
```

### CI 上报接口

```
POST /api/v1/projects/{project_id}/ci/report
Authorization: Bearer {PROJECT_API_KEY}
Content-Type: application/json

{
  "entries": [
    {
      "matched_case_id": "ab12ef34...",  // casemap 的 stable_id
      "status": "passed",                 // passed / failed / skipped
      "note": "Test ran in 0.5s",
      "ran_at": "2026-10-07T12:34:56Z"
    }
  ]
}
```

### 怎么拿到 stable_id

每个测试用例都有唯一的 stable_id — 内容哈希。两种方式：

**方式 A：从脑图 HTML 里看**

打开脑图，浏览器开发者工具 → 选中一个节点 → 看 SVG 的 `data-case-id` 属性。

**方式 B：从服务器 API 拿**

```bash
curl "http://服务器IP:8765/api/v1/projects/$PROJECT_ID/cases" \
  -H "Authorization: Bearer $PROJECT_API_KEY"
```

返回 JSON 里每个 case 有 `id`（即 stable_id）。

**方式 C：自动化测试输出 stable_id**

如果你在自动化测试用例里直接加 metadata，让测试运行器打印 stable_id：

```python
@pytest.mark.casemap_id("ab12ef34...")
def test_user_can_login_with_valid_credentials():
    ...
```

测试运行器收集这些 ID，CI 步骤里批量上报。

### CI 例子（GitHub Actions）

```yaml
# .github/workflows/test-and-report.yml
name: Tests + casemap report

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install
        run: pip install -e .

      - name: Run tests (collect casemap IDs)
        run: pytest --casemap-output=results.json

      - name: Report to casemap
        if: always()  # 即使失败也上报（失败用例也要标记）
        run: |
          curl -X POST "${{ secrets.CASEMAP_URL }}/api/v1/projects/${{ secrets.CASEMAP_PROJECT_ID }}/ci/report" \
            -H "Authorization: Bearer ${{ secrets.CASEMAP_PROJECT_KEY }}" \
            -H "Content-Type: application/json" \
            -d @results.json
```

### CI 例子里用到的 secrets

去 GitHub repo → Settings → Secrets → 添加：

| Name | Value |
|------|-------|
| `CASEMAP_URL` | 服务器 URL，如 `http://casemap.company.com` |
| `CASEMAP_PROJECT_ID` | 项目 ID（PM 给你的） |
| `CASEMAP_PROJECT_KEY` | 项目 API Key（PM 给你的，存到 secrets 里别明文） |

### 收集 pytest 的稳定 ID（自定义插件）

```python
# conftest.py
import pytest
import json

collected = []

def pytest_configure(config):
    config._casemap_results = []

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    if call.when != "call":
        return
    marker = item.get_closest_marker("casemap_id")
    if marker:
        # 第一个参数 pass 是 stable_id
        status = "passed" if call.excinfo is None else "failed"
        collected.append({
            "matched_case_id": marker.args[0],
            "status": status,
            "note": item.nodeid,
        })

def pytest_sessionfinish(session, exitstatus):
    # 写到 results.json 给 CI 步骤用
    with open("results.json", "w") as f:
        json.dump({"entries": collected}, f)
```

测试用例里加 marker：

```python
import pytest

@pytest.mark.casemap_id("ab12ef34...")
def test_user_can_login():
    ...
```

### 上报后的效果

CI 上报后：

- 脑图对应节点**自动变色**（passed = 绿，failed = 红）
- 节点显示「来源：CI」（区别于 QA 手工标的）
- **其他浏览器实时看到**（团队模式的实时同步）

---

## 3. 从 casemap HTML 提取测试进度

有些团队希望把测试进度集成到自己的看板 / 大屏 / Slack 通知里。casemap 提供公开 API。

### REST API（推荐）

```bash
# 获取项目进度
curl "http://服务器IP:8765/api/v1/projects/$PROJECT_ID/progress" \
  -H "Authorization: Bearer $PROJECT_API_KEY"
```

返回：

```json
{
  "total": 245,
  "pending": 20,
  "in_progress": 20,
  "passed": 180,
  "failed": 12,
  "blocked": 5,
  "skipped": 8,
  "completion_pct": 73.5
}
```

### 从 HTML 解析（如果服务器 API 不够用）

casemap 的脑图 HTML 用了内联 JSON：

```javascript
// 浏览器开发者工具 → Console
const data = window.__casemap_data__;
console.log(data.cases);  // 所有用例 + 状态
```

或者用 cheerio / BeautifulSoup 抓 HTML：

```python
import json
import re
from pathlib import Path

html = Path("cases.html").read_text()
match = re.search(r"window\.__casemap_data__\s*=\s*(\{.*?\});", html, re.DOTALL)
data = json.loads(match.group(1))
print(f"Total: {len(data['cases'])}")
```

---

## 4. 解析 casemap HTML 报告

casemap 可以导出**只读报告 HTML** — 你可以用 cheerio / BeautifulSoup / BeautifulSoup 提取数据：

```python
import json
import re
from pathlib import Path

html = Path("report.html").read_text()

# 提取进度统计
stats_match = re.search(r'"stats":\s*({[^}]+})', html)
if stats_match:
    stats = json.loads(stats_match.group(1))
    print(f"Pass rate: {stats['completion_pct']}%")

# 提取失败用例
# (取决于实际 HTML 结构)
```

或者直接用服务器 API — 更稳定。

---

## 5. 在 CI 中跑 casemap 自身

casemap 自身的开发流程里有 CI：

```yaml
# .github/workflows/python.yml
name: Python tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install uv
      - run: uv sync
      - run: uv run pytest -q
```

如果你改的是 casemap 本身，参考根 README 的「Development」部分。

---

## 6. 安全注意

- ⚠️ **API Key 是密码** — 不要 commit 到 git，不要明文写在 CI 配置里，用 secrets / env vars
- ⚠️ **数据库要备份** — `casemap.db` 是 SQLite 文件，定期备份
- ⚠️ **不要把 casemap 服务器暴露到公网** — 默认假设内网使用；如需公网，前面套 Nginx + 鉴权

---

## 7. 进阶：casemap 作为库使用

casemap 的 Python 包是可编程的：

```python
from casemap.parsers import ParserRegistry
from casemap.generators import GenerationPipeline
from casemap.renderers import HtmlRenderer

# 解析
parser = ParserRegistry.match("examples/petstore_swagger.json")
endpoints = parser.parse(open("examples/petstore_swagger.json"))

# 生成用例（不带 LLM）
graph = GenerationPipeline().run(endpoints)

# 渲染 HTML
html = HtmlRenderer().render(graph)
Path("cases.html").write_text(html)
```

更多 API 见根 README 和源码 docstring。

---

## 下一步

- 想了解部署？ → [根 README - Quick start - Docker](../../README.md#quick-start--docker)
- 想知道 API 完整列表？ → 启动服务器后访问 `http://服务器IP:8765/docs`（自动生成的 Swagger UI）
- 概念不清楚？ → [术语表](./glossary.md)
- 出问题了？ → [故障排查](./troubleshooting.md)