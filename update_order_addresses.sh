#!/bin/bash
# 批量更新订单表的起运地址和目的地地址字段

set -e

echo "=== 批量更新订单表的地址字段 ==="
echo ""

# 切换到地址库表，获取地址ID列表
echo "=== 步骤1: 获取地址ID列表 ==="
t use 地址库表
ADDRESS_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
ADDRESS_COUNT=${#ADDRESS_IDS[@]}
echo "找到 $ADDRESS_COUNT 条地址记录"
echo ""

if [ $ADDRESS_COUNT -lt 2 ]; then
    echo "❌ 地址数量不足，至少需要2条地址"
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

# 批量更新订单地址
echo "=== 步骤3: 批量更新订单地址 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!ORDER_IDS[@]}"; do
    ORDER_ID=${ORDER_IDS[$i]}
    
    # 循环使用地址（前一半作为起运地址，后一半作为目的地地址）
    PICKUP_ADDR_INDEX=$((i % (ADDRESS_COUNT / 2)))
    DELIVERY_ADDR_INDEX=$((PICKUP_ADDR_INDEX + ADDRESS_COUNT / 2))
    
    if [ $DELIVERY_ADDR_INDEX -ge $ADDRESS_COUNT ]; then
        DELIVERY_ADDR_INDEX=$((DELIVERY_ADDR_INDEX - ADDRESS_COUNT / 2))
    fi
    
    PICKUP_ADDR_ID=${ADDRESS_IDS[$PICKUP_ADDR_INDEX]}
    DELIVERY_ADDR_ID=${ADDRESS_IDS[$DELIVERY_ADDR_INDEX]}
    
    # 更新订单
    if t update "$ORDER_ID" "起运地址=$PICKUP_ADDR_ID" "目的地地址=$DELIVERY_ADDR_ID" > /dev/null 2>&1; then
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
t show limit=5 | grep -E "^rec|起运地址|目的地地址" || true

