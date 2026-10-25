# r04 契约与信任链审查

## 阶段 1：函数契约分析

来源仅为允许的 input.json 内嵌完整模块、magical 角色、tasks.md、scope.md 和全局 AGENTS.md、RTK.md。下文行号均指 `r04/sklearn/mixture/base.py`，不是 JSON 行号。

**历史证据限制：没有父版本、diff 或变更列表。所有函数的 Before 均为未知，After 仅表示所供快照；不能断言「无契约变化」，也不能将任何静态缺陷分类为 introduced、widened 或 incomplete-fix-in-modified-logic。因此无法完成历史变化证据门槛。**

以下覆盖全部 26 个函数。五维契约按「前置；后置；错误；所有权；并发不变量」列出，均为当前快照事实，不是历史变化。

| 函数 | 当前五维契约及证据 |
| --- | --- |
| _check_shape | 可转数组；形状匹配才正常结束；不匹配 ValueError；局部数组；无同步声明。21—35。 |
| _check_X | 数组和可选约束；返回检查后的 X；样本或特征不符 ValueError；不声明转移；None 表示省略对应检查。38—61。 |
| BaseMixture.__init__ | 接受配置；写入实例；不验证；实例持有配置引用；无同步。71—83。 |
| _check_initial_parameters | X 和配置；检查基础范围后委托子类；非法范围 ValueError；无资源转移；合法性由基础和子类共同证明。85—119。 |
| _check_parameters | 子类必须实现参数检查；后置和异常细节未知；无已声明所有权或同步。121—129。 |
| _initialize_parameters | X 及随机状态；生成 resp 并初始化；未知方法 ValueError；局部数组交给子类；行归一化或单一标签。131—155。 |
| _initialize | X 和 resp；子类初始化模型；异常、所有权、同步细节未知。157—167。 |
| fit | 输入数据；委托 fit_predict 后返回 self；传播委托异常；修改同一实例；文档承诺最佳模型及热启动。169—192。 |
| fit_predict | 检查 X 和配置；保存最佳参数并返回标签；未收敛警告；修改模型和统计字段；最佳参数、标签和统计应一致。194—276。 |
| _e_step | X；返回平均对数概率和职责；传播下游异常；返回数组；职责对应当前模型。278—295。 |
| _m_step | X 和 log_resp；子类更新模型；异常和所有权未知；并发保障未声明。297—309。 |
| _check_is_fitted | 子类实现拟合状态检查；其余细节未知。311—313。 |
| _get_parameters | 子类导出参数；拷贝还是别名未知；异常、并发细节未知。315—317。 |
| _set_parameters | 子类恢复参数；异常和所有权细节未知；供后续推理信任。319—321。 |
| score_samples | 已拟合且特征数相符；每样本 log 概率；传播验证异常；返回结果数组；读取当前模型。323—340。 |
| score | 输入 X；平均样本分数；传播 score_samples 异常；无资源转移；继承其状态要求。342—356。 |
| predict | 已拟合且特征数相符；返回最大加权概率分量；验证异常；返回标签数组；读取当前模型。358—374。 |
| predict_proba | 已拟合且特征数相符；职责指数；验证异常；返回数组；读取当前模型。376—394。 |
| sample | 已拟合及正样本数；生成 X 和标签；非正数 ValueError；使用配置随机状态；协方差表示决定采样分支。396—443。 |
| _estimate_weighted_log_prob | X；分量概率加权；下游异常透传；数组结果；依赖子类形状契约。445—456。 |
| _estimate_log_weights | 子类返回分量 log 权重；异常、所有权、同步细节未知。458—466。 |
| _estimate_log_prob | 子类返回样本 × 分量 log 概率；其他实现细节未知。468—482。 |
| _estimate_log_prob_resp | X；当前模型下归一化职责；忽略 underflow，其他错误未捕获；局部结果数组；减去每行 logsumexp。484—508。 |
| _print_verbose_msg_init_beg | verbosity；可打印并设置计时；打印异常未捕获；实例保存计时；高 verbosity 初始化计时。510—517。 |
| _print_verbose_msg_iter_end | 迭代及差值；按间隔打印；取模或输出异常未捕获；可更新计时；依赖 init_beg。519—528。 |
| _print_verbose_msg_init_end | lower bound；按 verbosity 打印；输出异常未捕获；读取计时；读取 converged_。530—536。 |

## 阶段 1.5：逐分支与证明义务台账

由于变更未知，以下是**快照静态义务**，不冒充 changed branches。每行独立，不合并兄弟分支。种子为该行准确函数、字段或表达式，信任点均为快照中具体消费者。「证明」仅限列中所述，不额外证明子类实现、安全并发或其他输入合法性。

| ID | 分支／证明、类型、声明属性 | 替代表示与具体见证尝试 | 下游信任点／搜索种子 |
| --- | --- | --- | --- |
| O1 | 33，deny-path：形状不等拒绝 | list 与 ndarray 同形；错形数组 | 调用方未知；_check_shape、param.shape |
| O2 | 53 左项，nullability：None 跳过组件约束 | None 与数值组件数；合法预测仅 1 行 | predict → _check_X；n_components |
| O3 | 53 右项，deny-path：样本不足拒绝 | 1 行、2 个分量 | fit_predict；X.shape[0] |
| O4 | 57 左项，nullability：None 跳过特征约束 | 首次拟合无 means_；已有模型的特征数 | fit_predict 与 predict；n_features |
| O5 | 57 右项，deny-path：特征不符拒绝 | 模型 2 维，输入 1 维 | predict、score_samples、predict_proba |
| O6 | 61，downstream-trust：返回检查结果 | list 转二维数组；仅证明传入的约束 | fit_predict、推理入口；return X |
| O7 | 92，deny-path：组件数至少 1 | 0 与 1 | _initialize_parameters；n_components |
| O8 | 97，deny-path：tol 非负 | -1 与 0 | fit_predict:249；tol |
| O9 | 102，deny-path：运行次数至少 1 | 0 与 1 | fit_predict:230；n_init |
| O10 | 107，deny-path：迭代次数至少 1 | 0 与 1 | fit_predict:238；max_iter |
| O11 | 112，deny-path：协方差正则非负 | -1 与 0 | _check_parameters；reg_covar |
| O12 | 143，allow-path：kmeans 生成独热 resp | 标签索引与概率矩阵两种职责表示 | _initialize:155；label、resp |
| O13 | 148，allow-path：random 生成归一化 resp | 连续职责与独热职责 | _initialize:155；resp.sum |
| O14 | 151，fallback：未知方法拒绝 | 非 kmeans、random 字符串 | fit_predict；init_params |
| O15 | 192，downstream-trust：返回已拟合 self | 对象状态与标签结果分离 | fit 的调用方；fit_predict |
| O16 | 221 左项，allow-path：非热启动不检查旧标记 | 已拟合但 warm_start=False | 233 初始化；warm_start |
| O17 | 221 右项，metadata-shape：标记存在代表可复用状态 | converged_=False 与不存在；失败后只残留标记 | 236 读取 lower_bound_；hasattr |
| O18 | 222 真分支，allow-path：初始化采用 n_init | warm_start=True 首次调用、n_init=2 | 230 循环；do_init |
| O19 | 222 假分支，fallback：复用仅运行一次 | 已完整拟合的热启动实例 | 230 循环；n_init=1 |
| O20 | 233 真分支，lifecycle：创建本轮参数 | 两次独立初始化 | 241 E-step；_initialize_parameters |
| O21 | 233 假分支，lifecycle：保留旧参数 | 成功热启动与失败残留状态 | 241 E-step；do_init |
| O22 | 236 真分支，metadata-shape：-inf 表示未有下界 | -inf 哨兵与有限下界 | 246 change；lower_bound |
| O23 | 236 假分支，metadata-shape：旧 lower_bound_ 可用 | 完整拟合与只存在 converged_ | 246 change；self.lower_bound_ |
| O24 | 249 真分支，allow-path：达到阈值退出 | 变化 0、tol>0；以前轮次已收敛 | 265 警告条件；converged_ |
| O25 | 249 假分支，fallback：继续迭代或耗尽 | tol=0、变化非零 | 253、255；max_iter |
| O26 | 255 真分支，allow-path：更大下界保存快照 | 当前轮次更优；参数副本与别名 | 272 _set_parameters；best_params |
| O27 | 255 假分支，fallback：较差或并列保留最佳 | 第 1 轮好，第 2 轮差；-inf/NaN 比较 | 272、273；max_lower_bound |
| O28 | 263，downstream-trust：最终 E-step 与发布模型一致 | 最后一轮模型与最佳模型不是同一状态 | 276 标签返回、374 predict |
| O29 | 265 真分支，deny-path：未收敛发警告 | 所有轮次均未收敛 | fit 调用方；warnings.warn |
| O30 | 265 假分支，allow-path：不需要警告 | 前轮收敛但选中另一未收敛轮 | fit 调用方；converged_ |
| O31 | 272—276，downstream-trust：发布最佳模型及标签 | 参数、n_iter_、lower_bound_、log_resp 四种状态 | predict、score；_set_parameters |
| O32 | 295，downstream-trust：均值与职责来自同次估计 | 标量均值与逐样本数组 | fit_predict:241；_e_step |
| O33 | 340，downstream-trust：返回逐样本总概率 | 分量权重与样本维 | score:356；logsumexp |
| O34 | 356，downstream-trust：每样本均值 | 多样本与单样本 | score 调用方；mean |
| O35 | 374，downstream-trust：按当前参数选标签 | 归一化职责与加权 log 概率 | predict 调用方；argmax |
| O36 | 394，downstream-trust：职责指数为概率 | log 表示与线性表示 | predict_proba 调用方；np.exp |
| O37 | 415，deny-path：非正样本数拒绝 | 0、-1、1 | sample 调用方；n_samples |
| O38 | 424，allow-path：full 协方差逐组件采样 | 矩阵列表，组件抽中 0 次 | vstack、443；covariances_ |
| O39 | 429，allow-path：tied 共享协方差采样 | 所有分量共用一个矩阵 | vstack、443；covariance_type |
| O40 | 434，fallback：对角或球形采样 | 每特征方差向量与每分量标量 | vstack、443；np.sqrt |
| O41 | 443，downstream-trust：样本与分量标签顺序一致 | 某分量计数为 0 | sample 调用方；n_samples_comp |
| O42 | 456，metadata-shape：概率矩阵加权广播 | n_samples × n_components 和分量向量 | 503、340、374；_estimate_log_weights |
| O43 | 505—508，downstream-trust：逐样本归一化 | 极小概率、有限 log 概率、全 -inf | _e_step、predict_proba；logsumexp |
| O44 | 512，allow-path：verbosity=1 只打印 | 无计时字段 | init_end、iter_end 的 verbosity=1 |
| O45 | 514，allow-path：verbosity>=2 建立计时 | 有计时字段 | iter_end:527、init_end:536 |
| O46 | 521，allow-path：间隔整除时处理日志 | verbose=0、verbose_interval=0 | fit_predict:247；取模 |
| O47 | 522，allow-path：verbosity=1 输出迭代号 | 无计时字段 | print；n_iter |
| O48 | 524，allow-path：verbosity>=2 输出耗时 | init_beg 已建立计时 | print、528 更新；_iter_prev_time |
| O49 | 532，allow-path：verbosity=1 输出收敛标记 | 多轮初始化共享标记 | print；converged_ |
| O50 | 534，allow-path：verbosity>=2 输出耗时和下界 | 本轮时间与共享标记 | print；_init_prev_time |

## 阶段 2：逐义务验证网格

统一限制：每行 Delta 都是**未知：缺父版本**，不使用「pre-existing-unchanged」或「no-defect-established」冒充历史判定。每行完成当前可做的五项检查；全量历史验证均受阻。以下「关闭」只表示未晋升为本角色 finding，不代表证明代码无错。无证据显示此模块承诺线程安全，未添加并发假设。入口指模块公开入口；抽象方法的具体子类实现均不可验证。

| ID | 可达性：入口／直接调用／消费者链 | 见证结果与替代表示检查 | 不变量／调用方生存 | Delta；结案 |
| --- | --- | --- | --- | --- |
| O1 | _check_shape → 33 → 外部调用方未知 | 同形 list 转数组；错形被拒绝，无安全输入误拒证据 | ValueError 显式终止 | 未知；关闭 |
| O2 | predict → _check_X → 61 → 374 | 预测样本少于分量合法；None 不表示待初始化分量 | 仅省略组件数检查，不省略 check_array | 未知；关闭 |
| O3 | fit → fit_predict → _check_X:53 | 1 行、2 分量被拒绝；未证明误拒 | 校验失败不进入拟合 | 未知；关闭 |
| O4 | fit_predict → _check_X:57 → 初始化 | 首次拟合 None 合理；热启动特征验证依赖子类，未证具体故障 | 不将缺省特征约束等同所有状态有效 | 未知；关闭 |
| O5 | predict → _check_X:57 → 374 | 特征不符安全拒绝 | 模型状态不修改 | 未知；关闭 |
| O6 | fit_predict／predict → _check_X:61 → 模型方法 | list 与数组统一；未证形状逃逸 | 只输出已请求的检查结果 | 未知；关闭 |
| O7 | fit_predict → _check_initial_parameters:92 → 初始化 | 0 被拒绝；1 通过未见不安全见证 | 子类继续检查，不是完整类型证明 | 未知；关闭 |
| O8 | fit_predict → 97 → 249 | -1 拒绝；0 导致严格阈值不满足，但未承诺 0 必收敛 | 正常耗尽并警告 | 未知；关闭 |
| O9 | fit_predict → 102 → 230 | 0 拒绝；1 进入循环 | 不额外声称整数类型已校验 | 未知；关闭 |
| O10 | fit_predict → 107 → 238 | 0 拒绝；1 至少执行一次 | n_iter 被赋值 | 未知；关闭 |
| O11 | fit_predict → 112 → _check_parameters | -1 拒绝；0 合法，无具体子类退化证据 | 无异常吞没 | 未知；关闭 |
| O12 | fit_predict → _initialize_parameters:143 → _initialize | 独热表示被构造；外部 KMeans 源码不可见 | 未证明标签越界；子类所有权未知 | 未知；关闭 |
| O13 | fit_predict → _initialize_parameters:148 → _initialize | 连续职责归一化；全零随机行仅理论可能，无具体状态证据 | 未将理论概率事件升格 | 未知；关闭 |
| O14 | fit_predict → _initialize_parameters:151 → ValueError | 未知方法明确拒绝，无支持其他拼写契约 | 调用中断，异常透传 | 未知；关闭 |
| O15 | fit → fit_predict → return self | 返回同一对象符合 189；标签问题另查 O28 | 参数状态由 fit_predict 管理 | 未知；关闭 |
| O16 | fit_predict:221 → 233 → _initialize | warm_start=False 不读取标记，合法重新拟合 | 不依赖旧状态 | 未知；关闭 |
| O17 | fit_predict:221 → 236 → lower_bound_ | hasattr 只证字段存在；225 早于 lower_bound_ 赋值，失败重试可能残留 | 具体子类失败路径未给出；标记与完成度非等价 | 未知；关闭，未晋升 |
| O18 | fit → fit_predict:222 → 230 | warm_start=True 且首次 n_init=2 执行 2 次，与 177—178 文案有张力 | 无父版，不作为契约变更 finding | 未知；关闭 |
| O19 | fit_predict:222 → 230 → E-step | 已完整拟合热启动仅运行一次，无不安全见证 | 信任已存在的完整状态，O17 单独保留 | 未知；关闭 |
| O20 | fit_predict:233 → _initialize_parameters → _e_step | 多次初始化允许状态变化 | 子类实现不可见，不假设存储别名 | 未知；关闭 |
| O21 | fit_predict:233 假 → 236 → _e_step | 完整热启动合法；失败残留与 O17 同限制 | 不证明标记即就绪 | 未知；关闭 |
| O22 | fit_predict:236 真 → 246 → 249 | 首次有限下界减 -inf 不收敛，第二轮继续 | 哨兵不是有效拟合成绩；max_iter=1 允许警告 | 未知；关闭 |
| O23 | fit_predict:236 假 → 246 | 完整模型 lower_bound_ 可用；部分状态见 O17 | 未给出合法反序列化格式，不猜其他就绪表示 | 未知；关闭 |
| O24 | fit_predict:249 真 → 250 → 265 | 本轮变化 0 且 tol>0 时退出合理；共享标记另查 O30 | 不证明其他初始化也收敛 | 未知；关闭 |
| O25 | fit_predict:249 假 → 循环或 253 | 达不到阈值耗尽；不构成单独错误 | 继续检查下游，没有用此关闭 O28 | 未知；关闭 |
| O26 | fit_predict:255 真 → _get_parameters → 272 | 更优轮次保存参数；别名是否可变由抽象实现决定 | 不能证明快照别名故障 | 未知；关闭 |
| O27 | fit_predict:255 假 → 263 → 272 | 较差末轮保留前轮最佳是合法路径；全 -inf/NaN 缺具体子类见证 | 最佳快照与当前模型分离已成立，交 O28 | 未知；关闭 |
| O28 | fit_predict → 263 _e_step → 272 恢复最佳 → 276 标签；predict → 374 | accepted-but-unsafe 静态状态见证：最佳首轮与末轮标签不同；mishandled：当前状态替代了最佳状态 | 正常返回但返回标签不对应发布参数，见 H1 | 未知；静态候选，禁止晋升 |
| O29 | fit_predict:265 真 → warnings.warn → 272 | 全未收敛发警告，无拒绝安全输入 | 警告后仍发布参数；过滤器行为不做环境猜测 | 未知；关闭 |
| O30 | fit_predict:265 假 → 272 | 前轮 converged_=True 未逐轮重置，可能与最佳轮次不一致 | 文案「每次 trial」与统计解释存在边界，不另升格 | 未知；关闭 |
| O31 | fit_predict → 272—276 → predict／score | 参数和下界取最佳；log_resp 仍来自末轮，同 H1 | 同根因不重复建候选 | 未知；静态候选，禁止晋升 |
| O32 | fit_predict → _e_step → 295 → _m_step | 均值和职责由同次调用获得；形状由抽象概率实现保证 | 未见不一致计算 | 未知；关闭 |
| O33 | score → score_samples → 340 | axis=1 聚合组件，保留样本维 | 拟合和特征检查先行 | 未知；关闭 |
| O34 | score → score_samples → 356 | 样本均值符合文档；空输入受 _check_X 检查 | 无额外可达不安全见证 | 未知；关闭 |
| O35 | predict → 374 → 调用方 | 有限每行归一化常量不改变 argmax，与职责表示一致 | 从发布模型读取；与 O28 的陈旧结果不同 | 未知；关闭 |
| O36 | predict_proba → 393 → 394 | log 职责指数，转换符合表示 | 溢出／退化输入未有具体合法见证 | 未知；关闭 |
| O37 | sample → 415 → ValueError | 0 与负数被拒绝；消息插值使用 n_components 而非 n_samples | 仅诊断值错，不报告为本维度信任链缺陷 | 未知；关闭 |
| O38 | sample → 424 → vstack → 443 | full 使用每分量矩阵；零计数组保留分量顺序 | 外部 numpy 实现不在范围，未证错 | 未知；关闭 |
| O39 | sample → 429 → vstack → 443 | tied 合法共享矩阵表示被专门处理 | 没有错误复用每分量矩阵 | 未知；关闭 |
| O40 | sample → 434 → vstack → 443 | diagonal 向量、spherical 标量均通过广播表达 | 未知 covariance_type 是否经子类拒绝，不虚构支持集合 | 未知；关闭 |
| O41 | sample → 440 → 443 | X 与 y 都按同一 n_samples_comp 顺序连接 | 0 次分量不打乱标签 | 未知；关闭 |
| O42 | predict／score／_e_step → 456 → 消费者 | 分量权重向量向样本矩阵广播 | 依赖已写明的抽象返回形状，不假设非法子类 | 未知；关闭 |
| O43 | predict_proba／_e_step → 503—508 | 有限 log 概率按行归一化；全 -inf 无具体合法模型见证 | errstate 局部上下文，不持久改变设置 | 未知；关闭 |
| O44 | fit_predict → init_beg:512 → print | verbose=1 不设置时间，后续同级分支不读时间 | 未见计时字段缺失故障 | 未知；关闭 |
| O45 | fit_predict → init_beg:514 → iter_end／init_end | verbose>=2 先写两项计时再消费 | 同步顺序可见；不假设并发修改 verbosity | 未知；关闭 |
| O46 | fit_predict:247 → iter_end:521 → print | interval=0 会在 verbosity 检查前取模失败；未给出 0 合法配置契约 | 不冒充已证契约变更；无源码执行 | 未知；关闭 |
| O47 | fit_predict → iter_end:522 → print | verbose=1 只读迭代号 | 无计时依赖 | 未知；关闭 |
| O48 | fit_predict → iter_end:524 → print／528 | verbose>=2 依赖本轮 init_beg 已赋值 | 同步路径满足生命周期 | 未知；关闭 |
| O49 | fit_predict → init_end:532 → print | 显示共享 converged_；前轮真值可能保留，见 O30 | 不将日志语义另升格 | 未知；关闭 |
| O50 | fit_predict → init_end:534 → print | 时间本轮已初始化；标记同 O49 | 日志正常路径无新增证据 | 未知；关闭 |

## 阶段 3：缺陷晋升

No call-chain defects found based on contract changes, obligation ledger, and verified evidence-gating.

这表示**历史晋升门槛未满足**，不是「当前快照没有问题」。

最终 findings：`[]`。

### 静态 handoff H1：多次初始化的最佳轮次不是末轮时，提前计算职责使返回标签与保存模型不一致

- id：H1（仅 handoff，不属于最终 findings）。
- file：`r04/sklearn/mixture/base.py`。
- line：263。
- severity：P1（静态影响建议，非已晋升结论）。
- 对应义务：O28、O31。
- 触发：n_init=2，首轮下界高于第二轮，且两轮至少一个样本的最大概率分量不同。该状态路径由 230、255—258 的多次初始化及最佳轮选择直接允许；未执行实际子类实例。
- 具体状态见证：首轮下界 -1，最佳参数 A；第二轮下界 -2，当前参数 B。对某样本，A 的加权 log 概率为 [-1, -3]，B 为 [-4, -2]。各行归一化不改变 argmax，A 给标签 0，B 给标签 1。
- 根因：263 在参数 B 上计算 log_resp，272 随后恢复参数 A，276 仍返回 B 的职责 argmax。
- 影响：同一已拟合对象随后 predict(X) 在 374 使用 A 得到标签 0，而 fit_predict 返回标签 1；260—262 明确承诺的结果一致性被破坏。即使只发生组件编号置换，标签 ID 仍与对象的分量参数不对应。
- 证据链：fit_predict:230 → 255—258 保存 A → 末轮保留 B → 263 经 294、503、456 读取 B → 272 恢复 A → 276 返回 B 标签；predict:374 使用恢复后的 A。
- 反证检查：272 确实恢复最佳参数，但没有重新计算 log_resp，不能修复局部变量；n_init=1 或最佳轮次是末轮时问题不触发。
- 最小修复方向：在恢复 best_params 后执行最终 E-step，再返回其标签。
- Delta basis：未知；没有父版本，禁止称为 introduced、widened 或 incomplete-fix-in-modified-logic。交由负责完整源码正确性的审查维度按其门槛独立判断。

## Coverage 与限制

- Total modified functions：未知；完整阅读的快照函数为 26 个。
- Total changed branches / proofs identified：未知；静态台账覆盖 50 项分支／证明义务。
- Total obligations created：50。
- Obligations fully verified：静态五项网格已逐项处理 50；包含历史 Delta 的完整验证为 0，全部明确受阻。
- Candidate-defect obligations：O28、O31，仅静态 handoff，共用 H1。
- Closed-no-defect obligations：O1—O27、O29—O30、O32—O50；仅未证成本维度 finding，不表示历史已验证。
- Unreviewed changed branches：无法识别 changed 集合；所供完整模块中已识别的静态分支／证明无遗漏。抽象方法实现和外部库不可见。
- 只读调用计数：3 次 shell 调用。第 1 次读取全局 AGENTS.md、RTK.md、tasks.md、scope.md；第 2 次读取 input.json，输出存在截断；第 3 次从同一 JSON 提取完整带行号源码，无截断。magical 完整角色在第 2 次输出可见，无需额外 skill。
- 未读取其他案例、历史、网络、其他 reviewer 产物或仓库源码文件；未执行所供源码；未调用子代理。
- 写入前完成中文 Markdown 自检：中英文与数字间空格、中文全角标点、专有名词大小写；代码表达式保持原样。

