#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量脚本执行工具
可以批量执行多个脚本，支持依赖管理和错误处理
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json


class BatchScriptRunner:
    """批量脚本执行器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path(__file__).parent
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def run_scripts(self, script_names: List[str], 
                   stop_on_error: bool = False,
                   delay: float = 0.5,
                   dry_run: bool = False) -> Dict:
        """批量执行脚本"""
        self.start_time = datetime.now()
        total = len(script_names)
        success_count = 0
        failed_count = 0
        
        print(f"\n{'='*60}")
        print(f"批量执行脚本")
        print(f"{'='*60}")
        print(f"总脚本数: {total}")
        print(f"停止条件: {'遇到错误即停止' if stop_on_error else '继续执行'}")
        print(f"延迟间隔: {delay}秒")
        print(f"{'='*60}\n")
        
        for i, script_name in enumerate(script_names, 1):
            script_path = self.workspace_path / script_name
            if not script_path.exists():
                # 尝试在tests目录查找
                script_path = self.workspace_path / 'tests' / script_name
                if not script_path.exists():
                    print(f"[{i}/{total}] ❌ 跳过: {script_name} (文件不存在)")
                    failed_count += 1
                    self.results.append({
                        'script': script_name,
                        'status': 'not_found',
                        'error': '文件不存在'
                    })
                    continue
            
            print(f"[{i}/{total}] {'[模拟]' if dry_run else ''} 执行: {script_name}")
            print(f"  路径: {script_path.relative_to(self.workspace_path)}")
            
            if dry_run:
                print(f"  ✅ [模拟] 将执行此脚本")
                success_count += 1
                self.results.append({
                    'script': script_name,
                    'status': 'simulated',
                    'path': str(script_path.relative_to(self.workspace_path))
                })
                continue
            
            try:
                start = time.time()
                
                # 判断脚本类型
                if script_path.suffix == '.sh':
                    result = subprocess.run(
                        ['bash', str(script_path)],
                        cwd=self.workspace_path,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                else:
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=self.workspace_path,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                
                elapsed = time.time() - start
                
                if result.returncode == 0:
                    print(f"  ✅ 成功 (耗时: {elapsed:.2f}秒)")
                    success_count += 1
                    self.results.append({
                        'script': script_name,
                        'status': 'success',
                        'elapsed': elapsed,
                        'path': str(script_path.relative_to(self.workspace_path))
                    })
                else:
                    print(f"  ❌ 失败 (退出码: {result.returncode}, 耗时: {elapsed:.2f}秒)")
                    failed_count += 1
                    
                    # 显示错误输出（前5行）
                    if result.stderr:
                        error_lines = result.stderr.strip().split('\n')[:5]
                        for line in error_lines:
                            print(f"      {line}")
                    
                    self.results.append({
                        'script': script_name,
                        'status': 'failed',
                        'exit_code': result.returncode,
                        'elapsed': elapsed,
                        'error': result.stderr[:200] if result.stderr else '未知错误',
                        'path': str(script_path.relative_to(self.workspace_path))
                    })
                    
                    if stop_on_error:
                        print(f"\n⚠️  遇到错误，停止执行")
                        break
                
                # 延迟
                if i < total and delay > 0:
                    time.sleep(delay)
                
            except subprocess.TimeoutExpired:
                print(f"  ⏱️  超时 (超过5分钟)")
                failed_count += 1
                self.results.append({
                    'script': script_name,
                    'status': 'timeout',
                    'error': '执行超时'
                })
                if stop_on_error:
                    break
            
            except Exception as e:
                print(f"  ❌ 执行异常: {e}")
                failed_count += 1
                self.results.append({
                    'script': script_name,
                    'status': 'error',
                    'error': str(e)
                })
                if stop_on_error:
                    break
            
            print()
        
        self.end_time = datetime.now()
        total_time = (self.end_time - self.start_time).total_seconds()
        
        # 打印总结
        print(f"{'='*60}")
        print(f"执行完成")
        print(f"{'='*60}")
        print(f"总脚本数: {total}")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"{'='*60}\n")
        
        return {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'total_time': total_time,
            'results': self.results
        }
    
    def save_report(self, output_file: str = None):
        """保存执行报告"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"script_execution_report_{timestamp}.json"
        
        report = {
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_time': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0,
            'results': self.results
        }
        
        output_path = self.workspace_path / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"报告已保存: {output_path}")
        return output_path


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量脚本执行工具')
    parser.add_argument('scripts', nargs='+', help='要执行的脚本名称列表')
    parser.add_argument('--stop-on-error', action='store_true', 
                       help='遇到错误即停止')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='脚本之间的延迟时间（秒）')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟执行，不实际运行脚本')
    parser.add_argument('--save-report', action='store_true',
                       help='保存执行报告到JSON文件')
    
    args = parser.parse_args()
    
    runner = BatchScriptRunner()
    result = runner.run_scripts(
        args.scripts,
        stop_on_error=args.stop_on_error,
        delay=args.delay,
        dry_run=args.dry_run
    )
    
    if args.save_report:
        runner.save_report()


if __name__ == '__main__':
    main()
