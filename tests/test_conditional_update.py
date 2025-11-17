#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试条件更新功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from session import Session
from teable_api_client import TeableClient
from commands.table import update_record


def test_conditional_update():
    """测试条件更新功能"""
    # 创建测试配置
    config = Config()
    
    # 检查是否已配置
    if not config.is_configured():
        print("请先配置连接信息:")
        print("使用: python cli.py config --token YOUR_TOKEN --base YOUR_BASE_ID")
        return
    
    # 创建会话
    session = Session(config)
    
    # 获取连接信息
    conn_info = config.get_connection_info()
    client = TeableClient(
        conn_info['base_url'],
        conn_info['token'],
        conn_info['base_id']
    )
    
    # 首先列出可用表格
    try:
        tables = client.get_tables()
        if not tables:
            print("没有找到表格，请先创建测试表格")
            return
        
        print("可用表格:")
        for i, table in enumerate(tables):
            print(f"  {i+1}. {table.get('name', '未知')} (ID: {table.get('id', '未知')})")
        
        # 选择第一个表格进行测试
        test_table = tables[0]
        table_name = test_table.get('name')
        table_id = test_table.get('id')
        
        print(f"\n选择表格: {table_name}")
        
        # 设置当前表格
        session.set_current_table(table_name, table_id)
        
        # 获取表格字段信息
        fields = client.get_table_fields(table_id)
        print(f"表格字段: {[f.get('name') for f in fields]}")
        
        # 测试1: 简单的条件更新
        print("\n=== 测试1: 简单条件更新 ===")
        print("执行: t update 状态=已完成 where 优先级=高")
        
        # 模拟命令行参数
        test_args = ["状态=已完成", "where", "优先级=高"]
        result = update_record(client, session, test_args)
        print(f"测试结果: {'成功' if result == 0 else '失败'}")
        
        # 测试2: 多个条件的更新
        print("\n=== 测试2: 多个条件更新 ===")
        print("执行: t update 状态=处理中 处理人=张三 where 创建时间>2024-01-01 优先级>=中")
        
        test_args = ["状态=处理中", "处理人=张三", "where", "创建时间>2024-01-01", "优先级>=中"]
        result = update_record(client, session, test_args)
        print(f"测试结果: {'成功' if result == 0 else '失败'}")
        
        # 测试3: 模糊查询条件
        print("\n=== 测试3: 模糊查询条件 ===")
        print("执行: t update 备注=已处理 where 标题like重要")
        
        test_args = ["备注=已处理", "where", "标题like重要"]
        result = update_record(client, session, test_args)
        print(f"测试结果: {'成功' if result == 0 else '失败'}")
        
        # 测试4: 传统单记录更新（应该仍然有效）
        print("\n=== 测试4: 传统单记录更新 ===")
        
        # 先获取一条记录进行测试
        records_data = client.get_records(table_id, take=1)
        if records_data.get('records'):
            test_record = records_data['records'][0]
            record_id = test_record.get('id')
            
            print(f"执行: t update {record_id} 状态=测试中")
            
            test_args = [record_id, "状态=测试中"]
            result = update_record(client, session, test_args)
            print(f"测试结果: {'成功' if result == 0 else '失败'}")
        else:
            print("表格中没有记录，跳过单记录更新测试")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_conditional_update()