#!/bin/bash
# 测试CLI管道功能

set -e

echo "=== 测试CLI管道功能 ==="
echo ""

# 清理：如果测试表已存在，先删除
echo "=== 步骤0: 清理旧数据（如果存在）==="
t drop 测试产品表 --force 2>/dev/null || true
t drop 测试订单表 --force 2>/dev/null || true
echo ""

# 步骤1: 创建测试表格
echo "=== 步骤1: 创建测试表格 ==="
echo "创建测试产品表..."
t create 测试产品表 "产品名称:singleLineText" "产品编号:autoNumber" "价格:number:2"
echo ""

echo "创建测试订单表..."
t create 测试订单表 "订单号:autoNumber" "订单状态:singleSelect" "关联产品:link:manyOne:测试产品表"
echo ""

# 步骤2: 插入产品数据
echo "=== 步骤2: 插入产品数据 ==="
PRODUCT1_ID=$(t insert 测试产品表 "产品名称=笔记本电脑" "价格=5999.99" | grep "^rec" | head -1 | cut -d' ' -f1)
PRODUCT2_ID=$(t insert 测试产品表 "产品名称=手机" "价格=3999.00" | grep "^rec" | head -1 | cut -d' ' -f1)
PRODUCT3_ID=$(t insert 测试产品表 "产品名称=平板电脑" "价格=2999.50" | grep "^rec" | head -1 | cut -d' ' -f1)

echo "产品1 ID: $PRODUCT1_ID"
echo "产品2 ID: $PRODUCT2_ID"
echo "产品3 ID: $PRODUCT3_ID"
echo ""

# 步骤3: 测试管道插入（show | insert）
echo "=== 步骤3: 测试管道插入（show | insert）==="
echo "使用管道方式插入订单，关联产品..."
t use 测试产品表
t show limit=2 | t insert 测试订单表 "订单状态=待处理" "关联产品=@产品名称"
echo ""

# 步骤4: 验证管道插入结果
echo "=== 步骤4: 验证管道插入结果 ==="
t use 测试订单表
echo "订单表数据:"
t show
echo ""

# 步骤5: 测试管道更新（show | update）
echo "=== 步骤5: 测试管道更新（show | update）==="
echo "使用管道方式更新订单状态..."
t use 测试订单表
t show where 订单状态=待处理 | t update "订单状态=已处理"
echo ""

# 步骤6: 验证管道更新结果
echo "=== 步骤6: 验证管道更新结果 ==="
echo "更新后的订单表数据:"
t show
echo ""

# 步骤7: 测试关联查询（show | show）
echo "=== 步骤7: 测试关联查询（show | show）==="
echo "查询产品，然后查询关联的订单..."
t use 测试产品表
echo "产品数据:"
t show limit=2
echo ""
echo "查询这些产品关联的订单:"
t show limit=2 | t show 测试订单表 where 关联产品=@产品名称
echo ""

# 步骤8: 测试链式管道（insert | insert）
echo "=== 步骤8: 测试链式管道（insert | insert）==="
echo "先插入产品，然后管道插入订单..."
PRODUCT4_ID=$(t insert 测试产品表 "产品名称=键盘" "价格=299.00" | grep "^rec" | head -1 | cut -d' ' -f1)
echo "产品4 ID: $PRODUCT4_ID"
echo "使用链式管道插入订单..."
t insert 测试产品表 "产品名称=鼠标" "价格=199.00" | t insert 测试订单表 "订单状态=待发货" "关联产品=@产品名称"
echo ""

# 步骤9: 测试复杂管道链（show | insert | update | show）
echo "=== 步骤9: 测试复杂管道链（show | insert | update | show）==="
echo "查询产品 -> 插入订单 -> 更新状态 -> 显示结果..."
t use 测试产品表
t show limit=1 | t insert 测试订单表 "订单状态=待处理" "关联产品=@产品名称" | t update 测试订单表 "订单状态=已完成" | t show 测试订单表 limit=3
echo ""

# 步骤10: 最终验证
echo "=== 步骤10: 最终验证 ==="
echo "产品表数据:"
t use 测试产品表
t show
echo ""

echo "订单表数据:"
t use 测试订单表
t show
echo ""

echo "✅ 所有管道功能测试完成！"
echo ""
echo "测试内容："
echo "  ✅ show | insert（管道插入）"
echo "  ✅ show | update（管道更新）"
echo "  ✅ show | show（关联查询）"
echo "  ✅ insert | insert（链式插入）"
echo "  ✅ show | insert | update | show（复杂管道链）"
echo ""

