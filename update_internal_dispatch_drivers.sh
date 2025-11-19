#!/bin/bash
# 批量更新内部派车表的关联司机字段

set -e

echo "=== 批量更新内部派车表的关联司机字段 ==="
echo ""

# 切换到员工表，获取员工ID列表
echo "=== 步骤1: 获取员工ID列表 ==="
t use 员工表
EMPLOYEE_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
EMPLOYEE_COUNT=${#EMPLOYEE_IDS[@]}
echo "找到 $EMPLOYEE_COUNT 条员工记录"
echo ""

if [ $EMPLOYEE_COUNT -eq 0 ]; then
    echo "❌ 员工表中没有员工记录"
    exit 1
fi

# 切换到内部派车表，获取内部派车ID列表
echo "=== 步骤2: 获取内部派车ID列表 ==="
t use 内部派车表
DISPATCH_IDS=($(t show limit=100 | grep "^rec" | cut -d' ' -f1))
DISPATCH_COUNT=${#DISPATCH_IDS[@]}
echo "找到 $DISPATCH_COUNT 条内部派车记录"
echo ""

if [ $DISPATCH_COUNT -eq 0 ]; then
    echo "❌ 没有找到内部派车记录"
    exit 1
fi

# 批量更新内部派车的关联司机字段
echo "=== 步骤3: 批量更新内部派车的关联司机 ==="
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!DISPATCH_IDS[@]}"; do
    DISPATCH_ID=${DISPATCH_IDS[$i]}
    
    # 循环使用员工（按内部派车索引取模）
    EMPLOYEE_INDEX=$((i % EMPLOYEE_COUNT))
    EMPLOYEE_ID=${EMPLOYEE_IDS[$EMPLOYEE_INDEX]}
    
    # 更新内部派车
    if t update "$DISPATCH_ID" "关联司机=$EMPLOYEE_ID" > /dev/null 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        if [ $((SUCCESS_COUNT % 10)) -eq 0 ]; then
            echo "已更新 $SUCCESS_COUNT 条内部派车记录..."
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $FAIL_COUNT -le 5 ]; then
            echo "❌ 更新内部派车 $DISPATCH_ID 失败"
        fi
    fi
    
    # 避免请求过快
    sleep 0.1
done

echo ""
echo "=== 更新完成 ==="
echo "成功: $SUCCESS_COUNT 条内部派车记录"
echo "失败: $FAIL_COUNT 条内部派车记录"
echo ""

# 验证更新结果
echo "=== 验证更新结果 ==="
t use 内部派车表
t show limit=5 | grep -E "^rec|关联司机" || true

