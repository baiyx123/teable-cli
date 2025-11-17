#!/bin/bash
# 测试 merge update 功能

echo "=== 测试 Merge Update 功能 ==="
echo ""

# 切换到订单表
echo "1. 切换到订单表..."
t use 订单表 > /dev/null 2>&1
echo "✅ 已切换到订单表"
echo ""

# 测试1: 直接更新模式
echo "2. 测试直接更新模式（更新管道记录本身）"
echo "   命令: echo 'recTest001 订单号=ORD001' | t update 备注=直接更新"
echo "recTest001 订单号=ORD001" | t update 备注=直接更新 2>&1 | grep -E "(开始流式处理|流式更新完成|错误)" | head -2
echo ""

# 测试2: Merge update模式 - 基本用法
echo "3. 测试 Merge Update 模式（基本用法）"
echo "   命令: echo 'recTest002 订单号=ORD002' | t update 状态=已完成 where 订单号=@订单号"
echo "recTest002 订单号=ORD002" | t update 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(开始merge update|Merge update完成|错误)" | head -2
echo ""

# 测试3: Merge update模式 - 多个条件
echo "4. 测试 Merge Update 模式（多个条件）"
echo "   命令: echo 'recTest003 订单号=ORD003 客户名称=张三' | t update 状态=已完成 where 订单号=@订单号 客户名称=@客户名称"
echo "recTest003 订单号=ORD003 客户名称=张三" | t update 状态=已完成 where 订单号=@订单号 客户名称=@客户名称 2>&1 | grep -E "(开始merge update|Merge update完成|错误)" | head -2
echo ""

# 测试4: Merge update模式 - 混合条件
echo "5. 测试 Merge Update 模式（混合条件：管道值 + 常量值）"
echo "   命令: echo 'recTest004 订单号=ORD004' | t update 状态=已完成 where 订单号=@订单号 状态=待处理"
echo "recTest004 订单号=ORD004" | t update 状态=已完成 where 订单号=@订单号 状态=待处理 2>&1 | grep -E "(开始merge update|Merge update完成|错误)" | head -2
echo ""

# 测试5: 字段映射更新
echo "6. 测试字段映射更新（从管道记录中获取值）"
echo "   命令: echo 'recTest005 订单号=ORD005 备注=原始备注' | t update 新备注=@备注"
echo "recTest005 订单号=ORD005 备注=原始备注" | t update 新备注=@备注 2>&1 | grep -E "(开始流式处理|流式更新完成|错误)" | head -2
echo ""

echo "=== 功能说明 ==="
echo ""
echo "✅ 直接更新模式：更新管道记录本身"
echo "   语法: t show | t update 字段=值"
echo ""
echo "✅ Merge Update 模式：根据 where 条件查找并更新匹配的记录"
echo "   语法: t show | t update 字段=值 where 条件字段=@源字段"
echo ""
echo "✅ 字段映射：使用 @字段名 从管道记录中获取值"
echo "   示例: t show | t update 新状态=@状态 where 订单号=@订单号"

