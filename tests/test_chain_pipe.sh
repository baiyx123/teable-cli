#!/bin/bash
# 测试链式管道操作：show | insert | update | show

echo "=========================================="
echo "测试链式管道操作"
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

echo "=== 测试1: show | insert（插入后输出）==="
echo "命令: t show limit=2 | t insert 订单号=@订单号 客户名称=@客户名称 | head -2"
echo "说明: 查询订单，插入到另一张表，然后输出插入的记录"
echo ""
t show limit=2 2>&1 | head -2 | t insert 订单号=@订单号 客户名称=@客户名称 2>&1 | head -3
echo ""

echo "=== 测试2: show | insert | update（插入后更新，更新后输出）==="
echo "命令: t show limit=1 | t insert 订单号=@订单号 | t update 状态=已完成 | head -1"
echo "说明: 查询订单，插入，更新状态，然后输出更新的记录"
echo ""
t show limit=1 2>&1 | head -1 | t insert 订单号=@订单号 2>&1 | t update 状态=已完成 2>&1 | head -2
echo ""

echo "=== 测试3: show | insert | update | show（完整链式操作）==="
echo "命令: t show limit=1 | t insert 订单号=@订单号 | t update 状态=已完成 | t show 客户表 where 联系人姓名=@客户名称"
echo "说明: 查询订单 -> 插入 -> 更新 -> 关联查询客户表"
echo ""
t show limit=1 2>&1 | head -1 | t insert 订单号=@订单号 2>&1 | t update 状态=已完成 2>&1 | t show 客户表 where 联系人姓名=@客户名称 2>&1 | head -3
echo ""

echo "=========================================="
echo "✅ 链式管道操作测试完成"
echo "=========================================="
echo ""
echo "功能说明:"
echo "✅ show | insert: 插入后输出插入的记录"
echo "✅ show | insert | update: 插入后更新，更新后输出更新的记录"
echo "✅ show | insert | update | show: 完整的链式管道操作"

