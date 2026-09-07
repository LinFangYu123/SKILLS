# Rust 审查清单

逐类过检，每类都给出结论（有问题列出，无问题跳过）。
编译器已兜底的部分不重复报，聚焦惯用法与运行时风险。

## 1. 缺陷类（🔴）

- **panic 路径**：非测试代码中 `unwrap()` / `expect()` / 数组索引 / 整数除法 —— 必须改用 `?`、`unwrap_or`、`get()` 或带说明的 `expect("具体不变量")`
- **整数溢出**：release 模式下溢出回绕（非 panic）——计算长度/索引/秒数处用 `checked_*` / `saturating_*` / `wrapping_*` 显式声明意图
- **`as` 窄化截断**：`usize as u32`、`i64 as i32` 静默截断 → 用 `try_into()` 或 `TryFrom`
- **锁中毒/死锁**：同线程重入 `Mutex`；持锁跨 `.await`（非 Send 或阻塞执行器）；锁未覆盖所有共享访问点
- **阻塞异步**：async 上下文中 `std::thread::sleep` / 同步 IO / `Mutex`（应用 tokio 的 sleep/异步 Mutex 或 spawn_blocking）

## 2. unsafe 审查（🔴，有 unsafe 必逐行查）

- 每个 unsafe 块有注释说明**依赖哪些不变量**、为何在此处成立
- 裸指针解引用前判空/对齐/生命周期；切片构造（`from_raw_parts`）长度真实性
- FFI：C 字符串以 NUL 结尾的保证、`CString`/`CStr` 边界转换、内存谁分配谁释放
- 能用安全抽象替代的 unsafe（如 `get_unchecked` → `get`）

## 3. 惯用法（🟡）

- **错误处理**：库用 `thiserror` 定义错误类型，应用用 `anyhow`；`Box<dyn Error>` 混用于需要匹配的场景；`impl Error` 链未保留 source
- **多余 clone**：热路径为绕借用检查 clone 大对象（String/Vec/HashMap）；应借用的地方 `to_owned`/`to_string`
- **`String` vs `&str` / `Vec` vs `&[T]`**：函数参数应取借用而非 owned
- **unwrap_or_default 滥用**：静默吞掉错误场景（该是 `unwrap_or_else` 记日志或 `?`）
- **`ref` / 模式匹配冗余**：match 分支可用 move/借用语义简化；`match true` 反模式

## 4. 并发与 API 设计（🟡）

- `Send`/`Sync` 边界：含 `Rc`/`RefCell` 的类型跨线程传递（编译报错才想起，应提前 `Arc<Mutex<_>>` 设计）
- 公共 API：返回类型暴露内部具体类型（应用 trait object 或 newtype 隔离）；`pub` 该收紧成 `pub(crate)`
- 类型转换 trait（`From`/`TryFrom`）应实现的没实现，导致调用方手写转换

## 5. 风格类（🔵）

- `cargo clippy` 级别问题零容忍（能查到的不复述，只列 diff 与理由）
- 命名：类型/ trait `PascalCase`，函数/变量 `snake_case`，常量 `UPPER_SNAKE`，生命周期短小写
- 模块组织：`mod.rs` 与同名文件混用；公共项缺 doc comment（`///`）
- 测试：核心逻辑无单元测试；`#[cfg(test)]` 内断言用 `assert_eq!` 而非 `assert!(a == b)`
