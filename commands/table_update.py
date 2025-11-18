#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格操作命令
"""

import sys
import json
import logging
from typing import Optional, Dict, List, Any
from tabulate import tabulate
from rich.console import Console
from rich.table import Table

# 导入管道操作组件
from .pipe_core import (
    is_pipe_output, format_record_for_pipe
)


logger = logging.getLogger(__name__)
console = Console()



from .table_common import *
from .table_common import (
    _parse_where_conditions_with_mapping,
    _build_query_params_from_conditions,
    _parse_where_conditions,
    _build_query_params
)

def update_record(client, session, args: list):
    """更新记录，支持条件更新（where语法）和智能管道操作，支持指定表名"""
    try:
        # 检测是否有管道输入 - 智能管道模式
        from .pipe_core import is_pipe_input
        
        # 检查第一个参数是否是表名
        target_table_name = None
        remaining_args = args
        
        if args and not is_pipe_input():
            first_arg = args[0]
            # 判断是否是表名：不是记录ID格式（rec开头），不是字段=值格式，不是where关键字
            is_record_id = first_arg.startswith('rec') and len(first_arg) > 10
            is_field_assignment = '=' in first_arg
            is_where_keyword = first_arg.lower() == 'where'
            
            if not is_record_id and not is_field_assignment and not is_where_keyword:
                # 可能是表名，尝试查找表格
                tables = client.get_tables()
                for table in tables:
                    if table.get('name') == first_arg:
                        target_table_name = first_arg
                        remaining_args = args[1:]
                        break
        
        # 如果指定了表名，切换到该表
        if target_table_name:
            original_table = session.get_current_table()
            original_table_id = session.get_current_table_id()
            
            result = use_table(client, session, target_table_name)
            if result != 0:
                return result
            
            # 更新后的表信息
            table_id = session.get_current_table_id()
            table_name = session.get_current_table()
        else:
            # 使用当前表
            table_id = session.get_current_table_id()
            table_name = session.get_current_table()
        
        # 检查参数中是否有记录ID或字段映射
        has_record_id = False
        has_field_mapping = False
        
        for arg in remaining_args:
            # 检查是否是记录ID
            if arg.startswith('rec') and len(arg) > 10:
                has_record_id = True
                break
            # 检查是否有字段映射（@字段名 或 $字段名）
            # 需要检查等号后面的值，以及条件操作符后面的值
            if '=' in arg:
                parts = arg.split('=', 1)
                if len(parts) == 2:
                    value = parts[1].strip()
                    if value.startswith('@') or value.startswith('$'):
                        has_field_mapping = True
            elif '>' in arg or '<' in arg or '>=' in arg or '<=' in arg or '!=' in arg:
                # 处理条件操作符
                for op in ['>=', '<=', '!=', '>', '<']:
                    if op in arg:
                        parts = arg.split(op, 1)
                        if len(parts) == 2:
                            value = parts[1].strip()
                            if value.startswith('@') or value.startswith('$'):
                                has_field_mapping = True
                                break
        
        # 管道模式：有管道输入、没有记录ID、有字段映射
        if is_pipe_input() and not has_record_id and has_field_mapping:
            return update_pipe_mode(client, session, table_id, table_name, remaining_args)
        
        # 传统模式处理
        if not remaining_args:
            print("错误: 请指定更新参数")
            print("使用: t update [表名] [记录ID] 字段1=值1 字段2=值2 ... [where 条件字段1=值1 条件字段2>值2 ...]")
            print("示例: t update 姓名=张三 where 状态=待处理")
            print("示例: t update 订单表 状态=已完成 where 订单号=ORD001")
            print("示例: t update 记录ID123 姓名=张三 年龄=25")
            print("管道示例: t show -w 状态=待处理 | t update 状态=处理中")
            print("管道示例: t show | t update 订单表 状态=已完成 where 订单号=@订单号")
            return 1
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        field_names = [f.get('name', '') for f in fields]
        
        # 解析参数，支持where条件
        where_index = -1
        for i, arg in enumerate(remaining_args):
            if arg.lower() == 'where':
                where_index = i
                break
        
        if where_index == -1:
            # 传统模式：单记录更新
            return _update_single_record(client, session, table_id, table_name, fields, link_fields, field_names, remaining_args)
        else:
            # 条件更新模式
            update_args = remaining_args[:where_index]
            where_args = remaining_args[where_index + 1:]
            
            if not update_args:
                print("错误: where条件前必须指定要更新的字段")
                return 1
            
            if not where_args:
                print("错误: where条件后必须指定过滤条件")
                return 1
            
            return _update_with_where(client, session, table_id, table_name, fields, link_fields, field_names, update_args, where_args)
            
    except Exception as e:
        print(f"错误: 更新记录失败: {e}")
        logger.error(f"更新记录失败: {e}", exc_info=True)
        return 1



def update_pipe_mode(client, session, table_id: str, table_name: str, args: list):
    """管道模式的update命令 - 支持直接更新和merge update（带where条件），支持指定表名"""
    try:
        # 检查第一个参数是否是表名
        target_table_name = None
        remaining_args = args
        
        if args:
            first_arg = args[0]
            # 判断是否是表名：不是字段=值格式，不是where关键字
            is_field_assignment = '=' in first_arg
            is_where_keyword = first_arg.lower() == 'where'
            
            if not is_field_assignment and not is_where_keyword:
                # 可能是表名，尝试查找表格
                tables = client.get_tables()
                for table in tables:
                    if table.get('name') == first_arg:
                        target_table_name = first_arg
                        remaining_args = args[1:]
                        break
        
        # 如果指定了表名，切换到该表
        if target_table_name:
            result = use_table(client, session, target_table_name)
            if result != 0:
                return result
            
            # 更新后的表信息
            table_id = session.get_current_table_id()
            table_name = session.get_current_table()
        
        from .pipe_core import parse_pipe_input_line
        
        # 解析参数，分离更新字段和where条件
        where_index = -1
        for i, arg in enumerate(remaining_args):
            if arg.lower() == 'where':
                where_index = i
                break
        
        if where_index == -1:
            # 直接更新模式：更新管道记录本身
            return _update_pipe_direct_mode(client, session, table_id, table_name, remaining_args)
        else:
            # Merge update模式：根据where条件查找并更新匹配的记录
            update_args = remaining_args[:where_index]
            where_args = remaining_args[where_index + 1:]
            
            if not update_args:
                print("错误: where条件前必须指定要更新的字段")
                return 1
            
            if not where_args:
                print("错误: where条件后必须指定过滤条件")
                return 1
            
            return _update_pipe_merge_mode(client, session, table_id, table_name, update_args, where_args)
            
    except Exception as e:
        print(f"错误: 流式管道模式更新记录失败: {e}")
        logger.error(f"流式管道模式更新记录失败: {e}", exc_info=True)
        return 1



def _update_pipe_direct_mode(client, session, table_id: str, table_name: str, args: list):
    """直接更新模式：更新管道记录本身"""
    try:
        from .pipe_core import parse_pipe_input_line
        
        # 解析更新字段（支持@字段名语法和常量值）
        update_fields = {}
        for arg in args:
            if '=' in arg:
                field_name, value = arg.split('=', 1)
                field_name = field_name.strip()
                value = value.strip()
                
                # 检查是否是字段映射语法（@字段名 或 $字段名）
                if value.startswith('@') or value.startswith('$'):
                    # 字段映射：从管道记录中获取值
                    update_fields[field_name] = {
                        'type': 'field_mapping',
                        'source_field': value[1:]
                    }
                else:
                    # 常量值：直接使用
                    update_fields[field_name] = {
                        'type': 'constant',
                        'value': value
                    }
        
        if not update_fields:
            print("错误: 请指定要更新的字段")
            return 1
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        has_link_fields = any(field_name in link_fields for field_name in update_fields.keys())
        
        # 流式处理参数
        batch_size = 10
        total_processed = 0
        current_batch = []
        
        print(f"开始流式处理，每批{batch_size}条记录...")
        
        # 从管道流式读取记录
        try:
            for line in sys.stdin:
                record = parse_pipe_input_line(line)
                if record:
                    current_batch.append(record)
                    
                    if len(current_batch) >= batch_size:
                        _process_update_batch_direct(client, table_id, current_batch, update_fields,
                                                    fields, link_fields, has_link_fields, 
                                                    total_processed + len(current_batch))
                        total_processed += len(current_batch)
                        current_batch = []
                        
                        if total_processed % 50 == 0:
                            print(f"实时流式更新进度: 已处理 {total_processed} 条记录")
        
        except KeyboardInterrupt:
            print(f"\n用户中断，正在处理剩余记录...")
        
        # 处理剩余记录
        if current_batch:
            _process_update_batch_direct(client, table_id, current_batch, update_fields,
                                        fields, link_fields, has_link_fields, 
                                        total_processed + len(current_batch))
            total_processed += len(current_batch)
        
        if total_processed > 0:
            print(f"✅ 流式更新完成，共处理 {total_processed} 条记录")
            return 0
        else:
            print("错误: 没有从管道接收到有效的记录数据")
            return 1
            
    except Exception as e:
        print(f"错误: 直接更新模式失败: {e}")
        logger.error(f"直接更新模式失败: {e}", exc_info=True)
        return 1



def _update_pipe_merge_mode(client, session, table_id: str, table_name: str, 
                             update_args: list, where_args: list):
    """Merge update模式：根据where条件查找并更新匹配的记录"""
    try:
        from .pipe_core import parse_pipe_input_line
        
        # 解析更新字段（支持@字段名语法和常量值）
        update_fields = {}
        for arg in update_args:
            if '=' in arg:
                field_name, value = arg.split('=', 1)
                field_name = field_name.strip()
                value = value.strip()
                
                if value.startswith('@') or value.startswith('$'):
                    update_fields[field_name] = {
                        'type': 'field_mapping',
                        'source_field': value[1:]
                    }
                else:
                    update_fields[field_name] = {
                        'type': 'constant',
                        'value': value
                    }
        
        if not update_fields:
            print("错误: 请指定要更新的字段")
            return 1
        
        # 使用通用函数解析where条件（支持@字段名语法和常量值）
        where_conditions = _parse_where_conditions_with_mapping(where_args)
        
        if not where_conditions:
            print("错误: 请指定where条件")
            return 1
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        
        # 流式处理
        total_processed = 0
        total_updated = 0
        
        print(f"开始merge update处理...")
        
        # 从管道流式读取记录
        try:
            for line in sys.stdin:
                pipe_record = parse_pipe_input_line(line)
                if pipe_record:
                    # 对于每条管道记录，构建查询条件并更新匹配的记录
                    updated_count = _process_merge_update(client, table_id, pipe_record, 
                                                          update_fields, where_conditions,
                                                          fields, link_fields)
                    total_processed += 1
                    total_updated += updated_count
                    
                    if total_processed % 50 == 0:
                        print(f"实时merge update进度: 已处理 {total_processed} 条管道记录，更新 {total_updated} 条目标记录")
        
        except KeyboardInterrupt:
            print(f"\n用户中断，正在处理剩余记录...")
        
        if total_processed > 0:
            print(f"✅ Merge update完成，共处理 {total_processed} 条管道记录，更新 {total_updated} 条目标记录")
            return 0
        else:
            print("错误: 没有从管道接收到有效的记录数据")
            return 1
            
    except Exception as e:
        print(f"错误: Merge update模式失败: {e}")
        logger.error(f"Merge update模式失败: {e}", exc_info=True)
        return 1



def _process_update_batch_direct(client, table_id: str, batch_records: List[Dict[str, Any]],
                                 update_fields: Dict[str, Dict[str, Any]], 
                                 fields: List[Dict[str, Any]], link_fields: Dict[str, Dict[str, Any]],
                                 has_link_fields: bool, progress_count: int):
    """处理直接更新模式的批次"""
    try:
        from .pipe_core import is_pipe_output, format_record_for_pipe
        
        updates = []
        updated_record_ids = []  # 记录更新的记录ID，用于管道输出
        field_info_map = {f.get('name'): f for f in fields}
        
        for record in batch_records:
            record_id = record['id']
            pipe_fields = record.get('fields', {})
            
            # 构建更新数据
            fields_data = {}
            for target_field, mapping_info in update_fields.items():
                # 确定字段值
                if mapping_info['type'] == 'field_mapping':
                    source_field = mapping_info['source_field']
                    if source_field in pipe_fields:
                        field_value = pipe_fields[source_field]
                    else:
                        logger.warning(f"管道记录中不存在字段 '{source_field}'，跳过字段 '{target_field}'")
                        continue
                else:
                    field_value = mapping_info['value']
                
                # 处理关联字段
                if target_field in link_fields:
                    linked_record_id = process_link_field_value(
                        client, target_field, str(field_value), link_fields, session=None
                    )
                    if linked_record_id:
                        relationship = link_fields[target_field].get('relationship', 'manyOne')
                        if relationship in ['manyMany', 'oneMany']:
                            fields_data[target_field] = [{'id': linked_record_id}]
                        else:
                            fields_data[target_field] = {'id': linked_record_id}
                    else:
                        logger.warning(f"关联字段 '{target_field}' 处理失败，跳过")
                        continue
                else:
                    # 普通字段，转换值类型
                    target_field_info = field_info_map.get(target_field)
                    if target_field_info:
                        field_type = target_field_info.get('type', 'singleLineText')
                        converted_value = convert_field_value(field_type, field_value)
                        fields_data[target_field] = converted_value
            
            if fields_data:
                updates.append({
                    'record_id': record_id,
                    'fields_data': fields_data
                })
                updated_record_ids.append(record_id)
        
        # 执行批量更新
        if updates:
            if has_link_fields:
                result = client.batch_update_records(table_id, updates, use_field_ids=False)
            else:
                result = client.batch_update_records(table_id, updates)
            
            if result:
                logger.info(f"成功更新批次: {len(updates)} 条记录 (累计: {progress_count})")
                
                # 如果有管道输出，输出更新的记录（链式管道操作）
                if is_pipe_output() and updated_record_ids:
                    # 使用 filter 查询更新后的记录
                    # 构建 ID 过滤条件（使用 OR 连接多个 ID）
                    filter_set = []
                    for record_id in updated_record_ids:
                        filter_set.append({
                            "fieldId": "id",
                            "operator": "is",
                            "value": record_id
                        })
                    
                    if filter_set:
                        query_params = {
                            'filter': json.dumps({
                                "conjunction": "or",
                                "filterSet": filter_set
                            }),
                            'take': len(updated_record_ids),
                            'skip': 0
                        }
                        updated_records = client.get_records(table_id, **query_params)
                        if updated_records and 'records' in updated_records:
                            for updated_record in updated_records['records']:
                                output_line = format_record_for_pipe(updated_record)
                                print(output_line, flush=True)
            else:
                logger.warning(f"批次更新失败: {len(updates)} 条记录")
            
    except Exception as e:
        logger.error(f"批次更新失败: {e}", exc_info=True)
        print(f"⚠️  批次更新失败 ({len(batch_records)} 条记录): {e}")



def _process_update_batch(client, table_id: str, batch_records: List[Dict[str, Any]],
                         update_fields: Dict[str, str], has_link_fields: bool,
                         progress_count: int):
    """处理一批更新记录（旧版本，保持兼容）"""
    try:
        # 构建批量更新数据
        updates = []
        for record in batch_records:
            record_id = record['id']
            updates.append({
                'record_id': record_id,
                'fields_data': update_fields
            })
        
        # 执行批量更新
        if has_link_fields:
            result = client.batch_update_records(table_id, updates, use_field_ids=False)
        else:
            result = client.batch_update_records(table_id, updates)
        
        if result:
            logger.info(f"成功更新批次: {len(batch_records)} 条记录 (累计: {progress_count})")
        else:
            logger.warning(f"批次更新失败: {len(batch_records)} 条记录")
            
    except Exception as e:
        logger.error(f"批次更新失败: {e}")
        print(f"⚠️  批次更新失败 ({len(batch_records)} 条记录): {e}")



def _process_merge_update(client, table_id: str, pipe_record: Dict[str, Any],
                          update_fields: Dict[str, Dict[str, Any]], 
                          where_conditions: List[Dict[str, Any]],
                          fields: List[Dict[str, Any]], link_fields: Dict[str, Dict[str, Any]]) -> int:
    """处理merge update：根据where条件查找并更新匹配的记录"""
    try:
        pipe_fields = pipe_record.get('fields', {})
        
        # 使用通用函数构建查询参数
        query_params = _build_query_params_from_conditions(
            conditions=where_conditions,
            pipe_fields=pipe_fields,
            limit=1000,  # 限制每次最多更新1000条
            skip=0
        )
        
        if 'filter' not in query_params:
            logger.warning("没有有效的查询条件，跳过")
            return 0
        
        records_data = client.get_records(table_id, **query_params)
        matched_records = records_data.get('records', [])
        
        if not matched_records:
            logger.debug(f"没有找到匹配的记录，跳过")
            return 0
        
        # 构建更新数据（使用管道记录中的值替换@字段名）
        field_info_map = {f.get('name'): f for f in fields}
        fields_data = {}
        
        for target_field, mapping_info in update_fields.items():
            # 确定字段值
            if mapping_info['type'] == 'field_mapping':
                source_field = mapping_info['source_field']
                if source_field in pipe_fields:
                    field_value = pipe_fields[source_field]
                else:
                    logger.warning(f"管道记录中不存在字段 '{source_field}'，跳过字段 '{target_field}'")
                    continue
            else:
                field_value = mapping_info['value']
            
            # 处理关联字段
            if target_field in link_fields:
                linked_record_id = process_link_field_value(
                    client, target_field, str(field_value), link_fields, session=None
                )
                if linked_record_id:
                    relationship = link_fields[target_field].get('relationship', 'manyOne')
                    if relationship in ['manyMany', 'oneMany']:
                        fields_data[target_field] = [{'id': linked_record_id}]
                    else:
                        fields_data[target_field] = {'id': linked_record_id}
                else:
                    logger.warning(f"关联字段 '{target_field}' 处理失败，跳过")
                    continue
            else:
                # 普通字段，转换值类型
                target_field_info = field_info_map.get(target_field)
                if target_field_info:
                    field_type = target_field_info.get('type', 'singleLineText')
                    converted_value = convert_field_value(field_type, field_value)
                    fields_data[target_field] = converted_value
        
        if not fields_data:
            logger.warning("没有有效的更新字段，跳过")
            return 0
        
        # 批量更新匹配的记录
        updates = []
        for record in matched_records:
            record_id = record.get('id')
            updates.append({
                'record_id': record_id,
                'fields_data': fields_data
            })
        
        # 检查是否有关联字段
        has_link_fields = any(field_name in link_fields for field_name in fields_data.keys())
        
        if updates:
            if has_link_fields:
                result = client.batch_update_records(table_id, updates, use_field_ids=False)
            else:
                result = client.batch_update_records(table_id, updates)
            
            if result:
                logger.info(f"成功更新 {len(updates)} 条匹配记录")
                return len(updates)
            else:
                logger.warning(f"更新失败: {len(updates)} 条记录")
                return 0
        
        return 0
        
    except Exception as e:
        logger.error(f"Merge update处理失败: {e}", exc_info=True)
        return 0



def _update_single_record(client, session, table_id, table_name, fields, link_fields, field_names, args):
    """单记录更新（传统模式）"""
    record_id = args[0]
    
    # 获取字段信息和关联字段
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
            field_type = field.get('type', 'singleLineText')
            
            # 跳过系统字段
            if field_name in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                continue
            
            current_value = current_fields.get(field_name, '')
            
            # 特殊处理关联字段
            if field_type == 'link':
                new_value = input(f"{field_name} (当前: {current_value}): ").strip()
                if new_value and new_value != str(current_value):
                    linked_record_id = process_link_field_value(client, field_name, new_value, link_fields, session)
                    if linked_record_id:
                        # 根据关联类型决定格式
                        relationship = link_fields[field_name].get('relationship', 'manyOne')
                        if relationship in ['manyMany', 'oneMany']:
                            # 多对多/一对多关系使用数组格式
                            update_data[field_name] = [{'id': linked_record_id}]
                        else:
                            # 一对一/多对一关系使用对象格式
                            update_data[field_name] = {'id': linked_record_id}
                    else:
                        print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                continue
            
            new_value = input(f"{field_name} (当前: {current_value}): ").strip()
            
            if new_value and new_value != str(current_value):
                # 根据字段类型转换值
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
                    # 检查是否为关联字段
                    if field_name in link_fields:
                        linked_record_id = process_link_field_value(client, field_name, value, link_fields, session)
                        if linked_record_id:
                            # 根据关联类型决定格式
                            relationship = link_fields[field_name].get('relationship', 'manyOne')
                            logger.info(f"关联字段 '{field_name}' 的关联类型: {relationship}")
                            if relationship in ['manyMany', 'oneMany']:
                                # 多对多/一对多关系使用数组格式
                                update_data[field_name] = [{'id': linked_record_id}]
                            else:
                                # 一对一/多对一关系使用对象格式
                                update_data[field_name] = {'id': linked_record_id}
                        else:
                            print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                    else:
                        # 普通字段，直接使用值
                        update_data[field_name] = value
                else:
                    print(f"警告: 字段 '{field_name}' 不存在，跳过")
    
    if not update_data:
        print("没有数据需要更新")
        return 0
    
    # 检查是否有关联字段需要特殊处理
    has_link_fields = any(field_name in link_fields for field_name in update_data.keys())
    
    # 打印更新数据用于调试
    logger.info(f"更新数据: {update_data}")
    
    # 直接使用字段名模式更新（包括关联字段）
    # Teable API 应该支持使用字段名更新关联字段
    result = client.update_record(table_id, record_id, update_data, use_field_ids=False)
    
    if result:
        print(f"✅ 成功更新记录 {record_id}")
        return 0
    else:
        print(f"❌ 更新记录 {record_id} 失败")
        return 1


# ==================== 通用查询函数 ====================


def _update_with_where(client, session, table_id, table_name, fields, link_fields, field_names, update_args, where_args):
    """条件更新模式 - 复用show_current_table的过滤逻辑"""
    # 解析更新字段
    update_data = {}
    for arg in update_args:
        if '=' in arg:
            field_name, value = arg.split('=', 1)
            if field_name in field_names:
                # 检查是否为关联字段
                if field_name in link_fields:
                    linked_record_id = process_link_field_value(client, field_name, value, link_fields, session)
                    if linked_record_id:
                        # 根据关联类型决定格式
                        relationship = link_fields[field_name].get('relationship', 'manyOne')
                        if relationship in ['manyMany', 'oneMany']:
                            update_data[field_name] = [{'id': linked_record_id}]
                        else:
                            update_data[field_name] = {'id': linked_record_id}
                    else:
                        print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                        return 1
                else:
                    # 普通字段，直接使用值
                    update_data[field_name] = value
            else:
                print(f"警告: 字段 '{field_name}' 不存在，跳过")
    
    if not update_data:
        print("错误: 没有有效的更新字段")
        return 1
    
    # 解析where条件 - 复用show_current_table的解析逻辑
    where_conditions = _parse_where_conditions(where_args)
    
    if not where_conditions:
        print("错误: 没有有效的过滤条件")
        return 1
    
    # 构建查询参数 - 复用show_current_table的构建逻辑
    query_params = _build_query_params(where_conditions)
    
    # 查询符合条件的记录 - 支持分页获取所有记录
    print(f"正在查询符合条件的记录...")
    all_records = []
    page_size = 100  # 每页获取100条记录
    page = 1
    
    while True:
        # 设置分页参数
        page_query_params = query_params.copy()
        page_query_params['take'] = page_size
        page_query_params['skip'] = (page - 1) * page_size
        
        # 获取当前页数据
        records_data = client.get_records(table_id, **page_query_params)
        records = records_data.get('records', [])
        
        if not records:
            break
        
        all_records.extend(records)
        
        # 检查是否还有更多数据
        total_count = records_data.get('total', len(records))
        if len(all_records) >= total_count:
            break
        
        page += 1
        
        # 显示进度
        if len(all_records) % 500 == 0:
            print(f"已获取 {len(all_records)} 条记录...")
    
    if not all_records:
        print("没有找到符合条件的记录")
        return 0
    
    print(f"找到 {len(all_records)} 条符合条件的记录")
    
    # 批量更新记录
    updates = []
    for record in all_records:
        record_id = record.get('id')
        updates.append({
            'record_id': record_id,
            'fields_data': update_data
        })
    
    # 检查是否有关联字段需要特殊处理
    has_link_fields = any(field_name in link_fields for field_name in update_data.keys())
    
    if has_link_fields:
        # 使用批量更新API，关联字段需要使用字段ID模式
        result = client.batch_update_records(table_id, updates, use_field_ids=False)
    else:
        # 普通批量更新
        result = client.batch_update_records(table_id, updates)
    
    if result:
        print(f"✅ 成功更新 {len(all_records)} 条记录")
        return 0
    else:
        print(f"❌ 批量更新失败")
        return 1



