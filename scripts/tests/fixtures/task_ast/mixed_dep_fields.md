# 合成语料：depends_on 与遗留「依赖」字段并存（不同任务各用一种）

### 任务 1：[pending] 甲
- depends_on: []

### 任务 2：[pending] 乙
- 依赖: Task 1

### 任务 3：[pending] 丙
- depends_on: Task 1, Task 2
