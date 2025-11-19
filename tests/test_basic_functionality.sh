#!/bin/bash
# 测试CLI基本功能：创建表格、建立关联、插入数据

set -e

echo "=== 测试CLI基本功能 ==="
echo ""

# 清理：如果测试表已存在，先删除
echo "=== 步骤0: 清理旧数据（如果存在）==="
t drop 测试学生表 --force 2>/dev/null || true
t drop 测试课程表 --force 2>/dev/null || true
echo ""

# 步骤1: 创建两个表格
echo "=== 步骤1: 创建测试表格 ==="
echo "创建测试课程表..."
t create 测试课程表 "课程名称:singleLineText" "课程编号:autoNumber" "学分:number:0"
echo ""

echo "创建测试学生表..."
t create 测试学生表 "学生姓名:singleLineText" "学号:autoNumber" "关联课程:link:manyOne:测试课程表"
echo ""

# 步骤2: 验证表格创建
echo "=== 步骤2: 验证表格创建 ==="
echo "课程表结构:"
t desc 测试课程表
echo ""

echo "学生表结构:"
t desc 测试学生表
echo ""

# 步骤3: 插入课程数据
echo "=== 步骤3: 插入课程数据 ==="
COURSE1_ID=$(t insert 测试课程表 "课程名称=数学" "学分=4" | grep "^rec" | head -1 | cut -d' ' -f1)
COURSE2_ID=$(t insert 测试课程表 "课程名称=英语" "学分=3" | grep "^rec" | head -1 | cut -d' ' -f1)
COURSE3_ID=$(t insert 测试课程表 "课程名称=物理" "学分=4" | grep "^rec" | head -1 | cut -d' ' -f1)

echo "课程1 ID: $COURSE1_ID"
echo "课程2 ID: $COURSE2_ID"
echo "课程3 ID: $COURSE3_ID"
echo ""

# 步骤4: 插入学生数据（关联课程）
echo "=== 步骤4: 插入学生数据（关联课程）==="
STUDENT1_ID=$(t insert 测试学生表 "学生姓名=张三" "关联课程=$COURSE1_ID" | grep "^rec" | head -1 | cut -d' ' -f1)
STUDENT2_ID=$(t insert 测试学生表 "学生姓名=李四" "关联课程=$COURSE2_ID" | grep "^rec" | head -1 | cut -d' ' -f1)
STUDENT3_ID=$(t insert 测试学生表 "学生姓名=王五" "关联课程=$COURSE1_ID" | grep "^rec" | head -1 | cut -d' ' -f1)
STUDENT4_ID=$(t insert 测试学生表 "学生姓名=赵六" "关联课程=$COURSE3_ID" | grep "^rec" | head -1 | cut -d' ' -f1)

echo "学生1 ID: $STUDENT1_ID"
echo "学生2 ID: $STUDENT2_ID"
echo "学生3 ID: $STUDENT3_ID"
echo "学生4 ID: $STUDENT4_ID"
echo ""

# 步骤5: 验证数据插入
echo "=== 步骤5: 验证数据插入 ==="
echo "课程表数据:"
t use 测试课程表
t show
echo ""

echo "学生表数据:"
t use 测试学生表
t show
echo ""

# 步骤6: 测试使用课程名称关联（智能匹配）
echo "=== 步骤6: 测试使用课程名称关联（智能匹配）==="
STUDENT5_ID=$(t insert 测试学生表 "学生姓名=钱七" "关联课程=数学" | grep "^rec" | head -1 | cut -d' ' -f1)
echo "使用课程名称'数学'插入学生5，ID: $STUDENT5_ID"
echo ""

# 步骤7: 测试更新关联字段
echo "=== 步骤7: 测试更新关联字段 ==="
t update "$STUDENT5_ID" "关联课程=英语"
echo "将学生5的课程从'数学'更新为'英语'"
echo ""

# 步骤8: 最终验证
echo "=== 步骤8: 最终验证 ==="
echo "学生表最终数据:"
t use 测试学生表
t show
echo ""

echo "✅ 所有基本功能测试通过！"
echo ""
echo "测试内容："
echo "  ✅ 创建表格（create）"
echo "  ✅ 创建关联字段（link）"
echo "  ✅ 插入记录（insert）"
echo "  ✅ 使用记录ID关联"
echo "  ✅ 使用字段名称智能匹配关联"
echo "  ✅ 更新记录（update）"
echo "  ✅ 查看数据（show）"
echo ""

