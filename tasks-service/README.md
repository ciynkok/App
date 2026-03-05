# Task Service

A microservice for managing Kanban boards, tasks, columns, and comments with real-time integration and deadline reminders.

## Overview

Task Service is responsible for the business logic of managing boards, tasks, columns, and comments. It implements a REST API for CRUD operations, supports filtering, search, analytics (burn-down chart), and integrates with the Real-time Service through webhooks.

## Features

- **Board Management**: Create, read, update, and delete Kanban boards
- **Column Management**: Manage columns within boards
- **Task Management**: Full CRUD operations for tasks with:
  - Priority levels (low, medium, high, urgent)
  - Status tracking (todo, in_progress, review, done)
  - Deadline management with automated reminders
  - Task assignment
  - Position-based ordering
- **Comment System**: Add, update, and delete comments on tasks
- **Search & Filter**: Advanced filtering and search capabilities
- **Analytics**: Burn-down chart generation for project tracking
- **Real-time Integration**: Webhook notifications to Real-time Service
- **Authentication**: JWT-based authentication via Auth Service
- **Authorization**: Role-based access control (RBAC) with admin/editor/viewer roles

## Technology Stack

- **Python 3.12** with **FastAPI** - HTTP server and routing
- **SQLAlchemy 2.0 (async)** - Async ORM for PostgreSQL
- **PostgreSQL 16** - Primary database (task schema)
- **Pydantic** - Data validation
- **pytest + pytest-asyncio** - Testing framework
- **APScheduler** - Task scheduling for deadline reminders
- **httpx** - Async HTTP client for webhooks

## Project Structure

```
tasks-service/
├── cmd/
│   ├── __init__.py
│   └── main.py              # Application entry point
├── src/
│   ├── __init__.py
│   ├── config.py             # Configuration management
│   ├── database.py           # Database connection and session management
│   ├── models.py             # SQLAlchemy ORM models
│   ├── schemas.py            # Pydantic schemas for validation
│   ├── middleware.py         # Authentication and authorization middleware
│   ├── webhook.py            # Webhook service for Real-time integration
│   ├── scheduler.py          # Deadline reminder scheduler
│   └── routers/
│       ├── __init__.py
│       ├── boards.py         # Board API endpoints
│       ├── columns.py        # Column API endpoints
│       ├── tasks.py          # Task API endpoints
│       ├── comments.py       # Comment API endpoints
│       └── analytics.py      # Analytics endpoints (burn-down chart)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration and fixtures
│   └── test_boards.py       # Sample tests
├── .dockerignore
├── .env.example             # Environment variables template
├── Dockerfile               # Docker configuration
├── init.sql                 # Database schema initialization
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Docker and Docker Compose (for containerized deployment)

### Local Development

1. **Clone the repository and navigate to the service directory**

```bash
cd tasks-service
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up the database**

```bash
# Run the init.sql script to create the task schema
psql -U postgres -d taskdb -f init.sql
```

6. **Run the service**

```bash
python -m cmd.main
```

The service will start on `http://localhost:3002`

### Docker Deployment

1. **Build the Docker image**

```bash
docker build -t task-service .
```

2. **Run with Docker Compose**

```bash
docker-compose up -d task-service
```

## API Documentation

When running in debug mode, the API documentation is available at:

- **Swagger UI**: `http://localhost:3002/api/docs`
- **ReDoc**: `http://localhost:3002/api/redoc`

### Main Endpoints

#### Boards
- `POST /api/boards` - Create a new board
- `GET /api/boards` - List user's boards
- `GET /api/boards/{board_id}` - Get board details with stats
- `PUT /api/boards/{board_id}` - Update board
- `DELETE /api/boards/{board_id}` - Delete board
- `POST /api/boards/{board_id}/members` - Add board member
- `GET /api/boards/{board_id}/members` - List board members
- `PUT /api/boards/{board_id}/members/{member_id}` - Update member role
- `DELETE /api/boards/{board_id}/members/{member_id}` - Remove member

#### Columns
- `POST /api/boards/{board_id}/columns` - Create column
- `GET /api/boards/{board_id}/columns` - List columns
- `GET /api/boards/{board_id}/columns/{column_id}` - Get column with tasks
- `PUT /api/boards/{board_id}/columns/{column_id}` - Update column
- `DELETE /api/boards/{board_id}/columns/{column_id}` - Delete column

#### Tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks` - List and filter tasks
- `GET /api/tasks/{task_id}` - Get task details
- `PUT /api/tasks/{task_id}` - Update task
- `POST /api/tasks/{task_id}/move` - Move task to another column
- `DELETE /api/tasks/{task_id}` - Delete task

#### Comments
- `POST /api/tasks/{task_id}/comments` - Create comment
- `GET /api/tasks/{task_id}/comments` - List comments
- `GET /api/tasks/{task_id}/comments/{comment_id}` - Get comment
- `PUT /api/tasks/{task_id}/comments/{comment_id}` - Update comment
- `DELETE /api/tasks/{task_id}/comments/{comment_id}` - Delete comment

#### Analytics
- `GET /api/boards/{board_id}/stats` - Get board statistics and burn-down chart

## Authentication & Authorization

### Authentication

All protected endpoints require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

Tokens are validated against the Auth Service.

### Authorization

Access to boards and their resources is controlled by roles:

- **Viewer**: Can view boards, tasks, and comments
- **Editor**: Can create and modify tasks, columns, and comments
- **Admin**: Can manage board members and perform all editor actions
- **Owner**: Can delete the board and modify board settings

Role hierarchy: `admin > editor > viewer`

## Webhook Integration

Task Service sends webhook notifications to the Real-time Service for the following events:

- `task.created` - When a task is created
- `task.updated` - When a task is updated
- `task.moved` - When a task is moved between columns
- `task.deleted` - When a task is deleted
- `comment.created` - When a comment is created
- `comment.updated` - When a comment is updated
- `comment.deleted` - When a comment is deleted
- `column.created` - When a column is created
- `column.updated` - When a column is updated
- `column.deleted` - When a column is deleted

## Deadline Reminders

The service includes a scheduler that automatically sends deadline reminders:

- **Daily checks** at 9:00 AM for tasks due within 24 hours
- **Daily checks** at 9:30 AM for overdue tasks
- **Individual reminders** scheduled 1 day before each task's deadline

Reminders are sent as webhook events to the Real-time Service, which can then notify users through WebSocket connections.

## Testing

### Run tests

```bash
pytest
```

### Run tests with coverage

```bash
pytest --cov=src --cov-report=html
```

### Run specific test file

```bash
pytest tests/test_boards.py
```

## Environment Variables

See `.env.example` for all available configuration options:

| Variable | Description | Default |
|----------|-------------|----------|
| `APP_NAME` | Application name | Task Service |
| `APP_VERSION` | Application version | 1.0.0 |
| `DEBUG` | Enable debug mode | False |
| `HOST` | Server host | 0.0.0.0 |
| `PORT` | Server port | 3002 |
| `DATABASE_URL` | PostgreSQL connection string | - |
| `AUTH_SERVICE_URL` | Auth Service URL | http://auth-service:3001 |
| `REALTIME_SERVICE_URL` | Real-time Service URL | http://realtime-service:3003 |
| `JWT_SECRET_KEY` | JWT secret key | - |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `CORS_ORIGINS` | Allowed CORS origins | http://localhost:3000 |
| `SCHEDULER_ENABLED` | Enable deadline scheduler | True |

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

Common error codes:
- `INVALID_TOKEN` - JWT token is invalid or expired
- `ACCESS_DENIED` - User doesn't have access to the resource
- `INSUFFICIENT_ROLE` - User's role is insufficient for the action
- `BOARD_NOT_FOUND` - Board doesn't exist
- `COLUMN_NOT_FOUND` - Column doesn't exist
- `TASK_NOT_FOUND` - Task doesn't exist
- `COMMENT_NOT_FOUND` - Comment doesn't exist
- `MEMBER_EXISTS` - User is already a board member
- `NOT_AUTHOR` - User is not the author of the comment

## Development

### Code Style

This project follows PEP 8 style guidelines. Consider using tools like:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

### Adding New Features

1. Add models to `src/models.py`
2. Add Pydantic schemas to `src/schemas.py`
3. Create API routes in `src/routers/`
4. Add tests in `tests/`
5. Update this README if needed

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
