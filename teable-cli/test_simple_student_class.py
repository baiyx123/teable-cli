#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的学生和班级关联字段测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teable_cli.teable_api_client import TeableClient
from teable_cli.commands.table import detect_link_fields, find_linked_record, interactive_select_linked_record


def test_simple_student_class():
    """使用现有的学生表和班级表进行测试"""
    print("=== 使用现有学生表和班级表测试关联字段 ===")
    
    # 配置
    BASE_URL = "https://app.teable.cn"
    TOKEN = "teable_acclJEk4pc3WDzywrRl_hcpXy3tSAJcTUStdGJz0uZT74rzpTOIA/wnbZeukdm4="
    BASE_ID = "bsewQso4GDsJoRyuFDA"
    
    # 创建客户端
    client = TeableClient(BASE_URL, TOKEN, BASE_ID)
    
    try:
        # 获取所有表格
        tables = client.get_tables()
        print(f"找到 {len(tables)} 个表格")
        
        # 查找学生表和班级表
        student_table = None
        class_table = None
        
        for table in tables:
            table_name = table.get('name', '')
            if '学生' in table_name or 'student' in table_name.lower():
                student_table = table
            elif '班级' in table_name or 'class' in table_name.lower():
                class_table = table
        
        if not student_table:
            print("❌ 未找到学生表")
            return
            
        if not class_table:
            print("❌ 未找到班级表")
            return
        
        student_table_id = student_table['id']
        class_table_id = class_table['id']
        
        print(f"✅ 找到学生表: {student_table.get('name')} (ID: {student_table_id})")
        print(f"✅ 找到班级表: {class_table.get('name')} (ID: {class_table_id})")
        
        # 检查是否已有关联字段
        student_fields = client.get_table_fields(student_table_id)
        class_fields = client.get_table_fields(class_table_id)
        
        # 查找关联字段
        student_link_field = None
        class_link_field = None
        
        for field in student_fields:
            if field.get('type') == 'link':
                options = field.get('options', {})
                if options.get('foreignTableId') == class_table_id:
                    student_link_field = field
                    break
        
        for field in class_fields:
            if field.get('type') == 'link':
                options = field.get('options', {})
                if options.get('foreignTableId') == student_table_id:
                    class_link_field = field
                    break
        
        if student_link_field:
            print(f"✅ 学生表中已有关联字段: {student_link_field.get('name')}")
        else:
            print("⚠️  学生表中未找到关联到班级的字段")
        
        if class_link_field:
            print(f"✅ 班级表中已有关联字段: {class_link_field.get('name')}")
        else:
            print("⚠️  班级表中未找到关联到学生的字段")
        
        # 获取现有数据
        print("\n=== 查询现有数据 ===")
        
        # 获取班级数据
        classes_data = client.get_records(class_table_id)
        classes = classes_data.get('records', [])
        print(f"班级表中有 {len(classes)} 条记录")
        
        # 获取学生数据
        students_data = client.get_records(student_table_id)
        students = students_data.get('records', [])
        print(f"学生表中有 {len(students)} 条记录")
        
        # 显示班级信息
        if classes:
            print("\n班级信息:")
            for i, class_record in enumerate(classes[:3]):  # 显示前3个班级
                class_fields = class_record.get('fields', {})
                # 尝试获取班级名称
                class_name = None
                for field_name, field_value in class_fields.items():
                    if field_value and isinstance(field_value, str) and ('班' in field_value or 'class' in field_value.lower()):
                        class_name = field_value
                        break
                if not class_name:
                    # 如果没有明显的班级名称，使用第一个非空字段
                    for field_name, field_value in class_fields.items():
                        if field_value and field_name not in ['id', 'createdTime', 'updatedTime']:
                            class_name = str(field_value)
                            break
                if not class_name:
                    class_name = f"班级{i+1}"
                
                print(f"  {i+1}. {class_name} (ID: {class_record.get('id', 'N/A')[:8]}...)")
        
        # 显示学生信息及关联
        if students:
            print("\n学生信息及关联班级:")
            for i, student in enumerate(students[:5]):  # 显示前5个学生
                student_fields = student.get('fields', {})
                
                # 获取学生姓名
                student_name = None
                for field_name, field_value in student_fields.items():
                    if field_value and isinstance(field_value, str) and len(field_value) <= 10:
                        if 'name' in field_name.lower() or '姓名' in field_name or student_name is None:
                            student_name = field_value
                            if 'name' in field_name.lower() or '姓名' in field_name:
                                break
                
                if not student_name:
                    student_name = f"学生{i+1}"
                
                # 获取关联的班级
                linked_class_name = None
                if student_link_field:
                    link_field_name = student_link_field.get('name')
                    class_id = student_fields.get(link_field_name)
                    if class_id:
                        try:
                            class_info = client.get_record(class_table_id, class_id)
                            if class_info:
                                class_fields = class_info.get('fields', {})
                                # 尝试找到班级名称
                                for field_name, field_value in class_fields.items():
                                    if field_value and isinstance(field_value, str) and ('班' in field_value or 'class' in field_value.lower()):
                                        linked_class_name = field_value
                                        break
                                if not linked_class_name:
                                    # 使用第一个非空字段
                                    for field_name, field_value in class_fields.items():
                                        if field_value and field_name not in ['id', 'createdTime', 'updatedTime']:
                                            linked_class_name = str(field_value)
                                            break
                        except Exception as e:
                            print(f"   ⚠️  获取关联班级信息失败: {e}")
                
                print(f"  {i+1}. {student_name}", end="")
                if linked_class_name:
                    print(f" -> {linked_class_name}")
                else:
                    print(" -> 未关联班级")
        
        # 测试关联字段功能
        print("\n=== 测试关联字段功能 ===")
        
        # 测试通过学生姓名查找关联班级
        if students and student_link_field and classes:
            test_student = students[0]
            test_student_fields = test_student.get('fields', {})
            test_student_name = None
            
            # 获取学生姓名
            for field_name, field_value in test_student_fields.items():
                if field_value and isinstance(field_value, str) and len(field_value) <= 10:
                    if 'name' in field_name.lower() or '姓名' in field_name or test_student_name is None:
                        test_student_name = field_value
                        if 'name' in field_name.lower() or '姓名' in field_name:
                            break
            
            if test_student_name:
                print(f"测试学生 '{test_student_name}' 的关联班级:")
                link_field_name = student_link_field.get('name')
                class_id = test_student_fields.get(link_field_name)
                if class_id:
                    try:
                        class_info = client.get_record(class_table_id, class_id)
                        if class_info:
                            class_fields = class_info.get('fields', {})
                            # 显示班级关键信息
                            print("   关联班级信息:")
                            for field_name, field_value in class_fields.items():
                                if field_value and field_name not in ['id', 'createdTime', 'updatedTime']:
                                    print(f"     {field_name}: {field_value}")
                        else:
                            print("   未找到关联的班级")
                    except Exception as e:
                        print(f"   ⚠️  获取关联班级失败: {e}")
                else:
                    print("   该学生未关联班级")
        
        # 测试通过班级查找学生
        if classes and student_link_field and students:
            test_class = classes[0]
            test_class_fields = test_class.get('fields', {})
            test_class_name = None
            
            # 获取班级名称
            for field_name, field_value in test_class_fields.items():
                if field_value and isinstance(field_value, str):
                    if '班' in field_value or 'class' in field_value.lower() or test_class_name is None:
                        test_class_name = field_value
                        if '班' in field_value or 'class' in field_value.lower():
                            break
            
            if test_class_name:
                print(f"\n测试班级 '{test_class_name}' 的学生:")
                class_id = test_class.get('id')
                
                # 查找该班级的所有学生
                students_in_class = []
                for student in students:
                    student_fields = student.get('fields', {})
                    student_class_id = student_fields.get(student_link_field.get('name'), '')
                    if student_class_id == class_id:
                        student_name = None
                        for field_name, field_value in student_fields.items():
                            if field_value and isinstance(field_value, str) and len(field_value) <= 10:
                                if 'name' in field_name.lower() or '姓名' in field_name or student_name is None:
                                    student_name = field_value
                                    if 'name' in field_name.lower() or '姓名' in field_name:
                                        break
                        if student_name:
                            students_in_class.append(student_name)
                        else:
                            students_in_class.append(f"学生{len(students_in_class)+1}")
                
                if students_in_class:
                    print(f"   学生列表: {', '.join(students_in_class)}")
                else:
                    print("   暂无学生")
        
        print("\n✅ 关联字段功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试关联字段功能失败: {e}")


if __name__ == "__main__":
    test_simple_student_class()
