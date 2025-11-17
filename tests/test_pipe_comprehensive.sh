#!/bin/bash
# 综合测试管道功能

echo "=========================================="
echo "Teable CLI 管道功能综合测试"
echo "=========================================="
echo ""

# 切换到订单表
echo "1. 切换到订单表..."
t use 订单表 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 已切换到订单表"
else
    echo "❌ 切换表格失败"
    exit 1
fi
echo ""

# 测试1: show 命令管道输出格式
echo "2. 测试 show 命令管道输出格式"
echo "   命令: t show limit=1"
output=$(t show limit=1 2>&1 | head -1)
if [ -n "$output" ]; then
    echo "✅ 管道输出: ${output:0:80}..."
    if [[ $output == rec* ]]; then
        echo "✅ 输出格式正确：以记录ID开头"
    else
        echo "⚠️  输出格式可能不正确"
    fi
else
    echo "❌ 没有输出"
fi
echo ""

# 测试2: show | insert 字段映射模式
echo "3. 测试 show | insert 字段映射模式"
echo "   命令: echo 'recTest001 订单号=ORD001 客户名称=测试客户' | t insert 新订单号=@订单号 新客户=@客户名称 状态=已完成"
echo "recTest001 订单号=ORD001 客户名称=测试客户" | t insert 新订单号=@订单号 新客户=@客户名称 状态=已完成 2>&1 | grep -E "(使用手动映射模式|字段映射|常量值|真正流式插入完成|错误)" | head -3
echo ""

# 测试3: show | update 直接更新模式
echo "4. 测试 show | update 直接更新模式"
echo "   命令: echo 'recTest002 订单号=ORD002' | t update 备注=直接更新测试"
echo "recTest002 订单号=ORD002" | t update 备注=直接更新测试 2>&1 | grep -E "(开始流式处理|流式更新完成|错误)" | head -2
echo ""

# 测试4: show | update 字段映射模式
echo "5. 测试 show | update 字段映射模式"
echo "   命令: echo 'recTest003 订单号=ORD003 状态=待处理' | t update 新状态=@状态"
echo "recTest003 订单号=ORD003 状态=待处理" | t update 新状态=@状态 2>&1 | grep -E "(开始流式处理|流式更新完成|错误)" | head -2
echo ""

# 测试5: show | update merge update 模式
echo "6. 测试 show | update merge update 模式"
echo "   命令: echo 'recTest004 订单号=ORD004' | t update 状态=已完成 where 订单号=@订单号"
echo "recTest004 订单号=ORD004" | t update 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(切换到表格|开始merge update|Merge update完成|错误)" | head -3
echo ""

# 测试6: show | update 表名参数
echo "7. 测试 show | update 表名参数"
echo "   命令: echo 'recTest005 订单号=ORD005' | t update 订单表 备注=表名参数测试"
echo "recTest005 订单号=ORD005" | t update 订单表 备注=表名参数测试 2>&1 | grep -E "(切换到表格|流式更新完成|错误)" | head -2
echo ""

# 测试7: show | update merge update 表名参数
echo "8. 测试 show | update merge update 表名参数"
echo "   命令: echo 'recTest006 订单号=ORD006' | t update 订单表 状态=已完成 where 订单号=@订单号"
echo "recTest006 订单号=ORD006" | t update 订单表 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(切换到表格|开始merge update|Merge update完成|错误)" | head -3
echo ""

# 测试8: 复杂场景 - 混合字段映射和常量值
echo "9. 测试复杂场景 - 混合字段映射和常量值"
echo "   命令: echo 'recTest007 订单号=ORD007 客户名称=张三' | t insert 新订单=@订单号 原客户=@客户名称 状态=已完成 备注=来自管道"
echo "recTest007 订单号=ORD007 客户名称=张三" | t insert 新订单=@订单号 原客户=@客户名称 状态=已完成 备注=来自管道 2>&1 | grep -E "(使用手动映射模式|字段映射|常量值|真正流式插入完成)" | head -4
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "功能说明:"
echo "✅ show | insert: 支持字段映射(@字段名)和常量值"
echo "✅ show | update: 支持直接更新和merge update模式"
echo "✅ update 表名参数: 支持指定表名进行更新"
echo "✅ merge update: 根据where条件查找并更新匹配的记录"

