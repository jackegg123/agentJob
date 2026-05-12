# Java 重构最佳实践

本文档提供 Java 代码重构的常用模式和最佳实践。

## 目录

1. [提取方法 (Extract Method)](#1-提取方法-extract-method)
2. [提取工具类 (Extract Util Class)](#2-提取工具类-extract-util-class)
3. [泛型化 (Generics)](#3-泛型化-generics)
4. [模板方法模式 (Template Method)](#4-模板方法模式-template-method)
5. [策略模式 (Strategy)](#5-策略模式-strategy)

---

## 1. 提取方法 (Extract Method)

**适用场景**：同一个类中存在重复代码片段

**示例 - 重构前**：
```java
public class OrderService {
    public void processRegularOrder(Order order) {
        // 验证订单
        if (order.getItems().isEmpty()) {
            throw new IllegalArgumentException("Order is empty");
        }
        for (Item item : order.getItems()) {
            if (item.getQuantity() <= 0) {
                throw new IllegalArgumentException("Invalid quantity");
            }
        }
        // 处理逻辑...
    }
    
    public void processVIPOrder(Order order) {
        // 同样的验证逻辑
        if (order.getItems().isEmpty()) {
            throw new IllegalArgumentException("Order is empty");
        }
        for (Item item : order.getItems()) {
            if (item.getQuantity() <= 0) {
                throw new IllegalArgumentException("Invalid quantity");
            }
        }
        // 处理逻辑...
    }
}
```

**示例 - 重构后**：
```java
public class OrderService {
    public void processRegularOrder(Order order) {
        validateOrder(order);
        // 处理逻辑...
    }
    
    public void processVIPOrder(Order order) {
        validateOrder(order);
        // 处理逻辑...
    }
    
    private void validateOrder(Order order) {
        if (order.getItems().isEmpty()) {
            throw new IllegalArgumentException("Order is empty");
        }
        for (Item item : order.getItems()) {
            if (item.getQuantity() <= 0) {
                throw new IllegalArgumentException("Invalid quantity");
            }
        }
    }
}
```

---

## 2. 提取工具类 (Extract Util Class)

**适用场景**：跨类的通用逻辑

**示例 - 重构前**：
```java
// UserService.java
public boolean isValidEmail(String email) {
    return email != null && email.matches("^[A-Za-z0-9+_.-]+@(.+)$");
}

// AdminService.java
public boolean isValidEmail(String email) {
    return email != null && email.matches("^[A-Za-z0-9+_.-]+@(.+)$");
}
```

**示例 - 重构后**：
```java
// StringUtils.java
public class StringUtils {
    private StringUtils() {}
    
    public static boolean isValidEmail(String email) {
        return email != null && email.matches("^[A-Za-z0-9+_.-]+@(.+)$");
    }
    
    public static boolean isEmpty(String str) {
        return str == null || str.trim().isEmpty();
    }
}

// UserService.java
public boolean isValidEmail(String email) {
    return StringUtils.isValidEmail(email);
}
```

**常见工具类**：
- `StringUtils` - 字符串处理
- `DateUtils` - 日期处理
- `CollectionUtils` - 集合处理
- `ValidationUtils` - 验证逻辑
- `SecurityUtils` - 安全相关

---

## 3. 泛型化 (Generics)

**适用场景**：多个类只是数据类型不同

**示例 - 重构前**：
```java
// IntegerListProcessor.java
public class IntegerListProcessor {
    public List<Integer> filterPositive(List<Integer> numbers) {
        return numbers.stream()
            .filter(n -> n > 0)
            .collect(Collectors.toList());
    }
}

// DoubleListProcessor.java
public class DoubleListProcessor {
    public List<Double> filterPositive(List<Double> numbers) {
        return numbers.stream()
            .filter(n -> n > 0)
            .collect(Collectors.toList());
    }
}
```

**示例 - 重构后**：
```java
// ListProcessor.java
public class ListProcessor<T extends Number> {
    public List<T> filterPositive(List<T> numbers) {
        return numbers.stream()
            .filter(n -> n.doubleValue() > 0)
            .collect(Collectors.toList());
    }
    
    public List<T> filterByCondition(List<T> numbers, Predicate<T> condition) {
        return numbers.stream()
            .filter(condition)
            .collect(Collectors.toList());
    }
}
```

---

## 4. 模板方法模式 (Template Method)

**适用场景**：多个类有相同的算法结构，但某些步骤不同

**示例 - 重构前**：
```java
// FileExporter.java
public void exportToCSV(List<Record> records) {
    connect();
    writeHeader();
    for (Record record : records) {
        writeLine(record);
    }
    disconnect();
}

public void exportToJSON(List<Record> records) {
    connect();
    writeHeader();
    for (Record record : records) {
        writeLine(record);
    }
    disconnect();
}
```

**示例 - 重构后**：
```java
// AbstractExporter.java
public abstract class AbstractExporter {
    public final void export(List<Record> records) {
        connect();
        writeHeader();
        for (Record record : records) {
            writeLine(record);
        }
        disconnect();
    }
    
    protected abstract void connect();
    protected abstract void writeHeader();
    protected abstract void writeLine(Record record);
    protected abstract void disconnect();
}

// CSVExporter.java
public class CSVExporter extends AbstractExporter {
    @Override
    protected void connect() { /* ... */ }
    
    @Override
    protected void writeHeader() { /* ... */ }
    
    @Override
    protected void writeLine(Record record) { /* ... */ }
    
    @Override
    protected void disconnect() { /* ... */ }
}
```

---

## 5. 策略模式 (Strategy)

**适用场景**：需要根据不同条件选择不同算法/行为

**示例 - 重构前**：
```java
public class DiscountCalculator {
    public double calculate(Order order, String type) {
        if ("VIP".equals(type)) {
            return order.getAmount() * 0.9;
        } else if ("NEW".equals(type)) {
            return order.getAmount() * 0.95;
        } else if ("HOLIDAY".equals(type)) {
            return order.getAmount() * 0.8;
        }
        return order.getAmount();
    }
}
```

**示例 - 重构后**：
```java
// DiscountStrategy.java
public interface DiscountStrategy {
    double calculate(Order order);
}

// VIPDiscount.java
public class VIPDiscount implements DiscountStrategy {
    @Override
    public double calculate(Order order) {
        return order.getAmount() * 0.9;
    }
}

// NewCustomerDiscount.java
public class NewCustomerDiscount implements DiscountStrategy {
    @Override
    public double calculate(Order order) {
        return order.getAmount() * 0.95;
    }
}

// DiscountCalculator.java
public class DiscountCalculator {
    private DiscountStrategy strategy;
    
    public void setStrategy(DiscountStrategy strategy) {
        this.strategy = strategy;
    }
    
    public double calculate(Order order) {
        return strategy.calculate(order);
    }
}
```

---

## 重构决策流程

```
发现重复代码
       │
       ▼
┌──────────────────┐
│ 重复代码在哪？    │
└──────────────────┘
       │
  ┌────┴────┐
  ▼         ▼
同一个类   不同类
  │         │
  ▼         ▼
提取方法   跨类的通用逻辑？
  │         │
  │      ┌──┴──┐
  │      ▼     ▼
  │    是    否
  │      │     │
  │      ▼     ▼
  │   工具类  算法结构相同？
  │            │
  │         ┌──┴──┐
  │         ▼     ▼
  │       是    否
  │         │     │
  │         ▼     ▼
  │    模板方法  行为不同？
  │              │
  │           ┌──┴──┐
  │           ▼     ▼
  │         是    否
  │           │     │
  │           ▼     ▼
  │        策略模式 考虑其他模式
```

---

## 何时不建议重构

1. **重复代码行数很少**（如 < 10 行）
2. **业务逻辑确实不同**，只是碰巧代码相似
3. **重构成本高于收益**
4. **代码即将废弃**
5. **团队不熟悉该领域**，可能导致错误

---

## 相关工具

- **jscpd**: Token 级别的复制粘贴检测
- **SonarQube**: 静态代码分析
- **PMD**: Java 代码规则检查
- **SpotBugs**: 字节码级别的 bug 检测