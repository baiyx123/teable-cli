# Teable CLI 智能管道操作设计

## 核心思想：自动检测，零参数配置

### 设计原则
1. **零配置**：不需要额外的参数，自动检测管道模式
2. **智能识别**：自动判断输入输出格式
3. **向后兼容**：现有命令完全不变
4. **渐进增强**：管道功能是自动启用的增强特性

## 智能检测机制

### 1. 自动检测管道输入
```python
def is_pipe_input() -> bool:
    """检测是否有管道输入"""
    return not sys.stdin.isatty()

def has_pipe_input() -> bool:
    """检测标准输入是否有数据"""
    if not is_pipe_input():
        return False
    
    # 检查是否有数据可读
    import select
    return bool(select.select([sys.stdin], [], [], 0.0)[0])
```

### 2. 自动检测管道输出
```python
def is_pipe_output() -> bool:
    """检测是否输出到管道"""
    return not sys.stdout.isatty()
```

### 3. 智能命令行为

#### show 命令
```bash
# 普通模式（输出到终端）- 显示表格
t show -w 状态=待处理

# 管道模式（输出到管道）- 自动输出简洁格式
t show -w 状态=待处理 | grep "重要" | t update 状态=紧急
```

#### update 命令
```bash
# 普通模式（无管道输入）- 传统用法
t update rec123 状态=处理中

# 管道模式（有管道输入）- 自动接收记录列表
t show -w 状态=待处理 | t update 状态=处理中
```

## 简化后的使用方式

### 基础管道操作

```bash
# 查询并更新 - 超级简单！
t show -w 状态=待处理 | t update 状态=处理中

# 复杂条件查询+更新
t show -w 创建时间>2024-01-01 优先级=高 | t update 状态=紧急 处理人=张三

# 查询并删除
t show -w 状态=已取消 | t delete

# 查询并复制数据
t show -w 状态=已完成 | t insert --to-table 备份表
```

### 与传统Unix命令结合

```bash
# 只处理前10条
t show -w 状态=新建 | head -10 | t update 状态=已分配

# 筛选特定客户
t show -w 状态=待处理 | grep "客户=张三" | t update 状态=处理中

# 保存到文件
t show -w 状态=异常 > exceptions.txt
cat exceptions.txt | t update 状态=需要审核
```

## 技术实现

### 1. 智能命令分发

```python
class SmartCommandHandler:
    """智能命令处理器"""
    
    def handle_show(self, client, session, args):
        """处理show命令"""
        if is_pipe_output():
            # 管道输出模式：输出简洁格式
            return self._show_pipe_mode(client, session, args)
        else:
            # 终端输出模式：显示表格
            return self._show_table_mode(client, session, args)
    
    def handle_update(self, client, session, args):
        """处理update命令"""
        if has_pipe_input():
            # 管道输入模式：从管道读取记录
            return self._update_pipe_mode(client, session, args)
        else:
            # 传统模式：使用参数
            return self._update_normal_mode(client, session, args)
```

### 2. 管道输出格式

```python
def format_pipe_output(record: Dict[str, Any]) -> str:
    """格式化管道输出"""
    record_id = record.get('id', '')
    fields = record.get('fields', {})
    
    if not fields:
        return record_id
    
    # 简单的键值对格式
    field_parts = []
    for field_name, value in fields.items():
        field_parts.append(f"{field_name}={value}")
    
    return f"{record_id} {' '.join(field_parts)}"
```

### 3. 管道输入解析

```python
def parse_pipe_input(line: str) -> Dict[str, Any]:
    """解析管道输入"""
    line = line.strip()
    if not line:
        return None
    
    parts = line.split(' ', 1)
    record_id = parts[0]
    
    record = {
        'id': record_id,
        'fields': {}
    }
    
    if len(parts) > 1:
        # 解析字段
        field_part = parts[1]
        for field_pair in field_part.split(' '):
            if '=' in field_pair:
                field_name, field_value = field_pair.split('=', 1)
                record['fields'][field_name] = field_value
    
    return record
```

## 具体命令实现

### show 命令的智能实现

```python
def show_current_table(client, session, args):
    """智能show命令"""
    
    # 检测输出模式
    if is_pipe_output():
        # 管道模式：流式输出简洁格式
        return show_pipe_mode(client, session, args)
    else:
        # 终端模式：显示表格
        return show_table_mode(client, session, args)

def show_pipe_mode(client, session, args):
    """管道模式的show命令"""
    # 执行查询（复用现有逻辑）
    records = query_records(client, session, args)
    
    # 流式输出
    for record in records:
        output_line = format_pipe_output(record)
        print(output_line, flush=True)
    
    return 0
```

### update 命令的智能实现

```python
def update_record(client, session, args):
    """智能update命令"""
    
    # 检测输入模式
    if has_pipe_input():
        # 管道模式：从管道读取记录
        return update_pipe_mode(client, session, args)
    else:
        # 传统模式：使用参数
        return update_normal_mode(client, session, args)

def update_pipe_mode(client, session, args):
    """管道模式的update命令"""
    # 解析更新字段
    update_fields = parse_update_fields(args)
    
    # 从管道读取记录
    records = []
    for line in sys.stdin:
        record = parse_pipe_input(line)
        if record:
            records.append(record)
    
    if not records:
        print("没有接收到管道数据")
        return 1
    
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
```

## 优势

1. **零学习成本**：用户不需要学习新参数
2. **直觉操作**：管道操作符合Unix哲学
3. **完美兼容**：现有脚本完全不受影响
4. **智能适应**：自动选择最佳的工作模式
5. **简洁高效**：没有多余的参数和配置

## 使用场景

### 场景1：日常数据处理
```bash
# 每天处理新订单
t show -w 状态=新建 | t update 状态=处理中 处理时间=$(date +%Y-%m-%d)
```

### 场景2：数据清洗
```bash
# 查找并修复异常数据
t show -w 状态=异常 | grep "金额=0" | t update 状态=待检查 备注="金额为零"
```

### 场景3：批量操作
```bash
# 批量分配任务
t show -w 状态=待分配 优先级=高 | head -20 | t update 状态=已分配 负责人=张三
```

### 场景4：数据迁移
```bash
# 复制完成的数据到备份表
t show -w 状态=已完成 完成时间>2024-01-01 | t insert --to-table 历史订单表
```

这个智能设计让用户可以零配置地使用管道操作，同时保持与现有命令的完全兼容性。