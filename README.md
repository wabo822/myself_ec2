# Jiahan Wang Personal Site + Local RAG

这是一个可本地运行、可部署到 EC2 的个人主页项目，包含：

- 法语个人品牌主页
- 本地免费 embedding 的 RAG 服务
- 网站内置 AI 入口，访客可以直接提问
- 预留知识库目录，后续可以继续往里加简历、项目说明、技术笔记等内容

## 1. 项目介绍

技术栈：

- 前端：HTML + CSS + JavaScript
- 后端：FastAPI
- RAG 检索：`fastembed + ONNX`
- 向量检索：本地内存余弦相似度
- LLM：通过环境变量接入你的 API，默认按 OpenAI-compatible Chat Completions 接口处理
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
```

### 第二步：配置 LLM API

复制环境变量模板：

```bash
cp backend/.env.example backend/.env
```

然后编辑 `backend/.env`，至少填写：

```env
LLM_API_BASE_URL=你的接口根地址
LLM_MODEL=你的模型名
LLM_API_KEY=你的 API Key
```

可选的轻量参数：

```env
EMBEDDING_THREADS=1
RAG_TOP_K=3
```

如果你的服务不是标准 OpenAI-compatible 路径，可以直接设置：

```env
LLM_CHAT_COMPLETIONS_URL=你的完整聊天接口 URL
```

### 第三步：启动服务

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

- `assets/js/content.js`
- `index.html`
- `assets/css/styles.css`

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

## 4. 如何部署到 AWS EC2

推荐架构：

- `uvicorn` 跑 FastAPI
- `systemd` 托管后端
- `nginx` 做反向代理

### 服务器需要安装的依赖

Amazon Linux 上至少需要：

- `python3`
- `python3-pip`
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
```

3. 配置环境变量

```bash
cp backend/.env.example backend/.env
vim backend/.env
```

4. 先本地起服务验证

```bash
source .venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

5. 配置 systemd 和 nginx

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

6. 浏览器访问

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

## 7. 目录结构

```text
.
├── index.html
├── README.md
├── assets
│   ├── css/styles.css
│   ├── icons/favicon.svg
│   └── js
│       ├── content.js
│       └── main.js
├── backend
│   ├── .env.example
│   ├── app.py
│   ├── knowledge
│   │   └── jiahan_profile.md
│   ├── rag.py
│   └── requirements.txt
└── deploy
    ├── deploy-ec2.sh
    ├── nginx-personal-site.conf
    └── personal-site.service
```
