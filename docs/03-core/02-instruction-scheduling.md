# LLVM 指令调度 (Instruction Scheduling) 总结

> 本文档整理自 LLVM 源码分析，介绍编译器后端的指令调度机制

## 1. 指令调度概述

### 1.1 什么是指令调度

指令调度是编译器后端的重要优化步骤，目的是重新排列指令的执行顺序，以：
- **隐藏指令延迟**: 避免因数据依赖导致的流水线停顿
- **提高指令级并行度 (ILP)**: 充分利用处理器的执行单元
- **最大化资源利用率**: 平衡处理器的各种执行单元

### 1.2 调度的时机

在 LLVM 中，指令调度分为两个阶段：

```
┌─────────────────────────────────────────────────────────────┐
│                  指令调度在CodeGen中的位置                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  High-level Optimization                                    │
│         │                                                   │
│         ▼                                                   │
│  SelectionDAG ISel                                          │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         MachineScheduler (发射前调度)                 │   │
│  │         - 寄存器分配之前                              │   │
│  │         - 基于虚拟寄存器                              │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  Register Allocation (寄存器分配)                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │    PostRASchedulerList (发射后调度)                   │   │
│  │    - 寄存器分配之后                                  │   │
│  │    - 基于物理寄存器                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  Code Emission                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 调度核心数据结构

### 2.1 ScheduleDAG - 调度DAG基类

**文件位置**: [📁 llvm/lib/CodeGen/ScheduleDAG.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/ScheduleDAG.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/ScheduleDAG.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/ScheduleDAG.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAG.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAG.h)

`ScheduleDAG` 是所有调度器的基类，核心功能：
- 构建指令依赖图 (DAG)
- 拓扑排序
- 调度序列生成

```cpp
// 核心类定义
class ScheduleDAG {
public:
    // 调度单位（指令）
    SUnit *SU;                    // 调度单元
    
    // 构建调度DAG
    virtual void BuildSchedGraph(AAWrapper *AA);
    
    // 拓扑排序
    void topologicalSort();
    
    // 调度接口
    virtual void Schedule() = 0;
};
```

### 2.2 ScheduleDAGInstrs - 机器指令调度

**文件位置**: [📁 llvm/lib/CodeGen/ScheduleDAGInstrs.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/ScheduleDAGInstrs.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/ScheduleDAGInstrs.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/ScheduleDAGInstrs.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAGInstrs.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAGInstrs.h)

继承自 `ScheduleDAG`，专门用于机器指令（MachineInstr）的调度：

```cpp
class ScheduleDAGInstrs : public ScheduleDAG {
private:
    const MachineFunction *MF;    // 机器函数
    const TargetInstrInfo *TII;   // 目标指令信息
    const TargetRegisterInfo *TRI; // 目标寄存器信息
    
public:
    // 构建机器指令DAG
    void BuildSchedGraph(AAWrapper *AA) override;
    
    // 初始化队列
    void InitQueues(MachineBasicBlock *BB);
    
    // 释放资源
    void ReleasePred(SUnit *SU, bool isPred);
    void ReleaseSucc(SUnit *SU, bool isSucc);
};
```

### 2.3 SUnit - 调度单元

`SUnit` (Scheduling Unit) 代表调度图中的一个节点，可以是一条指令或一个寄存器定义：

```cpp
class SUnit {
public:
    MachineInstr *Inst;           // 对应的机器指令
    unsigned short NumPreds;      // 前驱数量
    unsigned short NumSuccs;      // 后继数量
    
    // 依赖类型
    enum DependenceType {
        Data,                     // 数据依赖（真依赖）
        Anti,                     // 反依赖（写后读）
        Output,                   // 输出依赖（写后写）
        Order                     // 顺序依赖（控制依赖等）
    };
};
```

---

## 3. 依赖类型分析

### 3.1 数据依赖 (Data Dependence)

也称为**真依赖** (True Dependence)，由指令间的数据流动引起：

```cpp
// 示例：a = b + c  依赖于  b 和 c
%v1 = ADD %v2, %v3      ; 指令1
%v4 = ADD %v1, %v5      ; 指令2 依赖指令1的结果
```

### 3.2 反依赖 (Anti-Dependence)

也称为**反依赖** (Read-After-Write)，后读指令依赖前写指令：

```cpp
// 示例：先写后读
store %v1, @x           ; 指令1 写 x
%v2 = load @x           ; 指令2 读 x，不能移到指令1之前
```

### 3.3 输出依赖 (Output Dependence)

**写后写**依赖，两条指令都写同一位置：

```cpp
// 示例
store %v1, @x           ; 指令1 写 x
store %v2, @x           ; 指令2 写 x，不能交换顺序
```

### 3.4 顺序依赖 (Order Dependence)

控制流和其他顺序约束：

```cpp
// 示例：分支指令
cmp %v1, %v2
br_条件 %label
```

---

## 4. 调度器实现

### 4.1 MachineScheduler - 发射前调度

**文件位置**: [📁 llvm/lib/CodeGen/MachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/MachineScheduler.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/MachineScheduler.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/MachineScheduler.h)

`MachineScheduler` 在寄存器分配之前运行，是 LLVM 现代化的调度框架：

```cpp
// Pass 定义
class MachineSchedulerPass : public PassInfoMixin<MachineSchedulerPass> {
    PreservedAnalyses run(MachineFunction &MF, MachineFunctionAnalysisManager &AM);
};

// 遗留 Pass（兼容）
class MachineSchedulerLegacy : public MachineFunctionPass {
    bool runOnMachineFunction(MachineFunction &MF) override;
};
```

#### 4.1.1 ScheduleDAGMI - 机器指令调度器

```cpp
class ScheduleDAGMI : public ScheduleDAGInstrs {
    // 实时调度信息
    std::vector<SUnit*> PendingQueue;    // 待调度队列
    std::vector<SUnit*> AvailableQueue;   // 可用队列
};
```

#### 4.1.2 GenericScheduler - 通用调度器

**默认调度器**，实现多种启发式算法：

```cpp
class GenericScheduler : public GenericSchedulerBase {
public:
    // 调度决策
    SUnit *pickNode(bool &IsTopDown) override;
    
    // 调度策略
    void initialize(ScheduleDAGMI *dag) override;
    
    // 成本计算
    int computeNodeCost(SUnit *SU, bool IsTopDown);
};
```

**调度启发式**:
- **Linearize**: 按程序顺序调度
- **Source**: 优先调度源节点
- **Latency**: 基于延迟调度
- **ILP**: 最大化 ILP
- **RegPressure**: 考虑寄存器压力
- **Cluster**: 聚簇相关指令

### 4.2 PostRASchedulerList - 发射后调度

**文件位置**: [📁 llvm/lib/CodeGen/PostRASchedulerList.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/PostRASchedulerList.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/PostRASchedulerList.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/PostRASchedulerList.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/PostRASchedulerList.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/PostRASchedulerList.h)

在寄存器分配之后进行调度，使用物理寄存器信息：

```cpp
class PostMachineSchedulerPass : public PassInfoMixin<PostMachineSchedulerPass> {
    PreservedAnalyses run(MachineFunction &MF, MachineFunctionAnalysisManager &AM);
};

// 遗留 Pass
class PostMachineSchedulerLegacy : public MachineFunctionPass {
    bool runOnMachineFunction(MachineFunction &MF) override;
};
```

**特点**:
- 使用物理寄存器而非虚拟寄存器
- 更精确的依赖分析
- 可以修复寄存器分配引入的问题

---

## 5. 调度策略

### 5.1 调度器类型

通过 `TargetPassConfig` 或命令行选择：

```bash
# 选择调度器
-misched=<scheduler>           # 发射前调度器
-postmisched=<scheduler>       # 发射后调度器
```

**可用调度器**:

| 调度器 | 描述 | 适用场景 |
|--------|------|---------|
| `source` | 按源码顺序 | 快速编译 |
| `list-ilp` | List scheduling + ILP | 平衡质量与速度 |
| `list-td` | Top-down list scheduling | 通用 |
| `list-burr` | Bottom-up list scheduling | 通用 |
| `fast` | 快速调度 | 快速编译 |
| `latency` | 基于延迟调度 | 延迟敏感 |

### 5.2 调度算法

#### List Scheduling (列表调度)

最常用的调度算法：

```
1. 计算每个节点的最早可能调度时间
2. 维护一个就绪队列（满足所有前驱的节点）
3. 每次从队列中选择一个节点调度
4. 更新后继节点的可调度状态
5. 重复直到所有节点调度完成
```

#### Top-down vs Bottom-up

- **Top-down**: 从入口节点向下调度，适合延迟敏感场景
- **Bottom-up**: 从出口节点向上调度，有利于寄存器分配

---

## 6. 冒险识别 (Hazard Recognition)

### 6.1 ScheduleHazardRecognizer

**文件位置**: [📁 llvm/include/llvm/CodeGen/ScheduleHazardRecognizer.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleHazardRecognizer.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleHazardRecognizer.h)

处理处理器流水线冒险：

```cpp
class ScheduleHazardRecognizer {
public:
    // 检测冒险
    virtual HazardResult getHazardType(SUnit *SU, int Stalls);
    
    // 推进周期
    virtual void AdvanceCycle(bool UpdateCycleLimit = false);
    
    // 发射指令
    virtual void EmitInstruction(SUnit *SU);
};
```

### 6.2 冒险类型

| 冒险类型 | 描述 | 处理方式 |
|---------|------|---------|
| **结构冒险** | 硬件资源冲突 | 等待资源可用 |
| **数据冒险 RAW** | 读后写 | 插入气泡或重新调度 |
| **控制冒险** | 分支预测失败 | 延迟槽填充 |

---

## 7. 高级调度主题

### 7.1 VLIW 调度

**文件位置**: [📁 llvm/lib/CodeGen/VLIWMachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/VLIWMachineScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/VLIWMachineScheduler.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/VLIWMachineScheduler.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/VLIWMachineScheduler.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/VLIWMachineScheduler.h)

针对 VLIW (Very Long Instruction Word) 架构的调度器：

```cpp
class VLIWMachineScheduler : public MachineSchedulerImpl {
    // 包bundle指令
    void packInstruction(SUnit *SU);
    
    // 资源分配
    void ResourceAllocate(SUnit *SU);
};
```

**特点**:
- 将多个指令打包成一个 VLIW 包
- 处理资源约束
- 打包策略优化

### 7.2 模调度 (Modulo Scheduling)

**文件位置**: [📁 llvm/lib/CodeGen/ModuloSchedule.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/ModuloSchedule.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/ModuloSchedule.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/ModuloSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ModuloSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ModuloSchedule.h)

用于软件流水 (Software Pipelining)：

```cpp
class ModuloSchedulePass : public PassInfoMixin<ModuloSchedulePass> {
    // 核心算法
    void computeMII();        // 计算最小启动间隔
    void computeMaxMII();     // 计算最大启动间隔
    void schedule();           // 生成调度
};
```

### 7.3 窗口调度器 (Window Scheduler)

**文件位置**: [📁 llvm/lib/CodeGen/WindowScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/WindowScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/WindowScheduler.cpp)

**头文件**: [📁 llvm/include/llvm/CodeGen/WindowScheduler.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/WindowScheduler.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/WindowScheduler.h)

现代调度器，使用滑动窗口方法：

```cpp
class WindowScheduler {
    // 窗口调度
    void scheduleInWindow(MachineBasicBlock &MBB);
    
    // 资源约束
    void enforceResourceConstraints();
};
```

---

## 8. 调度相关 Pass 配置

### 8.1 CodeGen Pass 顺序

```
MachineIROptimizer
    │
    ├─ MachineScheduler (发射前调度)
    │    └─ RegisterAllocator (寄存器分配)
    │         └─ PostRASchedulerList (发射后调度)
    │
    └─ CodeEmission
```

### 8.2 调度配置选项

```bash
# 启用/禁用调度
-disable-scheduler          # 禁用调度
-enable-misched            # 启用机器调度器

# 调度策略
-misched=ilp              # ILP 调度器
-misched=source           # 源码顺序
-misched=fast             # 快速调度

# 寄存器压力控制
-misched=regpressure      # 寄存器压力感知
```

### 8.3 TargetSchedModel

每个目标架构定义调度模型：

```cpp
// 定义处理器的调度特性
TargetSchedModel ProcModel;
ProcModel.init(&STI);

// 获取指令延迟
unsigned Latency = ProcModel.getLatency(Iti);

// 获取发射宽度
unsigned IssueWidth = ProcModel.getIssueWidth();
```

---

## 9. 调试与分析

### 9.1 查看调度信息

```bash
# 查看调度决策
opt -debug-only=misched input.ll -o output.ll

# 打印 ScheduleDAG
opt -view-sched-dags input.ll

# 查看寄存器压力
opt -debug-only=regpressure input.ll
```

### 9.2 调度统计

```
===-------------------------------------------------------------------------===
                      Instruction Scheduling Info
===-------------------------------------------------------------------------===
Total Instructions selected:     1234
Total micro-ops:                 2345
Total Resource Cycles:          5678
Total Execution Cycles:         9012
ILP (Instructions / Cycles):    0.137
===-------------------------------------------------------------------------===
```

---

## 10. 调度器扩展

### 10.1 自定义调度策略

```cpp
class MyCustomScheduler : public MachineSchedStrategy {
public:
    void initialize(ScheduleDAGMI *dag) override {
        // 初始化
    }
    
    SUnit *pickNode(bool &IsTopDown) override {
        // 自定义调度逻辑
        return nullptr;
    }
    
    void scheduleTree(SUnit *SU) override {
        // 调度树
    }
};
```

### 10.2 注册调度器

```cpp
static RegisterScheduler myCustomScheduler(
    "my-scheduler", "My Custom Scheduler",
    createMyCustomScheduler
);
```

---

## 11. 总结

### 11.1 调度流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    指令调度流程                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MachineFunction                                            │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  BuildSchedGraph                                     │   │
│  │  - 分析指令依赖                                       │   │
│  │  - 构建 SUnit DAG                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Hazard Recognition                                  │   │
│  │  - 检测流水线冒险                                     │   │
│  │  - 避免资源冲突                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  List Scheduling (或其他算法)                        │   │
│  │  - 选择就绪指令                                       │   │
│  │  - 更新依赖状态                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│       │                                                     │
│       ▼                                                     │
│  ScheduleComplete                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 核心类关系

```
ScheduleDAG (抽象基类)
    │
    ├── ScheduleDAGInstrs (机器指令DAG)
    │       │
    │       └── ScheduleDAGMI (带调度信息)
    │               │
    │               ├── GenericScheduler (通用调度)
    │               └── [自定义调度器]
    │
    ├── VLIWMachineScheduler (VLIW调度)
    │
    ├── ModuloSchedule (模调度)
    │
    └── WindowScheduler (窗口调度)
```

### 11.3 关键文件速查

| 功能 | 文件路径 |
|------|---------|
| 调度基类 | [📁 ScheduleDAG.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAG.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAG.h) |
| 机器指令调度 | [📁 ScheduleDAGInstrs.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAGInstrs.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleDAGInstrs.h) |
| MachineScheduler | [📁 MachineScheduler.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/MachineScheduler.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/MachineScheduler.h) |
| 发射后调度 | [📁 PostRASchedulerList.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/PostRASchedulerList.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/PostRASchedulerList.h) |
| 冒险识别 | [📁 ScheduleHazardRecognizer.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ScheduleHazardRecognizer.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ScheduleHazardRecognizer.h) |
| VLIW调度 | [📁 VLIWMachineScheduler.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/VLIWMachineScheduler.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/VLIWMachineScheduler.h) |
| 模调度 | [📁 ModuloSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/ModuloSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/ModuloSchedule.h) |

---

## 参考资料

- [LLVM Language Reference](https://llvm.org/docs/LangRef.html)
- [Writing an LLVM Pass](https://llvm.org/docs/WritingAnLLVMPass.html)
- [LLVM Machine Scheduler](https://llvm.org/docs/MachineLangRef.html)
- [Target Scheduler Model](https://llvm.org/docs/TargetInstrInfo.html)
