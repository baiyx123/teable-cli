#!/usr/bin/env python3
"""
创建大型数据集用于测试流式管道操作
"""

import subprocess
import sys

def create_large_dataset():
    """创建200条测试记录用于流式管道测试"""
    print("开始创建大型数据集（200条记录）...")
    
    companies = [
        "阿里巴巴", "腾讯科技", "百度在线", "字节跳动", "美团点评", 
        "滴滴出行", "小米科技", "华为技术", "网易公司", "新浪微博",
        "搜狐公司", "360安全", "京东集团", "拼多多", "快手科技",
        "今日头条", "携程旅行", "去哪儿", "爱奇艺", "优酷视频",
        "腾讯视频", "网易云音乐", "酷狗音乐", "QQ音乐", "喜马拉雅",
        "得到APP", "知乎", "豆瓣", "简书", "CSDN",
        "掘金", "SegmentFault", "开源中国", "InfoQ", "极客时间",
        "慕课网", "网易云课堂", "腾讯课堂", "百度传课", "淘宝教育"
    ]
    
    contacts = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "王十二"]
    
    customer_types = ["企业客户", "个人客户", "政府客户", "教育机构"]
    credit_levels = ["优秀", "良好", "一般", "较差"]
    
    success_count = 0
    total_records = 200
    
    for i in range(total_records):
        company = companies[i % len(companies)] + f"分部{i+1}"
        code = str(200 + i)
        contact = contacts[i % len(contacts)] + str(i % 10)
        phone = f"138{10000000 + i:08d}"
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
            
            if i % 20 == 0:
                print(f"创建记录 {i+1}/{total_records}: {company}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
            else:
                print(f"❌ 失败: {company} - {result.stderr}")
                
        except Exception as e:
            print(f"❌ 异常: {company} - {str(e)}")
    
    print(f"\n大型数据集创建完成！成功: {success_count}/{total_records}")
    return success_count

if __name__ == "__main__":
    create_large_dataset()