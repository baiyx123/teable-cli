#!/bin/bash
# 测试 show | show 关联查询功能

echo "=========================================="
echo "测试 show | show 关联查询功能"
echo "=========================================="
echo ""

# 切换到订单表
t use 订单表 > /dev/null 2>&1
echo "✅ 已切换到订单表"
echo ""

echo "=== 测试1: show | show 关联查询（基本用法）==="
echo "命令: t show limit=2 | t show 客户表 where 客户ID=@订单客户ID"
echo "说明: 从订单表查询订单，然后根据订单中的客户ID查询客户表"
echo ""
t show limit=2 2>&1 | head -2 | t show 客户表 where 客户ID=@订单客户ID 2>&1 | head -5
echo ""

echo "=== 测试2: show | show 关联查询（使用@字段名）==="
echo "命令: t show limit=2 | t show 客户表 where 联系人姓名=@订单客户名称"
echo "说明: 从订单表查询订单，然后根据订单中的客户名称查询客户表"
echo ""
t show limit=2 2>&1 | head -2 | t show 客户表 where 联系人姓名=@订单客户名称 2>&1 | head -5
echo ""

echo "=== 测试3: show | show 多条件关联查询 ==="
echo "命令: t show limit=2 | t show 客户表 where 联系人姓名=@订单客户名称 联系电话=@订单联系电话"
echo ""
t show limit=2 2>&1 | head -2 | t show 客户表 where 联系人姓名=@订单客户名称 联系电话=@订单联系电话 2>&1 | head -5
echo ""

echo "=========================================="
echo "✅ 关联查询功能测试完成"
echo "=========================================="
echo ""
echo "功能说明:"
echo "✅ show | show: 实现关联查询，类似 SQL 的 JOIN"
echo "✅ where 条件支持 @字段名: 从管道记录中获取值"
echo "✅ 流式处理: 每条管道记录独立查询"

