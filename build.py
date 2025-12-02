#!/usr/bin/env python3
"""
build.py - 静态站点生成器
功能：
1. 将 src 目录中的内容生成为静态页面放到 doc 目录
2. public 目录中的文件不加密，其他文件需要加密
3. md 文件使用 style.css 渲染
4. 生成 index.html 作为目录首页，使用 index.css 渲染
5. 已生成的文件不再重复生成（增量构建）
6. 自动生成随机密码并保存到 passwords.json
"""

import os
import subprocess
import shutil
import hashlib
import json
import secrets
import string
from pathlib import Path
from datetime import datetime
import markdown

# 配置
SRC_DIR = Path("src")
DOC_DIR = Path("docs")
ASSETS_DIR = Path("assets")
MD_STYLE_CSS = ASSETS_DIR / "md_style.css"
INDEX_CSS = ASSETS_DIR / "index.css"
PASSWORDS_FILE = Path("passwords.json")

# 重要文件说明：
# - .staticrypt.json: staticrypt 的盐值文件，不能删除！删除会导致密码记忆失效
# - docs/.build_cache: 增量构建缓存，删除后会全量重建（可选保留）


def generate_password(length: int = 16) -> str:
    """生成随机密码"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def load_passwords() -> dict:
    """加载密码本"""
    if PASSWORDS_FILE.exists():
        with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "created_at": datetime.now().isoformat(),
        "files": {}
    }


def save_passwords(passwords: dict):
    """保存密码本"""
    passwords["updated_at"] = datetime.now().isoformat()
    with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(passwords, f, ensure_ascii=False, indent=2)
    print(f"🔑 密码本已保存: {PASSWORDS_FILE}")


def get_password_for_file(passwords: dict, file_path: str, file_name: str) -> str:
    """获取文件的密码，如果不存在则生成新密码"""
    if file_path in passwords.get("files", {}):
        return passwords["files"][file_path]["password"]
    
    # 生成新密码
    new_password = generate_password()
    passwords["files"][file_path] = {
        "name": file_name,
        "password": new_password,
        "created_at": datetime.now().isoformat()
    }
    return new_password


def get_file_hash(filepath: Path) -> str:
    """计算文件的 MD5 哈希值"""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_build_cache() -> dict:
    """加载构建缓存"""
    cache_file = DOC_DIR / ".build_cache"
    cache = {}
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and ":" in line:
                    path, hash_val = line.rsplit(":", 1)
                    cache[path] = hash_val
    return cache


def save_build_cache(cache: dict):
    """保存构建缓存"""
    cache_file = DOC_DIR / ".build_cache"
    with open(cache_file, "w", encoding="utf-8") as f:
        for path, hash_val in cache.items():
            f.write(f"{path}:{hash_val}\n")


def needs_rebuild(src_path: Path, cache: dict) -> bool:
    """检查文件是否需要重新构建"""
    src_str = str(src_path)
    current_hash = get_file_hash(src_path)
    
    if src_str not in cache:
        return True
    
    return cache[src_str] != current_hash


def is_public_file(src_path: Path) -> bool:
    """判断文件是否在 public 目录中（不需要加密）"""
    parts = src_path.parts
    return "public" in parts


def get_output_path(src_path: Path) -> Path:
    """获取输出文件路径"""
    relative = src_path.relative_to(SRC_DIR)
    
    # 如果是 md 文件，改为 html
    if src_path.suffix.lower() == ".md":
        relative = relative.with_suffix(".html")
    
    return DOC_DIR / relative


def convert_md_to_html(md_path: Path, style_css_content: str) -> str:
    """将 Markdown 转换为 HTML"""
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    
    # 使用 markdown 库转换，启用数学公式支持
    html_content = markdown.markdown(
        md_content,
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "nl2br",
            "pymdownx.arithmatex",  # 数学公式支持
            "pymdownx.superfences",  # 增强的代码块
            "pymdownx.highlight",    # 代码高亮
        ],
        extension_configs={
            "pymdownx.arithmatex": {
                "generic": True  # 使用通用模式，兼容 KaTeX/MathJax
            },
            "pymdownx.highlight": {
                "use_pygments": True,
                "css_class": "highlight"
            }
        }
    )
    
    # 获取标题（从文件名或 md 第一行）
    title = md_path.stem
    lines = md_content.strip().split("\n")
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
    
    # 生成完整 HTML（包含 KaTeX 支持）
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- KaTeX CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <style>
{style_css_content}
    </style>
    <style>
        body {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 1rem;
            color: #0366d6;
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        /* 数学公式样式 */
        .arithmatex {{
            overflow-x: auto;
        }}
    </style>
</head>
<body class="markdown-body">
    <a href="./index.html" class="back-link">← 返回目录</a>
    {html_content}
    
    <!-- KaTeX JS -->
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{
            delimiters: [
                {{left: '$$', right: '$$', display: true}},
                {{left: '$', right: '$', display: false}},
                {{left: '\\\\[', right: '\\\\]', display: true}},
                {{left: '\\\\(', right: '\\\\)', display: false}}
            ],
            throwOnError: false
        }});"></script>
</body>
</html>
'''
    return full_html


def encrypt_html(html_path: Path, output_path: Path, password: str):
    """使用 staticrypt 加密 HTML 文件"""
    # staticrypt 会忽略 -o 指定的目录结构，默认输出到 encrypted/
    # 所以我们需要手动处理输出
    
    # 创建临时目录用于 staticrypt 输出
    temp_encrypted_dir = Path("encrypted")
    temp_encrypted_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "staticrypt",
        str(html_path),
        "-p", password,
        "--short",
        "--remember", "7",
        "--template-title", "请输入密码",
        "--template-instructions", "此页面已加密，请输入密码查看内容",
        "--template-button", "解锁"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  ⚠️  加密失败: {result.stderr}")
        return False
    
    # staticrypt 默认输出到 encrypted/{filename}
    encrypted_output = temp_encrypted_dir / html_path.name
    
    if encrypted_output.exists():
        # 确保目标目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 移动到正确的位置
        shutil.move(str(encrypted_output), str(output_path))
        return True
    else:
        print(f"  ⚠️  找不到加密后的文件: {encrypted_output}")
        return False


def process_file(src_path: Path, cache: dict, style_css_content: str, passwords: dict) -> bool:
    """处理单个文件"""
    output_path = get_output_path(src_path)
    is_public = is_public_file(src_path)
    
    # 检查是否需要重建
    if not needs_rebuild(src_path, cache):
        if output_path.exists():
            print(f"  ⏭️  跳过 (未修改): {src_path}")
            return False
    
    # 创建输出目录
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    suffix = src_path.suffix.lower()
    
    # 获取文件显示名称
    file_name = src_path.stem
    if suffix == ".md":
        with open(src_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("# "):
                file_name = first_line[2:].strip()
    
    if suffix == ".md":
        # 转换 Markdown 为 HTML
        html_content = convert_md_to_html(src_path, style_css_content)
        
        if is_public:
            # 直接写入
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"  ✅ 转换 (公开): {src_path} -> {output_path}")
        else:
            # 获取该文件的密码（每个文件独立密码）
            password = get_password_for_file(passwords, str(src_path), file_name)
            
            # 先写入临时文件，再加密
            temp_path = output_path.with_suffix(".temp.html")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            if encrypt_html(temp_path, output_path, password):
                print(f"  🔒 转换+加密: {src_path} -> {output_path}")
            
            # 删除临时文件
            temp_path.unlink(missing_ok=True)
    
    elif suffix == ".html":
        if is_public:
            # 直接复制
            shutil.copy2(src_path, output_path)
            print(f"  ✅ 复制 (公开): {src_path} -> {output_path}")
        else:
            # 获取该文件的密码（每个文件独立密码）
            password = get_password_for_file(passwords, str(src_path), file_name)
            
            # 加密后复制
            if encrypt_html(src_path, output_path, password):
                print(f"  🔒 加密: {src_path} -> {output_path}")
    
    else:
        # 其他文件直接复制
        shutil.copy2(src_path, output_path)
        print(f"  📄 复制: {src_path} -> {output_path}")
    
    # 更新缓存
    cache[str(src_path)] = get_file_hash(src_path)
    return True


def collect_files() -> list:
    """收集所有需要处理的文件"""
    files = []
    for src_path in SRC_DIR.rglob("*"):
        if src_path.is_file() and not src_path.name.startswith("."):
            files.append(src_path)
    return files


def generate_index(files: list, index_css_content: str):
    """生成目录首页"""
    
    # 按目录分组文件
    public_files = []
    encrypted_files = []
    
    for src_path in files:
        if src_path.suffix.lower() in [".md", ".html"]:
            output_path = get_output_path(src_path)
            relative_output = output_path.relative_to(DOC_DIR)
            
            # 获取显示名称
            if src_path.suffix.lower() == ".md":
                # 尝试从 md 文件获取标题
                with open(src_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("# "):
                        name = first_line[2:].strip()
                    else:
                        name = src_path.stem
            else:
                name = src_path.stem
            
            file_info = {
                "name": name,
                "path": str(relative_output),
                "src_path": str(src_path),
                "is_public": is_public_file(src_path)
            }
            
            if file_info["is_public"]:
                public_files.append(file_info)
            else:
                encrypted_files.append(file_info)
    
    # 生成文件列表 HTML
    def generate_file_list(files_list: list, section_title: str, is_public: bool) -> str:
        if not files_list:
            return ""
        
        items = []
        for f in files_list:
            public_class = "is-public" if is_public else ""
            status_class = "status-public" if is_public else "status-lock"
            status_icon = "🌐 公开" if is_public else "🔒 加密"
            
            items.append(f'''
                <li>
                    <a href="{f['path']}" class="{public_class}">
                        <span class="file-name">{f['name']}</span>
                        <span class="file-status {status_class}">{status_icon}</span>
                    </a>
                </li>''')
        
        return f'''
        <section class="file-section">
            <h2>{section_title}</h2>
            <ul class="file-list">
                {"".join(items)}
            </ul>
        </section>'''
    
    encrypted_section = generate_file_list(encrypted_files, "📚 加密文档", False)
    public_section = generate_file_list(public_files, "📖 公开文档", True)
    
    # 生成完整的 index.html
    index_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhD Site - 文档目录</title>
    <style>
{index_css_content}

/* 额外样式 */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 2rem;
}}

.container {{
    max-width: 800px;
    margin: 0 auto;
}}

header {{
    text-align: center;
    margin-bottom: 2rem;
    color: white;
}}

header h1 {{
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}}

header p {{
    font-size: 1.1rem;
    opacity: 0.9;
}}

.file-section {{
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}}

.file-section h2 {{
    color: #24292e;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e1e4e8;
}}

.file-list {{
    list-style: none;
}}

.file-list li {{
    margin-bottom: 0.75rem;
}}

.file-name {{
    flex-grow: 1;
}}

footer {{
    text-align: center;
    color: rgba(255,255,255,0.8);
    margin-top: 2rem;
    font-size: 0.9rem;
}}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📚 PhD Site</h1>
            <p>个人文档管理系统</p>
        </header>
        
        {encrypted_section}
        {public_section}
        
        <footer>
            <p>构建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </footer>
    </div>
</body>
</html>
'''
    
    # 写入 index.html
    index_path = DOC_DIR / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    
    print(f"\n📋 生成目录页: {index_path}")


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 开始构建静态站点")
    print("=" * 50)
    
    # 确保输出目录存在
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    
    # 加载或生成密码本
    passwords = load_passwords()
    
    # 复制 assets 到 doc
    assets_output = DOC_DIR / "assets"
    if ASSETS_DIR.exists():
        if assets_output.exists():
            shutil.rmtree(assets_output)
        shutil.copytree(ASSETS_DIR, assets_output)
        print(f"\n📁 复制资源目录: {ASSETS_DIR} -> {assets_output}")
    
    # 读取 CSS 文件内容
    style_css_content = ""
    if MD_STYLE_CSS.exists():
        with open(MD_STYLE_CSS, "r", encoding="utf-8") as f:
            style_css_content = f.read()
    
    index_css_content = ""
    if INDEX_CSS.exists():
        with open(INDEX_CSS, "r", encoding="utf-8") as f:
            index_css_content = f.read()
    
    # 加载构建缓存
    cache = load_build_cache()
    
    # 收集所有文件
    files = collect_files()
    print(f"\n📄 发现 {len(files)} 个文件待处理\n")
    
    # 处理每个文件
    processed_count = 0
    for src_path in files:
        if process_file(src_path, cache, style_css_content, passwords):
            processed_count += 1
    
    # 保存缓存
    save_build_cache(cache)
    
    # 保存密码本
    save_passwords(passwords)
    
    # 生成目录页
    generate_index(files, index_css_content)
    
    # 清理临时的 encrypted 目录（如果为空）
    encrypted_dir = Path("encrypted")
    if encrypted_dir.exists():
        # 删除临时文件
        for temp_file in encrypted_dir.glob("*.temp.html"):
            temp_file.unlink()
        # 如果目录为空则删除
        if not any(encrypted_dir.iterdir()):
            encrypted_dir.rmdir()
            print(f"\n🧹 清理临时目录: {encrypted_dir}")
    
    print("\n" + "=" * 50)
    print(f"✨ 构建完成! 处理了 {processed_count} 个文件")
    print(f"📂 输出目录: {DOC_DIR.absolute()}")
    print(f"🔑 密码本: {PASSWORDS_FILE.absolute()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
