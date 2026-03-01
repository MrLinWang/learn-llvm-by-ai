# LLVM 源码学习教程

> 通过 AI 辅助学习 LLVM 编译器源代码的中文教程

## 项目简介

本项目旨在为中文开发者提供一个系统化的 LLVM 源代码学习资源。通过结合 llvm-project 官方源码和文档，生成循序渐进的学习教程，帮助大家深入理解 LLVM 编译器的架构与实现。

## 内容结构

```
learn-llvm-by-ai/
├── docs/                       # 教程文档
│   └── 03-core/                # 核心组件
│       ├── 01-pass-framework.md      # Pass 框架与优化
│       ├── 02-instruction-scheduling.md  # 指令调度
│       └── 03-sched-model-td.md     # 调度模型 (*.td)
├── llvm-project/               # LLVM 源码（子模块）
├── .trae/config/               # 项目配置
│   ├── source-link-guide.md    # 源码跳转配置指南
│   └── convert_links.py        # 链接转换脚本
├── DESIGN.md                  # 项目设计文档
└── README.md                  # 本文件
```

## 教程内容

### 核心组件

#### 1. Pass 框架与优化 Pass
- Pass 管理器架构（PassBuilder、PassManager）
- 核心优化 Pass 详解
  - InstCombine（指令组合）
  - GVN（全局值编号）
  - DCE/DSE（死代码/存储消除）
  - SimplifyCFG（控制流简化）
- 循环优化（LoopUnroll、LICM、LoopVectorize）
- 向量化优化（SLPVectorizer）
- Pipeline 执行流程

#### 2. 指令调度 (Instruction Scheduling)
- 调度器架构（MachineScheduler、PostRAScheduler）
- 调度算法（List Scheduling、Top-down/Bottom-up）
- 依赖类型分析（数据依赖，反依赖、输出依赖）
- 冒险识别（Hazard Recognition）
- VLIW 调度与模调度

#### 3. 调度模型 (*.td)
- TableGen 调度模型定义
- 处理器资源（ProcResource）
- 指令延迟（Latency）与资源映射
- **实际案例：RISC-V XiangShan-NanHu（香山·南湖）调度模型**
  - 处理器参数配置
  - 执行单元定义
  - 指令延迟表
  - 流水线绕过 (Bypass)

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
2. 学习指令调度 [docs/03-core/02-instruction-scheduling.md](docs/03-core/02-instruction-scheduling.md)
3. 深入理解调度模型 [docs/03-core/03-sched-model-td.md](docs/03-core/03-sched-model-td.md)
4. 点击文档中的源码链接，跳转到 LLVM 源码对应位置
5. 结合源码深入理解

## 源码跳转

教程文档中的源码链接同时支持**本地 VS Code** 和 **GitHub 网页**两种访问方式：

```markdown
[📁 源码](file:///root/.../InstructionCombining.cpp) · [🌐 GitHub](https://github.com/.../InstructionCombining.cpp)
```

- 📁 源码 - 本地 VS Code 点击跳转
- 🌐 GitHub - 浏览器点击跳转

详见 [.trae/config/source-link-guide.md](.trae/config/source-link-guide.md)

### 核心源码链接

| 文档 | 关键源码 |
|------|---------|
| Pass 框架 | [📁 InstCombine.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp) |
| Pass 框架 | [📁 GVN.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/GVN.cpp) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Transforms/Scalar/GVN.cpp) |
| 指令调度 | [📁 MachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) |
| 调度模型 | [📁 TargetSchedule.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) |
| XiangShan | [📁 RISCVSchedXiangShanNanHu.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td) |

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
- [LLVM Machine Scheduler](https://llvm.org/docs/MachineLangRef.html)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

本项目内容遵循 MIT 许可证。LLVM 项目本身遵循 Apache 2.0 许可证。
