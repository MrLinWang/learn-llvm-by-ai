# 源码跳转配置指南

> 本文件为项目配置文档，不属于教程内容

## 链接格式说明

为了同时支持**本地 VS Code 学习**和**GitHub 网页浏览**，推荐使用双链接格式：

```markdown
[📁 源码](file:///root/learn-llvm-by-ai/llvm-project/xxx.cpp) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/xxx.cpp)
```

**效果展示**：
- 📁 源码 - 在 VS Code 中点击直接跳转本地文件
- 🌐 GitHub - 在浏览器中点击跳转到 GitHub 仓库

---

## 快速开始

### 方法一：手动编写双链接

在编写文档时，直接使用双链接格式：

```markdown
## InstCombine Pass

[📁 源码](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp#L1-L50) · [🌐 GitHub](https://github.com/your-org/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp#L1-L50)
```

### 方法二：使用脚本批量转换

如果已有单链接文档，可以使用脚本批量转换：

```bash
# 先配置脚本中的 GitHub 仓库信息
# 编辑 .trae/config/convert_links.py 修改:
#   GITHUB_ORG = "your-org"
#   GITHUB_REPO = "learn-llvm-by-ai"

# 运行转换脚本
python3 .trae/config/convert_links.py
```

---

## 链接格式规则

### 本地链接格式
```
file:///root/learn-llvm-by-ai/llvm-project/{相对路径}#L{行号}
```

### GitHub 链接格式
```
https://github.com/{org}/{repo}/blob/main/llvm-project/{相对路径}#L{行号}
```

### 行号格式
- 单行: `#L100`
- 多行: `#L100-L150`

---

## 当前使用说明

### 在本地 VS Code 中
- 点击 **📁 源码** 链接可以直接跳转到本地对应文件和行号

### 在 GitHub 网页上
- 点击 **🌐 GitHub** 链接可以直接跳转到 GitHub 仓库对应文件和行号

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
| LICM | `llvm/lib/Transforms/Scalar/LICM.cpp` |
| LoopUnroll | `llvm/lib/Transforms/Utils/LoopUnroll.cpp` |
| LoopVectorize | `llvm/lib/Transforms/Vectorize/LoopVectorize.cpp` |
| SLPVectorizer | `llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp` |

### 调度相关文件

| 功能 | 源码路径 |
|------|---------|
| MachineScheduler | `llvm/lib/CodeGen/MachineScheduler.cpp` |
| PostRA Scheduler | `llvm/lib/CodeGen/PostRASchedulerList.cpp` |
| 调度模型定义 | `llvm/include/llvm/Target/TargetSchedule.td` |
| XiangShan调度 | `llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td` |

---

## 注意事项

1. **GitHub 仓库配置**: 使用脚本前请先修改 `convert_links.py` 中的 `GITHUB_ORG` 和 `GITHUB_REPO` 变量
2. **分支名称**: 默认使用 `main` 分支，如使用 `master` 请修改 `GITHUB_BRANCH` 变量
3. **路径一致性**: 脚本会自动处理本地路径和 GitHub 路径的转换
