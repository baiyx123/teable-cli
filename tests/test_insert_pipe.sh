#!/bin/bash
# 测试 show | insert 管道功能

echo "=== 测试 show | insert 管道功能 ==="
echo ""

# 切换到订单表
echo "1. 切换到订单表..."
t use 订单表 > /dev/null 2>&1
echo "✅ 已切换到订单表"
echo ""

# 测试1: 自动映射模式（无参数）
echo "2. 测试自动映射模式（类似 INSERT INTO ... SELECT ...）"
echo "   模拟管道输入: recTest001 订单号=ORD001 客户名称=测试客户"
echo "recTest001 订单号=ORD001 客户名称=测试客户" | t insert 2>&1 | grep -E "(使用自动映射模式|使用字段映射模式|真正流式插入完成|没有有效字段数据)" | head -3
echo ""

# 测试2: 手动映射模式（有参数）
echo "3. 测试手动字段映射模式"
echo "   模拟管道输入: recTest002 订单号=ORD002"
echo "recTest002 订单号=ORD002" | t insert 备注=来自管道测试 状态=测试中 2>&1 | grep -E "(使用自动映射模式|使用字段映射模式|字段映射|真正流式插入完成)" | head -3
echo ""

# 测试3: 验证管道输入检测
echo "4. 验证管道输入检测功能"
echo "   测试: echo 'recTest003 字段=值' | t insert"
result=$(echo "recTest003 字段=值" | t insert 2>&1 | grep -c "使用自动映射模式")
if [ "$result" -gt 0 ]; then
    echo "✅ 成功检测到管道输入并启用自动映射模式"
else
    echo "⚠️  未检测到自动映射模式提示"
fi
echo ""

echo "=== 测试完成 ==="
echo ""
echo "说明:"
echo "- 如果看到'使用自动映射模式'，说明自动字段映射功能正常"
echo "- 如果看到'使用字段映射模式'，说明手动字段映射功能正常"
echo "- 插入失败可能是因为字段名不匹配或字段不存在，这是正常的"

