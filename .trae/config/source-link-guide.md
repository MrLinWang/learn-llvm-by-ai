# 源码跳转配置指南

> 本文件为项目配置文档，不属于教程内容

## 快速开始

### 方法一：使用 VS Code 工作区（推荐）

1. 打开 VS Code
2. 选择 `文件` → `打开工作区 from 文件...`
3. 选择 `learn-llvm.code-workspace`

这将同时打开教程项目和 llvm-project 源码。

### 方法二：手动配置源码跳转

在 VS Code 中添加源码文件夹：

1. `文件` → `将文件夹添加到工作区`
2. 选择 `llvm-project` 文件夹

---

## 源码链接格式

在教程文档中使用以下格式创建可点击的源码链接：

### 格式说明

```markdown
[源文件名](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp#L100-L120)
```

**链接结构**:
- `file:///root/learn-llvm-by-ai/llvm-project/` - 源码根目录
- `llvm/lib/Transforms/...` - 相对于 llvm-project 的路径
- `#L100-L120` - 跳转到指定行号

---

## 常用源码路径速查

### Pass 框架核心文件

| 功能 | 源码路径 |
|------|---------|
| Pass 管理器 | `llvm/include/llvm/IR/PassManager.h` |
| PassBuilder | `llvm/include/llvm/Passes/PassBuilder.h` |

### 核心优化 Pass 源码

| Pass | 源码路径 |
|------|---------|
| InstCombine | `llvm/lib/Transforms/InstCombine/InstructionCombining.cpp` |
| GVN | `llvm/lib/Transforms/Scalar/GVN.cpp` |
| DCE | `llvm/lib/Transforms/Scalar/DCE.cpp` |
| DSE | `llvm/lib/Transforms/Scalar/DeadStoreElimination.cpp` |
| SimplifyCFG | `llvm/lib/Transforms/Utils/SimplifyCFG.cpp` |
| Reassociate | `llvm/lib/Transforms/Scalar/Reassociate.cpp` |
| LICM | `llvm/lib/Transforms/Scalar/LICM.cpp` |
| LoopUnroll | `llvm/lib/Transforms/Utils/LoopUnroll.cpp` |
| LoopVectorize | `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp` |
| SLPVectorizer | `llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp` |

---

## 使用示例

在 markdown 文档中添加链接：

```markdown
## InstCombine Pass

InstCombine 是 LLVM 最基本的优化 Pass，位于 [InstructionCombining.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp#L1-L50)。

核心逻辑在 `visitAdd` 函数中：
```cpp
// 源码分析
Value *visitAdd(BinaryOperator &I) {
  // 优化逻辑...
}
```
```

---

## 推荐的源码阅读技巧

1. **从入口点开始**: 找到 Pass 的 `run` 方法
2. **搜索关键函数**: 如 `visitXXX`（访问者模式）
3. **使用符号跳转**: `Ctrl+点击` 跳转，`Alt+←` 返回
4. **大纲视图**: 左侧边栏查看文件结构

---

## 扩展推荐

安装以下 VS Code 扩展提升体验：

- **vscode-llvm**: LLVM 语法高亮和工具集成
- **C/C++**: IntelliSense 和代码导航
- **Markdown All in One**: Markdown 预览和导航
