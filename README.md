# LLVM 源码学习教程

> 通过 AI 辅助学习 LLVM 编译器源代码的中文教程

## 项目简介

本项目旨在为中文开发者提供一个系统化的 LLVM 源代码学习资源。通过结合 llvm-project 官方源码和文档，生成循序渐进的学习教程，帮助大家深入理解 LLVM 编译器的架构与实现。

## 内容结构

```
learn-llvm-by-ai/
├── docs/                       # 教程文档
│   └── 03-core/                # 核心组件
│       └── 01-pass-framework.md   # Pass 框架详解
├── llvm-project/               # LLVM 源码（子模块）
├── .trae/config/               # 项目配置
├── DESIGN.md                  # 项目设计文档
└── README.md                  # 本文件
```

## 教程内容

### 核心组件

- **Pass 框架与优化 Pass**
  - Pass 管理器架构
  - 核心优化 Pass 详解（InstCombine、GVN、DCE、DSE 等）
  - 循环优化（LoopUnroll、LICM、LoopVectorize）
  - 向量化优化（SLPVectorizer）
  - Pipeline 执行流程

### 即将推出

- LLVM IR（中间表示）
- Clang 前端技术
- 后端代码生成
- MLIR 多级中间表示

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/learn-llvm-by-ai.git
cd learn-llvm-by-ai
git submodule update --init --recursive
```

### 2. 配置 IDE

推荐使用 VS Code 打开工作区：

```bash
code learn-llvm.code-workspace
```

这将同时打开教程文档和 llvm-project 源码，方便一键跳转到源码阅读。

### 3. 开始学习

从 Pass 框架开始：

1. 阅读 [docs/03-core/01-pass-framework.md](docs/03-core/01-pass-framework.md)
2. 点击文档中的源码链接，跳转到 LLVM 源码对应位置
3. 结合源码深入理解

## 源码跳转

教程文档中的代码都带有可点击的链接，可以直接跳转到 llvm-project 源码：

- [InstructionCombining.cpp](llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp) - InstCombine 实现
- [GVN.cpp](llvm-project/llvm/lib/Transforms/Scalar/GVN.cpp) - GVN 实现
- [LoopVectorize.cpp](llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp) - 循环向量化

## 核心优化 Pass 速查

| Pass | 功能 | 重要性 |
|------|------|-------|
| InstCombine | 指令组合简化 | ⭐⭐⭐⭐⭐ |
| SimplifyCFG | 控制流图简化 | ⭐⭐⭐⭐⭐ |
| GVN | 公共子表达式消除 | ⭐⭐⭐⭐ |
| LICM | 循环不变代码移动 | ⭐⭐⭐⭐ |
| LoopUnroll | 循环展开 | ⭐⭐⭐⭐ |
| LoopVectorize | 循环向量化 | ⭐⭐⭐⭐ |
| SLPVectorizer | SLP 向量化 | ⭐⭐⭐⭐ |

## 参考资源

- [LLVM 官方文档](https://llvm.org/docs/)
- [LLVM Language Reference](https://llvm.org/docs/LangRef.html)
- [Writing an LLVM Pass](https://llvm.org/docs/WritingAnLLVMPass.html)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目内容遵循 MIT 许可证。LLVM 项目本身遵循 Apache 2.0 许可证。
