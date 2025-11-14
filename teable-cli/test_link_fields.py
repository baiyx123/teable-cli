#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试关联字段功能的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teable_cli.teable_api_client import TeableClient
from teable_cli.commands.table import detect_link_fields, find_linked_record, interactive_select_linked_record


def test_link_field_detection():
    """测试关联字段检测功能"""
    print("=== 测试关联字段检测 ===")
    
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
        
        for table in tables:
            table_id = table['id']
            table_name = table['name']
            print(f"\n--- 表格: {table_name} (ID: {table_id}) ---")
            
            # 检测关联字段
            link_fields = detect_link_fields(client, table_id)
            if link_fields:
                print("关联字段:")
                for field_name, link_info in link_fields.items():
                    print(f"  - {field_name}: 外键表ID={link_info['foreign_table_id']}, 关系={link_info['relationship']}")
            else:
                print("无关联字段")
                
    except Exception as e:
        print(f"测试失败: {e}")


def test_find_linked_record():
    """测试关联记录查找功能"""
    print("\n=== 测试关联记录查找 ===")
    
    # 配置
    BASE_URL = "https://app.teable.cn/api"
    TOKEN = "teable_acclJEk4pc3WDzywrRl_hcpXy3tSAJcTUStdGJz0uZT74rzpTOIA/wnbZeukdm4="
    BASE_ID = "bsewQso4GDsJoRyuFDA"
    
    # 创建客户端
    client = TeableClient(BASE_URL, TOKEN, BASE_ID)
    
    try:
        # 获取所有表格
        tables = client.get_tables()
        
        if len(tables) >= 2:
            # 使用第二个表格作为外键表进行测试
            foreign_table = tables[1]
            foreign_table_id = foreign_table['id']
            foreign_table_name = foreign_table['name']
            
            print(f"使用表格 '{foreign_table_name}' 作为外键表进行测试")
            
            # 获取一些记录用于测试
            records_data = client.get_records(foreign_table_id, take=5)
            records = records_data.get('records', [])
            
            if records:
                # 使用第一个记录进行测试
                test_record = records[0]
                record_id = test_record['id']
                
                print(f"测试记录ID查找: {record_id}")
                result = find_linked_record(client, foreign_table_id, record_id)
                
                if result:
                    print(f"✅ 找到记录: {result.get('id')}")
                    # 尝试获取显示字段
                    fields = result.get('fields', {})
                    display_value = None
                    for field_name in ['name', 'title']:
                        if field_name in fields and fields[field_name]:
                            display_value = fields[field_name]
                            break
                    if display_value:
                        print(f"   显示值: {display_value}")
                else:
                    print("❌ 未找到记录")
                
                # 测试模糊查找
                if fields:
                    # 尝试使用第一个字段的值进行模糊查找
                    for field_name, field_value in fields.items():
                        if field_value and isinstance(field_value, str) and len(field_value) > 2:
                            print(f"\n测试模糊查找: '{field_value[:3]}'")
                            result = find_linked_record(client, foreign_table_id, field_value[:3])
                            
                            if result:
                                if isinstance(result, list):
                                    print(f"✅ 找到 {len(result)} 个匹配记录")
                                else:
                                    print(f"✅ 找到记录: {result.get('id')}")
                            else:
                                print("❌ 未找到匹配记录")
                            break
            else:
                print("外键表中没有记录可用于测试")
        else:
            print("需要至少2个表格来测试关联功能")
            
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    print("开始测试关联字段功能...")
    test_link_field_detection()
    test_find_linked_record()
    print("\n测试完成！")
