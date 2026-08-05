# AI Agent Backend

基于 FastAPI、LangGraph 和 Chroma 构建的 AI Agent 后端，支持自动请求路由、工具调用、私有知识库问答、PDF/OCR 导入和引用溯源。

## 核心能力

- 普通对话、工具调用和 RAG 自动路由
- LangGraph 状态工作流和会话上下文
- Calculator 与 Weather 工具
- Chroma 向量知识库
- PDF 文本提取与 OCR 回退
- 带来源引用的知识库回答
- pytest、MyPy、flake8 和 Black 自动质量检查
- 可复现依赖锁定与 Docker 部署

## 环境要求

- Python 3.13
- Git
- 模型服务 API 密钥
- Docker Desktop，可选

## 本地快速启动

克隆项目：

```bash
git clone https://github.com/claercc/ai_std_3
cd ai-agent-backend
```

自动创建环境并安装依赖：

```bash
python scripts/bootstrap.py
```

打开 `.env` 并填写：

```dotenv
OPENAI_API_KEY=填写你的密钥
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

Windows 启动：

```powershell
.\.venv\Scripts\start.exe
```

Linux 或 macOS 启动：

```bash
./.venv/bin/start
```

服务地址：

- API 根地址：<http://localhost:8000>
- Swagger 文档：<http://localhost:8000/docs>
- 存活检查：<http://localhost:8000/api/health/live>
- 就绪检查：<http://localhost:8000/api/health/ready>

## Docker 启动

复制环境变量示例：

```bash
cp .env.example .env
```

填写 `.env` 后执行：

```bash
docker compose up --build --detach
```

查看状态：

```bash
docker compose ps
```

停止服务：

```bash
docker compose down
```

## 质量检查

执行统一质量门禁：

```bash
python scripts/check.py
```

检查内容包括：

- Black 代码格式
- flake8 代码规范
- MyPy 严格类型检查
- pytest 自动化测试