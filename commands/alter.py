#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格结构修改命令
"""

import logging
from typing import Dict, List, Any, Optional
from teable_api_client import (
    create_field_config, 
    create_link_field_config,
    create_lookup_field_config,
    create_formula_field_config,
    SUPPORTED_FIELD_TYPES,
    LINK_FIELD_TYPES
)

logger = logging.getLogger(__name__)


def add_field_command(client, session, args: list):
    """添加字段命令
    
    用法:
        t alter add <字段名> <字段类型> [选项...]
        t alter add <字段名> link <关联关系> <目标表名> [字段名]
    
    字段类型:
        singleLineText    - 单行文本
        longText         - 长文本
        number           - 数字
        checkbox         - 复选框
        singleSelect     - 单选
        multipleSelect   - 多选
        date             - 日期
        currency         - 货币
        rating           - 评分
        formula          - 公式
        rollup           - 汇总
        autoNumber       - 自动编号
        link             - 关联字段
    
    关联字段:
        t alter add 关联客户 link manyOne 客户表
        t alter add 订单明细 link manyMany 货物明细表
    
    引用字段（Lookup）:
        t alter add <字段名> lookup <关联字段名> <引用字段名>
        示例: t alter add 客户名称 lookup 关联客户 客户名称
    
    示例:
        t alter add 目的城市 singleLineText
        t alter add 备注 longText
        t alter add 金额 number          # 默认精度2
        t alter add 数量 number 0        # 整数
        t alter add 金额 number 2        # 2位小数
        t alter add 用户名 singleLineText unique        # 唯一字段
        t alter add 邮箱 singleLineText unique required # 唯一且必填
        t alter add 客户名称 singleLineText required    # 必填字段
        t alter add 产品编号 number 0 unique             # 唯一数字字段
        t alter add 关联客户 link manyOne 客户表
        t alter add 客户名称 lookup 关联客户 客户名称
    
    修改字段属性:
        t alter modify 订单金额 precision 0    # 修改精度为整数
        t alter modify 订单金额 precision 2    # 修改精度为2位小数
        t alter modify 用户名 unique true       # 设置唯一约束
        t alter modify 用户名 unique false      # 取消唯一约束
        t alter modify 邮箱 required true      # 设置必填
        t alter modify 邮箱 required false     # 取消必填
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    # 检查是否指定了表名（第一个参数可能是表名）
    # 只有当第一个参数是表名且后面还有至少2个参数（字段名和字段类型），且第二个参数不是表名时，才认为是表名
    if len(args) >= 3:
        tables = client.get_tables()
        table_names = [t.get('name') for t in tables]
        
        # 如果第一个参数是表名，第二个参数不是表名，且第三个参数是字段类型，则认为是表名
        # 这样可以避免表达式中的表名被误判
        if (args[0] in table_names and 
            args[1] not in table_names and 
            args[2].lower() in ['formula', 'link', 'lookup'] + [t.lower() for t in SUPPORTED_FIELD_TYPES]):
            table_name_arg = args[0]
            args = args[1:]  # 移除表名参数
            # 临时切换表
            from .table_common import use_table
            use_table(client, session, table_name_arg)
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        print("使用: t use 表格名称")
        print("或: t alter add <表名> <字段名> <字段类型> [选项...]")
        return 1
    
    if len(args) < 2:
        print("错误: 参数不足")
        print("使用: t alter add [表名] <字段名> <字段类型> [选项...]")
        print("使用: t alter add [表名] <字段名> link <关联关系> <目标表名>")
        print("使用: t alter add [表名] <字段名> lookup <关联字段名> <引用字段名>")
        print("使用: t alter add [表名] <字段名> formula <表达式>")
        print("使用: t help alter 查看详细帮助")
        return 1
    
    table_id = session.get_current_table_id()
    table_name = session.get_current_table()
    
    field_name = args[0]
    field_type_raw = args[1]
    field_type = field_type_raw.lower()
    
    try:
        # 检查字段名是否已存在
        existing_fields = client.get_table_fields(table_id)
        field_names = [f.get('name', '') for f in existing_fields]
        if field_name in field_names:
            print(f"错误: 字段 '{field_name}' 已存在")
            return 1
        
        # 处理引用字段（Lookup）
        if field_type == 'lookup':
            if len(args) < 4:
                print("错误: 引用字段需要指定关联字段和引用字段")
                print("使用: t alter add <字段名> lookup <关联字段名> <引用字段名>")
                print("示例: t alter add 客户名称 lookup 关联客户 客户名称")
                return 1
            
            link_field_name = args[2]
            lookup_field_name = args[3]
            
            # 获取当前表的字段，查找关联字段
            current_fields = client.get_table_fields(table_id)
            link_field = None
            link_field_id = None
            for field in current_fields:
                if field.get('name') == link_field_name:
                    link_field = field
                    link_field_id = field.get('id')
                    break
            
            if not link_field_id:
                print(f"错误: 找不到关联字段 '{link_field_name}'")
                print("当前表的字段:")
                for field in current_fields:
                    print(f"  - {field.get('name')} ({field.get('type', '未知类型')})")
                return 1
            
            # 检查关联字段类型
            if link_field.get('type') != 'link':
                print(f"错误: '{link_field_name}' 不是关联字段（类型: {link_field.get('type')}）")
                return 1
            
            # 从关联字段获取目标表ID
            link_options = link_field.get('options', {})
            foreign_table_id = link_options.get('foreignTableId')
            
            if not foreign_table_id:
                print(f"错误: 关联字段 '{link_field_name}' 没有配置目标表")
                return 1
            
            # 获取目标表的字段，查找引用字段
            foreign_fields = client.get_table_fields(foreign_table_id)
            lookup_field = None
            lookup_field_id = None
            lookup_field_type = None
            
            for field in foreign_fields:
                if field.get('name') == lookup_field_name:
                    lookup_field = field
                    lookup_field_id = field.get('id')
                    lookup_field_type = field.get('type')
                    break
            
            if not lookup_field_id:
                print(f"错误: 在目标表中找不到字段 '{lookup_field_name}'")
                print("目标表的字段:")
                for field in foreign_fields:
                    print(f"  - {field.get('name')} ({field.get('type', '未知类型')})")
                print("\n提示: 如果是 lookup 字段，请使用完整名称，例如: '城市名称 (from 关联城市)'")
                return 1
            
            # 获取目标表名称（用于显示）
            tables = client.get_tables()
            foreign_table_name = None
            for table in tables:
                if table.get('id') == foreign_table_id:
                    foreign_table_name = table.get('name')
                    break
            
            # 创建引用字段配置
            field_config = create_lookup_field_config(
                name=field_name,
                field_type=lookup_field_type,
                foreign_table_id=foreign_table_id,
                link_field_id=link_field_id,
                lookup_field_id=lookup_field_id
            )
            
            print(f"正在添加引用字段 '{field_name}' 到表格 '{table_name}'...")
            print(f"   关联字段: {link_field_name}")
            print(f"   引用字段: {lookup_field_name} (类型: {lookup_field_type})")
            if foreign_table_name:
                print(f"   目标表: {foreign_table_name}")
        
        # 处理公式字段
        elif field_type == 'formula':
            if len(args) < 3:
                print("错误: 公式字段需要指定表达式")
                print("使用: t alter add <字段名> formula <表达式>")
                print("示例: t alter add 总价 formula \"{单价} * {数量}\"")
                print("示例: t alter add 订单号显示 formula \"{订单号} + 5000000000\"")
                return 1
            
            expression = ' '.join(args[2:])  # 支持表达式中包含空格
            
            # 获取当前表的字段，将表达式中的字段名替换为字段ID
            current_fields = client.get_table_fields(table_id)
            field_name_to_id = {f['name']: f['id'] for f in current_fields}
            
            # 将表达式中的字段名替换为字段ID
            # 注意：使用 fn 作为循环变量，避免覆盖外层的 field_name
            for fn, field_id in field_name_to_id.items():
                # 替换 {字段名} 为 { 字段ID }
                expression = expression.replace(f'{{{fn}}}', f'{{ {field_id} }}')
                expression = expression.replace(f'{{ {fn} }}', f'{{ {field_id} }}')
            
            # 创建公式字段配置
            field_config = create_formula_field_config(
                name=field_name,
                expression=expression
            )
            
            print(f"正在添加公式字段 '{field_name}' 到表格 '{table_name}'...")
            print(f"   表达式: {expression}")
        
        # 处理关联字段
        elif field_type == 'link':
            if len(args) < 4:
                print("错误: 关联字段需要指定关联关系和目标表")
                print("使用: t alter add <字段名> link <关联关系> <目标表名>")
                print("关联关系: manyOne, oneMany, manyMany, oneOne")
                return 1
            
            relationship_input = args[2].lower()
            foreign_table_name = args[3]
            
            # 验证关联关系并转换为API需要的格式
            relationship_map = {
                'manyone': 'manyOne',
                'onemany': 'oneMany',
                'manymany': 'manyMany',
                'oneone': 'oneOne'
            }
            
            if relationship_input not in relationship_map:
                print(f"错误: 无效的关联关系 '{relationship_input}'")
                print(f"支持的关联关系: manyOne, oneMany, manyMany, oneOne")
                return 1
            
            relationship = relationship_map[relationship_input]  # 转换为API格式
            
            # 查找目标表
            tables = client.get_tables()
            foreign_table_id = None
            for table in tables:
                if table.get('name') == foreign_table_name:
                    foreign_table_id = table.get('id')
                    break
            
            if not foreign_table_id:
                print(f"错误: 找不到表格 '{foreign_table_name}'")
                print("可用表格:")
                for table in tables:
                    print(f"  - {table.get('name')}")
                return 1
            
            # 创建关联字段配置
            field_config = create_link_field_config(
                name=field_name,
                relationship=relationship,  # 使用转换后的格式
                foreign_table_id=foreign_table_id
            )
            
            print(f"正在添加关联字段 '{field_name}' ({relationship}) 到表格 '{table_name}'...")
            
        else:
            # 处理普通字段
            # 验证字段类型（使用原始大小写）
            if field_type_raw not in SUPPORTED_FIELD_TYPES:
                print(f"错误: 不支持的字段类型 '{field_type_raw}'")
                print(f"支持的字段类型: {', '.join(SUPPORTED_FIELD_TYPES)}")
                return 1
            
            # 解析 unique 和 required 标志
            is_unique = False
            is_required = False
            precision = None
            
            # 检查参数中是否有 unique 和 required
            for i in range(2, len(args)):
                arg_lower = args[i].lower()
                if arg_lower == 'unique':
                    is_unique = True
                elif arg_lower == 'required':
                    is_required = True
                elif field_type == 'number' and precision is None:
                    # 对于 number 类型，第一个非 unique/required 的参数可能是精度
                    try:
                        precision = int(args[i])
                    except ValueError:
                        pass
            
            # 处理number字段的精度参数
            field_config = None
            if field_type == 'number':
                if precision is None:
                    precision = 2  # 默认精度
                
                # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                # 这些属性需要通过 Web 界面手动设置
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
                
                attrs = [f"精度: {precision}"]
                if is_unique or is_required:
                    attrs.append("⚠️ 注意：unique/required 需要通过 Web 界面设置")
                print(f"正在添加字段 '{field_name}' (类型: {field_type_raw}, {', '.join(attrs)}) 到表格 '{table_name}'...")
            else:
                # 创建字段配置
                # 注意：Teable API 不支持在创建字段时设置 unique 和 notNull
                # 这些属性需要通过 Web 界面手动设置
                field_config = create_field_config(
                    name=field_name,
                    field_type=field_type_raw  # 使用原始大小写
                )
                
                attrs = []
                if is_unique or is_required:
                    attrs.append("⚠️ 注意：unique/required 需要通过 Web 界面设置")
                
                if attrs:
                    print(f"正在添加字段 '{field_name}' (类型: {field_type_raw}, {', '.join(attrs)}) 到表格 '{table_name}'...")
                else:
                    print(f"正在添加字段 '{field_name}' (类型: {field_type_raw}) 到表格 '{table_name}'...")
        
        # 调用 API 添加字段
        result = client.add_field(table_id, field_config)
        
        field_id = result.get('id', '未知')
        print(f"✅ 字段添加成功!")
        print(f"   字段名称: {field_name}")
        print(f"   字段ID: {field_id}")
        print(f"   字段类型: {field_type}")
        
        if field_type == 'link':
            print(f"   关联关系: {relationship}")
            print(f"   目标表: {foreign_table_name}")
        elif field_type == 'lookup':
            print(f"   关联字段: {link_field_name}")
            print(f"   引用字段: {lookup_field_name} (类型: {lookup_field_type})")
            if foreign_table_name:
                print(f"   目标表: {foreign_table_name}")
        elif field_type == 'formula':
            print(f"   表达式: {expression}")
        elif field_type == 'number' and precision is not None:
            print(f"   精度: {precision}")
        
        # 只在普通字段的情况下检查 unique/required
        if field_type not in ['link', 'lookup', 'formula']:
            if is_unique or is_required:
                print(f"   ⚠️  注意：unique/required 属性需要通过 Teable Web 界面手动设置")
        
        logger.info(f"字段添加成功: {field_name} ({field_type})")
        return 0
        
    except Exception as e:
        print(f"错误: 添加字段失败: {e}")
        logger.error(f"添加字段失败: {e}", exc_info=True)
        return 1


def modify_field_properties_command(client, session, args: list):
    """修改字段属性命令（唯一性和必填）
    
    ⚠️ 注意：根据 Teable API 文档，目前 Teable API 不支持通过 API/CLI 修改字段的唯一性约束和必填属性。
    这些属性需要通过 Teable Web 界面手动设置。此命令会显示警告信息。
    
    用法:
        t alter modify <字段名> unique <true|false>
        t alter modify <字段名> required <true|false>
        t alter modify <表名> <字段名> unique <true|false>
        t alter modify <表名> <字段名> required <true|false>
    
    示例:
        t alter modify 用户名 unique true       # ⚠️ 不会生效，需要通过 Web 界面设置
        t alter modify 邮箱 required true       # ⚠️ 不会生效，需要通过 Web 界面设置
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    # 检查是否指定了表名（第一个参数可能是表名）
    if len(args) >= 4:
        tables = client.get_tables()
        table_names = [t.get('name') for t in tables]
        
        if args[0] in table_names and args[2].lower() in ['unique', 'required']:
            table_name_arg = args[0]
            args = args[1:]  # 移除表名参数
            # 临时切换表
            from .table_common import use_table
            use_table(client, session, table_name_arg)
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        print("使用: t use 表格名称")
        print("或: t alter modify <表名> <字段名> <属性> <值>")
        return 1
    
    if len(args) < 3:
        print("错误: 参数不足")
        print("使用: t alter modify [表名] <字段名> <属性> <值>")
        print("属性: unique, required")
        print("值: true, false")
        print("示例: t alter modify 用户名 unique true")
        return 1
    
    table_id = session.get_current_table_id()
    table_name = session.get_current_table()
    
    field_name = args[0]
    property_name = args[1].lower()
    value_str = args[2].lower()
    
    # 验证属性名
    if property_name not in ['unique', 'required']:
        print(f"错误: 未知的属性 '{args[1]}'")
        print("支持的属性: unique, required")
        return 1
    
    # 解析值
    if value_str in ['true', '1', 'yes', '是', 'on']:
        value = True
    elif value_str in ['false', '0', 'no', '否', 'off']:
        value = False
    else:
        print(f"错误: 无效的值 '{args[2]}'")
        print("值必须是: true, false, 1, 0, yes, no, 是, 否")
        return 1
    
    try:
        # 查找字段
        fields = client.get_table_fields(table_id)
        field = None
        for f in fields:
            if f.get('name') == field_name:
                field = f
                break
        
        if not field:
            print(f"错误: 字段 '{field_name}' 不存在")
            return 1
        
        field_id = field.get('id')
        
        # ⚠️ 警告：Teable API 不支持通过 API 修改字段的唯一性和必填属性
        print(f"⚠️  警告：Teable API 目前不支持通过 API/CLI 修改字段的唯一性约束和必填属性")
        print(f"   字段名称: {field_name}")
        print(f"   属性: {'唯一约束' if property_name == 'unique' else '必填'}")
        print(f"   请求的值: {'是' if value else '否'}")
        print(f"   请通过 Teable Web 界面手动设置这些属性")
        
        # 尝试调用 API（虽然可能不会生效）
        try:
            if property_name == 'unique':
                result = client.update_field_properties(
                    table_id=table_id,
                    field_id=field_id,
                    unique=value
                )
            else:  # required
                result = client.update_field_properties(
                    table_id=table_id,
                    field_id=field_id,
                    not_null=value
                )
            print(f"   API 调用返回成功，但属性可能不会实际更新")
        except Exception as e:
            print(f"   API 调用失败: {e}")
        
        logger.warning(f"字段属性修改请求（可能不会生效）: {field_name} ({property_name}={value})")
        return 0
        
    except Exception as e:
        print(f"错误: 修改字段属性失败: {e}")
        logger.error(f"修改字段属性失败: {e}", exc_info=True)
        return 1


def modify_field_precision_command(client, session, args: list):
    """修改字段精度命令
    
    用法:
        t alter modify <字段名> precision <精度>
        t alter modify <表名> <字段名> precision <精度>
    
    示例:
        t alter modify 订单金额 precision 0    # 修改为整数
        t alter modify 订单金额 precision 2    # 修改为2位小数
        t alter modify 订单表 订单金额 precision 0
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    # 检查是否指定了表名（第一个参数可能是表名）
    if len(args) >= 4:
        tables = client.get_tables()
        table_names = [t.get('name') for t in tables]
        
        if args[0] in table_names and args[2].lower() == 'precision':
            table_name_arg = args[0]
            args = args[1:]  # 移除表名参数
            # 临时切换表
            from .table_common import use_table
            use_table(client, session, table_name_arg)
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        print("使用: t use 表格名称")
        print("或: t alter modify <表名> <字段名> precision <精度>")
        return 1
    
    if len(args) < 3:
        print("错误: 参数不足")
        print("使用: t alter modify [表名] <字段名> precision <精度>")
        print("示例: t alter modify 订单金额 precision 0")
        return 1
    
    table_id = session.get_current_table_id()
    table_name = session.get_current_table()
    
    field_name = args[0]
    precision_keyword = args[1].lower()
    
    if precision_keyword != 'precision':
        print(f"错误: 未知的关键字 '{args[1]}'")
        print("使用: t alter modify <字段名> precision <精度>")
        return 1
    
    try:
        precision_str = args[2]
        precision = int(precision_str)
        
        # 查找字段
        fields = client.get_table_fields(table_id)
        field = None
        for f in fields:
            if f.get('name') == field_name:
                field = f
                break
        
        if not field:
            print(f"错误: 字段 '{field_name}' 不存在")
            return 1
        
        if field.get('type') != 'number':
            print(f"错误: 字段 '{field_name}' 不是number类型，无法修改精度")
            return 1
        
        # 更新精度
        result = client.update_number_field_precision(
            table_id=table_id,
            field_id=field.get('id'),
            precision=precision
        )
        
        print(f"✅ 字段精度修改成功!")
        print(f"   字段名称: {field_name}")
        print(f"   新精度: {precision}")
        
        logger.info(f"字段精度修改成功: {field_name} (精度: {precision})")
        return 0
        
    except ValueError:
        print(f"错误: 无效的精度值 '{precision_str}'，精度必须是整数")
        return 1
    except Exception as e:
        print(f"错误: 修改字段精度失败: {e}")
        logger.error(f"修改字段精度失败: {e}", exc_info=True)
        return 1


def alter_command(client, session, args: list):
    """表格结构修改命令主入口
    
    用法:
        t alter add <字段名> <字段类型> [选项...]
        t alter modify <字段名> precision <精度>
        t alter modify <字段名> unique <true|false>
        t alter modify <字段名> required <true|false>
    """
    if not args:
        print("错误: 请指定操作")
        print("使用: t alter add <字段名> <字段类型>")
        print("使用: t alter modify <字段名> precision <精度>")
        print("使用: t alter modify <字段名> unique <true|false>")
        print("使用: t alter modify <字段名> required <true|false>")
        print("使用: t help alter 查看详细帮助")
        return 1
    
    operation = args[0].lower()
    
    if operation == 'add':
        return add_field_command(client, session, args[1:])
    elif operation == 'modify':
        # 判断是修改精度还是修改属性
        if len(args) >= 3:
            modify_type = args[2].lower()
            if modify_type == 'precision':
                return modify_field_precision_command(client, session, args[1:])
            elif modify_type in ['unique', 'required']:
                return modify_field_properties_command(client, session, args[1:])
        
        # 默认尝试精度修改（向后兼容）
        return modify_field_precision_command(client, session, args[1:])
    elif operation == 'delete':
        # 检查是否指定了表名（第一个参数可能是表名）
        if len(args) >= 3:
            tables = client.get_tables()
            table_names = [t.get('name') for t in tables]
            
            if args[1] in table_names:
                table_name_arg = args[1]
                field_name = args[2]
                # 临时切换表
                from .table_common import use_table
                use_table(client, session, table_name_arg)
            else:
                field_name = args[1]
        else:
            if len(args) < 2:
                print("错误: 请指定要删除的字段名")
                print("使用: t alter delete <字段名>")
                print("或: t alter delete <表名> <字段名>")
                return 1
            field_name = args[1]
        
        if not session.is_table_selected():
            print("错误: 请先选择表格")
            print("使用: t use 表格名称")
            print("或: t alter delete <表名> <字段名>")
            return 1
        
        table_id = session.get_current_table_id()
        table_name = session.get_current_table()
        
        # 查找字段
        fields = client.get_table_fields(table_id)
        field_to_delete = None
        for field in fields:
            if field.get('name') == field_name:
                field_to_delete = field
                break
        
        if not field_to_delete:
            print(f"错误: 找不到字段 '{field_name}'")
            return 1
        
        field_id = field_to_delete.get('id')
        
        # 确认删除
        confirm = input(f"确定要删除字段 '{field_name}' 吗？此操作不可恢复！(y/N): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("取消删除操作")
            return 0
        
        # 删除字段
        try:
            success = client.delete_field(table_id, field_id)
            if success:
                print(f"✅ 字段 '{field_name}' 删除成功")
                return 0
            else:
                print(f"❌ 字段 '{field_name}' 删除失败")
                return 1
        except Exception as e:
            print(f"错误: 删除字段失败: {e}")
            logger.error(f"删除字段失败: {e}", exc_info=True)
            return 1
    else:
        print(f"错误: 未知操作 '{operation}'")
        print("支持的操作: add, delete, modify")
        print("使用: t alter add <字段名> <字段类型>")
        print("使用: t alter delete <字段名>")
        print("使用: t alter modify <字段名> precision <精度>")
        print("使用: t alter modify <字段名> unique <true|false>")
        print("使用: t alter modify <字段名> required <true|false>")
        return 1

