#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话管理
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime


class Session:
    """Teable CLI 会话管理"""
    
    def __init__(self, config):
        self.config = config
        self.current_table = None
        self.current_table_id = None
        self.tables_cache = {}  # 表格信息缓存
        self.load_session()
    
    def load_session(self):
        """加载会话信息"""
        session_data = self.config.load_session()
        if session_data:
            self.current_table = session_data.get('current_table')
            self.current_table_id = session_data.get('current_table_id')
            self.tables_cache = session_data.get('tables_cache', {})
    
    def save_session(self):
        """保存会话信息"""
        session_data = {
            'current_table': self.current_table,
            'current_table_id': self.current_table_id,
            'tables_cache': self.tables_cache,
            'last_updated': datetime.now().isoformat()
        }
        self.config.save_session(session_data)
    
    def set_current_table(self, table_name: str, table_id: str):
        """设置当前表格"""
        self.current_table = table_name
        self.current_table_id = table_id
        self.save_session()
    
    def get_current_table(self) -> Optional[str]:
        """获取当前表格名称"""
        return self.current_table
    
    def get_current_table_id(self) -> Optional[str]:
        """获取当前表格ID"""
        return self.current_table_id
    
    def is_table_selected(self) -> bool:
        """检查是否已选择表格"""
        return self.current_table is not None
    
    def clear_session(self):
        """清除会话信息"""
        self.current_table = None
        self.current_table_id = None
        self.tables_cache = {}
        self.config.clear_session()
    
    def cache_table_info(self, table_name: str, table_info: Dict[str, Any]):
        """缓存表格信息"""
        self.tables_cache[table_name] = {
            'info': table_info,
            'cached_at': datetime.now().isoformat()
        }
        self.save_session()
    
    def get_cached_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取缓存的表格信息"""
        cached = self.tables_cache.get(table_name)
        if cached:
            return cached.get('info')
        return None
    
    def get_all_cached_tables(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的表格信息"""
        return {name: data['info'] for name, data in self.tables_cache.items()}
    
    def print_session_status(self):
        """打印会话状态"""
        if self.is_table_selected():
            print(f"当前表格: {self.current_table} (ID: {self.current_table_id})")
        else:
            print("未选择任何表格")
        
        if self.tables_cache:
            print(f"缓存表格数: {len(self.tables_cache)}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return {
            'current_table': self.current_table,
            'current_table_id': self.current_table_id,
            'tables_cached': len(self.tables_cache),
            'is_table_selected': self.is_table_selected()
        }
