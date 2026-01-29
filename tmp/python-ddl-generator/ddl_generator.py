"""
SQL建表语句生成器 - Python版本
支持多数据库类型DDL生成
"""

from typing import Dict, List, Optional
import re

# 数据库配置
DATABASE_CONFIGS = {
    'spark': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
    },
    'mysql': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
        'add_primary_key': True,
        'add_engine': True,
    },
    'postgresql': {
        'create_table_prefix': 'CREATE TABLE',
        'comment_syntax': 'SEPARATE',
    },
    'starrocks': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
    },
    'clickhouse': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
    },
    'hive': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
    },
    'doris': {
        'create_table_prefix': 'CREATE TABLE IF NOT EXISTS',
        'comment_syntax': 'INLINE',
    },
}

DATABASE_LABELS = {
    'spark': 'Spark SQL',
    'mysql': 'MySQL',
    'postgresql': 'PostgreSQL',
    'starrocks': 'StarRocks',
    'clickhouse': 'ClickHouse',
    'hive': 'Hive',
    'doris': 'Doris',
}


class FieldInfo:
    """字段信息"""
    def __init__(self, name: str, alias: Optional[str] = None, comment: str = ''):
        self.name = name
        self.alias = alias
        self.comment = comment


class TypeRule:
    """类型映射规则"""
    def __init__(self, id: str, keywords: List[str], data_type: str, priority: int):
        self.id = id
        self.keywords = keywords
        self.data_type = data_type
        self.priority = priority


def parse_sql_fields(sql: str) -> List[FieldInfo]:
    """解析SQL，提取字段信息"""
    fields = []
    trimmed_sql = sql.strip()

    # 策略1: 尝试解析标准 SELECT ... FROM
    if 'SELECT' in trimmed_sql.upper():
        result = try_parse_select_from(trimmed_sql)
        if result:
            return result

    # 策略2: 解析 SELECT 后的字段列表（无FROM）
    if 'SELECT' in trimmed_sql.upper():
        result = try_parse_select_fields(trimmed_sql)
        if result:
            return result

    # 策略3: 解析纯字段列表
    result = try_parse_field_list(trimmed_sql)
    if result:
        return result

    raise ValueError('无法解析SQL，请确保输入的是有效的SELECT查询或字段列表')


def try_parse_select_from(sql: str) -> Optional[List[FieldInfo]]:
    """尝试解析标准 SELECT ... FROM 语句"""
    # 找到FROM关键字（考虑括号）
    paren_count = 0
    select_start = -1
    from_pos = -1

    # 查找SELECT
    select_match = re.search(r'\bSELECT\b', sql, re.IGNORECASE)
    if not select_match:
        return None

    select_start = select_match.end()

    # 查找FROM
    for i in range(select_start, len(sql)):
        char = sql[i]

        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        elif paren_count == 0 and sql[i:i+4].upper() == 'FROM':
            # 检查FROM是否是独立单词
            if i + 4 >= len(sql) or sql[i+4].isspace():
                if i == 0 or sql[i-1].isspace():
                    from_pos = i
                    break

    if from_pos == -1:
        return None

    select_clause = sql[select_start:from_pos].strip()
    return parse_select_clause(select_clause)


def try_parse_select_fields(sql: str) -> Optional[List[FieldInfo]]:
    """解析SELECT后无FROM的字段列表"""
    select_match = re.search(r'\bSELECT\b', sql, re.IGNORECASE)
    if not select_match:
        return None

    select_start = select_match.end()
    select_clause = sql[select_start:].strip()

    # 移除WHERE, GROUP BY, ORDER BY等
    stop_keywords = ['WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION']
    for keyword in stop_keywords:
        keyword_match = re.search(f'\\b{keyword}\\b', select_clause, re.IGNORECASE)
        if keyword_match:
            select_clause = select_clause[:keyword_match.start()].strip()
            break

    return parse_select_clause(select_clause)


def try_parse_field_list(sql: str) -> Optional[List[FieldInfo]]:
    """解析纯字段列表"""
    # 移除注释
    clean_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', '', clean_sql, flags=re.DOTALL)
    clean_sql = clean_sql.strip()

    # 按逗号分割（考虑括号）
    field_expressions = []
    current = []
    paren_count = 0

    for char in clean_sql:
        if char == '(':
            paren_count += 1
            current.append(char)
        elif char == ')':
            paren_count -= 1
            current.append(char)
        elif char == ',' and paren_count == 0:
            field_expressions.append(''.join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        field_expressions.append(''.join(current).strip())

    # 解析每个字段
    fields = []
    for expr in field_expressions:
        field = parse_field_expression(expr)
        if field:
            fields.append(field)

    return fields


def parse_select_clause(select_clause: str) -> List[FieldInfo]:
    """解析SELECT子句"""
    fields = []

    # 提取注释
    comment_map = {}
    lines = select_clause.split('\n')
    for line in lines:
        comment_match = re.search(r'--\s*(.+)$', line)
        if comment_match:
            comment = comment_match.group(1).strip()
            field_part = line[:comment_match.start()].strip()
            if field_part:
                normalized_key = field_part.lstrip(',').strip()
                comment_map[normalized_key] = comment

    # 移除注释
    clean_clause = re.sub(r'--.*$', '', select_clause, flags=re.MULTILINE)
    clean_clause = re.sub(r'/\*.*?\*/', '', clean_clause, flags=re.DOTALL)

    # 分割字段
    field_expressions = split_fields(clean_clause)

    for expr in field_expressions:
        field = parse_field_expression(expr, comment_map)
        if field:
            fields.append(field)

    return fields


def split_fields(select_clause: str) -> List[str]:
    """分割字段（考虑括号）"""
    field_expressions = []
    current = []
    paren_count = 0

    for char in select_clause:
        if char == '(':
            paren_count += 1
            current.append(char)
        elif char == ')':
            paren_count -= 1
            current.append(char)
        elif char == ',' and paren_count == 0:
            field_expressions.append(''.join(current).strip())
            current = []
        else:
            current.append(char)

    if current:
        field_expressions.append(''.join(current).strip())

    return field_expressions


def parse_field_expression(expr: str, comment_map: Optional[Dict[str, str]] = None) -> Optional[FieldInfo]:
    """解析字段表达式"""
    expr = expr.strip()

    # 跳过子查询
    if 'SELECT' in expr.upper() or ' FROM ' in expr.upper():
        return None

    if comment_map is None:
        comment_map = {}

    # 移除DISTINCT
    expr = re.sub(r'\bDISTINCT\s+', '', expr, flags=re.IGNORECASE)

    # 查找AS别名
    alias_match = re.search(r'\s+AS\s+([^\s,]+)$', expr, re.IGNORECASE)
    if alias_match:
        main_expr = expr[:alias_match.start()].strip()
        alias = alias_match.group(1).strip("'\"")
        name = main_expr
    else:
        # 简单判断最后一个空格后的部分是否是别名
        parts = expr.split()
        if len(parts) > 1:
            # 检查是否是简单别名
            last_part = parts[-1].strip("'\"")
            if not any(op in parts[-2] for op in ['(', '+', '-', '*', '/', '=']):
                name = ' '.join(parts[:-1])
                alias = last_part
            else:
                name = expr
                alias = None
        else:
            name = expr
            alias = None

    # 使用别名作为字段名
    field_name = alias or name

    # 获取注释
    comment = comment_map.get(name, field_name)

    return FieldInfo(name=field_name, alias=alias, comment=comment)


def infer_field_type(field_name: str, custom_rules: Optional[List[TypeRule]] = None) -> str:
    """推断字段类型"""
    name = field_name.lower()

    # 自定义规则
    if custom_rules:
        sorted_rules = sorted(custom_rules, key=lambda x: x.priority)
        for rule in sorted_rules:
            for keyword in rule.keywords:
                if name == keyword.lower() or keyword.lower() in name:
                    return rule.data_type

    # 默认规则
    # 币种代码
    if name in ['fcytp', 'scytp', 'cytp', 'currency_type'] or '币种代码' in name:
        return 'STRING'

    # 模式、代码
    if 'mode' in name or 'code' in name or 'icode' in name:
        return 'STRING'

    # 日期
    if 'date' in name or '日期' in name:
        if 'day' not in name and 'days' not in name:
            return 'DATE'

    # 时间
    if 'time' in name or 'timestamp' in name or '时间' in name:
        return 'TIMESTAMP'

    # 组织、客户、人员
    if any(k in name for k in ['org', 'trcl', 'cust', 'stff', 'user', 'dept']):
        return 'STRING'

    # 名称
    if any(k in name for k in ['_name', '_dscr', '_rmrk', 'name', '描述', '备注']):
        return 'STRING'

    # 标记
    if 'flag' in name or name.startswith('is_') or '标记' in name:
        return 'STRING'

    # 天数
    if 'days' in name or ('day' in name and name != 'weekday'):
        return 'DECIMAL(24, 6)'

    # 金额
    if any(k in name for k in ['amt', 'amount', 'price', 'ocy', 'rcy', 'scy', 'elmn', 'crdt', 'totl', 'ocpt', '金额']):
        return 'DECIMAL(24, 6)'

    # 数量
    if any(k in name for k in ['qty', 'quantity', 'cnt', 'count', '数量']):
        return 'DECIMAL(24, 6)'

    return 'STRING'


def map_data_type_for_database(data_type: str, database_type: str) -> str:
    """将通用类型映射到特定数据库"""
    if database_type == 'clickhouse':
        if data_type == 'STRING':
            return 'String'
        if data_type == 'DATE':
            return 'Date'
        if data_type == 'TIMESTAMP':
            return 'DateTime'
        if data_type.startswith('DECIMAL'):
            return data_type.replace('DECIMAL', 'Decimal')

    if database_type == 'postgresql':
        if data_type == 'STRING':
            return 'TEXT'
        if data_type == 'TIMESTAMP':
            return 'TIMESTAMP'

    return data_type


def select_primary_key(fields: List[FieldInfo]) -> Optional[str]:
    """选择主键字段"""
    if not fields:
        return None

    # 规则1: 优先选择后缀为icode的字段
    icode_field = next((f for f in fields if f.name.lower().endswith('icode')), None)
    if icode_field:
        return icode_field.name

    # 规则2: 选择后缀为id的字段（非icode）
    id_field = next(
        (f for f in fields if f.name.lower().endswith('id') and not f.name.lower().endswith('icode')),
        None
    )
    if id_field:
        return id_field.name

    # 规则3: 选择第一个字段
    return fields[0].name


def generate_ddl(
    fields: List[FieldInfo],
    custom_rules: Optional[Dict[str, List[TypeRule]]] = None,
    database_type: str = 'spark'
) -> str:
    """生成DDL语句"""
    if custom_rules is None:
        custom_rules = {}

    config = DATABASE_CONFIGS.get(database_type, DATABASE_CONFIGS['spark'])

    # 计算对齐宽度
    max_name_length = max((len(f.name) for f in fields), default=0) or 30
    max_type_length = 18

    # 获取自定义规则
    db_rules = custom_rules.get(database_type, [])

    # 调整数据类型
    adjusted_fields = []
    for field in fields:
        field_type = infer_field_type(field.name, db_rules)
        mapped_type = map_data_type_for_database(field_type, database_type)
        adjusted_fields.append({
            'name': field.name,
            'type': mapped_type,
            'comment': field.comment
        })

    # 生成DDL
    ddl_parts = [f"{config['create_table_prefix']} 表名 ("]

    for idx, field in enumerate(adjusted_fields):
        padded_name = field['name'].ljust(max_name_length)
        padded_type = field['type'].ljust(max_type_length)
        comment_text = f"COMMENT '{field['comment'].replace(\"'\", \"''\")}'"

        if idx == 0:
            ddl_parts.append(f"    {padded_name} {padded_type} {comment_text}")
        else:
            ddl_parts.append(f"   ,{padded_name} {padded_type} {comment_text}")

    # 添加主键（MySQL）
    if config.get('add_primary_key'):
        primary_key = select_primary_key(fields)
        if primary_key:
            ddl_parts.append(f"   ,PRIMARY KEY ({primary_key})")

    ddl_parts.append(")")

    # 添加ENGINE和COMMENT
    if config['comment_syntax'] == 'INLINE':
        if config.get('add_engine'):
            ddl_parts.append(" ENGINE=InnoDB")
        ddl_parts.append(" COMMENT ''")
    elif config['comment_syntax'] == 'SEPARATE':
        ddl_parts.append(";")
        ddl_parts.append("")
        ddl_parts.append("COMMENT ON TABLE 表名 IS '';")
        for field in adjusted_fields:
            ddl_parts.append(f"COMMENT ON COLUMN 表名.{field['name']} IS '{field['comment'].replace(\"'\", \"''\")}';")

    return '\n'.join(ddl_parts)


def generate_multiple_ddls(
    fields: List[FieldInfo],
    custom_rules: Dict[str, List[TypeRule]],
    database_types: List[str]
) -> Dict:
    """为多个数据库类型生成DDL"""
    ddls = []

    for db_type in database_types:
        if db_type in DATABASE_CONFIGS:
            ddl = generate_ddl(fields, custom_rules, db_type)
            ddls.append({
                'databaseType': db_type,
                'label': DATABASE_LABELS.get(db_type, db_type.upper()),
                'ddl': ddl
            })

    # 单个数据库返回简单格式
    if len(ddls) == 1:
        return {'ddl': ddls[0]['ddl']}

    # 多个数据库返回数组格式
    return {'ddls': ddls}
