#!/bin/bash
# 批量插入20条订单测试数据

set -e

echo "=== 开始批量插入20条订单测试数据 ==="
echo ""

# 准备测试数据
CUSTOMERS=("顺丰速运有限公司" "京东物流科技" "中通快递股份有限公司" "上海化工集团有限公司" "江苏石油化工股份公司")
PRODUCTS=("油漆" "硫酸" "汽油" "液化石油气" "氢氧化钠")
PICKUP_ADDRESSES=("上海化工集团仓库" "江苏石化南京仓库" "上海火车站")
DELIVERY_ADDRESSES=("上海化工集团收货点" "江苏石化苏州分库" "上海火车站路")

# 步骤1: 准备客户（查询不到就创建）
echo "=== 步骤1: 准备客户数据 ==="
for CUSTOMER in "${CUSTOMERS[@]}"; do
    EXISTS=$(t show 客户表 "客户名称=$CUSTOMER" 2>&1 | grep -c "^rec" || echo "0")
    EXISTS=$(echo "$EXISTS" | tr -d '\r\n ')
    if [ "$EXISTS" = "0" ]; then
        echo "创建客户: $CUSTOMER"
        t insert 客户表 "客户名称=$CUSTOMER" > /dev/null 2>&1
    else
        echo "客户已存在: $CUSTOMER"
    fi
done
echo ""

# 步骤2: 准备地址（查询不到就创建）
echo "=== 步骤2: 准备地址数据 ==="
for i in "${!PICKUP_ADDRESSES[@]}"; do
    PICKUP_ADDR=${PICKUP_ADDRESSES[$i]}
    DELIVERY_ADDR=${DELIVERY_ADDRESSES[$i]}
    CUSTOMER=${CUSTOMERS[$i]}
    
    # 检查提货地址
    EXISTS=$(t show 地址库表 "任务=$PICKUP_ADDR" 2>&1 | grep -c "^rec" || echo "0")
    EXISTS=$(echo "$EXISTS" | tr -d '\r\n ')
    if [ "$EXISTS" = "0" ]; then
        echo "创建提货地址: $PICKUP_ADDR"
        t insert 地址库表 "任务=$PICKUP_ADDR" "详细地址=${PICKUP_ADDR}详细地址" "地址类型=发货地址" "关联客户=$CUSTOMER" > /dev/null 2>&1
    fi
    
    # 检查送货地址
    EXISTS=$(t show 地址库表 "任务=$DELIVERY_ADDR" 2>&1 | grep -c "^rec" || echo "0")
    EXISTS=$(echo "$EXISTS" | tr -d '\r\n ')
    if [ "$EXISTS" = "0" ]; then
        echo "创建送货地址: $DELIVERY_ADDR"
        t insert 地址库表 "任务=$DELIVERY_ADDR" "详细地址=${DELIVERY_ADDR}详细地址" "地址类型=收货地址" "关联客户=$CUSTOMER" > /dev/null 2>&1
    fi
done
echo ""

# 步骤3: 准备产品（查询不到就创建）
echo "=== 步骤3: 准备产品数据 ==="
for PRODUCT in "${PRODUCTS[@]}"; do
    EXISTS=$(t show 产品表 "产品名称=$PRODUCT" 2>&1 | grep -c "^rec" || echo "0")
    EXISTS=$(echo "$EXISTS" | tr -d '\r\n ')
    if [ "$EXISTS" = "0" ]; then
        echo "创建产品: $PRODUCT"
        t insert 产品表 "产品名称=$PRODUCT" "产品分类=普通货物" "标准毛重=10" "标准净重=10" > /dev/null 2>&1
    else
        echo "产品已存在: $PRODUCT"
    fi
done
echo ""

# 步骤4: 创建20条订单（使用 insert | insert 管道）
echo "=== 步骤4: 创建20条订单（使用 insert | insert 管道）==="

SUCCESS_COUNT=0
FAIL_COUNT=0

for i in {1..20}; do
    PRODUCT=${PRODUCTS[$((($i-1) % ${#PRODUCTS[@]}))]}
    CUSTOMER=${CUSTOMERS[$((($i-1) % ${#CUSTOMERS[@]}))]}
    PICKUP_ADDR=${PICKUP_ADDRESSES[$((($i-1) % ${#PICKUP_ADDRESSES[@]}))]}
    DELIVERY_ADDR=${DELIVERY_ADDRESSES[$((($i-1) % ${#DELIVERY_ADDRESSES[@]}))]}
    WEIGHT=$((10 + $i))
    
    # 计算日期
    DELEGATE_DATE=$(date -v+${i}d +%Y-%m-%d 2>/dev/null || date -d "+${i} days" +%Y-%m-%d)
    ARRIVE_DATE=$(date -v+$((i+3))d +%Y-%m-%d 2>/dev/null || date -d "+$((i+3)) days" +%Y-%m-%d)
    
    echo "创建订单 $i: 委托时间=$DELEGATE_DATE, 要求到达时间=$ARRIVE_DATE"
    echo "  客户=$CUSTOMER, 提货地址=$PICKUP_ADDR, 送货地址=$DELIVERY_ADDR"
    echo "  货物名称=订单${i}_货物, 毛重=$WEIGHT, 关联产品=$PRODUCT"
    
    # 使用 insert | insert 管道：先插入货物明细，然后管道到订单表
    RESULT=$(t insert 货物明细表 "货物名称=订单${i}_货物" "毛重=$WEIGHT" "关联产品=$PRODUCT" | \
             t insert 订单表 "货物明细表=@id" "委托时间=$DELEGATE_DATE" "要求到达时间=$ARRIVE_DATE" \
             "订单状态=待接单" "关联客户=$CUSTOMER" "提货地址=$PICKUP_ADDR" "送货地址=$DELIVERY_ADDR")
    
    # 检查是否成功
    if echo "$RESULT" | grep -q "✅ 成功插入记录"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "  ✅ 成功创建订单 $i"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  ❌ 创建失败"
        echo "$RESULT" | grep -E "(错误|失败|警告)" | head -5
    fi
    
    sleep 0.3
done

echo ""
echo "=== 插入完成 ==="
echo "成功: $SUCCESS_COUNT 条订单"
echo "失败: $FAIL_COUNT 条订单"
echo ""
