#!/usr/bin/env python3
"""
批量转换文档中的源码链接为双链接格式
"""

import re
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))

GITHUB_ORG = "MrLinWang"
GITHUB_REPO = "learn-llvm-by-ai"
LOCAL_BASE = project_root
GITHUB_BRANCH = "main"

def convert_link(match):
    """转换单个链接为双链接格式"""
    text = match.group(1)
    local_path = match.group(2)
    
    if "📁" in text or "🌐" in text:
        return match.group(0)
    
    line_match = re.search(r'#L(\d+)(?:-L(\d+))?$', local_path)
    line_part = ""
    if line_match:
        line_start = line_match.group(1)
        line_end = line_match.group(2) or line_start
        if line_start == line_end:
            line_part = f"#L{line_start}"
        else:
            line_part = f"#L{line_start}-L{line_end}"
        local_path = local_path[:local_path.rfind('#')]
    
    local_url = "file://" + LOCAL_BASE + "/" + local_path + line_part
    
    github_path = local_path.replace(LOCAL_BASE + "/", "")
    github_url = f"https://github.com/{GITHUB_ORG}/{GITHUB_REPO}/blob/{GITHUB_BRANCH}/{github_path}{line_part}"
    
    return f"[📁 {text}]({local_url}) · [🌐 GitHub]({github_url})"

def process_file(filepath, pattern):
    """处理单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(pattern, convert_link, content)
    
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ 已更新: {filepath}")
        return True
    return False

def main():
    docs_dir = os.path.join(project_root, "docs")
    
    if not os.path.exists(docs_dir):
        print(f"错误: 目录 {docs_dir} 不存在")
        sys.exit(1)
    
    pattern = r'\[([^\]]+)\]\(file://|LOCAL_BASE|/([^\)]+)\)'.replace('|LOCAL_BASE|', LOCAL_BASE)
    
    updated = 0
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                if process_file(filepath, pattern):
                    updated += 1
    
    print(f"\n完成! 共更新 {updated} 个文件")

if __name__ == "__main__":
    main()
