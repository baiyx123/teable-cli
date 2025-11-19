#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建表格命令
"""

import logging
from typing import Dict, List, Any, Optional
from teable_api_client import (
    create_field_config, 
    create_link_field_config,
    create_formula_field_config,
    SUPPORTED_FIELD_TYPES,
    LINK_FIELD_TYPES
)

logger = logging.getLogger(__name__)


def create_table_command(client, session, args: list):
    """创建表格命令
    
    用法:
        t create <表名> [字段定义...]
        t create <表名> --desc <描述> [字段定义...]
    
    字段定义格式:
        <字段名>:<字段类型>                    - 普通字段
        <字段名>:<字段类型>:unique             - 带唯一约束的字段
        <字段名>:<字段类型>:required           - 必填字段
        <字段名>:<字段类型>:unique:required    - 唯一且必填的字段
        <字段名>:number:<精度>                 - 数字字段（精度为小数位数，0表示整数）
        <字段名>:number:<精度>:unique          - 带唯一约束的数字字段
        <字段名>:link:<关联关系>:<目标表名>      - 关联字段（需要目标表已存在）
        <字段名>:formula:<表达式>              - 公式字段（表达式使用 {字段名} 引用其他字段）
    
    字段类型:
        singleLineText    - 单行文本
        longText         - 长文本
        number           - 数字
        checkbox         - 复选框
        singleSelect     - 单选（需要选项，格式: singleSelect:选项1,选项2）
        multipleSelect   - 多选（需要选项，格式: multipleSelect:选项1,选项2）
        date             - 日期
        rating           - 评分
        formula          - 公式
        rollup           - 汇总
        autoNumber       - 自动编号
        link             - 关联字段
        user             - 用户
        attachment       - 附件
    
    关联关系:
        manyOne    - 多对一
        oneMany    - 一对多
        manyMany   - 多对多
        oneOne     - 一对一
    
    示例:
        # 创建简单表
        t create 测试表 姓名:singleLineText 年龄:number
        
        # 创建带唯一约束的字段
        t create 用户表 用户名:singleLineText:unique 邮箱:singleLineText:unique
        
        # 创建必填字段
        t create 订单表 订单号:singleLineText:required 客户名称:singleLineText:required
        
        # 创建唯一且必填的字段
        t create 车辆表 车牌号:singleLineText:unique:required
        
        # 创建带描述的表
        t create 订单表 --desc "订单信息表" 订单号:singleLineText:unique 金额:number
        
        # 创建带精度的数字字段（整数）
        t create 订单表 订单号:singleLineText 数量:number:0
        
        # 创建带精度的数字字段（2位小数）
        t create 订单表 订单号:singleLineText 金额:number:2
        
        # 创建带唯一约束的数字字段
        t create 产品表 产品编号:number:0:unique
        
        # 创建带关联字段的表（需要先有客户表）
        t create 订单表 订单号:singleLineText 关联客户:link:manyOne:客户表
        
        # 创建带选项的表
        t create 状态表 状态名:singleLineText 类型:singleSelect:类型1,类型2
        
        # 创建带公式字段的表
        t create 订单明细表 单价:number 数量:number 总价:formula:{单价} * {数量}
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    if len(args) < 1:
        print("错误: 请指定表名")
        print("使用: t create <表名> [字段定义...]")
        print("使用: t help create 查看详细帮助")
        return 1
    
    # 解析参数
    table_name = None
    description = None
    field_definitions = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '--desc' or arg == '--description':
            if i + 1 < len(args):
                description = args[i + 1]
                i += 2
            else:
                print("错误: --desc 需要指定描述内容")
                return 1
        elif not table_name:
            # 第一个非选项参数是表名
            table_name = arg
            i += 1
        else:
            # 其余是字段定义
            field_definitions.append(arg)
            i += 1
    
    if not table_name:
        print("错误: 请指定表名")
        return 1
    
    try:
        # 检查表名是否已存在
        tables = client.get_tables()
        for table in tables:
            if table.get('name') == table_name:
                print(f"错误: 表格 '{table_name}' 已存在")
                return 1
        
        # 解析字段定义
        fields = []
        link_fields_to_add = []  # 关联字段需要单独添加
        formula_fields_to_add = []  # 公式字段需要单独添加（需要引用其他字段的ID）
        
        for field_def in field_definitions:
            # 字段定义格式: 字段名:字段类型[:选项...]
            parts = field_def.split(':')
            
            if len(parts) < 2:
                print(f"错误: 字段定义格式错误: {field_def}")
                print("格式: <字段名>:<字段类型>[:选项...]")
                return 1
            
            field_name = parts[0]
            field_type_raw = parts[1]
            field_type = field_type_raw.lower()  # 用于比较
            
            # 解析 unique 和 required 标志（可能在最后）
            is_unique = False
            is_required = False
            # 检查最后几个部分是否有 unique 或 required
            for part in parts[2:]:
                part_lower = part.lower()
                if part_lower == 'unique':
                    is_unique = True
                elif part_lower == 'required':
                    is_required = True
            
            # 处理关联字段
            if field_type == 'link':
                if len(parts) < 4:
                    print(f"错误: 关联字段定义格式错误: {field_def}")
                    print("格式: <字段名>:link:<关联关系>:<目标表名>")
                    return 1
                
                relationship_input = parts[2].lower()
                foreign_table_name = parts[3]
                
                # 验证关联关系并转换为API需要的格式
                relationship_map = {
                    'manyone': 'manyOne',
                    'onemany': 'oneMany',
                    'manymany': 'manyMany',
                    'oneone': 'oneOne'
                }
                
                if relationship_input not in relationship_map:
                    print(f"错误: 无效的关联关系 '{parts[2]}'")
                    print(f"支持的关联关系: manyOne, oneMany, manyMany, oneOne")
                    return 1
                
                relationship = relationship_map[relationship_input]  # 转换为API格式
                
                # 查找目标表
                foreign_table_id = None
                for table in tables:
                    if table.get('name') == foreign_table_name:
                        foreign_table_id = table.get('id')
                        break
                
                if not foreign_table_id:
                    print(f"错误: 找不到目标表格 '{foreign_table_name}'")
                    print("可用表格:")
                    for table in tables:
                        print(f"  - {table.get('name')}")
                    return 1
                
                # 关联字段需要在表创建后单独添加，先保存配置
                link_fields_to_add.append({
                    'name': field_name,
                    'relationship': relationship,
                    'foreign_table_id': foreign_table_id,
                    'foreign_table_name': foreign_table_name
                })
                print(f"  ⚠ 字段: {field_name} (link, {relationship} -> {foreign_table_name}) - 将在表创建后添加")
            
            # 处理公式字段
            elif field_type == 'formula':
                if len(parts) < 3:
                    print(f"错误: 公式字段定义格式错误: {field_def}")
                    print("格式: <字段名>:formula:<表达式>")
                    print("示例: 总价:formula:{单价} * {数量}")
                    return 1
                
                expression = ':'.join(parts[2:])  # 支持表达式中包含冒号
                formula_fields_to_add.append({
                    'name': field_name,
                    'expression': expression
                })
                print(f"  ⚠ 字段: {field_name} (formula) - 将在表创建后添加")
            
            # 处理number字段（支持精度参数）
            elif field_type == 'number':
                # 检查是否有精度参数（排除 unique 和 required）
                precision = None
                if len(parts) >= 3:
                    precision_str = parts[2]
                    # 如果第二部分是 unique 或 required，则没有精度参数
                    if precision_str.lower() not in ['unique', 'required']:
                        # 支持两种格式: precision=2 或直接数字 2
                        if '=' in precision_str:
                            # precision=2 格式
                            precision_value = precision_str.split('=')[1].strip()
                        else:
                            # 直接数字格式
                            precision_value = precision_str.strip()
                        
                        try:
                            precision = int(precision_value)
                        except ValueError:
                            print(f"  ⚠ 警告: 无效的精度值 '{precision_value}'，使用默认精度")
                
                # 默认精度为2（如果没有指定）
                if precision is None:
                    precision = 2
                
                # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                field_config = create_field_config(
                    name=field_name,
                    field_type=field_type_raw,  # 使用原始大小写
                    options={
                        'formatting': {
                            'type': 'decimal',
                            'precision': precision
                        }
                    }
                )
                fields.append(field_config)
                
                attrs = []
                attrs.append(f"精度={precision}")
                if is_unique:
                    attrs.append("唯一")
                if is_required:
                    attrs.append("必填")
                print(f"  ✓ 字段: {field_name} (number, {', '.join(attrs)})")
            
            # 处理带选项的字段（singleSelect, multipleSelect）
            elif field_type in ['singleselect', 'multipleselect']:
                if len(parts) >= 3:
                    # 有选项
                    options_str = ':'.join(parts[2:])  # 支持选项中包含冒号
                    options_list = [opt.strip() for opt in options_str.split(',')]
                    
                    # 转换为API需要的格式：[{"name": "选项名"}]
                    choices = [{"name": opt} for opt in options_list]
                    
                    # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                    field_config = create_field_config(
                        name=field_name,
                        field_type=field_type_raw,  # 使用原始大小写
                        options={'choices': choices}
                    )
                else:
                    # 无选项，使用默认配置
                    # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                    field_config = create_field_config(
                        name=field_name,
                        field_type=field_type_raw  # 使用原始大小写
                    )
                fields.append(field_config)
                
                attrs = []
                if len(parts) >= 3 and parts[2].lower() not in ['unique', 'required']:
                    attrs.append(f"选项: {', '.join(options_list)}")
                if is_unique:
                    attrs.append("唯一")
                if is_required:
                    attrs.append("必填")
                
                if attrs:
                    print(f"  ✓ 字段: {field_name} ({field_type_raw}, {', '.join(attrs)})")
                else:
                    print(f"  ✓ 字段: {field_name} ({field_type_raw})")
            
            # 处理普通字段（number已经在上面单独处理了）
            else:
                # 验证字段类型（使用原始大小写）
                if field_type_raw not in SUPPORTED_FIELD_TYPES:
                    print(f"错误: 不支持的字段类型 '{field_type_raw}'")
                    print(f"支持的字段类型: {', '.join(SUPPORTED_FIELD_TYPES)}")
                    return 1
                
                # 创建字段配置（使用原始大小写）
                # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                # 这些属性需要通过 Web 界面手动设置
                field_config = create_field_config(
                    name=field_name,
                    field_type=field_type_raw
                    # unique 和 notNull 在创建时会被忽略，所以不传递
                )
                fields.append(field_config)
                
                attrs = []
                if is_unique:
                    attrs.append("唯一")
                if is_required:
                    attrs.append("必填")
                
                if attrs:
                    print(f"  ✓ 字段: {field_name} ({field_type_raw}, {', '.join(attrs)})")
                else:
                    print(f"  ✓ 字段: {field_name} ({field_type_raw})")
        
        # 如果没有指定字段，创建默认字段
        if not fields:
            print("提示: 未指定字段，将创建空表")
            print("提示: 可以使用 't alter add' 命令添加字段")
        
        # 构建表格配置
        table_config = {
            "name": table_name,
            "fields": fields
        }
        
        if description:
            table_config["description"] = description
        
        # 创建表格
        print(f"\n正在创建表格 '{table_name}'...")
        if description:
            print(f"描述: {description}")
        print(f"字段数: {len(fields)}")
        if link_fields_to_add:
            print(f"关联字段数: {len(link_fields_to_add)} (将在表创建后添加)")
        
        result = client.create_table(table_config)
        
        table_id = result.get('id', '未知')
        print(f"\n✅ 表格创建成功!")
        print(f"   表格名称: {table_name}")
        print(f"   表格ID: {table_id}")
        print(f"   字段数: {len(fields)}")
        
        # 添加关联字段
        if link_fields_to_add:
            print(f"\n正在添加关联字段...")
            for link_field in link_fields_to_add:
                try:
                    field_config = create_link_field_config(
                        name=link_field['name'],
                        relationship=link_field['relationship'],
                        foreign_table_id=link_field['foreign_table_id']
                    )
                    add_result = client.add_field(table_id, field_config)
                    field_id = add_result.get('id', '未知')
                    print(f"  ✅ 关联字段 '{link_field['name']}' 添加成功 (ID: {field_id})")
                except Exception as e:
                    print(f"  ❌ 关联字段 '{link_field['name']}' 添加失败: {e}")
                    logger.error(f"添加关联字段失败: {e}", exc_info=True)
        
        # 添加公式字段（需要在表创建后，因为需要引用其他字段的ID）
        if formula_fields_to_add:
            print(f"\n正在添加公式字段...")
            # 获取所有字段的映射（字段名 -> 字段ID）
            table_fields = client.get_table_fields(table_id)
            field_name_to_id = {f['name']: f['id'] for f in table_fields}
            
            for formula_field in formula_fields_to_add:
                try:
                    # 将表达式中的字段名替换为字段ID
                    expression = formula_field['expression']
                    # 表达式格式：{字段名} -> { 字段ID }
                    for field_name, field_id in field_name_to_id.items():
                        # 替换 {字段名} 为 { 字段ID }
                        expression = expression.replace(f'{{{field_name}}}', f'{{ {field_id} }}')
                        expression = expression.replace(f'{{ {field_name} }}', f'{{ {field_id} }}')
                    
                    field_config = create_formula_field_config(
                        name=formula_field['name'],
                        expression=expression
                    )
                    add_result = client.add_field(table_id, field_config)
                    field_id = add_result.get('id', '未知')
                    print(f"  ✅ 公式字段 '{formula_field['name']}' 添加成功 (ID: {field_id})")
                except Exception as e:
                    print(f"  ❌ 公式字段 '{formula_field['name']}' 添加失败: {e}")
                    logger.error(f"添加公式字段失败: {e}", exc_info=True)
        
        # 自动切换到新创建的表
        from .table_common import use_table
        use_table(client, session, table_name)
        
        logger.info(f"表格创建成功: {table_name} (ID: {table_id})")
        return 0
        
    except Exception as e:
        print(f"错误: 创建表格失败: {e}")
        logger.error(f"创建表格失败: {e}", exc_info=True)
        return 1

