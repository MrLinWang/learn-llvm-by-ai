# LLVM 调度模型 (*.td) 与指令调度的实现原理

> 深入解析 TableGen 调度模型如何影响指令调度

## 1. 整体流程概述

调度模型从定义到实际影响指令调度，经历了以下完整流程：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        调度模型完整流程图                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  阶段一：*.td 文件定义                                            │   │
│   │  (TargetSchedule.td + 目标特定 .td)                              │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              ▼                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  阶段二：TableGen 生成 C++ 代码                                   │   │
│   │  (生成 .inc 文件，包含 MCSchedModel 等数据结构)                   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              ▼                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  阶段三：运行时初始化                                             │   │
│   │  (TargetSchedModel::init() 加载模型)                            │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              │                                            │
│                              ▼                                            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  阶段四：调度器使用                                               │   │
│   │  (MachineScheduler/PostRA Scheduler 查询模型)                   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 调度模型的 TD 定义

### 2.1 核心类层次

调度模型的核心定义在 [📁 llvm/include/llvm/Target/TargetSchedule.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/Target/TargetSchedule.td)：

```tablegen
// 调度机器模型 - 定义处理器基本属性
class SchedMachineModel {
  int IssueWidth = -1;           // 每周期最大微指令数
  int MicroOpBufferSize = -1;    // 微指令缓冲大小
  int LoadLatency = -1;          // 加载延迟周期数
  int HighLatency = -1;          // 高延迟操作延迟
  int MispredictPenalty = -1;    // 分支预测失败惩罚
  bit PostRAScheduler = false;   // 是否启用发射后调度
  // ...
}

// 处理器资源种类
class ProcResourceKind;

// 处理器资源单元 (如 ALU、端口等)
class ProcResource<int num> : ProcResourceKind;

// 调度读写类型 (与指令operand关联)
class SchedReadWrite;
class SchedWrite : SchedReadWrite;   // 定义操作 (写寄存器)
class SchedRead : SchedReadWrite;    // 使用操作 (读寄存器)

// 资源定义
class WriteRes<SchedWrite write, list<ProcResourceKind> resources>;
class ReadAdvance<SchedRead read, int cycles>;
```

### 2.2 处理器资源定义示例

以 X86 为例 ([📁 X86ScheduleBdVer2.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Target/X86/X86ScheduleBdVer2.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Target/X86/X86ScheduleBdVer2.td))：

```tablegen
// 定义执行端口 (Processor Execution Units)
def PdEX0  : ProcResource<1>;  // ALU, Integer Pipe0
def PdEX1  : ProcResource<1>;  // ALU, Integer Pipe1
def PdAGU01: ProcResource<2>;  // AGU, Integer Pipe[23]
def PdFPU0 : ProcResource<1>;  // Vector/FPU Pipe0
def PdFPU1 : ProcResource<1>;  // Vector/FPU Pipe1
def PdFPU2 : ProcResource<1>;  // Vector/FPU Pipe2
def PdFPU3 : ProcResource<1>;  // Vector/FPU Pipe3
def PdLoad : ProcResource<2>;  // 加载单元
def PdStore: ProcResource<1>;  // 存储单元
def PdDiv  : ProcResource<1>;  // 整数除法
def PdMul  : ProcResource<1>;  // 整数乘法
def PdBranch: ProcResource<1>; // 分支单元
def PdFPFMA: ProcResource<2>; // FMA 单元
```

### 2.3 指令调度属性定义

```tablegen
// 定义 SchedWrite 类型 (对应指令的"写"操作)
def WriteALU : SchedWrite;        // ALU 写操作
def WriteLoad : SchedWrite;        // 加载写操作
def WriteStore: SchedWrite;        // 存储写操作

// 定义 SchedRead 类型 (对应指令的"读"操作)
def ReadALU  : SchedRead;         // ALU 读操作
def ReadLoad : SchedRead;         // 加载读操作

// 将 SchedWrite 映射到处理器资源和延迟
def : WriteRes<WriteALU, [PdEX0, PdEX1]> {
  let Latency = 1;               // 延迟 1 周期
  let NumMicroOps = 1;          // 1 个微指令
}

def : WriteRes<WriteLoad, [PdLoad]> {
  let Latency = 4;               // 加载延迟 4 周期
  let NumMicroOps = 1;
}

def : WriteRes<WriteMul, [PdMul]> {
  let Latency = 3;               // 乘法延迟 3 周期
  let NumMicroOps = 1;
}

// 定义读取前置 (减少有效延迟)
def : ReadAdvance<ReadLoad, -1, [WriteLoad]>;  // 加载后1周期可用
```

### 2.4 指令调度类映射

```tablegen
// 定义指令的调度属性
class : Instruction {
  let SchedRW = [WriteALU, ReadALU];  // ALU 指令
}

// 或者使用 InstRW 直接映射
def : InstRW<[WriteLoad, ReadALU], (instrs LOAD)>;
def : InstRW<[WriteStore, ReadALU], (instrs STORE)>;
```

---

## 3. TableGen 代码生成

### 3.1 生成的数据结构

TableGen 会生成以下关键数据结构：

```cpp
// 生成的 MCSchedModel 结构 (简化版)
struct MCSchedModel {
  unsigned ProcessorID;
  unsigned IssueWidth;           // 每周期发射指令数
  unsigned MicroOpBufferSize;    // 微指令缓冲大小
  unsigned LoadLatency;          // 加载延迟
  // ... 其他属性
  
  // 处理器资源表
  unsigned NumProcResourceKinds;
  const MCProcResourceDesc *ProcResourceTable;
  
  // 调度类表
  unsigned NumSchedClass;
  const MCSchedClassDesc *SchedClassTable;
  
  // ...
};

// 处理器资源描述
struct MCProcResourceDesc {
  const char *Name;
  unsigned NumUnits;         // 资源单元数
  int BufferSize;            // 缓冲大小
};

// 调度类描述
struct MCSchedClassDesc {
  const char *Name;
  unsigned WriteProcResIdx;  // 写资源索引
  unsigned NumWriteRes;      // 写资源数
  unsigned Latency;          // 基础延迟
  // ...
};
```

### 3.2 生成过程

```bash
# TableGen 生成调度模型代码
llvm-tblgen -gen-subtarget -I /path/to/include X86Schedule.td -o X86GenSubtarget.inc
```

生成的代码会被包含到目标后端的 Subtarget 实现中：

```cpp
// X86Subtarget.cpp 中
#include "X86GenSubtarget.inc"

void X86Subtarget::initSchedModel() const {
  // 从 TableGen 生成的表初始化调度模型
  MCSchedModel = &X86SchedModel;
}
```

---

## 4. 运行时模型加载

### 4.1 TargetSchedModel 初始化

在 [📁 llvm/include/llvm/CodeGen/TargetSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h) 中：

```cpp
class TargetSchedModel {
  MCSchedModel SchedModel;           // TableGen 生成的模型
  InstrItineraryData InstrItins;    // 指令 itinerary
  const TargetSubtargetInfo *STI = nullptr;
  const TargetInstrInfo *TII = nullptr;
  
public:
  // 初始化调度模型
  LLVM_ABI void init(const TargetSubtargetInfo *TSInfo,
                     bool EnableSModel = true, bool EnableSItins = true);
};
```

### 4.2 初始化过程

```cpp
// TargetSchedule.cpp
void TargetSchedModel::init(const TargetSubtargetInfo *TSInfo,
                            bool EnableSModel, bool EnableSItins) {
  STI = TSInfo;
  TII = STI->getInstrInfo();
  
  // 获取 TableGen 生成的调度模型
  SchedModel = *STI->getMCSchedModel();
  
  // 初始化指令 itinerary
  InstrItins = STI->getInstrItineraryData();
  
  // 计算资源因子 (用于归一化)
  computeResourceFactor();
}
```

---

## 5. 调度器使用调度模型

### 5.1 MachineScheduler 中的使用

在 [📁 llvm/lib/CodeGen/MachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) 中，调度器在多个关键点查询调度模型：

#### 5.1.1 获取指令延迟

```cpp
// MachineScheduler.cpp - 计算指令延迟
void ScheduleDAGMILive::initSUnits() {
  // 获取指令的调度类
  const MCSchedClassDesc *SC = SchedModel.resolveSchedClass(MI);
  
  // 计算延迟
  int Latency = SchedModel.computeInstrLatency(SC);
  
  // 为每个后继设置延迟边
  for (SUnit::const_succ_iterator I = SU->Succs.begin(); 
       I != SU->Succs.end(); ++I) {
    SUnit *SuccSU = I->getSUnit();
    if (SuccSU->TopReadyCycle < SU->TopReadyCycle + I->getLatency())
      SuccSU->TopReadyCycle = SU->TopReadyCycle + I->getLatency();
  }
}
```

#### 5.1.2 获取处理器资源

```cpp
// MachineScheduler.cpp - 获取指令使用的处理器资源
void ResourceAwareScheduler::init(ScheduleDAGMI *DAG, 
                                   const TargetSchedModel *SchedModel) {
  // 遍历指令的写资源
  for (TargetSchedModel::ProcResIter 
       PI = SchedModel->getWriteProcResBegin(SC),
       PE = SchedModel->getWriteProcResEnd(SC); 
       PI != PE; ++PI) {
    
    unsigned PIdx = PI->ProcResourceIdx;
    unsigned Cycles = PI->ProcResourceCycles;
    
    // 记录资源使用
    ResourceCount[PIdx] += Cycles;
  }
}
```

#### 5.1.3 获取微指令数量

```cpp
// MachineScheduler.cpp - 获取微指令数
unsigned TargetSchedModel::getNumMicroOps(const MachineInstr *MI,
                                         const MCSchedClassDesc *SC) const {
  if (!SC)
    SC = resolveSchedClass(MI);
  
  // 从调度模型获取微指令数
  return SC->NumMicroOps;
}
```

#### 5.1.4 资源冲突检测

```cpp
// MachineScheduler.cpp - 检查资源冲突
bool GenericScheduler::pickNode() {
  // 检查当前周期的资源使用
  for (auto &Resource : Resources) {
    unsigned ResourceID = Resource.first;
    unsigned Used = Resource.second;
    unsigned Capacity = SchedModel.getProcResource(ResourceID)->NumUnits;
    
    if (Used >= Capacity) {
      // 资源已被占满，需要等待
      return false;
    }
  }
  return true;
}
```

### 5.2 调度决策中的使用

```cpp
// GenericScheduler - 调度决策中使用延迟信息
SUnit *GenericScheduler::pickNode(bool &IsTopDown) {
  // 遍历可用节点
  for (SUnit *SU : Available) {
    // 计算调度成本
    int Cost = computeNodeCost(SU, IsTopDown);
    
    // 成本最低的优先调度
    if (Cost < BestCost) {
      BestCost = Cost;
      BestSU = SU;
    }
  }
  return BestSU;
}

// 计算节点成本
int GenericScheduler::computeNodeCost(SUnit *SU, bool IsTopDown) {
  const MCSchedClassDesc *SC = SchedModel.resolveSchedClass(SU->getInstr());
  
  // 延迟成本
  unsigned Latency = SchedModel.computeInstrLatency(SC);
  
  // 资源成本
  unsigned ResourceCost = 0;
  for (auto &Res : getResourcesUsed(SU)) {
    ResourceCost += Res.second;
  }
  
  return Latency + ResourceCost * ResourcePressureFactor;
}
```

---

## 6. 调度模型的实际效果示例

### 6.1 处理器资源约束示例

假设一个简单的处理器有 2 个 ALU 端口：

```tablegen
def ALU0 : ProcResource<1>;
def ALU1 : ProcResource<1>;
def MulUnit : ProcResource<1>;
def LoadUnit : ProcResource<2>;
```

对于以下代码：

```c
a = b + c;      // ADD - 需要 ALU，延迟 1
d = e + f;      // ADD - 需要 ALU，延迟 1
g = h * i;      // MUL - 需要 MulUnit，延迟 3
```

调度器会：
1. **ADD1** 使用 ALU0，在周期 1 发射
2. **ADD2** 可以并行使用 ALU1，在周期 1 发射（无冲突）
3. **MUL** 需要 MulUnit，必须等待周期 2

### 6.2 延迟约束示例

```c
// 原始代码
a = b + c;        // 延迟 1
d = a * e;        // 延迟 3，依赖 a
```

**无调度**：
```
周期 1: ADD b, c -> a
周期 2: (空转 - 等待 a)
周期 3: (空转 - 等待 a)
周期 4: MUL a, e -> d
总周期: 4
```

**优化调度**（利用延迟间隙）：
```
周期 1: ADD b, c -> a
周期 2: MUL a, e -> d   (ADD 已完成，可以开始)
总周期: 2
```

---

## 7. 实际案例：RISC-V XiangShan-NanHu 调度模型

> 本节以 RISC-V 架构的 **XiangShan-NanHu**（香山）处理器为例，详细展示调度模型的定义和应用

### 7.1 处理器简介

**XiangShan-NanHu**（香山）是由中科院计算技术研究所开发的高性能 RISC-V 开源处理器。

- **源码位置**: [📁 llvm/lib/Target/RISCV/RISCVProcessors.td#L700](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Target/RISCV/RISCVProcessors.td#L700) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Target/RISCV/RISCVProcessors.td#L700)
- **调度模型定义**: [📁 llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/Target/RISCV/RISCVSchedXiangShanNanHu.td)

### 7.2 处理器参数定义

```tablegen
def XiangShanNanHuModel : SchedMachineModel {
  let MicroOpBufferSize = 256;        // 微指令缓冲大小 (ROB/寄存器重命名缓冲)
  let LoopMicroOpBufferSize = 48;     // 循环缓冲大小 (指令队列)
  let IssueWidth = 6;                 // 每周期发射6条指令
  let LoadLatency = 4;                // 加载延迟4周期
  let MispredictPenalty = 11;         // 分支预测失败惩罚11周期
  let CompleteModel = 0;               // 非完整模型(部分指令未定义)
}
```

**参数解读**：

| 参数 | 值 | 含义 |
|------|-----|------|
| IssueWidth | 6 | 每周期最多发射6条指令（6-way） |
| MicroOpBufferSize | 256 | 寄存器重命名缓冲/ROB大小 |
| LoopMicroOpBufferSize | 48 | 循环指令缓冲大小 |
| LoadLatency | 4 | L1缓存加载延迟4周期 |
| MispredictPenalty | 11 | 分支预测失败代价11周期 |

### 7.3 处理器执行单元定义

XiangShan-NanHu 采用分布式预留 station，分为多个独立的执行单元：

```tablegen
//  Reservation Stations: 32-entry or 16-entry grouped
let BufferSize = 16 in {
  // 整数单元
  def XS2ALU : ProcResource<4>;    // 4个ALU端口
  def XS2MDU : ProcResource<2>;    // 2个乘法/除法单元
  def XS2MISC : ProcResource<1>;    // 1个杂项单元(Jump/CSR)
  
  // 浮点单元
  def XS2FMAC : ProcResource<4>;    // 4个浮点MAC单元
  def XS2FMISC : ProcResource<2>;   // 2个浮点杂项单元
  
  // 访存单元
  def XS2LD : ProcResource<2>;      // 2个加载单元
  def XS2ST : ProcResource<2>;       // 2个存储单元
}
```

**执行单元拓扑**：

```
                    ┌─────────────────────────────────────┐
                    │         Issue / Decode (6-way)      │
                    └─────────────────────────────────────┘
                                      │
         ┌──────────────┬──────────────┼──────────────┬──────────────┐
         │              │              │              │              │
    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
    │XS2ALU(4)│   │XS2MDU(2)│   │XS2MISC(1)│   │XS2FMAC(4)│   │XS2LD(2) │
    │   ALU   │   │ Mul/Div │   │  Jmp/CSR │   │  FMA/FP  │   │  Load   │
    └─────────┘   └─────────┘   └──────────┘   └──────────┘   └──────────┘
                                      │
                                ┌────▼────┐
                                │XS2ST(2) │
                                │  Store  │
                                └─────────┘
```

### 7.4 指令延迟定义

#### 7.4.1 整数运算

```tablegen
// Integer arithmetic and logic (延迟1周期)
let Latency = 1 in {
  def : WriteRes<WriteIALU, [XS2ALU]>;      // 通用ALU
  def : WriteRes<WriteIALU32, [XS2ALU]>;    // 32位ALU
  def : WriteRes<WriteShiftImm, [XS2ALU]>;  // 立即数移位
  def : WriteRes<WriteShiftReg, [XS2ALU]>;  // 寄存器移位
}
```

#### 7.4.2 整数乘法

```tablegen
// Integer multiplication (延迟3周期)
let Latency = 3 in {
  def : WriteRes<WriteIMul, [XS2MDU]>;      // 64位乘法
  def : WriteRes<WriteIMul32, [XS2MDU]>;    // 32位乘法
}
```

#### 7.4.3 整数除法

```tablegen
// Integer division (SRT16算法, 延迟20周期)
// 特殊: 需要保留资源20周期
let Latency = 20, ReleaseAtCycles = [20] in {
  def : WriteRes<WriteIDiv32, [XS2MDU]>;   // 32位除法
  def : WriteRes<WriteIDiv, [XS2MDU]>;      // 64位除法
  def : WriteRes<WriteIRem32, [XS2MDU]>;     // 32位取模
  def : WriteRes<WriteIRem, [XS2MDU]>;      // 64位取模
}
```

#### 7.4.4 浮点运算

```tablegen
// 浮点加减/比较 (延迟3周期)
let Latency = 3 in {
  def : WriteRes<WriteFAdd32, [XS2FMAC]>;     // 32位加法
  def : WriteRes<WriteFAdd64, [XS2FMAC]>;      // 64位加法
  def : WriteRes<WriteFMinMax32, [XS2FMAC]>;  // 32位比较
  def : WriteRes<WriteFCmp32, [XS2FMAC]>;     // 32位浮点比较
}

// 浮点乘法 (延迟3周期)
let Latency = 3 in {
  def : WriteRes<WriteFMul32, [XS2FMAC]>;     // 32位乘法
  def : WriteRes<WriteFMul64, [XS2FMAC]>;     // 64位乘法
}

// FMA (融合乘加) (延迟5周期)
let Latency = 5 in {
  def : WriteRes<WriteFMA32, [XS2FMAC]>;      // 32位FMA
  def : WriteRes<WriteFMA64, [XS2FMAC]>;      // 64位FMA
}

// 浮点除法/平方根 (更长延迟)
def : WriteRes<WriteFDiv32, [XS2FMISC]> { let Latency = 11; }
def : WriteRes<WriteFDiv64, [XS2FMISC]> { let Latency = 18; }
def : WriteRes<WriteFSqrt32, [XS2FMISC]> { let Latency = 17; }
def : WriteRes<WriteFSqrt64, [XS2FMISC]> { let Latency = 31; }
```

#### 7.4.5 访存操作

```tablegen
// 存储 (无延迟，返回执行单元)
def : WriteRes<WriteSTB, [XS2ST]>;
def : WriteRes<WriteSTH, [XS2ST]>;
def : WriteRes<WriteSTW, [XS2ST]>;
def : WriteRes<WriteSTD, [XS2ST]>;

// 加载 (延迟5周期)
let Latency = 5 in {
  def : WriteRes<WriteLDB, [XS2LD]>;   // 字节加载
  def : WriteRes<WriteLDH, [XS2LD]>;   // 半字加载
  def : WriteRes<WriteLDW, [XS2LD]>;   // 字加载
  def : WriteRes<WriteLDD, [XS2LD]>;   // 双字加载
  def : WriteRes<WriteFLD32, [XS2LD]>; // 浮点加载
  def : WriteRes<WriteFLD64, [XS2LD]>; // 双精度浮点加载
}
```

### 7.5 延迟表总结

| 指令类型 | 延迟周期 | 执行单元 |
|---------|---------|---------|
| Integer ALU | 1 | XS2ALU |
| Integer Mul | 3 | XS2MDU |
| Integer Div/Rem | 20 | XS2MDU |
| Load | 5 | XS2LD |
| Store | 0 | XS2ST |
| FP Add/Sub | 3 | XS2FMAC |
| FP Mul | 3 | XS2FMAC |
| FP FMA | 5 | XS2FMAC |
| FP Div | 11/18 | XS2FMISC |
| FP Sqrt | 17/31 | XS2FMISC |

### 7.6 流水线绕过 (Bypass)

XiangShan 支持 **流水线绕过 (Bypass)**，使后续指令可以提前使用前一条指令的结果，而不必等待写入寄存器堆：

```tablegen
// 加载到ALU的bypass: 加载完成后1周期即可使用
class XS2LoadToALUBypass<SchedRead read>
    : ReadAdvance<read, 1, [WriteLDB, WriteLDH, WriteLDW, WriteLDD, ...]>;

// 应用到各个ALU读取操作
def : XS2LoadToALUBypass<ReadIALU>;       // 通用ALU
def : XS2LoadToALUBypass<ReadShiftImm>;   // 立即数移位
def : XS2LoadToALUBypass<ReadRotateReg>; // 寄存器旋转
// ... 更多

// FMA 链式计算的bypass (2周期cascade延迟)
def : ReadAdvance<ReadFMA32Addend, 2>;    // FMA链式计算
def : ReadAdvance<ReadFMA64Addend, 2>;
```

**Bypass 效果示例**：

```c
// 原始代码
a = b + c;        // ADD: 延迟1周期
d = a * e;        // MUL: 依赖a，需要等ADD完成

// 无Bypass: 需要等a写入寄存器才能开始乘法
周期1: ADD b,c -> a
周期2: (等待)
周期3: (等待)
周期4: MUL a,e -> d

// 有Bypass: 乘法可以提前使用ADD的结果
周期1: ADD b,c -> a
周期2: MUL a,e -> d    // 通过bypass提前获得a的值
```

### 7.7 处理器注册

处理器模型通过 `RISCVProcessorModel` 注册到系统中：

```tablegen
// 在 RISCVProcessors.td 中
def XIANGSHAN_NANHU : RISCVProcessorModel<"xiangshan-nanhu",
                                          XiangShanNanHuModel,
                                          [Feature64Bit,
                                           FeatureStdExtI,
                                           FeatureStdExtM,
                                           FeatureStdExtA,
                                           FeatureStdExtF,
                                           FeatureStdExtD,
                                           // ... 更多扩展
                                          ],
                                          [TuneNoDefaultUnroll,
                                           TuneZExtHFusion,
                                           TuneZExtWFusion,
                                           TuneShiftedZExtWFusion]>;
```

### 7.8 调度模型对编译的影响

基于 XiangShan-NanHu 的调度模型，编译器会做出以下优化决策：

1. **指令发射顺序**
   - 优先调度无依赖的指令填充6个发射槽
   - 整数ALU指令(延迟1)可以紧凑排列
   - 乘除法延迟较长，会尝试调度独立指令隐藏延迟

2. **循环展开**
   - 由于 IssueWidth=6，循环展开因子通常为6或12
   - 避免在循环中连续调度延迟超过5的指令

3. **寄存器分配**
   - 256个微指令缓冲足够大多数场景
   - 但对于长依赖链仍需注意寄存器压力

4. **向量化**
   - 4个浮点单元适合SIMD操作
   - FMA延迟5周期，需要合理调度隐藏延迟

---

## 8. 关键源码文件

### 7.1 TD 定义文件

| 文件 | 作用 |
|------|------|
| [📁 TargetSchedule.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) | 调度模型核心类定义 |
| [📁 TargetItinerary.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Target/TargetItinerary.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/Target/TargetItinerary.td) | 指令 itinerary 定义 |
| X86Schedule*.td | X86 各处理器型号调度定义 |

### 7.2 C++ 运行时文件

| 文件 | 作用 |
|------|------|
| [📁 TargetSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h) | TargetSchedModel 类 |
| [📁 MCSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/MC/MCSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/MC/MCSchedule.h) | MCSchedModel 定义 |
| [📁 MachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) | 调度器实现 |
| [📁 TargetSchedule.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/TargetSchedule.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/TargetSchedule.cpp) | 调度模型运行时 |

---

## 8. 调试与分析

### 8.1 查看调度信息

```bash
# 查看指令的调度信息
llvm-mca -mtriple=x86_64-unknown-unknown -mcpu=skylake \
  -view-all -all-views input.s

# 查看调度统计
opt -stats -debug-only=misched input.ll
```

### 8.2 查看调度模型

```bash
# 查看生成的调度模型
llvm-tblgen -dump-json X86.td | grep -A 20 "SchedMachineModel"
```

---

## 9. 总结

### 9.1 核心流程

```
┌─────────────────────────────────────────────────────────────────┐
│  TD 定义 (TargetSchedule.td)                                    │
│  ├── ProcResourceKind / ProcResource (执行单元)                  │
│  ├── SchedWrite / SchedRead (指令读写)                          │
│  └── WriteRes / ReadAdvance (资源映射和延迟)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TableGen 生成                                                   │
│  └── MCSchedModel / MCProcResourceDesc / MCSchedClassDesc       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TargetSchedModel::init()                                       │
│  └── 加载模型到运行时                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  调度器使用                                                       │
│  ├── getLatency() - 获取指令延迟                                  │
│  ├── getProcResource() - 获取资源使用                             │
│  ├── getNumMicroOps() - 获取微指令数                             │
│  └── mustBeginGroup/mustEndGroup - 资源冲突检测                   │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 调度模型影响调度的关键方式

| 方式 | 说明 |
|------|------|
| **延迟计算** | 根据 WriteRes 的 Latency 设置指令间依赖边的延迟 |
| **资源限制** | 根据 ProcResource 的 NumUnits 限制并行度 |
| **微指令数** | IssueWidth 限制每周期发射的微指令总数 |
| **发射组** | mustBeginGroup/mustEndGroup 控制发射组边界 |
| **读取前置** | ReadAdvance 减少有效延迟，支持流水线 bypass |

---

## 参考资料

- [📁 TargetSchedule.td](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/Target/TargetSchedule.td) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/Target/TargetSchedule.td)
- [📁 TargetSchedule.h](file:///root/learn-llvm-by-ai/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/include/llvm/CodeGen/TargetSchedule.h)
- [📁 MachineScheduler.cpp](file:///root/learn-llvm-by-ai/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp) · [🌐 GitHub](https://github.com/MrLinWang/learn-llvm-by-ai/blob/main/llvm-project/llvm/lib/CodeGen/MachineScheduler.cpp)
- [LLVM TableGen Documentation](https://llvm.org/docs/TableGen/)
