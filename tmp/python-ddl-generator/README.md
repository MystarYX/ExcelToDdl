# SQL建表语句生成器 - Python版本

基于FastAPI实现的SQL建表语句生成器，支持多种数据库类型。

## 功能特性

- ✅ 支持解析SELECT查询语句
- ✅ 支持纯字段列表输入
- ✅ 自动推断字段类型
- ✅ 支持7种数据库类型：
  - Spark SQL
  - MySQL（带PRIMARY KEY和ENGINE=InnoDB）
  - PostgreSQL
  - StarRocks
  - ClickHouse
  - Hive
  - Doris
- ✅ 自定义字段类型映射规则
- ✅ 多数据库同时生成

## 项目结构

```
python-ddl-generator/
├── ddl_generator.py      # 核心逻辑：SQL解析和DDL生成
├── main.py               # FastAPI应用
├── requirements.txt      # 依赖包
├── static/
│   └── index.html       # 前端页面
└── README.md            # 说明文档
```

## 快速开始

### 1. 安装依赖

```bash
cd /tmp/python-ddl-generator
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务将在 `http://localhost:5000` 启动

### 3. 访问应用

打开浏览器访问：`http://localhost:5000`

## 使用示例

### 输入SQL

```sql
SELECT
  org_id,
  trcl_id,
  cust_id,
  business_date,
  credit_amt,
  quantity
FROM credit_usage_detail
```

### 输出MySQL DDL

```sql
CREATE TABLE IF NOT EXISTS 表名 (
    org_id                         STRING             COMMENT 'org_id'
   ,trcl_id                        STRING             COMMENT 'trcl_id'
   ,cust_id                        STRING             COMMENT 'cust_id'
   ,business_date                  DATE               COMMENT 'business_date'
   ,credit_amt                     DECIMAL(24, 6)     COMMENT 'credit_amt'
   ,quantity                       DECIMAL(24, 6)     COMMENT 'quantity'
   ,PRIMARY KEY (org_id)
) ENGINE=InnoDB COMMENT '';
```

## API接口

### POST /api/generate-ddl

生成DDL语句

**请求体：**
```json
{
  "sql": "SELECT org_id, trcl_id FROM table",
  "rulesByDatabase": {},
  "databaseTypes": ["mysql", "postgresql"]
}
```

**响应：**
```json
{
  "ddls": [
    {
      "databaseType": "mysql",
      "label": "MySQL",
      "ddl": "CREATE TABLE IF NOT EXISTS ..."
    },
    {
      "databaseType": "postgresql",
      "label": "PostgreSQL",
      "ddl": "CREATE TABLE ..."
    }
  ]
}
```

## 核心模块说明

### ddl_generator.py

主要函数：

- `parse_sql_fields(sql)`: 解析SQL，提取字段信息
- `infer_field_type(field_name, custom_rules)`: 推断字段类型
- `map_data_type_for_database(data_type, database_type)`: 类型映射
- `select_primary_key(fields)`: 选择主键字段
- `generate_ddl(fields, custom_rules, database_type)`: 生成DDL语句
- `generate_multiple_ddls(fields, custom_rules, database_types)`: 批量生成DDL

### main.py

FastAPI应用：
- `/`: 主页（HTML界面）
- `/api/generate-ddl`: API接口

## 技术栈

- **后端**: FastAPI 0.104.1
- **服务器**: Uvicorn 0.24.0
- **数据验证**: Pydantic 2.5.0
- **SQL解析**: sqlparse 0.4.4
- **前端**: 原生HTML + JavaScript

## Python vs Node.js 对比

| 特性 | Python版本 | Node.js版本 |
|------|-----------|------------|
| 代码行数 | ~400行 | ~600行 |
| 启动速度 | 较慢 | 较快 |
| 类型安全 | 类型提示 | TypeScript |
| 依赖管理 | pip | pnpm |
| 学习曲线 | 较平缓 | 需要React知识 |
| 性能 | 略低 | 更高 |
| 生态 | 数据科学丰富 | 前端生态强 |

## 生产部署

### 使用Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### 使用Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
```

### 构建和运行

```bash
docker build -t sql-ddl-generator .
docker run -p 5000:5000 sql-ddl-generator
```

## 开发建议

1. **添加更多数据库类型**：在`DATABASE_CONFIGS`中添加配置
2. **自定义类型规则**：通过API传递`rulesByDatabase`参数
3. **优化SQL解析**：可以集成`sqlglot`库获得更强大的解析能力

## 许可证

MIT License
