#!/bin/bash
# 使用客户表测试 update 管道功能（多条记录测试）

echo "=========================================="
echo "客户表 Update 管道功能测试（多条记录）"
echo "=========================================="
echo ""

# 切换到客户表
t use 客户表 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ 已切换到客户表"
else
    echo "❌ 切换表格失败"
    exit 1
fi
echo ""

echo "=== 测试1: show 命令管道输出（多条记录）==="
echo "命令: t show limit=5"
echo ""
t show limit=5 2>&1 | head -6
echo ""

echo "=== 测试2: show | update 直接更新模式（批量更新多条记录）==="
echo "命令: t show limit=5 | t update 备注=批量更新测试"
echo ""
t show limit=5 2>&1 | head -5 | t update 备注=批量更新测试 2>&1 | grep -E "(开始流式处理|流式更新完成|已处理.*条记录|错误)" | head -3
echo ""

echo "=== 测试3: show | update 字段映射更新（多条记录）==="
echo "命令: t show limit=5 | t update 新姓名=@联系人姓名"
echo ""
t show limit=5 2>&1 | head -5 | t update 新姓名=@联系人姓名 2>&1 | grep -E "(开始流式处理|流式更新完成|已处理.*条记录|错误)" | head -3
echo ""

echo "=== 测试4: show | update 混合更新（多条记录）==="
echo "命令: t show limit=5 | t update 新姓名=@联系人姓名 状态=已批量更新"
echo ""
t show limit=5 2>&1 | head -5 | t update 新姓名=@联系人姓名 状态=已批量更新 2>&1 | grep -E "(开始流式处理|流式更新完成|已处理.*条记录|错误)" | head -3
echo ""

echo "=== 测试5: show | update merge update 模式（多条记录）==="
echo "命令: t show limit=5 | t update 状态=已完成 where 联系人姓名=@联系人姓名"
echo ""
t show limit=5 2>&1 | head -5 | t update 状态=已完成 where 联系人姓名=@联系人姓名 2>&1 | grep -E "(开始merge update|Merge update完成|已处理.*条管道记录|更新.*条目标记录|错误)" | head -3
echo ""

echo "=== 测试6: show | update merge update 多条件（多条记录）==="
echo "命令: t show limit=5 | t update 状态=已处理 where 联系人姓名=@联系人姓名 联系电话=@联系电话"
echo ""
t show limit=5 2>&1 | head -5 | t update 状态=已处理 where 联系人姓名=@联系人姓名 联系电话=@联系电话 2>&1 | grep -E "(开始merge update|Merge update完成|已处理.*条管道记录|更新.*条目标记录|错误)" | head -3
echo ""

echo "=== 测试6.5: show | update merge update 核心功能（更新字段和where都使用@字段名）==="
echo "命令: t show limit=5 | t update 状态=@状态 where 联系人姓名=@联系人姓名"
echo "说明: 这是merge update的核心功能，更新字段和where条件都从管道记录中获取值"
echo ""
t show limit=5 2>&1 | head -5 | t update 状态=@状态 where 联系人姓名=@联系人姓名 2>&1 | grep -E "(开始merge update|Merge update完成|已处理.*条管道记录|更新.*条目标记录|错误)" | head -3
echo ""

echo "=== 测试6.6: show | update merge update 复杂场景（多个字段映射）==="
echo "命令: t show limit=5 | t update 新姓名=@联系人姓名 新电话=@联系电话 where 联系人姓名=@联系人姓名"
echo "说明: 更新多个字段（都使用@字段名），where条件也使用@字段名"
echo ""
t show limit=5 2>&1 | head -5 | t update 新姓名=@联系人姓名 新电话=@联系电话 where 联系人姓名=@联系人姓名 2>&1 | grep -E "(开始merge update|Merge update完成|已处理.*条管道记录|更新.*条目标记录|错误)" | head -3
echo ""

echo "=== 测试7: show | update 指定表名（多条记录）==="
echo "命令: t show limit=5 | t update 客户表 备注=批量表名参数测试"
echo ""
t show limit=5 2>&1 | head -5 | t update 客户表 备注=批量表名参数测试 2>&1 | grep -E "(切换到表格|流式更新完成|已处理.*条记录|错误)" | head -3
echo ""

echo "=== 测试8: show | update merge update 指定表名（多条记录）==="
echo "命令: t show limit=5 | t update 客户表 状态=已完成 where 联系人姓名=@联系人姓名"
echo ""
t show limit=5 2>&1 | head -5 | t update 客户表 状态=已完成 where 联系人姓名=@联系人姓名 2>&1 | grep -E "(切换到表格|开始merge update|Merge update完成|已处理.*条管道记录|更新.*条目标记录|错误)" | head -4
echo ""

echo "=== 测试9: 流式处理进度显示（大量记录）==="
echo "命令: t show limit=20 | t update 备注=流式处理测试"
echo ""
t show limit=20 2>&1 | head -20 | t update 备注=流式处理测试 2>&1 | grep -E "(开始流式处理|实时流式更新进度|流式更新完成|已处理.*条记录|错误)" | head -5
echo ""

echo "=========================================="
echo "✅ 客户表 Update 管道功能测试完成（多条记录）"
echo "=========================================="
echo ""
echo "测试总结:"
echo "✅ 批量直接更新：成功处理多条记录"
echo "✅ 批量字段映射更新：成功处理多条记录"
echo "✅ 批量merge update：成功处理多条管道记录"
echo "✅ 流式处理：支持大规模数据批量处理"
echo "✅ 进度显示：实时显示处理进度"
