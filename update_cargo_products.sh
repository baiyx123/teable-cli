#!/bin/bash
# 批量更新货物明细表的关联产品字段

set -e

echo "=== 批量更新货物明细表的产品字段 ==="
echo ""

# 切换到产品表，获取产品ID列表
echo "=== 步骤1: 获取产品ID列表 ==="
t use 产品表
PRODUCT_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
PRODUCT_COUNT=${#PRODUCT_IDS[@]}
echo "找到 $PRODUCT_COUNT 条产品记录"
echo ""

if [ $PRODUCT_COUNT -eq 0 ]; then
    echo "❌ 产品表中没有产品记录"
    exit 1
fi

# 切换到货物明细表，获取货物明细ID列表
echo "=== 步骤2: 获取货物明细ID列表 ==="
t use 货物明细表
CARGO_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
CARGO_COUNT=${#CARGO_IDS[@]}
echo "找到 $CARGO_COUNT 条货物明细记录"
echo ""

if [ $CARGO_COUNT -eq 0 ]; then
    echo "❌ 没有找到货物明细记录"
    exit 1
fi

# 批量更新货物明细的产品字段
echo "=== 步骤3: 批量更新货物明细产品 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!CARGO_IDS[@]}"; do
    CARGO_ID=${CARGO_IDS[$i]}
    
    # 循环使用产品（按货物明细索引取模）
    PRODUCT_INDEX=$((i % PRODUCT_COUNT))
    PRODUCT_ID=${PRODUCT_IDS[$PRODUCT_INDEX]}
    
    # 更新货物明细
    if t update "$CARGO_ID" "关联产品=$PRODUCT_ID" > /dev/null 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        if [ $((SUCCESS_COUNT % 10)) -eq 0 ]; then
            echo "已更新 $SUCCESS_COUNT 条货物明细..."
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $FAIL_COUNT -le 5 ]; then
            echo "❌ 更新货物明细 $CARGO_ID 失败"
        fi
    fi
    
    # 避免请求过快
    sleep 0.1
done

echo ""
echo "=== 更新完成 ==="
echo "成功: $SUCCESS_COUNT 条货物明细"
echo "失败: $FAIL_COUNT 条货物明细"
echo ""

# 验证更新结果
echo "=== 验证更新结果 ==="
t use 货物明细表
t show limit=5 | grep -E "^rec|关联产品" || true

