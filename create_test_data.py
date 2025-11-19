#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为TMS系统各表创建测试数据
"""

from config import Config
from teable_api_client import TeableClient
from datetime import datetime, timedelta
import random
import time
import json

c = Config()
info = c.get_connection_info()
client = TeableClient(info['base_url'], info['token'], info['base_id'])

# 获取所有表
tables = client.get_tables()
table_map = {t.get('name'): t.get('id') for t in tables}

def get_table_id(table_name):
    return table_map.get(table_name)

def insert_records(table_name, records):
    """插入记录到指定表"""
    table_id = get_table_id(table_name)
    if not table_id:
        print(f"❌ 找不到表: {table_name}")
        return []
    
    print(f"\n=== 插入数据到 {table_name} ===")
    print(f"准备插入 {len(records)} 条记录...")
    
    # 将记录格式转换为API需要的格式：每条记录需要包装在"fields"键中
    formatted_records = [{"fields": record} for record in records]
    
    try:
        result = client.insert_records(table_id, formatted_records, use_field_ids=False)
        inserted_records = result.get('records', [])
        print(f"✅ 成功插入 {len(inserted_records)} 条记录")
        return inserted_records
    except Exception as e:
        error_msg = str(e)
        # 打印详细错误信息
        if '400' in error_msg:
            print(f"⚠️  详细错误信息: {error_msg}")
        print(f"❌ 插入失败: {e}")
        # 只打印前3条记录的详细信息用于调试
        if len(records) > 0:
            print(f"\n调试信息 - 第一条记录示例:")
            print(json.dumps({"fields": records[0]}, ensure_ascii=False, indent=2))
        return []

# ==================== 1. 基础数据表 ====================

print("\n" + "="*60)
print("开始创建基础数据表数据")
print("="*60)

# 1.1 客户表
customers = [
    {
        "客户名称": "上海贸易有限公司",
        "客户类型": "企业客户",
        "联系人姓名": "张经理",
        "联系电话": "021-12345678",
        "联系邮箱": "zhang@shanghai-trade.com",
        "客户地址": "上海市浦东新区世纪大道1000号",
        "信用等级": "AAA",
        "结算方式": "月结",
        "开户银行": "中国工商银行",
        "银行账号": "6222021234567890123",
        "税号": "91310000123456789X"
    },
    {
        "客户名称": "北京科技有限公司",
        "客户类型": "企业客户",
        "联系人姓名": "李总",
        "联系电话": "010-87654321",
        "联系邮箱": "li@beijing-tech.com",
        "客户地址": "北京市海淀区中关村大街1号",
        "信用等级": "AA",
        "结算方式": "账期30天",
        "开户银行": "中国建设银行",
        "银行账号": "6227001234567890124",
        "税号": "91110000123456789Y"
    },
    {
        "客户名称": "广州制造有限公司",
        "客户类型": "企业客户",
        "联系人姓名": "王主任",
        "联系电话": "020-11223344",
        "联系邮箱": "wang@guangzhou-mfg.com",
        "客户地址": "广州市天河区天河路123号",
        "信用等级": "A",
        "结算方式": "月结",
        "开户银行": "中国农业银行",
        "银行账号": "6228481234567890125",
        "税号": "91440000123456789Z"
    },
    {
        "客户名称": "深圳电子有限公司",
        "客户类型": "企业客户",
        "联系人姓名": "赵经理",
        "联系电话": "0755-22334455",
        "联系邮箱": "zhao@shenzhen-elec.com",
        "客户地址": "深圳市南山区科技园南路2号",
        "信用等级": "AA",
        "结算方式": "现结",
        "开户银行": "招商银行",
        "银行账号": "6225881234567890126",
        "税号": "91440300123456789A"
    },
    {
        "客户名称": "杭州贸易公司",
        "客户类型": "代理商",
        "联系人姓名": "钱经理",
        "联系电话": "0571-33445566",
        "联系邮箱": "qian@hangzhou-trade.com",
        "客户地址": "杭州市西湖区文三路456号",
        "信用等级": "A",
        "结算方式": "账期60天",
        "开户银行": "中国银行",
        "银行账号": "6216601234567890127",
        "税号": "91330100123456789B"
    }
]
customer_records = insert_records("客户表", customers)

# 1.2 供应商表
suppliers = [
    {
        "供应商名称": "德邦快运股份公司",
        "供应商类型": "物流公司",
        "联系人姓名": "孙经理",
        "联系电话": "400-123-4567",
        "联系邮箱": "sun@debang.com",
        "供应商地址": "上海市青浦区华新镇华志路123号",
        "服务能力": ["整车运输", "零担运输"],
        "结算方式": "月结",
        "开户银行": "中国工商银行",
        "银行账号": "6222029876543210123",
        "税号": "91310000987654321X",
        "信用等级": "AAA",
        "状态": "启用"
    },
    {
        "供应商名称": "顺丰速运有限公司",
        "供应商类型": "物流公司",
        "联系人姓名": "周经理",
        "联系电话": "400-111-1111",
        "联系邮箱": "zhou@sf-express.com",
        "供应商地址": "深圳市福田区福华路1号",
        "服务能力": ["整车运输", "零担运输", "冷链运输"],
        "结算方式": "月结",
        "开户银行": "招商银行",
        "银行账号": "6225889876543210124",
        "税号": "91440300987654321Y",
        "信用等级": "AAA",
        "状态": "启用"
    },
    {
        "供应商名称": "个体司机-张师傅",
        "供应商类型": "个体司机",
        "联系人姓名": "张师傅",
        "联系电话": "13800138001",
        "联系邮箱": "zhang@driver.com",
        "供应商地址": "江苏省苏州市工业园区",
        "服务能力": ["整车运输"],
        "结算方式": "现结",
        "开户银行": "中国建设银行",
        "银行账号": "6227009876543210125",
        "税号": "32050000987654321Z",
        "信用等级": "A",
        "状态": "启用"
    },
    {
        "供应商名称": "冷链运输车队",
        "供应商类型": "车队",
        "联系人姓名": "吴队长",
        "联系电话": "13900139002",
        "联系邮箱": "wu@cold-chain.com",
        "供应商地址": "上海市嘉定区安亭镇",
        "服务能力": ["冷链运输", "整车运输"],
        "结算方式": "账期30天",
        "开户银行": "中国农业银行",
        "银行账号": "6228489876543210126",
        "税号": "91310000987654321A",
        "信用等级": "AA",
        "状态": "启用"
    },
    {
        "供应商名称": "危险品运输公司",
        "供应商类型": "物流公司",
        "联系人姓名": "郑经理",
        "联系电话": "400-999-8888",
        "联系邮箱": "zheng@hazmat.com",
        "供应商地址": "天津市滨海新区",
        "服务能力": ["危险品运输", "整车运输"],
        "结算方式": "月结",
        "开户银行": "中国银行",
        "银行账号": "6216609876543210127",
        "税号": "91120000987654321B",
        "信用等级": "AA",
        "状态": "启用"
    }
]
supplier_records = insert_records("供应商表", suppliers)

# 1.3 地址库表
addresses = [
    {
        "地址名称": "上海仓库A",
        "省份": "上海市",
        "城市": "上海市",
        "区县": "浦东新区",
        "详细地址": "世纪大道1000号",
        "联系人姓名": "仓库管理员A",
        "联系电话": "021-11111111",
        "地址类型": "仓库"
    },
    {
        "地址名称": "北京配送中心",
        "省份": "北京市",
        "城市": "北京市",
        "区县": "海淀区",
        "详细地址": "中关村大街1号",
        "联系人姓名": "配送中心管理员",
        "联系电话": "010-22222222",
        "地址类型": "配送中心"
    },
    {
        "地址名称": "广州仓库B",
        "省份": "广东省",
        "城市": "广州市",
        "区县": "天河区",
        "详细地址": "天河路123号",
        "联系人姓名": "仓库管理员B",
        "联系电话": "020-33333333",
        "地址类型": "仓库"
    },
    {
        "地址名称": "深圳客户地址1",
        "省份": "广东省",
        "城市": "深圳市",
        "区县": "南山区",
        "详细地址": "科技园南路2号",
        "联系人姓名": "客户联系人1",
        "联系电话": "0755-44444444",
        "地址类型": "客户地址"
    },
    {
        "地址名称": "杭州客户地址2",
        "省份": "浙江省",
        "城市": "杭州市",
        "区县": "西湖区",
        "详细地址": "文三路456号",
        "联系人姓名": "客户联系人2",
        "联系电话": "0571-55555555",
        "地址类型": "客户地址"
    },
    {
        "地址名称": "苏州仓库C",
        "省份": "江苏省",
        "城市": "苏州市",
        "区县": "工业园区",
        "详细地址": "工业园区星海街200号",
        "联系人姓名": "仓库管理员C",
        "联系电话": "0512-66666666",
        "地址类型": "仓库"
    },
    {
        "地址名称": "南京配送中心",
        "省份": "江苏省",
        "城市": "南京市",
        "区县": "建邺区",
        "详细地址": "建邺路88号",
        "联系人姓名": "配送中心管理员2",
        "联系电话": "025-77777777",
        "地址类型": "配送中心"
    }
]
address_records = insert_records("地址库表", addresses)

# 1.4 产品表
products = [
    {
        "产品名称": "普通货物-电子产品",
        "产品分类": "普通货物",
        "单位": "件",
        "标准重量": 0.5,
        "标准体积": 0.1,
        "危险品等级": "非危险品",
        "存储要求": "常温干燥"
    },
    {
        "产品名称": "普通货物-服装",
        "产品分类": "普通货物",
        "单位": "箱",
        "标准重量": 0.3,
        "标准体积": 0.2,
        "危险品等级": "非危险品",
        "存储要求": "常温干燥"
    },
    {
        "产品名称": "普通货物-食品",
        "产品分类": "普通货物",
        "单位": "箱",
        "标准重量": 1.0,
        "标准体积": 0.5,
        "危险品等级": "非危险品",
        "存储要求": "常温干燥"
    },
    {
        "产品名称": "危险品-酒精",
        "产品分类": "危险品",
        "单位": "吨",
        "标准重量": 1.0,
        "标准体积": 1.2,
        "危险品等级": "3类",
        "存储要求": "远离火源，阴凉通风"
    },
    {
        "产品名称": "冷链-生鲜食品",
        "产品分类": "冷链",
        "单位": "箱",
        "标准重量": 0.8,
        "标准体积": 0.4,
        "危险品等级": "非危险品",
        "存储要求": "0-4度冷藏"
    },
    {
        "产品名称": "大件-机械设备",
        "产品分类": "大件",
        "单位": "件",
        "标准重量": 5.0,
        "标准体积": 3.0,
        "危险品等级": "非危险品",
        "存储要求": "防潮防震"
    }
]
product_records = insert_records("产品表", products)

# 1.5 车辆表
vehicles = [
    {
        "车牌号": "沪A12345",
        "车辆类型": "厢式货车",
        "车辆型号": "解放J6L",
        "车辆品牌": "一汽解放",
        "载重吨位": 10.0,
        "载重体积": 30.0,
        "购买日期": "2020-01-15",
        "保险到期日": "2025-01-15",
        "年检到期日": "2025-06-15",
        "状态": "空闲",
        "所属司机": "内部司机1"
    },
    {
        "车牌号": "京B67890",
        "车辆类型": "高栏车",
        "车辆型号": "东风天锦",
        "车辆品牌": "东风商用车",
        "载重吨位": 15.0,
        "载重体积": 40.0,
        "购买日期": "2019-05-20",
        "保险到期日": "2025-05-20",
        "年检到期日": "2025-11-20",
        "状态": "空闲",
        "所属司机": "内部司机2"
    },
    {
        "车牌号": "粤C11111",
        "车辆类型": "冷藏车",
        "车辆型号": "福田欧马可",
        "车辆品牌": "福田汽车",
        "载重吨位": 8.0,
        "载重体积": 25.0,
        "购买日期": "2021-03-10",
        "保险到期日": "2025-03-10",
        "年检到期日": "2025-09-10",
        "状态": "在途",
        "所属司机": "内部司机3"
    },
    {
        "车牌号": "苏D22222",
        "车辆类型": "危险品车",
        "车辆型号": "重汽豪沃",
        "车辆品牌": "中国重汽",
        "载重吨位": 12.0,
        "载重体积": 35.0,
        "购买日期": "2020-08-25",
        "保险到期日": "2025-08-25",
        "年检到期日": "2026-02-25",
        "状态": "空闲",
        "所属司机": "内部司机4"
    },
    {
        "车牌号": "浙E33333",
        "车辆类型": "平板车",
        "车辆型号": "陕汽德龙",
        "车辆品牌": "陕汽重卡",
        "载重吨位": 20.0,
        "载重体积": 50.0,
        "购买日期": "2018-11-30",
        "保险到期日": "2024-11-30",
        "年检到期日": "2025-05-30",
        "状态": "维修",
        "所属司机": "内部司机5"
    }
]
vehicle_records = insert_records("车辆表", vehicles)

# 1.6 员工表
employees = [
    {
        "姓名": "张三",
        "性别": "男",
        "部门": "业务部",
        "职位": "业务经理",
        "手机号": "13800138001",
        "邮箱": "zhangsan@company.com",
        "入职日期": "2020-01-01",
        "状态": "在职"
    },
    {
        "姓名": "李四",
        "性别": "女",
        "部门": "调度部",
        "职位": "调度员",
        "手机号": "13800138002",
        "邮箱": "lisi@company.com",
        "入职日期": "2020-03-15",
        "状态": "在职"
    },
    {
        "姓名": "王五",
        "性别": "男",
        "部门": "财务部",
        "职位": "财务专员",
        "手机号": "13800138003",
        "邮箱": "wangwu@company.com",
        "入职日期": "2019-06-01",
        "状态": "在职"
    },
    {
        "姓名": "赵六",
        "性别": "女",
        "部门": "客服部",
        "职位": "客服专员",
        "手机号": "13800138004",
        "邮箱": "zhaoliu@company.com",
        "入职日期": "2021-02-20",
        "状态": "在职"
    },
    {
        "姓名": "钱七",
        "性别": "男",
        "部门": "管理部",
        "职位": "运营总监",
        "手机号": "13800138005",
        "邮箱": "qianqi@company.com",
        "入职日期": "2018-01-01",
        "状态": "在职"
    }
]
employee_records = insert_records("员工表", employees)

print("\n" + "="*60)
print("基础数据表数据创建完成")
print("="*60)

# 等待一下，确保数据已保存
time.sleep(2)

# ==================== 2. 业务主表 ====================

print("\n" + "="*60)
print("开始创建业务主表数据")
print("="*60)

# 2.1 订单表（需要关联客户和地址）
# 先获取客户和地址的记录ID
customer_ids = [r.get('id') for r in customer_records]
address_ids = [r.get('id') for r in address_records]

# 获取客户名称和地址名称的映射
customer_name_map = {}
for i, customer in enumerate(customers):
    if i < len(customer_records):
        customer_name_map[customer['客户名称']] = customer_records[i].get('id')

address_name_map = {}
for i, address in enumerate(addresses):
    if i < len(address_records):
        address_name_map[address['地址名称']] = address_records[i].get('id')

today = datetime.now()
orders = [
    {
        "客户名称": "上海贸易有限公司",
        "订单日期": (today - timedelta(days=10)).strftime("%Y-%m-%d"),
        "要求提货日期": (today - timedelta(days=8)).strftime("%Y-%m-%d"),
        "要求到达日期": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        "提货联系人": "仓库管理员A",
        "提货电话": "021-11111111",
        "收货联系人": "客户联系人1",
        "收货电话": "0755-44444444",
        "订单状态": "已完成",
        "订单金额": 15000.00,
        "结算状态": "已结算"
    },
    {
        "客户名称": "北京科技有限公司",
        "订单日期": (today - timedelta(days=7)).strftime("%Y-%m-%d"),
        "要求提货日期": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        "要求到达日期": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        "提货联系人": "配送中心管理员",
        "提货电话": "010-22222222",
        "收货联系人": "客户联系人2",
        "收货电话": "0571-55555555",
        "订单状态": "运输中",
        "订单金额": 25000.00,
        "结算状态": "部分结算"
    },
    {
        "客户名称": "广州制造有限公司",
        "订单日期": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
        "要求提货日期": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
        "要求到达日期": today.strftime("%Y-%m-%d"),
        "提货联系人": "仓库管理员B",
        "提货电话": "020-33333333",
        "收货联系人": "客户联系人1",
        "收货电话": "0755-44444444",
        "订单状态": "已到达",
        "订单金额": 18000.00,
        "结算状态": "未结算"
    },
    {
        "客户名称": "深圳电子有限公司",
        "订单日期": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
        "要求提货日期": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
        "要求到达日期": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
        "提货联系人": "仓库管理员C",
        "提货电话": "0512-66666666",
        "收货联系人": "客户联系人2",
        "收货电话": "0571-55555555",
        "订单状态": "已指派",
        "订单金额": 22000.00,
        "结算状态": "未结算"
    },
    {
        "客户名称": "杭州贸易公司",
        "订单日期": today.strftime("%Y-%m-%d"),
        "要求提货日期": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
        "要求到达日期": (today + timedelta(days=4)).strftime("%Y-%m-%d"),
        "提货联系人": "配送中心管理员2",
        "提货电话": "025-77777777",
        "收货联系人": "客户联系人1",
        "收货电话": "0755-44444444",
        "订单状态": "待指派",
        "订单金额": 12000.00,
        "结算状态": "未结算"
    }
]
order_records = insert_records("订单表", orders)

time.sleep(2)

# 2.2 货物明细表（需要关联订单和产品）
order_ids = [r.get('id') for r in order_records]
product_ids = [r.get('id') for r in product_records]

cargo_details = []
for i, order in enumerate(orders):
    if i < len(order_records):
        # 每个订单创建1-3个货物明细
        num_items = random.randint(1, 3)
        for j in range(num_items):
            product_idx = random.randint(0, len(products) - 1)
            product = products[product_idx]
            
            quantity = random.randint(1, 10)
            weight = quantity * product['标准重量']
            volume = quantity * product['标准体积']
            value = random.randint(1000, 5000) * quantity
            
            cargo_detail = {
                "货物名称": f"{product['产品名称']}-批次{i+1}-{j+1}",
                "数量": quantity,
                "单位": product['单位'],
                "重量": round(weight, 2),
                "体积": round(volume, 2),
                "货物价值": value,
                "状态": "已完成" if order['订单状态'] == "已完成" else order['订单状态']
            }
            # 关联订单字段（manyOne关系，传递对象格式）
            if order_records[i].get('id'):
                cargo_detail["关联订单"] = {'id': order_records[i].get('id')}
            # 关联产品字段（manyOne关系，传递对象格式；产品名称是lookup字段，不能直接设置）
            if product_idx < len(product_records) and product_records[product_idx].get('id'):
                cargo_detail["关联产品"] = {'id': product_records[product_idx].get('id')}
            cargo_details.append(cargo_detail)

cargo_detail_records = insert_records("货物明细表", cargo_details)

time.sleep(2)

# 2.3 供应商派车表（需要关联供应商和货物明细）
supplier_ids = [r.get('id') for r in supplier_records]

supplier_dispatches = []
# 只为前min(10, len(cargo_detail_records))个货物明细创建派车记录
num_dispatches = min(10, len(cargo_detail_records))
for i in range(num_dispatches):
    if i < len(cargo_detail_records):
        cargo = cargo_details[i]
        supplier_idx = random.randint(0, len(suppliers) - 1)
        supplier = suppliers[supplier_idx]
        
        dispatch_date = (today - timedelta(days=random.randint(1, 10))).strftime("%Y-%m-%d")
        
        dispatch = {
            "指派类型": random.choice(["自动指派", "手动指派"]),
            "指派时间": dispatch_date,
            "提货费": random.randint(200, 500),
            "送货费": random.randint(300, 800),
            "运费": random.randint(1000, 3000),
            "其他费用": random.randint(0, 500),
            "车牌号": f"供应商车牌{i+1}",
            "司机姓名": f"司机{i+1}",
            "司机电话": f"1380000{i+1:04d}",
            "状态": random.choice(["待提货", "已提货", "运输中", "已到达", "已完成"])
        }
        # 关联供应商字段（manyOne关系，传递对象格式；供应商名称是lookup字段，不能直接设置）
        if supplier_idx < len(supplier_records) and supplier_records[supplier_idx].get('id'):
            dispatch["关联供应商"] = {'id': supplier_records[supplier_idx].get('id')}
        # 关联货物明细字段（manyMany关系，传递数组格式，每个元素是对象）
        if cargo_detail_records[i].get('id'):
            dispatch["关联货物明细"] = [{'id': cargo_detail_records[i].get('id')}]
        supplier_dispatches.append(dispatch)

supplier_dispatch_records = insert_records("供应商派车表", supplier_dispatches)

time.sleep(2)

# 2.4 内部派车表（需要关联车辆和货物明细）
vehicle_ids = [r.get('id') for r in vehicle_records]

internal_dispatches = []
# 为接下来的货物明细创建内部派车（从第10个开始，最多5个）
start_idx = min(10, len(cargo_detail_records))
end_idx = min(start_idx + 5, len(cargo_detail_records))
for i in range(start_idx, end_idx):
    if i < len(cargo_detail_records):
        cargo = cargo_details[i]
        vehicle_idx = random.randint(0, len(vehicles) - 1)
        vehicle = vehicles[vehicle_idx]
        
        dispatch_date = (today - timedelta(days=random.randint(1, 7))).strftime("%Y-%m-%d")
        
        dispatch = {
            "指派时间": dispatch_date,
            "提货费": random.randint(150, 400),
            "送货费": random.randint(250, 600),
            "运费": random.randint(800, 2500),
            "油费": random.randint(200, 600),
            "过路费": random.randint(100, 400),
            "其他费用": random.randint(0, 300),
            "司机": f"内部司机{i+1}",
            "状态": cargo['状态']
        }
        # 关联车辆字段（manyOne关系，传递对象格式；车牌号是lookup字段，不能直接设置）
        if vehicle_idx < len(vehicle_records) and vehicle_records[vehicle_idx].get('id'):
            dispatch["关联车辆"] = {'id': vehicle_records[vehicle_idx].get('id')}
        # 关联货物明细字段（manyMany关系，传递数组格式，每个元素是对象）
        if cargo_detail_records[i].get('id'):
            dispatch["关联货物明细"] = [{'id': cargo_detail_records[i].get('id')}]
        internal_dispatches.append(dispatch)

internal_dispatch_records = insert_records("内部派车表", internal_dispatches)

time.sleep(2)

# 2.5 应收对账单表（需要关联订单）
receivable_bills = []
for i, order in enumerate(orders[:3]):  # 为前3个订单创建应收对账单
    if i < len(order_records):
        bill_date = (today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        invoice_date = (today - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d") if random.random() > 0.3 else None
        
        bill = {
            "客户名称": order['客户名称'],
            "对账日期": bill_date,
            "应收金额": order['订单金额'],
            "已收金额": order['订单金额'] if order['结算状态'] == "已结算" else order['订单金额'] * 0.5 if order['结算状态'] == "部分结算" else 0,
            "结算状态": order['结算状态'],
            "开票状态": "已开票" if invoice_date else "未开票",
            "开票日期": invoice_date,
            "发票号": f"INV{random.randint(100000, 999999)}" if invoice_date else None
        }
        # 关联订单字段（manyOne关系，传递对象格式）
        if order_records[i].get('id'):
            bill["关联订单"] = {'id': order_records[i].get('id')}
        receivable_bills.append(bill)

receivable_bill_records = insert_records("应收对账单表", receivable_bills)

time.sleep(2)

# 2.6 应付对账单表（需要关联供应商派车和供应商）
payable_bills = []
for i, dispatch in enumerate(supplier_dispatches[:3]):  # 为前3个供应商派车创建应付对账单
    if i < len(supplier_dispatch_records):
        supplier = suppliers[i % len(suppliers)]
        bill_date = (today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        
        total_amount = dispatch['提货费'] + dispatch['送货费'] + dispatch['运费'] + dispatch['其他费用']
        paid_amount = total_amount if random.random() > 0.5 else total_amount * 0.5
        
        bill = {
            "供应商名称": supplier['供应商名称'],
            "对账日期": bill_date,
            "应付金额": total_amount,
            "已付金额": paid_amount,
            "结算状态": "已结算" if paid_amount >= total_amount else "部分结算" if paid_amount > 0 else "未结算",
            "开票状态": "已开票" if random.random() > 0.3 else "未开票",
            "开票日期": bill_date if random.random() > 0.3 else None,
            "发票号": f"SUP{random.randint(100000, 999999)}" if random.random() > 0.3 else None,
            "结算方式": supplier['结算方式']
        }
        # 关联字段（manyOne关系，传递对象格式）
        if i < len(supplier_dispatch_records) and supplier_dispatch_records[i].get('id'):
            bill["关联供应商派车"] = {'id': supplier_dispatch_records[i].get('id')}
        if i % len(supplier_records) < len(supplier_records) and supplier_records[i % len(supplier_records)].get('id'):
            bill["关联供应商"] = {'id': supplier_records[i % len(supplier_records)].get('id')}
        payable_bills.append(bill)

payable_bill_records = insert_records("应付对账单表", payable_bills)

print("\n" + "="*60)
print("所有测试数据创建完成！")
print("="*60)
print(f"\n创建统计：")
print(f"  客户表: {len(customer_records)} 条")
print(f"  供应商表: {len(supplier_records)} 条")
print(f"  地址库表: {len(address_records)} 条")
print(f"  产品表: {len(product_records)} 条")
print(f"  车辆表: {len(vehicle_records)} 条")
print(f"  员工表: {len(employee_records)} 条")
print(f"  订单表: {len(order_records)} 条")
print(f"  货物明细表: {len(cargo_detail_records)} 条")
print(f"  供应商派车表: {len(supplier_dispatch_records)} 条")
print(f"  内部派车表: {len(internal_dispatch_records)} 条")
print(f"  应收对账单表: {len(receivable_bill_records)} 条")
print(f"  应付对账单表: {len(payable_bill_records)} 条")
