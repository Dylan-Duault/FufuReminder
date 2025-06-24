# FufuRemind Bot - Project Guidelines

## Project Overview
Enterprise-grade Discord bot for scheduled reminders with user validation system. Built with Python 3.11, discord.py 2.x, and SQLite.

## Core Features
- Admin-created reminders with configurable frequencies (hourly, daily, weekly, monthly)
- Optional user validation via ✅ reaction within 48h timeout
- Automatic user kick if validation not received
- Persistent SQLite storage with proper abstraction
- Structured logging and comprehensive error handling

## Architecture & Design Patterns

### SOLID Principles Applied
- **Single Responsibility**: Each service handles one concern
- **Open/Closed**: Strategy pattern for extensible scheduling
- **Liskov Substitution**: Repository pattern with base classes
- **Interface Segregation**: Focused interfaces for each layer
- **Dependency Inversion**: Dependency injection throughout

### Design Patterns Used
- **Repository Pattern**: Database abstraction (ReminderRepository, ValidationRepository)
- **Strategy Pattern**: Frequency calculation (FrequencyStrategy)
- **Factory Pattern**: Reminder creation (ReminderFactory)
- **Observer Pattern**: Reaction handling (ReactionObserver)
- **Command Pattern**: Slash command separation

### Project Structure
```
src/
├── bot/           # Discord client and events
├── commands/      # Slash command handlers
├── services/      # Business logic layer
├── models/        # Domain models
├── repositories/  # Data access layer
├── database/      # Database models and connection
├── strategies/    # Algorithm implementations
├── factories/     # Object creation
├── observers/     # Event handling
├── config/        # Configuration management
└── utils/         # Helper utilities
```

## Development Guidelines

### TDD Approach
1. **Red**: Write failing test first
2. **Green**: Implement minimum code to pass
3. **Refactor**: Improve while keeping tests green
4. Never modify tests to match broken code - fix implementation instead

### Testing Commands
```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests (101 tests currently passing)
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=src --cov-report=html

# Run specific test file
python3 -m pytest tests/unit/test_reminder_model.py -v

# Run integration tests
python3 -m pytest tests/integration/ -v

# Run specific service tests
python3 -m pytest tests/unit/test_notification_service.py -v
python3 -m pytest tests/unit/test_scheduler_service.py -v
python3 -m pytest tests/unit/test_validation_service.py -v
```

### Code Quality Commands
```bash
# Activate virtual environment first
source venv/bin/activate

# Format code
python3 -m black src/ tests/

# Sort imports
python3 -m isort src/ tests/

# Lint code
python3 -m flake8 src/ tests/

# Type checking
python3 -m mypy src/
```

### Database Commands
- Database auto-initializes on bot startup
- Migrations in `src/database/migrations/`
- Use in-memory SQLite for tests

### Configuration
- Environment variables in `config/.env`
- JSON config in `config/config.json`
- Settings managed via Pydantic in `src/config/settings.py`

## Key Implementation Notes

### Security Requirements
- Only users with Manage Server permission or specific roles can create reminders
- All user inputs must be validated and sanitized
- No sensitive data in error messages or logs
- Rate limiting on commands

### Performance Considerations
- Async/await throughout for Discord API calls
- Connection pooling for database
- Background task scheduling with asyncio
- Efficient database queries with proper indexing

### Error Handling
- Structured logging with contextual information
- Graceful degradation on Discord API failures
- Database transaction rollback on errors
- User-friendly error messages

### Reminder Lifecycle
1. Admin creates reminder via `/reminder add`
2. Bot schedules execution using asyncio
3. Message sent to configured channel at interval
4. If validation required, bot adds ✅ reaction
5. 48h timeout starts for user validation
6. User kicked if no validation received

### Testing Strategy
- **Unit Tests**: Individual components in isolation
- **Integration Tests**: Service interactions with mocked Discord
- **Fixtures**: Reusable test data and mocks
- **Coverage Target**: Minimum 90% code coverage

## Dependencies
- discord.py >= 2.3.0 (Discord API)
- SQLAlchemy >= 2.0.0 (Database ORM)
- aiosqlite >= 0.19.0 (Async SQLite)
- pydantic >= 2.0.0 (Configuration & validation)
- pydantic-settings >= 2.0.0 (Settings management)
- structlog >= 23.0.0 (Structured logging)
- pytest ecosystem for testing

## Current Implementation Status (101 Tests Passing)

### Completed Layers ✅
1. **Domain Models** (16 tests) - Reminder, Validation with business logic
2. **Repositories** (27 tests) - Data access with base, reminder, validation repos
3. **Services** (78 tests) - Business orchestration:
   - ReminderService (19 tests) - Core reminder management
   - SchedulerService (19 tests) - Async task scheduling  
   - ValidationService (23 tests) - Reaction processing & user kicking
   - NotificationService (17 tests) - Discord messaging & reactions
4. **Strategies** (23 tests) - Frequency calculation with edge cases
5. **Factories** (19 tests) - Object creation with validation

### Key Patterns Implemented
- Repository Pattern with generic base class
- Strategy Pattern for frequency calculations  
- Factory Pattern for reminder creation
- Service Layer for business orchestration
- Dependency Injection throughout
- Observer Pattern ready for reaction handling

### Integration Points Ready
- Frequency strategies integrated into Reminder model
- NotificationService ready for Discord client injection
- ValidationService handles user kicking automatically
- SchedulerService manages async task lifecycle
- All services properly handle Discord API errors

## Development Workflow
1. Write tests first (TDD)
2. Implement feature to pass tests
3. Run full test suite
4. Format and lint code
5. Update documentation if needed
6. Commit with clear message