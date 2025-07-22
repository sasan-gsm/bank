# Account Service

A microservice for managing bank accounts in a distributed banking system. Built with FastAPI, SQLAlchemy, and Redis for high-performance account management with event-driven architecture.

## Features

- **Account Management**: Create, read, update, and manage bank accounts
- **Balance Operations**: Credit/debit transactions with real-time balance updates
- **Authorization System**: Multi-user account access with permission controls
- **Event-Driven Architecture**: Redis Streams for inter-service communication
- **Security**: JWT-based authentication and authorization
- **Performance**: Redis caching and optimized database queries
- **Monitoring**: Health checks, metrics, and comprehensive logging
- **Containerized**: Docker and Docker Compose for easy deployment

## Architecture

```
account-service/
├── api/                    # API layer
│   ├── deps.py            # Dependencies and middleware
│   └── routes/
│       └── accounts.py    # Account endpoints
├── core/                  # Core configuration
│   ├── config.py         # Settings management
│   └── security.py       # JWT and security
├── domain/               # Domain layer
│   ├── models.py         # Domain models and schemas
│   └── events.py         # Domain events
├── db/                   # Data layer
│   ├── session.py        # Database session management
│   └── repository.py     # Data access layer
├── services/             # Business logic
│   └── account_service.py # Account business logic
├── scripts/              # Utility scripts
│   └── init_db.py        # Database initialization
├── main.py               # FastAPI application
├── worker.py             # Background worker
└── requirements.txt      # Dependencies
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Redis (for development)

### Installation

1. **Clone and setup**:
   ```bash
   cd account-service
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize database**:
   ```bash
   python scripts/init_db.py init
   ```

4. **Run the service**:
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Production deployment**:
   ```bash
   # Create network (if not exists)
   docker network create bank_network
   
   # Start services
   docker-compose up -d
   ```

2. **Development with hot reload**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
   ```

3. **Initialize database in Docker**:
   ```bash
   docker-compose run --rm db-init
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `DATABASE_URL` | SQLite database URL | `sqlite+aiosqlite:///./data/accounts.db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `JWT_PUBLIC_KEY` | JWT public key for token validation | Required |
| `JWT_ALGORITHM` | JWT algorithm | `RS256` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `REDIS_STREAM_ACCOUNTS` | Redis stream for account events | `account-events` |
| `REDIS_STREAM_TRANSACTIONS` | Redis stream for transaction events | `transaction-events` |
| `CACHE_TTL` | Cache TTL in seconds | `300` |
| `LOG_LEVEL` | Logging level | `INFO` |

## API Documentation

### Authentication

All endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer <jwt-token>
```

### Endpoints

#### Account Management

- `POST /api/v1/accounts/` - Create new account
- `GET /api/v1/accounts/{account_id}` - Get account by ID
- `GET /api/v1/accounts/number/{account_number}` - Get account by number
- `PUT /api/v1/accounts/{account_id}` - Update account
- `GET /api/v1/accounts/user/me` - Get my accounts

#### Balance Operations

- `PATCH /api/v1/accounts/{account_id}/balance` - Update balance

#### Account Status

- `PATCH /api/v1/accounts/{account_id}/activate` - Activate account
- `PATCH /api/v1/accounts/{account_id}/deactivate` - Deactivate account

#### Authorization Management

- `POST /api/v1/accounts/{account_id}/authorized-users/{user_id}` - Add authorized user
- `DELETE /api/v1/accounts/{account_id}/authorized-users/{user_id}` - Remove authorized user

#### Search and Filtering

- `GET /api/v1/accounts/search?q={query}` - Search accounts
- `GET /api/v1/accounts/filter/type/{account_type}` - Filter by type
- `GET /api/v1/accounts/filter/status/{status}` - Filter by status

#### Statistics

- `GET /api/v1/accounts/summary` - Get account summary
- `GET /api/v1/accounts/statistics` - Get detailed statistics

#### Health and Monitoring

- `GET /health` - Health check
- `GET /metrics` - Basic metrics

### Example Requests

#### Create Account
```bash
curl -X POST "http://localhost:8001/api/v1/accounts/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Checking Account",
    "account_type": "checking",
    "bank_name": "Example Bank",
    "initial_balance": 1000.00
  }'
```

#### Update Balance
```bash
curl -X PATCH "http://localhost:8001/api/v1/accounts/1/balance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 500.00,
    "is_credit": true,
    "description": "Deposit"
  }'
```

#### Search Accounts
```bash
curl "http://localhost:8001/api/v1/accounts/search?q=checking&limit=10" \
  -H "Authorization: Bearer <token>"
```

## Event System

The service publishes events to Redis Streams for inter-service communication:

### Published Events

- `account_created` - New account created
- `account_updated` - Account information updated
- `balance_updated` - Account balance changed
- `account_status_changed` - Account activated/deactivated
- `user_authorization_changed` - User access granted/revoked

### Consumed Events

- `transaction_created` - Updates account balance
- `transaction_updated` - Adjusts balance if needed
- `transaction_deleted` - Reverses balance changes

### Event Format

```json
{
  "event_id": "uuid",
  "event_type": "account_created",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "account-service",
  "data": {
    "account_id": 1,
    "user_id": 123,
    "account_number": "ACC001",
    "account_type": "checking",
    "initial_balance": 1000.00
  }
}
```

## Database Schema

### Accounts Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `account_number` | String | Unique account number |
| `name` | String | Account name |
| `account_type` | Enum | checking/savings/business |
| `bank_name` | String | Bank name |
| `balance` | Decimal | Current balance |
| `currency` | String | Currency code |
| `status` | Enum | active/inactive |
| `user_id` | Integer | Owner user ID |
| `authorized_users` | JSON | List of authorized user IDs |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |
| `is_deleted` | Boolean | Soft delete flag |

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
flake8 .
```

### Database Operations

```bash
# Initialize database
python scripts/init_db.py init

# Reset database (development only)
python scripts/init_db.py reset

# Check database health
python scripts/init_db.py health

# Validate database setup
python scripts/init_db.py validate
```

### Worker Process

The background worker handles:
- Processing transaction events from other services
- Periodic maintenance tasks
- Health monitoring

```bash
# Run worker
python worker.py
```

## Monitoring and Logging

### Health Checks

- **Application**: `GET /health`
- **Database**: Connection and query tests
- **Redis**: Connection and ping tests

### Logging

- **Structured logging** with JSON format in production
- **Request/response logging** with timing
- **Error tracking** with stack traces
- **Event publishing** logs

### Metrics

- **Request metrics**: Count, duration, status codes
- **Business metrics**: Account counts, balance totals
- **System metrics**: Database connections, Redis operations

## Security

### Authentication
- JWT token validation with public key
- User identity extraction from tokens
- Role-based access control

### Authorization
- Account ownership validation
- Authorized user access control
- Admin-only operations

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- Sensitive data logging exclusion

## Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure proper JWT public key
- [ ] Set up Redis cluster for high availability
- [ ] Configure proper CORS origins
- [ ] Set up log aggregation
- [ ] Configure monitoring and alerting
- [ ] Set up backup strategy for SQLite database
- [ ] Configure resource limits in Docker

### Scaling Considerations

- **Horizontal scaling**: Multiple service instances behind load balancer
- **Database**: Consider PostgreSQL for high-load scenarios
- **Caching**: Redis cluster for distributed caching
- **Event streaming**: Redis Cluster or Apache Kafka for high throughput

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check database file permissions
   - Verify database directory exists
   - Run database health check

2. **Redis connection errors**:
   - Verify Redis is running
   - Check Redis URL configuration
   - Test Redis connectivity

3. **JWT validation errors**:
   - Verify JWT public key configuration
   - Check token format and expiration
   - Validate algorithm settings

4. **Permission errors**:
   - Check user authentication
   - Verify account ownership
   - Review authorized users list

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug mode
python main.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.