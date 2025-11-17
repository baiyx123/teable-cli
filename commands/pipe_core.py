#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teable CLI 智能管道操作核心组件
自动检测管道模式，无需额外参数
"""

import sys
import json
import select
from typing import List, Dict, Any, Optional, Iterator


def is_pipe_input() -> bool:
    """检测是否有管道输入"""
    return not sys.stdin.isatty()


def is_pipe_output() -> bool:
    """检测是否输出到管道"""
    return not sys.stdout.isatty()


def has_pipe_input_data(timeout: float = 0.1) -> bool:
    """检测标准输入是否有数据可读
    
    注意：在非交互式环境中（如脚本），即使 stdin 不是 tty，
    也不意味着一定有管道数据。需要实际检查是否有数据可读。
    """
    if not is_pipe_input():
        return False
    
    try:
        # 使用select检查是否有数据可读
        readable, _, _ = select.select([sys.stdin], [], [], timeout)
        return bool(readable)
    except (select.error, OSError):
        return False
    except Exception:
        # 捕获其他可能的异常
        return False


def wait_for_pipe_input(timeout: float = 1.0) -> bool:
    """等待管道输入数据"""
    if not is_pipe_input():
        return False
    
    try:
        readable, _, _ = select.select([sys.stdin], [], [], timeout)
        return bool(readable)
    except (select.error, OSError):
        return False


class SimplePipeData:
    """简单的管道数据格式"""
    
    def __init__(self, record_id: str, fields: Dict[str, Any] = None):
        self.record_id = record_id
        self.fields = fields or {}
    
    def to_line(self) -> str:
        """转换为管道输出行格式"""
        if not self.fields:
            return self.record_id
        
        field_parts = []
        for field_name, value in self.fields.items():
            field_parts.append(f"{field_name}={value}")
        
        return f"{self.record_id} {' '.join(field_parts)}"
    
    @classmethod
    def from_line(cls, line: str) -> 'SimplePipeData':
        """从管道输入行解析"""
        line = line.strip()
        if not line:
            return None
        
        parts = line.split(' ', 1)
        record_id = parts[0]
        
        fields = {}
        if len(parts) > 1:
            # 解析字段部分
            field_part = parts[1]
            for field_pair in field_part.split(' '):
                if '=' in field_pair:
                    field_name, field_value = field_pair.split('=', 1)
                    fields[field_name] = field_value
        
        return cls(record_id, fields)


class SimplePipeOutput:
    """简单的管道输出处理器"""
    
    def __init__(self, output_format: str = 'full'):
        """
        初始化输出处理器
        
        Args:
            output_format: 输出格式 'full' (完整) 或 'ids' (仅ID)
        """
        self.output_format = output_format
        self.record_count = 0
    
    def output_record(self, record: Dict[str, Any], selected_fields: List[str] = None):
        """输出一条记录"""
        record_id = record.get('id', '')
        
        if self.output_format == 'ids':
            print(record_id, flush=True)
        else:
            # 完整格式
            field_parts = []
            fields = record.get('fields', {})
            
            if selected_fields:
                # 只输出指定字段
                for field_name in selected_fields:
                    if field_name in fields:
                        value = fields[field_name]
                        field_parts.append(f"{field_name}={value}")
            else:
                # 输出所有字段
                for field_name, value in fields.items():
                    field_parts.append(f"{field_name}={value}")
            
            output_line = f"{record_id} {' '.join(field_parts)}" if field_parts else record_id
            print(output_line, flush=True)
        
        self.record_count += 1


class SimplePipeInput:
    """简单的管道输入处理器"""
    
    def read_records(self, input_stream=None) -> List[Dict[str, Any]]:
        """从输入流读取记录"""
        if input_stream is None:
            input_stream = sys.stdin
        
        records = []
        for line in input_stream:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            pipe_data = SimplePipeData.from_line(line)
            if pipe_data:
                record = {
                    'id': pipe_data.record_id,
                    'fields': pipe_data.fields
                }
                records.append(record)
        
        return records
    
    def read_record_ids(self, input_stream=None) -> List[str]:
        """从输入流读取记录ID"""
        if input_stream is None:
            input_stream = sys.stdin
        
        record_ids = []
        for line in input_stream:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 只取第一个部分作为ID
            record_id = line.split(' ')[0]
            if record_id:
                record_ids.append(record_id)
        
        return record_ids


class StreamingPipeProcessor:
    """流式管道处理器 - 用于大数据量场景"""
    
    def __init__(self, batch_size: int = 50, progress_callback=None):
        """
        初始化流式处理器
        
        Args:
            batch_size: 批处理大小
            progress_callback: 进度回调函数
        """
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.processed_count = 0
    
    def process_input_stream(self, input_stream, processor_func):
        """处理输入流"""
        batch = []
        
        for line in input_stream:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            batch.append(line)
            
            # 批次满时处理
            if len(batch) >= self.batch_size:
                self._process_batch(batch, processor_func)
                batch = []
        
        # 处理剩余
        if batch:
            self._process_batch(batch, processor_func)
    
    def _process_batch(self, batch: List[str], processor_func):
        """处理一批数据"""
        # 转换格式
        records = []
        for line in batch:
            pipe_data = SimplePipeData.from_line(line)
            if pipe_data:
                record = {
                    'id': pipe_data.record_id,
                    'fields': pipe_data.fields
                }
                records.append(record)
        
        # 处理
        if records:
            processor_func(records)
            self.processed_count += len(records)
            
            # 进度回调
            if self.progress_callback:
                self.progress_callback(self.processed_count)


def is_pipe_mode() -> bool:
    """检测是否处于管道模式"""
    # 检查是否有管道输入
    return not sys.stdin.isatty()


def detect_pipe_input_format(first_line: str) -> str:
    """检测管道输入格式"""
    first_line = first_line.strip()
    
    if not first_line:
        return 'empty'
    
    # 简单格式：rec123 或 rec123 字段=值
    if first_line.startswith('rec'):
        return 'simple'
    
    # JSON格式
    if first_line.startswith('{'):
        return 'json'
    
    return 'unknown'


# 使用示例和测试
if __name__ == "__main__":
    # 测试数据
    test_record = {
        'id': 'rec123',
        'fields': {
            '订单号': 'ORD001',
            '状态': '待处理',
            '客户': '张三'
        }
    }
    
    # 测试输出
    print("=== 测试输出 ===")
    output = SimplePipeOutput('full')
    output.output_record(test_record)
    
    output_ids = SimplePipeOutput('ids')
    output_ids.output_record(test_record)
    
    # 测试输入
    print("\n=== 测试输入 ===")
    test_input = "rec123 订单号=ORD001 状态=待处理 客户=张三\nrec124 订单号=ORD002"
    
    import io
    input_stream = io.StringIO(test_input)
    
    input_handler = SimplePipeInput()
    records = input_handler.read_records(input_stream)
    
    for record in records:
        print(f"记录: {record}")
    
    # 测试流式处理
    print("\n=== 测试流式处理 ===")
    input_stream = io.StringIO(test_input)
    
    def mock_processor(records):
        print(f"处理 {len(records)} 条记录")
    
    processor = StreamingPipeProcessor(batch_size=2)
    processor.process_input_stream(input_stream, mock_processor)


class SmartPipeHandler:
    """智能管道处理器 - 零配置自动检测"""
    
    def __init__(self):
        self.input_handler = SimplePipeInput()
        self.output_handler = None
        self.stream_processor = None
    
    def detect_and_handle_output(self, records: List[Dict[str, Any]],
                               selected_fields: List[str] = None,
                               output_format: str = 'auto'):
        """
        智能检测输出模式并处理
        
        Args:
            records: 记录列表
            selected_fields: 要输出的字段
            output_format: 输出格式 ('auto', 'full', 'ids')
        """
        if output_format == 'auto':
            output_format = 'ids' if is_pipe_output() else 'full'
        
        if not self.output_handler or self.output_handler.output_format != output_format:
            self.output_handler = SimplePipeOutput(output_format)
        
        # 输出记录
        for record in records:
            self.output_handler.output_record(record, selected_fields)
    
    def detect_and_handle_input(self) -> List[Dict[str, Any]]:
        """
        智能检测输入模式并读取数据
        
        Returns:
            记录列表，如果没有管道输入则返回空列表
        """
        if not is_pipe_input():
            return []
        
        if not has_pipe_input_data():
            return []
        
        return self.input_handler.read_records()
    
    def get_pipe_mode_summary(self) -> Dict[str, Any]:
        """获取管道模式摘要"""
        return {
            'has_pipe_input': is_pipe_input(),
            'has_pipe_input_data': has_pipe_input_data() if is_pipe_input() else False,
            'is_pipe_output': is_pipe_output(),
            'input_records_count': len(self.detect_and_handle_input()) if is_pipe_input() else 0
        }


def format_record_for_pipe(record: Dict[str, Any], selected_fields: List[str] = None) -> str:
    """将记录格式化为管道输出格式"""
    record_id = record.get('id', '')
    fields = record.get('fields', {})
    
    if not fields:
        return record_id
    
    field_parts = []
    
    if selected_fields:
        # 只输出指定字段
        for field_name in selected_fields:
            if field_name in fields:
                value = fields[field_name]
                field_parts.append(f"{field_name}={value}")
    else:
        # 输出所有字段
        for field_name, value in fields.items():
            field_parts.append(f"{field_name}={value}")
    
    if field_parts:
        return f"{record_id} {' '.join(field_parts)}"
    else:
        return record_id


def parse_pipe_input_line(line: str) -> Optional[Dict[str, Any]]:
    """解析管道输入行"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    parts = line.split(' ', 1)
    record_id = parts[0] if parts else ''
    
    if not record_id:
        return None
    
    record = {
        'id': record_id,
        'fields': {}
    }
    
    # 解析字段部分
    if len(parts) > 1:
        field_part = parts[1]
        for field_pair in field_part.split(' '):
            if '=' in field_pair:
                field_name, field_value = field_pair.split('=', 1)
                record['fields'][field_name] = field_value
    
    return record


# 使用示例和测试
if __name__ == "__main__":
    print("=== 智能管道处理器测试 ===")
    
    # 测试智能处理器
    handler = SmartPipeHandler()
    pipe_summary = handler.get_pipe_mode_summary()
    print(f"管道模式摘要: {pipe_summary}")
    
    # 测试数据
    test_records = [
        {
            'id': 'rec123',
            'fields': {
                '订单号': 'ORD001',
                '状态': '待处理',
                '客户': '张三'
            }
        },
        {
            'id': 'rec124',
            'fields': {
                '订单号': 'ORD002',
                '状态': '处理中',
                '客户': '李四'
            }
        }
    ]
    
    # 测试输出格式化
    print("\n=== 输出格式化测试 ===")
    for record in test_records:
        pipe_line = format_record_for_pipe(record)
        print(f"管道格式: {pipe_line}")
    
    # 测试输入解析
    print("\n=== 输入解析测试 ===")
    test_lines = [
        "rec123 订单号=ORD001 状态=待处理 客户=张三",
        "rec124 订单号=ORD002 状态=处理中",
        "rec125",
        "# 这是注释",
        ""
    ]
    
    for line in test_lines:
        parsed = parse_pipe_input_line(line)
        if parsed:
            print(f"解析结果: {parsed}")
        else:
            print(f"跳过行: {line}")
    
    print("\n=== 管道处理器功能测试完成 ===")