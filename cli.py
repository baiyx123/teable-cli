#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teable CLI 主程序
"""

import sys
import os
import click
from pathlib import Path
from typing import Optional

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from session import Session
from commands import (
    list_tables, show_current_table, use_table, 
    show_help, config_command, show_session_status,
    insert_record, update_record, delete_record,
    alter_command, show_table_schema, create_table_command
)

# 版本号
__version__ = "0.1.0"


class TeableCLI:
    """Teable CLI 主类"""
    
    def __init__(self):
        self.config = Config()
        self.session = Session(self.config)
        self.client = None
        self._ensure_client()
    
    def _ensure_client(self):
        """确保客户端已初始化"""
        if self.client is None and self.config.is_configured():
            try:
                # 延迟导入，避免循环依赖
                from teable_api_client import TeableClient
                conn_info = self.config.get_connection_info()
                self.client = TeableClient(
                    conn_info['base_url'],
                    conn_info['token'],
                    conn_info['base_id']
                )
            except Exception as e:
                print(f"错误: 无法连接到Teable服务: {e}")
                self.client = None
    
    def run_command(self, command: str, args: list):
        """执行命令"""
        if not self.config.is_configured() and command not in ['config', 'help']:
            print("错误: 请先配置连接信息")
            print("使用: t config --token YOUR_TOKEN --base YOUR_BASE_ID")
            return 1
        
        self._ensure_client()
        
        # 命令分发
        commands = {
            'ls': self._handle_list,
            'use': self._handle_use,
            'show': self._handle_show,
            'help': self._handle_help,
            'config': self._handle_config,
            'status': self._handle_status,
            'insert': self._handle_insert,
            'update': self._handle_update,
            'delete': self._handle_delete,
            'version': self._handle_version,
            'alter': self._handle_alter,
            'create': self._handle_create,
            'desc': self._handle_desc,
            'schema': self._handle_desc,
            'fields': self._handle_desc,
        }
        
        handler = commands.get(command)
        if handler:
            return handler(args)
        else:
            print(f"错误: 未知命令 '{command}'")
            print("使用 't help' 查看可用命令")
            return 1
    
    def _handle_list(self, args: list):
        """处理列表命令"""
        verbose = '-v' in args or '--verbose' in args
        return list_tables(self.client, verbose)
    
    def _handle_use(self, args: list):
        """处理使用表格命令"""
        if not args:
            print("错误: 请指定表格名称")
            print("使用: t use 表格名称")
            return 1
        
        table_name = args[0]
        return use_table(self.client, self.session, table_name)
    
    def _handle_show(self, args: list):
        """处理显示命令"""
        if not self.session.is_table_selected():
            print("错误: 请先选择表格")
            print("使用: t use 表格名称")
            return 1
        
        return show_current_table(self.client, self.session, args)
    
    def _handle_help(self, args: list):
        """处理帮助命令"""
        return show_help()
    
    def _handle_config(self, args: list):
        """处理配置命令"""
        return config_command(self.config, args)
    
    def _handle_status(self, args: list):
        """处理状态命令"""
        return show_session_status(self.config, self.session)
    
    def _handle_insert(self, args: list):
        """处理插入记录命令"""
        # 如果第一个参数可能是表名（不是字段=值格式），让insert_record处理表名切换
        # 否则检查是否已选择表格
        if not args or '=' in args[0]:
            # 没有参数或第一个参数是字段=值格式，需要检查session
            if not self.session.is_table_selected():
                print("错误: 请先选择表格")
                print("使用: t use 表格名称")
                return 1
        
        result = insert_record(self.client, self.session, args)
        # insert_record 返回 (状态码, 记录ID) 元组（非管道模式）或整数（管道模式）
        # 记录ID已经由 insert_record 输出到stdout（标准管道格式）
        if isinstance(result, tuple):
            status_code, record_id = result
            return status_code
        else:
            # 管道模式返回的是整数状态码，直接返回
            return result
    
    def _handle_update(self, args: list):
        """处理更新记录命令"""
        if not self.session.is_table_selected():
            print("错误: 请先选择表格")
            print("使用: t use 表格名称")
            return 1
        
        return update_record(self.client, self.session, args)
    
    def _handle_delete(self, args: list):
        """处理删除记录命令"""
        if not self.session.is_table_selected():
            print("错误: 请先选择表格")
            print("使用: t use 表格名称")
            return 1
        
        return delete_record(self.client, self.session, args)
    
    def _handle_version(self, args: list):
        """处理版本命令"""
        print(f"teable-cli version {__version__}")
        return 0
    
    def _handle_alter(self, args: list):
        """处理表格结构修改命令"""
        if not self.config.is_configured():
            print("错误: 请先配置连接信息")
            print("使用: t config --token YOUR_TOKEN --base YOUR_BASE_ID")
            return 1
        
        self._ensure_client()
        return alter_command(self.client, self.session, args)
    
    def _handle_create(self, args: list):
        """处理创建表格命令"""
        if not self.config.is_configured():
            print("错误: 请先配置连接信息")
            print("使用: t config --token YOUR_TOKEN --base YOUR_BASE_ID")
            return 1
        
        self._ensure_client()
        return create_table_command(self.client, self.session, args)
    
    def _handle_desc(self, args: list):
        """处理表格结构查看命令"""
        if not self.config.is_configured():
            print("错误: 请先配置连接信息")
            print("使用: t config --token YOUR_TOKEN --base YOUR_BASE_ID")
            return 1
        
        self._ensure_client()
        return show_table_schema(self.client, self.session, args)


# Click命令行接口
@click.command()
@click.argument('command', required=False)
@click.argument('args', nargs=-1)
@click.option('--interactive', '-i', is_flag=True, help='交互式模式')
def main(command: Optional[str], args: tuple, interactive: bool):
    """Teable CLI - 命令行界面工具"""
    
    cli = TeableCLI()
    
    if interactive:
        # 交互式模式
        from commands.interactive import run_interactive
        return run_interactive(cli)
    
    if not command:
        # 没有命令，显示帮助
        return cli.run_command('help', [])
    
    # 执行命令
    return cli.run_command(command, list(args))


if __name__ == '__main__':
    sys.exit(main())
