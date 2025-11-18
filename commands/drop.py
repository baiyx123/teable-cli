#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除表格命令
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def drop_table_command(client, session, args: list):
    """删除表格命令
    
    用法:
        t drop <表名>
        t drop <表名> --force    # 跳过确认，直接删除
    
    示例:
        t drop 测试表
        t drop 测试表 --force
    """
    if not client:
        print("错误: 无法连接到Teable服务")
        return 1
    
    if not args:
        print("错误: 请指定要删除的表名")
        print("用法: t drop <表名>")
        print("      t drop <表名> --force  # 跳过确认")
        return 1
    
    table_name = args[0]
    force = '--force' in args or '-f' in args
    
    try:
        # 获取所有表格
        tables = client.get_tables()
        target_table = None
        target_table_id = None
        
        for table in tables:
            if table.get('name') == table_name:
                target_table = table
                target_table_id = table.get('id')
                break
        
        if not target_table:
            print(f"错误: 找不到表格 '{table_name}'")
            print("\n可用表格:")
            for table in tables:
                print(f"  - {table.get('name')}")
            return 1
        
        # 确认删除
        if not force:
            print(f"\n⚠️  警告: 即将删除表格 '{table_name}'")
            print(f"   表格ID: {target_table_id}")
            
            # 尝试获取记录数量（如果API支持）
            try:
                records = client.get_records(target_table_id, take=1)
                record_count = records.get('totalRecords', 0)
                if record_count > 0:
                    print(f"   记录数: {record_count} 条")
                    print(f"   ⚠️  删除表格将同时删除所有记录！")
            except Exception:
                pass
            
            print("\n⚠️  此操作不可恢复！")
            confirm = input("确认删除？(输入 'yes' 或 'y' 确认): ").strip().lower()
            
            if confirm not in ['yes', 'y']:
                print("已取消删除操作")
                return 0
        
        # 执行删除
        print(f"\n正在删除表格 '{table_name}'...")
        result = client.delete_table(target_table_id)
        
        print(f"✅ 表格 '{table_name}' 删除成功")
        logger.info(f"表格删除成功: {table_name} (ID: {target_table_id})")
        
        # 如果删除的是当前选中的表，清除选择
        if session.is_table_selected() and session.current_table_id == target_table_id:
            session.current_table_id = None
            session.current_table_name = None
            print("⚠️  已清除当前表格选择")
        
        return 0
        
    except Exception as e:
        print(f"错误: 删除表格失败: {e}")
        logger.error(f"删除表格失败: {e}", exc_info=True)
        return 1

