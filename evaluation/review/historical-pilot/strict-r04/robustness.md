# Robustness reviewer 原始报告

Using bp-coding-best-practices

## 范围与限制

完整阅读 input.json 提供的 r04/sklearn/mixture/base.py，依据嵌入 robustness 角色、编码最佳实践和 workflow 严重度定义。共 5 次只读调用，仅读取获准输入及全局 AGENTS／RTK。未执行代码、联网或读取其他 reviewer 产物。没有 diff、历史、派生类及依赖实现，无法确定引入时间，不构成集成批准。技能引用的 safety 详细文件不在输入中，未越界读取。

## ROB-1：首次拟合警告升级为异常后，warm-start 重试访问未初始化状态

- File：r04/sklearn/mixture/base.py
- Line：221–225；关联 236、265–274。
- Severity：P1。
- 触发：新建模型启用 warm_start=True、n_init=1、max_iter=1、有限容差；初始化正常，首轮 EM 得到有限 lower bound。调用方将 ConvergenceWarning 配置为异常，首次拟合在第 266 行退出，然后恢复默认警告策略或增加迭代次数并在同一对象重试。
- 根因：第 225 行提前创建 converged_，第 221 行却仅凭其存在判定可 warm-start。第 266 行位于第 274 行 lower_bound_ 初始化之前，异常没有撤销完成标记。
- 影响：重试 do_init=False，跳过初始化，并在第 236 行读取尚不存在的 self.lower_bound_，抛出 AttributeError；已消除首次失败条件仍不能恢复。
- 证据：首次 fit → fit_predict → converged_=False → lower_bound=-inf；单轮有限结果的 change 为无穷大，不满足第 249 行有限容差条件；第 266 行警告升级为异常，未执行第 274 行。第二次 fit → fit_predict → hasattr(converged_)=True → do_init=False → 读取缺失的 lower_bound_。
- 建议：用完整已提交拟合状态判定 warm-start，或首次拟合异常时撤销未完成状态，避免以提前设置的 converged_ 属性存在性代表完成。
- 验证性质：静态路径推导，未执行复现；假设派生实现允许正常 EM 迭代并返回有限 lower bound，不依赖其具体算法。

## 跨维度提示

第 263 行最终 E-step 在第 272 行恢复最佳参数之前执行；最佳初始化不是最后一次时，返回标签与最终模型可能不一致。该正常路径契约问题交由对应 reviewer 判断，不计入本维度候选。
