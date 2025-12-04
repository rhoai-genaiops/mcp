from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional
import configparser
import database_handler
import method
import os
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

config = configparser.ConfigParser()
config.read('db.conf')
info = config['DEFAULT']

# Use DATABASE_PATH environment variable if available, otherwise use db.conf
db_path = os.getenv('DATABASE_PATH')
if db_path:
    # Remove .db extension if present in the path, as DatabaseHandler will handle it
    db_name = db_path.replace('.db', '')
else:
    db_name = info['db_name']

dbh = database_handler.DatabaseHandler(db_name=db_name, check_same_thread=False)

# Ensure the table exists on startup
columns = json.loads(info['columns'])
dbh.create_table(table_name=info['table_name'], columns=columns)

m = method.Method(conf_file='db.conf')

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # The origin of your React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

class Schedule(BaseModel):
    sid: str
    user_id: Optional[str] = None
    name: str
    content: str
    category: str
    level: int
    status: float
    creation_time: str
    start_time: str
    end_time: str

def get_user_from_headers(request: Request) -> Optional[str]:
    """Extract user ID from OpenShift OAuth proxy headers or X-User-ID header."""
    # Try OpenShift OAuth proxy header first
    user_id = request.headers.get('X-Forwarded-User')
    if not user_id:
        # Fall back to custom header for development
        user_id = request.headers.get('X-User-ID')
    if not user_id:
        # Fall back to basic auth username for development
        user_id = request.headers.get('X-Remote-User')
    return user_id

@app.get('/')
def index():
    return {'app_name': 'calendar'}

@app.get('/schedules')
def get_schedules(request: Request):
    user_id = get_user_from_headers(request)
    if user_id:
        # Filter by user_id for multi-tenant support
        return dbh.fetch_data(info['table_name'], condition={'user_id': user_id})
    else:
        # Return all schedules if no user context (for backward compatibility)
        return dbh.fetch_data(info['table_name'])

@app.get('/schedules/{schedule_id}')
def get_schedule(schedule_id: str, request: Request):
    user_id = get_user_from_headers(request)
    schedule = m.get(dbh, schedule_id, user_id=user_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

@app.post('/schedules')
def create_schedule(schedule: Schedule, request: Request):
    user_id = get_user_from_headers(request)
    if not m.post(dbh, schedule, user_id=user_id):
        raise HTTPException(status_code=400, detail="Schedule already exists or invalid data")
    # Return the schedule with the user_id set
    response = schedule.dict()
    if user_id:
        response['user_id'] = user_id
    return response

@app.put('/schedules/{schedule_id}')
def update_schedule(schedule_id: str, schedule: Schedule, request: Request):
    user_id = get_user_from_headers(request)
    if not m.update(dbh, schedule_id, schedule, user_id=user_id):
        raise HTTPException(status_code=404, detail="Schedule not found or invalid data")
    # Return the schedule with the user_id set
    response = schedule.dict()
    if user_id:
        response['user_id'] = user_id
    return response

@app.delete('/schedules/{schedule_id}')
def delete_schedule(schedule_id: str, request: Request):
    user_id = get_user_from_headers(request)
    if not m.delete(dbh, schedule_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted successfully"}
