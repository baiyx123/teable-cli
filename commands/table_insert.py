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
    is_pipe_output, format_record_for_pipe, SmartPipeHandler
)


logger = logging.getLogger(__name__)
console = Console()



from .table_common import *

def insert_record(client, session, args: list):
    """插入记录，返回(状态码, 记录ID)元组"""
    try:
        # 检测是否有管道输入 - 智能管道模式
        from .pipe_core import is_pipe_input
        
        # 检查第一个参数是否是表名
        target_table_name = None
        remaining_args = args
        
        if args:
            first_arg = args[0]
            # 判断是否是表名：不是字段=值格式
            is_field_assignment = '=' in first_arg
            
            if not is_field_assignment:
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
                return result, None
            
            # 更新后的表信息
            table_id = session.get_current_table_id()
            table_name = session.get_current_table()
        else:
            # 使用当前表
            table_id = session.get_current_table_id()
            table_name = session.get_current_table()
        
        logger.info(f"开始插入记录到表格 '{table_name}' (ID: {table_id})")
        
        # 检查参数中是否有字段映射（@字段名 或 $字段名）
        has_field_mapping = False
        if remaining_args:
            for arg in remaining_args:
                if '=' in arg:
                    _, value = arg.split('=', 1)
                    if value.strip().startswith('@') or value.strip().startswith('$'):
                        has_field_mapping = True
                        break
        
        # 管道模式判断：如果有管道输入且有字段映射，进入管道模式
        if is_pipe_input() and has_field_mapping:
            return insert_pipe_mode(client, session, table_id, table_name, remaining_args)
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        
        logger.debug(f"获取到 {len(fields)} 个字段，其中 {len(link_fields)} 个关联字段")
        
        if not remaining_args:
            # 交互式模式
            print(f"向表格 '{table_name}' 插入记录:")
            record_data = {}
            
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'singleLineText')
                
                # 跳过系统字段
                if field_name in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                    continue
                
                # 跳过公式字段和引用字段
                if not is_field_editable(field):
                    logger.info(f"跳过字段 '{field_name}' ({field_type}，不可编辑)")
                    print(f"⏭️  跳过字段 '{field_name}' ({field_type}，不可编辑)")
                    continue
                
                # 检查是否有默认值
                default_value = get_field_default_value(field)
                is_required = is_field_required(field)
                
                # 特殊处理关联字段
                if field_type == 'link':
                    # 构建提示信息
                    prompt_suffix = ""
                    if default_value is not None:
                        prompt_suffix = f"，默认值: {default_value}"
                    if is_required:
                        prompt_suffix += " [必填]"
                    
                    value = input(f"{field_name} (关联字段{prompt_suffix}，直接回车跳过): ").strip()
                    
                    # 如果没有输入值，检查是否有默认值或是否必填
                    if not value:
                        if default_value is not None:
                            # 使用默认值（关联字段的默认值应该是记录ID）
                            value = str(default_value)
                            logger.info(f"字段 '{field_name}' 使用默认值: {value}")
                            print(f"✅ 使用默认值: {value}")
                        elif is_required:
                            print(f"❌ 字段 '{field_name}' 是必填字段，不能为空")
                            # 继续循环，让用户重新输入
                            continue
                        else:
                            # 非必填且无默认值，跳过
                            continue
                    
                    if value:
                        # 确保在处理关联字段前后，当前表格状态一致
                        current_table_before = session.get_current_table()
                        current_table_id_before = session.get_current_table_id()
                        
                        linked_record_id = process_link_field_value(client, field_name, value, link_fields, session)
                        
                        # 确保处理完关联字段后，恢复原表格状态
                        current_table_after = session.get_current_table()
                        current_table_id_after = session.get_current_table_id()
                        if current_table_before and current_table_id_before:
                            if current_table_after != current_table_before or current_table_id_after != current_table_id_before:
                                # 状态不一致，尝试恢复
                                try:
                                    use_table(client, session, current_table_before)
                                except:
                                    try:
                                        session.set_current_table(current_table_before, current_table_id_before)
                                    except:
                                        pass
                        
                        if linked_record_id:
                            # 根据关联类型决定格式
                            relationship = link_fields[field_name].get('relationship', 'manyOne')
                            if relationship in ['manyMany', 'oneMany']:
                                # 多对多/一对多关系使用数组格式
                                record_data[field_name] = [{'id': linked_record_id}]
                            else:
                                # 一对一/多对一关系使用对象格式
                                record_data[field_name] = {'id': linked_record_id}
                        else:
                            if is_required:
                                print(f"❌ 字段 '{field_name}' 是必填字段，必须提供有效的关联记录")
                                # 继续循环，让用户重新输入
                                continue
                            else:
                                print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                    # 无论是否输入值，都继续处理下一个字段
                    continue
                
                # 处理普通字段
                # 构建提示信息
                prompt_suffix = ""
                if default_value is not None:
                    prompt_suffix = f"，默认值: {default_value}"
                if is_required:
                    prompt_suffix += " [必填]"
                
                value = input(f"{field_name} ({field_type}{prompt_suffix}，直接回车跳过): ").strip()
                
                # 如果没有输入值，检查是否有默认值或是否必填
                if not value:
                    if default_value is not None:
                        # 使用默认值
                        value = default_value
                        logger.info(f"字段 '{field_name}' 使用默认值: {value}")
                        print(f"✅ 使用默认值: {value}")
                    elif is_required:
                        print(f"❌ 字段 '{field_name}' 是必填字段，不能为空")
                        # 继续循环，让用户重新输入
                        continue
                    else:
                        # 非必填且无默认值，跳过
                        continue
                
                # 根据字段类型转换值
                converted_value = convert_field_value(field_type, value)
                record_data[field_name] = converted_value
            
            if not record_data:
                print("没有输入任何数据，取消插入")
                return 0, None
        else:
            # 命令行参数模式
            # 格式: field1=value1 field2=value2
            record_data = {}
            
            # 先收集所有提供的字段
            provided_fields = {}
            for arg in remaining_args:
                if '=' in arg:
                    field_name, value = arg.split('=', 1)
                    provided_fields[field_name] = value
            
            # 处理所有字段（包括未提供的必填字段和默认值字段）
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', 'singleLineText')
                
                # 跳过系统字段
                if field_name in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                    continue
                
                # 跳过公式字段和引用字段
                if not is_field_editable(field):
                    continue
                
                # 检查是否有默认值和是否必填
                default_value = get_field_default_value(field)
                is_required = is_field_required(field)
                
                # 检查字段是否在命令行参数中提供
                if field_name in provided_fields:
                    value = provided_fields[field_name]
                else:
                    # 字段未提供，检查默认值或必填要求
                    if default_value is not None:
                        value = default_value
                        logger.info(f"字段 '{field_name}' 使用默认值: {value}")
                        print(f"✅ 字段 '{field_name}' 使用默认值: {value}")
                    elif is_required:
                        print(f"❌ 字段 '{field_name}' 是必填字段，但未在命令行参数中提供")
                        return 1, None
                    else:
                        # 非必填且无默认值，跳过
                        continue
                
                # 检查是否为关联字段
                if field_name in link_fields:
                    linked_record_id = process_link_field_value(client, field_name, value, link_fields, session)
                    if linked_record_id:
                        # 根据关联类型决定格式
                        relationship = link_fields[field_name].get('relationship', 'manyOne')
                        if relationship in ['manyMany', 'oneMany']:
                            # 多对多/一对多关系使用数组格式
                            record_data[field_name] = [{'id': linked_record_id}]
                        else:
                            # 一对一/多对一关系使用对象格式
                            record_data[field_name] = {'id': linked_record_id}
                    else:
                        if is_required:
                            print(f"❌ 字段 '{field_name}' 是必填字段，必须提供有效的关联记录")
                            return 1, None
                        else:
                            print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                    continue
                else:
                    # 普通字段，需要根据字段类型转换值
                    converted_value = convert_field_value(field_type, value)
                    record_data[field_name] = converted_value
            
            # 检查是否有未识别的字段
            for field_name in provided_fields:
                # 检查字段是否存在
                field_exists = False
                for field in fields:
                    if field.get('name') == field_name:
                        field_exists = True
                        break
                
                if not field_exists:
                    print(f"⚠️  警告: 字段 '{field_name}' 不存在，跳过")
        
        if not record_data:
            print("没有有效数据，取消插入")
            return 0, None
        
        # 检查是否有关联字段
        has_link_fields = any(field_name in link_fields for field_name in record_data.keys())
        
        # 插入记录 - 使用正确的insert_records方法
        logger.info(f"准备插入记录，包含字段: {list(record_data.keys())}")
        # 如果有关联字段，使用字段名模式（fieldKeyType: "name"）
        result = client.insert_records(table_id, [{'fields': record_data}], use_field_ids=False)
        
        if result and 'records' in result:
            inserted_record = result['records'][0]
            record_id = inserted_record.get('id')
            logger.info(f"成功插入记录，ID: {record_id}")
            
            # 统一输出格式：总是输出记录ID到stdout（标准管道格式）
            print(record_id)
            
            # 人类可读的消息输出到stderr，这样不会影响管道传递
            if sys.stdout.isatty():
                print(f"✅ 成功插入记录，ID: {record_id}", file=sys.stderr)
            
            return 0, record_id
        else:
            logger.error("插入记录失败：API返回结果异常")
            if sys.stdout.isatty():
                print("❌ 插入记录失败", file=sys.stderr)
            return 1, None
            
    except Exception as e:
        logger.error(f"插入记录失败: {e}", exc_info=True)
        print(f"错误: 插入记录失败: {e}")
        return 1, None



def insert_pipe_mode(client, session, table_id: str, table_name: str, args: list):
    """管道模式的insert命令 - 从管道流式读取记录并批量插入"""
    try:
        from .pipe_core import parse_pipe_input_line
        
        # 直接读取第一行
        first_line = sys.stdin.readline()
        if not first_line or not first_line.strip():
            print("错误: 没有从管道接收到有效的记录数据", file=sys.stderr)
            return 1
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        
        logger.debug(f"获取到 {len(fields)} 个字段，其中 {len(link_fields)} 个关联字段")
        
        # 解析命令行参数中的字段映射
        # 语法规则：
        # - 目标字段=@源字段 或 目标字段=$源字段：字段映射（从管道记录中获取）
        # - 目标字段=常量值：常量值（直接使用）
        field_mappings = {}
        for arg in args:
            if '=' in arg:
                target_field, source_value = arg.split('=', 1)
                target_field = target_field.strip()
                source_value = source_value.strip()
                
                # 检查是否是字段映射语法（@字段名 或 $字段名）
                if source_value.startswith('@') or source_value.startswith('$'):
                    # 字段映射：去掉@或$前缀，使用字段名
                    pipe_field_name = source_value[1:]
                    field_mappings[target_field] = {
                        'type': 'field_mapping',
                        'source_field': pipe_field_name
                    }
                else:
                    # 常量值：直接使用
                    field_mappings[target_field] = {
                        'type': 'constant',
                        'value': source_value
                    }
        
        # 检查是否提供了字段映射
        if not field_mappings:
            print("错误: 管道模式下必须指定字段映射或常量值")
            print("")
            print("使用方式:")
            print("  字段映射: t show | t insert 目标字段=@源字段")
            print("  常量值:   t show | t insert 目标字段=常量值")
            print("  混合使用: t show | t insert 字段1=@源字段1 字段2=常量值")
            print("")
            print("示例:")
            print("  t show | t insert 新订单号=@订单号 客户名称=@客户名称 状态=已完成")
            print("  t show | t insert 订单号=ORD999 备注=来自管道")
            return 1
        
        # 显示映射模式信息
        # 统计字段映射和常量值的数量
        field_mapping_count = sum(1 for m in field_mappings.values() if m['type'] == 'field_mapping')
        constant_count = sum(1 for m in field_mappings.values() if m['type'] == 'constant')
        
        print(f"使用手动映射模式: {len(field_mappings)} 个字段")
        if field_mapping_count > 0:
            print(f"  - 字段映射: {field_mapping_count} 个（使用 @字段名 或 $字段名 语法）")
        if constant_count > 0:
            print(f"  - 常量值: {constant_count} 个")
        
        logger.info(f"字段映射详情: {field_mappings}")
        
        # 流式处理参数
        batch_size = 10  # 小批次，快速响应
        total_processed = 0
        current_batch = []
        success_count = 0
        error_count = 0
        
        print(f"开始真正流式处理，每批{batch_size}条记录...")
        
        # 从管道流式读取记录
        try:
            # 先处理第一行（已经在前面读取了）
            logger.debug(f"解析第一行管道输入: '{first_line.strip()}'")
            pipe_record = parse_pipe_input_line(first_line)
            if pipe_record:
                logger.debug(f"解析成功: record_id='{pipe_record.get('id')}', fields={list(pipe_record.get('fields', {}).keys())}")
                current_batch.append(pipe_record)
            else:
                logger.warning(f"第一行解析失败，跳过: '{first_line.strip()}'")
            
            # 继续读取剩余的行
            for line in sys.stdin:
                pipe_record = parse_pipe_input_line(line)
                if pipe_record:
                    current_batch.append(pipe_record)
                    
                    # 当批次满时立即处理
                    if len(current_batch) >= batch_size:
                        batch_success, batch_errors = _process_insert_batch(
                            client, table_id, current_batch, field_mappings,
                            fields, link_fields, total_processed + len(current_batch)
                        )
                        success_count += batch_success
                        error_count += batch_errors
                        total_processed += len(current_batch)
                        current_batch = []
                        
                        # 显示实时进度
                        if total_processed % 50 == 0:
                            print(f"实时流式插入进度: 已处理 {total_processed} 条记录，成功 {success_count} 条，失败 {error_count} 条")
        
        except KeyboardInterrupt:
            print(f"\n用户中断，正在处理剩余记录...")
        
        # 处理剩余记录
        if current_batch:
            batch_success, batch_errors = _process_insert_batch(
                client, table_id, current_batch, field_mappings,
                fields, link_fields, total_processed + len(current_batch)
            )
            success_count += batch_success
            error_count += batch_errors
            total_processed += len(current_batch)
        
        if total_processed > 0:
            print(f"✅ 真正流式插入完成，共处理 {total_processed} 条记录，成功 {success_count} 条，失败 {error_count} 条")
            return 0 if error_count == 0 else 1
        else:
            print("错误: 没有从管道接收到有效的记录数据")
            return 1
            
    except Exception as e:
        print(f"错误: 流式管道模式插入记录失败: {e}")
        return 1



def _process_insert_batch(client, table_id: str, batch_records: List[Dict[str, Any]],
                         field_mappings: Dict[str, str], fields: List[Dict[str, Any]],
                         link_fields: Dict[str, Dict[str, Any]], progress_count: int):
    """处理一批插入记录"""
    try:
        insert_records = []
        batch_success = 0
        batch_errors = 0
        
        # 构建字段名到字段信息的映射，方便查找
        field_info_map = {}
        for field in fields:
            field_name = field.get('name', '')
            field_info_map[field_name] = field
        
        for pipe_record in batch_records:
            try:
                record_data = {}
                record_id = pipe_record.get('id', '')
                pipe_fields = pipe_record.get('fields', {})
                logger.info(f"处理管道记录: record_id='{record_id}', pipe_fields={list(pipe_fields.keys())}")
                
                # 根据字段映射构建记录数据
                for target_field, mapping_info in field_mappings.items():
                    # 检查目标字段是否存在
                    target_field_info = field_info_map.get(target_field)
                    
                    if not target_field_info:
                        logger.warning(f"目标字段 '{target_field}' 不存在，跳过")
                        continue
                    
                    # 跳过系统字段和不可编辑字段
                    if target_field in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy']:
                        continue
                    if not is_field_editable(target_field_info):
                        logger.debug(f"跳过不可编辑字段 '{target_field}'")
                        continue
                    
                    field_type = target_field_info.get('type', 'singleLineText')
                    
                    # 确定字段值：根据映射类型决定
                    if mapping_info['type'] == 'field_mapping':
                        # 字段映射：从管道记录中获取字段值
                        source_field = mapping_info['source_field']
                        logger.info(f"处理字段映射: 目标字段='{target_field}', 源字段='{source_field}', record_id='{record_id}'")
                        # 特殊处理：@id 表示记录ID，从 pipe_record 的 id 字段获取
                        if source_field == 'id' or source_field == '@id':
                            field_value = record_id
                            logger.info(f"使用记录ID: field_value='{field_value}'")
                            if not field_value:
                                logger.warning(f"记录ID为空，跳过字段 '{target_field}'")
                                continue
                        elif source_field in pipe_fields:
                            field_value = pipe_fields[source_field]
                        else:
                            logger.warning(f"管道记录中不存在字段 '{source_field}'，跳过字段 '{target_field}'")
                            continue
                    else:
                        # 常量值：直接使用
                        field_value = mapping_info['value']
                    
                    # 处理关联字段
                    if target_field in link_fields:
                        linked_record_id = process_link_field_value(
                            client, target_field, str(field_value), link_fields, session=None
                        )
                        if linked_record_id:
                            relationship = link_fields[target_field].get('relationship', 'manyOne')
                            if relationship in ['manyMany', 'oneMany']:
                                record_data[target_field] = [{'id': linked_record_id}]
                            else:
                                record_data[target_field] = {'id': linked_record_id}
                        else:
                            logger.warning(f"关联字段 '{target_field}' 处理失败，跳过")
                            continue
                    else:
                        # 普通字段，转换值类型
                        converted_value = convert_field_value(field_type, field_value)
                        record_data[target_field] = converted_value
                
                if record_data:
                    insert_records.append({'fields': record_data})
                else:
                    logger.warning(f"记录 {record_id} 没有有效字段数据，跳过")
                    batch_errors += 1
                    
            except Exception as e:
                logger.error(f"处理管道记录失败: {e}", exc_info=True)
                batch_errors += 1
        
        # 执行批量插入
        if insert_records:
            # 检查是否有关联字段
            has_link_fields = any(
                any(target_field in link_fields for target_field in record.get('fields', {}).keys())
                for record in insert_records
            )
            
            # 如果有关联字段，使用字段名模式（fieldKeyType: "name"）
            try:
                result = client.insert_records(table_id, insert_records, use_field_ids=False)
                if result and 'records' in result:
                    inserted_count = len(result['records'])
                    batch_success += inserted_count
                    logger.info(f"成功插入批次: {inserted_count} 条记录 (累计: {progress_count})")
                    
                    # 统一输出格式：总是输出记录ID到stdout（标准管道格式）
                    for inserted_record in result['records']:
                        record_id = inserted_record.get('id', '')
                        if record_id:
                            print(record_id, flush=True)
                    
                    # 人类可读的消息输出到stderr，这样不会影响管道传递
                    if sys.stdout.isatty():
                        print(f"✅ 成功插入 {inserted_count} 条记录", file=sys.stderr)
                else:
                    logger.warning(f"批次插入失败: {len(insert_records)} 条记录")
                    batch_errors += len(insert_records)
            except Exception as e:
                logger.error(f"批次插入异常: {e}", exc_info=True)
                logger.error(f"插入数据: {insert_records}")
                batch_errors += len(insert_records)
        
        return batch_success, batch_errors
        
    except Exception as e:
        logger.error(f"批次插入失败: {e}", exc_info=True)
        print(f"⚠️  批次插入失败 ({len(batch_records)} 条记录): {e}")
        return 0, len(batch_records)



