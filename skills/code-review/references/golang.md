# Go 审查清单

逐类过检，每类都给出结论（有问题列出，无问题跳过）。
本清单提炼自 Effective Go、Go Code Review Comments 及社区安全清单。

## 1. 缺陷类（🔴）

- **错误被忽略**：`_ = err` 或直接不接返回的 error。必须处理或注释说明为何可忽略
- **error 未 wrap 丢上下文**：`return err` 直接透传丢失发生位置；应 `fmt.Errorf("doing x: %w", err)`，且 `%w` 只包一层、用 `errors.Is/As` 判断
- **goroutine 泄漏**：goroutine 阻塞在无超时的 channel 收发/锁上，永不退出；for 循环里起 goroutine 无退出机制
- **map 并发读写**：多 goroutine 读写同一 map 未加 `sync.Mutex` / 用 `sync.Map` → 直接 panic
- **defer 在循环内**：文件/连接在循环里 defer，句柄堆积到函数结束才释放 → 移入闭包或显式 Close
- **slice 别名共享底层数组**：`append` 意外修改原 slice、sub-slice 持有大数组不释放 → 需要时 `copy` 或 `slices.Clone`
- **range 变量复用**（Go <1.22）：goroutine/闭包捕获循环变量取最终值

## 2. 并发类（🔴/🟡）

- **context 传递**：跨 API/网络/数据库调用的函数未接收 `ctx`；`context.Background()` 该用请求级 ctx 的地方滥用
- **锁粒度与死锁**：持锁时做 IO/回调；两把锁获取顺序不一致
- **`sync.WaitGroup` 用法**：`Add` 在 goroutine 内调用（应在启动前）；Wait 前未覆盖所有路径
- **channel 方向**：生产者消费者应声明单向 channel 类型约束

## 3. 安全类（🔴）

- SQL 拼接 → 注入，必须参数化（`db.Query(sql, args...)`）
- `os/exec` 命令含用户输入未用参数列表形式
- `net/http` 未设超时（缺 `http.Client{Timeout}` / 无 `ReadTimeout` 的 server）
- 路径拼接用户输入未 `filepath.Clean` + 前缀校验（目录穿越）
- 硬编码密钥；日志打印敏感字段

## 4. 隐患类（🟡）

- **性能**：循环内字符串 `+=` 拼接（用 `strings.Builder`）；已知容量 slice/map 不预分配；热路径每请求分配大对象（考虑 `sync.Pool`）
- **接口滥用**：接口定义在使用方而非实现方（Go 惯例）；为单一实现提前抽象
- **`panic` 用于可预期错误**：panic 仅限程序性错误（不可达分支、初始化失败）；可预期错误必须返回 error
- **`init()` 里做重活/隐藏依赖**：初始化顺序难追踪
- **裸返回值**（named return + naked return）在长函数中易错

## 5. 风格类（🔵）

- 命名：`MixedCaps`，导出 `PascalCase`，包内 `camelCase`；包名小写单词不用下划线；缩写保持一致大小写（`URL`/`url`，不 `Url`）
- receiver 命名统一且简短（同一类型的所有方法用同一 receiver 名）
- error 变量 `errXxx` / `ErrXxx`，类型 `XxxError`
- `gofmt`/`go vet` 级别问题零容忍（能查到的不复述，只列 diff）
- 注释以标识符名开头，导出符号有注释
