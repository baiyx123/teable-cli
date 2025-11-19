# 测试脚本目录

本目录包含所有CLI功能的测试脚本。

## 测试脚本说明

### 基本功能测试
- **test_basic_functionality.sh** - 测试CLI基本功能
  - 创建表格
  - 创建关联字段
  - 插入记录
  - 更新记录
  - 查看数据
  - 智能匹配关联

### 管道功能测试
- **test_pipe_simple.sh** - 简单管道功能测试
  - show | insert（管道插入）
  - show | update（管道更新）

- **test_pipe_functionality.sh** - 完整管道功能测试
  - show | insert
  - show | update
  - show | show（关联查询）
  - insert | insert（链式插入）
  - 复杂管道链

- **test_pipe_functionality_fixed.sh** - 修复版管道功能测试（使用text字段）

## 运行测试

```bash
# 运行基本功能测试
./tests/test_basic_functionality.sh

# 运行简单管道测试
./tests/test_pipe_simple.sh

# 运行完整管道测试
./tests/test_pipe_functionality.sh
```

## 注意事项

1. 测试脚本会创建和删除测试表格（测试产品表、测试订单表等）
2. 确保已正确配置CLI（`t config`）
3. 测试过程中可能会产生一些测试数据

## 测试报告

详细的测试报告请查看：`../docs/test_summary.md`
