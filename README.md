# Bank Transaction Management System

A microservices-based application for managing bank transactions, with custom permissions, Persian language support, and Jalali calendar integration.

## Architecture

This system is built using a microservices architecture with the following services:

1. **Auth Service** - Handles user authentication and custom permissions
2. **Account Service** - Manages bank accounts and balances
3. **Transaction Service** - Processes bank transactions (immediate and future-dated)
4. **Notification Service** - Manages notifications for transactions
5. **Document Service** - Handles document attachments
6. **Analytics Service** - Provides reporting and analytics

## Technology Stack

- **Backend**: FastAPI
- **Database**: Hybrid approach with SQLite (WAL mode)
- **Message Broker**: RabbitMQ for inter-service communication
- **Task Queue**: Celery for asynchronous processing
- **Authentication**: JWT
- **Localization**: Persian language and Jalali calendar support

## Getting Started

See individual service README files for setup and running instructions.

┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   Auth Service      │  │  Account Service    │  │ Transaction Service │
│                     │  │                     │  │                     │
│ - User management   │  │ - Bank accounts     │  │ - Transactions      │
│ - Authentication    │  │ - Balance tracking  │  │ - Transaction state │
│ - Authorization     │  │ - Account reporting │  │ - Verification      │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
          │                         │                        │
          │                         │                        │
          ▼                         ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ Notification Service│  │  Document Service   │  │  Analytics Service  │
│                     │  │                     │  │                     │
│ - Email delivery    │  │ - File storage      │  │ - Reporting         │
│ - Notification rules│  │ - Document versions │  │ - Data visualization│
│ - Scheduling        │  │ - Access control    │  │ - Trend analysis    │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘


# Banking Microservices Directory Structure

This document provides a detailed directory structure for each microservice in the banking application.

## Account Service

```
account-service/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── accounts.py         # Account API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication utilities
│   │   └── config.py           # Configuration settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Database base models
│   │   └── init_db.py          # Database initialization
│   ├── models/
│   │   ├── __init__.py
│   │   └── account.py          # Account SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── account.py          # Account Pydantic schemas
│   └── services/
│       ├── __init__.py
│       └── account_service.py  # Account business logic
├── main.py                     # Application entry point
└── requirements.txt            # Dependencies
```

## Analytics Service

```
analytics-service/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # API dependencies
│   │   ├── router.py           # API router configuration
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── analytics.py    # Analytics API endpoints
│   │       ├── ml.py           # Machine learning API endpoints
│   │       └── system.py       # System API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration settings
│   │   └── logging.py          # Logging configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Database base models
│   │   └── database.py         # Database connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── analytics.py        # Analytics SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── analytics.py        # Analytics Pydantic schemas
│   │   └── ml.py               # Machine learning Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── account_service.py  # Account service client
│       ├── analytics_service.py # Analytics business logic
│       ├── auth_service.py     # Auth service client
│       ├── ml_service.py       # Machine learning service
│       └── transaction_service.py # Transaction service client
├── main.py                     # Application entry point
└── requirements.txt            # Dependencies
```

## API Gateway

```
api-gateway/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration settings
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py             # Authentication middleware
│   │   ├── logging.py          # Logging middleware
│   │   └── rate_limiting.py    # Rate limiting middleware
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py           # Health check endpoints
│   │   └── proxy.py            # Proxy route handlers
│   └── services/
│       ├── __init__.py
│       ├── circuit_breaker.py  # Circuit breaker implementation
│       ├── proxy.py            # Proxy service
│       └── service_discovery.py # Service discovery
├── main.py                     # Application entry point
└── requirements.txt            # Dependencies
```

## Auth Service

```
auth-service/
├── .env                        # Environment variables
├── Dockerfile                  # Docker configuration
├── alembic.ini                 # Alembic configuration
├── alembic/
│   ├── env.py                  # Alembic environment
│   ├── script.py.mako          # Alembic script template
│   └── versions/
│       ├── 20230501_000000_initial_migration.py # Initial migration
│       └── 20230501_000001_seed_data.py        # Seed data migration
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py         # Authentication endpoints
│   │       ├── permissions.py  # Permission endpoints
│   │       ├── roles.py        # Role endpoints
│   │       └── users.py        # User endpoints
│   ├── core/
│   │   ├── config.py           # Configuration settings
│   │   ├── logging.py          # Logging configuration
│   │   ├── middleware.py       # Middleware configuration
│   │   └── security.py         # Security utilities
│   ├── db/
│   │   ├── base.py             # Database base models
│   │   └── init_db.py          # Database initialization
│   ├── main.py                 # Application entry point
│   ├── models/
│   │   ├── permission.py       # Permission SQLAlchemy models
│   │   ├── role.py             # Role SQLAlchemy models
│   │   └── user.py             # User SQLAlchemy models
│   ├── schemas/
│   │   ├── auth.py             # Auth Pydantic schemas
│   │   ├── permission.py       # Permission Pydantic schemas
│   │   ├── token.py            # Token Pydantic schemas
│   │   └── user.py             # User Pydantic schemas
│   └── services/
│       ├── auth_service.py     # Authentication business logic
│       ├── message_broker.py   # Message broker client
│       ├── permission_service.py # Permission business logic
│       └── user_service.py     # User business logic
├── data/
│   └── auth.db                 # SQLite database
├── init_db.py                  # Database initialization script
├── logs/
│   ├── auth_service_2025-06-12.log # Log files
│   └── auth_service_2025-06-17.log
├── requirements.txt            # Dependencies
├── run_dev.py                  # Development runner
├── run_tests.py                # Test runner
└── tests/
    ├── conftest.py             # Test configuration
    ├── test_auth.py            # Auth tests
    ├── test_permissions.py     # Permission tests
    ├── test_roles.py           # Role tests
    └── test_users.py           # User tests
```

## Document Service

```
document-service/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # API dependencies
│   │   ├── router.py           # API router configuration
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── documents.py    # Document API endpoints
│   │       └── system.py       # System API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Database base models
│   │   └── database.py         # Database connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── document.py         # Document SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── document.py         # Document Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py     # Auth service client
│       └── document_service.py # Document business logic
├── main.py                     # Application entry point
└── requirements.txt            # Dependencies
```

## Notification Service

```
notification-service/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # API dependencies
│   │   ├── router.py           # API router configuration
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── notifications.py # Notification API endpoints
│   │       └── preferences.py  # Preference API endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py           # Configuration settings
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py         # Database connection
│   ├── models/
│   │   ├── __init__.py
│   │   └── notification.py     # Notification SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── notification.py     # Notification Pydantic schemas
│   │   └── preference.py       # Preference Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py     # Auth service client
│       ├── notification_consumer.py # Notification message consumer
│       └── notification_service.py # Notification business logic
├── main.py                     # Application entry point
└── requirements.txt            # Dependencies
```

## Transaction Service

```
transaction-service/
├── alembic.ini                 # Alembic configuration
├── alembic/
│   ├── env.py                  # Alembic environment
│   └── script.py.mako          # Alembic script template
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # API dependencies
│   │   ├── router.py           # API router configuration
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── transactions.py # Transaction API endpoints
│   ├── core/
│   │   └── config.py           # Configuration settings
│   ├── db/
│   │   ├── __init__.py
│   │   └── base.py             # Database base models
│   ├── main.py                 # Application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── transaction.py      # Transaction SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── transaction.py      # Transaction Pydantic schemas
│   └── services/
│       ├── __init__.py
│       ├── account_service.py  # Account service client
│       ├── auth_service.py     # Auth service client
│       ├── notification_service.py # Notification service client
│       └── transaction_service.py # Transaction business logic
├── requirements.txt            # Dependencies
└── tests/
    ├── __init__.py
    └── conftest.py             # Test configuration
```