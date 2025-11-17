# Teable CLI 流式管道操作设计

## 核心挑战：大数据量处理

### 问题分析
- 内存限制：不能一次性加载所有数据到内存
- 性能要求：需要实时处理，不能长时间阻塞
- 网络限制：API调用需要合理分批
- 用户体验：需要显示进度和状态

## 流式处理架构设计

### 1. 数据流模型

```
数据源 → 缓冲区 → 处理器 → 输出流
   ↓        ↓        ↓        ↓
分页查询 → 批次处理 → 实时输出 → 管道传输
```

### 2. 核心设计原则

#### 2.1 分页流式查询
```python
class StreamingRecordReader:
    """流式记录读取器"""
    
    def __init__(self, client, table_id, page_size=100):
        self.client = client
        self.table_id = table_id
        self.page_size = page_size
        self.current_page = 0
        self.total_records = 0
        self.buffer = []
    
    def __iter__(self):
        return self
    
    def __next__(self):
        # 如果缓冲区为空，获取下一页
        if not self.buffer:
            self._fetch_next_page()
        
        # 如果仍然没有数据，结束迭代
        if not self.buffer:
            raise StopIteration
        
        # 返回一条记录
        return self.buffer.pop(0)
    
    def _fetch_next_page(self):
        """获取下一页数据"""
        skip = self.current_page * self.page_size
        response = self.client.get_records(
            self.table_id,
            skip=skip,
            take=self.page_size
        )
        
        records = response.get('records', [])
        self.buffer.extend(records)
        self.total_records = response.get('total', 0)
        self.current_page += 1
```

#### 2.2 批次处理机制
```python
class BatchProcessor:
    """批次处理器"""
    
    def __init__(self, batch_size=50, progress_callback=None):
        self.batch_size = batch_size
        self.progress_callback = progress_callback
        self.processed_count = 0
    
    def process_stream(self, record_stream, processor_func):
        """流式处理记录"""
        batch = []
        
        for record in record_stream:
            batch.append(record)
            
            # 当批次满时，处理并输出
            if len(batch) >= self.batch_size:
                self._process_batch(batch, processor_func)
                batch = []
        
        # 处理剩余记录
        if batch:
            self._process_batch(batch, processor_func)
    
    def _process_batch(self, batch, processor_func):
        """处理一批记录"""
        results = processor_func(batch)
        
        # 实时输出结果
        for result in results:
            yield result
        
        self.processed_count += len(batch)
        
        # 进度回调
        if self.progress_callback:
            self.progress_callback(self.processed_count)
```

#### 2.3 实时输出机制
```python
class StreamingOutput:
    """流式输出处理器"""
    
    def __init__(self, output_format='json'):
        self.output_format = output_format
        self.record_count = 0
    
    def output_record(self, record):
        """输出单条记录"""
        if self.output_format == 'json':
            print(json.dumps(record), flush=True)
        elif self.output_format == 'id':
            print(record.get('id', ''), flush=True)
        
        self.record_count += 1
        
        # 每1000条记录显示进度
        if self.record_count % 1000 == 0:
            self._show_progress()
    
    def _show_progress(self):
        """显示处理进度"""
        print(f"# 已处理 {self.record_count} 条记录", file=sys.stderr, flush=True)
```

### 3. 管道数据协议

#### 3.1 流式JSON协议
```json
{"type":"record_start","table_id":"tblxxx","table_name":"订单表"}
{"id":"rec123","fields":{"订单号":"ORD001","状态":"待处理"}}
{"id":"rec124","fields":{"订单号":"ORD002","状态":"待处理"}}
{"id":"rec125","fields":{"订单号":"ORD003","状态":"待处理"}}
{"type":"record_end","total":3}
```

#### 3.2 纯ID流协议
```
rec123
rec124
rec125
```

#### 3.3 批量JSON协议
```json
{"type":"batch_start","size":100}
{"records":[{"id":"rec123","fields":{...}},{"id":"rec124","fields":{...}}]}
{"type":"batch_end","processed":100}
```

### 4. 命令流式处理设计

#### 4.1 show 命令流式输出
```bash
# 流式JSON输出
t show -w 状态=待处理 --stream --output json-stream

# 流式ID输出
t show -w 状态=待处理 --stream --output id-stream

# 带进度显示
t show -w 状态=待处理 --stream --output json-stream --progress
```

实现逻辑：
```python
def show_streaming(client, session, args):
    """流式显示命令"""
    # 解析参数
    output_format = get_output_format(args)
    show_progress = '--progress' in args
    
    # 创建流式读取器
    reader = StreamingRecordReader(client, table_id, page_size=100)
    
    # 创建批次处理器
    processor = BatchProcessor(batch_size=50, progress_callback=show_progress_status)
    
    # 创建输出处理器
    output = StreamingOutput(output_format)
    
    # 输出开始标记
    if output_format == 'json-stream':
        print('{"type":"record_start"}', flush=True)
    
    # 流式处理
    def process_batch(batch):
        for record in batch:
            output.output_record(record)
        return batch
    
    processor.process_stream(reader, process_batch)
    
    # 输出结束标记
    if output_format == 'json-stream':
        print(f'{{"type":"record_end","total":{output.record_count}}}', flush=True)
```

#### 4.2 update 命令流式输入
```bash
# 从管道接收ID并更新
t show -w 状态=待处理 --stream --output id-stream | \
t update --stream-input --set "状态=处理中"

# 从JSON流接收并更新
t show -w 状态=待处理 --stream --output json-stream | \
t update --stream-input --set "状态=处理中" --json-format
```

实现逻辑：
```python
def update_streaming(client, session, args):
    """流式更新命令"""
    # 解析更新字段
    update_fields = parse_update_fields(args)
    
    # 检测输入格式
    input_format = get_input_format(args)  # 'id-stream' or 'json-stream'
    
    # 创建批次处理器
    processor = BatchProcessor(batch_size=50)
    
    # 流式读取输入
    if input_format == 'id-stream':
        # ID流式输入
        def process_id_batch(id_batch):
            updates = []
            for record_id in id_batch:
                updates.append({
                    'record_id': record_id,
                    'fields_data': update_fields
                })
            
            # 批量更新
            result = client.batch_update_records(table_id, updates)
            return result.get('records', [])
        
        # 从标准输入读取ID流
        id_stream = read_id_stream(sys.stdin)
        processor.process_stream(id_stream, process_id_batch)
        
    elif input_format == 'json-stream':
        # JSON流式输入
        def process_json_batch(record_batch):
            updates = []
            for record in record_batch:
                updates.append({
                    'record_id': record['id'],
                    'fields_data': update_fields
                })
            
            # 批量更新
            result = client.batch_update_records(table_id, updates)
            return result.get('records', [])
        
        # 从标准输入读取JSON流
        json_stream = read_json_stream(sys.stdin)
        processor.process_stream(json_stream, process_json_batch)
```

### 5. 流式读取器实现

#### 5.1 ID流读取器
```python
def read_id_stream(input_stream):
    """从输入流读取ID"""
    for line in input_stream:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('{'):
            yield line

def read_json_stream(input_stream):
    """从输入流读取JSON记录"""
    for line in input_stream:
        line = line.strip()
        if line.startswith('{"id":'):
            try:
                record = json.loads(line)
                yield record
            except json.JSONDecodeError:
                continue
```

#### 5.2 分页查询流
```python
class StreamingQuery:
    """流式查询器"""
    
    def __init__(self, client, table_id, filter_conditions=None, page_size=100):
        self.client = client
        self.table_id = table_id
        self.filter_conditions = filter_conditions or {}
        self.page_size = page_size
        self.current_page = 0
        self.total_fetched = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        # 实现分页查询逻辑
        while True:
            if self._need_fetch():
                self._fetch_page()
            
            if self._has_buffered():
                return self._get_next()
            
            if not self._has_more():
                raise StopIteration
    
    def _fetch_page(self):
        """获取一页数据"""
        skip = self.current_page * self.page_size
        
        # 构建查询参数
        query_params = {
            'skip': skip,
            'take': self.page_size
        }
        
        # 添加过滤条件
        if self.filter_conditions:
            query_params['filter'] = json.dumps(self.filter_conditions)
        
        # 执行查询
        response = self.client.get_records(self.table_id, **query_params)
        
        records = response.get('records', [])
        self.buffer = records
        self.total_fetched += len(records)
        self.current_page += 1
        
        # 检查是否还有更多数据
        total_count = response.get('total', 0)
        self.has_more = self.total_fetched < total_count
```

### 6. 进度显示和错误处理

#### 6.1 进度显示
```python
class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total=None, interval=1000):
        self.total = total
        self.processed = 0
        self.interval = interval
        self.start_time = time.time()
    
    def update(self, count=1):
        """更新进度"""
        self.processed += count
        
        if self.processed % self.interval == 0:
            self._show_progress()
    
    def _show_progress(self):
        """显示进度信息"""
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0
        
        if self.total:
            percent = (self.processed / self.total) * 100
            eta = (self.total - self.processed) / rate if rate > 0 else 0
            print(f"# 进度: {percent:.1f}% ({self.processed}/{self.total}) 速度: {rate:.0f}/s 预计剩余: {eta:.0f}s", 
                  file=sys.stderr, flush=True)
        else:
            print(f"# 已处理: {self.processed} 速度: {rate:.0f}/s", 
                  file=sys.stderr, flush=True)
```

#### 6.2 错误处理和重试
```python
class StreamingErrorHandler:
    """流式错误处理器"""
    
    def __init__(self, max_retries=3, error_log=None):
        self.max_retries = max_retries
        self.error_log = error_log or sys.stderr
        self.error_count = 0
        self.success_count = 0
    
    def handle_error(self, error, context=None):
        """处理错误"""
        self.error_count += 1
        context_str = f" (context: {context})" if context else ""
        print(f"# 错误: {error}{context_str}", file=self.error_log, flush=True)
        
        # 决定是否继续
        if self.error_count > self.max_retries * 10:
            raise Exception("错误过多，停止处理")
    
    def handle_success(self, count=1):
        """处理成功"""
        self.success_count += count
```

### 7. 完整使用示例

#### 7.1 大数据查询和更新
```bash
# 查询大量记录并流式更新
t show -w 状态=待处理 --stream --output json-stream --progress | \
t update --stream-input --set "状态=处理中" --progress --batch-size 50

# 预期输出：
# # 已处理 1000 条记录
# # 已处理 2000 条记录
# # 已处理 3000 条记录
# ...
# ✅ 完成：成功更新 5234 条记录
```

#### 7.2 复杂数据处理管道
```bash
# 多步骤数据处理
t show -w 创建时间>2024-01-01 --stream --output json-stream | \
jq -c 'select(.fields.金额 > 1000)' | \
t update --stream-input --set "优先级=高" --json-format

# 数据迁移
t show --table 旧表 --stream --output json-stream | \
t insert --stream-input --target-table 新表 --map-fields "旧字段=新字段"
```

#### 7.3 实时监控和处理
```bash
# 持续监控和处理新数据
while true; do
    t show -w 状态=新建 --stream --output id-stream --limit 100 | \
    t update --stream-input --set "状态=已分配" 分配时间=$(date +%Y-%m-%d)
    
    sleep 60  # 每分钟检查一次
done
```

这个流式设计确保了我们能够处理任意大小的数据集，而不会因为内存限制而崩溃，同时提供了良好的用户体验和错误处理机制。