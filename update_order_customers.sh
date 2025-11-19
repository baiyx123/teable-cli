#!/bin/bash
# 批量更新订单表的关联客户字段

set -e

echo "=== 批量更新订单表的客户字段 ==="
echo ""

# 切换到客户表，获取客户ID列表
echo "=== 步骤1: 获取客户ID列表 ==="
t use 客户表
CUSTOMER_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
CUSTOMER_COUNT=${#CUSTOMER_IDS[@]}
echo "找到 $CUSTOMER_COUNT 条客户记录"
echo ""

if [ $CUSTOMER_COUNT -eq 0 ]; then
    echo "❌ 客户表中没有客户记录"
    exit 1
fi

# 切换到订单表，获取订单ID列表
echo "=== 步骤2: 获取订单ID列表 ==="
t use 订单表
ORDER_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
ORDER_COUNT=${#ORDER_IDS[@]}
echo "找到 $ORDER_COUNT 条订单记录"
echo ""

if [ $ORDER_COUNT -eq 0 ]; then
    echo "❌ 没有找到订单记录"
    exit 1
fi

# 批量更新订单客户
echo "=== 步骤3: 批量更新订单客户 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!ORDER_IDS[@]}"; do
    ORDER_ID=${ORDER_IDS[$i]}
    
    # 循环使用客户（按订单索引取模）
    CUSTOMER_INDEX=$((i % CUSTOMER_COUNT))
    CUSTOMER_ID=${CUSTOMER_IDS[$CUSTOMER_INDEX]}
    
    # 更新订单
    if t update "$ORDER_ID" "关联客户=$CUSTOMER_ID" > /dev/null 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        if [ $((SUCCESS_COUNT % 10)) -eq 0 ]; then
            echo "已更新 $SUCCESS_COUNT 条订单..."
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $FAIL_COUNT -le 5 ]; then
            echo "❌ 更新订单 $ORDER_ID 失败"
        fi
    fi
    
    # 避免请求过快
    sleep 0.1
done

echo ""
echo "=== 更新完成 ==="
echo "成功: $SUCCESS_COUNT 条订单"
echo "失败: $FAIL_COUNT 条订单"
echo ""

# 验证更新结果
echo "=== 验证更新结果 ==="
t use 订单表
t show limit=5 | grep -E "^rec|关联客户" || true

