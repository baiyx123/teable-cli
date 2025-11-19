#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本管理工具
用于分析、管理和执行项目中的脚本
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional
import json


class ScriptManager:
    """脚本管理器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path(__file__).parent
        self.scripts = {}
        self._scan_scripts()
    
    def _scan_scripts(self):
        """扫描项目中的所有脚本文件"""
        script_extensions = ['.sh', '.py']
        
        # 扫描根目录
        for file_path in self.workspace_path.glob('*.sh'):
            self._analyze_script(file_path)
        
        for file_path in self.workspace_path.glob('*.py'):
            if file_path.name != 'script_manager.py':  # 排除自己
                self._analyze_script(file_path)
        
        # 扫描tests目录
        tests_dir = self.workspace_path / 'tests'
        if tests_dir.exists():
            for file_path in tests_dir.glob('*.sh'):
                self._analyze_script(file_path)
            for file_path in tests_dir.glob('*.py'):
                self._analyze_script(file_path)
    
    def _analyze_script(self, file_path: Path):
        """分析脚本文件，提取信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            info = {
                'path': str(file_path.relative_to(self.workspace_path)),
                'full_path': str(file_path),
                'name': file_path.name,
                'type': 'bash' if file_path.suffix == '.sh' else 'python',
                'size': file_path.stat().st_size,
                'description': self._extract_description(content),
                'commands': self._extract_commands(content),
                'usage': self._extract_usage(content),
            }
            
            self.scripts[file_path.name] = info
        except Exception as e:
            print(f"警告: 无法分析脚本 {file_path}: {e}", file=sys.stderr)
    
    def _extract_description(self, content: str) -> str:
        """提取脚本描述"""
        # 查找注释中的描述
        lines = content.split('\n')
        description_lines = []
        
        for i, line in enumerate(lines[:20]):  # 只检查前20行
            line = line.strip()
            if line.startswith('#') or line.startswith('"""') or line.startswith("'''"):
                # 移除注释符号
                desc = re.sub(r'^#+\s*', '', line)
                desc = re.sub(r'^"""\s*', '', desc)
                desc = re.sub(r"^'''\s*", '', desc)
                desc = desc.strip()
                
                if desc and not desc.startswith('!'):  # 排除shebang
                    # 跳过常见的无意义注释
                    if desc.lower() not in ['coding: utf-8', 'env python3', '/bin/bash']:
                        description_lines.append(desc)
        
        if description_lines:
            return ' '.join(description_lines[:3])  # 返回前3行
        return "无描述"
    
    def _extract_commands(self, content: str) -> List[str]:
        """提取脚本中使用的主要命令"""
        commands = []
        
        # 查找 t 命令调用
        t_commands = re.findall(r'\bt\s+(\w+)(?:\s+[^\n|]*)?', content)
        if t_commands:
            commands.extend([f"t {cmd}" for cmd in set(t_commands[:10])])  # 去重，最多10个
        
        # 查找其他常见命令
        common_commands = ['echo', 'grep', 'head', 'tail', 'wc', 'sort', 'uniq', 'awk', 'sed']
        for cmd in common_commands:
            if cmd in content:
                commands.append(cmd)
        
        return list(set(commands))[:15]  # 去重，最多15个
    
    def _extract_usage(self, content: str) -> str:
        """提取使用说明"""
        # 查找使用说明模式
        usage_patterns = [
            r'使用:\s*(.+?)(?:\n|$)',
            r'用法:\s*(.+?)(?:\n|$)',
            r'Usage:\s*(.+?)(?:\n|$)',
            r'示例:\s*(.+?)(?:\n|$)',
            r'Example:\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in usage_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def list_scripts(self, category: Optional[str] = None) -> List[Dict]:
        """列出所有脚本"""
        scripts_list = list(self.scripts.values())
        
        if category:
            if category == 'test':
                scripts_list = [s for s in scripts_list if 'test' in s['name'].lower()]
            elif category == 'demo':
                scripts_list = [s for s in scripts_list if 'demo' in s['name'].lower()]
            elif category == 'insert':
                scripts_list = [s for s in scripts_list if 'insert' in s['name'].lower()]
        
        return sorted(scripts_list, key=lambda x: x['name'])
    
    def show_script_info(self, script_name: str):
        """显示脚本详细信息"""
        if script_name not in self.scripts:
            print(f"错误: 找不到脚本 '{script_name}'")
            return
        
        info = self.scripts[script_name]
        print(f"\n{'='*60}")
        print(f"脚本信息: {info['name']}")
        print(f"{'='*60}")
        print(f"路径: {info['path']}")
        print(f"类型: {info['type']}")
        print(f"大小: {info['size']} 字节")
        print(f"\n描述:")
        print(f"  {info['description']}")
        
        if info['usage']:
            print(f"\n使用说明:")
            print(f"  {info['usage']}")
        
        if info['commands']:
            print(f"\n主要命令:")
            for cmd in info['commands']:
                print(f"  - {cmd}")
        
        print(f"\n{'='*60}\n")
    
    def execute_script(self, script_name: str, dry_run: bool = False):
        """执行脚本"""
        if script_name not in self.scripts:
            print(f"错误: 找不到脚本 '{script_name}'")
            return False
        
        info = self.scripts[script_name]
        script_path = Path(info['full_path'])
        
        if not script_path.exists():
            print(f"错误: 脚本文件不存在: {script_path}")
            return False
        
        if dry_run:
            print(f"[模拟执行] 将运行: {script_path}")
            print(f"命令: {'bash' if info['type'] == 'bash' else 'python3'} {script_path}")
            return True
        
        try:
            print(f"\n执行脚本: {info['name']}")
            print(f"路径: {info['path']}")
            print(f"{'='*60}\n")
            
            if info['type'] == 'bash':
                result = subprocess.run(['bash', str(script_path)], 
                                      cwd=self.workspace_path,
                                      capture_output=False)
            else:
                result = subprocess.run([sys.executable, str(script_path)], 
                                      cwd=self.workspace_path,
                                      capture_output=False)
            
            print(f"\n{'='*60}")
            if result.returncode == 0:
                print(f"✅ 脚本执行成功")
            else:
                print(f"❌ 脚本执行失败 (退出码: {result.returncode})")
            print(f"{'='*60}\n")
            
            return result.returncode == 0
        except Exception as e:
            print(f"错误: 执行脚本失败: {e}")
            return False
    
    def search_scripts(self, keyword: str) -> List[Dict]:
        """搜索脚本"""
        keyword_lower = keyword.lower()
        results = []
        
        for script in self.scripts.values():
            if (keyword_lower in script['name'].lower() or 
                keyword_lower in script['description'].lower() or
                keyword_lower in ' '.join(script['commands']).lower()):
                results.append(script)
        
        return results
    
    def generate_report(self) -> str:
        """生成脚本报告"""
        report = []
        report.append("="*60)
        report.append("项目脚本分析报告")
        report.append("="*60)
        report.append(f"\n总脚本数: {len(self.scripts)}")
        
        # 按类型统计
        bash_count = sum(1 for s in self.scripts.values() if s['type'] == 'bash')
        python_count = sum(1 for s in self.scripts.values() if s['type'] == 'python')
        report.append(f"  - Bash脚本: {bash_count}")
        report.append(f"  - Python脚本: {python_count}")
        
        # 按目录统计
        root_scripts = [s for s in self.scripts.values() if '/' not in s['path']]
        test_scripts = [s for s in self.scripts.values() if 'tests/' in s['path']]
        report.append(f"\n按目录分布:")
        report.append(f"  - 根目录: {len(root_scripts)}")
        report.append(f"  - tests目录: {len(test_scripts)}")
        
        # 列出所有脚本
        report.append(f"\n所有脚本列表:")
        for script in sorted(self.scripts.values(), key=lambda x: x['name']):
            report.append(f"  - {script['name']:30s} ({script['type']:6s}) - {script['description'][:50]}")
        
        return "\n".join(report)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='脚本管理工具')
    parser.add_argument('action', nargs='?', choices=['list', 'info', 'run', 'search', 'report'],
                       default='list', help='操作类型')
    parser.add_argument('script', nargs='?', help='脚本名称')
    parser.add_argument('--category', choices=['test', 'demo', 'insert'], 
                       help='脚本类别')
    parser.add_argument('--keyword', help='搜索关键词')
    parser.add_argument('--dry-run', action='store_true', help='模拟执行')
    
    args = parser.parse_args()
    
    manager = ScriptManager()
    
    if args.action == 'list':
        scripts = manager.list_scripts(args.category)
        print(f"\n找到 {len(scripts)} 个脚本:\n")
        for script in scripts:
            print(f"  {script['name']:30s} - {script['description'][:60]}")
        print()
    
    elif args.action == 'info':
        if not args.script:
            print("错误: 请指定脚本名称")
            print("使用: python script_manager.py info <脚本名>")
            return
        manager.show_script_info(args.script)
    
    elif args.action == 'run':
        if not args.script:
            print("错误: 请指定脚本名称")
            print("使用: python script_manager.py run <脚本名>")
            return
        manager.execute_script(args.script, dry_run=args.dry_run)
    
    elif args.action == 'search':
        if not args.keyword:
            print("错误: 请指定搜索关键词")
            print("使用: python script_manager.py search --keyword <关键词>")
            return
        results = manager.search_scripts(args.keyword)
        print(f"\n找到 {len(results)} 个匹配的脚本:\n")
        for script in results:
            print(f"  {script['name']:30s} - {script['description'][:60]}")
        print()
    
    elif args.action == 'report':
        print(manager.generate_report())


if __name__ == '__main__':
    main()
