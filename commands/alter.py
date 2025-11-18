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
        t alter add 金额 number
        t alter add 关联客户 link manyOne 客户表
        t alter add 客户名称 lookup 关联客户 客户名称
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    if not session.is_table_selected():
        print("错误: 请先选择表格")
        print("使用: t use 表格名称")
        return 1
    
    if len(args) < 2:
        print("错误: 参数不足")
        print("使用: t alter add <字段名> <字段类型> [选项...]")
        print("使用: t alter add <字段名> link <关联关系> <目标表名>")
        print("使用: t alter add <字段名> lookup <关联字段名> <引用字段名>")
        print("使用: t help alter 查看详细帮助")
        return 1
    
    table_id = session.get_current_table_id()
    table_name = session.get_current_table()
    
    field_name = args[0]
    field_type = args[1].lower()
    
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
        
        # 处理关联字段
        elif field_type == 'link':
            if len(args) < 4:
                print("错误: 关联字段需要指定关联关系和目标表")
                print("使用: t alter add <字段名> link <关联关系> <目标表名>")
                print("关联关系: manyOne, oneMany, manyMany, oneOne")
                return 1
            
            relationship = args[2].lower()
            foreign_table_name = args[3]
            
            # 验证关联关系
            valid_relationships = ['manyone', 'onemany', 'manymany', 'oneone']
            if relationship not in valid_relationships:
                print(f"错误: 无效的关联关系 '{relationship}'")
                print(f"支持的关联关系: {', '.join(valid_relationships)}")
                return 1
            
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
                relationship=relationship,
                foreign_table_id=foreign_table_id
            )
            
            print(f"正在添加关联字段 '{field_name}' ({relationship}) 到表格 '{table_name}'...")
            
        else:
            # 处理普通字段
            # 验证字段类型
            if field_type not in SUPPORTED_FIELD_TYPES:
                print(f"错误: 不支持的字段类型 '{field_type}'")
                print(f"支持的字段类型: {', '.join(SUPPORTED_FIELD_TYPES)}")
                return 1
            
            # 创建字段配置
            field_config = create_field_config(
                name=field_name,
                field_type=field_type
            )
            
            print(f"正在添加字段 '{field_name}' (类型: {field_type}) 到表格 '{table_name}'...")
        
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
        
        logger.info(f"字段添加成功: {field_name} ({field_type})")
        return 0
        
    except Exception as e:
        print(f"错误: 添加字段失败: {e}")
        logger.error(f"添加字段失败: {e}", exc_info=True)
        return 1


def alter_command(client, session, args: list):
    """表格结构修改命令主入口
    
    用法:
        t alter add <字段名> <字段类型> [选项...]
    """
    if not args:
        print("错误: 请指定操作")
        print("使用: t alter add <字段名> <字段类型>")
        print("使用: t help alter 查看详细帮助")
        return 1
    
    operation = args[0].lower()
    
    if operation == 'add':
        return add_field_command(client, session, args[1:])
    else:
        print(f"错误: 未知操作 '{operation}'")
        print("支持的操作: add")
        print("使用: t alter add <字段名> <字段类型>")
        return 1

