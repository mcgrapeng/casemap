# examples

可运行的样例接口文档与命令。

## petstore_swagger.json

一个最小的 Swagger 2.0 示例，含 4 个接口（listPets / createPet / getPet / deletePet），
每个接口都带有 `parameters` 与 `responses`，方便快速验证全流程。

## 直接生成脑图（无 LLM）

```bash
uv run casemap generate examples/petstore_swagger.json -o /tmp/cases.html
```

打开 `/tmp/cases.html`：
- 左侧：测试用例脑图（按 tag 分列，按 CaseType 着色）
- 右侧：选中节点后查看用例详情
- 顶栏：进度条 + 状态导出/导入 + 报告导出

## 启用 LLM 业务语言改写（可选）

需要先有 OpenAI 兼容服务的 API Key（OpenAI、DeepSeek、Moonshot、Qwen、Ollama 等都支持）：

```bash
export CASEMAP_LLM_API_KEY=sk-...
uv run casemap generate examples/petstore_swagger.json -o /tmp/cases.html \
    --llm --model gpt-4o-mini
```

LLM 失败时会回退到纯结构化用例，脑图照常可用。
