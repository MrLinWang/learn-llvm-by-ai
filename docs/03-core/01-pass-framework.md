# LLVM 中端 Pass 框架与核心优化 Pass 总结

> 本文档整理自 LLVM 源码分析，旨在帮助理解 LLVM 编译器的优化 Pass 框架

## 1. Pass 框架概述

### 1.1 Pass 管理器架构

LLVM 的 Pass 框架是编译器后端优化的核心基础设施。主要包含以下组件：

**核心头文件**:
- [llvm/include/llvm/IR/PassManager.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/IR/PassManager.h) - Pass 管理器接口
- [llvm/include/llvm/Passes/PassBuilder.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Passes/PassBuilder.h) - Pass 构建器
- [llvm/include/llvm/IR/LegacyPassManager.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/IR/LegacyPassManager.h) - 旧版 Pass 管理器

```
┌─────────────────────────────────────────────────────────────────┐
│                     PassBuilder                                 │
│  - 构建优化 Pipeline                                             │
│  - 注册 Pass 依赖关系                                            │
│  - 管理 Pass 执行顺序                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PassManager                                    │
│  - ModulePassManager (整个模块)                                  │
│  - FunctionPassManager (函数级别)                                │
│  - LoopPassManager (循环级别)                                    │
│  - CGSCCPassManager (调用图 SCC 级别)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Analysis Managers                              │
│  - FunctionAnalysisManager                                      │
│  - LoopAnalysisManager                                          │
│  - ModuleAnalysisManager                                        │
│  - CGSCCAnalysisManager                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Pass 的分类

| 级别 | Pass 类型 | 作用范围 | 示例 |
|------|----------|---------|------|
| **Module** | ModulePass | 整个 LLVM Module | 函数内联、链接时优化 |
| **CGSCC** | CallGraphSCCPass | 调用图的强连通分量 | 函数类型推断 |
| **Function** | FunctionPass | 单个函数 | 指令组合、GVN |
| **Loop** | LoopPass | 单个循环 | 循环展开、循环向量化 |
| **BasicBlock** | BasicBlockPass | 单个基本块 | 极少使用 |

### 1.3 Pass 的作用

1. **Analysis Pass（分析 Pass）**
   - 收集程序信息但不修改 IR
   - 为其他 Pass 提供分析结果缓存
   - 示例：DominatorTree（支配树）、LoopInfo（循环信息）

2. **Transformation Pass（转换 Pass）**
   - 优化和转换 IR
   - 可能破坏原始分析信息
   - 示例：InstCombine、GVN

3. **Utility Pass（工具 Pass）**
   - 提供辅助功能
   - 示例：PrintFunctionPass（打印函数）

---

## 2. 核心优化 Pass 详解

### 2.1 指令组合 (InstCombine)

**文件位置**: [llvm/lib/Transforms/InstCombine/InstructionCombining.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/InstCombine/InstructionCombining.cpp)

**头文件**: [llvm/include/llvm/Transforms/InstCombine/InstCombine.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/InstCombine/InstCombine.h)

**Pass 类**:
- `InstCombinePass` (新 Pass 管理器)
- `InstructionCombiningPass` (兼容旧版)

**功能描述**:
InstCombine 是 LLVM 最基本也是最重要的优化 Pass 之一，通过反复应用各种代数简化和指令替换规则来简化代码。

**核心优化示例**:

```llvm
; 优化前
%a = add i32 %x, 0      →  %a = %x                  (加0消除)
%b = mul i32 %x, 1      →  %b = %x                  (乘1消除)
%c = and i32 %x, -1     →  %c = %x                  (与-1消除)
%d = shl i32 %x, 0      →  %d = %x                  (移位0消除)
%e = or i32 %x, 0       →  %e = %x                  (或0消除)

; 复杂优化
%a = add i32 %x, %x     →  %a = shl i32 %x, 1      (x+x → 2*x)
%a = mul i32 %x, 4     →  %a = shl i32 %x, 2      (x*4 → x<<2)
%a = sub i32 0, %x     →  %a = neg i32 %x         (0-x → -x)

; 重新关联
%a = add i32 (add i32 %x, %y), %z  
                    →  add i32 %x, (add i32 %y, %z)
```

**在 Pipeline 中的位置**: 处于函数简化 Pipeline 的核心位置，通常会多次运行以达到不动点。

---

### 2.2 活跃变量分析 (GVN - Global Value Numbering)

**文件位置**: [llvm/lib/Transforms/Scalar/GVN.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/GVN.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/GVN.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/GVN.h)

**Pass 类**: `GVNPass`

**功能描述**:
GVN 通过为表达式分配相同的"值编号"，识别出冗余计算的 Pass。当发现相同的值已经计算过，则用已有值替代。

**核心优化示例**:

```llvm
; 优化前
entry:
  %a = add i32 %x, %y
  br %cond, %bb1, %bb2

bb1:
  %b = add i32 %x, %y    ; 与 entry 中的 %a 等价
  %c = mul i32 %b, 2
  br %bb3

bb2:
  %d = add i32 %x, %y    ; 与 entry 中的 %a 等价
  %e = sub i32 %d, 1
  br %bb3

bb3:
  %f = phi i32 [%c, %bb1], [%e, %bb2]

; GVN 优化后 - 消除 bb1 和 bb2 中的重复加法
entry:
  %a = add i32 %x, %y
  br %cond, %bb1, %bb2

bb1:
  %c = mul i32 %a, 2     ; 直接使用 %a
  br %bb3

bb2:
  %e = sub i32 %a, 1     ; 直接使用 %a
  br %bb3

bb3:
  %f = phi i32 [%c, %bb1], [%e, %bb2]
```

**GVN 的关键概念**:
- **值编号 (Value Number)**: 对每个表达式分配唯一编号
- **可用表达式 (Available Expressions)**: 沿控制流可用的表达式
- **冗余消除 (Redundancy Elimination)**: 消除重复计算

---

### 2.3 死代码消除 (DCE - Dead Code Elimination)

**文件位置**: [llvm/lib/Transforms/Scalar/DCE.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/DCE.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/DCE.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/DCE.h)

**Pass 类**: `DCEPass`

**功能描述**:
DCE 删除计算结果不被使用的指令，以及不可达的基本块。

```llvm
; 优化前
entry:
  %a = add i32 %x, %y     ; 结果未使用，可删除
  %b = mul i32 %x, 2
  br label %exit

exit:
  ret i32 %b

; DCE 优化后
entry:
  %b = mul i32 %x, 2
  br label %exit

exit:
  ret i32 %b
```

---

### 2.4 死存储消除 (DSE - Dead Store Elimination)

**文件位置**: [llvm/lib/Transforms/Scalar/DeadStoreElimination.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/DeadStoreElimination.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/DeadStoreElimination.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/DeadStoreElimination.h)

**Pass 类**: `DSEPass`

**功能描述**:
DSE 删除冗余的内存写入操作。当后续的存储操作覆盖了前面的值时，前面的存储可以删除。

```llvm
; 优化前
store i32 10, ptr %a
store i32 20, ptr %a    ; 覆盖了前面的值
%val = load i32, ptr %a

; DSE 优化后
store i32 20, ptr %a
%val = load i32, ptr %a
```

---

### 2.5 简化控制流 (SimplifyCFG)

**文件位置**: [llvm/lib/Transforms/Utils/SimplifyCFG.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Utils/SimplifyCFG.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/SimplifyCFG.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/SimplifyCFG.h)

**Pass 类**: `SimplifyCFGPass`

**功能描述**:
简化控制流图，包括：
- 合并基本块
- 消除不可达基本块
- 简化条件跳转
- 合并返回语句

```llvm
; 优化前
entry:
  br i1 %cond, %then, %else

then:
  br %exit

else:
  br %exit

exit:
  ret i32 0

; SimplifyCFG 优化后
entry:
  ret i32 0
```

---

### 2.6 重新关联 (Reassociate)

**文件位置**: [llvm/lib/Transforms/Scalar/Reassociate.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/Reassociate.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/Reassociate.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/Reassociate.h)

**Pass 类**: `ReassociatePass`

**功能描述**:
重新组织表达式的结合顺序以暴露更多的优化机会，如常量折叠和公共子表达式消除。

```llvm
; 优化前
%a = add i32 %x, 10
%b = add i32 %a, 5    ; (x + 10) + 5

; Reassociate 优化后
%b = add i32 %x, 15   ; x + (10 + 5) = x + 15
```

---

## 3. 循环优化 Pass

### 3.1 循环展开 (LoopUnroll)

**文件位置**: [llvm/lib/Transforms/Utils/LoopUnroll.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Utils/LoopUnroll.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/LoopUnrollPass.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/LoopUnrollPass.h)
- `llvm/lib/Transforms/Utils/LoopUnrollRuntime.cpp`

**Pass 类**: `LoopUnrollPass`

**功能描述**:
将循环体复制多次执行，减少循环控制开销。

```llvm
; 展开前
for (i = 0; i < 4; i++)
  a[i] = b[i] + c[i];

; 展开后 (2x展开)
a[0] = b[0] + c[0];
a[1] = b[1] + c[1];
i = 2;
if (i < 4) goto loop_start;
```

**展开类型**:
- **完全展开**: 循环次数固定且较小
- **部分展开**: 按固定因子展开
- **运行时展开**: 展开次数在运行时确定

---

### 3.2 循环代码移动 (LICM - Loop Invariant Code Motion)

**文件位置**: [llvm/lib/Transforms/Scalar/LICM.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/LICM.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/LICM.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/LICM.h)

**Pass 类**: `LICMPass`

**功能描述**:
将循环内不变的代码移到循环外部，减少重复计算。

```llvm
; LICM 优化前
for (i = 0; i < n; i++) {
  x = a + b;        // 循环不变量
  arr[i] = x + i;
}

; LICM 优化后
x = a + b;          // 移到循环外
for (i = 0; i < n; i++) {
  arr[i] = x + i;
}
```

---

### 3.3 循环向量化 (LoopVectorize)

**文件位置**: [llvm/lib/Transforms/Vectorize/LoopVectorize.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Vectorize/LoopVectorize.cpp)

**头文件**: [llvm/include/llvm/Transforms/Vectorize/LoopVectorize.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Vectorize/LoopVectorize.h)

**Pass 类**: `LoopVectorizePass`

**功能描述**:
将标量循环转换为向量操作，利用 SIMD 指令并行执行。

```llvm
; 向量化前
for (i = 0; i < 1024; i++)
  a[i] = b[i] + c[i];

; 向量化后 (假设向量宽度为4)
for (i = 0; i < 1024; i += 4) {
  vec4 vb = vec4_load(&b[i]);
  vec4 vc = vec4_load(&c[i]);
  vec4 va = vb + vc;
  vec4_store(&a[i], va);
}
```

---

### 3.4 循环简化 (LoopSimplify)

**文件位置**: [llvm/lib/Transforms/Utils/LoopSimplify.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Utils/LoopSimplify.cpp)

**Pass 类**: `LoopSimplify`

**功能描述**:
规范化循环结构，为其他循环优化做准备：
- 确保循环有唯一入口
- 简化循环退出条件
- 维护 LCSSA（Loop-Closed SSA）形式

---

### 3.5 归纳变量简化 (IndVarSimplify)

**文件位置**: [llvm/lib/Transforms/Scalar/IndVarSimplify.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/IndVarSimplify.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/IndVarSimplify.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/IndVarSimplify.h)

**Pass 类**: `IndVarSimplifyPass`

**功能描述**:
简化和扩展循环归纳变量，简化循环终止条件。

```llvm
; 优化前
for (i = 0; i < n; i++)
  arr[i] = i * 2;

; 优化后 - 消除乘法和归纳变量
ptr = arr;
for (i = 0; i < n; i++) {
  *ptr = i << 1;
  ptr++;
}
```

---

### 3.6 循环合并 (LoopFuse)

**文件位置**: [llvm/lib/Transforms/Scalar/LoopFuse.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/LoopFuse.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/LoopFuse.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/LoopFuse.h)

**Pass 类**: `LoopFusePass`

**功能描述**:
合并连续的相似循环，减少循环开销并提高并行性。

```llvm
; 合并前
for (i = 0; i < n; i++)
  a[i] = b[i] + 1;
for (i = 0; i < n; i++)
  c[i] = a[i] * 2;

; 合并后
for (i = 0; i < n; i++) {
  a[i] = b[i] + 1;
  c[i] = a[i] * 2;
}
```

---

## 4. 向量化优化 Pass

### 4.1 SLP 向量化 (SLPVectorizer)

**文件位置**: [llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Vectorize/SLPVectorizer.cpp)

**头文件**: [llvm/include/llvm/Transforms/Vectorize/SLPVectorizer.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Vectorize/SLPVectorizer.h)

**Pass 类**: `SLPVectorizerPass`

**功能描述**:
将独立的标量操作组合成向量操作，特别适合处理基本块内的数据并行模式。

```llvm
; SLP 向量化前
a[0] = b[0] + c[0];
a[1] = b[1] + c[1];
a[2] = b[2] + c[2];
a[3] = b[3] + c[3];

; SLP 向量化后
va = vec4_load(&b);
vc = vec4_load(&c);
va = va + vc;
vec4_store(&a, va);
```

---

### 4.2 循环非独立检查 (LoopPredication)

**文件位置**: `llvm/lib/Transforms/Scalar/LoopPredication.cpp`

**Pass 类**: `LoopPredicationPass`

**功能描述**:
将循环边界检查转换为前置条件检查，使向量化更有效。

---

### 4.3 加载/存储向量化 (LoadStoreVectorizer)

**文件位置**: `llvm/lib/Transforms/Vectorize/LoadStoreVectorizer.cpp`

**Pass 类**: `LoadStoreVectorizerPass`

**功能描述**:
合并连续的内存访问为向量加载/存储操作。

---

## 5. 数据流优化 Pass

### 5.1 早期公共子表达式消除 (EarlyCSE)

**文件位置**: [llvm/lib/Transforms/Scalar/EarlyCSE.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/EarlyCSE.cpp)

**Pass 类**: `EarlyCSELegacyCommonPass`

**功能描述**:
在基本块内进行公共子表达式消除，效率高但范围有限。

---

### 5.2 条件传播 (CCP - Conditional Constant Propagation)

**文件位置**: [llvm/lib/Transforms/Scalar/SCCP.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/SCCP.cpp)

**Pass 类**: 包含在 SCCP (Sparse Conditional Constant Propagation)

**功能描述**:
结合常量传播和条件分支分析，推断更多常量值。

```llvm
; CCP 优化前
if (sizeof(int) == 4)     // 编译时已知为 true
  x = 1;
else
  x = 2;

; CCP 优化后
x = 1;
```

---

### 5.3 相关值传播 (CVP - Correlated Value Propagation)

**文件位置**: [llvm/lib/Transforms/Scalar/CorrelatedValuePropagation.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/CorrelatedValuePropagation.cpp)

**Pass 类**: `CorrelatedValuePropagationPass`

**功能描述**:
基于条件分支的相关信息进行更精确的值传播。

---

### 5.4 常量提升 (ConstantHoisting)

**文件位置**: [llvm/lib/Transforms/Scalar/ConstantHoisting.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/ConstantHoisting.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/ConstantHoisting.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/ConstantHoisting.h)

**Pass 类**: `ConstantHoistingPass`

**功能描述**:
将重复的常量操作提升到统一位置，减少代码体积。

```llvm
; 优化前
bb1:
  %a = add i32 %x, 12345
  br %cond

bb2:
  %b = add i32 %x, 12345
  br %next

; 提升后
entry:
  %common = add i32 %x, 12345  ; 提升常量计算
  br %cond

bb1:
  br %next

bb2:
  br %next

next:
  %result = phi i32 [%common, %bb1], [%common, %bb2]
```

---

## 6. 其他重要优化 Pass

### 6.1 函数内联 (Inliner)

**文件位置**: [llvm/lib/Transforms/IPO/ModuleInliner.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/IPO/ModuleInliner.cpp)

**Pass 类**: `ModuleInlinerPass`

**功能描述**:
将函数调用替换为函数体，增加内联机会以进行更多优化。

---

### 6.2 归纳变量替换 (IVUsers)

**文件位置**: `llvm/lib/Transforms/Utils/IndVars.cpp`

**功能描述**:
用更简单的表达式替换复杂的归纳变量表达式。

---

### 6.3 内存优化 (SROA - Scalar Replacement of Aggregates)

**文件位置**: [llvm/lib/Transforms/Scalar/SROA.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/SROA.cpp)

**Pass 类**: `SROALegacyPass`

**功能描述**:
将聚合体（struct/array）分解为独立的标量成员，提高优化效果。

---

### 6.4 激进指令组合 (AggressiveInstCombine)

**文件位置**: [llvm/lib/Transforms/AggressiveInstCombine/AggressiveInstCombine.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/AggressiveInstCombine/AggressiveInstCombine.cpp)

**Pass 类**: `AggressiveInstCombinePass`

**功能描述**:
在 InstCombine 之后运行，执行更激进的优化转换。

---

### 6.5 Jump Threading

**文件位置**: [llvm/lib/Transforms/Scalar/JumpThreading.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Transforms/Scalar/JumpThreading.cpp)

**头文件**: [llvm/include/llvm/Transforms/Scalar/JumpThreading.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Transforms/Scalar/JumpThreading.h)

**Pass 类**: `JumpThreadingPass`

**功能描述**:
通过分析条件分支，跳转到已知结果的后继。

```llvm
; 优化前
entry:
  %cmp = icmp eq i32 %x, 0
  br i1 %cmp, %then, %else

then:
  br %exit

else:
  br %exit

; Jump Threading 后
entry:
  %cmp = icmp eq i32 %x, 0
  br %exit      ; 直接跳到 exit
```

---

## 7. 优化级别与 Pipeline

### 7.1 标准优化级别

| 级别 | 描述 | 主要 Pass |
|------|------|----------|
| **O0** | 无优化 | 仅生成代码 |
| **O1** | 基本优化 | 快速优化，减少编译时间 |
| **O2** | 标准优化 | 平衡编译时间和性能 |
| **O3** | 激进优化 | 最高性能优化 |
| **Os** | 大小优化 | 优先代码大小 |
| **Oz** | 极致大小优化 | 最小化代码大小 |

### 7.2 标准优化 Pipeline (O2)

```
Module Pipeline:
├── buildModuleSimplificationPipeline
│   ├── PassBuilder::buildInlinerPipeline
│   │   └── 模块内联 (ModuleInlinerPass)
│   └── 函数简化 (Function Simplification)
│       ├── SimplifyCFG
│       ├── EarlyCSE
│       ├── LoopRotate
│       └── buildFunctionSimplificationPipeline
│           ├── InstCombine
│           ├── SimplifyCFG
│           ├── SCCP
│           └── ... 更多
│
└── buildModuleOptimizationPipeline
    ├── GVN (值编号)
    ├── MemCpyOptimizer
    ├── SLPVectorizer (向量化)
    ├── LoopVectorize (循环向量化)
    ├── InstCombine
    └── ... 更多
```

### 7.3 函数简化 Pipeline 详情

```
buildFunctionSimplificationPipeline:
├── SimplifyCFGPass
├── EarlyCSE (成本模型引导)
├── LoopRotatePass
├── LICMPass (循环不变量代码移动)
├── LoopInstSimplifyPass (循环指令简化)
├── IndVarSimplifyPass (归纳变量简化)
├── LoopUnrollPass (循环展开)
├── SimplifyCFGPass
└── InstCombinePass (多次迭代)
```

---

## 8. Pass 依赖关系

### 8.1 核心依赖图

```
                    ┌──────────────┐
                    │  DominatorTree│
                    │   Analysis   │
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  InstCombine  │  │     GVN       │  │    LICM       │
│ (Transformation)│  │(Transformation)│  │(Transformation)│
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     DCE      │
                    │(Transformation)│
                    └──────────────┘
```

---

## 9. 常用 Pass 使用方法

### 9.1 通过 opt 工具使用

```bash
# 运行特定 Pass
opt -pass-name=instcombine input.ll -o output.ll

# 运行 O2 Pipeline
opt -O2 input.ll -o output.ll

# 查看 Pass 执行顺序
opt -O2 -debug-pass-manager input.ll 2>&1 | less
```

### 9.2 编程方式使用

```cpp
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/StandardPasses.h"

using namespace llvm;

void buildOptimizationPipeline(ModulePassManager &MPM) {
  PassBuilder PB;
  
  // 注册标准分析
  PB.registerModuleAnalyses(MAM);
  PB.registerFunctionAnalyses(FAM);
  
  // 添加优化 Pipeline
  MPM.addPB(PB.buildPerModuleDefaultPipeline(OptimizationLevel::O2));
}
```

---

## 10. 总结

### 10.1 Pass 执行顺序原则

1. **Analysis before Transformation**: 先分析再转换
2. **Preserve analyses after modifications**: 转换后需要使分析失效
3. **Iterate to fixpoint**: 多次迭代直到稳定
4. **Coarse-grained before fine-grained**: 粗粒度优化在前

### 10.2 关键优化 Pass 总结表

| 类别 | Pass | 功能 | 重要性 |
|------|------|------|-------|
| **基础** | InstCombine | 指令组合简化 | ⭐⭐⭐⭐⭐ |
| **基础** | SimplifyCFG | 控制流简化 | ⭐⭐⭐⭐⭐ |
| **数据流** | GVN | 公共子表达式消除 | ⭐⭐⭐⭐ |
| **数据流** | DCE | 死代码消除 | ⭐⭐⭐⭐ |
| **数据流** | DSE | 死存储消除 | ⭐⭐⭐ |
| **循环** | LICM | 循环不变代码移动 | ⭐⭐⭐⭐ |
| **循环** | LoopUnroll | 循环展开 | ⭐⭐⭐⭐ |
| **循环** | LoopVectorize | 循环向量化 | ⭐⭐⭐⭐ |
| **向量化** | SLPVectorizer | SLP 向量化 | ⭐⭐⭐⭐ |
| **其他** | Reassociate | 重新关联表达式 | ⭐⭐⭐ |

---

## 参考资料

- [LLVM Language Reference](https://llvm.org/docs/LangRef.html)
- [Writing an LLVM Pass](https://llvm.org/docs/WritingAnLLVMPass.html)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)
- [Pass Manager Deep Dive](https://llvm.org/docs/NewPassManager.html)
