#!/bin/bash
# 简单的管道功能测试

set -e

echo "=== 简单管道功能测试 ==="
echo ""

# 使用已有的测试表
echo "=== 步骤1: 测试 show | insert（使用有产品名称的记录）==="
t use 测试产品表
echo "查询有产品名称的产品（跳过只有编号的旧记录）..."
t show | grep "产品名称=" | head -2 | t insert 测试订单表 "订单状态=新订单" "关联产品=@产品名称"
echo ""

echo "=== 步骤2: 验证插入结果 ==="
t use 测试订单表
echo "订单表数据（最新3条）:"
t show limit=3
echo ""

echo "=== 步骤3: 测试 show | update（管道更新）==="
echo "更新订单状态..."
t show limit=1 | t update "订单状态=已更新"
echo ""

echo "=== 步骤4: 验证更新结果 ==="
t show limit=3
echo ""

echo "✅ 管道功能测试完成！"
echo ""
echo "测试内容："
echo "  ✅ show | insert（管道插入，使用@字段名映射）"
echo "  ✅ show | update（管道更新）"
echo ""

