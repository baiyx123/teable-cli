# Teable CLI 管道操作架构设计

## 设计目标

构建一个强大的管道操作系统，支持命令之间的数据流转，实现类似 SQL 的复杂操作：

- **关联查询**：`show` → `show`（引用前结果做条件）
- **INSERT SELECT**：`show` → `insert`（查询结果插入新表）
- **MERGE UPDATE**：`show` → `update`（查询结果批量更新）
- **数据转换**：`show` → `show`（数据筛选、转换）

## 核心概念

### 1. 数据流格式
所有命令统一支持以下数据交换格式：

#### JSON 格式（主要格式）
```json
{
  "type": "records",
  "table_id": "tblxxx",
  "table_name": "订单表",
  "records": [
    {
      "id": "rec123",
      "fields": {
        "订单号": "ORD001",
        "状态": "待处理",
        "客户ID": "cus456"
      }
    }
  ],
  "total": 100
}
```

#### 简化格式
- **IDs 模式**：只输出记录ID列表
- **Fields 模式**：只输出字段数据
- **Table 模式**：表格展示（当前默认）

### 2. 管道操作类型

#### Type A: 记录流操作
- `show` → `update`：批量更新查询结果
- `show` → `delete`：批量删除查询结果
- `show` → `show`：关联查询、数据筛选

#### Type B: 数据转换操作
- `show` → `insert`：INSERT SELECT 操作
- `show` → `show`：数据转换、字段映射

#### Type C: 控制流操作
- `show` → 文件 → `update`：离线处理
- `show` → 其他命令：数据分析、统计

## 命令增强设计

### 1. show 命令增强

```bash
# 输出格式选项
t show --output json          # JSON格式输出
t show --output ids           # 仅记录ID
t show --output fields        # 仅字段数据
t show --output table         # 表格格式（默认）

# 管道支持选项
t show --pipe                 # 启用管道输出模式
t show --fields 订单号,状态    # 指定输出字段
t show --no-header            # 不包含表头信息
```

**输出示例**：
```bash
# JSON管道输出
t show -w 状态=待处理 --output json --pipe
{"type":"records","table_id":"tblxxx","table_name":"订单表","records":[{"id":"rec123","fields":{"订单号":"ORD001","状态":"待处理"}}]}

# IDs管道输出
t show -w 状态=待处理 --output ids --pipe
rec123
rec124
rec125
```

### 2. update 命令增强

```bash
# 管道输入支持
t show -w 状态=待处理 --output ids | t update --from-pipe 状态=处理中

# JSON数据输入
t show -w 状态=待处理 --output json | t update --from-json 状态=处理中 处理人=张三

# 字段映射
t show --output json | t update --from-json --map-fields "旧字段=新字段"
```

### 3. insert 命令增强

```bash
# INSERT SELECT 操作
t show -w 状态=已完成 --output json | t insert --from-pipe --target-table 完成订单表

# 字段映射插入
t show --output json | t insert --from-pipe --target-table 备份表 --map-fields "订单号=备份订单号"
```

### 4. delete 命令增强

```bash
# 批量删除查询结果
t show -w 状态=已取消 --output ids | t delete --from-pipe

# 安全模式
t show -w 状态=已取消 --output ids | t delete --from-pipe --confirm
```

## 高级管道操作

### 1. 关联查询（类似 SQL JOIN）

```bash
# 查询客户表，获取VIP客户ID
t show -w 客户等级=VIP --output ids | \
# 查询订单表，找到这些客户的订单
xargs -I {} t show -w 客户ID={} --output json | \
# 更新这些订单的优先级
t update --from-json 优先级=高
```

### 2. 复杂数据处理

```bash
# 查询待处理订单
t show -w 状态=待处理 --output json | \
# 数据转换（添加处理时间）
jq '.records[].fields.处理时间 = "2024-01-01"' | \
# 插入到处理记录表
t insert --from-json --target-table 处理记录表
```

### 3. 批量操作工作流

```bash
# 1. 查询需要处理的订单
t show -w 状态=新建 --output ids > new_orders.txt

# 2. 分配给不同处理人
split -l 10 new_orders.txt order_batch_

# 3. 并行处理
for batch in order_batch_*; do
    cat $batch | t update --from-pipe 状态=处理中 处理人=张三 &
done
```

## 技术实现架构

### 1. 数据序列化层
```python
class PipeData:
    """管道数据统一格式"""
    def __init__(self, data_type, table_info, records):
        self.type = data_type
        self.table_id = table_info.get('id')
        self.table_name = table_info.get('name')
        self.records = records
        self.total = len(records)
    
    def to_json(self):
        return json.dumps({
            "type": self.type,
            "table_id": self.table_id,
            "table_name": self.table_name,
            "records": self.records,
            "total": self.total
        })
    
    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(data['type'], data, data['records'])
```

### 2. 管道输入处理器
```python
class PipeInputHandler:
    """处理管道输入"""
    
    def read_ids(self):
        """从标准输入读取记录ID列表"""
        ids = []
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith('#'):
                ids.append(line)
        return ids
    
    def read_json(self):
        """从标准输入读取JSON数据"""
        json_str = sys.stdin.read()
        return PipeData.from_json(json_str)
    
    def read_records(self):
        """从标准输入读取记录数据"""
        # 支持多种格式
        first_line = sys.stdin.readline().strip()
        if first_line.startswith('{'):
            # JSON格式
            json_str = first_line + sys.stdin.read()
            return self.read_json_from_string(json_str)
        else:
            # ID列表格式
            ids = [first_line] if first_line else []
            for line in sys.stdin:
                line = line.strip()
                if line:
                    ids.append(line)
            return ids
```

### 3. 管道输出处理器
```python
class PipeOutputHandler:
    """处理管道输出"""
    
    def output_ids(self, records):
        """输出记录ID列表"""
        for record in records:
            print(record.get('id', ''))
    
    def output_json(self, pipe_data):
        """输出JSON格式"""
        print(pipe_data.to_json())
    
    def output_table(self, records, fields):
        """输出表格格式（现有功能）"""
        # 保持现有的表格输出逻辑
        pass
```

## 命令处理流程

### show 命令流程
```
1. 解析参数（包括管道相关参数）
2. 执行查询
3. 根据输出格式处理结果：
   - table: 显示表格
   - ids: 输出ID列表
   - json: 输出JSON数据
   - pipe: 启用管道模式
4. 输出到相应目标（终端/管道）
```

### update 命令流程
```
1. 检测是否有管道输入
2. 解析参数：
   - 如果有 --from-pipe：从标准输入读取数据
   - 如果有 --from-json：解析JSON数据
   - 否则：使用传统参数模式
3. 执行更新操作
4. 输出结果
```

### insert 命令流程
```
1. 检测是否有管道输入
2. 解析目标表格和字段映射
3. 转换数据格式
4. 批量插入记录
5. 输出结果
```

## 错误处理和安全性

### 1. 数据验证
- 验证记录ID格式
- 检查字段存在性
- 验证数据类型

### 2. 错误恢复
- 部分失败的处理
- 事务性操作
- 回滚机制

### 3. 安全考虑
- 批量操作限制
- 确认机制
- 日志记录

## 性能优化

### 1. 批量处理
- 批量更新记录
- 分批处理大数据
- 进度显示

### 2. 内存管理
- 流式处理大数据
- 分页加载
- 垃圾回收

### 3. 并发支持
- 异步处理
- 并行操作
- 连接池

## 使用场景示例

### 场景1：数据迁移
```bash
# 从旧表查询数据
t show --table 旧订单表 --output json | \
# 转换数据格式
jq '.records[] | {fields: {订单号: .fields.编号, 状态: .fields.旧状态}}' | \
# 插入到新表
t insert --from-json --target-table 新订单表
```

### 场景2：数据清洗
```bash
# 查询异常数据
t show -w 状态=异常 --output json | \
# 数据清洗
jq '.records[] | select(.fields.金额 > 0)' | \
# 更新清洗后的状态
t update --from-json 状态=已清洗
```

### 场景3：批量工作流
```bash
# 创建批量处理脚本
cat << 'EOF' > process_orders.sh
#!/bin/bash
t show -w 状态=待处理 --output ids | \
while read order_id; do
    echo "处理订单: $order_id"
    t update $order_id 状态=处理中 处理时间=$(date +%Y-%m-%d)
done
EOF

chmod +x process_orders.sh
./process_orders.sh
```

这个架构设计提供了一个强大、灵活且安全的管道操作系统，可以支持复杂的数据处理工作流。