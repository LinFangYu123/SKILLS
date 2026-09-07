# TypeScript / JavaScript 审查清单

逐类过检，每类都给出结论（有问题列出，无问题跳过）。

## 1. 缺陷类（🔴）

- **`==` 隐式转换**：一律 `===`/`!==`（`null == undefined` 场景除外并注明）
- **`any` 逃逸**：`any` 类型传播导致类型检查失效。外部数据先 `unknown` 再收窄（类型守卫/zod 校验）
- **未处理的 Promise 拒绝**：`async` 函数调用无 await 也无 `.catch()`；`Promise.all` 一个失败全失败未按需用 `allSettled`
- **async 循环串行**：`for...of` 中 `await` 导致串行，可并行场景应 `Promise.all`；反之 forEach + async 不等待是 bug
- **浮点数做等值/金额运算**：金额用分/整数或 decimal 库
- **`NaN` 比较**：`x === x` 恒假判断；排序回调返回 NaN 导致乱序

## 2. 安全类（🔴）

- `innerHTML` / `dangerouslySetInnerHTML` 接未净化输入 → XSS
- `eval` / `new Function` 动态执行
- 硬编码密钥/Token 入库（含前端打包泄露的 API key）
- `postMessage` 不校验 origin；URL 拼接用户输入未编码

## 3. React 专项（命中 React 项目时必查 🔴/🟡）

- **Hook 依赖数组**：缺失依赖读到旧值（stale closure）；对象/数组/函数依赖每次渲染变化导致 effect 疯跑 → 用 `useMemo`/`useCallback` 稳定
- **Effect 清理**：订阅/定时器/事件监听未在 cleanup 中释放；异步 setState 在组件卸载后调用
- **列表 key**：用 index 作 key 且列表会重排/增删
- **条件 Hook**：Hook 在 if/return/循环/嵌套函数中调用，打破调用顺序
- **直接改 state**：`state.x = 1` 或 `arr.push` 后不 set，引用相等跳过渲染

## 4. 隐患类（🟡）

- **null/undefined 边界**：可选链 `?.` 与空值合并 `??` 应用的地方用了 `||`（0/'' 被误吞）
- **switch 不穷尽/无 default**：联合类型 switch 后无 `never` 兜底，新增成员静默漏处理
- **类型断言滥用**：`as` 双重断言绕过检查；`!` 非空断言在运行时可能为空
- **模块卫生**：循环依赖； barrel 文件导出全部导致打包膨胀
- **魔法数字/重复代码块**：三处以上相同逻辑未提取

## 5. 风格类（🔵）

- 命名：变量/函数 camelCase，类型/类 PascalCase，常量 UPPER_SNAKE；
  布尔用 is/has/can 前缀
- `const` 优先；无未使用的导入/变量/导出
- 公共 API 有 JSDoc；复杂类型有显式命名（不内联巨型联合/交叉类型）
- 与项目 tsconfig/eslint 配置一致，不为一致性重写整个文件
