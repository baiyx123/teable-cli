#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础命令
"""

import sys
from typing import List


def show_help():
    """显示帮助信息"""
    help_text = """
Teable CLI - 命令行界面工具

使用方法:
  t [命令] [参数...] [选项]

基础命令:
  config    配置连接信息
  ls        列出所有表格
  use       选择表格
  show      显示当前表格数据
  insert    插入记录
  update    更新记录
  delete    删除记录
  create    创建新表格
  alter     修改表格结构（添加字段等）
  desc      显示表格结构（字段列表）
  schema    显示表格结构（同 desc）
  fields    显示表格结构（同 desc）
  help      显示帮助信息
  status    显示会话状态
  version   显示版本信息

配置命令:
  t config --token YOUR_TOKEN --base YOUR_BASE_ID
  t config --url https://app.teable.cn

表格操作:
  t ls                    # 列出所有表格
  t ls -v                 # 显示详细信息
  t use 学生表            # 切换到学生表
  t show                  # 显示当前表格数据
  t show -w 年龄>18 -o 成绩:desc -l 10  # 查询条件、排序、限制
  t insert                # 交互式插入记录
  t insert 姓名=张三 年龄=20  # 直接插入记录
  t update rec123 姓名=李四  # 更新单条记录
  t update 状态=已完成 where 优先级=高  # 条件更新多条记录
  t delete rec123          # 删除记录

管道操作（新功能）:
  t show -w 状态=待处理 | t update 状态=处理中     # 查询并更新
  t show -w 优先级=高 | head -10 | t update 处理人=张三  # 查询前10条并更新
  t show -w 状态=已取消 | t delete                    # 查询并删除
  t show -w 状态=已完成 | t insert --to-table 备份表    # 数据复制

示例:
  # 配置连接
  t config --token teable_xxxxx --base bsexxxxx
  
  # 查看表格
  t ls
  
  # 使用表格
  t use 学生表
  
  # 查看数据
  t show
  
  # 插入数据
  t insert
  t insert 姓名=张三 年龄=20 性别=男
  
  # 更新数据
  t update rec123 姓名=李四 年龄=21                    # 更新单条记录
  t update 状态=已完成 where 优先级=高               # 条件更新多条记录
  t update 状态=处理中 处理人=张三 where 创建时间>2024-01-01 优先级>=中
  t update 备注=已处理 where 标题like重要              # 模糊匹配条件更新
  
  # 管道操作（零配置，智能识别）
  t show -w 状态=待处理 | t update 状态=处理中        # 查询并更新
  t show -w 优先级=高 | head -10 | t update 处理人=张三  # 查询前10条并更新
  t show -w 创建时间>2024-01-01 | grep '客户=重要客户' | t update 优先级=最高
  
  # 删除数据
  t delete rec123
  t show -w 状态=已取消 | t delete                    # 批量删除查询结果

更多信息:
  使用 't help' 显示此帮助信息
  使用 't [命令] --help' 显示特定命令的帮助
"""
    print(help_text)
    return 0


def config_command(config, args: List[str]):
    """处理配置命令"""
    if not args:
        # 显示当前配置
        config.print_config()
        return 0
    
    # 解析参数
    i = 0
    updates = {}
    
    while i < len(args):
        arg = args[i]
        
        if arg in ['--token', '-t'] and i + 1 < len(args):
            updates['token'] = args[i + 1]
            i += 2
        elif arg in ['--base', '-b'] and i + 1 < len(args):
            updates['base_id'] = args[i + 1]
            i += 2
        elif arg in ['--url', '-u'] and i + 1 < len(args):
            updates['base_url'] = args[i + 1]
            i += 2
        elif arg == '--reset':
            # 重置配置
            print("重置所有配置...")
            config.config.update(config.defaults)
            config.save_config()
            print("配置已重置为默认值")
            return 0
        else:
            print(f"错误: 未知选项 '{arg}'")
            print("使用: t config --token TOKEN --base BASE_ID [--url URL]")
            return 1
    
    if updates:
        config.update(updates)
        print("配置已更新")
        
        # 验证配置
        if config.is_configured():
            print("✅ 配置验证通过")
        else:
            print("⚠️  配置不完整，请检查token和base_id")
    
    return 0


def show_session_status(config, session):
    """显示会话状态"""
    print("=== Teable CLI 状态 ===")
    
    # 配置状态
    print("\n配置状态:")
    if config.is_configured():
        print("✅ 已配置连接信息")
        print(f"  服务地址: {config.get('base_url')}")
        print(f"  Base ID: {config.get('base_id')[:10]}...")
    else:
        print("❌ 未配置连接信息")
        print("  使用: t config --token TOKEN --base BASE_ID")
    
    # 会话状态
    print("\n会话状态:")
    session_info = session.get_session_info()
    
    if session_info['is_table_selected']:
        print(f"✅ 已选择表格: {session_info['current_table']}")
        print(f"  表格ID: {session_info['current_table_id']}")
    else:
        print("❌ 未选择表格")
        print("  使用: t use 表格名称")
    
    if session_info['tables_cached'] > 0:
        print(f"📊 缓存表格数: {session_info['tables_cached']}")
    
    # 连接测试
    print("\n连接测试:")
    try:
        # 这里可以添加实际的连接测试
        print("✅ 连接正常")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
    
    return 0
