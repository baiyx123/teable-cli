#!/usr/bin/env python3
"""
创建更多测试数据用于真正的流式管道测试
"""

import subprocess
import sys

def create_more_test_data():
    """创建500条测试记录用于真正的流式测试"""
    print("开始创建更多测试数据（500条记录）...")
    
    companies = [
        "阿里巴巴", "腾讯科技", "百度在线", "字节跳动", "美团点评", 
        "滴滴出行", "小米科技", "华为技术", "网易公司", "新浪微博",
        "搜狐公司", "360安全", "京东集团", "拼多多", "快手科技",
        "今日头条", "携程旅行", "去哪儿", "爱奇艺", "优酷视频"
    ]
    
    contacts = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "王十二"]
    
    customer_types = ["企业客户", "个人客户", "政府客户", "教育机构"]
    credit_levels = ["优秀", "良好", "一般", "较差"]
    
    success_count = 0
    total_records = 500
    
    for i in range(total_records):
        company = companies[i % len(companies)] + f"第{i+1}分部"
        code = str(1000 + i)
        contact = contacts[i % len(contacts)] + str(i % 10)
        phone = f"139{10000000 + i:08d}"
        ctype = customer_types[i % len(customer_types)]
        credit = credit_levels[i % len(credit_levels)]
        
        try:
            cmd = [
                "t", "insert",
                f"客户名称={company}",
                f"客户编号={code}",
                f"联系人={contact}",
                f"联系电话={phone}",
                f"客户类型={ctype}",
                f"信用等级={credit}"
            ]
            
            if i % 50 == 0:
                print(f"创建记录 {i+1}/{total_records}: {company}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
            else:
                if i % 50 == 0:  # 只在每50条时显示错误，避免刷屏
                    print(f"❌ 失败: {company} - {result.stderr}")
                
        except Exception as e:
            if i % 50 == 0:  # 只在每50条时显示错误
                print(f"❌ 异常: {company} - {str(e)}")
    
    print(f"\n更多测试数据创建完成！成功: {success_count}/{total_records}")
    return success_count

if __name__ == "__main__":
    create_more_test_data()