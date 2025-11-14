#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移命令
用于将一张表的数据循环插入到另一张表
"""

import sys
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def migrate_data(client, session, args: list):
    """迁移数据命令"""
    try:
        if not client:
            print("错误: 无法连接到Teable服务")
            return 1
        
        if len(args) < 2:
            print("错误: 参数不足")
            print("使用: t migrate 源表名 目标表名 [字段映射...]")
            print("示例: t migrate 学生表 学生备份表 姓名=姓名 年龄=年龄 成绩=成绩")
            print("示例: t migrate 学生表 优秀学生表 成绩>80")  # 带条件迁移
            return 1
        
        source_table = args[0]
        target_table = args[1]
        
        # 解析字段映射或条件
        field_mappings = {}
        condition = None
        
        for arg in args[2:]:
            if '=' in arg:
                # 字段映射: 源字段=目标字段
                source_field, target_field = arg.split('=', 1)
                field_mappings[source_field.strip()] = target_field.strip()
            elif '>' in arg or '<' in arg or '=' in arg:
                # 条件: 成绩>80
                condition = arg
            else:
                print(f"警告: 忽略无效参数 '{arg}'")
        
        print(f"📊 开始数据迁移:")
        print(f"   源表: {source_table}")
        print(f"   目标表: {target_table}")
        if field_mappings:
            print(f"   字段映射: {field_mappings}")
        if condition:
            print(f"   条件: {condition}")
        
        # 获取源表数据
        tables = client.get_tables()
        source_table_info = None
        target_table_info = None
        
        for table in tables:
            if table.get('name') == source_table:
                source_table_info = table
            elif table.get('name') == target_table:
                target_table_info = table
        
        if not source_table_info:
            print(f"错误: 找不到源表 '{source_table}'")
            return 1
        
        if not target_table_info:
            print(f"错误: 找不到目标表 '{target_table}'")
            return 1
        
        source_table_id = source_table_info['id']
        target_table_id = target_table_info['id']
        
        # 获取源表记录
        query_params = {}
        if condition:
            # 解析条件
            if '>' in condition:
                field, value = condition.split('>', 1)
                query_params['filter'] = json.dumps({
                    "conjunction": "and",
                    "filterSet": [{
                        "fieldId": field.strip(),
                        "operator": "isGreater",
                        "value": value.strip()
                    }]
                })
            elif '<' in condition:
                field, value = condition.split('<', 1)
                query_params['filter'] = json.dumps({
                    "conjunction": "and",
                    "filterSet": [{
                        "fieldId": field.strip(),
                        "operator": "isLess",
                        "value": value.strip()
                    }]
                })
            elif '=' in condition:
                field, value = condition.split('=', 1)
                query_params['filter'] = json.dumps({
                    "conjunction": "and",
                    "filterSet": [{
                        "fieldId": field.strip(),
                        "operator": "is",
                        "value": value.strip()
                    }]
                })
        
        # 获取所有记录（分页处理）
        all_records = []
        page = 1
        page_size = 100
        
        while True:
            records_data = client.get_records(source_table_id, page=page, page_size=page_size, **query_params)
            records = records_data.get('records', [])
            
            if not records:
                break
            
            all_records.extend(records)
            
            if len(records) < page_size:
                break
            
            page += 1
        
        if not all_records:
            print(f"源表 '{source_table}' 中没有符合条件的记录")
            return 0
        
        print(f"📋 找到 {len(all_records)} 条记录需要迁移")
        
        # 获取目标表字段信息
        target_fields = client.get_table_fields(target_table_id)
        target_field_names = [field.get('name') for field in target_fields]
        
        # 准备要插入的记录
        records_to_insert = []
        skipped_records = 0
        
        for i, record in enumerate(all_records):
            source_fields = record.get('fields', {})
            
            # 如果没有指定字段映射，尝试自动映射同名字段
            if not field_mappings:
                # 自动映射同名字段
                target_data = {}
                for field_name, value in source_fields.items():
                    if field_name in target_field_names:
                        target_data[field_name] = value
            else:
                # 使用指定的字段映射
                target_data = {}
                for source_field, target_field in field_mappings.items():
                    if source_field in source_fields:
                        target_data[target_field] = source_fields[source_field]
            
            if target_data:
                records_to_insert.append({
                    "fields": target_data
                })
            else:
                skipped_records += 1
                logger.warning(f"跳过记录 {i+1}: 没有有效的字段数据")
        
        if not records_to_insert:
            print("错误: 没有有效的记录可以迁移")
            return 1
        
        # 批量插入记录
        print(f"🔄 开始插入 {len(records_to_insert)} 条记录到目标表...")
        
        success_count = 0
        failed_count = 0
        batch_size = 10  # 每批插入10条记录
        
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i+batch_size]
            
            try:
                result = client.insert_records(target_table_id, batch)
                inserted_records = result.get('records', [])
                success_count += len(inserted_records)
                
                if len(inserted_records) < len(batch):
                    failed_count += len(batch) - len(inserted_records)
                
                print(f"   已处理 {min(i+batch_size, len(records_to_insert))}/{len(records_to_insert)} 条记录")
                
            except Exception as e:
                failed_count += len(batch)
                logger.error(f"批量插入失败: {e}")
        
        # 显示结果
        print(f"\n✅ 数据迁移完成!")
        print(f"   成功: {success_count} 条记录")
        print(f"   失败: {failed_count} 条记录")
        print(f"   跳过: {skipped_records} 条记录")
        
        if failed_count > 0:
            return 1
        
        return 0
        
    except Exception as e:
        print(f"错误: 数据迁移失败: {e}")
        logger.error(f"数据迁移失败: {e}", exc_info=True)
        return 1


def copy_table_structure(client, session, args: list):
    """复制表结构命令"""
    try:
        if len(args) < 2:
            print("错误: 参数不足")
            print("使用: t copy-structure 源表名 新表名 [描述]")
            return 1
        
        source_table = args[0]
        new_table_name = args[1]
        description = args[2] if len(args) > 2 else f"从 {source_table} 复制的表"
        
        print(f"📋 复制表结构:")
        print(f"   源表: {source_table}")
        print(f"   新表名: {new_table_name}")
        print(f"   描述: {description}")
        
        # 获取源表信息
        tables = client.get_tables()
        source_table_info = None
        
        for table in tables:
            if table.get('name') == source_table:
                source_table_info = table
                break
        
        if not source_table_info:
            print(f"错误: 找不到源表 '{source_table}'")
            return 1
        
        source_table_id = source_table_info['id']
        
        # 获取源表字段
        source_fields = client.get_table_fields(source_table_id)
        
        # 准备新表配置
        field_configs = []
        for field in source_fields:
            field_name = field.get('name')
            field_type = field.get('type')
            
            # 跳过系统字段
            if field_type in ['autoNumber', 'createdTime', 'lastModifiedTime', 'createdBy', 'lastModifiedBy']:
                continue
            
            field_config = {
                "name": field_name,
                "type": field_type
            }
            
            # 复制字段选项（如果有）
            if 'options' in field:
                field_config['options'] = field['options']
            
            field_configs.append(field_config)
        
        # 创建新表
        new_table_config = {
            "name": new_table_name,
            "description": description,
            "fields": field_configs
        }
        
        result = client.create_table(new_table_config)
        
        if result:
            print(f"✅ 表结构复制成功!")
            print(f"   新表ID: {result.get('id')}")
            return 0
        else:
            print("❌ 表结构复制失败")
            return 1
            
    except Exception as e:
        print(f"错误: 表结构复制失败: {e}")
        return 1
