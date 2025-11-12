#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teable API 客户端
基于测试结果整理的完整 API 客户端
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TeableClient:
    """Teable API 客户端"""
    
    def __init__(self, base_url: str, token: str, base_id: str):
        """
        初始化 Teable 客户端
        
        Args:
            base_url: API 基础URL
            token: 认证令牌
            base_id: 数据库ID
        """
        self.base_url = base_url
        self.token = token
        self.base_id = base_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        logger.info("Teable 客户端初始化完成")

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            data: 请求数据
            params: 查询参数
            
        Returns:
            API 响应数据
        """
        url = f"{self.base_url}/api{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers,
                data=json.dumps(data) if data else None,
                params=params, timeout=10
            )
            # 对于创建操作，201也是成功状态码
            if response.status_code not in [200, 201]:
                response.raise_for_status()
            
            # 检查响应内容
            if not response.text.strip():
                logger.error(f"响应为空: {url}")
                raise Exception("响应为空")
            
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"响应内容: {response.text[:500]}")
                raise Exception(f"JSON解析失败: {e}")
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"请求异常: {e}")
            logger.error(f"请求失败: {response.status_code} - {response.text}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"网络连接错误: {e}")
            raise
        except Exception as e:
            logger.error(f"发生未知错误: {e}")
            raise

    def create_table(self, table_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建表格
        
        Args:
            table_config: 表格配置
                {
                    "name": "表格名称",
                    "description": "表格描述",
                    "fields": [
                        {
                            "name": "字段名称",
                            "type": "字段类型"
                        }
                    ]
                }
                
        Returns:
            创建的表格信息
        """
        logger.info(f"创建表格: {table_config.get('name', '未知')}")
        endpoint = f"/base/{self.base_id}/table/"
        return self._request("POST", endpoint, data=table_config)
    
    def get_table_fields(self, table_id: str) -> List[Dict[str, Any]]:
        """
        获取表格字段信息
        
        Args:
            table_id: 表格ID
            
        Returns:
            字段列表
        """
        logger.info(f"获取表格字段: {table_id}")
        endpoint = f"/table/{table_id}/field/"
        return self._request("GET", endpoint)

    def add_field(self, table_id: str, field_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加字段
        
        Args:
            table_id: 表格ID
            field_config: 字段配置
                普通字段:
                {
                    "name": "字段名称",
                    "type": "字段类型",
                    "description": "字段描述"
                }
                
                关联字段:
                {
                    "type": "link",
                    "name": "关联字段名称",  # 可选
                    "options": {
                        "relationship": "manyMany",  # 或 "manyOne", "oneMany", "oneOne"
                        "foreignTableId": "tblXXXXXXXXXXXXXXXX"
                    }
                }
                
                引用字段:
                {
                    "type": "singleLineText",  # 必须与被引用字段的类型一致
                    "name": "引用字段名称",
                    "isLookup": True,          # 标识这是一个lookup字段
                    "lookupOptions": {
                        "foreignTableId": "tblXXXXXXXXXXXXXXXX",  # 外表ID
                        "linkFieldId": "fldXXXXXXXXXXXXXXXX",     # 当前表中的link字段ID
                        "lookupFieldId": "fldYYYYYYYYYYYYYYYY"    # 外表中要查找的字段ID
                    }
                }
                
                公式字段:
                {
                    "type": "formula",
                    "name": "公式字段名称",
                    "options": {
                        "expression": "{字段ID1} * {字段ID2} + {字段ID3}"
                    }
                }
                
        Returns:
            添加的字段信息
        """
        logger.info(f"向表格 {table_id} 添加字段: {field_config.get('name', '未知')}")
        endpoint = f"/table/{table_id}/field/"
        return self._request("POST", endpoint, data=field_config)

    def insert_records(self, table_id: str, records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        插入记录
        
        Args:
            table_id: 表格ID
            records_data: 记录数据列表
                [
                    {
                        "fields": {
                            "字段名": "字段值"
                        }
                    }
                ]
                
        Returns:
            插入结果
        """
        logger.info(f"向表格 {table_id} 插入 {len(records_data)} 条记录")
        endpoint = f"/table/{table_id}/record/"
        return self._request("POST", endpoint, data={"records": records_data})

    def get_records(self, table_id: str, page: int = 1, page_size: int = 100, **kwargs) -> Dict[str, Any]:
        """
        查询记录
        
        Args:
            table_id: 表格ID
            page: 页码，从1开始
            page_size: 每页记录数
            **kwargs: 其他查询参数，如filter, orderBy, take, skip等
            
        Returns:
            记录列表
        """
        # 计算skip和take参数
        skip = (page - 1) * page_size
        take = page_size
        
        logger.info(f"查询表格 {table_id} 的记录，skip={skip}, take={take}")
        endpoint = f"/table/{table_id}/record/"
        params = {
            'skip': skip,
            'take': take
        }
        
        # 添加其他查询参数
        if kwargs:
            # 如果提供了take和skip，使用提供的值
            if 'take' in kwargs:
                params['take'] = kwargs.pop('take')
            if 'skip' in kwargs:
                params['skip'] = kwargs.pop('skip')
            
            # 添加其他参数
            params.update(kwargs)
        
        logger.info(f"实际请求参数: {params}")
        return self._request("GET", endpoint, params=params)

    def update_record(self, table_id: str, record_id: str, 
                     fields_data: Dict[str, Any], use_field_ids: bool = False) -> Dict[str, Any]:
        """
        更新记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            fields_data: 要更新的字段数据
            use_field_ids: 是否使用字段ID作为键（用于更新关联字段）
            
        Returns:
            更新结果
        """
        logger.info(f"更新表格 {table_id} 的记录 {record_id}")
        endpoint = f"/table/{table_id}/record/{record_id}"
        
        if use_field_ids:
            # 用于更新关联字段的格式
            update_data = {
                "fieldKeyType": "id",
                "record": {
                    "fields": fields_data
                }
            }
        else:
            # 普通字段更新格式
            update_data = {"fields": fields_data}
        
        return self._request("PATCH", endpoint, data=update_data)
    
    def batch_update_records(self, table_id: str, updates: List[Dict[str, Any]], 
                             use_field_ids: bool = False) -> Dict[str, Any]:
        """
        批量更新记录
        
        Args:
            table_id: 表格ID
            updates: 更新数据列表，每个元素包含record_id和fields_data
            use_field_ids: 是否使用字段ID作为键
            
        Returns:
            批量更新结果
        """
        logger.info(f"批量更新表格 {table_id} 的 {len(updates)} 条记录")
        endpoint = f"/table/{table_id}/record"
        
        # 准备批量更新数据 - 使用正确的API格式
        batch_data = []
        for update in updates:
            record_id = update['record_id']
            fields_data = update['fields_data']
            
            record_data = {
                "id": record_id,
                "fields": fields_data
            }
            batch_data.append(record_data)
        
        return self._request("PATCH", endpoint, data={"records": batch_data})

    def delete_record(self, table_id: str, record_id: str) -> bool:
        """
        删除记录
        
        Args:
            table_id: 表格ID
            record_id: 记录ID
            
        Returns:
            删除是否成功
        """
        logger.info(f"删除表格 {table_id} 的记录 {record_id}")
        endpoint = f"/table/{table_id}/record/{record_id}"
        try:
            self._request("DELETE", endpoint)
            return True
        except Exception as e:
            logger.error(f"删除记录失败: {e}")
            return False

    def create_view(self, table_id: str, view_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建视图
        
        Args:
            table_id: 表格ID
            view_config: 视图配置
            
        Returns:
            创建的视图信息
        """
        logger.info(f"为表格 {table_id} 创建视图: {view_config.get('name', '未知')}")
        endpoint = f"/table/{table_id}/view/"
        return self._request("POST", endpoint, data=view_config)

    def get_views(self, table_id: str) -> List[Dict[str, Any]]:
        """
        获取表格的所有视图
        
        Args:
            table_id: 表格ID
            
        Returns:
            视图列表
        """
        logger.info(f"获取表格 {table_id} 的所有视图")
        endpoint = f"/table/{table_id}/view/"
        response = self._request("GET", endpoint)
        
        # 处理不同的返回格式
        if isinstance(response, list):
            return response
        else:
            return response.get('views', [])

    def get_table_details(self, table_id: str) -> Dict[str, Any]:
        """
        获取表格详情
        
        Args:
            table_id: 表格ID
            
        Returns:
            表格详情
        """
        logger.info(f"获取表格 {table_id} 的详情")
        endpoint = f"/base/{self.base_id}/table/{table_id}"
        return self._request("GET", endpoint)
    
    def delete_table(self, table_id: str) -> bool:
        """
        删除表格
        
        Args:
            table_id: 表格ID
            
        Returns:
            是否删除成功
        """
        logger.info(f"删除表格: {table_id}")
        endpoint = f"/base/{self.base_id}/table/{table_id}"
        try:
            # 删除操作可能返回空响应，直接检查状态码
            response = requests.delete(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"删除表格失败: {e}")
            return False
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """
        获取所有表格列表
        
        Returns:
            表格列表
        """
        logger.info("获取表格列表")
        endpoint = f"/base/{self.base_id}/table"
        return self._request("GET", endpoint)

    def delete_field(self, table_id: str, field_id: str) -> bool:
        """
        删除字段
        
        Args:
            table_id: 表格 ID
            field_id: 字段 ID
            
        Returns:
            删除是否成功
        """
        logger.info(f"删除字段: {field_id}")
        endpoint = f"/table/{table_id}/field/{field_id}"
        try:
            self._request("DELETE", endpoint)
            logger.info(f"✅ 字段删除成功: {field_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 字段删除失败: {field_id}, 错误: {e}")
            return False

    def batch_add_fields(self, table_id: str, field_configs: List[Dict], window_id: Optional[str] = None) -> Dict:
        """
        批量添加字段
        
        Args:
            table_id: 表格 ID
            field_configs: 字段配置列表
            window_id: 窗口 ID（可选）
            
        Returns:
            批量创建结果
        """
        url = f"/table/{table_id}/field"
        
        headers = self.headers.copy()
        if window_id:
            headers['x-window-id'] = window_id
        
        data = {
            "fields": field_configs
        }
        
        logger.info(f"批量添加字段到表 {table_id}，字段数量: {len(field_configs)}")
        
        try:
            response = requests.post(
                url=f"{self.base_url}{url}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            logger.info(f"响应状态码: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"批量添加字段失败: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            result = response.json()
            logger.debug(f"批量添加字段结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"批量添加字段请求异常: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            raise

    def convert_field_to_formula(self, table_id: str, field_id: str, expression: str, 
                                time_zone: str = "Asia/Shanghai", formatting: Optional[Dict] = None,
                                window_id: Optional[str] = None) -> Dict:
        """
        将文本字段转换为公式字段
        
        Args:
            table_id: 表格 ID
            field_id: 要转换的字段 ID
            expression: 公式表达式
            time_zone: 时区（日期公式需要，默认为 Asia/Shanghai）
            formatting: 格式化选项（可选）
            window_id: 窗口 ID（可选）
            
        Returns:
            转换结果
        """
        endpoint = f"/table/{table_id}/field/{field_id}/convert"
        
        # 构建请求头
        headers = self.headers.copy()
        if window_id:
            headers['x-window-id'] = window_id
        
        # 构建请求数据
        data = {
            "type": "formula",
            "options": {
                "expression": expression,
                "timeZone": time_zone
            }
        }
        
        # 添加格式化选项（如果提供）
        if formatting:
            data["options"]["formatting"] = formatting
        
        logger.info(f"转换字段 {field_id} 为公式字段，表达式: {expression}")
        
        try:
            response = requests.put(
                url=f"{self.base_url}{endpoint}",
                headers=headers,
                json=data,
                timeout=30
            )
            
            logger.info(f"响应状态码: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"字段转换失败: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            result = response.json()
            logger.debug(f"转换结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"字段转换请求异常: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            raise


# 支持的字段类型
SUPPORTED_FIELD_TYPES = [
    "singleLineText",    # 单行文本
    "longText",         # 长文本
    "number",           # 数字
    "checkbox",         # 复选框
    "singleSelect",     # 单选
    "multipleSelect",   # 多选
    "date",             # 日期
    "currency",         # 货币
    "rating",           # 评分
    "formula",          # 公式
    "rollup",           # 汇总
    "createdTime",      # 创建时间
    "lastModifiedTime", # 最后修改时间
    "createdBy",        # 创建者
    "lastModifiedBy",   # 最后修改者
    "autoNumber",       # 自动编号
    "button"            # 按钮
]

# 关联字段类型
LINK_FIELD_TYPES = [
    "link"                     # 关联字段 (现在支持了！)
]

# 不支持的字段类型
UNSUPPORTED_FIELD_TYPES = [
    "linkToAnotherRecord",     # 关联到另一条记录
    "phoneNumber",             # 电话号码 (应使用 singleLineText)
    "email"                    # 邮箱 (应使用 singleLineText)
]


def create_field_config(name: str, field_type: str, **kwargs) -> Dict[str, Any]:
    """
    创建字段配置的辅助函数
    
    Args:
        name: 字段名称
        field_type: 字段类型
        **kwargs: 其他字段属性
        
    Returns:
        字段配置字典
    """
    if field_type not in SUPPORTED_FIELD_TYPES and field_type not in LINK_FIELD_TYPES:
        logger.warning(f"字段类型 {field_type} 可能不被支持")
    
    config = {
        "name": name,
        "type": field_type
    }
    
    # 添加其他属性
    for key, value in kwargs.items():
        if value is not None:
            config[key] = value
    
    return config


def create_link_field_config(name: str, relationship: str, foreign_table_id: str) -> Dict[str, Any]:
    """
    创建关联字段配置的辅助函数
    
    Args:
        name: 字段名称 (可选，不提供会自动生成)
        relationship: 关联关系类型 ("manyMany", "manyOne", "oneMany", "oneOne")
        foreign_table_id: 外键表格ID
        
    Returns:
        关联字段配置字典
    """
    config = {
        "type": "link",
        "options": {
            "relationship": relationship,
            "foreignTableId": foreign_table_id
        }
    }
    
    if name:
        config["name"] = name
    
    return config


def create_lookup_field_config(name: str, field_type: str, foreign_table_id: str, 
                              link_field_id: str, lookup_field_id: str) -> Dict[str, Any]:
    """
    创建引用字段配置的辅助函数
    
    Args:
        name: 字段名称
        field_type: 字段类型 (必须与被引用字段的类型一致)
        foreign_table_id: 外键表格ID
        link_field_id: 当前表中的关联字段ID
        lookup_field_id: 外表中要查找的字段ID
        
    Returns:
        引用字段配置字典
    """
    return {
        "type": field_type,
        "name": name,
        "isLookup": True,
        "lookupOptions": {
            "foreignTableId": foreign_table_id,
            "linkFieldId": link_field_id,
            "lookupFieldId": lookup_field_id
        }
    }


    def create_formula_field_config(name: str, expression: str) -> Dict[str, Any]:
        """
        创建公式字段配置的辅助函数
        
        Args:
            name: 字段名称
            expression: 公式表达式，使用 {字段ID} 引用其他字段
            
        Returns:
            公式字段配置字典
        """
        return {
            "type": "formula",
            "name": name,
            "options": {
                "expression": expression
            }
        }

    def create_single_select_field_config(name: str, choices: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        创建单选字段配置的辅助函数
        
        Args:
            name: 字段名称
            choices: 选项列表，格式：[{"name": "选项名称", "color": "颜色"}]
            
        Returns:
            单选字段配置字典
        """
        return {
            "type": "singleSelect",
            "name": name,
            "options": {
                "choices": choices
            }
        }

    def create_multiple_select_field_config(name: str, choices: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        创建多选字段配置的辅助函数
        
        Args:
            name: 字段名称
            choices: 选项列表，格式：[{"name": "选项名称", "color": "颜色"}]
            
        Returns:
            多选字段配置字典
        """
        return {
            "type": "multipleSelect",
            "name": name,
            "options": {
                "choices": choices
            }
        }

    def create_view_config(name: str, description: str = "", view_type: str = "grid",
                          options: Dict[str, Any] = None, filter_config: Dict[str, Any] = None,
                          sort_config: Dict[str, Any] = None, column_meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        创建视图配置的辅助函数
        
        Args:
            name: 视图名称
            description: 视图描述
            view_type: 视图类型（默认 grid）
            options: 视图选项
            filter_config: 过滤配置
            sort_config: 排序配置
            column_meta: 列配置
            
        Returns:
            视图配置字典
        """
        config = {
            "name": name,
            "description": description,
            "type": view_type
        }
        
        if options:
            config["options"] = options
        if filter_config:
            config["filter"] = filter_config
        if sort_config:
            config["sort"] = sort_config
        if column_meta:
            config["columnMeta"] = column_meta
            
        return config

    def create_filter_config(conjunction: str = "and", filter_set: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建过滤配置的辅助函数
        
        Args:
            conjunction: 逻辑连接符（and/or）
            filter_set: 过滤条件列表
            
        Returns:
            过滤配置字典
        """
        return {
            "conjunction": conjunction,
            "filterSet": filter_set or []
        }

    def create_sort_config(sort_objects: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        创建排序配置的辅助函数
        
        Args:
            sort_objects: 排序对象列表
            
        Returns:
            排序配置字典
        """
        return {
            "sortObjs": sort_objects or []
        }

    def create_system_field_config(name: str, field_type: str) -> Dict[str, Any]:
        """
        创建系统字段配置的辅助函数
        
        Args:
            name: 字段名称
            field_type: 系统字段类型
            
        Returns:
            系统字段配置字典
        """
        return {
            "type": field_type,
            "name": name
        }


def create_record_data(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    创建记录数据的辅助函数
    
    Args:
        fields: 字段数据
        
    Returns:
        记录数据字典
    """
    return {"fields": fields}


# 使用示例
if __name__ == "__main__":
    # 配置
    BASE_URL = "https://app.teable.cn/api"
    TOKEN = "teable_acclJEk4pc3WDzywrRl_hcpXy3tSAJcTUStdGJz0uZT74rzpTOIA/wnbZeukdm4="
    BASE_ID = "bsewQso4GDsJoRyuFDA"
    
    # 创建客户端
    client = TeableClient(BASE_URL, TOKEN, BASE_ID)
    
    try:
        # 创建第一个表格
        table1_config = {
            "name": "用户表",
            "description": "用户信息表",
            "fields": [
                create_field_config("姓名", "singleLineText"),
                create_field_config("年龄", "number")
            ]
        }
        
        created_table1 = client.create_table(table1_config)
        table1_id = created_table1["id"]
        print(f"用户表创建成功，ID: {table1_id}")
        
        # 创建第二个表格
        table2_config = {
            "name": "订单表",
            "description": "订单信息表",
            "fields": [
                create_field_config("订单号", "singleLineText"),
                create_field_config("金额", "number")
            ]
        }
        
        created_table2 = client.create_table(table2_config)
        table2_id = created_table2["id"]
        print(f"订单表创建成功，ID: {table2_id}")
        
        # 添加关联字段
        link_field = create_link_field_config("用户", "manyOne", table1_id)
        added_field = client.add_field(table2_id, link_field)
        print(f"关联字段添加成功，字段ID: {added_field.get('id')}")
        
        # 插入记录
        user_records = [
            create_record_data({"姓名": "张三", "年龄": 25}),
            create_record_data({"姓名": "李四", "年龄": 30})
        ]
        
        inserted_users = client.insert_records(table1_id, user_records)
        print(f"用户记录插入成功，插入了 {len(inserted_users.get('records', []))} 条记录")
        
        order_records = [
            create_record_data({"订单号": "ORD001", "金额": 1000}),
            create_record_data({"订单号": "ORD002", "金额": 2000})
        ]
        
        inserted_orders = client.insert_records(table2_id, order_records)
        print(f"订单记录插入成功，插入了 {len(inserted_orders.get('records', []))} 条记录")
        
        # 查询记录
        all_users = client.get_records(table1_id)
        print(f"查询到 {len(all_users.get('records', []))} 条用户记录")
        
        all_orders = client.get_records(table2_id)
        print(f"查询到 {len(all_orders.get('records', []))} 条订单记录")
        
    except Exception as e:
        print(f"操作失败: {e}")
