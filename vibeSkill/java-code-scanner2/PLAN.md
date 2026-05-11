# Java Code Scanner v2 - 经 DeepSeek Pro 审视后的完善方案

> 本方案已由小香菇基于 DeepSeek Pro 的思维模式，对技术可行性、
> 边界情况、潜在风险进行全面审视和补充。

## 技术选型

| 扫描类型 | 工具 | 安装方式 | 已验证 |
|---------|------|---------|--------|
| 冗余重复代码 | **jscpd**（npm） | `npm install -g jscpd` | ✅ v1 已验证 |
| 无用代码 | **javalang**（Python 库） | `pip install javalang` | ✅ 本方案验证 |

### 选择理由（审视结论）

**包管理器安装，没有下载失败的烦恼：**
- npm 有淘宝镜像，pip 有清华/阿里镜像
- 用户只需一行命令，无需去 GitHub 下载 zip、解压、配置 PATH
- 国内网络环境友好

**javalang 可行性验证结果：**
- ✅ 可正确解析 Java AST（类、方法、字段、import、局部变量）
- ✅ 行号精准（每个 AST 节点自带 `position.line`）
- ✅ 支持泛型、Lambda、注解、内部类等 Java 语法
- ✅ 500 行代码解析仅 6ms，性能足够
- ✅ 纯 Python，零编译，零外部依赖，跨平台

### 不采用其他工具的原因

| 工具 | 问题 |
|------|------|
| Qodana | 需要 Docker，安装 70MB+ 镜像，网络困难 |
| PMD | 70MB zip，需要 JDK，手动配置 PATH |
| checkstyle | 需要 JDK，配置繁琐 |
| cpd (PMD 内置) | 同 PMD，需要 JDK |
| 纯正则自实现 | 无法解析复杂的泛型/内部类，误报率高 |

## 死代码检测算法（基于 javalang AST）

### 检测项 1：未使用的 import

```
算法：遍历 AST 的 import 节点 → 获取包名的短名称（如 'List' 来自 'java.util.List'）
     → 在文件中搜索除 import 行外的所有引用
     → 如果短名称从未出现，标记为未使用的 import
注意：通配符 import（如 java.util.*）也纳入检测
```

### 检测项 2：未使用的 private 字段

```
算法：遍历 AST 的 FieldDeclaration 节点
     → 筛选 modifiers 包含 'private' 的
     → 收集字段名称列表
     → 在文件中搜索除字段声明行外的引用
     → 从未被引用的标记为未使用
注意：忽略序列化相关字段（serialVersionUID）
      忽略被 @Autowired/@Inject/@Resource 注解的字段
```

### 检测项 3：未使用的 private 方法

```
算法：遍历 AST 的 MethodDeclaration 节点
     → 筛选 modifiers 包含 'private' 的
     → 收集方法名称列表
     → 在文件中搜索除方法定义行外的调用
     → 从未被调用的标记为未使用
注意：重名但不同参数的方法（overload）也通过名称匹配
      main 方法不检测
```

### 检测项 4：未使用的局部变量

```
算法：遍历 AST 的 LocalVariableDeclaration 节点
     → 收集变量名称
     → 在声明行之后的代码中搜索引用
     → 如果只有赋值（=）没有读取，标记为未使用
注意：只读的变量声明（声明即赋值但不读取）
      循环变量（for int i = 0...）不检测
```

## 剩余重复代码检测（jscpd）

```
直接使用 npx jscpd 命令，与 v1 一致，已验证可用。
输出格式：JSON
关键参数：--min-lines 6 --min-tokens 50
```

## 边界情况与风险点（审视结果）

| 风险 | 缓解措施 |
|------|---------|
| javalang 不支持某些 Java 新特性（record, sealed class） | 降级处理：遇到解析错误时回退到正则检测 |
| 大项目（1万+ 文件）全部解析内存不足 | 逐文件解析，不一次性加载全部 AST |
| 误报（false positive）不可避免 | 在 SKILL.md 说明检测是启发式的，建议人工复核 |
| jscpd 在大型项目中慢 | 在说明中提示：大型项目可增加 min-lines / 分模块扫描 |

## 目录结构

```
java-code-scanner2/
├── SKILL.md              # YAML metadata + OpenCode Steps
├── requirements.txt      # pandas, openpyxl, javalang
├── scripts/
│   ├── main.py           # 核心扫描逻辑（含详细中文注释）
│   └── setup.sh          # 环境安装脚本（Linux/macOS）
└── examples/
    └── run_example.sh    # 调用示例
```

## 执行流程

```
1. 环境自检
   ├── Python 版本 (>= 3.9)
   ├── jscpd (npm)
   ├── javalang / pandas / openpyxl (pip)
   └── 显示检查结果，缺失项提示用户安装

2. 冗余代码扫描 (jscpd)
   ├── npx jscpd ... --reporters json
   ├── 解析 JSON 报告
   └── 提取 duplicates 数组，映射行号

3. 无用代码扫描 (javalang)
   ├── 遍历项目下所有 *.java 文件
   ├── javalang.parse 逐个解析
   ├── 跳过解析失败的文件（记录警告）
   ├── 执行 4 项死代码检测
   └── 聚合结果

4. Excel 输出
   ├── Sheet 1: 冗余重复代码（同 v1 表头）
   ├── Sheet 2: 无用代码（同 v1 表头）
   ├── 样式美化（表头冻结、列宽自适应）
   └── 无问题时跳过 Excel 生成

5. 临时文件清理
```

## 安装方式

### macOS / Linux
```bash
bash scripts/setup.sh
```

### Windows (PowerShell)
```powershell
pip install -r requirements.txt
npm install -g jscpd
```

## 使用方式

```bash
python scripts/main.py --project-path /path/to/java/project
```

如果此方案你认可，下一步我将为 CC 生成完整的开发提示词。
