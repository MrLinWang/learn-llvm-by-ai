#!/usr/bin/env python3
"""
将教程文档合并并转换为 PDF
依赖: pandoc, LaTeX (xelatex)
安装: apt install pandoc texlive-xelatex
"""

import os
import re
import subprocess
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
docs_dir = os.path.join(project_root, "docs")
output_dir = os.path.join(project_root, "output")
os.makedirs(output_dir, exist_ok=True)
output_pdf = os.path.join(output_dir, "learn-llvm-tutorial.pdf")

def find_markdown_files():
    md_files = []
    for root, dirs, files in os.walk(docs_dir):
        for file in sorted(files):
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    return md_files

def convert_link_for_pdf(text):
    text = re.sub(r'\[📁 ([^\]]+)\]\([^)]+\) · \[🌐 [^\]]+\]\([^)]+\)', r'**\1**', text)
    text = re.sub(r'\[📁 ([^\]]+)\]\([^)]+\)', r'**\1**', text)
    return text

def process_markdown(content):
    content = convert_link_for_pdf(content)
    content = re.sub(r'\.md\)', r'.pdf)', content)
    return content

def merge_documents(md_files):
    merged = []
    title = "# LLVM 学习教程\n\n"
    merged.append(title)
    
    for md_file in md_files:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = process_markdown(content)
        
        relative_path = os.path.relpath(md_file, docs_dir)
        section_title = f"\n\n---\n\n# {relative_path}\n\n"
        merged.append(section_title + content)
    
    return ''.join(merged)

def check_dependencies():
    try:
        subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def generate_pdf(merged_content):
    temp_md = "/tmp/learn-llvm-tutorial.md"
    
    with open(temp_md, 'w', encoding='utf-8') as f:
        f.write(merged_content)
    
    cmd = [
        'pandoc',
        temp_md,
        '-o', output_pdf,
        '--pdf-engine=xelatex',
        '-V', 'geometry:margin=1in',
        '--toc',
        '--number-sections'
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ PDF 生成成功: {output_pdf}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ PDF 生成失败: {e.stderr}")
        return False

def main():
    print("=" * 50)
    print("LLVM 教程 PDF 生成器")
    print("=" * 50)
    
    if not check_dependencies():
        print("\n错误: 未安装 pandoc")
        print("请运行: apt install pandoc texlive-xelatex")
        sys.exit(1)
    
    md_files = find_markdown_files()
    if not md_files:
        print(f"错误: 未找到 markdown 文件 in {docs_dir}")
        sys.exit(1)
    
    print(f"\n找到 {len(md_files)} 个文档文件:")
    for f in md_files:
        print(f"  - {os.path.relpath(f, docs_dir)}")
    
    merged = merge_documents(md_files)
    
    print("\n正在生成 PDF...")
    if generate_pdf(merged):
        print("\n✓ 完成!")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
