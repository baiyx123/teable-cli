#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格操作命令
"""

import sys
import json
from typing import Optional
from tabulate import tabulate
from rich.console import Console
from rich.table import Table


console = Console()


def list_tables(client, verbose: bool = False):
    """列出所有表格"""
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    try:
        tables = client.get_tables()
        
        if not tables:
            print("没有找到表格")
            return 0
        
        if verbose:
            # 详细信息模式
            headers = ["表格名称", "表格ID", "描述", "创建时间"]
            rows = []
            
            for table in tables:
                table_info = client.get_table_details(table['id'])
                rows.append([
                    table.get('name', 'N/A'),
                    table.get('id', 'N/A')[:8] + '...',
                    table_info.get('description', '无描述')[:30],
                    table.get('createdTime', 'N/A')[:10]
                ])
            
            print(tabulate(rows, headers=headers, tablefmt='simple'))
        else:
            # 简洁模式
            table_names = [table.get('name', 'N/A') for table in tables]
            print("可用表格:")
            for name in table_names:
                print(f"  {name}")
        
        return 0
        
    except Exception as e:
        print(f"错误: 获取表格列表失败: {e}")
        return 1


def insert_record(client, session, args: list):
    """插入记录"""
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        
        if not args:
            # 交互式模式
            print(f"向表格 '{table_name}' 插入记录:")
            record_data = {}
            
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'singleLineText')
                
                # 跳过系统字段
                if field_name in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                    continue
                
                value = input(f"{field_name} ({field_type}): ").strip()
                if value:
                    # 根据字段类型转换值
                    if field_type in ['number', 'percent']:
                        try:
                            value = float(value)
                        except ValueError:
                            print(f"警告: {field_name} 需要数字，使用文本值")
                    elif field_type == 'checkbox':
                        value = value.lower() in ['true', '1', 'yes', '是']
                    elif field_type == 'multipleSelect':
                        value = [v.strip() for v in value.split(',')]
                    
                    record_data[field_name] = value
            
            if not record_data:
                print("没有输入任何数据，取消插入")
                return 0
        else:
            # 命令行参数模式
            # 格式: field1=value1 field2=value2
            record_data = {}
            for arg in args:
                if '=' in arg:
                    field_name, value = arg.split('=', 1)
                    record_data[field_name] = value
        
        # 插入记录
        result = client.create_record(table_id, record_data)
        
        if result:
            print(f"✅ 成功插入记录，ID: {result.get('id', 'N/A')}")
            return 0
        else:
            print("❌ 插入记录失败")
            return 1
            
    except Exception as e:
        print(f"错误: 插入记录失败: {e}")
        return 1


def update_record(client, session, args: list):
    """更新记录"""
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        if not args:
            print("错误: 请指定记录ID")
            print("使用: t update 记录ID [字段1=值1 字段2=值2 ...]")
            return 1
        
        record_id = args[0]
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        field_names = [f.get('name', '') for f in fields]
        
        if len(args) == 1:
            # 交互式模式
            print(f"更新表格 '{table_name}' 的记录 {record_id}:")
            
            # 先显示当前记录
            current_record = client.get_record(table_id, record_id)
            if not current_record:
                print(f"错误: 找不到记录 {record_id}")
                return 1
            
            current_fields = current_record.get('fields', {})
            
            update_data = {}
            for field in fields:
                field_name = field.get('name', '')
                
                # 跳过系统字段
                if field_name in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                    continue
                
                current_value = current_fields.get(field_name, '')
                new_value = input(f"{field_name} (当前: {current_value}): ").strip()
                
                if new_value and new_value != str(current_value):
                    # 根据字段类型转换值
                    field_type = field.get('type', 'singleLineText')
                    if field_type in ['number', 'percent']:
                        try:
                            new_value = float(new_value)
                        except ValueError:
                            print(f"警告: {field_name} 需要数字，使用文本值")
                    elif field_type == 'checkbox':
                        new_value = new_value.lower() in ['true', '1', 'yes', '是']
                    elif field_type == 'multipleSelect':
                        new_value = [v.strip() for v in new_value.split(',')]
                    
                    update_data[field_name] = new_value
            
            if not update_data:
                print("没有数据需要更新")
                return 0
        else:
            # 命令行参数模式
            # 格式: record_id field1=value1 field2=value2
            update_data = {}
            for arg in args[1:]:
                if '=' in arg:
                    field_name, value = arg.split('=', 1)
                    if field_name in field_names:
                        update_data[field_name] = value
                    else:
                        print(f"警告: 字段 '{field_name}' 不存在，跳过")
        
        if not update_data:
            print("没有数据需要更新")
            return 0
        
        # 更新记录
        result = client.update_record(table_id, record_id, update_data)
        
        if result:
            print(f"✅ 成功更新记录 {record_id}")
            return 0
        else:
            print(f"❌ 更新记录 {record_id} 失败")
            return 1
            
    except Exception as e:
        print(f"错误: 更新记录失败: {e}")
        return 1


def delete_record(client, session, args: list):
    """删除记录"""
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        if not args:
            print("错误: 请指定要删除的记录ID")
            print("使用: t delete 记录ID1 [记录ID2 ...]")
            return 1
        
        # 确认删除
        confirm = input(f"确定要删除 {len(args)} 条记录吗？ (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("取消删除操作")
            return 0
        
        success_count = 0
        failed_records = []
        
        for record_id in args:
            try:
                result = client.delete_record(table_id, record_id)
                if result:
                    success_count += 1
                    print(f"✅ 已删除记录 {record_id}")
                else:
                    failed_records.append(record_id)
                    print(f"❌ 删除记录 {record_id} 失败")
            except Exception as e:
                failed_records.append(record_id)
                print(f"❌ 删除记录 {record_id} 失败: {e}")
        
        print(f"\n📊 删除完成: 成功 {success_count} 条，失败 {len(failed_records)} 条")
        
        if failed_records:
            print(f"失败的记录ID: {', '.join(failed_records)}")
            return 1
        
        return 0
            
    except Exception as e:
        print(f"错误: 删除记录失败: {e}")
        return 1


def use_table(client, session, table_name: str):
    """切换到指定表格"""
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    try:
        # 获取所有表格
        tables = client.get_tables()
        
        # 查找匹配的表格
        found_table = None
        for table in tables:
            if table.get('name') == table_name:
                found_table = table
                break
        
        if not found_table:
            print(f"错误: 找不到表格 '{table_name}'")
            print("可用表格:")
            for table in tables:
                print(f"  {table.get('name', 'N/A')}")
            return 1
        
        # 设置当前表格
        session.set_current_table(table_name, found_table['id'])
        
        # 缓存表格信息
        table_details = client.get_table_details(found_table['id'])
        session.cache_table_info(table_name, table_details)
        
        print(f"✅ 已切换到表格: {table_name}")
        print(f"   表格ID: {found_table['id']}")
        
        if table_details.get('description'):
            print(f"   描述: {table_details['description']}")
        
        return 0
        
    except Exception as e:
        print(f"错误: 切换表格失败: {e}")
        return 1


def show_current_table(client, session, args: list):
    """显示当前表格数据"""
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        return 1
    
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        # 解析参数
        limit = 20  # 默认显示20条
        verbose = '-v' in args or '--verbose' in args
        where_conditions = {}
        order_by = None
        order_direction = 'asc'
        
        # 获取字段名到ID的映射
        fields = client.get_table_fields(table_id)
        field_name_to_id = {field.get('name'): field.get('id') for field in fields}
        
        # 解析查询条件参数 - 支持 key=value 格式
        for arg in args:
            # 先处理特殊的系统参数
            if arg.startswith('limit='):
                try:
                    limit = int(arg.split('=', 1)[1])
                except ValueError:
                    print(f"警告: 无效的limit值 '{arg}'，使用默认值")
            elif arg.startswith('order='):
                order_spec = arg.split('=', 1)[1]
                if ':' in order_spec:
                    order_by_name, order_direction = order_spec.split(':', 1)
                    order_direction = order_direction.lower()
                    if order_direction not in ['asc', 'desc']:
                        order_direction = 'asc'
                    # 直接使用字段名，不转换为字段ID
                    order_by = order_by_name
                else:
                    order_by = order_spec
            else:
                # 处理where条件 - 支持 field=value, field>value, field<value 等格式
                condition = arg
                
                # 先检查like操作符（模糊查询）
                if 'like' in condition:
                    field_name, value = condition.split('like', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    where_conditions[f"{field_name}__like"] = value
                # 先检查比较操作符（优先级高于等于）
                elif '>=' in condition:
                    field_name, value = condition.split('>=', 1)
                    field_id = field_name_to_id.get(field_name, field_name)
                    where_conditions[f"{field_id}__gte"] = value
                elif '<=' in condition:
                    field_name, value = condition.split('<=', 1)
                    field_id = field_name_to_id.get(field_name, field_name)
                    where_conditions[f"{field_id}__lte"] = value
                elif '>' in condition:
                    field_name, value = condition.split('>', 1)
                    where_conditions[f"{field_name}__gt"] = value
                elif '<' in condition:
                    field_name, value = condition.split('<', 1)
                    where_conditions[f"{field_name}__lt"] = value
                elif '=' in condition:
                    # 纯等于条件 - 精确匹配
                    field_name, value = condition.split('=', 1)
                    where_conditions[f"{field_name}__eq"] = value
        
        # 构建查询参数 - 使用Teable API正确的格式
        query_params = {}
        
        # 设置分页参数
        if limit:
            query_params['take'] = limit
            query_params['skip'] = 0  # 从第0条开始
        
        # 构建过滤条件 - 使用字段名而不是字段ID
        if where_conditions:
            filter_set = []
            for field, value in where_conditions.items():
                # 直接使用字段名而不是字段ID
                field_name = field
                if field.endswith('__gt'):
                    field_name = field.replace('__gt', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "isGreater",
                        "value": value
                    })
                elif field.endswith('__gte'):
                    field_name = field.replace('__gte', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "isGreaterEqual",
                        "value": value
                    })
                elif field.endswith('__lt'):
                    field_name = field.replace('__lt', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "isLess",
                        "value": value
                    })
                elif field.endswith('__lte'):
                    field_name = field.replace('__lte', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "isLessEqual",
                        "value": value
                    })
                elif field.endswith('__eq'):
                    field_name = field.replace('__eq', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "is",  # 精确匹配
                        "value": value
                    })
                elif field.endswith('__like'):
                    field_name = field.replace('__like', '')
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "contains",  # 模糊匹配
                        "value": value
                    })
                else:
                    # 默认使用精确匹配
                    filter_set.append({
                        "fieldId": field_name,
                        "operator": "is",  # 精确匹配
                        "value": value
                    })
            
            query_params['filter'] = json.dumps({
                "conjunction": "and",
                "filterSet": filter_set
            })
        
        # 构建排序参数 - 使用字段名而不是字段ID
        if order_by:
            # 直接使用字段名，而不是字段ID
            order_config = [{
                "fieldId": order_by,
                "order": order_direction
            }]
            query_params['orderBy'] = json.dumps(order_config)
        
        # 获取记录
        records_data = client.get_records(table_id, **query_params)
        records = records_data.get('records', [])
        
        if not records:
            print(f"表格 '{table_name}' 中没有记录")
            return 0
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        field_names = [field.get('name', 'N/A') for field in fields]
        
        # 准备数据
        rows = []
        for record in records:
            record_fields = record.get('fields', {})
            row = []
            for field_name in field_names:
                value = record_fields.get(field_name, '')
                # 处理长文本
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + '...'
                row.append(value)
            rows.append(row)
        
        # 使用rich库显示彩色表格
        if console.is_terminal:
            table = Table(title=f"表格: {table_name}")
            
            for field_name in field_names:
                table.add_column(field_name, style="cyan", no_wrap=False)
            
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            
            console.print(table)
        else:
            # 非终端环境使用tabulate
            print(tabulate(rows, headers=field_names, tablefmt='simple'))
        
        # 显示统计信息
        total_count = records_data.get('total', len(records))
        print(f"\n📊 显示 {len(records)}/{total_count} 条记录")
        
        return 0
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}")
        return 1
