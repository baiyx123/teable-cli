# Teable CLI 简单管道操作设计

## 设计原则

1. **简单直观**：不区分复杂的流格式，统一使用简单的数据传递
2. **向后兼容**：现有命令完全兼容，管道功能是可选增强
3. **渐进式**：从基础功能开始，逐步扩展
4. **实用为主**：解决实际业务场景，避免过度设计

## 核心概念：简单数据传递

### 数据格式统一
所有命令都支持一种简单的数据交换格式：

```
记录ID 字段1 字段2 字段3 ...
```

或者纯ID列表：
```
rec123
rec124
rec125
```

### 基本管道操作

#### 1. show → update（最常用）
```bash
# 查询一批记录，然后更新它们
t show -w 状态=待处理 | t update 状态=处理中

# 复杂条件
t show -w 创建时间>2024-01-01 优先级=高 | t update 状态=紧急 处理人=张三
```

#### 2. show → insert（数据复制）
```bash
# 查询数据，插入到新表（类似INSERT SELECT）
t show -w 状态=已完成 | t insert --to-table 完成订单备份表
```

#### 3. show → delete（批量删除）
```bash
# 查询要删除的记录，然后删除
t show -w 状态=已取消 | t delete
```

## 具体实现方案

### 1. show 命令增强

添加 `--pipe-output` 参数，让输出可以被后续命令使用：

```bash
# 默认表格输出（现有功能）
t show -w 状态=待处理

# 管道输出（新功能）
t show -w 状态=待处理 --pipe-output
```

输出格式：
```
rec123 订单号=ORD001 状态=待处理 客户=张三
rec124 订单号=ORD002 状态=待处理 客户=李四
```

或者只输出ID（更简洁）：
```
rec123
rec124
```

### 2. update 命令增强

添加 `--from-pipe` 参数，从管道读取要更新的记录：

```bash
# 传统方式（完全兼容）
t update rec123 状态=处理中

# 管道方式（新功能）
t show -w 状态=待处理 --pipe-output | t update --from-pipe 状态=处理中
```

### 3. insert 命令增强

```bash
# 从管道接收数据并插入
t show -w 状态=已完成 --pipe-output | t insert --from-pipe --to-table 备份表
```

### 4. delete 命令增强

```bash
# 批量删除管道传来的记录
t show -w 状态=已取消 --pipe-output | t delete --from-pipe
```

## 技术实现

### 管道数据格式

采用最简单的格式：每行一条记录，字段用空格分隔

```
记录ID [字段1=值1] [字段2=值2] ...
```

示例：
```
rec123 订单号=ORD001 状态=待处理
rec124 订单号=ORD002 状态=待处理
```

### 核心代码结构

#### 管道输出处理器
```python
class SimplePipeOutput:
    def __init__(self, output_format='full'):
        self.output_format = output_format  # 'full' or 'ids'
    
    def output_record(self, record, fields=None):
        """输出一条记录"""
        record_id = record.get('id', '')
        
        if self.output_format == 'ids':
            print(record_id, flush=True)
        else:
            # 完整格式：ID + 字段
            field_parts = []
            record_fields = record.get('fields', {})
            
            if fields:
                # 只输出指定字段
                for field_name in fields:
                    if field_name in record_fields:
                        value = record_fields[field_name]
                        field_parts.append(f"{field_name}={value}")
            else:
                # 输出所有字段
                for field_name, value in record_fields.items():
                    field_parts.append(f"{field_name}={value}")
            
            output_line = f"{record_id} {' '.join(field_parts)}"
            print(output_line, flush=True)
```

#### 管道输入处理器
```python
class SimplePipeInput:
    def read_records(self, input_stream=None):
        """从输入流读取记录"""
        if input_stream is None:
            input_stream = sys.stdin
        
        records = []
        for line in input_stream:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split(' ', 1)
            record_id = parts[0]
            
            record = {
                'id': record_id,
                'fields': {}
            }
            
            # 解析字段（如果有）
            if len(parts) > 1:
                field_part = parts[1]
                for field_pair in field_part.split(' '):
                    if '=' in field_pair:
                        field_name, field_value = field_pair.split('=', 1)
                        record['fields'][field_name] = field_value
            
            records.append(record)
        
        return records
```

### 命令集成

#### show 命令修改
```python
def show_current_table(client, session, args):
    # 解析参数
    pipe_output = '--pipe-output' in args
    output_fields = None
    
    if pipe_output:
        # 管道输出模式
        output_handler = SimplePipeOutput(output_format='full')
        
        # 流式查询和处理
        for record in query_records_streaming(client, table_id, filter_conditions):
            output_handler.output_record(record, output_fields)
        
        return 0
    
    # 原有逻辑保持不变...
```

#### update 命令修改
```python
def update_record(client, session, args):
    # 检测管道输入
    from_pipe = '--from-pipe' in args
    
    if from_pipe:
        # 管道输入模式
        input_handler = SimplePipeInput()
        records = input_handler.read_records()
        
        # 解析更新字段
        update_fields = parse_update_fields(args)
        
        # 批量更新
        updates = []
        for record in records:
            updates.append({
                'record_id': record['id'],
                'fields_data': update_fields
            })
        
        result = client.batch_update_records(table_id, updates)
        print(f"✅ 成功更新 {len(records)} 条记录")
        return 0
    
    # 原有逻辑保持不变...
```

## 使用示例

### 基础管道操作

```bash
# 1. 简单查询+更新
t show -w 状态=待处理 --pipe-output | t update --from-pipe 状态=处理中

# 2. 复杂条件查询+更新
t show -w 创建时间>2024-01-01 优先级=高 --pipe-output | \
t update --from-pipe 状态=紧急 处理人=张三

# 3. 查询+删除
t show -w 状态=已取消 --pipe-output | t delete --from-pipe

# 4. 数据复制（INSERT SELECT）
t show -w 状态=已完成 --pipe-output | \
t insert --from-pipe --to-table 完成订单备份表
```

### 高级组合

```bash
# 多步处理
t show -w 状态=新建 --pipe-output | \
head -10 | \
t update --from-pipe 状态=已分配 分配时间=$(date +%Y-%m-%d)

# 保存到文件处理
t show -w 状态=待审核 --pipe-output > pending.txt
cat pending.txt | t update --from-pipe 状态=已审核

# 实时处理新数据
while true; do
    t show -w 状态=新建 --pipe-output --limit 100 | \
    t update --from-pipe 状态=已分配
    sleep 60
done
```

## 优势

1. **简单易学**：格式直观，一看就懂
2. **兼容性好**：不影响现有命令使用
3. **灵活组合**：可以和其他Unix命令组合
4. **性能合理**：支持流式处理，内存占用小
5. **调试方便**：输出格式人类可读

## 实现优先级

1. **Phase 1**：show + update 管道操作
2. **Phase 2**：show + delete 管道操作  
3. **Phase 3**：show + insert 管道操作
4. **Phase 4**：错误处理和进度显示
5. **Phase 5**：性能优化和批量处理

这个设计保持了简单性，同时提供了强大的管道操作能力，让用户能够轻松实现复杂的数据处理工作流。