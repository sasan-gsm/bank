# Document Service

A robust, enterprise-grade document management service built with FastAPI, MinIO, and Celery for asynchronous processing.

## Architecture

The service follows a layered architecture pattern:

```
document-service/
├── app/
│   ├── api/
│   │   └── documents.py          # REST API endpoints
│   ├── core/
│   │   ├── config.py             # Configuration management
│   │   ├── celery_app.py         # Celery setup
│   │   └── auth.py               # Authentication & JWT handling
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py            # Database session management
│   ├── services/
│   │   ├── storage.py            # MinIO interactions
│   │   ├── documents.py          # Business logic
│   │   └── tasks.py              # Background tasks
│   ├── models.py                 # SQLAlchemy & Pydantic models
│   └── main.py                   # FastAPI application
├── worker.py                     # Celery worker runner
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables
└── README.md                     # This file
```

## Features

### Core Functionality
- **Document Upload**: Asynchronous file upload to MinIO object storage
- **Document Management**: CRUD operations with metadata support
- **File Validation**: Size, type, and content validation
- **Duplicate Detection**: Hash-based duplicate file detection
- **Search & Filtering**: Advanced document search and filtering
- **Thumbnail Generation**: Automatic thumbnail generation for images

### Security
- **JWT Authentication**: Secure API access with JWT tokens
- **Role-based Access**: User and admin role management
- **File Type Validation**: Configurable allowed MIME types
- **Size Limits**: Configurable file size restrictions

### Performance & Reliability
- **Asynchronous Processing**: Background task processing with Celery
- **Connection Pooling**: Efficient database and Redis connections
- **Error Handling**: Comprehensive error handling and retry mechanisms
- **Health Checks**: Service health monitoring endpoints
- **Cleanup Tasks**: Automatic cleanup of failed uploads

## Prerequisites

- Python 3.11+
- Redis server
- MinIO server
- SQLite (default) or PostgreSQL

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd document-service
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```

## Configuration

The service uses environment variables for configuration. Key settings include:

### Database
```env
DATABASE_URL=sqlite+aiosqlite:///./documents.db
```

### MinIO Storage
```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documents
MINIO_SECURE=false
MINIO_REGION=us-east-1
```

### Redis/Celery
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Authentication
```env
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
AUTH_SERVICE_URL=http://localhost:8001
```

### File Upload Settings
```env
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_MIME_TYPES=application/pdf,image/jpeg,image/png,text/plain
```

## Running the Service

### Development Mode

1. **Start Redis server**:
   ```bash
   redis-server
   ```

2. **Start MinIO server**:
   ```bash
   minio server ./minio-data --console-address ":9001"
   ```

3. **Initialize database**:
   ```bash
   python -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db())"
   ```

4. **Start the FastAPI application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Start the Celery worker** (in a separate terminal):
   ```bash
   python worker.py
   ```

### Production Mode

For production deployment, consider using:
- **Docker Compose** for containerized deployment
- **Gunicorn** with multiple workers
- **Nginx** as reverse proxy
- **PostgreSQL** for production database
- **Redis Cluster** for high availability

## API Documentation

Once the service is running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Document Management
- `POST /api/v1/documents/` - Upload document
- `GET /api/v1/documents/` - List documents with filtering
- `GET /api/v1/documents/{doc_id}` - Get document metadata
- `GET /api/v1/documents/{doc_id}/download` - Download document
- `PUT /api/v1/documents/{doc_id}` - Update document metadata
- `DELETE /api/v1/documents/{doc_id}` - Delete document

#### Statistics (Admin only)
- `GET /api/v1/documents/stats/summary` - Get document statistics

#### Health Checks
- `GET /health` - Service health status
- `GET /` - Service information

## Background Tasks

The service uses Celery for background processing:

### Available Tasks
- **process_upload**: Process document upload to MinIO
- **generate_document_thumbnail**: Generate thumbnails for images
- **cleanup_failed_uploads**: Clean up failed uploads
- **test_services_health**: Health check for external services

### Monitoring Tasks

You can monitor Celery tasks using:
```bash
celery -A app.core.celery_app events
```

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Development

### Code Quality

The project uses several tools for code quality:

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

### Database Migrations

For database schema changes, use Alembic:
```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

## Monitoring and Logging

The service includes comprehensive logging and monitoring:

- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Checks**: Built-in health check endpoints
- **Metrics**: Performance and usage metrics
- **Error Tracking**: Detailed error logging and tracking

## Security Considerations

- **Authentication**: All endpoints require valid JWT tokens
- **Authorization**: Role-based access control
- **File Validation**: Strict file type and size validation
- **Input Sanitization**: All inputs are validated and sanitized
- **Secure Headers**: Security headers are set by default

## Troubleshooting

### Common Issues

1. **MinIO Connection Failed**:
   - Check MinIO server is running
   - Verify credentials and endpoint configuration
   - Ensure bucket exists or service has permission to create it

2. **Celery Tasks Not Processing**:
   - Check Redis server is running
   - Verify Celery worker is started
   - Check task queue status

3. **Database Connection Issues**:
   - Verify database file permissions (SQLite)
   - Check database URL configuration
   - Ensure database is initialized

### Logs

Check application logs for detailed error information:
```bash
# Application logs
tail -f app.log

# Celery worker logs
tail -f celery.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation and FAQ