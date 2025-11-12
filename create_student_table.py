#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建学生表演示脚本
基于 teable_api_client.py 的示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from teable_api_client import TeableClient, create_field_config, create_record_data

def main():
    # 配置参数（使用示例中的配置）
    BASE_URL = "https://app.teable.cn"
    TOKEN = "teable_acclJEk4pc3WDzywrRl_hcpXy3tSAJcTUStdGJz0uZT74rzpTOIA/wnbZeukdm4="
    BASE_ID = "bsewQso4GDsJoRyuFDA"
    
    # 创建客户端
    client = TeableClient(BASE_URL, TOKEN, BASE_ID)
    
    try:
        print("=== 创建学生表 ===")
        
        # 创建学生表配置
        student_table_config = {
            "name": "学生表",
            "description": "学生信息管理表",
            "fields": [
                create_field_config("学号", "singleLineText"),
                create_field_config("姓名", "singleLineText"),
                create_field_config("年龄", "number"),
                create_field_config("性别", "singleSelect", options={
                    "choices": [
                        {"name": "男", "color": "blue"},
                        {"name": "女", "color": "pink"}
                    ]
                }),
                create_field_config("班级", "singleLineText"),
                create_field_config("成绩", "number"),
                create_field_config("入学日期", "date"),
                create_field_config("邮箱", "singleLineText"),
                create_field_config("电话", "singleLineText"),
                create_field_config("备注", "longText")
            ]
        }
        
        # 创建表格
        created_table = client.create_table(student_table_config)
        table_id = created_table["id"]
        print(f"✅ 学生表创建成功，ID: {table_id}")
        
        print("\n=== 插入学生数据 ===")
        
        # 准备学生数据
        student_records = [
            create_record_data({
                "学号": "2024001",
                "姓名": "张三",
                "年龄": 18,
                "性别": "男",
                "班级": "计算机1班",
                "成绩": 85,
                "入学日期": "2024-09-01",
                "邮箱": "zhangsan@example.com",
                "电话": "13800138001",
                "备注": "学习认真，表现优秀"
            }),
            create_record_data({
                "学号": "2024002", 
                "姓名": "李四",
                "年龄": 19,
                "性别": "女",
                "班级": "计算机1班",
                "成绩": 92,
                "入学日期": "2024-09-01",
                "邮箱": "lisi@example.com",
                "电话": "13800138002",
                "备注": "成绩优异，积极参与活动"
            }),
            create_record_data({
                "学号": "2024003",
                "姓名": "王五",
                "年龄": 18,
                "性别": "男", 
                "班级": "计算机2班",
                "成绩": 78,
                "入学日期": "2024-09-01",
                "邮箱": "wangwu@example.com",
                "电话": "13800138003",
                "备注": "需要加强数学基础"
            }),
            create_record_data({
                "学号": "2024004",
                "姓名": "赵六",
                "年龄": 20,
                "性别": "女",
                "班级": "计算机2班", 
                "成绩": 88,
                "入学日期": "2024-09-01",
                "邮箱": "zhaoliu@example.com",
                "电话": "13800138004",
                "备注": "文艺骨干，组织能力强"
            }),
            create_record_data({
                "学号": "2024005",
                "姓名": "孙七",
                "年龄": 19,
                "性别": "男",
                "班级": "计算机1班",
                "成绩": 95,
                "入学日期": "2024-09-01",
                "邮箱": "sunqi@example.com", 
                "电话": "13800138005",
                "备注": "班级第一名，编程能力突出"
            })
        ]
        
        # 插入记录
        inserted_records = client.insert_records(table_id, student_records)
        print(f"✅ 成功插入 {len(inserted_records.get('records', []))} 条学生记录")
        
        print("\n=== 查询学生数据 ===")
        
        # 查询记录
        all_students = client.get_records(table_id)
        students = all_students.get('records', [])
        print(f"📊 查询到 {len(students)} 条学生记录")
        
        # 显示部分数据
        print("\n前3条学生记录:")
        for i, student in enumerate(students[:3]):
            fields = student.get('fields', {})
            print(f"{i+1}. {fields.get('姓名', 'N/A')} - 学号: {fields.get('学号', 'N/A')} - "
                  f"班级: {fields.get('班级', 'N/A')} - 成绩: {fields.get('成绩', 'N/A')}")
        
        print(f"\n🎉 学生表创建和数据插入完成！")
        print(f"表格ID: {table_id}")
        print(f"总记录数: {len(students)}")
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✨ 所有操作执行成功！")
    else:
        print("\n💥 操作执行失败！")
        sys.exit(1)
