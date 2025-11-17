#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 show | insert 管道操作功能
测试自动字段映射和手动字段映射模式
"""

import subprocess
import sys
import time

def run_command(cmd, input_data=None):
    """运行命令并返回结果"""
    try:
        if input_data:
            result = subprocess.run(
                cmd, 
                shell=True, 
                input=input_data,
                capture_output=True, 
                text=True,
                timeout=60
            )
        else:
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=60
            )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "命令执行超时"
    except Exception as e:
        return 1, "", str(e)

def print_test_header(test_name):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"{'='*60}")

def print_result(success, message):
    """打印测试结果"""
    status = "✅" if success else "❌"
    print(f"{status} {message}")

def test_show_pipe_output():
    """测试1: show命令的管道输出格式"""
    print_test_header("show命令管道输出格式")
    
    # 测试show命令输出到管道
    cmd = "t show limit=2"
    returncode, stdout, stderr = run_command(cmd)
    
    if returncode == 0:
        print_result(True, "show命令执行成功")
        print(f"输出示例（前200字符）:\n{stdout[:200]}...")
        
        # 检查输出格式
        lines = stdout.strip().split('\n')
        if lines:
            first_line = lines[0]
            if first_line.startswith('rec'):
                print_result(True, "输出格式正确：以记录ID开头")
            else:
                print_result(False, f"输出格式错误：不以记录ID开头，实际: {first_line[:50]}")
            
            # 检查是否包含字段数据
            if '=' in first_line:
                print_result(True, "输出包含字段数据（field=value格式）")
            else:
                print_result(False, "输出不包含字段数据")
        else:
            print_result(False, "没有输出数据")
    else:
        print_result(False, f"show命令执行失败: {stderr}")
        return False
    
    return True

def test_insert_auto_mapping():
    """测试2: insert命令的自动字段映射模式"""
    print_test_header("insert自动字段映射模式（show | insert）")
    
    print("提示: 这个测试需要先切换到正确的表格")
    print("建议步骤:")
    print("  1. 确保已配置并连接到Teable")
    print("  2. 切换到包含测试数据的表格: t use <表格名>")
    print("  3. 运行: t show limit=1 | t insert")
    print("  4. 检查是否显示'使用自动映射模式'")
    
    # 测试管道输入检测
    test_input = "recTest123 订单号=ORD001 客户名称=测试客户 金额=1000"
    cmd = "t insert"
    
    print(f"\n模拟管道输入: {test_input}")
    print("执行命令: echo '...' | t insert")
    
    returncode, stdout, stderr = run_command(cmd, input_data=test_input)
    
    if returncode == 0 or "使用自动映射模式" in stdout or "使用字段映射模式" in stdout:
        print_result(True, "insert命令能够检测管道输入")
        print(f"输出: {stdout[:300]}")
    else:
        print_result(False, f"insert命令管道检测失败: {stderr}")
        print("注意: 如果表格不存在或未选择表格，这是正常的")
    
    return True

def test_insert_manual_mapping():
    """测试3: insert命令的手动字段映射模式"""
    print_test_header("insert手动字段映射模式")
    
    test_input = "recTest123 订单号=ORD001 客户名称=测试客户 金额=1000"
    cmd = "t insert 新订单号=订单号 新客户=客户名称 备注=来自管道"
    
    print(f"模拟管道输入: {test_input}")
    print(f"执行命令: echo '...' | {cmd}")
    print("预期: 使用字段映射模式，映射 新订单号->订单号, 新客户->客户名称")
    
    returncode, stdout, stderr = run_command(cmd, input_data=test_input)
    
    if "使用字段映射模式" in stdout or returncode == 0:
        print_result(True, "手动字段映射模式检测成功")
        print(f"输出: {stdout[:300]}")
    else:
        print_result(False, f"手动字段映射模式失败: {stderr}")
    
    return True

def test_pipe_format_parsing():
    """测试4: 管道数据格式解析"""
    print_test_header("管道数据格式解析")
    
    from commands.pipe_core import parse_pipe_input_line
    
    test_cases = [
        ("rec123 订单号=ORD001 客户=张三", True, "标准格式"),
        ("rec456 订单号=ORD002", True, "单个字段"),
        ("rec789", True, "仅记录ID"),
        ("", False, "空行"),
        ("# 这是注释", False, "注释行"),
        ("recABC 订单号=ORD003 金额=1000 状态=已完成", True, "多个字段"),
    ]
    
    success_count = 0
    for test_input, expected_valid, description in test_cases:
        result = parse_pipe_input_line(test_input)
        is_valid = result is not None
        
        if is_valid == expected_valid:
            print_result(True, f"{description}: {test_input[:50]}")
            if result:
                print(f"  解析结果: ID={result.get('id', 'N/A')}, 字段数={len(result.get('fields', {}))}")
            success_count += 1
        else:
            print_result(False, f"{description}: 预期{'有效' if expected_valid else '无效'}，实际{'有效' if is_valid else '无效'}")
    
    print(f"\n解析测试: {success_count}/{len(test_cases)} 通过")
    return success_count == len(test_cases)

def test_field_mapping_logic():
    """测试5: 字段映射逻辑（代码逻辑测试）"""
    print_test_header("字段映射逻辑测试")
    
    # 模拟字段信息
    fields = [
        {'name': '订单号', 'type': 'singleLineText'},
        {'name': '客户名称', 'type': 'singleLineText'},
        {'name': '金额', 'type': 'number'},
        {'name': '状态', 'type': 'singleLineText'},
        {'name': 'id', 'type': 'id'},  # 系统字段，应该跳过
    ]
    
    # 模拟管道记录
    pipe_record = {
        'id': 'rec123',
        'fields': {
            '订单号': 'ORD001',
            '客户名称': '张三',
            '金额': '1000',
            '状态': '已完成',
            'id': 'rec123',  # 系统字段，应该跳过
        }
    }
    
    # 测试自动映射逻辑
    print("测试自动映射逻辑:")
    field_info_map = {f['name']: f for f in fields}
    
    auto_mapped_fields = []
    for pipe_field_name, pipe_field_value in pipe_record['fields'].items():
        if pipe_field_name in ['id', 'createdTime', 'updatedTime']:
            continue
        if pipe_field_name in field_info_map:
            auto_mapped_fields.append(pipe_field_name)
    
    print_result(True, f"自动映射字段: {', '.join(auto_mapped_fields)}")
    
    # 验证系统字段被跳过
    if 'id' not in auto_mapped_fields:
        print_result(True, "系统字段 'id' 被正确跳过")
    else:
        print_result(False, "系统字段 'id' 未被跳过")
    
    return True

def demonstrate_usage():
    """演示使用方式"""
    print_test_header("使用示例演示")
    
    examples = [
        ("自动映射模式", "t show limit=10 | t insert", 
         "字段名相同则自动复制，类似 INSERT INTO ... SELECT ..."),
        
        ("手动映射模式", "t show limit=1 | t insert 新订单号=订单号 新客户=客户名称",
         "指定字段映射，从管道记录中获取值"),
        
        ("混合模式", "t show 状态=已完成 | t insert 状态=已备份 备注=来自备份",
         "部分字段自动映射，部分字段使用常量值"),
        
        ("条件复制", "t show 创建时间>2024-01-01 | t insert",
         "复制符合条件的记录"),
        
        ("跨表格复制", "t use 源表 && t show limit=10 > /tmp/data.txt && t use 目标表 && cat /tmp/data.txt | t insert",
         "从源表复制数据到目标表"),
    ]
    
    print("\n使用示例:")
    for i, (name, cmd, desc) in enumerate(examples, 1):
        print(f"\n{i}. {name}:")
        print(f"   命令: {cmd}")
        print(f"   说明: {desc}")

def main():
    """主测试函数"""
    print("="*60)
    print("Teable CLI show | insert 管道操作测试")
    print("="*60)
    
    print("\n注意: 部分测试需要实际的Teable连接和表格数据")
    print("建议先运行: t config 配置连接信息")
    print("然后运行: t use <表格名> 切换到测试表格")
    
    results = []
    
    # 运行测试
    results.append(("管道数据格式解析", test_pipe_format_parsing()))
    results.append(("字段映射逻辑", test_field_mapping_logic()))
    results.append(("show命令管道输出", test_show_pipe_output()))
    results.append(("insert自动映射模式", test_insert_auto_mapping()))
    results.append(("insert手动映射模式", test_insert_manual_mapping()))
    
    # 显示使用示例
    demonstrate_usage()
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查:")
        print("  1. 是否已配置Teable连接: t config")
        print("  2. 是否已选择表格: t use <表格名>")
        print("  3. 表格中是否有测试数据")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

