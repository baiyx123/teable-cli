#!/usr/bin/env python3
"""
批量创建测试数据的脚本
"""

import subprocess
import sys

# 测试数据模板
test_companies = [
    ("百度在线", "102", "李彦宏", "13800100102", "企业客户", "优秀"),
    ("字节跳动", "103", "张一鸣", "13800100103", "企业客户", "优秀"),
    ("美团点评", "104", "王兴", "13800100104", "企业客户", "良好"),
    ("滴滴出行", "105", "程维", "13800100105", "企业客户", "良好"),
    ("小米科技", "106", "雷军", "13800100106", "企业客户", "优秀"),
    ("华为技术", "107", "任正非", "13800100107", "企业客户", "优秀"),
    ("网易公司", "108", "丁磊", "13800100108", "企业客户", "良好"),
    ("新浪微博", "109", "曹国伟", "13800100109", "企业客户", "一般"),
    ("搜狐公司", "110", "张朝阳", "13800100110", "企业客户", "一般"),
    ("360安全", "111", "周鸿祎", "13800100111", "企业客户", "良好"),
]

def create_test_data():
    """批量创建测试数据"""
    print("开始批量创建测试数据...")
    
    success_count = 0
    for i, (company, code, contact, phone, ctype, credit) in enumerate(test_companies):
        try:
            # 构建命令
            cmd = [
                "t", "insert",
                f"客户名称={company}",
                f"客户编号={code}",
                f"联系人={contact}",
                f"联系电话={phone}",
                f"客户类型={ctype}",
                f"信用等级={credit}"
            ]
            
            print(f"创建记录 {i+1}/{len(test_companies)}: {company}")
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                success_count += 1
                print(f"✅ 成功: {company}")
            else:
                print(f"❌ 失败: {company} - {result.stderr}")
                
        except Exception as e:
            print(f"❌ 异常: {company} - {str(e)}")
    
    print(f"\n批量创建完成！成功: {success_count}/{len(test_companies)}")
    return success_count

if __name__ == "__main__":
    create_test_data()