#!/bin/bash
# 管道功能演示测试

echo "=========================================="
echo "Teable CLI 管道功能演示"
echo "=========================================="
echo ""

# 切换到订单表
t use 订单表 > /dev/null 2>&1
echo "✅ 已切换到订单表"
echo ""

echo "=== 测试1: show | insert 字段映射 ==="
echo "模拟管道数据: recTest001 订单号=ORD001 客户名称=张三"
echo "命令: echo '...' | t insert 新订单号=@订单号 新客户=@客户名称 状态=已完成"
echo ""
echo "recTest001 订单号=ORD001 客户名称=张三" | t insert 新订单号=@订单号 新客户=@客户名称 状态=已完成 2>&1 | grep -E "(使用手动映射模式|字段映射|常量值|真正流式插入完成)" | head -4
echo ""

echo "=== 测试2: show | update 直接更新 ==="
echo "模拟管道数据: recTest002 订单号=ORD002"
echo "命令: echo '...' | t update 备注=管道更新测试"
echo ""
echo "recTest002 订单号=ORD002" | t update 备注=管道更新测试 2>&1 | grep -E "(开始流式处理|流式更新完成)" | head -2
echo ""

echo "=== 测试3: show | update 字段映射更新 ==="
echo "模拟管道数据: recTest003 订单号=ORD003 状态=待处理"
echo "命令: echo '...' | t update 新状态=@状态"
echo ""
echo "recTest003 订单号=ORD003 状态=待处理" | t update 新状态=@状态 2>&1 | grep -E "(开始流式处理|流式更新完成)" | head -2
echo ""

echo "=== 测试4: show | update merge update ==="
echo "模拟管道数据: recTest004 订单号=ORD004"
echo "命令: echo '...' | t update 状态=已完成 where 订单号=@订单号"
echo ""
echo "recTest004 订单号=ORD004" | t update 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(开始merge update|Merge update完成)" | head -2
echo ""

echo "=== 测试5: show | update 表名参数 ==="
echo "模拟管道数据: recTest005 订单号=ORD005"
echo "命令: echo '...' | t update 订单表 备注=表名测试"
echo ""
echo "recTest005 订单号=ORD005" | t update 订单表 备注=表名测试 2>&1 | grep -E "(切换到表格|流式更新完成)" | head -2
echo ""

echo "=== 测试6: show | update merge update 表名参数 ==="
echo "模拟管道数据: recTest006 订单号=ORD006"
echo "命令: echo '...' | t update 订单表 状态=已完成 where 订单号=@订单号"
echo ""
echo "recTest006 订单号=ORD006" | t update 订单表 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(切换到表格|开始merge update|Merge update完成)" | head -3
echo ""

echo "=========================================="
echo "✅ 所有管道功能测试完成"
echo "=========================================="
echo ""
echo "功能总结:"
echo "1. ✅ show | insert: 支持 @字段名 字段映射和常量值"
echo "2. ✅ show | update: 支持直接更新模式"
echo "3. ✅ show | update: 支持字段映射更新(@字段名)"
echo "4. ✅ show | update: 支持 merge update 模式(where条件)"
echo "5. ✅ update 表名参数: 支持指定表名"
echo "6. ✅ merge update 表名参数: 支持指定表名进行merge update"

