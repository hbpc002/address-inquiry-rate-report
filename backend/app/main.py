from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import init_db
from app.api import auth, employees, shift_types, schedules, checkins, reports, system
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
    ]
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


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {"message": "排班签到报表系统 API"}


@app.get("/health")
def health_check():
    return {"status": "ok"}