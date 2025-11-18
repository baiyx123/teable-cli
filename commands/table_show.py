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
    _build_query_params_from_conditions
)

def show_current_table(client, session, args: list):
    """显示当前表格数据 - 支持智能管道操作和关联查询"""
    if not client:
        print("错误: 无法连接到Teable服务", file=sys.stderr)
        return 1
    
    # 检查第一个参数是否是表名
    target_table_name = None
    remaining_args = args
    
    if args:
        first_arg = args[0]
        # 判断是否是表名：不是字段=值格式，不是limit=, order=等参数
        is_field_assignment = '=' in first_arg
        is_limit_or_order = first_arg.lower().startswith(('limit=', 'order='))
        
        if not is_field_assignment and not is_limit_or_order:
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
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
    elif not session.is_table_selected():
        print("错误: 请先选择表格", file=sys.stderr)
        return 1
    else:
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
    
    try:
        from .pipe_core import is_pipe_input, is_pipe_output
        
        # 管道输出模式：优先检查，如果输出到管道，使用流式输出
        if is_pipe_output():
            return show_pipe_mode(client, session, remaining_args, table_id, table_name)
        
        # 管道输入模式（关联查询）：有管道输入且有where条件
        if is_pipe_input():
            # 检查是否有where条件（排除limit=, order=等参数）
            has_where = any(
                arg.lower() == 'where' or 
                ('=' in arg and not arg.lower().startswith(('limit=', 'order=')))
                for arg in remaining_args
            )
            if has_where:
                return show_pipe_input_mode(client, session, remaining_args, table_id, table_name)
        
        # 终端显示模式
        return show_table_mode(client, session, remaining_args, table_id, table_name)
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}", file=sys.stderr)
        logger.error(f"显示表格数据失败: {e}", exc_info=True)
        return 1



def show_pipe_input_mode(client, session, args: list, table_id: str, table_name: str):
    """管道输入模式的show命令 - 关联查询，根据管道记录中的值查询当前表"""
    try:
        from .pipe_core import parse_pipe_input_line, format_record_for_pipe
        
        # 解析查询条件参数，支持@字段名语法
        where_args = []
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
                # 收集where条件参数
                where_args.append(arg)
        
        # 使用通用函数解析where条件
        where_conditions = _parse_where_conditions_with_mapping(where_args)
        
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
            # 使用迭代器读取，避免阻塞
            import sys
            
            # 尝试读取第一行，如果没有数据或读取失败，回退到正常模式
            try:
                first_line = sys.stdin.readline()
                logger.info(f"管道输入模式：读取第一行: {repr(first_line)}")
                if not first_line or not first_line.strip():
                    # 没有数据，回退到正常模式
                    logger.info("管道输入模式：没有数据，回退到正常模式")
                    return show_table_mode(client, session, args, table_id, table_name)
            except Exception as e:
                # 读取失败，回退到正常模式
                logger.info(f"管道输入模式：读取失败，回退到正常模式: {e}")
                return show_table_mode(client, session, args, table_id, table_name)
            
            # 先处理第一行
            pipe_record = parse_pipe_input_line(first_line)
            if pipe_record:
                found_count = _process_show_pipe_input(client, table_id, pipe_record, 
                                                      where_conditions, fields, limit, 
                                                      order_by, order_direction)
                total_found += found_count
            
            # 继续读取剩余行
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
        except Exception as e:
            # 如果读取失败，回退到正常模式
            logger.debug(f"管道读取失败，回退到正常模式: {e}")
            return show_table_mode(client, session, args, table_id, table_name)
        
        if total_processed > 0:
            logger.info(f"关联查询完成，共处理 {total_processed} 条管道记录，找到 {total_found} 条匹配记录")
            return 0
        else:
            # 没有读取到数据，回退到正常模式
            return show_table_mode(client, session, args, table_id, table_name)
            
    except Exception as e:
        print(f"错误: 关联查询模式失败: {e}")
        logger.error(f"关联查询模式失败: {e}", exc_info=True)
        return 1



def _process_show_pipe_input(client, table_id: str, pipe_record: Dict[str, Any],
                            where_conditions: List[Dict[str, Any]], 
                            fields: List[Dict[str, Any]], limit: Optional[int],
                            order_by: Optional[str], order_direction: str) -> int:
    """处理关联查询：根据管道记录中的值查询匹配的记录"""
    try:
        pipe_fields = pipe_record.get('fields', {})
        
        # 使用通用函数构建查询参数
        query_params = _build_query_params_from_conditions(
            conditions=where_conditions,
            pipe_fields=pipe_fields,
            limit=limit if limit else 1000,
            skip=0,
            order_by=order_by,
            order_direction=order_direction
        )
        
        if 'filter' not in query_params:
            logger.warning("没有有效的查询条件，跳过")
            return 0
        
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
        print(f"错误: 显示表格数据失败: {e}", file=sys.stderr)
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
            # 提示信息输出到stderr
            if sys.stdout.isatty():
                print(f"表格 '{table_name}' 中没有记录", file=sys.stderr)
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
        
        # 统一输出格式：总是输出标准管道格式到stdout
        from .pipe_core import format_record_for_pipe
        for record in records:
            output_line = format_record_for_pipe(record)
            print(output_line, flush=True)
        
        # 如果输出到终端，额外显示人类可读的表格到stderr
        if sys.stdout.isatty():
            if console.is_terminal:
                table = Table(title=f"表格: {table_name}")
                
                # 添加recordId列作为第一列
                table.add_column("记录ID", style="yellow", no_wrap=False)
                for field_name in field_names:
                    table.add_column(field_name, style="cyan", no_wrap=False)
                
                for row in rows:
                    table.add_row(*[str(cell) for cell in row])
                
                console.print(table, file=sys.stderr)
            else:
                # 非终端环境使用tabulate - 添加recordId到表头
                headers = ["记录ID"] + field_names
                print(tabulate(rows, headers=headers, tablefmt='simple'), file=sys.stderr)
            
            # 显示统计信息到stderr
            total_count = records_data.get('total', len(records))
            print(f"\n📊 显示 {len(records)}/{total_count} 条记录", file=sys.stderr)
        
        return 0
        
    except Exception as e:
        print(f"错误: 显示表格数据失败: {e}", file=sys.stderr)
        return 1


