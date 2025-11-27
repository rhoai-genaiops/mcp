#!/usr/bin/env python3
"""
Test data script to populate the calendar database with sample schedules
"""

import json
from datetime import datetime, timedelta
import database_handler
import configparser
import os

def load_config():
    config = configparser.ConfigParser()
    config.read('db.conf')
    return config['DEFAULT']

def get_db_path():
    """Get database path from environment variable or config"""
    db_path = os.getenv('DATABASE_PATH')
    if db_path:
        # Remove .db extension if present in the path
        return db_path.replace('.db', '')
    else:
        info = load_config()
        return info['db_name']

def create_test_schedules():
    """Create Redwood Digital University schedules for teachers and students"""
    
    # Get current date and create schedules for this month
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    test_schedules = [
        # Today - Classes and Academic Activities
        {
            "sid": "class-cs301",
            "name": "CS 301: Machine Learning",
            "content": "Introduction to Neural Networks - Lecture Hall B203, Redwood Digital University",
            "category": "Lecture",
            "level": 3,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{today.day:02d} 09:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{today.day:02d} 10:30:00"
        },
        {
            "sid": "office-hours-001",
            "name": "Office Hours - Dr. Chen",
            "content": "Student consultations for AI Ethics course - Room 305, CS Building",
            "category": "Office Hours",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{today.day:02d} 14:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{today.day:02d} 16:00:00"
        },
        # Tomorrow - Assignments and Labs
        {
            "sid": "lab-ai401",
            "name": "AI 401: Deep Learning Lab",
            "content": "Hands-on training with TensorFlow and PyTorch - Computer Lab 101",
            "category": "Lab",
            "level": 3,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 10:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 12:00:00"
        },
        {
            "sid": "assignment-due-001",
            "name": "Assignment Due: NLP Project",
            "content": "Submit Natural Language Processing final project - Canvas submission deadline",
            "category": "Assignment",
            "level": 3,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 23:59:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 23:59:00"
        },
        # This week - Faculty and Student Activities
        {
            "sid": "faculty-meeting-001",
            "name": "Faculty Meeting: AI Department",
            "content": "Monthly department meeting - Discuss new curriculum for Generative AI track",
            "category": "Meeting",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 2):02d} 15:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 2):02d} 16:30:00"
        },
        {
            "sid": "thesis-defense-001",
            "name": "PhD Defense: Sarah Martinez",
            "content": "\"Explainable AI in Healthcare Applications\" - Conference Room A, Admin Building",
            "category": "Defense",
            "level": 3,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 3):02d} 14:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 3):02d} 16:00:00"
        },
        {
            "sid": "guest-lecture-001",
            "name": "Guest Lecture: Industry AI Trends",
            "content": "Dr. Alex Thompson from TechCorp AI - Auditorium Main Hall",
            "category": "Lecture",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 4):02d} 11:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 4):02d} 12:30:00"
        },
        # Weekend - Student Activities
        {
            "sid": "study-group-001",
            "name": "Study Group: Quantum Computing",
            "content": "Student-led study session for QC 205 final exam - Library Study Room 12",
            "category": "Study Group",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 5):02d} 14:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 5):02d} 17:00:00"
        },
        {
            "sid": "workshop-001",
            "name": "AI Workshop: Ethics & Bias",
            "content": "Interactive workshop on responsible AI development - Student Center Room 201",
            "category": "Workshop",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 6):02d} 13:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 6):02d} 15:00:00"
        },
        # Past completed activities
        {
            "sid": "grading-completed-001",
            "name": "Grading: Midterm Exams",
            "content": "Completed grading CS 201 midterm exams - 45 students processed",
            "category": "Grading",
            "level": 2,
            "status": 1.0,
            "creation_time": (today - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day - 1):02d} 09:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day - 1):02d} 17:00:00"
        },
        {
            "sid": "seminar-completed-001",
            "name": "Research Seminar: Computer Vision",
            "content": "Presented latest research on object detection algorithms - Faculty Lounge",
            "category": "Seminar",
            "level": 3,
            "status": 1.0,
            "creation_time": (today - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day - 2):02d} 16:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day - 2):02d} 17:30:00"
        },
        # Additional university activities
        {
            "sid": "committee-meeting-001",
            "name": "Curriculum Committee",
            "content": "Review proposed changes to AI Master's program - Admin Building Room 401",
            "category": "Meeting",
            "level": 2,
            "status": 0.0,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 7):02d} 10:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 7):02d} 11:30:00"
        },
        {
            "sid": "student-consultation-001",
            "name": "Student Advising Session",
            "content": "Academic advising for graduate students - Course selection for next semester",
            "category": "Advising",
            "level": 2,
            "status": 0.5,
            "creation_time": today.strftime("%Y-%m-%d %H:%M:%S"),
            "start_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 13:00:00",
            "end_time": f"{current_year}-{current_month:02d}-{(today.day + 1):02d} 15:00:00"
        }
    ]
    
    return test_schedules

def populate_database():
    """Populate the database with test schedules"""
    print("🗃️  Populating database with test data...")

    # Load configuration
    info = load_config()

    # Initialize database handler with DATABASE_PATH env var or config
    db_name = get_db_path()
    dbh = database_handler.DatabaseHandler(db_name=db_name, check_same_thread=False)

    # Ensure the table exists before inserting data
    columns = json.loads(info['columns'])
    print(f"📋 Ensuring table '{info['table_name']}' exists...")
    dbh.create_table(table_name=info['table_name'], columns=columns)

    # Create test schedules
    test_schedules = create_test_schedules()
    
    # Insert test data
    success_count = 0
    for schedule in test_schedules:
        try:
            # Check if schedule already exists
            if not dbh.check_existence(info['table_name'], {'sid': schedule['sid']}):
                dbh.insert_data(info['table_name'], json.loads(info['columns']), schedule)
                print(f"✅ Added: {schedule['name']} ({schedule['category']})")
                success_count += 1
            else:
                print(f"⚠️  Skipped: {schedule['name']} (already exists)")
        except Exception as e:
            print(f"❌ Error adding {schedule['name']}: {e}")
    
    print(f"\n🎉 Successfully added {success_count} test schedules!")
    print("📅 You can now view them in the frontend calendar.")

def clear_test_data():
    """Remove all test data from the database"""
    print("🗑️  Clearing test data...")

    # Load configuration
    info = load_config()

    # Initialize database handler with DATABASE_PATH env var or config
    db_name = get_db_path()
    dbh = database_handler.DatabaseHandler(db_name=db_name, check_same_thread=False)
    
    # Get test schedule IDs
    test_schedules = create_test_schedules()
    test_ids = [schedule['sid'] for schedule in test_schedules]
    
    # Remove test data
    removed_count = 0
    for sid in test_ids:
        try:
            if dbh.check_existence(info['table_name'], {'sid': sid}):
                dbh.delete_data(info['table_name'], {'sid': sid})
                print(f"🗑️  Removed: {sid}")
                removed_count += 1
        except Exception as e:
            print(f"❌ Error removing {sid}: {e}")
    
    print(f"\n✅ Removed {removed_count} test schedules!")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_test_data()
    else:
        populate_database()