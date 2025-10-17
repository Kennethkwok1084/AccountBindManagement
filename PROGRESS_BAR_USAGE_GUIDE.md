# 进度条功能快速使用指南

## 🎯 已完成的功能

### ✅ 核心组件
- `ProgressTracker` 类 - 智能进度追踪器（`ui_components.py`）
- 自动计算进度、显示统计、预估时间

### ✅ 已支持进度条的功能

#### 1. 账号导入 ✅
**页面:** `pages/1_🗂️_账号管理.py`  
**业务逻辑:** `AccountManager.import_accounts_from_excel()`  
**显示内容:**
- 文件解析进度 (0-10%)
- 数据预处理进度 (10-50%)
- 数据库写入进度 (50-90%)
- 成功/失败统计

#### 2. 缴费导入 ✅
**页面:** `pages/3_🚀_绑定导出.py`  
**业务逻辑:** `PaymentProcessor.import_payments_from_excel()`  
**显示内容:**
- 文件读取 (0-20%)
- 数据处理和写入 (20-90%)
- 成功/失败统计

#### 3. 绑定任务处理 ✅ **（最重要）**
**页面:** `pages/3_🚀_绑定导出.py`  
**业务逻辑:** `PaymentProcessor.process_pending_payments_and_generate_export()`  
**显示内容:**
- 当前处理第 X/Y 条
- 正在处理的学号
- 查找账号/执行绑定/数据库同步
- 实时成功/失败统计
- 预估剩余时间

#### 4. 用户列表同步 ✅
**页面:** *待集成*  
**业务逻辑:** `AccountManager.sync_binding_details_from_excel()`  
**显示内容:**
- 文件解析 (0-10%)
- 同步处理 (10-90%)
- 更新数量/释放数量统计

## 🚀 如何使用

### 在页面中集成进度条（3步）

```python
# 第1步：导入组件
from ui_components import ProgressTracker

# 第2步：创建追踪器和回调
if st.button("执行任务"):
    progress_container = st.container()
    
    with progress_container:
        # 创建进度追踪器
        tracker = ProgressTracker(
            total=100,  # 总任务数（或使用100表示百分比）
            title="任务标题",
            show_eta=True  # 显示预估时间
        )
        
        # 定义回调函数
        def update_progress(info):
            tracker.update(
                current=info.get('current', 0),
                message=info.get('message', ''),
                success_count=info.get('success', 0),
                failed_count=info.get('failed', 0),
                step=info.get('step', '')
            )
        
        # 第3步：调用业务逻辑并传递回调
        result = business_logic.process_data(
            data,
            progress_callback=update_progress
        )
        
        # 标记完成
        if result['success']:
            tracker.complete(
                success_count=result['processed_count'],
                failed_count=result['failed_count'],
                message="处理完成"
            )
        else:
            tracker.error(result['message'])
```

### 在业务逻辑中支持进度回调

```python
def your_business_method(data, progress_callback=None):
    """
    Args:
        progress_callback: 可选的进度回调函数
    """
    result = {'success': False, 'processed_count': 0}
    
    try:
        total = len(data)
        
        # 初始化进度
        if progress_callback:
            progress_callback({
                'current': 0,
                'total': total,
                'success': 0,
                'failed': 0,
                'message': '开始处理...',
                'step': '初始化'
            })
        
        # 处理数据
        for idx, item in enumerate(data, 1):
            # 你的业务逻辑
            process_item(item)
            result['processed_count'] += 1
            
            # 更新进度（每5条或完成时）
            if progress_callback and (idx % 5 == 0 or idx == total):
                progress_callback({
                    'current': idx,
                    'total': total,
                    'success': result['processed_count'],
                    'failed': 0,
                    'message': f'正在处理: {item}',
                    'step': f'进度 - {idx}/{total}'
                })
        
        # 完成
        if progress_callback:
            progress_callback({
                'current': total,
                'total': total,
                'success': result['processed_count'],
                'failed': 0,
                'message': '处理完成',
                'step': '完成'
            })
        
        result['success'] = True
        
    except Exception as e:
        if progress_callback:
            progress_callback({
                'current': 0,
                'total': 0,
                'success': 0,
                'failed': 0,
                'message': f'错误: {e}',
                'step': '错误'
            })
    
    return result
```

## 📝 进度信息标准格式

所有进度回调使用统一的字典格式：

```python
{
    'current': 50,              # 当前进度（数值）
    'total': 100,               # 总数
    'success': 45,              # 成功计数
    'failed': 5,                # 失败计数
    'message': '正在处理...',   # 状态消息
    'step': '数据处理'          # 当前步骤
}
```

## ⚡ 性能优化建议

### 1. 控制更新频率
```python
# ❌ 不好：每次循环都更新（性能差）
for item in data:
    if progress_callback:
        progress_callback({...})

# ✅ 好：每N条更新一次
for idx, item in enumerate(data, 1):
    if progress_callback and (idx % 10 == 0 or idx == len(data)):
        progress_callback({...})
```

### 2. 大数据集处理
- 数据量 < 100：每条更新
- 数据量 100-1000：每5-10条更新
- 数据量 > 1000：每50-100条更新

### 3. 使用百分比模式
```python
# 对于不确定总数的任务，使用百分比
tracker = ProgressTracker(
    total=100,  # 使用100表示百分比
    title="处理任务"
)

# 更新时使用0-100的值
progress_callback({
    'current': 50,  # 50%
    'total': 100,
    ...
})
```

## 🎨 自定义样式

### 修改进度条颜色
在 `ui_components.py` 中的 `ProgressTracker` 类：

```python
# 修改进度条渐变色
st.progress(progress)  # 默认使用全局主题色
```

### 自定义统计显示
```python
# 在 tracker.update() 中自定义显示逻辑
with self.stats_container.container():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("✅ 成功", success_count)
    # ... 添加更多指标
```

## 🐛 常见问题

### Q: 进度条不更新？
A: 检查是否传递了 `progress_callback` 参数，确保回调函数被正确调用。

### Q: 页面卡顿？
A: 降低更新频率，避免每次循环都更新进度。

### Q: 时间预估不准确？
A: 前几次更新时预估可能不准，处理越多越准确。可以在开始时隐藏ETA：
```python
tracker = ProgressTracker(total=100, show_eta=False)
```

### Q: 如何禁用进度条？
A: 不传递 `progress_callback` 参数即可，代码会自动退化到原有行为。

## 📚 示例参考

查看以下文件了解完整实现：

1. **绑定导出页面** - `pages/3_🚀_绑定导出.py`
   - 完整的进度条集成示例
   - 包含错误处理

2. **账号管理页面** - `pages/1_🗂️_账号管理.py`
   - 百分比模式的使用

3. **业务逻辑** - `utils/business_logic.py`
   - 如何在业务逻辑中添加进度支持

## 🎯 下一步

### 待完成的任务：
- [ ] 用户列表页面集成进度条
- [ ] 系统维护添加进度反馈
- [ ] 完整测试（小数据和大数据）
- [ ] 性能优化

### 建议的改进：
- 添加暂停/取消功能
- 支持多步骤任务的进度展示
- 添加进度历史记录
- 优化移动端显示

---

**最后更新:** 2025-10-17  
**文档版本:** 1.0
