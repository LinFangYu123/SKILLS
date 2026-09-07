# Java 审查清单

逐类过检，每类都给出结论（有问题列出，无问题跳过）。

## 1. 缺陷类（🔴）

- **equals/hashCode 契约**：重写 equals 未重写 hashCode → HashMap/HashSet 行为错误；equals 未满足自反/对称/传递
- **浮点数做金额**：`double`/`float` 表示货币 → 精度丢失，用 `BigDecimal`（且用字符串构造，不用 double 构造）
- **`==` 比较对象**：Integer/String 用 `==` 比较（缓存区间内碰巧正确，区间外错误）
- **异常被吞**：`catch (Exception e) {}` 空块或仅打印不处理；catch 后返回默认值掩盖错误
- **资源未关闭**：流/连接/锁未用 try-with-resources
- **迭代时修改**：遍历集合时 `remove`/`add` → ConcurrentModificationException，用 `Iterator.remove` 或 `removeIf`
- **并发误用**：`SimpleDateFormat` 共享（线程不安全）；double-checked locking 无 volatile；HashMap 多线程共享

## 2. 安全类（🔴）

- SQL 拼接（`Statement` + 字符串拼接）→ 必须 `PreparedStatement` 参数化
- 反序列化不可信数据（原生 `ObjectInputStream` / 脆弱 JSON 库配置）
- `Runtime.exec` / `ProcessBuilder` 命令含用户输入
- 硬编码密钥/口令；`MessageDigest` 用 MD5/SHA1 做安全用途
- XML 解析未禁外部实体（XXE）

## 3. 空安全与异常设计（🟡）

- **NPE 高危点**：链式调用无判空；`Map.get` 直接 `.method()`；自动拆箱 `Integer` 为 null 时 NPE
- **Optional 使用**：字段/参数用 Optional（应只作返回类型）；`optional.get()` 无 isPresent 检查
- **异常粒度**：catch Exception 一把抓吞掉InterruptedException；自定义异常无类型层次；用异常做流程控制
- **受检异常滥用**：包装后层层抛 SQLException 等底层异常污染上层接口

## 4. 隐患类（🟡）

- **性能**：循环内字符串 `+` 拼接（用 StringBuilder）；循环内 `list.contains`（O(n²)，用 Set）；在热点路径创建大对象
- **可变性问题**：该不可变的类（值对象/作 Map key）字段可变；返回内部可变集合/数组的直接引用（应 `List.copyOf`/clone）
- **泛型**：raw type（`List` 而非 `List<String>`）；`@SuppressWarnings("unchecked")` 无注释理由
- **过度设计**：只有一个实现的接口 + 工厂 + 抽象基类三层套娃

## 5. 风格类（🔵）

- 命名：类 `PascalCase`，方法/变量 `camelCase`，常量 `UPPER_SNAKE`；
  避免单字母（循环索引除外）
- 一个 public 类一个文件；方法 >50 行 / 类 >400 行考虑拆分
- 公共方法有 Javadoc（含参数/返回/抛出）；`@Override` 注解不省略
- 与项目既有惯例一致（Lombok/记录类/构造风格）
