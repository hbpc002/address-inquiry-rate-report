from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.models.database import init_db
from app.api import auth, employees, shift_types, schedules, checkins, reports, system, users
from app.models.database import SessionLocal
import asyncio
import traceback
from datetime import datetime, timedelta
from app.models.operation_log import OperationLog
try:
    from app.models.app_config import AppConfig
    _HAS_DB_CONFIG = True
except Exception:
    _HAS_DB_CONFIG = False
    _autoclean_config = {'enabled': True, 'retention_days': 90}
from app.utils.logger import log_operation
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_tags=[
        {"name": "认证", "description": "认证相关接口"},
        {"name": "员工管理", "description": "员工CRUD"},
        {"name": "班次类型管理", "description": "班次类型配置"},
        {"name": "排班管理", "description": "排班相关接口"},
        {"name": "签到记录", "description": "签到记录导入"},
        {"name": "考勤报表", "description": "考勤报表查询"},
        {"name": "用户管理", "description": "系统用户管理"},
    ]
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_trace = traceback.format_exc()
    print(f"全局异常: {error_trace}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(employees.router)
app.include_router(shift_types.router)
app.include_router(schedules.router)
app.include_router(checkins.router)
app.include_router(reports.router)
app.include_router(system.router)
app.include_router(users.router)


@app.on_event("startup")
def startup_event():
    init_db()
    _ensure_defaults()
    # 启动后台日志清理任务
    asyncio.create_task(_log_cleanup_task())

def _ensure_defaults():
    if _HAS_DB_CONFIG:
        try:
            db = SessionLocal()
            try:
                if not db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first():
                    db.add(AppConfig(key='log_autoclean_enabled', value='true'))
                if not db.query(AppConfig).filter(AppConfig.key == 'log_retention_days').first():
                    db.add(AppConfig(key='log_retention_days', value='90'))
                db.commit()
            finally:
                db.close()
        except Exception:
            pass
    else:
        # 使用内存配置的默认值
        global _autoclean_config
        _autoclean_config = {'enabled': True, 'retention_days': 90}

async def _log_cleanup_task():
    while True:
        try:
            if _HAS_DB_CONFIG:
                db = SessionLocal()
                try:
                    en = db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first()
                    enabled = en.value.lower() == 'true' if en and en.value else True
                    r = db.query(AppConfig).filter(AppConfig.key == 'log_retention_days').first()
                    retention_days = int(r.value) if r and r.value and str(r.value).isdigit() else 90
                finally:
                    db.close()
            else:
                enabled = _autoclean_config.get('enabled', True)
                retention_days = _autoclean_config.get('retention_days', 90)

            if enabled:
                cutoff = datetime.utcnow() - timedelta(days=retention_days)
                if _HAS_DB_CONFIG:
                    db2 = SessionLocal()
                    try:
                        db2.query(OperationLog).filter(OperationLog.created_at < cutoff).delete()
                        db2.commit()
                    finally:
                        db2.close()
        except Exception:
            pass
        await asyncio.sleep(60 * 60 * 24)


@app.get("/")
def root():
    return {"message": "排班签到报表系统 API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
