#!/bin/bash
# 批量给货物明细指派内部派车

set -e

echo "=== 批量给货物明细指派内部派车 ==="
echo ""

# 切换到车辆表，获取车辆ID列表
echo "=== 步骤1: 获取车辆ID列表 ==="
t use 车辆表
VEHICLE_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
VEHICLE_COUNT=${#VEHICLE_IDS[@]}
echo "找到 $VEHICLE_COUNT 条车辆记录"
echo ""

if [ $VEHICLE_COUNT -eq 0 ]; then
    echo "❌ 车辆表中没有车辆记录"
    exit 1
fi

# 切换到员工表，获取司机ID列表
echo "=== 步骤2: 获取司机ID列表 ==="
t use 员工表
DRIVER_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
DRIVER_COUNT=${#DRIVER_IDS[@]}
echo "找到 $DRIVER_COUNT 条员工记录"
echo ""

if [ $DRIVER_COUNT -eq 0 ]; then
    echo "❌ 员工表中没有员工记录"
    exit 1
fi

# 切换到货物明细表，获取待指派的货物明细ID列表
echo "=== 步骤3: 获取待指派的货物明细ID列表 ==="
t use 货物明细表
CARGO_IDS=($(t show where 状态=待指派 limit=100 | grep "^rec" | cut -d' ' -f1))
CARGO_COUNT=${#CARGO_IDS[@]}
echo "找到 $CARGO_COUNT 条待指派的货物明细记录"
echo ""

if [ $CARGO_COUNT -eq 0 ]; then
    echo "❌ 没有找到待指派的货物明细记录"
    exit 1
fi

# 批量创建内部派车记录并关联到货物明细
echo "=== 步骤4: 批量创建内部派车记录 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!CARGO_IDS[@]}"; do
    CARGO_ID=${CARGO_IDS[$i]}
    
    # 循环使用车辆和司机（按货物明细索引取模）
    VEHICLE_INDEX=$((i % VEHICLE_COUNT))
    DRIVER_INDEX=$((i % DRIVER_COUNT))
    
    VEHICLE_ID=${VEHICLE_IDS[$VEHICLE_INDEX]}
    DRIVER_ID=${DRIVER_IDS[$DRIVER_INDEX]}
    
    # 先创建内部派车记录
    DISPATCH_ID=$(t insert 内部派车表 "关联车辆=$VEHICLE_ID" "关联司机=$DRIVER_ID" "指派类型=手动指派" 2>&1 | grep "^rec" | head -1 | cut -d' ' -f1)
    
    if [ -n "$DISPATCH_ID" ] && [[ "$DISPATCH_ID" =~ ^rec ]]; then
        # 更新内部派车记录，关联货物明细
        if t update "$DISPATCH_ID" "关联货物明细=$CARGO_ID" > /dev/null 2>&1; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            if [ $((SUCCESS_COUNT % 10)) -eq 0 ]; then
                echo "已创建 $SUCCESS_COUNT 条内部派车记录..."
            fi
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            if [ $FAIL_COUNT -le 5 ]; then
                echo "❌ 更新内部派车记录 $DISPATCH_ID 失败"
            fi
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $FAIL_COUNT -le 5 ]; then
            echo "❌ 创建内部派车记录失败"
        fi
    fi
    
    # 避免请求过快
    sleep 0.1
done

echo ""
echo "=== 创建完成 ==="
echo "成功: $SUCCESS_COUNT 条内部派车记录"
echo "失败: $FAIL_COUNT 条内部派车记录"
echo ""

# 验证创建结果
echo "=== 验证创建结果 ==="
t use 内部派车表
t show limit=5 | grep -E "^rec|关联货物明细|关联车辆|关联司机" || true

