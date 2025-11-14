#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试学生和班级关联字段的完整示例
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teable_cli.teable_api_client import TeableClient, create_field_config, create_link_field_config, create_record_data


def setup_test_environment():
    """设置测试环境 - 创建学生和班级表格"""
    print("=== 设置测试环境 ===")
    
    # 配置
    BASE_URL = "https://app.teable.cn"
    TOKEN = "teable_acclJEk4pc3WDzywrRl_hcpXy3tSAJcTUStdGJz0uZT74rzpTOIA/wnbZeukdm4="
    BASE_ID = "bsewQso4GDsJoRyuFDA"
    
    # 创建客户端
    client = TeableClient(BASE_URL, TOKEN, BASE_ID)
    
    try:
        # 1. 创建班级表
        class_table_config = {
            "name": "测试班级表",
            "description": "用于测试关联字段的班级表",
            "fields": [
                create_field_config("班级名称", "singleLineText"),
                create_field_config("班级编号", "singleLineText"),
                create_field_config("班主任", "singleLineText"),
                create_field_config("教室", "singleLineText")
            ]
        }
        
        created_class_table = client.create_table(class_table_config)
        class_table_id = created_class_table["id"]
        print(f"✅ 班级表创建成功，ID: {class_table_id}")
        
        # 2. 创建学生表
        student_table_config = {
            "name": "测试学生表",
            "description": "用于测试关联字段的学生表",
            "fields": [
                create_field_config("学生姓名", "singleLineText"),
                create_field_config("学号", "singleLineText"),
                create_field_config("年龄", "number"),
                create_field_config("性别", "singleLineText")
            ]
        }
        
        created_student_table = client.create_table(student_table_config)
        student_table_id = created_student_table["id"]
        print(f"✅ 学生表创建成功，ID: {student_table_id}")
        
        # 3. 在学生表中添加关联到班级表的字段
        link_field = create_link_field_config("所属班级", "manyOne", class_table_id)
        added_field = client.add_field(student_table_id, link_field)
        print(f"✅ 关联字段添加成功，字段ID: {added_field.get('id')}")
        
        # 4. 在班级表中添加关联到学生表的字段（反向关联）
        reverse_link_field = create_link_field_config("学生", "oneMany", student_table_id)
        reverse_added_field = client.add_field(class_table_id, reverse_link_field)
        print(f"✅ 反向关联字段添加成功，字段ID: {reverse_added_field.get('id')}")
        
        return client, class_table_id, student_table_id
        
    except Exception as e:
        print(f"❌ 设置测试环境失败: {e}")
        return None, None, None


def insert_test_data(client, class_table_id, student_table_id):
    """插入测试数据"""
    print("\n=== 插入测试数据 ===")
    
    try:
        # 1. 先插入班级数据
        class_records = [
            create_record_data({
                "班级名称": "高一(1)班",
                "班级编号": "G101",
                "班主任": "张老师",
                "教室": "教学楼101"
            }),
            create_record_data({
                "班级名称": "高一(2)班", 
                "班级编号": "G102",
                "班主任": "李老师",
                "教室": "教学楼102"
            }),
            create_record_data({
                "班级名称": "高二(1)班",
                "班级编号": "G201", 
                "班主任": "王老师",
                "教室": "教学楼201"
            })
        ]
        
        inserted_classes = client.insert_records(class_table_id, class_records)
        class_records_data = inserted_classes.get('records', [])
        print(f"✅ 班级数据插入成功，共 {len(class_records_data)} 条记录")
        
        # 获取班级记录用于关联
        all_classes = client.get_records(class_table_id)
        class_list = all_classes.get('records', [])
        
        # 2. 插入学生数据（使用记录ID进行关联）
        student_records = [
            create_record_data({
                "学生姓名": "张三",
                "学号": "S001",
                "年龄": 16,
                "性别": "男",
                "所属班级": class_list[0]['id']  # 关联到高一(1)班
            }),
            create_record_data({
                "学生姓名": "李四",
                "学号": "S002", 
                "年龄": 17,
                "性别": "女",
                "所属班级": class_list[0]['id']  # 关联到高一(1)班
            }),
            create_record_data({
                "学生姓名": "王五",
                "学号": "S003",
                "年龄": 16, 
                "性别": "男",
                "所属班级": class_list[1]['id']  # 关联到高一(2)班
            })
        ]
        
        inserted_students = client.insert_records(student_table_id, student_records)
        student_records_data = inserted_students.get('records', [])
        print(f"✅ 学生数据插入成功，共 {len(student_records_data)} 条记录")
        
        return class_list, student_records_data
        
    except Exception as e:
        print(f"❌ 插入测试数据失败: {e}")
        return [], []


def test_link_field_functionality(client, student_table_id, class_table_id, class_list, student_list):
    """测试关联字段功能"""
    print("\n=== 测试关联字段功能 ===")
    
    try:
        # 1. 测试通过学生姓名查找班级
        print("1. 测试通过学生姓名查找班级关联:")
        
        # 获取学生表字段
        student_fields = client.get_table_fields(student_table_id)
        link_fields = {}
        for field in student_fields:
            if field.get('type') == 'link':
                field_name = field.get('name')
                options = field.get('options', {})
                link_fields[field_name] = {
                    'foreign_table_id': options.get('foreignTableId'),
                    'relationship': options.get('relationship')
                }
        
        print(f"   发现的关联字段: {list(link_fields.keys())}")
        
        # 2. 测试查询学生数据并显示关联的班级信息
        print("\n2. 查询学生数据及关联班级:")
        students_data = client.get_records(student_table_id)
        students = students_data.get('records', [])
        
        for student in students:
            student_fields = student.get('fields', {})
            student_name = student_fields.get('学生姓名', '未知')
            class_id = student_fields.get('所属班级', '')
            
            print(f"   学生: {student_name}")
            if class_id:
                # 获取关联的班级信息
                class_info = client.get_record(class_table_id, class_id)
                if class_info:
                    class_fields = class_info.get('fields', {})
                    class_name = class_fields.get('班级名称', '未知班级')
                    print(f"   -> 所属班级: {class_name}")
                else:
                    print(f"   -> 未找到关联班级")
            else:
                print(f"   -> 未关联班级")
        
        # 3. 测试通过班级名称查找学生
        print("\n3. 测试通过班级名称查找学生:")
        for class_record in class_list:
            class_fields = class_record.get('fields', {})
            class_name = class_fields.get('班级名称', '未知班级')
            class_id = class_record.get('id')
            
            print(f"   班级: {class_name}")
            
            # 查找该班级的所有学生
            students_in_class = []
            for student in students:
                student_fields = student.get('fields', {})
                student_class_id = student_fields.get('所属班级', '')
                if student_class_id == class_id:
                    students_in_class.append(student_fields.get('学生姓名', '未知学生'))
            
            if students_in_class:
                print(f"   -> 学生列表: {', '.join(students_in_class)}")
            else:
                print(f"   -> 暂无学生")
        
        print("\n✅ 关联字段功能测试完成")
        
    except Exception as e:
        print(f"❌ 测试关联字段功能失败: {e}")


def cleanup_test_data(client, class_table_id, student_table_id):
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    try:
        # 删除学生表记录
        students_data = client.get_records(student_table_id)
        students = students_data.get('records', [])
        
        for student in students:
            student_id = student.get('id')
            if student_id:
                client.delete_record(student_table_id, student_id)
        
        print(f"✅ 已删除 {len(students)} 条学生记录")
        
        # 删除班级表记录
        classes_data = client.get_records(class_table_id)
        classes = classes_data.get('records', [])
        
        for class_record in classes:
            class_id = class_record.get('id')
            if class_id:
                client.delete_record(class_table_id, class_id)
        
        print(f"✅ 已删除 {len(classes)} 条班级记录")
        
    except Exception as e:
        print(f"⚠️  清理测试数据时出错: {e}")


def main():
    """主函数"""
    print("开始测试学生和班级关联字段功能...")
    
    # 设置测试环境
    client, class_table_id, student_table_id = setup_test_environment()
    
    if not client:
        print("❌ 无法设置测试环境，测试终止")
        return
    
    try:
        # 插入测试数据
        class_list, student_list = insert_test_data(client, class_table_id, student_table_id)
        
        if not class_list or not student_list:
            print("❌ 无法插入测试数据，测试终止")
            return
        
        # 测试关联字段功能
        test_link_field_functionality(client, student_table_id, class_table_id, class_list, student_list)
        
        # 询问是否清理测试数据
        cleanup = input("\n是否清理测试数据？(y/N): ").strip().lower()
        if cleanup in ['y', 'yes', '是']:
            cleanup_test_data(client, class_table_id, student_table_id)
        
        print("\n🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")


if __name__ == "__main__":
    main()
