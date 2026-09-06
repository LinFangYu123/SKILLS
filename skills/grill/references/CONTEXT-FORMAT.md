# CONTEXT.md 格式

## 结构

```md
# {上下文名称}

{一两句话：这个上下文是什么、为什么存在。}

## Language

**Order（订单）**:
{一两句话描述这个术语}
_Avoid_: Purchase, transaction

**Invoice（发票）**:
交付后发给客户的付款请求。
_Avoid_: Bill, payment request

**Customer（客户）**:
下单的个人或组织。
_Avoid_: Client, buyer, account
```

## 规则

- **要有主见。** 同一概念存在多个说法时，挑最好的一个作为规范术语，
  其余列在 `_Avoid_` 下
- **定义要紧凑。** 一两句话为限。定义它**是什么**，不是它**做什么**
- **只收本上下文特有的术语。** 通用编程概念（超时、错误类型、工具模式）
  即使项目里用得再多也不收。加术语前先问：这是本上下文独有的概念，
  还是通用编程概念？只有前者属于这里
- **自然成簇时按子标题分组。** 如果所有术语属于同一内聚区域，平铺即可

## 单上下文 vs 多上下文仓库

**单上下文（多数仓库）**：仓库根目录一个 `CONTEXT.md`。

**多上下文**：根目录放一个 `CONTEXT-MAP.md`，列出各上下文的位置及关系：

```md
# Context Map

## Contexts

- [Ordering](./src/ordering/CONTEXT.md): 接收并跟踪客户订单
- [Billing](./src/billing/CONTEXT.md): 生成发票并处理付款
- [Fulfillment](./src/fulfillment/CONTEXT.md): 管理仓库拣货与发货

## Relationships

- **Ordering → Fulfillment**: Ordering 发出 `OrderPlaced` 事件；Fulfillment
  消费后开始拣货
- **Fulfillment → Billing**: Fulfillment 发出 `ShipmentDispatched` 事件；
  Billing 消费后生成发票
- **Ordering ↔ Billing**: 共享 `CustomerId` 与 `Money` 类型
```

判断采用哪种结构：

- 根目录有 `CONTEXT-MAP.md` → 读它定位各上下文
- 只有根目录 `CONTEXT.md` → 单上下文
- 两者都没有 → 第一个术语敲定时，惰性创建根目录 `CONTEXT.md`

多上下文仓库中，推断当前话题属于哪个上下文；不确定就问用户。
