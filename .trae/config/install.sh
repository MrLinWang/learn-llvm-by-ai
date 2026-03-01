#!/bin/bash
# LLVM 教程工具一键安装脚本

set -e

echo "=========================================="
echo "LLVM 教程工具安装脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then
    echo "检测到 root 用户，将使用 apt-get 安装"
    PKG_MANAGER="apt-get"
else
    echo "检测到非 root 用户，将使用 sudo apt-get 安装"
    PKG_MANAGER="sudo apt-get"
fi

echo ""
echo "正在安装依赖..."

# 安装 pandoc 和 LaTeX
$PKG_MANAGER update
$PKG_MANAGER install -y pandoc texlive-latex-base texlive-xetex

echo ""
echo "=========================================="
echo "安装完成!"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  生成 PDF: python3 .trae/config/generate_pdf.py"
echo "  转换链接: python3 .trae/config/convert_links.py"
echo ""
