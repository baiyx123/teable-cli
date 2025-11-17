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


def insert_record(client, session, args: list):
    """插入记录，返回(状态码, 记录ID)元组"""
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        logger.info(f"开始插入记录到表格 '{table_name}' (ID: {table_id})")
        
        # 检测是否有管道输入 - 智能管道模式
        from .pipe_core import is_pipe_input, has_pipe_input_data, parse_pipe_input_line
        
        if is_pipe_input():
            # 管道输入模式：从管道读取记录并插入
            return insert_pipe_mode(client, session, table_id, table_name, args)
        
        # 获取字段信息和关联字段
        fields = client.get_table_fields(table_id)
        link_fields = detect_link_fields(client, table_id)
        
        logger.debug(f"获取到 {len(fields)} 个字段，其中 {len(link_fields)} 个关联字段")
        
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
            for arg in args:
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
        
        # 插入记录 - 使用正确的insert_records方法
        logger.info(f"准备插入记录，包含字段: {list(record_data.keys())}")
        result = client.insert_records(table_id, [{'fields': record_data}])
        
        if result and 'records' in result:
            inserted_record = result['records'][0]
            record_id = inserted_record.get('id')
            logger.info(f"成功插入记录，ID: {record_id}")
            print(f"✅ 成功插入记录，ID: {record_id}")
            return 0, record_id
        else:
            logger.error("插入记录失败：API返回结果异常")
            print("❌ 插入记录失败")
            return 1, None
            
    except Exception as e:
        logger.error(f"插入记录失败: {e}", exc_info=True)
        print(f"错误: 插入记录失败: {e}")
        return 1, None


def insert_pipe_mode(client, session, table_id: str, table_name: str, args: list):
    """管道模式的insert命令 - 从管道流式读取记录并批量插入"""
    try:
        # 检测是否有管道输出（链式管道操作）
        from .pipe_core import is_pipe_output
        
        if is_pipe_output():
            print(f"正在从管道流式读取记录进行批量插入（链式管道模式）...")
        else:
            print(f"正在从管道流式读取记录进行批量插入...")
        
        # 确保导入解析函数
        from .pipe_core import parse_pipe_input_line
        
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
                        if source_field in pipe_fields:
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
            result = client.insert_records(table_id, insert_records)
            if result and 'records' in result:
                inserted_count = len(result['records'])
                batch_success += inserted_count
                logger.info(f"成功插入批次: {inserted_count} 条记录 (累计: {progress_count})")
                
                # 如果有管道输出，输出插入的记录（链式管道操作）
                from .pipe_core import is_pipe_output, format_record_for_pipe
                if is_pipe_output():
                    for inserted_record in result['records']:
                        output_line = format_record_for_pipe(inserted_record)
                        print(output_line, flush=True)
            else:
                logger.warning(f"批次插入失败: {len(insert_records)} 条记录")
                batch_errors += len(insert_records)
        
        return batch_success, batch_errors
        
    except Exception as e:
        logger.error(f"批次插入失败: {e}", exc_info=True)
        print(f"⚠️  批次插入失败 ({len(batch_records)} 条记录): {e}")
        return 0, len(batch_records)


def update_record(client, session, args: list):
    """更新记录，支持条件更新（where语法）和智能管道操作，支持指定表名"""
    try:
        # 检测是否有管道输入 - 智能管道模式
        from .pipe_core import is_pipe_input, has_pipe_input_data, parse_pipe_input_line
        
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
        
        if is_pipe_input():
            # 管道输入模式：从管道读取记录并更新
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
            print(f"切换到表格 '{table_name}' 进行更新...")
        
        print(f"正在从管道流式读取记录进行批量更新...")
        
        # 确保导入解析函数
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
        
        # 解析where条件（支持@字段名语法和常量值）
        where_conditions = []
        for arg in where_args:
            if '=' in arg:
                field_name, value = arg.split('=', 1)
                field_name = field_name.strip()
                value = value.strip()
                
                if value.startswith('@') or value.startswith('$'):
                    where_conditions.append({
                        'field': field_name,
                        'type': 'field_mapping',
                        'source_field': value[1:],
                        'operator': '='
                    })
                else:
                    where_conditions.append({
                        'field': field_name,
                        'type': 'constant',
                        'value': value,
                        'operator': '='
                    })
            elif '>' in arg and not arg.startswith('>'):
                field_name, value = arg.split('>', 1)
                field_name = field_name.strip()
                value = value.strip()
                
                if value.startswith('@') or value.startswith('$'):
                    where_conditions.append({
                        'field': field_name,
                        'type': 'field_mapping',
                        'source_field': value[1:],
                        'operator': '>'
                    })
                else:
                    where_conditions.append({
                        'field': field_name,
                        'type': 'constant',
                        'value': value,
                        'operator': '>'
                    })
            elif '<' in arg and not arg.startswith('<'):
                field_name, value = arg.split('<', 1)
                field_name = field_name.strip()
                value = value.strip()
                
                if value.startswith('@') or value.startswith('$'):
                    where_conditions.append({
                        'field': field_name,
                        'type': 'field_mapping',
                        'source_field': value[1:],
                        'operator': '<'
                    })
                else:
                    where_conditions.append({
                        'field': field_name,
                        'type': 'constant',
                        'value': value,
                        'operator': '<'
                    })
        
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
        
        # 构建查询条件（使用管道记录中的值替换@字段名）
        filter_set = []
        for condition in where_conditions:
            field_name = condition['field']
            operator = condition['operator']
            
            # 确定条件值
            if condition['type'] == 'field_mapping':
                source_field = condition['source_field']
                if source_field in pipe_fields:
                    condition_value = pipe_fields[source_field]
                else:
                    logger.warning(f"管道记录中不存在字段 '{source_field}'，跳过条件 '{field_name}'")
                    continue
            else:
                condition_value = condition['value']
            
            # 构建过滤条件
            if operator == '=':
                filter_set.append({
                    "fieldId": field_name,
                    "operator": "is",
                    "value": condition_value
                })
            elif operator == '>':
                filter_set.append({
                    "fieldId": field_name,
                    "operator": "isGreater",
                    "value": condition_value
                })
            elif operator == '<':
                filter_set.append({
                    "fieldId": field_name,
                    "operator": "isLess",
                    "value": condition_value
                })
        
        if not filter_set:
            logger.warning("没有有效的查询条件，跳过")
            return 0
        
        # 查询匹配的记录
        query_params = {
            'filter': json.dumps({
                "conjunction": "and",
                "filterSet": filter_set
            }),
            'take': 1000,  # 限制每次最多更新1000条
            'skip': 0
        }
        
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


def _parse_where_conditions(where_args: list) -> Dict[str, str]:
    """解析where条件参数，返回条件字典"""
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
    """显示当前表格数据 - 支持智能管道操作和关联查询"""
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        return 1
    
    try:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        # 检测是否有管道输入（关联查询模式）
        from .pipe_core import is_pipe_input, has_pipe_input_data, parse_pipe_input_line
        
        if is_pipe_input() and has_pipe_input_data():
            # 管道输入模式：关联查询
            return show_pipe_input_mode(client, session, args, table_id, table_name)
        
        # 检测是否为管道输出模式
        if is_pipe_output():
            return show_pipe_mode(client, session, args, table_id, table_name)
        
        # 原有终端显示模式
        return show_table_mode(client, session, args, table_id, table_name)
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}")
        logger.error(f"显示表格数据失败: {e}", exc_info=True)
        return 1


def show_pipe_input_mode(client, session, args: list, table_id: str, table_name: str):
    """管道输入模式的show命令 - 关联查询，根据管道记录中的值查询当前表"""
    try:
        from .pipe_core import parse_pipe_input_line, format_record_for_pipe
        
        print(f"正在从管道读取记录进行关联查询...")
        
        # 解析查询条件参数，支持@字段名语法
        where_conditions = {}
        limit = None
        order_by = None
        order_direction = 'asc'
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        
        # 解析参数
        for arg in args:
            if arg.startswith('limit='):
                try:
                    limit = int(arg.split('=', 1)[1])
                except ValueError:
                    pass
            elif arg.startswith('order='):
                order_spec = arg.split('=', 1)[1]
                if ':' in order_spec:
                    order_by_name, order_direction = order_spec.split(':', 1)
                    order_direction = order_direction.lower()
                    if order_direction not in ['asc', 'desc']:
                        order_direction = 'asc'
                    order_by = order_by_name
                else:
                    order_by = order_spec
            else:
                # 处理where条件，支持@字段名语法
                condition = arg
                if 'like' in condition:
                    field_name, value = condition.split('like', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__like"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__like"] = {
                            'type': 'constant',
                            'value': value
                        }
                elif '>=' in condition:
                    field_name, value = condition.split('>=', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__gte"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__gte"] = {
                            'type': 'constant',
                            'value': value
                        }
                elif '<=' in condition:
                    field_name, value = condition.split('<=', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__lte"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__lte"] = {
                            'type': 'constant',
                            'value': value
                        }
                elif '>' in condition and not condition.startswith('>'):
                    field_name, value = condition.split('>', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__gt"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__gt"] = {
                            'type': 'constant',
                            'value': value
                        }
                elif '<' in condition and not condition.startswith('<'):
                    field_name, value = condition.split('<', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__lt"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__lt"] = {
                            'type': 'constant',
                            'value': value
                        }
                elif '=' in condition:
                    field_name, value = condition.split('=', 1)
                    field_name = field_name.strip()
                    value = value.strip()
                    if value.startswith('@') or value.startswith('$'):
                        where_conditions[f"{field_name}__eq"] = {
                            'type': 'field_mapping',
                            'source_field': value[1:]
                        }
                    else:
                        where_conditions[f"{field_name}__eq"] = {
                            'type': 'constant',
                            'value': value
                        }
        
        if not where_conditions:
            print("错误: 关联查询模式下必须指定where条件（使用@字段名从管道记录中获取值）")
            print("示例: t show 订单表 | t show 客户表 where 客户ID=@订单客户ID")
            return 1
        
        # 流式处理：对于每条管道记录，查询匹配的记录
        total_processed = 0
        total_found = 0
        
        print(f"开始关联查询处理...")
        
        # 从管道流式读取记录
        try:
            for line in sys.stdin:
                pipe_record = parse_pipe_input_line(line)
                if pipe_record:
                    # 对于每条管道记录，构建查询条件并查询匹配的记录
                    found_count = _process_show_pipe_input(client, table_id, pipe_record, 
                                                          where_conditions, fields, limit, 
                                                          order_by, order_direction)
                    total_processed += 1
                    total_found += found_count
                    
                    if total_processed % 50 == 0:
                        logger.info(f"关联查询进度: 已处理 {total_processed} 条管道记录，找到 {total_found} 条匹配记录")
        
        except KeyboardInterrupt:
            print(f"\n用户中断，正在处理剩余记录...")
        
        if total_processed > 0:
            logger.info(f"关联查询完成，共处理 {total_processed} 条管道记录，找到 {total_found} 条匹配记录")
            return 0
        else:
            print("错误: 没有从管道接收到有效的记录数据")
            return 1
            
    except Exception as e:
        print(f"错误: 关联查询模式失败: {e}")
        logger.error(f"关联查询模式失败: {e}", exc_info=True)
        return 1


def _process_show_pipe_input(client, table_id: str, pipe_record: Dict[str, Any],
                            where_conditions: Dict[str, Dict[str, Any]], 
                            fields: List[Dict[str, Any]], limit: Optional[int],
                            order_by: Optional[str], order_direction: str) -> int:
    """处理关联查询：根据管道记录中的值查询匹配的记录"""
    try:
        pipe_fields = pipe_record.get('fields', {})
        
        # 构建查询条件（使用管道记录中的值替换@字段名）
        filter_set = []
        for condition_key, condition_info in where_conditions.items():
            # 解析条件键，获取字段名和操作符
            field_name = condition_key
            operator = "is"
            
            if condition_key.endswith('__eq'):
                field_name = condition_key.replace('__eq', '')
                operator = "is"
            elif condition_key.endswith('__gt'):
                field_name = condition_key.replace('__gt', '')
                operator = "isGreater"
            elif condition_key.endswith('__gte'):
                field_name = condition_key.replace('__gte', '')
                operator = "isGreaterEqual"
            elif condition_key.endswith('__lt'):
                field_name = condition_key.replace('__lt', '')
                operator = "isLess"
            elif condition_key.endswith('__lte'):
                field_name = condition_key.replace('__lte', '')
                operator = "isLessEqual"
            elif condition_key.endswith('__like'):
                field_name = condition_key.replace('__like', '')
                operator = "contains"
            
            # 确定条件值
            if condition_info['type'] == 'field_mapping':
                source_field = condition_info['source_field']
                if source_field in pipe_fields:
                    condition_value = pipe_fields[source_field]
                else:
                    logger.warning(f"管道记录中不存在字段 '{source_field}'，跳过条件 '{field_name}'")
                    continue
            else:
                condition_value = condition_info['value']
            
            # 构建过滤条件
            filter_set.append({
                "fieldId": field_name,
                "operator": operator,
                "value": condition_value
            })
        
        if not filter_set:
            logger.warning("没有有效的查询条件，跳过")
            return 0
        
        # 构建查询参数
        query_params = {
            'filter': json.dumps({
                "conjunction": "and",
                "filterSet": filter_set
            }),
            'take': limit if limit else 1000,  # 限制每次最多查询1000条
            'skip': 0
        }
        
        # 添加排序参数
        if order_by:
            order_config = [{
                "fieldId": order_by,
                "order": order_direction
            }]
            query_params['orderBy'] = json.dumps(order_config)
        
        # 查询匹配的记录
        records_data = client.get_records(table_id, **query_params)
        matched_records = records_data.get('records', [])
        
        if not matched_records:
            logger.debug(f"没有找到匹配的记录，跳过")
            return 0
        
        # 输出匹配的记录（管道格式）
        for record in matched_records:
            output_line = format_record_for_pipe(record)
            print(output_line, flush=True)
        
        return len(matched_records)
        
    except Exception as e:
        logger.error(f"关联查询处理失败: {e}", exc_info=True)
        return 0


def show_pipe_mode(client, session, args: list, table_id: str, table_name: str):
    """管道模式的show命令 - 真正的流式处理，查询一页→输出→下一页"""
    try:
        # 解析参数
        limit = None  # 默认不限制
        where_conditions = {}
        order_by = None
        order_direction = 'asc'
        page_size = 100  # 每页大小，用于流式处理
        
        # 获取字段信息
        fields = client.get_table_fields(table_id)
        
        # 解析查询条件参数
        for arg in args:
            if arg.startswith('limit='):
                try:
                    limit = int(arg.split('=', 1)[1])
                except ValueError:
                    pass
            elif arg.startswith('page_size='):
                try:
                    page_size = int(arg.split('=', 1)[1])
                    if page_size < 10 or page_size > 1000:
                        page_size = 100  # 限制范围
                except ValueError:
                    pass
            elif arg.startswith('order='):
                order_spec = arg.split('=', 1)[1]
                if ':' in order_spec:
                    order_by_name, order_direction = order_spec.split(':', 1)
                    order_direction = order_direction.lower()
                    if order_direction not in ['asc', 'desc']:
                        order_direction = 'asc'
                    order_by = order_by_name
                else:
                    order_by = order_spec
            else:
                # 处理where条件
                condition = arg
                if 'like' in condition:
                    field_name, value = condition.split('like', 1)
                    where_conditions[f"{field_name.strip()}__like"] = value.strip()
                elif '>=' in condition:
                    field_name, value = condition.split('>=', 1)
                    where_conditions[f"{field_name.strip()}__gte"] = value.strip()
                elif '<=' in condition:
                    field_name, value = condition.split('<=', 1)
                    where_conditions[f"{field_name.strip()}__lte"] = value.strip()
                elif '>' in condition:
                    field_name, value = condition.split('>', 1)
                    where_conditions[f"{field_name.strip()}__gt"] = value.strip()
                elif '<' in condition:
                    field_name, value = condition.split('<', 1)
                    where_conditions[f"{field_name.strip()}__lt"] = value.strip()
                elif '=' in condition:
                    field_name, value = condition.split('=', 1)
                    where_conditions[f"{field_name.strip()}__eq"] = value.strip()
        
        # 构建基础查询参数
        base_query_params = {}
        
        # 构建过滤条件
        if where_conditions:
            filter_set = []
            for field, value in where_conditions.items():
                field_name = field
                operator = "is"
                if field.endswith('__gt'):
                    field_name = field.replace('__gt', '')
                    operator = "isGreater"
                elif field.endswith('__gte'):
                    field_name = field.replace('__gte', '')
                    operator = "isGreaterEqual"
                elif field.endswith('__lt'):
                    field_name = field.replace('__lt', '')
                    operator = "isLess"
                elif field.endswith('__lte'):
                    field_name = field.replace('__lte', '')
                    operator = "isLessEqual"
                elif field.endswith('__eq'):
                    field_name = field.replace('__eq', '')
                    operator = "is"
                elif field.endswith('__like'):
                    field_name = field.replace('__like', '')
                    operator = "contains"
                
                filter_set.append({
                    "fieldId": field_name,
                    "operator": operator,
                    "value": value
                })
            
            base_query_params['filter'] = json.dumps({
                "conjunction": "and",
                "filterSet": filter_set
            })
        
        # 构建排序参数
        if order_by:
            order_config = [{
                "fieldId": order_by,
                "order": order_direction
            }]
            base_query_params['orderBy'] = json.dumps(order_config)
        
        # 真正的流式处理 - 查询一页，输出一页，再查询下一页
        total_processed = 0
        page = 1
        
        while True:
            # 计算当前页参数
            skip = (page - 1) * page_size
            current_limit = page_size
            
            # 如果指定了总limit，需要调整
            if limit and total_processed + page_size > limit:
                current_limit = limit - total_processed
            
            if current_limit <= 0:
                break
            
            # 构建当前页查询参数
            query_params = base_query_params.copy()
            query_params['take'] = current_limit
            query_params['skip'] = skip
            
            # 获取当前页数据
            logger.info(f"查询第{page}页数据: skip={skip}, take={current_limit}")
            records_data = client.get_records(table_id, **query_params)
            records = records_data.get('records', [])
            
            logger.info(f"第{page}页获取到 {len(records)} 条记录")
            
            if not records:
                logger.info(f"第{page}页没有记录，结束查询")
                break
            
            # 流式输出当前页记录 - 立即输出，不缓存
            for record in records:
                output_line = format_record_for_pipe(record)
                print(output_line, flush=True)
            
            total_processed += len(records)
            
            # 如果获取的记录数少于请求的页大小，说明没有更多数据了
            if len(records) < current_limit:
                logger.info(f"第{page}页记录数({len(records)})少于请求数({current_limit})，结束查询")
                break
            
            # 如果指定了limit且已经达到limit，结束查询
            if limit and total_processed >= limit:
                break
            
            # 显示进度（可选）
            if page % 5 == 0:  # 每5页显示一次进度
                logger.info(f"流式处理进度: 已处理 {total_processed} 条记录")
            
            page += 1
        
        logger.info(f"流式处理完成: 共输出 {total_processed} 条记录")
        return 0
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}")
        return 1


def show_table_mode(client, session, args: list, table_id: str, table_name: str):
    """表格显示模式（原有功能）"""
    try:
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
        
        # 准备数据 - 添加recordId作为第一列
        rows = []
        for record in records:
            record_id = record.get('id', '')
            record_fields = record.get('fields', {})
            row = [record_id]  # 第一列是记录ID
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
            
            # 添加recordId列作为第一列
            table.add_column("记录ID", style="yellow", no_wrap=False)
            for field_name in field_names:
                table.add_column(field_name, style="cyan", no_wrap=False)
            
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            
            console.print(table)
        else:
            # 非终端环境使用tabulate - 添加recordId到表头
            headers = ["记录ID"] + field_names
            print(tabulate(rows, headers=headers, tablefmt='simple'))
        
        # 显示统计信息
        total_count = records_data.get('total', len(records))
        print(f"\n📊 显示 {len(records)}/{total_count} 条记录")
        
        return 0
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}")
        return 1
