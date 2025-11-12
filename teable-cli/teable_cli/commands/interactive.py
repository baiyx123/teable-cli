#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式模式
"""

import cmd
import sys
from typing import Optional


class TeableInteractiveShell(cmd.Cmd):
    """Teable交互式命令行"""
    
    intro = """
╔══════════════════════════════════════════════════════════════════════╗
║                    Teable CLI 交互式模式                             ║
╠══════════════════════════════════════════════════════════════════════╣
║  输入 'help' 查看可用命令                                            ║
║  输入 'exit' 或 'quit' 退出                                         ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    
    prompt = "teable> "
    
    def __init__(self, cli):
        super().__init__()
        self.cli = cli
    
    def default(self, line):
        """处理未知命令"""
        if line.strip():
            # 将命令传递给主CLI处理
            parts = line.split()
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            try:
                result = self.cli.run_command(command, args)
                if result != 0:
                    print(f"命令执行失败，返回码: {result}")
            except Exception as e:
                print(f"错误: {e}")
        else:
            print("请输入命令，或输入 'help' 查看帮助")
    
    def do_exit(self, arg):
        """退出交互式模式"""
        print("再见！")
        return True
    
    def do_quit(self, arg):
        """退出交互式模式"""
        return self.do_exit(arg)
    
    def do_help(self, arg):
        """显示帮助信息"""
        if arg:
            # 显示特定命令的帮助
            self.cli.run_command('help', [arg])
        else:
            print("""
可用命令:
  ls        - 列出所有表格
  use       - 选择表格
  show      - 显示当前表格数据
  config    - 配置连接信息
  status    - 显示会话状态
  help      - 显示帮助信息
  exit/quit - 退出交互式模式

示例:
  ls                    # 列出表格
  use 学生表            # 切换到学生表
  show                  # 显示数据
  help ls              # 查看ls命令帮助
""")
    
    def emptyline(self):
        """处理空行"""
        pass
    
    def precmd(self, line):
        """命令预处理"""
        return line.strip()
    
    def postcmd(self, stop, line):
        """命令后处理"""
        return stop


def run_interactive(cli):
    """运行交互式模式"""
    try:
        shell = TeableInteractiveShell(cli)
        shell.cmdloop()
        return 0
    except KeyboardInterrupt:
        print("\n再见！")
        return 0
    except Exception as e:
        print(f"交互式模式错误: {e}")
        return 1
