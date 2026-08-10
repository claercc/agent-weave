# AI Agent Backend

一个面向 AI 应用开发岗位的全栈 Agent 演示项目。

项目使用 FastAPI、LangGraph、Chroma 和本地 BGE Embedding 构建 Agent 后端，并提供 Next.js 前端，用于展示结构化意图分析、RAG、工具调用、SSE 流式输出、执行轨迹和 Human-in-the-loop 人工审批。

## 项目定位

传统聊天接口通常只有：

```text
用户问题 → LLM → 文本回答
```

本项目实现了一条可观察、可中断、可恢复的 Agent 工作流：

```text
用户请求
→ 结构化意图分析
→ 工作流路由
→ 普通对话 / RAG / 工具 Agent
→ SSE 执行事件
→ 前端实时展示
```

对于创建工单等可能产生外部副作用的操作，工作流会在工具执行前暂停，等待用户批准或拒绝，再从 LangGraph checkpoint 恢复执行。

## 在线能力概览

### 结构化请求分析

Router 不只返回简单路由，还会生成结构化分析结果：

```json
{
  "intent": "knowledge_query",
  "route": "rag",
  "needs_knowledge": true,
  "needs_tools": false,
  "requires_clarification": false,
  "rewritten_query": "AI Agent Backend 如何实现工具调用前的人工审批？",
  "clarification_question": null,
  "reason": "用户的问题需要查询项目知识库"
}
```

当前支持四种意图：

| 意图 | 说明 | 默认路由 |
|---|---|---|
| `conversation` | 普通交流、问候和解释 | `chat` |
| `knowledge_query` | 私有知识库查询 | `rag` |
| `information_tool` | 天气、时间、计算等只读工具 | `agent` |
| `action` | 创建工单等有副作用的操作 | `agent` |

当任务缺少必要参数时，工作流会先进入 `clarify` 节点向用户提问，而不是猜测参数或直接执行。

### 显式 Embedding 与 RAG

项目使用本地模型：

```text
BAAI/bge-small-zh-v1.5
```

实际检索链路为：

```text
PDF / 文本
→ 文档解析
→ OCR 回退
→ 文本分块
→ BGE 批量生成 512 维归一化向量
→ 显式写入 Chroma
→ 查询向量化
→ cosine 相似度检索
→ 相关性过滤
→ 带引用回答
```

Embedding 不由 Chroma 隐式生成。入库和查询统一经过 `EmbeddingService`，保证模型、向量维度和相似度语义一致。

RAG 执行轨迹会展示：

- Router 改写后的独立检索问题
- 召回文档数量
- 文档来源和 PDF 页码
- cosine 相似度
- 过滤前后文档数量
- 最终引用来源

### 工具调用

当前内置工具包括：

| 工具 | 类型 | 是否需要审批 |
|---|---|---:|
| Calculator | 数学计算 | 否 |
| Time | 时间查询 | 否 |
| Weather | 天气查询 | 否 |
| Create Support Ticket | 创建模拟支持工单 | 是 |

只读工具可以直接执行。

创建工单属于有副作用的业务操作，必须经过人工审批。

### Human-in-the-loop

高风险工具调用流程：

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as Next.js
    participant A as FastAPI
    participant G as LangGraph
    participant T as Tool

    U->>F: 请求创建支持工单
    F->>A: POST /api/agent/chat/stream
    A->>G: 启动 Agent 工作流
    G->>G: 识别 action 意图
    G->>G: 生成工具调用参数
    G-->>A: interrupt(tool_approval)
    A-->>F: approval_required
    F-->>U: 展示工具名称和参数

    alt 用户批准
        U->>F: 批准执行
        F->>A: POST /api/agent/chat/resume/stream
        A->>G: Command(resume)
        G->>T: 执行工具
        T-->>G: 返回工单结果
        G-->>F: tool_result + token + done
    else 用户拒绝
        U->>F: 拒绝并填写原因
        F->>A: POST /api/agent/chat/resume/stream
        A->>G: Command(resume)
        G->>G: 不执行工具并生成后续回答
        G-->>F: approval_resolved + done
    end
```

工作流使用 `session_id` 作为 LangGraph `thread_id`。第一次 SSE 连接在 `interrupt()` 时结束，用户做出决定后通过第二次请求恢复同一条工作流。

### SSE 流式执行事件

后端不仅流式返回回答 token，还会输出 Agent 执行事件：

```text
start
analysis
route
retrieval
retrieval_graded
tool_call
approval_required
approval_resolved
tool_result
citations
token
done
error
```

前端通过原生 `fetch + ReadableStream` 解析 SSE，不依赖额外流式请求库。

Next.js Route Handler 直接转发 FastAPI 响应体，并关闭代理缓存和缓冲，保证 token 能够实时显示。

## 系统架构

```mermaid
flowchart LR
    User[用户] --> UI[Next.js 前端]

    UI --> Proxy[Next.js Route Handler]
    Proxy --> API[FastAPI Agent API]
    API --> Service[AgentService]
    Service --> Graph[LangGraph Workflow]

    Graph --> Router[Request Analysis]
    Router --> Chat[Chat]
    Router --> RAG[RAG Pipeline]
    Router --> Agent[Tool Agent]
    Router --> Clarify[Clarification]

    RAG --> Rewrite[Query Rewrite]
    Rewrite --> Embed[BGE Embedding]
    Embed --> Chroma[(Chroma)]
    Chroma --> Grade[Relevance Grade]
    Grade --> Generate[RAG Generation]

    Agent --> Tools[ToolNode]
    Agent --> Approval[Human Approval]
    Approval --> Tools

    Graph --> SSE[SSE Events]
    SSE --> Proxy
    Proxy --> UI
```

## LangGraph 工作流

```mermaid
flowchart TD
    Start([START]) --> Analyze[analyze_request]

    Analyze -->|需要澄清| Clarify[clarify]
    Clarify --> End([END])

    Analyze -->|conversation| Chat[chat]
    Chat --> End

    Analyze -->|knowledge_query| Prepare[prepare_retrieval_query]
    Prepare --> Retrieve[retrieve]
    Retrieve --> Grade[grade]
    Grade -->|存在相关文档| Generate[generate]
    Grade -->|没有相关文档| Fallback[fallback]
    Generate --> End
    Fallback --> End

    Analyze -->|information_tool / action| Agent[agent]
    Agent -->|无需工具| End
    Agent -->|低风险工具| Tools[tools]
    Agent -->|高风险工具| Approval[approval]

    Approval -->|批准| Tools
    Approval -->|拒绝| Agent
    Tools --> Agent
```

## 前端界面

前端使用 Next.js、TypeScript、Tailwind CSS 和 shadcn/ui，当前支持：

- Chat、RAG、Agent 和自动路由模式
- 真正的逐 token 流式回答
- 知识库集合管理
- PDF 上传
- 引用来源和相似度展示
- Agent 请求分析
- 路由原因
- RAG 召回和过滤轨迹
- 工具调用参数
- 人工审批卡片
- 批准或拒绝后恢复执行
- Agent 完整事件轨迹

## 技术栈

### Backend

- Python 3.13
- FastAPI
- LangGraph
- LangChain
- Pydantic
- OpenAI-compatible Chat API
- Sentence Transformers
- BAAI/bge-small-zh-v1.5
- Chroma
- PyPDF
- PyMuPDF
- RapidOCR

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide Icons
- 原生 `fetch + ReadableStream`

### Engineering

- pytest
- MyPy
- Black
- flake8
- GitHub Actions
- Docker
- Docker Compose

## 项目结构

```text
.
├── app
│   ├── api                 # FastAPI 路由
│   ├── core                # 配置、日志和生命周期
│   ├── domain              # 领域类型
│   ├── graph               # LangGraph State、Node 和 Workflow
│   ├── models              # 模型结构化输出
│   ├── prompts             # Router、Agent 和 RAG 提示词
│   ├── rag                 # PDF、OCR、Chunk、Embedding 和 Chroma
│   ├── schemas             # API 请求与响应模型
│   ├── services            # Agent、RAG、Chat 和 Tool 服务
│   ├── tools               # Calculator、Weather、Time 和 Ticket
│   └── utils               # SSE 等通用工具
├── frontend
│   └── src
│       ├── app             # Next.js App Router
│       ├── components      # 聊天、轨迹、审批和知识库 UI
│       ├── hooks           # Agent 聊天状态
│       ├── lib             # SSE 与 RAG 请求
│       └── types           # TypeScript 协议类型
├── scripts                 # 环境初始化和统一检查
├── tests                   # 后端自动测试
├── Dockerfile
├── docker-compose.yml
├── main.py
└── pyproject.toml
```

## 环境要求

- Python 3.13
- Node.js 20 或更高版本
- Git
- OpenAI-compatible Chat API 密钥
- Docker Desktop，可选

本地 BGE 模型首次运行时需要从 Hugging Face 下载。

## 快速启动

### 1. 克隆项目

```bash
git clone https://github.com/claercc/ai_std_3 ai-agent-backend
cd ai-agent-backend
```

### 2. 初始化 Python 环境

Windows：

```powershell
python scripts\bootstrap.py
```

也可以手动安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --editable ".[dev]"
```

Linux 或 macOS：

```bash
python scripts/bootstrap.py
```

### 3. 配置环境变量

复制示例文件：

```powershell
Copy-Item .env.example .env
```

填写：

```dotenv
OPENAI_API_KEY=你的模型服务密钥
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=你的聊天模型名称
MODEL_REQUEST_TIMEOUT_SECONDS=30
MODEL_MAX_RETRIES=2
```

天气工具还需要填写 `OPENWEATHER_API_KEY`。本地 Embedding 模型会在首次使用 RAG 时下载。

### 4. 启动后端

Windows：

```powershell
.\.venv\Scripts\python.exe main.py
```

Linux 或 macOS：

```bash
./.venv/bin/python main.py
```

验证服务：

```bash
curl http://127.0.0.1:8000/api/health/ready
```

API 文档位于 `http://127.0.0.1:8000/docs`。

### 5. 启动前端

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Windows PowerShell 可使用：

```powershell
cd frontend
Copy-Item .env.example .env.local
npm.cmd ci
npm.cmd run dev
```

浏览器访问 `http://127.0.0.1:3000`。如果后端不在本机，修改前端的 `BACKEND_BASE_URL`。

### Docker 启动后端

```bash
docker compose up --build
```

当前 Compose 管理后端、Chroma 数据卷和模型缓存；前端仍按上一节单独启动。

## API 示例

普通 Agent 请求：

```bash
curl -X POST http://127.0.0.1:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"现在几点？","mode":"auto"}'
```

SSE 流式请求：

```bash
curl -N -X POST http://127.0.0.1:8000/api/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo-1","message":"介绍一下这个项目","mode":"chat"}'
```

PDF 上传限制为 10 MB、100 页。查询不存在的知识库会返回 `404`。

## 质量检查

后端：

```bash
python scripts/check.py
```

前端：

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

GitHub Actions 会同时运行前后端检查。

## 已知限制

- LangGraph 当前使用内存 checkpoint，服务重启后会话和待审批状态不会保留。
- 当前没有用户认证，默认用于本地学习和作品演示，不应直接暴露到公网。
- Compose 当前只启动后端；生产部署需要为前端和后端配置独立域名、认证与限流。
- 本地 BGE、OCR 和 Chroma 更适合单机演示；多实例部署需要独立模型服务和持久化数据库。
