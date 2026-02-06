# Session Persistence Documentation

## Overview

This project implements robust session persistence using SQLite, allowing users to resume surveys after closing or reopening the application. The system maintains complete history of user interactions and provides automatic recovery mechanisms.

## Features

### 1. **SQLite Database Storage**
- Persistent storage of session data in `survey_sessions.db`
- Automatic table creation and schema management
- Indexed queries for optimal performance
- Transaction support for data integrity

### 2. **Session Data Persistence**
- **Current Step**: Tracks the current question/step in the survey
- **Answers**: Complete dictionary of all user answers
- **Step History**: Full navigation history for back button support
- **Audio Mode**: Tracks whether session is in audio or text mode
- **Timestamps**: Created and updated timestamps for each session

### 3. **Retry Logic**
- Exponential backoff retry mechanism for database operations
- Automatic retry for failed WebSocket connections
- Retry decorators for critical functions
- Configurable retry attempts and delays

### 4. **Session Recovery**
- Automatic session loading on reconnection
- State synchronization between client and server
- History preservation across sessions
- Graceful fallback to new session if recovery fails

## Database Schema

### `sessions` Table
```sql
CREATE TABLE sessions (
    user_id TEXT NOT NULL PRIMARY KEY,
    current_step TEXT NOT NULL,
    answers TEXT NOT NULL,  -- JSON encoded
    step_history TEXT NOT NULL,  -- JSON encoded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_audio_mode INTEGER DEFAULT 0,
    session_data TEXT  -- JSON encoded additional data
)
```

### `session_history` Table
```sql
CREATE TABLE session_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    step TEXT,
    answer TEXT,  -- JSON encoded
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES sessions(user_id)
)
```

## Usage

### Automatic Session Persistence

Sessions are automatically saved:
1. **On State Changes**: When the user navigates to a new step
2. **On Manual Updates**: When the user manually changes answers
3. **Periodically**: Every 30 seconds as a backup
4. **On Disconnect**: Final state is saved before WebSocket closes

### Manual Session Management

#### Load a Session
```python
from database import get_database

db = get_database()
session = db.load_session(user_id="user123")
if session:
    current_step = session["current_step"]
    answers = session["answers"]
    step_history = session["step_history"]
```

#### Save a Session
```python
db.save_session(
    user_id="user123",
    current_step="S5",
    answers={"S1": "Option A", "S2": "Option B"},
    step_history=["S1", "S2", "S3", "S4"],
    is_audio_mode=False
)
```

#### Update Session State
```python
db.update_session_state(
    user_id="user123",
    current_step="S6",
    answers={"S1": "Option A", "S2": "Option B", "S5": "Option C"}
)
```

## Retry Logic

### Database Operations
- **Max Retries**: 3 attempts
- **Initial Delay**: 0.5 seconds
- **Backoff**: Exponential (2x multiplier)
- **Max Delay**: 30 seconds

### WebSocket Operations
- **Connection Retry**: 5 attempts with exponential backoff
- **Message Send Retry**: 3 attempts with linear backoff
- **Automatic Recovery**: Re-establishes connection on failure

## API Endpoints

### GET `/api/session/{user_id}`
Retrieve saved session data for a user.

**Response:**
```json
{
    "success": true,
    "session": {
        "current_step": "S5",
        "answers": {"S1": "Option A", "S2": "Option B"},
        "step_history": ["S1", "S2", "S3", "S4"],
        "is_audio_mode": false
    }
}
```

## Error Handling

The system implements multiple layers of error handling:

1. **Database Errors**: Retry with exponential backoff, graceful degradation
2. **WebSocket Errors**: Automatic reconnection with retry logic
3. **Session Load Failures**: Fallback to new session creation
4. **Save Failures**: Logged but don't interrupt user flow

## Best Practices

1. **Always use retry decorators** for critical database operations
2. **Handle exceptions gracefully** - don't crash on save failures
3. **Log all errors** for debugging and monitoring
4. **Validate session data** before saving
5. **Use transactions** for multi-step operations

## Configuration

### Database Settings
- **DB Path**: `survey_sessions.db` (configurable)
- **Timeout**: 30 seconds
- **Connection Pooling**: Single connection with thread-safe access

### Retry Settings
- **Max Retries**: 3 (database), 5 (WebSocket)
- **Initial Delay**: 0.5 seconds
- **Backoff Multiplier**: 2.0
- **Max Delay**: 30 seconds

## Troubleshooting

### Database Locked Errors
- Ensure only one process accesses the database
- Check for long-running transactions
- Increase timeout if needed

### Session Not Loading
- Check database file permissions
- Verify user_id is consistent
- Check logs for JSON decode errors

### Performance Issues
- Database is indexed for optimal queries
- Consider connection pooling for high concurrency
- Monitor database file size

## Security Considerations

1. **User ID Validation**: Ensure user_id is sanitized
2. **SQL Injection**: Using parameterized queries
3. **Data Privacy**: Session data contains sensitive survey responses
4. **Access Control**: Implement authentication if needed

## Future Enhancements

- Session expiration and cleanup
- Database migration support
- Backup and restore functionality
- Session analytics and reporting
- Multi-database support (PostgreSQL, MySQL)
