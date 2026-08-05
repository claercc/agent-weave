# 项目常用命令

以下命令默认在项目根目录执行：

```text
D:\ai_std_3\ai-agent-backend
```

## 一、日常开发流程

### 1. 自动格式化所有 Python 文件

```powershell
# Black 会直接修改不符合格式规范的文件
.\.venv\Scripts\python.exe -m black app tests scripts main.py
```

### 2. 执行全部质量检查

```powershell
# 依次执行 Black、flake8、MyPy 和 pytest
.\.venv\Scripts\python.exe scripts\check.py
```

### 3. 启动项目

```powershell
# 使用 pyproject.toml 注册的 start 命令启动 FastAPI
.\.venv\Scripts\start.exe
```

浏览器访问：

```text
http://localhost:8000/
http://localhost:8000/docs
http://localhost:8000/api/health/live
```

## 二、Black 格式检查

### 检查全部文件，不自动修改

```powershell
# --check 只检查，不修改文件
.\.venv\Scripts\python.exe -m black `
  --check `
  app tests scripts main.py
```

### 检查单个文件

```powershell
# 将文件路径替换成需要检查的文件
.\.venv\Scripts\python.exe -m black `
  --check `
  app\services\chat_service.py
```

### 查看 Black 想怎样修改

```powershell
# --diff 显示当前代码与 Black 目标格式的差异
.\.venv\Scripts\python.exe -m black `
  --check `
  --diff `
  app\services\chat_service.py
```

差异符号：

```text
- 当前文件中的代码
+ Black 建议的代码
```

### 自动格式化单个文件

```powershell
# 不带 --check，Black 会直接修改文件
.\.venv\Scripts\python.exe -m black `
  app\services\chat_service.py
```

---

## 三、flake8 代码规范检查

### 检查全部代码

```powershell
# 检查未使用变量、未定义名称、换行和其他代码规范
.\.venv\Scripts\python.exe -m flake8 `
  app tests scripts main.py
```

### 检查单个文件

```powershell
.\.venv\Scripts\python.exe -m flake8 `
  app\services\chat_service.py
```

错误示例：

```text
app/example.py:10:5: F841 local variable is assigned but never used
```

读取方式：

```text
文件路径:行号:列号:错误编号 错误说明
```

---

## 四、MyPy 类型检查

### 检查全部源码

```powershell
# 检查参数、返回值和变量类型是否一致
.\.venv\Scripts\python.exe -m mypy `
  app scripts main.py
```

### 检查单个文件

```powershell
.\.venv\Scripts\python.exe -m mypy `
  app\api\chat.py
```

错误示例：

```text
app/example.py:10: error: Argument 1 has incompatible type "str"
```

重点查看：

```text
哪个文件
哪一行
实际传入什么类型
代码要求什么类型
```

---

## 五、pytest 自动化测试

### 运行全部测试

```powershell
# -q 使用简洁输出
.\.venv\Scripts\python.exe -m pytest -q
```

### 运行单个测试文件

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_chat.py `
  -v
```

### 运行单个测试函数

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests\test_health.py::test_liveness `
  -v
```

### 显示更完整的失败信息

```powershell
# -vv 增加输出，-s 显示 print 和日志内容
.\.venv\Scripts\python.exe -m pytest `
  tests\test_chat.py `
  -vv `
  -s
```

### 失败后立即停止

```powershell
# -x 表示第一次失败后停止
.\.venv\Scripts\python.exe -m pytest `
  -x `
  -vv
```

---

## 六、项目初始化与依赖安装

### 首次初始化项目

```powershell
# 创建 .venv、安装锁定依赖并创建 .env
python scripts\bootstrap.py
```

### 根据锁文件安装开发依赖

```powershell
# --require-hashes 会校验依赖文件哈希
.\.venv\Scripts\python.exe -m pip install `
  --require-hashes `
  --requirement requirements-dev.lock
```

### 安装当前项目

```powershell
# --no-deps 表示依赖已经从锁文件安装
# --editable 表示以开发模式安装当前项目
.\.venv\Scripts\python.exe -m pip install `
  --no-deps `
  --no-build-isolation `
  --editable .
```

### 检查依赖是否冲突

```powershell
.\.venv\Scripts\python.exe -m pip check
```

### 查看已安装依赖

```powershell
.\.venv\Scripts\python.exe -m pip list
```

### 查看指定依赖版本

```powershell
.\.venv\Scripts\python.exe -c `
  "import fastapi, pydantic, starlette; print('FastAPI:', fastapi.__version__); print('Pydantic:', pydantic.__version__); print('Starlette:', starlette.__version__)"
```

---

## 七、重新生成依赖锁文件

修改 `pyproject.toml` 中的依赖后，需要重新生成锁文件。

### 生成生产依赖锁文件

```powershell
.\.venv\Scripts\python.exe -m piptools compile `
  --generate-hashes `
  --strip-extras `
  --output-file requirements.lock `
  pyproject.toml
```

### 生成开发依赖锁文件

```powershell
.\.venv\Scripts\python.exe -m piptools compile `
  --extra dev `
  --generate-hashes `
  --strip-extras `
  --output-file requirements-dev.lock `
  pyproject.toml
```

### 检查是否包含不需要的重量级依赖

```powershell
Select-String `
  -Path requirements.lock `
  -Pattern "sentence-transformers|torch==|transformers=="
```

没有输出表示没有找到这些依赖。

---

## 八、启动与接口检查

### 使用 start 命令启动

```powershell
.\.venv\Scripts\start.exe
```

### 使用 Uvicorn 直接启动

```powershell
# 主要用于排查 start 入口问题
.\.venv\Scripts\python.exe -m uvicorn `
  main:app `
  --host 0.0.0.0 `
  --port 8000
```

注意：

```text
0.0.0.0:8000 是服务器监听地址
localhost:8000 是浏览器访问地址
```

### 检查根接口

```powershell
Invoke-RestMethod http://localhost:8000/
```

### 检查存活状态

```powershell
Invoke-RestMethod `
  http://localhost:8000/api/health/live
```

### 检查就绪状态

```powershell
Invoke-RestMethod `
  http://localhost:8000/api/health/ready
```

### 打开 Swagger 文档

```text
http://localhost:8000/docs
```

---

## 九、Git 差异检查

### 查看所有未提交改动

```powershell
git status --short
```

状态符号：

```text
M  已修改
A  已添加
?? 未被 Git 跟踪
```

### 查看全部代码差异

```powershell
git diff
```

### 查看单个文件差异

```powershell
git diff -- app\services\chat_service.py
```

### 查看已经暂存的差异

```powershell
git diff --staged
```

### 查看最近提交

```powershell
git log --oneline -10
```

---

## 十、错误排查顺序

统一检查失败后，按照以下顺序处理：

```text
1. 查看失败的是哪个工具
2. 查看失败的是哪个文件
3. 单独运行该工具检查这个文件
4. 查看具体差异或行号
5. 修复后再次单独检查
6. 最后重新执行 scripts/check.py
```

### Black失败

```powershell
python -m black --check --diff 文件路径
python -m black 文件路径
```

### flake8失败

```powershell
python -m flake8 文件路径
```

### MyPy失败

```powershell
python -m mypy 文件路径
```

### pytest失败

```powershell
python -m pytest 测试文件 -vv -s
```

---

## 十一、Docker 命令

需要先完成 Windows、WSL 2 和 Docker Desktop 安装。

### 验证 Docker

```powershell
docker version
docker compose version
```

### 检查 Compose 配置

```powershell
docker compose config
```

### 构建并后台启动

```powershell
docker compose up --build --detach
```

### 查看容器状态

```powershell
docker compose ps
```

### 查看后端日志

```powershell
docker compose logs --follow backend
```

按 `Ctrl+C` 只会停止查看日志，不会停止容器。

### 停止并删除容器

```powershell
# 保留 Chroma 数据卷
docker compose down
```

### 停止并删除容器及数据

```powershell
# 会永久删除 Docker 中保存的 Chroma 数据，谨慎使用
docker compose down --volumes
```

---

## 十二、最常用的三个命令

平时主要记住：

```powershell
# 1. 自动整理代码格式
.\.venv\Scripts\python.exe -m black app tests scripts main.py

# 2. 执行全部质量检查
.\.venv\Scripts\python.exe scripts\check.py

# 3. 启动服务
.\.venv\Scripts\start.exe
```