#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teable CLI 管道操作核心组件
提供管道输入/输出检测和格式化功能
"""

import sys
from typing import Dict, Any, Optional, List


def is_pipe_input() -> bool:
    """检测是否有管道输入"""
    return not sys.stdin.isatty()


def is_pipe_output() -> bool:
    """检测是否输出到管道"""
    return not sys.stdout.isatty()


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
    
    # 只解析以rec开头的行（记录ID格式），忽略其他行（如人类可读的消息）
    if not record_id or not record_id.startswith('rec'):
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
