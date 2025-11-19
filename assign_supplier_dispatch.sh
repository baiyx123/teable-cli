#!/bin/bash
# 批量给货物明细指派供应商派车

set -e

echo "=== 批量给货物明细指派供应商派车 ==="
echo ""

# 切换到供应商表，获取供应商ID列表
echo "=== 步骤1: 获取供应商ID列表 ==="
t use 供应商表
SUPPLIER_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
SUPPLIER_COUNT=${#SUPPLIER_IDS[@]}
echo "找到 $SUPPLIER_COUNT 条供应商记录"
echo ""

if [ $SUPPLIER_COUNT -eq 0 ]; then
    echo "❌ 供应商表中没有供应商记录"
    exit 1
fi

# 切换到货物明细表，获取待指派的货物明细ID列表
echo "=== 步骤2: 获取待指派的货物明细ID列表 ==="
t use 货物明细表
CARGO_IDS=($(t show where 状态=待指派 limit=100 | grep "^rec" | cut -d' ' -f1))
CARGO_COUNT=${#CARGO_IDS[@]}
echo "找到 $CARGO_COUNT 条待指派的货物明细记录"
echo ""

if [ $CARGO_COUNT -eq 0 ]; then
    echo "❌ 没有找到待指派的货物明细记录"
    exit 1
fi

# 批量创建供应商派车记录并关联到货物明细
echo "=== 步骤3: 批量创建供应商派车记录 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!CARGO_IDS[@]}"; do
    CARGO_ID=${CARGO_IDS[$i]}
    
    # 循环使用供应商（按货物明细索引取模）
    SUPPLIER_INDEX=$((i % SUPPLIER_COUNT))
    SUPPLIER_ID=${SUPPLIER_IDS[$SUPPLIER_INDEX]}
    
    # 使用管道方式创建供应商派车记录并关联货物明细
    # t insert 供应商派车表 关联货物明细=@id 关联供应商=$SUPPLIER_ID 指派类型=手动指派
    # 但是我们需要先插入供应商派车记录，然后更新关联货物明细
    # 或者直接使用 insert 命令，让系统自动关联
    
    # 先创建供应商派车记录
    DISPATCH_ID=$(t insert 供应商派车表 "关联供应商=$SUPPLIER_ID" "指派类型=手动指派" 2>&1 | grep "^rec" | head -1 | cut -d' ' -f1)
    
    if [ -n "$DISPATCH_ID" ] && [[ "$DISPATCH_ID" =~ ^rec ]]; then
        # 更新供应商派车记录，关联货物明细
        if t update "$DISPATCH_ID" "关联货物明细=$CARGO_ID" > /dev/null 2>&1; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            if [ $((SUCCESS_COUNT % 10)) -eq 0 ]; then
                echo "已创建 $SUCCESS_COUNT 条供应商派车记录..."
            fi
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [ $FAIL_COUNT -le 5 ]; then
                echo "❌ 更新供应商派车记录 $DISPATCH_ID 失败"
            fi
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $FAIL_COUNT -le 5 ]; then
            echo "❌ 创建供应商派车记录失败"
        fi
    fi
    
    # 避免请求过快
    sleep 0.1
done

echo ""
echo "=== 创建完成 ==="
echo "成功: $SUCCESS_COUNT 条供应商派车记录"
echo "失败: $FAIL_COUNT 条供应商派车记录"
echo ""

# 验证创建结果
echo "=== 验证创建结果 ==="
t use 供应商派车表
t show limit=5 | grep -E "^rec|关联货物明细|关联供应商" || true

