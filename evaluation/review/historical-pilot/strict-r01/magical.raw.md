## 阶段 1：函数契约分析

**正式发现：0。源级候选：1，因缺少父版本证据，不能通过冻结角色的升级门槛。**

审查来源仅为指定 `input.json` 中的角色、需求和源码，以及指定 `tasks.md`、`scope.md`。未执行待审代码。

下文 `S:L` 均指完整路径 `r01/astropy/modeling/separable.py:L`。

### 契约变化的证据限制

这是完整源码审查，不是 diff。所有函数的 **Before 均未知**，不能声称任何行为属于 `introduced`、`widened` 或 `incomplete-fix-in-modified-logic`，也不能声称「无契约变化」。

下面记录可见源码的 **After／当前契约**：

| 函数 | 前置条件 | 后置条件 | 错误传播 |
|---|---|---|---|
| `is_separable`，S:27 | 接收具有输入／输出数量的 Model | 单输入多输出直接返回 False；否则依据依赖矩阵行和是否为 1 返回布尔数组 | 未捕获矩阵计算错误 |
| `separability_matrix`，S:66 | 同上 | 返回输出 × 输入的布尔依赖矩阵 | 未捕获矩阵计算错误 |
| `_compute_n_outputs`，S:105 | 两侧分别是 Model 或二维坐标矩阵 | 返回两侧输出数之和 | 未验证任意对象／维度 |
| `_arith_oper`，S:130 | 两侧输入、输出数量分别相同 | 返回全 1 的依赖矩阵；注释明确采用非可分离处理 | 数量不匹配抛 `ModelDefinitionError` |
| `_arith_oper._n_inputs_outputs`，S:149 | Model 或二维矩阵 | 返回输入、输出数量 | 解包错误直接传播 |
| `_coord_matrix`，S:171 | 简单 Model，合法位置及输出空间 | 构建 Mapping、不可分离或可分离模型的依赖矩阵 | 索引／形状错误直接传播 |
| `_cstack`，S:219 | Model 或坐标矩阵 | 为 `&` 组合拼接依赖矩阵 | 数组操作错误直接传播 |
| `_cdot`，S:250 | Model 或坐标矩阵，满足复合维度 | 为 `|` 组合计算依赖乘积 | 点积 `ValueError` 转成 `ModelDefinitionError` |
| `_cdot._n_inputs_outputs`，S:267 | Model 或矩阵 | 将 Model 转矩阵，矩阵原样返回 | 转换错误直接传播 |
| `_separable`，S:290 | Model，提供自定义计算协议及必要模型元数据 | 优先使用自定义矩阵，否则递归复合模型或转换简单模型 | 无统一捕获；非 Model 的隐式返回不属于文档输入契约 |

**资源所有权／生命周期：** 当前源码主要创建局部 NumPy 数组；`_separable` 的自定义返回值和 `_cdot` 的矩阵参数可直接透传，未见释放、锁或外部资源管理契约。

**并发／不变量：** 可见代码未提供同步协议，亦无证据要求并发修改模型时保持快照一致性，故不据此提出缺陷。

## 阶段 1.5：Branch / Proof Obligation Ledger

由于无法识别「changed branches」，以下是对**当前源码分支与导出证明**的补充审查，不冒充变更账本。

调用链缩写：

- **A**：`is_separable` → `_separable` → 各帮助函数 → S:61–62 行和判定。
- **B**：`separability_matrix` → `_separable` → 各帮助函数 → S:101 非零判定。
- **C**：`_separable` S:307–309 → `_cstack` → `_compute_n_outputs`／`_coord_matrix`。
- **D**：`_separable` S:309 → `_arith_oper` → 内部数量提取函数。
- **E**：`_separable` S:309 → `_cdot` → 内部转换函数／`_coord_matrix`。

每行独立对应一个义务；「替代表达／见证」列也是后续验证的具体输入。源码定位、函数和字段同时构成 Search Seeds。

| ID | 分支／证明，类型 | 声称的性质；不证明什么 | 替代表达／见证 | 下游信任点 |
|---|---|---|---|---|
| O1 | S:57 `n_inputs == 1`，短路 | 非单输入绕过特殊规则；不证明独立性 | 两输入模型 | S:60 |
| O2 | S:57 `n_outputs > 1`，短路 | 区分单输出与多输出 | 一输入一输出 | S:58／60 |
| O3 | S:59 提前返回，deny-path | 单输入多输出不能标记独立 | `Mapping([0, 0])` | 公共 API 调用者 |
| O4 | S:61–63 行和证明，downstream-trust | 行和为 1 标记可分离；不检查实际模型求值 | 单位矩阵／全 1 矩阵 | 公共 API 调用者 |
| O5 | S:97 输入数条件，短路 | 非单输入进入递归 | 两输入模型 | S:100 |
| O6 | S:97 输出数条件，短路 | 一输入一输出进入递归 | 一输入一输出 | S:98／100 |
| O7 | S:98–99 提前返回，allow-path | 单输入多输出均依赖该输入；未检查自定义细节 | 重复 Mapping | 公共 API 调用者 |
| O8 | S:101–102 非零转换，downstream-trust | 非零表示依赖；不恢复丢失的零元素 | 单位矩阵／全 1 矩阵 | 公共 API 调用者 |
| O9 | S:118–119 左 Model，type-proof | 输出数取模型属性 | Model 与同形矩阵 | `_cstack` S:234 |
| O10 | S:120–121 左矩阵，metadata-shape | 第一维为输出数 | 二维坐标矩阵 | `_cstack` S:234 |
| O11 | S:122–123 右 Model，type-proof | 输出数取模型属性 | Model 与同形矩阵 | `_cstack` S:234 |
| O12 | S:124–125 右矩阵，metadata-shape | 第一维为输出数 | 二维坐标矩阵 | `_cstack` S:234 |
| O13 | S:150–151 Model，type-proof | 属性表示输入／输出数量 | 简单 Model | `_arith_oper` S:156–159 |
| O14 | S:152–154 矩阵，metadata-shape | 二维形状与属性顺序一致 | `(outputs, inputs)` 矩阵 | 同上 |
| O15 | S:159 输入不等，deny-path | 输入数量不同拒绝；短路输出比较 | 输入不同、输出相同 | S:160 |
| O16 | S:159 输出不等，deny-path | 输入相同但输出不同拒绝 | 输入相同、输出不同 | S:160 |
| O17 | S:167–168 全 1，downstream-trust | 算术操作保守按不可分离处理；不证明精确稀疏依赖 | 相同形状的稀疏矩阵 | A／B |
| O18 | S:189–195 Mapping，type-proof | 映射索引生成逐输出依赖 | 重复、重排索引 | S:197–201 |
| O19 | S:197–198 Mapping 左侧，allow-path | 保留映射并嵌入上方 | 重排 Mapping，左位置 | C／E／A／B |
| O20 | S:199–201 Mapping 右侧，allow-path | 保留映射并嵌入下方 | 重排 Mapping，右位置 | 同上 |
| O21 | S:202 不可分离，metadata-shape | 使用稠密依赖；不主张精确稀疏结构 | 多输入不可分离模型 | S:205–208 |
| O22 | S:205–206 稠密左侧，allow-path | 稠密块仅在左侧输出区域 | 两输入、两输出模型 | C／E／A／B |
| O23 | S:207–208 稠密右侧，allow-path | 稠密块仅在右侧输出区域 | 同模型右置 | 同上 |
| O24 | S:209–213 可分离，metadata-shape | 对角依赖表达可分离性 | 单输入模型；非方阵元数据 | S:214–216 |
| O25 | S:214–215 右侧滚动，allow-path | 将对角依赖放入右侧输出区域 | 方阵模型及额外左侧输出 | C／E／A／B |
| O26 | S:214 假分支／216，allow-path | 左侧对角矩阵直接返回 | 左置方阵模型 | 同上 |
| O27 | S:236–237 左 Model，type-proof | 转换简单模型保留其依赖 | 简单模型与等价矩阵 | S:247 |
| O28 | S:238–240 左矩阵，metadata-shape | 左侧递归矩阵原样嵌入 | 左侧单位矩阵 | S:247 |
| O29 | S:241–242 右 Model，type-proof | 转换简单模型保留其依赖 | 简单模型与等价矩阵 | S:247 |
| O30 | S:243–245 右矩阵，metadata-shape | 应保留右侧递归依赖；实际只保留形状 | 右侧 2 × 2 单位矩阵 | S:247，再到 A／B |
| O31 | S:247 拼接返回，downstream-trust | 拼接结果被当作完整依赖证明 | 嵌套 `&` | A／B |
| O32 | S:271–272 Model 转换，type-proof | 简单模型变为坐标矩阵 | Model 与等价矩阵 | S:277–281 |
| O33 | S:273–275 矩阵透传，allow-path | 已计算依赖不被重新解释 | 稀疏矩阵 | S:281 |
| O34 | S:280–281／287 成功返回，downstream-trust | 复合依赖由矩阵乘积传播 | 单位矩阵复合 | A／B |
| O35 | S:282–286 异常转换，fallback | 无法点积的形状被拒绝 | 不兼容内维度 | A／B 调用者 |
| O36 | S:304–305 自定义实现，allow-path | 非 `NotImplemented` 结果即可信矩阵；未自行校验形状 | 自定义合法矩阵；`None` | A／B／递归操作 |
| O37 | S:304 sentinel 假分支，fallback | `NotImplemented` 表示应使用默认计算 | 默认协议返回 sentinel | S:306 |
| O38 | S:306–309 CompoundModel，type-proof | 递归子矩阵可按操作符组合 | 嵌套 `&`／`|` | `_operators`，再到 A／B |
| O39 | S:310–311 Model，type-proof | 简单模型可转坐标矩阵 | 非 CompoundModel 的 Model | A／B／递归操作 |
| O40 | S:310 假分支，fallback | 非 Model 无显式处理 | 任意普通对象 | A／B；但不属文档输入 |

## 阶段 2：Obligation Verification Grid

**所有行的 Delta Check：未知，无法归类。** 这不是 `pre-existing-unchanged` 或 `no-defect-established` 的同义词。缺少父版本不能被改写成任何时间关系判断。

下表每行按「可达性 → 见证 → 替代表达 → 不变量」顺序完成静态检查。A–E 明确列出了直接调用者、间接公共入口与精确信任消费者。未执行代码，未读取未提供的 Model／Mapping 实现。

| ID | 可达性／调用链 | 见证检查与 verdict | 表达检查及不变量／调用者生存 | 当前状态 |
|---|---|---|---|---|
| O1 | A 入口 S:57 → S:60 | 两输入：正常递归；`none established` | 不绕过递归依赖计算 | closed-no-defect |
| O2 | A 入口 S:57 → S:60 | 一输入一输出：正常递归；`none established` | 单输出没有误走多输出分支 | closed-no-defect |
| O3 | A 入口 → S:59 → 调用者 | 重复 Mapping：返回 False；`none established` | 多输出共享输入，与该特殊规则一致 | closed-no-defect |
| O4 | A → S:61–63 | 单位矩阵为 True，稠密矩阵为 False；局部 `none established` | 消费者依赖上游准确性；O30 污染会传播 | closed-no-defect，关联 O30 |
| O5 | B 入口 S:97 → S:100 | 两输入递归；`none established` | 未绕过依赖计算 | closed-no-defect |
| O6 | B 入口 S:97 → S:100 | 一输入一输出递归；`none established` | 特殊处理范围一致 | closed-no-defect |
| O7 | B 入口 → S:98–99 | 重复 Mapping 全 True；`none established` | 未建立合法、无依赖的反例；自定义协议未提供 | closed-no-defect |
| O8 | B → S:101–102 | 零与非零转换准确；局部 `none established` | 不恢复上游被覆盖的零元素 | closed-no-defect，关联 O30 |
| O9 | A／B → C → S:119 | Model 输出属性；`none established` | 与二维表达第一维一致 | closed-no-defect |
| O10 | A／B → C → S:121 | 两行矩阵输出数为 2；`none established` | 一维数组不属文档坐标矩阵 | closed-no-defect |
| O11 | A／B → C → S:123 | 右 Model 输出属性；`none established` | 与左侧独立核对 | closed-no-defect |
| O12 | A／B → C → S:125 | 右二维矩阵输出数正确；`none established` | 不把列数当输出数 | closed-no-defect |
| O13 | A／B → D → S:151 | Model 数量提取；`none established` | 返回顺序是输入、输出 | closed-no-defect |
| O14 | A／B → D → S:153–154 | 非方阵数量提取；`none established` | 从输出、输入形状反转正确 | closed-no-defect |
| O15 | A／B → D → S:159–165 | 输入不同即拒绝；`none established` | 对照 S:148、163–164，拒绝符合契约 | closed-no-defect |
| O16 | A／B → D → S:159–165 | 输入相同、输出不同拒绝；`none established` | 没有被前一短路遗漏 | closed-no-defect |
| O17 | A／B → D → S:167–168 | 稀疏输入变稠密；`none established` | S:135 明确保守规则，不能按未要求的精确性报错 | closed-no-defect |
| O18 | A／B → `_coord_matrix` S:189–195 | 重复／重排索引逐行 one-hot；`none established` | 空映射、越界映射合法性未知，不能假定合法 | closed-no-defect |
| O19 | C／E → S:198 → A／B | Mapping 左置；`none established` | 逐行依赖保持，其他输出区域为零 | closed-no-defect |
| O20 | C／E → S:200 → A／B | Mapping 右置；`none established` | 与左置分别核对，保持列意义 | closed-no-defect |
| O21 | C／E／`_separable` → S:202 | 不可分离模型取稠密块；`none established` | 未建立违反其声明的合法元数据 | closed-no-defect |
| O22 | C／E → S:206 → A／B | 左侧稠密块；`none established` | 不污染右侧输出区域 | closed-no-defect |
| O23 | C／E → S:208 → A／B | 右侧稠密块；`none established` | 不污染左侧输出区域 | closed-no-defect |
| O24 | C／E／`_separable` → S:212–213 | 方阵／单输入按对角构造；`none established` | 非方阵且 `separable=True` 的合法性未获 Model 契约支持，未升级 | closed-no-defect |
| O25 | C／E → S:215 → A／B | 方阵增加左侧输出后滚动；`none established` | 对方阵而言偏移可将对角线移至下方；未证明合法非方阵反例 | closed-no-defect |
| O26 | C／E → S:216 → A／B | 左置方阵保持对角线；`none established` | 无额外资源或状态修改 | closed-no-defect |
| O27 | A／B → C → S:237 | 左简单模型转矩阵；`none established` | 与左矩阵分支逐元素保留方式相容 | closed-no-defect |
| O28 | A／B → C → S:240 | 左单位矩阵保持稀疏性；`none established` | 原始矩阵只读，嵌入新数组 | closed-no-defect |
| O29 | A／B → C → S:242 | 右简单模型转换；`none established` | 分支自身保留模型依赖，不代表右矩阵分支也正确 | closed-no-defect |
| O30 | A／B → S:307–309 → `_cstack` S:245 → S:247 → S:61／101 | 右侧单位矩阵被填成全 1；`accepted-but-unsafe` | **mishandled**：递归 ndarray 的稀疏依赖被形状替代；调用者继续运行并返回错误结果 | candidate-defect，未通过 Delta Gate |
| O31 | A／B → C → S:247 → S:61／101 | 嵌套 `&` 传播 O30；`accepted-but-unsafe` | **mishandled** 的上游结果直接导出；无独立新根因 | candidate-defect，归并 O30 |
| O32 | A／B → E → S:272 | 简单 Model 转换；`none established` | 对照矩阵表达，未发现转换分支独立反例 | closed-no-defect |
| O33 | A／B → E → S:274–275 | 稀疏矩阵透传；`none established` | 未覆盖稀疏结构，点积不原地修改参数 | closed-no-defect |
| O34 | A／B → E → S:281／287 | 单位矩阵复合保持依赖；`none established` | S:265 交换对应函数复合方向，未建立反向错误见证 | closed-no-defect |
| O35 | A／B → E → S:282–286 | 不兼容内维度报错；`none established` | 对照 `|` 所需维度，未建立 rejected-but-safe 见证 | closed-no-defect |
| O36 | A／B → S:304–305 → 下游 | 合法自定义矩阵透传；`none established` | `None` 会进入该分支，但没有证据说明它是协议允许的替代表达；不可升级 | closed-no-defect |
| O37 | A／B → S:304 → S:306 | `NotImplemented` 进入默认实现；`none established` | sentinel 不被解释成「没有依赖」，而是继续计算 | closed-no-defect |
| O38 | A／B → S:306–309 → 操作函数 | 嵌套 `&` 可到 O30；本分支局部 `none established` | 复合模型的矩阵表达明确来自递归计算，而非任意外部数组 | closed-no-defect，关联 O30 |
| O39 | A／B → S:310–311 → `_coord_matrix` | 简单 Model 转换；`none established` | 与复合模型分支相互排斥，未绕过自定义实现 | closed-no-defect |
| O40 | A／B → S:310 假分支 | 普通对象可能失败；`none established` | 文档要求 Model，未建立合法输入可达该末尾；not relevant | closed-no-defect |

### 保留的源级候选 C1

**[P2，未升级] 右侧嵌套 `&` 将依赖矩阵覆盖为全 1，导致独立输出被错误判为相关／不可分离。**

- **精确位置：** `r01/astropy/modeling/separable.py:245`
- **关联义务：** O30、O31。
- **见证：** `Shift(1) & (Shift(2) & Shift(3))`。`Shift` 与 `&` 的独立输出用法由同文件 S:45–47、85–87 的文档例子支持。
- **静态推导：**
  1. `_separable` 在 S:307–308 递归计算左右子模型。
  2. 右子树的两个一输入、一输出 Shift 形成 2 × 2 单位依赖矩阵。
  3. 外层 `_cstack` 的右参数因此为矩阵，进入 S:243–245。
  4. S:245 写入常量 `1`，而不是右矩阵内容。
  5. 应有的三阶单位依赖矩阵变成：
     ```text
     1 0 0
     0 1 1
     0 1 1
     ```
  6. S:101 将额外的非零元素报告为依赖；S:61–62 将后两个输出标记为 False。
- **影响：** 两个实际独立的右侧输出被报告为相互依赖；不需要崩溃即可产生错误结果。
- **最小修正方向：** 在 S:245 保留 `right` 的元素，而非以常量覆盖整个块。
- **关键限制：** 以上是静态源码证据，不是运行结果。缺少父版本，无法给出角色要求的变更分类。

## 阶段 3：Systemic Defect Promotion

**没有候选满足全部三个升级条件。**

| 候选 | 具体可达链 | 具体见证／表达错配 | 合格 Delta 分类 | 升级 |
|---|---|---|---|---|
| C1／O30、O31 | 已建立 | 已建立 | 未知：没有 diff／父版本 | 否 |

No call-chain defects found based on contract changes, obligation ledger, and verified evidence-gating.

这里的零正式发现表示「**冻结角色的变更证据门槛未满足**」，不表示源码正确，也不撤销 C1 的源级证据。

## Mandatory Coverage Check

- **Total modified functions：** 未知；完整源码可见 8 个顶层函数、2 个嵌套函数。
- **Total changed branches / proofs identified：** 未知；补充识别当前源码义务 40 项。
- **Total obligations created：** 40。
- **Obligations fully verified：** 完成源码静态网格 40 项；完成包含父子版本比较的完整验证 0 项。
- **Candidate-defect obligations：** O30、O31，共同对应 1 个源级候选。
- **Closed-no-defect obligations：** O1–O29、O32–O40；仅表示限定证据下未建立独立缺陷，不证明历史行为或完整集成正确。
- **Unreviewed changed branches：** 无法识别；无 diff／历史。上述当前源码账本不存在未处理义务。
- **只读调用次数：** 3 次，含 1 次 `rtk --help`、1 次冻结角色提取、1 次需求／完整源码／tasks／scope 读取。
- **执行待审源码／写文件／访问外部来源：** 均无。
