# 使用示例

## 示例 1：基本扫描

### 输入

用户在工作目录包含 `src/` 的 Java 项目中呼叫技能：

```
帮我分析一下这个 Java 项目的重复代码
```

### Agent 执行

1. 运行扫描命令：
   ```bash
   npx jscpd "src/" --pattern "**/*.java" --min-tokens 100 --reporters json --output .jscpd-report
   ```

2. 读取 `.jscpd-report/jscpd-report.json`

3. 发现 3 个重复项，筛选出 Top 2

4. 读取源码，分析业务逻辑

### 输出

```markdown
## Java 代码重复分析报告

### 概览
- **重复块数量**: 3 个
- **总重复行数**: 89 行
- **扫描范围**: src/ 目录

### 严重重复项（Top 2）

#### 1. UserService 与 AdminService 的权限验证重复
- **文件**: `src/com/example/service/UserService.java` (行 45-78) ↔ `src/com/example/service/AdminService.java` (行 52-85)
- **重复行数**: 34 行
- **业务逻辑**: 用户权限验证和角色检查的重复实现
- **重构方案**: 
  ```java
  // 提取到 AuthUtils.java
  public class AuthUtils {
      public static boolean validateUser(User user, Context context) {
          if (user == null || context == null) {
              return false;
          }
          Role role = user.getRole();
          return role.hasPermission(context.getRequiredPermission());
      }
  }
  ```

#### 2. OrderService 与 PaymentService 的参数验证重复
- **文件**: `src/com/example/service/OrderService.java` (行 120-145) ↔ `src/com/example/service/PaymentService.java` (行 80-105)
- **重复行数**: 26 行
- **业务逻辑**: 请求参数非空校验的重复实现
- **重构方案**:
  ```java
  // 提取到 ValidationUtils.java
  public class ValidationUtils {
      public static void validateNotNull(Object obj, String fieldName) {
          if (obj == null) {
              throw new IllegalArgumentException(fieldName + " cannot be null");
          }
      }
  }
  ```

### 建议

1. 优先处理 UserService/AdminService 的权限验证重复（影响范围更广）
2. 使用 AuthUtils 工具类提取通用权限验证逻辑
3. 重构后运行单元测试确保功能正常
```

---

## 示例 2：基本扫描 + 报告生成

### 输入

用户在工作目录包含 `src/` 的 Java 项目中呼叫技能：

```
帮我分析一下这个 Java 项目的重复代码
```

### Agent 执行

1. 运行扫描命令：
   ```bash
   npx jscpd "src/" --pattern "**/*.java" --min-tokens 100 --reporters json --output .jscpd-report
   ```

2. 生成 Markdown 报告：
   ```bash
   python scripts/generate_report.py .jscpd-report/jscpd-report.json ./java-duplicate-report.md
   ```

3. 生成 Excel 报告：
   ```bash
   python scripts/generate_excel.py .jscpd-report/jscpd-report.json ./java-duplicate-report.xlsx
   ```

4. 输出文件路径给用户

5. 清理临时目录：
   ```bash
   rm -rf .jscpd-report
   ```

### 输出

```
✅ 分析完成！

📊 报告已生成：
- Markdown 报告: ./java-duplicate-report.md
- Excel 详细报告: ./java-duplicate-report.xlsx
```

---

## 示例 3：自定义扫描参数

### 输入

```
我的 Java 代码在 app/ 目录下，帮我用更严格的参数扫描（min-tokens 150）
```

### Agent 执行

1. 运行扫描命令：
   ```bash
   npx jscpd "app/" --pattern "**/*.java" --min-tokens 150 --reporters json --output .jscpd-report
   ```

2. 读取报告并分析

### 输出

```markdown
## Java 代码重复分析报告

### 概览
- **重复块数量**: 1 个
- **总重复行数**: 45 行
- **扫描范围**: app/ 目录
- **扫描参数**: min-tokens 150

### 重复项详情

#### 1. 订单处理逻辑重复
- **文件**: `app/src/main/java/com/example/order/OrderController.java` (行 30-65) ↔ `app/src/main/java/com/example/payment/PaymentController.java` (行 25-60)
- **重复行数**: 36 行
- **业务逻辑**: 订单和支付的金额计算逻辑重复
- **重构方案**:
  ```java
  // 提取到 AmountCalculator.java
  public class AmountCalculator {
      public static BigDecimal calculate(final BigDecimal baseAmount, 
                                          final BigDecimal discount, 
                                          final BigDecimal tax) {
          BigDecimal afterDiscount = baseAmount.subtract(discount);
          return afterDiscount.multiply(tax.add(BigDecimal.ONE));
      }
  }
  ```

### 建议

1. 建议抽取金额计算工具类 AmountCalculator
2. 两个 Controller 共同调用该工具类
3. 重构后运行单元测试确保金额计算正确
```

---

## 示例 4：Excel 报告内容

当用户打开生成的 Excel 报告时，会看到以下内容：

### 工作表 1：概览统计

| 指标 | 数值 |
|------|------|
| 扫描时间 | 2026-04-30T06:47:23.663Z |
| 重复块数量 | 835 个 |
| 总重复行数 | 14,936 行 |
| 扫描范围 | hss-domain/src 目录 |

### 工作表 2：重复代码明细

| 序号 | 第一个文件 | 第二个文件 | 第一个文件行号 | 第二个文件行号 | 重复行数 | 严重程度 | 重构建议 |
|------|------------|------------|----------------|----------------|----------|----------|----------|
| 1 | hss-domain\src\main\java\...\PerformanceDetailScoreValidatorTest.java | hss-domain\src\main\java\...\PerformanceScoreValidatorTest.java | 43-314 | 48-319 | 272 | 严重 | 建议提取公共基类或工具类 |
| 2 | hss-domain\src\main\java\...\ImageOcrAndDimensionVO.java | hss-domain\src\main\java\...\ImageOcrAndImageInfoVO.java | 24-242 | 22-215 | 219 | 严重 | 建议提取公共基类或工具类 |
| ... | ... | ... | ... | ... | ... | ... | ... |

### 工作表 3：Top 10 严重重复

与"重复代码明细"类似，但仅包含最严重的 10 个重复项。

---

## 示例 5：无重复代码

### 输入

```
帮我检查一下这个项目的代码重复情况
```

### Agent 执行

1. 运行扫描命令
2. 读取报告，发现没有重复项

### 输出

```markdown
## Java 代码重复分析报告

### 概览
- **重复块数量**: 0 个
- **总重复行数**: 0 行
- **扫描范围**: src/ 目录

### 结论

🎉 太棒了！您的代码非常整洁，没有发现明显的重复代码！

### 建议

1. 继续保持良好的编码习惯
2. 定期使用此工具进行代码质量检查
3. 如有新增代码模块，建议再次扫描确认
```

---

## 示例 6：小型重复代码（不推荐重构）

### 输入

```
帮我分析一下这个 Java 项目
```

### Agent 执行

1. 运行扫描命令
2. 读取报告，发现 2 个重复项，但行数都较少

### 输出

```markdown
## Java 代码重复分析报告

### 概览
- **重复块数量**: 2 个
- **总重复行数**: 24 行
- **扫描范围**: src/ 目录

### 重复项详情

#### 1. 日志打印语句重复
- **文件**: `UserService.java` (行 10-12) ↔ `OrderService.java` (行 8-10)
- **重复行数**: 3 行
- **业务逻辑**: 简单的日志打印语句
- **建议**: 暂不重构，保持观察（行数太少，重构收益不高）

#### 2. 空值检查重复
- **文件**: `UserService.java` (行 25-28) ↔ `ProductService.java` (行 30-33)
- **重复行数**: 4 行
- **业务逻辑**: 基础的非空校验
- **建议**: 暂不重构，保持观察（这是常见的样板代码）

### 结论

检测到的重复代码行数较少（< 20 行），且业务逻辑相对简单。建议暂不进行重构，保持观察即可。

### 后续建议

1. 持续关注代码演进，后续如有新增重复再评估
2. 可考虑使用 IDE 的代码检查插件进行实时监控
3. 建议定期（如每季度）进行一次代码重复扫描
```