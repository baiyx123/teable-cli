#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格操作命令
"""

import sys
import json
from typing import Optional, Dict, List, Any
from tabulate import tabulate
from rich.console import Console
from rich.table import Table


console = Console()


def detect_link_fields(client, table_id: str) -> Dict[str, Dict[str, Any]]:
    """检测表格中的关联字段，返回字段名称和外键表ID映射"""
    fields = client.get_table_fields(table_id)
    link_fields = {}
    
    for field in fields:
        if field.get('type') == 'link':
            field_name = field.get('name')
            options = field.get('options', {})
            link_fields[field_name] = {
                'foreign_table_id': options.get('foreignTableId'),
                'relationship': options.get('relationship')
            }
    
    return link_fields


def find_linked_record(client, foreign_table_id: str, identifier: str) -> Optional[Dict[str, Any]]:
    """查找关联记录，支持精确匹配和模糊匹配"""
    # 1. 尝试作为记录ID查询 - 直接使用get_record API
    try:
        record = client.get_record(foreign_table_id, identifier)
        if record:
            return record
    except Exception as e:
        # 如果按ID查询失败，继续尝试其他方式
        pass
    
    # 2. 使用filter进行模糊查询 - 使用第一列字段进行匹配
    # 先获取表格字段信息，找到第一个非系统字段
    try:
        fields = client.get_table_fields(foreign_table_id)
        first_field = None
        for field in fields:
            field_name = field.get('name', '')
            field_type = field.get('type', '')
            # 跳过系统字段和关联字段
            if field_name not in ['id', 'createdTime', 'updatedTime', 'createdBy', 'updatedBy'] and field_type != 'link':
                first_field = field_name
                break
        
        if first_field:
            # 使用第一列字段进行模糊匹配
            records_data = client.get_records(foreign_table_id, filter=json.dumps({
                "conjunction": "and",
                "filterSet": [
                    {"fieldId": first_field, "operator": "contains", "value": identifier}
                ]
            }))
        else:
            # 如果没有合适的字段，只尝试ID匹配
            records_data = client.get_records(foreign_table_id, filter=json.dumps({
                "conjunction": "and",
                "filterSet": [
                    {"fieldId": "id", "operator": "is", "value": identifier}
                ]
            }))
        
        records = records_data.get('records', [])
        if not records:
            return None
        elif len(records) == 1:
            return records[0]
        else:
            # 多个结果，返回列表供交互选择
            return records
            
    except Exception as e:
        # 如果获取字段信息失败，返回None
        return None


def interactive_select_linked_record(records: List[Dict[str, Any]], field_name: str) -> Optional[Dict[str, Any]]:
    """交互式选择关联记录"""
    print(f"字段 '{field_name}' 找到多个匹配记录:")
    for i, record in enumerate(records):
        record_id = record.get('id', 'N/A')
        # 尝试获取显示字段的值
        fields = record.get('fields', {})
        display_value = None
        
        # 优先使用常见显示字段
        for display_field in ['name', 'title', 'label', 'display_name']:
            if display_field in fields and fields[display_field]:
                display_value = str(fields[display_field])
                break
        
        # 如果没有找到显示字段，使用第一个非空字段
        if not display_value:
            for field_value in fields.values():
                if field_value and str(field_value).strip():
                    display_value = str(field_value)
                    break
        
        if display_value:
            print(f"  {i+1}. {display_value} (ID: {record_id})")
        else:
            print(f"  {i+1}. 记录ID: {record_id}")
    
    while True:
        choice = input("请选择记录编号 (或输入0取消): ").strip()
        if choice == '0':
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(records):
                return records[idx]
            else:
                print("无效的选择，请重试")
        except ValueError:
            print("请输入有效的数字")


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


def process_link_field_value(client, field_name: str, field_value: str, link_fields: Dict[str, Dict[str, Any]], session=None) -> Optional[str]:
    """处理关联字段值，返回关联记录ID"""
    if field_name not in link_fields:
        return field_value
    
    link_info = link_fields[field_name]
    foreign_table_id = link_info['foreign_table_id']
    
    print(f"正在查找关联字段 '{field_name}' 的目标记录: {field_value}")
    
    # 查找关联记录
    result = find_linked_record(client, foreign_table_id, field_value)
    
    if result is None:
        print(f"❌ 未找到匹配的关联记录: {field_value}")
        
        # 询问用户是否要创建新记录
        create_new = input("是否创建新的关联记录？(y/N): ").strip().lower()
        if create_new not in ['y', 'yes', '是']:
            return None
        
        # 如果有session，使用现有的插入功能
        if session:
            try:
                # 获取关联表的名称
                tables = client.get_tables()
                foreign_table_name = None
                for table in tables:
                    if table.get('id') == foreign_table_id:
                        foreign_table_name = table.get('name')
                        break
                
                if not foreign_table_name:
                    print("❌ 无法找到关联表名称")
                    return None
                
                # 保存当前表格状态
                original_table = session.get_current_table()
                original_table_id = session.get_current_table_id()
                
                if not original_table or not original_table_id:
                    print("❌ 无法保存当前表格状态")
                    return None
                
                # 切换到关联表
                print(f"\n切换到关联表 '{foreign_table_name}' 创建新记录...")
                use_table(client, session, foreign_table_name)
                
                # 使用交互式模式插入记录
                print(f"\n为关联表 '{foreign_table_name}' 创建新记录:")
                insert_result, new_record_id = insert_record(client, session, [])
                
                # 无论成功与否，都要切换回原表格
                try:
                    if original_table and original_table_id:
                        use_table(client, session, original_table)
                        print(f"\n已切换回原表格: {original_table}")
                except Exception as restore_error:
                    print(f"⚠️  切换回原表格时出错: {restore_error}")
                    # 尝试手动恢复session状态
                    try:
                        session.set_current_table(original_table, original_table_id)
                    except:
                        pass
                
                if insert_result == 0 and new_record_id:
                    print(f"✅ 成功创建新关联记录，ID: {new_record_id}")
                    return new_record_id
                else:
                    print("❌ 创建新记录失败")
                    return None
                    
            except Exception as e:
                print(f"❌ 创建新记录时出错: {e}")
                # 确保切换回原表格
                if original_table and original_table_id:
                    try:
                        use_table(client, session, original_table)
                        print(f"\n已切换回原表格: {original_table}")
                    except Exception as restore_error:
                        print(f"⚠️  切换回原表格时出错: {restore_error}")
                        # 尝试手动恢复session状态
                        try:
                            session.set_current_table(original_table, original_table_id)
                        except:
                            pass
                return None
        else:
            # 没有session，使用简单的API调用
            print("❌ 无法创建新记录：缺少会话信息")
            return None
    
    if isinstance(result, list):
        # 多个匹配结果，需要交互式选择
        selected_record = interactive_select_linked_record(result, field_name)
        if selected_record is None:
            print("❌ 用户取消选择关联记录")
            return None
        result = selected_record
    
    # 返回关联记录的ID
    linked_record_id = result.get('id')
    if linked_record_id:
        # 尝试获取显示值用于确认
        fields = result.get('fields', {})
        display_value = None
        for display_field in ['name', 'title', 'label', 'display_name']:
            if display_field in fields and fields[display_field]:
                display_value = str(fields[display_field])
                break
        if display_value:
            print(f"✅ 找到关联记录: {display_value} (ID: {linked_record_id})")
        else:
            print(f"✅ 找到关联记录，ID: {linked_record_id}")
    
    return linked_record_id


def insert_record(client, session, args: list):
    """插入记录，返回(状态码, 记录ID)元组"""
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        
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
                
                # 特殊处理关联字段
                if field_type == 'link':
                    value = input(f"{field_name} (关联字段，直接回车跳过): ").strip()
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
                            print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                    # 无论是否输入值，都继续处理下一个字段
                    continue
                
                # 处理普通字段
                value = input(f"{field_name} ({field_type}，直接回车跳过): ").strip()
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
                return 0, None
        else:
            # 命令行参数模式
            # 格式: field1=value1 field2=value2
            record_data = {}
            for arg in args:
                if '=' in arg:
                    field_name, value = arg.split('=', 1)
                    
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
                            print(f"⚠️  跳过关联字段 '{field_name}'，未找到有效关联记录")
                        continue
                    else:
                        # 普通字段，需要根据字段类型转换值
                        # 查找字段类型
                        field_type = None
                        for field in fields:
                            if field.get('name') == field_name:
                                field_type = field.get('type', 'singleLineText')
                                break
                        
                        # 根据字段类型转换值
                        if field_type in ['number', 'percent']:
                            try:
                                value = float(value)
                            except ValueError:
                                print(f"警告: {field_name} 需要数字，跳过该字段")
                                continue
                        elif field_type == 'checkbox':
                            value = value.lower() in ['true', '1', 'yes', '是']
                        elif field_type == 'multipleSelect':
                            value = [v.strip() for v in value.split(',')]
                        # date类型保持字符串格式，由API处理
                        
                        record_data[field_name] = value
        
        if not record_data:
            print("没有有效数据，取消插入")
            return 0, None
        
        # 插入记录 - 使用正确的insert_records方法
        result = client.insert_records(table_id, [{'fields': record_data}])
        
        if result and 'records' in result:
            inserted_record = result['records'][0]
            record_id = inserted_record.get('id')
            print(f"✅ 成功插入记录，ID: {record_id}")
            return 0, record_id
        else:
            print("❌ 插入记录失败")
            return 1, None
            
    except Exception as e:
        print(f"错误: 插入记录失败: {e}")
        return 1, None


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
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
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
                                # 关联字段需要使用 [{'id': record_id}] 格式（manyMany关系）
                                update_data[field_name] = [{'id': linked_record_id}]
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
        
        if has_link_fields:
            # 使用字段ID模式更新关联字段
            result = client.update_record(table_id, record_id, update_data, use_field_ids=False)
        else:
            # 普通更新
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
                    field_name = field_name.strip()
                    value = value.strip()
                    where_conditions[f"{field_name}__gte"] = value
                elif '<=' in condition:
                    field_name, value = condition.split('<=', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    where_conditions[f"{field_name}__lte"] = value
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
