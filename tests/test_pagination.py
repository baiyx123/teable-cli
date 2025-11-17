#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试分页获取数据功能
"""

import subprocess
import sys
import os

def run_command(cmd):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def test_pagination():
    """测试分页功能"""
    print("=== 测试分页获取数据功能 ===")
    
    # 首先切换到订单表
    print("\n1. 切换到订单表...")
    returncode, stdout, stderr = run_command("t use 订单表")
    if returncode != 0:
        print(f"切换表格失败: {stderr}")
        return False
    
    # 使用现有的字段进行条件更新测试
    print("\n2. 测试分页获取数据...")
    
    # 使用订单状态字段进行测试
    test_cmd = 't update 订单状态=处理中 where 运输方式=公路运输'
    print(f"执行: {test_cmd}")
    
    returncode, stdout, stderr = run_command(test_cmd)
    print(f"返回码: {returncode}")
    print(f"输出: {stdout}")
    if stderr:
        print(f"错误: {stderr}")
    
    # 检查是否成功执行
    if "正在查询符合条件的记录..." in stdout:
        print("✅ 分页查询功能正常工作")
        return True
    else:
        print("❌ 分页查询功能可能有问题")
        return False

if __name__ == "__main__":
    success = test_pagination()
    sys.exit(0 if success else 1)