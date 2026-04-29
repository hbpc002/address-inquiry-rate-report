FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -c "
from app.models.database import SessionLocal, engine
from app.models import user
user.Base.metadata.create_all(bind=engine)

from app.models.user import User
from app.core.security import get_password_hash, verify_password

db = SessionLocal()
admin = db.query(User).filter(User.username == 'admin').first()
if not admin:
    admin = User(username='admin', password_hash=get_password_hash('admin123'), role='admin')
    db.add(admin)
    db.commit()
    print('Created admin user')
else:
    print('Admin user already exists')
db.close()
"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]