# 脚本工具使用指南

本项目提供了两个实用的脚本管理工具，帮助你更好地管理和使用项目中的脚本。

## 工具列表

### 1. script_manager.py - 脚本管理工具

用于分析、查看和搜索项目中的所有脚本。

#### 功能特性

- 📋 **列出所有脚本** - 按类别筛选
- 🔍 **搜索脚本** - 按关键词搜索
- 📖 **查看脚本详情** - 显示脚本描述、命令、用法等
- 📊 **生成报告** - 生成项目脚本分析报告

#### 使用方法

```bash
# 列出所有脚本
python3 script_manager.py list

# 列出测试脚本
python3 script_manager.py list --category test

# 查看脚本详细信息
python3 script_manager.py info insert_20_orders.sh

# 搜索脚本（按关键词）
python3 script_manager.py search --keyword pipe

# 生成完整报告
python3 script_manager.py report
```

#### 示例输出

```bash
$ python3 script_manager.py list --category test

找到 16 个脚本:

  test_chain_pipe.sh              - 测试链式管道操作：show | insert | update | show
  test_customer_update.sh         - 使用客户表测试 update 管道功能
  test_insert_pipe.sh             - 测试 show | insert 管道功能
  test_pipe_comprehensive.sh      - 综合测试管道功能
  ...
```

---

### 2. batch_script_runner.py - 批量脚本执行工具

用于批量执行多个脚本，支持错误处理和报告生成。

#### 功能特性

- 🚀 **批量执行** - 一次执行多个脚本
- ⏸️ **错误控制** - 可选择遇到错误时停止或继续
- ⏱️ **延迟控制** - 设置脚本之间的延迟时间
- 📝 **执行报告** - 生成详细的执行报告（JSON格式）
- 🧪 **模拟执行** - 支持dry-run模式

#### 使用方法

```bash
# 批量执行脚本
python3 batch_script_runner.py script1.sh script2.py script3.sh

# 遇到错误即停止
python3 batch_script_runner.py script1.sh script2.sh --stop-on-error

# 设置延迟时间（秒）
python3 batch_script_runner.py script1.sh script2.sh --delay 1.0

# 模拟执行（不实际运行）
python3 batch_script_runner.py script1.sh script2.sh --dry-run

# 保存执行报告
python3 batch_script_runner.py script1.sh script2.sh --save-report
```

#### 示例输出

```bash
$ python3 batch_script_runner.py test_pipe_demo.sh test_insert_pipe.sh

============================================================
批量执行脚本
============================================================
总脚本数: 2
停止条件: 继续执行
延迟间隔: 0.5秒
============================================================

[1/2] 执行: test_pipe_demo.sh
  路径: tests/test_pipe_demo.sh
  ✅ 成功 (耗时: 2.34秒)

[2/2] 执行: test_insert_pipe.sh
  路径: tests/test_insert_pipe.sh
  ✅ 成功 (耗时: 1.87秒)

============================================================
执行完成
============================================================
总脚本数: 2
成功: 2
失败: 0
总耗时: 4.71秒
============================================================
```

---

## 实际应用场景

### 场景1: 快速了解项目脚本

```bash
# 生成项目脚本报告
python3 script_manager.py report > scripts_report.txt

# 查看报告
cat scripts_report.txt
```

### 场景2: 批量运行测试脚本

```bash
# 查找所有测试脚本
python3 script_manager.py search --keyword test

# 批量执行测试脚本（模拟）
python3 batch_script_runner.py \
  test_pipe_demo.sh \
  test_insert_pipe.sh \
  test_customer_update.sh \
  --dry-run

# 实际执行
python3 batch_script_runner.py \
  test_pipe_demo.sh \
  test_insert_pipe.sh \
  test_customer_update.sh \
  --save-report
```

### 场景3: 查找特定功能的脚本

```bash
# 查找管道相关的脚本
python3 script_manager.py search --keyword pipe

# 查看脚本详情
python3 script_manager.py info test_pipe_comprehensive.sh
```

### 场景4: 创建脚本执行计划

```bash
# 1. 先查看所有脚本
python3 script_manager.py list

# 2. 选择要执行的脚本，创建执行计划
python3 batch_script_runner.py \
  insert_20_orders.sh \
  test_customer_update.sh \
  test_join_query.sh \
  --delay 1.0 \
  --save-report
```

---

## 项目脚本分类

根据脚本功能，可以大致分为以下几类：

### 测试脚本 (tests/)
- `test_*.sh` - 各种功能测试脚本
- `test_*.py` - Python测试脚本

### 数据生成脚本
- `insert_20_orders.sh` - 批量插入订单数据
- `create_test_data.py` - 创建测试数据
- `create_large_dataset.py` - 创建大数据集
- `create_more_test_data.py` - 创建更多测试数据

### 工具脚本
- `script_manager.py` - 脚本管理工具（本工具）
- `batch_script_runner.py` - 批量执行工具（本工具）

---

## 注意事项

1. **脚本执行权限**: 确保脚本有执行权限
   ```bash
   chmod +x *.sh
   ```

2. **依赖检查**: 某些脚本可能需要先配置Teable连接
   ```bash
   t config --token YOUR_TOKEN --base YOUR_BASE_ID
   ```

3. **执行环境**: 确保在正确的目录下执行脚本
   ```bash
   cd /workspace
   ```

4. **错误处理**: 使用 `--stop-on-error` 可以在遇到错误时立即停止

5. **报告保存**: 使用 `--save-report` 可以保存执行结果，方便后续分析

---

## 扩展建议

如果需要更多功能，可以考虑：

1. **脚本依赖管理** - 定义脚本之间的依赖关系
2. **并行执行** - 支持并行执行多个独立脚本
3. **脚本模板** - 快速创建新脚本的模板
4. **执行历史** - 记录脚本执行历史
5. **性能分析** - 分析脚本执行性能

---

## 快速开始

```bash
# 1. 查看所有可用脚本
python3 script_manager.py list

# 2. 查看脚本详情
python3 script_manager.py info <脚本名>

# 3. 搜索脚本
python3 script_manager.py search --keyword <关键词>

# 4. 批量执行脚本
python3 batch_script_runner.py <脚本1> <脚本2> ... --save-report
```
