# Jiahan Wang Personal Site + Local RAG

这是一个可本地运行、可部署到 EC2 的个人主页项目，包含：

- 法语个人品牌主页
- 本地免费 embedding 的 RAG 服务
- 网站内置 AI 入口，访客可以直接提问
- 预留知识库目录，后续可以继续往里加简历、项目说明、技术笔记等内容

## 1. 项目介绍

技术栈：

- 前端：React + Vite
- 后端：FastAPI
- RAG 检索：`fastembed + ONNX`
- 向量检索：本地内存余弦相似度
- LLM：通过环境变量接入你的 API，默认已适配 Claude / Anthropic Messages API，同时兼容 OpenAI-compatible Chat Completions
- 轻量优化：避免 `torch`，默认走更适合 micro 服务器的 embedding 运行时

当前知识库内容：

- 基于你的简历整理出的结构化文本
- 后续可以继续向 `backend/knowledge/` 里添加 `.md`、`.txt`、可提取文本的 `.pdf`

## 2. 本地运行方法

### 第一步：创建虚拟环境并安装依赖

```bash
cd /Users/asen/Desktop/presentation
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

### 第二步：配置 LLM API

复制环境变量模板：

```bash
cp backend/.env.example backend/.env
```

如果你现在用的是 Claude，`backend/.env.example` 已经是 Claude 默认配置。复制后至少确认：

```env
LLM_PROVIDER=anthropic
LLM_MESSAGES_URL=https://api.anthropic.com/v1/messages
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=你的 Anthropic API Key
```

可选的轻量参数：

```env
LLM_MAX_TOKENS=1024
LLM_TEMPERATURE=0.2
EMBEDDING_THREADS=1
RAG_TOP_K=3
```

如果你要继续接 OpenAI-compatible 服务，可以改成：

```env
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=你的接口根地址
LLM_API_PATH=/chat/completions
LLM_CHAT_COMPLETIONS_URL=你的完整聊天接口 URL
LLM_API_KEY_HEADER=Authorization
LLM_API_KEY_PREFIX=Bearer
```

### 第三步：构建 React 前端

```bash
cd frontend
npm run build
cd ..
```

### 第四步：启动服务

```bash
source .venv/bin/activate
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

打开：

```text
http://localhost:8000
```

## 3. 如何修改内容

### 修改页面文案和展示内容

- `frontend/src/siteContent.js`
- `frontend/src/App.jsx`
- `frontend/src/styles.css`

### 修改 RAG 知识库

知识库目录：

```text
backend/knowledge/
```

当前已经放了一个整理过的简历知识文件。后续你可以继续添加：

- `.md`
- `.txt`
- 文本可提取的 `.pdf`

注意：

- 你现在这份 `cv_mars2026.pdf` 是扫描版 PDF，不适合直接做文本检索
- 所以我已经先把简历内容整理成了知识库文本文件
- 后续如果你新增 PDF，最好优先放 markdown / txt，RAG 效果会更稳定
- 当前默认 embedding 方案已经按小服务器做过收缩，适合“个人主页问答”这种轻量场景

### 修改 RAG 行为

主要文件：

- `backend/app.py`：API、LLM 调用、静态页面服务
- `backend/rag.py`：文档加载、切块、embedding、检索
- `backend/.env.example`：配置模板
- `frontend/`：React 前端源码和构建配置

## 4. 如何部署到 AWS EC2

推荐架构：

- `uvicorn` 跑 FastAPI
- `systemd` 托管后端
- `nginx` 做反向代理

### 服务器需要安装的依赖

Amazon Linux 上至少需要：

- `python3`
- `python3-pip`
- `nodejs`
- `nginx`
- `git`

### 手动部署步骤

1. 拉代码

```bash
git clone https://github.com/wabo822/myself_ec2.git
cd myself_ec2
```

2. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

3. 配置环境变量

```bash
cp backend/.env.example backend/.env
vim backend/.env
```

4. 构建 React 前端

```bash
cd frontend
npm run build
cd ..
```

5. 先本地起服务验证

```bash
source .venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

6. 配置 systemd 和 nginx

项目里已经准备好了：

- `deploy/personal-site.service`
- `deploy/nginx-personal-site.conf`

复制到系统目录：

```bash
sudo cp deploy/personal-site.service /etc/systemd/system/personal-site.service
sudo cp deploy/nginx-personal-site.conf /etc/nginx/conf.d/personal-site.conf
sudo systemctl daemon-reload
sudo systemctl enable --now personal-site.service
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

7. 浏览器访问

```text
http://你的EC2公网IP
```

### 自动部署脚本

你也可以直接用：

```bash
chmod +x deploy/deploy-ec2.sh
EC2_HOST=你的EC2公网IP ./deploy/deploy-ec2.sh
```

如果你有域名：

```bash
EC2_HOST=你的EC2公网IP SERVER_NAME=your-domain.com ./deploy/deploy-ec2.sh
```

## 5. 如何绑定域名

最简步骤：

1. 把域名的 `A` 记录指向 EC2 公网 IP
2. 修改 `deploy/nginx-personal-site.conf` 里的 `server_name`
3. 重载 nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

4. 如果要 HTTPS，再补 Let's Encrypt / Certbot

## 6. GitHub 说明

当前代码已经推送到：

```text
https://github.com/wabo822/myself_ec2
```

后续你只需要在服务器上：

```bash
git pull
```

然后重新安装依赖或重启服务即可。

## 7. CI/CD（自动化测试和部署）

项目已经接入 GitHub Actions：每次 push / PR 都会自动跑测试，main 分支合并后会自动部署到 EC2。

### 测试栈

- **后端单元 / 集成测试**：`pytest`，位于 `backend/tests/`
  - `test_rag.py`：知识库切块、向量归一化、文档加载
  - `test_app_helpers.py`：LLM provider 解析、URL 构造、鉴权头、healthcheck 状态
  - `test_app_endpoints.py`：FastAPI TestClient 集成测试（`/api/health`、`/api/chat`、静态路由）
- **前端单元测试**：`Vitest` + `@testing-library/react`，位于 `frontend/src/__tests__/`
- **端到端测试**：`Playwright`（Chromium），位于 `frontend/tests-e2e/`，跑在 `npm run preview` 打出来的真实构建产物上，用 `page.route` mock `/api/*`

### 本地跑测试

```bash
# 后端
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/python -m pytest

# 前端单元
cd frontend
npm install
npm test

# 前端 e2e（首次需要装 chromium，约 300MB）
npm run test:e2e:install
npm run build
npm run test:e2e
```

### CI workflow

`.github/workflows/ci.yml` 在 push / PR 时跑三个 job：

1. `backend`：`pytest` + 覆盖率
2. `frontend`：`vitest run` + `vite build`，把 `dist/` 上传成 artifact
3. `e2e`：下载上一步的 `dist`，装 chromium，跑 Playwright

三个 job 全绿之后，仅在 push 到 `main` 时触发 `deploy` job。

### CD：自动部署到 EC2

`deploy` job 会通过 SSH 连到 EC2，跑下面这套：

```bash
git fetch && git reset --hard origin/main
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart personal-site.service
curl http://127.0.0.1:8000/api/health   # 健康检查
```

也可以手动跑：`bash deploy/update-on-server.sh`

### 启用 CD 前需要做的一次性配置

#### a) 在服务器允许 ec2-user 无密码 sudo restart

```bash
echo 'ec2-user ALL=(root) NOPASSWD: /bin/systemctl restart personal-site.service, /bin/systemctl reload-or-restart personal-site-healthcheck.timer' | sudo tee /etc/sudoers.d/personal-site
sudo chmod 440 /etc/sudoers.d/personal-site
```

#### b) 生成一对部署专用的 SSH key

在你的本地（不要复用个人 key）：

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/myself_ec2_deploy -N ""
ssh-copy-id -i ~/.ssh/myself_ec2_deploy.pub ec2-user@<EC2_HOST>
```

#### c) 在 GitHub 仓库设置里加 4 个 secret

`Settings → Secrets and variables → Actions → New repository secret`：

| Secret name | 值 |
| --- | --- |
| `EC2_HOST` | EC2 公网 IP 或域名 |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | `~/.ssh/myself_ec2_deploy` 的私钥内容（整个文件） |
| `EC2_PORT` | `22`（如果换了 SSH 端口才填） |

#### d) ⚠️ 第一次 deploy 之前 —— 提交服务器上的本地改动

CD 用的是 `git reset --hard origin/main`，会**清掉服务器上所有未提交的改动**。
如果你曾经直接在 EC2 上改过文件（比如 `backend/.env` 之外的代码），先：

```bash
cd /home/ec2-user/myself_ec2
git status              # 看清楚哪些动过
git stash               # 或 commit + push
```

`backend/.env` 在 `.gitignore` 里，CD 不会动它，安全。

### 触发部署

- 自动：push 到 `main` → CI 全绿 → 自动 deploy
- 手动：`Actions` 页面找到对应 workflow run，点 `Re-run jobs`

## 8. 目录结构

```text
.
├── README.md
├── pytest.ini
├── .github/workflows/ci.yml
├── assets
│   ├── css/styles.css
│   ├── icons/favicon.svg
│   ├── images
│   └── js
├── backend
│   ├── .env.example
│   ├── app.py
│   ├── healthcheck.py
│   ├── knowledge
│   │   └── jiahan_profile.md
│   ├── rag.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── tests
│       ├── conftest.py
│       ├── test_app_endpoints.py
│       ├── test_app_helpers.py
│       └── test_rag.py
├── frontend
│   ├── index.html
│   ├── package.json
│   ├── playwright.config.js
│   ├── src
│   │   ├── __tests__/App.test.jsx
│   │   └── test/setup.js
│   ├── tests-e2e/portfolio.spec.js
│   └── vite.config.js
└── deploy
    ├── deploy-ec2.sh
    ├── update-on-server.sh
    ├── nginx-personal-site.conf
    ├── personal-site.service
    ├── personal-site-healthcheck.service
    └── personal-site-healthcheck.timer
```
