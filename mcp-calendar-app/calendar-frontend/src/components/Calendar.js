// src/components/Calendar.js
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Day from './Day';
import EventModal from './EventModal';
import './Calendar.css';

const Calendar = () => {
  const [schedules, setSchedules] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showEventModal, setShowEventModal] = useState(false);
  const [newSchedule, setNewSchedule] = useState({
    sid: "",
    name: "",
    content: "",
    category: "Lecture",
    level: 1,
    status: 0.0,
    creation_time: "",
    start_time: "",
    end_time: ""
  });

  // Fetch schedules when the component mounts or the month changes
  useEffect(() => {
    fetchSchedules();
  }, [currentMonth]);

  // Function to fetch schedules from the backend
  const fetchSchedules = () => {
    axios.get('/api/schedules')
      .then((response) => {
        setSchedules(response.data);
      })
      .catch((error) => {
        console.error('Error fetching schedules:', error);
      });
  };

  // Handle month navigation
  const handleMonthChange = (increment) => {
    setCurrentMonth((prev) => (prev + increment + 12) % 12);
  };

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewSchedule((prev) => ({ ...prev, [name]: value }));
  };

  // Handle form submission
  const handleFormSubmit = async (e) => {
    e.preventDefault();

    // Validate required fields
    if (!newSchedule.name || !newSchedule.start_time || !newSchedule.end_time) {
      alert('Please fill in all required fields (Event Name, Start Time, End Time)');
      return;
    }

    // Validate start time is before end time
    if (new Date(newSchedule.start_time) >= new Date(newSchedule.end_time)) {
      alert('Start time must be before end time');
      return;
    }

    // Generate unique SID with random component to avoid duplicates
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000);
    const uniqueSid = `event-${timestamp}-${random}`;

    // Format datetime strings for backend (YYYY-MM-DD HH:MM:SS)
    const formatDateTime = (dateTimeStr) => {
      const date = new Date(dateTimeStr);
      return date.getFullYear() + '-' + 
             String(date.getMonth() + 1).padStart(2, '0') + '-' + 
             String(date.getDate()).padStart(2, '0') + ' ' + 
             String(date.getHours()).padStart(2, '0') + ':' + 
             String(date.getMinutes()).padStart(2, '0') + ':' + 
             String(date.getSeconds()).padStart(2, '0');
    };

    const currentDateTime = formatDateTime(new Date());
    const startTime = formatDateTime(newSchedule.start_time);
    const endTime = formatDateTime(newSchedule.end_time);

    // Prepare the schedule data with correct types and validation
    const formattedSchedule = {
      sid: uniqueSid,
      name: newSchedule.name.trim(),
      content: newSchedule.content.trim() || "",
      category: newSchedule.category,
      level: parseInt(newSchedule.level || 1), // Backend accepts 1,2,3
      status: parseFloat(newSchedule.status || 0.0),
      creation_time: currentDateTime,
      start_time: startTime,
      end_time: endTime
    };

    console.log('Submitting schedule:', formattedSchedule);

    try {
      const response = await axios.post('/api/schedules', formattedSchedule, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      console.log('Successfully created schedule:', response.data);
      
      // Reset form
      setNewSchedule({
        sid: "",
        name: "",
        content: "",
        category: "Lecture",
        level: 1,
        status: 0.0,
        creation_time: "",
        start_time: "",
        end_time: ""
      });
      
      // Close form
      setShowForm(false);
      
      // Refresh schedules from server
      fetchSchedules();
      
      alert('Event created successfully! 🎉');
    } catch (error) {
      console.error('Error creating schedule:', error.response?.data || error.message);
      let errorMsg = 'Unknown error occurred';
      
      if (error.response?.status === 400) {
        errorMsg = 'Invalid data - please check your inputs';
      } else if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      alert(`❌ Error creating event: ${errorMsg}`);
    }
  };

  // Handle event click to open modal
  const handleEventClick = (event) => {
    setSelectedEvent(event);
    setShowEventModal(true);
  };

  // Close event modal
  const closeEventModal = () => {
    setShowEventModal(false);
    setSelectedEvent(null);
  };

  // Handle event deletion
  const handleDeleteEvent = async (eventId) => {
    if (!eventId) {
      alert('❌ Error: No event ID provided');
      return;
    }

    // Confirm deletion
    const confirmed = window.confirm(
      `Are you sure you want to delete this event?\n\nThis action cannot be undone.`
    );

    if (!confirmed) {
      return;
    }

    try {
      await axios.delete(`/api/schedules/${eventId}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('Successfully deleted event:', eventId);
      
      // Close the modal
      closeEventModal();
      
      // Refresh schedules from server
      fetchSchedules();
      
      alert('✅ Event deleted successfully!');
    } catch (error) {
      console.error('Error deleting event:', error.response?.data || error.message);
      let errorMsg = 'Unknown error occurred';
      
      if (error.response?.status === 404) {
        errorMsg = 'Event not found - it may have already been deleted';
      } else if (error.response?.status === 400) {
        errorMsg = 'Invalid event ID';
      } else if (error.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error.message) {
        errorMsg = error.message;
      }
      
      alert(`❌ Error deleting event: ${errorMsg}`);
    }
  };

  // Calculate the number of days in the current month
  const currentYear = new Date().getFullYear();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const daysArray = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  return (
    <div className="calendar-container">
      <div className="month-navigation">
        <button onClick={() => handleMonthChange(-1)}>← Previous</button>
        <span>{new Date(currentYear, currentMonth).toLocaleString("default", { month: "long", year: "numeric" })}</span>
        <button onClick={() => handleMonthChange(1)}>Next →</button>
      </div>

      <button className="add-schedule-btn" onClick={() => setShowForm(!showForm)}>
        {showForm ? "✕ Close Form" : "+ Add New Event"}
      </button>

      {/* Schedule creation form */}
      {showForm && (
        <form onSubmit={handleFormSubmit} className="schedule-form">
          <h3>📅 Create New Event</h3>
          
          <div className="form-group">
            <label>Event Name</label>
            <input 
              type="text" 
              name="name" 
              value={newSchedule.name}
              placeholder="e.g., CS 301: Machine Learning Lecture"
              onChange={handleInputChange} 
              required 
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea 
              name="content" 
              value={newSchedule.content}
              placeholder="Event details, location, notes..."
              onChange={handleInputChange}
              rows="3"
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Category</label>
              <select name="category" onChange={handleInputChange} value={newSchedule.category}>
                <option value="Lecture">📚 Lecture</option>
                <option value="Lab">🔬 Lab</option>
                <option value="Meeting">👥 Meeting</option>
                <option value="Office Hours">🕐 Office Hours</option>
                <option value="Assignment">📝 Assignment</option>
                <option value="Defense">🎓 Defense</option>
                <option value="Workshop">🛠️ Workshop</option>
                <option value="Study Group">👨‍🎓 Study Group</option>
                <option value="Seminar">🎤 Seminar</option>
                <option value="Grading">📊 Grading</option>
                <option value="Advising">💬 Advising</option>
              </select>
            </div>

            <div className="form-group">
              <label>Priority Level</label>
              <select name="level" onChange={handleInputChange} value={newSchedule.level}>
                <option value="1">🟢 Low Priority</option>
                <option value="2">🟡 Medium Priority</option>
                <option value="3">🔴 High Priority</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Start Time</label>
              <input 
                type="datetime-local" 
                name="start_time" 
                value={newSchedule.start_time}
                onChange={handleInputChange} 
                required 
              />
            </div>

            <div className="form-group">
              <label>End Time</label>
              <input 
                type="datetime-local" 
                name="end_time" 
                value={newSchedule.end_time}
                onChange={handleInputChange} 
                required 
              />
            </div>
          </div>

          <button type="submit" className="submit-btn">✨ Create Event</button>
        </form>
      )}

      {/* Calendar header with day names */}
      <div className="calendar-header">
        <div className="calendar-header-day">Sun</div>
        <div className="calendar-header-day">Mon</div>
        <div className="calendar-header-day">Tue</div>
        <div className="calendar-header-day">Wed</div>
        <div className="calendar-header-day">Thu</div>
        <div className="calendar-header-day">Fri</div>
        <div className="calendar-header-day">Sat</div>
      </div>

      {/* Display the calendar */}
      <div className="calendar">
        {daysArray.map((day) => (
          <Day 
            key={day} 
            day={day} 
            currentMonth={currentMonth}
            currentYear={currentYear}
            schedules={schedules.filter(schedule => {
              const scheduleDate = new Date(schedule.start_time);
              return (
                scheduleDate.getDate() === day &&
                scheduleDate.getMonth() === currentMonth &&
                scheduleDate.getFullYear() === currentYear
              );
            })}
            onEventClick={handleEventClick}
          />
        ))}
      </div>

      {/* Event Details Modal */}
      <EventModal 
        event={selectedEvent}
        isOpen={showEventModal}
        onClose={closeEventModal}
        onDelete={handleDeleteEvent}
      />
    </div>
  );
};

export default Calendar;
