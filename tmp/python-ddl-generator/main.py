"""
SQL建表语句生成器 - FastAPI应用
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from ddl_generator import parse_sql_fields, generate_multiple_ddls, TypeRule

app = FastAPI(title="SQL建表语句生成器", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class GenerateDDLRequest(BaseModel):
    sql: str
    rulesByDatabase: Optional[Dict[str, List[TypeRule]]] = {}
    databaseTypes: Optional[List[str]] = ['spark']


# 主页
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


# API路由
@app.post("/api/generate-ddl")
async def generate_ddl(request: GenerateDDLRequest):
    """生成DDL语句"""
    try:
        if not request.sql or not request.sql.strip():
            raise HTTPException(status_code=400, detail="请提供有效的SQL查询语句")

        # 解析SQL字段
        fields = parse_sql_fields(request.sql)

        if not fields:
            raise HTTPException(status_code=400, detail="未能从SQL中解析出字段")

        # 验证数据库类型
        valid_types = [db for db in request.databaseTypes if db in request.rulesByDatabase.keys() or db in ['spark', 'mysql', 'postgresql', 'starrocks', 'clickhouse', 'hive', 'doris']]

        if not valid_types:
            raise HTTPException(status_code=400, detail="请提供至少一个有效的数据库类型")

        # 生成DDL
        result = generate_multiple_ddls(fields, request.rulesByDatabase, valid_types)

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成建表语句失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
