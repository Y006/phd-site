# 🔐 My Secure Docs

个人加密文档仓库。基于 Python + Staticrypt 自动化构建。

## ⚡️ 使用指南 (Workflow)

### 1. 写作 (Write)
将 Markdown 或 HTML 文件放入 `src/` 目录：
- **🔒 加密内容**：直接放在 `src/` 根目录或子目录下（例如 `src/notes/`）。
- **🔓 公开内容**：必须放在 `src/public/` 目录下（无需密码即可访问）。

### 2. 构建 (Build)
在终端运行脚本，自动生成加密网页并更新索引：
```bash
python build.py
```

## 🛠 使用此模板 (How to use)

你可以直接 Clone 本仓库作为你的起点。

### 1. 安装依赖
确保安装了 Python 3 和 Node.js。
```bash
npm install -g staticrypt