# Teable CLI 管道操作设计

## 概述
支持管道操作，让用户可以组合多个命令，实现复杂的数据处理工作流。

## 设计目标
- `show` 命令可以输出记录ID列表
- `update` 命令可以从标准输入接收记录ID
- 支持链式操作：`t show -w 状态=待处理 | t update 状态=处理中`
- 保持向后兼容性

## 实现方案

### 1. 输出格式选项
为 `show` 命令添加 `--output` 或 `-o` 选项：
- `table` (默认): 表格格式
- `ids`: 只输出记录ID，每行一个
- `json`: JSON格式
- `csv`: CSV格式

### 2. 管道输入支持
为 `update` 命令添加 `--from-stdin` 选项：
- 从标准输入读取记录ID列表
- 支持批量更新这些记录

### 3. 使用示例

```bash
# 基本管道操作
t show -w 状态=待处理 -o ids | t update --from-stdin 状态=处理中

# 复杂查询 + 更新
t show -w "创建时间>2024-01-01" "优先级=高" -o ids | t update --from-stdin 状态=紧急 处理人=张三

# 多步管道
t show -w 状态=新建 -o ids | head -10 | t update --from-stdin 状态=已分配

# 保存到文件再处理
t show -w 状态=待审核 -o ids > pending_ids.txt
cat pending_ids.txt | t update --from-stdin 状态=已审核
```

### 4. 技术实现

#### show命令修改
- 添加 `--output` 参数
- 支持多种输出格式
- 保持现有功能不变

#### update命令修改
- 添加 `--from-stdin` 参数
- 从标准输入读取记录ID
- 批量更新这些记录

#### 主CLI修改
- 检测管道输入
- 处理标准输入输出
- 保持交互模式兼容性

### 5. 错误处理
- 无效的记录ID格式
- 网络错误处理
- 部分更新失败的处理

### 6. 性能考虑
- 批量处理记录ID
- 合理分批更新
- 进度显示