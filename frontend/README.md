# AI Agent Frontend

Next.js 16 前端用于展示 Agent 对话、RAG 引用、工具执行轨迹和人工审批。

## 启动

先启动 FastAPI 后端，然后执行：

```powershell
Copy-Item .env.example .env.local
npm.cmd ci
npm.cmd run dev
```

默认后端地址为 `http://127.0.0.1:8000`，可通过 `.env.local` 中的 `BACKEND_BASE_URL` 修改。

打开 [http://localhost:3000](http://localhost:3000) 使用 Agent 工作台。

## 质量检查

```bash
npm run lint
npx tsc --noEmit
npm run build
```
