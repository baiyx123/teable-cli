#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件管理
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Teable CLI 配置管理"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.teable'
        self.config_file = self.config_dir / 'config.json'
        self.session_file = self.config_dir / 'session.json'
        self.history_file = self.config_dir / 'history'
        
        # 默认配置
        self.defaults = {
            'base_url': 'https://app.teable.cn',
            'token': '',
            'base_id': '',
            'timeout': 30,
            'page_size': 20,
            'color_output': True,
            'table_format': 'simple',
            'max_history': 1000
        }
        
        self.config = self.defaults.copy()
        self.ensure_config_dir()
        self.load_config()
    
    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(exist_ok=True)
        # 设置目录权限为700（仅所有者可读写执行）
        os.chmod(self.config_dir, 0o700)
    
    def load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"警告: 配置文件加载失败: {e}")
                print("使用默认配置")
    
    def save_config(self):
        """保存配置文件"""
        try:
            # 不保存敏感信息到配置文件
            safe_config = {k: v for k, v in self.config.items() 
                          if k not in ['token']}
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(safe_config, f, indent=2, ensure_ascii=False)
            
            # 设置文件权限为600（仅所有者可读写）
            os.chmod(self.config_file, 0o600)
            
        except IOError as e:
            print(f"错误: 配置文件保存失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates: Dict[str, Any]):
        """批量更新配置"""
        self.config.update(updates)
        self.save_config()
    
    def is_configured(self) -> bool:
        """检查是否已配置必要的连接信息"""
        return bool(self.get('token') and self.get('base_id'))
    
    def get_connection_info(self) -> Dict[str, str]:
        """获取连接信息"""
        return {
            'base_url': self.get('base_url'),
            'token': self.get('token'),
            'base_id': self.get('base_id')
        }
    
    def load_session(self) -> Dict[str, Any]:
        """加载会话信息"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}
    
    def save_session(self, session_data: Dict[str, Any]):
        """保存会话信息"""
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            # 设置文件权限为600
            os.chmod(self.session_file, 0o600)
            
        except IOError as e:
            print(f"错误: 会话文件保存失败: {e}")
    
    def clear_session(self):
        """清除会话信息"""
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except IOError:
                pass
    
    def get_history_file(self) -> Path:
        """获取历史文件路径"""
        return self.history_file
    
    def print_config(self):
        """打印当前配置"""
        print("当前配置:")
        for key, value in self.config.items():
            if key == 'token':
                # 隐藏token信息
                value = '*' * len(str(value)) if value else ''
            print(f"  {key}: {value}")
