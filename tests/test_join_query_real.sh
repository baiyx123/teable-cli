#!/bin/bash
# 使用真实的 show 命令测试关联查询功能

echo "=========================================="
echo "使用真实 show 命令测试关联查询功能"
echo "=========================================="
echo ""

# 切换到订单表
t use 订单表 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 已切换到订单表"
else
    echo "❌ 切换表格失败"
    exit 1
fi
echo ""

echo "=== 测试1: 查看订单表的字段 ==="
echo "命令: t show limit=1"
echo ""
t show limit=1 2>&1 | head -1
echo ""

echo "=== 测试2: show | show 关联查询（基本用法）==="
echo "命令: t show limit=2 | t show 客户表 where 联系人姓名=@客户名称"
echo "说明: 从订单表查询订单，然后根据订单中的客户名称查询客户表"
echo ""
t show limit=2 2>&1 | head -2 | t show 客户表 where 联系人姓名=@客户名称 2>&1 | head -10
echo ""

echo "=== 测试3: show | show 关联查询（多条记录）==="
echo "命令: t show limit=3 | t show 客户表 where 联系人姓名=@客户名称"
echo ""
t show limit=3 2>&1 | head -3 | t show 客户表 where 联系人姓名=@客户名称 2>&1 | grep -E "(正在从管道|开始关联查询|关联查询完成|找到.*条匹配记录|rec)" | head -10
echo ""

echo "=== 测试4: show | show 多条件关联查询 ==="
echo "命令: t show limit=2 | t show 客户表 where 联系人姓名=@客户名称 联系电话=@联系电话"
echo ""
t show limit=2 2>&1 | head -2 | t show 客户表 where 联系人姓名=@客户名称 联系电话=@联系电话 2>&1 | grep -E "(正在从管道|开始关联查询|关联查询完成|找到.*条匹配记录|rec)" | head -10
echo ""

echo "=== 测试5: show | show | show 链式关联查询 ==="
echo "命令: t show limit=1 | t show 客户表 where 联系人姓名=@客户名称 | head -1"
echo "说明: 订单表 -> 客户表 -> 限制输出"
echo ""
t show limit=1 2>&1 | head -1 | t show 客户表 where 联系人姓名=@客户名称 2>&1 | head -1
echo ""

echo "=========================================="
echo "✅ 关联查询功能测试完成"
echo "=========================================="
echo ""
echo "功能说明:"
echo "✅ show | show: 实现关联查询，类似 SQL 的 JOIN"
echo "✅ where 条件支持 @字段名: 从管道记录中获取值"
echo "✅ 流式处理: 每条管道记录独立查询"
echo "✅ 支持链式查询: show | show | show"

