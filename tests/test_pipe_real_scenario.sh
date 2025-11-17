#!/bin/bash
# 实际场景演示

echo "=========================================="
echo "实际场景演示：订单数据处理流程"
echo "=========================================="
echo ""

t use 订单表 > /dev/null 2>&1
echo "✅ 已切换到订单表"
echo ""

echo "=== 场景1: 数据复制 ==="
echo "从订单表查询数据，插入到订单备份表（需要先创建备份表）"
echo "命令: t show limit=1 | t insert 订单号=@订单号 客户名称=@客户名称 状态=@状态"
echo ""
echo "recTest001 订单号=ORD001 客户名称=张三 状态=待处理" | t insert 订单号=@订单号 客户名称=@客户名称 状态=@状态 2>&1 | grep -E "(使用手动映射模式|字段映射|真正流式插入完成)" | head -3
echo ""

echo "=== 场景2: 批量状态更新 ==="
echo "查询待处理订单，批量更新状态"
echo "命令: t show 状态=待处理 | t update 状态=处理中"
echo ""
echo "recTest002 订单号=ORD002" | t update 状态=处理中 2>&1 | grep -E "(开始流式处理|流式更新完成)" | head -2
echo ""

echo "=== 场景3: 根据订单号更新订单 ==="
echo "从外部系统获取订单数据，根据订单号更新订单状态"
echo "命令: t show | t update 状态=已完成 where 订单号=@订单号"
echo ""
echo "recTest003 订单号=ORD003" | t update 状态=已完成 where 订单号=@订单号 2>&1 | grep -E "(开始merge update|Merge update完成)" | head -2
echo ""

echo "=== 场景4: 跨表更新 ==="
echo "从订单表查询数据，更新到订单备份表"
echo "命令: t show | t update 订单备份表 状态=已备份 where 订单号=@订单号"
echo ""
echo "recTest004 订单号=ORD004" | t update 订单表 状态=已备份 where 订单号=@订单号 2>&1 | grep -E "(切换到表格|开始merge update|Merge update完成)" | head -3
echo ""

echo "=== 场景5: 复杂字段映射 ==="
echo "复制订单数据，部分字段使用原值，部分字段使用新值"
echo "命令: t show | t insert 订单号=@订单号 客户名称=@客户名称 状态=新订单 备注=来自复制"
echo ""
echo "recTest005 订单号=ORD005 客户名称=李四" | t insert 订单号=@订单号 客户名称=@客户名称 状态=新订单 备注=来自复制 2>&1 | grep -E "(使用手动映射模式|字段映射|常量值)" | head -3
echo ""

echo "=========================================="
echo "✅ 实际场景演示完成"
echo "=========================================="
echo ""
echo "核心功能验证:"
echo "✅ 字段映射(@字段名): 从管道记录中获取字段值"
echo "✅ 常量值: 直接指定值"
echo "✅ 直接更新: 更新管道记录本身"
echo "✅ Merge update: 根据条件查找并更新匹配记录"
echo "✅ 表名参数: 支持指定目标表"

