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
        if identifier.startswith('rec'):
            record = client.get_record(foreign_table_id, identifier)
            if record:
                return record
    except Exception as e:
        # 如果按ID查询失败，继续尝试其他方式
        # 注意: 此处仅在identifier不以'rec'开头时执行
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
                    table.get('id', 'N/A'),  # 显示完整ID以便复制使用
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
    
    # 如果 field_value 是记录ID格式（rec开头，长度合理），且是管道模式（session=None），直接返回
    # 这样可以避免不必要的查找，提高管道模式的性能
    if session is None and field_value.startswith('rec') and len(field_value) >= 15:
        # 管道模式下，直接使用记录ID，不需要查找
        logger.debug(f"管道模式：直接使用记录ID '{field_value}' 作为关联字段 '{field_name}' 的值")
        return field_value
    
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
                from .table_insert import insert_record
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



def is_field_editable(field: Dict[str, Any]) -> bool:
    """检查字段是否可编辑（非公式、非引用字段）"""
    field_type = field.get('type', '')
    is_lookup = field.get('isLookup', False)
    field_name = field.get('name', '未知')
    
    # 跳过公式字段和引用字段
    if field_type == 'formula':
        logger.debug(f"字段 '{field_name}' 是公式字段，不可编辑")
        return False
    
    if is_lookup:
        logger.debug(f"字段 '{field_name}' 是引用字段，不可编辑")
        return False
    
    return True



def get_field_default_value(field: Dict[str, Any]) -> Optional[Any]:
    """获取字段的默认值"""
    field_name = field.get('name', '未知')
    
    # 尝试从不同位置获取默认值
    defaultValue = field.get('defaultValue')
    if defaultValue is not None:
        logger.debug(f"字段 '{field_name}' 找到默认值: {defaultValue}")
        return defaultValue
    
    # 尝试从options中获取
    options = field.get('options', {})
    defaultValue = options.get('defaultValue')
    if defaultValue is not None:
        logger.debug(f"字段 '{field_name}' 从options中找到默认值: {defaultValue}")
        return defaultValue
    
    logger.debug(f"字段 '{field_name}' 没有默认值")
    return None



def is_field_required(field: Dict[str, Any]) -> bool:
    """检查字段是否必填"""
    field_name = field.get('name', '未知')
    
    # 尝试从不同位置获取required属性
    required = field.get('required', False)
    if required:
        logger.debug(f"字段 '{field_name}' 是必填字段")
        return True
    
    # 尝试从options中获取
    options = field.get('options', {})
    required = options.get('required', False)
    if required:
        logger.debug(f"字段 '{field_name}' 从options中标记为必填")
        return True
    
    logger.debug(f"字段 '{field_name}' 不是必填字段")
    return False



def convert_field_value(field_type: str, value: Any) -> Any:
    """根据字段类型转换值"""
    if field_type in ['number', 'percent', 'currency']:
        try:
            return float(value)
        except (ValueError, TypeError):
            return value
    elif field_type == 'checkbox':
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', '是']
        return bool(value)
    elif field_type == 'multipleSelect':
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [v.strip() for v in value.split(',')]
        return value
        return value
    return value



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



def _parse_where_condition_arg(arg: str) -> Optional[Dict[str, Any]]:
    """解析单个where条件参数，支持@字段名语法
    
    返回格式: {
        'field_name': str,
        'operator': str,  # =, >, <, >=, <=, like
        'type': str,  # 'field_mapping' 或 'constant'
        'source_field': str,  # 如果是field_mapping类型
        'value': Any  # 如果是constant类型
    }
    """
    arg = arg.strip()
    if not arg:
        return None
    
    # 解析操作符和字段名、值
    if 'like' in arg:
        field_name, value = arg.split('like', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = 'like'
    elif '>=' in arg:
        field_name, value = arg.split('>=', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = '>='
    elif '<=' in arg:
        field_name, value = arg.split('<=', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = '<='
    elif '>' in arg and not arg.startswith('>'):
        field_name, value = arg.split('>', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = '>'
    elif '<' in arg and not arg.startswith('<'):
        field_name, value = arg.split('<', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = '<'
    elif '=' in arg:
        field_name, value = arg.split('=', 1)
        field_name = field_name.strip()
        value = value.strip()
        operator = '='
    else:
        return None
    
    # 检查是否是字段映射语法（@字段名 或 $字段名）
    if value.startswith('@') or value.startswith('$'):
        return {
            'field_name': field_name,
            'operator': operator,
            'type': 'field_mapping',
            'source_field': value[1:]
        }
    else:
        return {
            'field_name': field_name,
            'operator': operator,
            'type': 'constant',
            'value': value
        }



def _parse_where_conditions_with_mapping(where_args: list) -> List[Dict[str, Any]]:
    """解析where条件参数列表，支持@字段名语法
    
    返回统一格式的条件列表，每个条件包含：
    {
        'field': str,  # 字段名
        'operator': str,  # =, >, <, >=, <=, like
        'type': str,  # 'field_mapping' 或 'constant'
        'source_field': str,  # 如果是field_mapping类型
        'value': Any  # 如果是constant类型
    }
    """
    conditions = []
    for arg in where_args:
        condition = _parse_where_condition_arg(arg)
        if condition:
            conditions.append({
                'field': condition['field_name'],
                'operator': condition['operator'],
                'type': condition['type'],
                'source_field': condition.get('source_field'),
                'value': condition.get('value')
            })
    return conditions



def _resolve_condition_value(condition: Dict[str, Any], pipe_fields: Dict[str, Any] = None) -> Optional[Any]:
    """解析条件值：从管道记录中获取或使用常量值
    
    Args:
        condition: 条件字典，包含 'type', 'source_field' 或 'value'
        pipe_fields: 管道记录的字段字典（可选）
    
    Returns:
        解析后的条件值，如果无法解析返回None
    """
    if condition['type'] == 'field_mapping':
        source_field = condition.get('source_field')
        if not source_field:
            return None
        if pipe_fields and source_field in pipe_fields:
            return pipe_fields[source_field]
        else:
            logger.warning(f"管道记录中不存在字段 '{source_field}'")
            return None
    else:
        return condition.get('value')



def _operator_to_api_operator(operator: str) -> str:
    """将条件操作符转换为API操作符"""
    operator_map = {
        '=': 'is',
        '>': 'isGreater',
        '>=': 'isGreaterEqual',
        '<': 'isLess',
        '<=': 'isLessEqual',
        'like': 'contains'
    }
    return operator_map.get(operator, 'is')



def _build_filter_set_from_conditions(conditions: List[Dict[str, Any]], 
                                     pipe_fields: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """从条件列表构建filter_set，支持从管道记录解析值
    
    Args:
        conditions: 条件列表，每个条件包含 field, operator, type, source_field/value
        pipe_fields: 管道记录的字段字典（可选，用于解析@字段名）
    
    Returns:
        filter_set列表，用于构建查询参数
    """
    filter_set = []
    for condition in conditions:
        field_name = condition['field']
        operator = condition['operator']
        
        # 解析条件值
        condition_value = _resolve_condition_value(condition, pipe_fields)
        if condition_value is None:
            logger.warning(f"无法解析条件值，跳过条件 '{field_name}'")
            continue
        
        # 转换为API操作符
        api_operator = _operator_to_api_operator(operator)
        
        # 构建过滤条件
        filter_set.append({
            "fieldId": field_name,
            "operator": api_operator,
            "value": condition_value
        })
    
    return filter_set



def _build_query_params_from_conditions(conditions: List[Dict[str, Any]], 
                                       pipe_fields: Dict[str, Any] = None,
                                       limit: Optional[int] = None,
                                       skip: int = 0,
                                       order_by: Optional[str] = None,
                                       order_direction: str = 'asc') -> Dict[str, Any]:
    """从条件列表构建完整的查询参数，支持从管道记录解析值
    
    Args:
        conditions: 条件列表
        pipe_fields: 管道记录的字段字典（可选）
        limit: 限制返回记录数
        skip: 跳过记录数
        order_by: 排序字段名
        order_direction: 排序方向（asc/desc）
    
    Returns:
        查询参数字典
    """
    query_params = {}
    
    # 构建filter_set
    if conditions:
        filter_set = _build_filter_set_from_conditions(conditions, pipe_fields)
        if filter_set:
            query_params['filter'] = json.dumps({
                "conjunction": "and",
                "filterSet": filter_set
            })
    
    # 设置分页参数
    if limit:
        query_params['take'] = limit
    if skip > 0:
        query_params['skip'] = skip
    
    # 设置排序参数
    if order_by:
        order_config = [{
            "fieldId": order_by,
            "order": order_direction
        }]
        query_params['orderBy'] = json.dumps(order_config)
    
    return query_params



def _parse_where_conditions(where_args: list) -> Dict[str, str]:
    """解析where条件参数，返回条件字典（旧版本，保持兼容）"""
    where_conditions = {}
    for arg in where_args:
        # 支持多种条件操作符
        if 'like' in arg:
            field_name, value = arg.split('like', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__like"] = value
        elif '>=' in arg:
            field_name, value = arg.split('>=', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__gte"] = value
        elif '<=' in arg:
            field_name, value = arg.split('<=', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__lte"] = value
        elif '>' in arg:
            field_name, value = arg.split('>', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__gt"] = value
        elif '<' in arg:
            field_name, value = arg.split('<', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__lt"] = value
        elif '=' in arg:
            field_name, value = arg.split('=', 1)
            field_name = field_name.strip()
            value = value.strip()
            where_conditions[f"{field_name}__eq"] = value
        else:
            print(f"警告: 无法解析的条件 '{arg}'，跳过")
    
    return where_conditions



def _build_query_params(where_conditions: Dict[str, str], limit: int = None) -> Dict[str, Any]:
    """构建查询参数，复用show_current_table的过滤逻辑"""
    query_params = {}
    
    if limit:
        query_params['take'] = limit
        query_params['skip'] = 0
    
    if where_conditions:
        filter_set = []
        for field, value in where_conditions.items():
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
                    "operator": "is",
                    "value": value
                })
            elif field.endswith('__like'):
                field_name = field.replace('__like', '')
                filter_set.append({
                    "fieldId": field_name,
                    "operator": "contains",
                    "value": value
                })
            else:
                # 默认使用精确匹配
                filter_set.append({
                    "fieldId": field_name,
                    "operator": "is",
                    "value": value
                })
        
        query_params['filter'] = json.dumps({
            "conjunction": "and",
            "filterSet": filter_set
        })
    
    return query_params


def show_table_schema(client, session, args: list):
    """显示表格结构（字段列表）
    
    用法:
        t desc [表名]
        t schema [表名]
        t fields [表名]
    
    如果不指定表名，显示当前表的字段结构
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    # 检查是否指定了表名
    table_name = None
    if args:
        table_name = args[0]
    
    # 获取表格ID
    if table_name:
        # 查找指定的表
        tables = client.get_tables()
        table_id = None
        for table in tables:
            if table.get('name') == table_name:
                table_id = table.get('id')
                table_name = table.get('name')
                break
        
        if not table_id:
            print(f"错误: 找不到表格 '{table_name}'")
            print("可用表格:")
            for table in tables:
                print(f"  - {table.get('name')}")
            return 1
    else:
        # 使用当前表
        if not session.is_table_selected():
            print("错误: 请先选择表格或指定表名")
            print("使用: t use 表格名称")
            print("或: t desc 表格名称")
            return 1
        
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
    
    try:
        # 获取字段列表
        fields = client.get_table_fields(table_id)
        
        if not fields:
            print(f"表格 '{table_name}' 没有字段")
            return 0
        
        # 显示表格信息
        print(f"\n=== 表格结构: {table_name} ===")
        print(f"表格ID: {table_id}")
        print(f"字段数量: {len(fields)}\n")
        
        # 显示字段列表
        print(f"{'序号':<4} {'字段名称':<40} {'字段类型':<20} {'说明':<10}")
        print("-" * 80)
        
        for i, field in enumerate(fields, 1):
            field_name = field.get('name', '未知')
            field_type = field.get('type', '未知')
            is_lookup = field.get('isLookup', False)
            
            # 格式化字段类型显示
            type_display = field_type
            if is_lookup:
                type_display += " (lookup)"
            
            # 获取字段描述或其他信息
            description = field.get('description', '')
            if not description:
                # 如果是关联字段，显示关联关系
                if field_type == 'link':
                    options = field.get('options', {})
                    relationship = options.get('relationship', '')
                    foreign_table_id = options.get('foreignTableId', '')
                    if relationship and foreign_table_id:
                        # 查找目标表名
                        tables = client.get_tables()
                        foreign_table_name = '未知表'
                        for table in tables:
                            if table.get('id') == foreign_table_id:
                                foreign_table_name = table.get('name')
                                break
                        description = f"{relationship} -> {foreign_table_name}"
            
            print(f"{i:<4} {field_name:<40} {type_display:<20} {description}")
        
        print()
        return 0
        
    except Exception as e:
        print(f"错误: 获取表格结构失败: {e}")
        logger.error(f"获取表格结构失败: {e}", exc_info=True)
        return 1

