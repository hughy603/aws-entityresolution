# AWS Entity Resolution - Simplified Architecture

This document provides a simplified overview of the AWS Entity Resolution solution architecture, focusing on the key components and their interactions.

## System Overview

The AWS Entity Resolution solution enables businesses to identify and link records that represent the same entities (customers, products, etc.) across disparate data sources, creating a unified view.

```mermaid
graph TB
    subgraph "Data Flow"
        SF[Snowflake Source] --> S3S[S3 Storage]
        S3S --> PR[Process]
        PR --> S3M[S3 Matched Results]
        S3M --> LD[Load]
        LD --> SFD[Snowflake Destination]
    end

    subgraph "AWS Services"
        ER[AWS Entity Resolution]
        S3[Amazon S3]
        IAM[IAM Roles]
    end

    subgraph "CLI Tool"
        CLI[Main CLI]
        PRC[Process Commands]
        LDC[Load Commands]
        SVC[AWS Services]
        CFG[Configuration]
    end

    PR --> ER
    S3S --> S3
    S3M --> S3
    CLI --> PRC
    CLI --> LDC
    PRC --> PR
    LDC --> LD
    PRC --> SVC
    LDC --> SVC
    SVC --> S3
    SVC --> ER
    SVC --> IAM
    CLI --> CFG

    style SF fill:#90CAF9,stroke:#1565C0
    style S3S fill:#FFE082,stroke:#FF8F00
    style PR fill:#A5D6A7,stroke:#2E7D32
    style S3M fill:#FFE082,stroke:#FF8F00
    style LD fill:#A5D6A7,stroke:#2E7D32
    style SFD fill:#90CAF9,stroke:#1565C0
    style ER fill:#CE93D8,stroke:#7B1FA2
    style S3 fill:#FFE082,stroke:#FF8F00
    style IAM fill:#B39DDB,stroke:#512DA8
    style CLI fill:#64B5F6,stroke:#1565C0
    style PRC fill:#64B5F6,stroke:#1565C0
    style LDC fill:#64B5F6,stroke:#1565C0
    style SVC fill:#FFCC80,stroke:#EF6C00
    style CFG fill:#FFCC80,stroke:#EF6C00
```

## Key Components

### 1. Python CLI Tool

The CLI tool provides a user-friendly interface for interacting with the AWS Entity Resolution pipeline. It's organized into two main commands:

- **Process**: Processes data through AWS Entity Resolution
- **Load**: Loads processed data back to Snowflake

```mermaid
classDiagram
    class CLI {
        +main()
        +configure()
    }

    class ProcessCommands {
        +run()
        +status()
        +validate_settings()
    }

    class LoadCommands {
        +run()
        +setup()
        +validate_settings()
    }

    class Services {
        +S3Service
        +EntityResolutionService
        +SnowflakeService
    }

    CLI --> ProcessCommands
    CLI --> LoadCommands
    ProcessCommands --> Services
    LoadCommands --> Services
```

### 2. Service Layer

The service layer provides a clean interface for interacting with AWS services and Snowflake. Each service follows a consistent pattern and uses dependency injection for configuration.

```mermaid
classDiagram
    class S3Service {
        +list_objects()
        +read_object()
        +write_object()
        +find_latest_path()
    }

    class EntityResolutionService {
        +start_matching_job()
        +get_job_status()
        +wait_for_job_completion()
        +get_output_path()
    }

    class SnowflakeService {
        +execute_query()
        +load_data()
        +setup_table()
        +load_data_from_s3()
    }

    class Settings {
        +aws_region
        +s3
        +snowflake_source
        +snowflake_target
        +entity_resolution
    }

    S3Service --> Settings
    EntityResolutionService --> Settings
    SnowflakeService --> Settings
```

### 3. Data Flow

The data flows through the system in a sequential process:

1. **Process**: AWS Entity Resolution processes the data from S3 to identify matching records
2. **Load**: Matched records are loaded to Snowflake as golden records

```mermaid
sequenceDiagram
    participant CLI as CLI Tool
    participant S3 as Amazon S3
    participant ER as AWS Entity Resolution
    participant SF as Snowflake

    CLI->>S3: Verify source data
    S3-->>CLI: Data ready
    CLI->>ER: Configure matching job
    ER->>S3: Read source data
    ER->>ER: Perform matching
    ER->>S3: Write matched results
    CLI->>S3: Read matched results
    CLI->>SF: Load golden records
```

## Code Structure

The codebase follows a clean, modular structure:

```
src/aws_entity_resolution/
├── __init__.py
├── cli/                      # CLI interfaces
│   ├── __init__.py
│   ├── main.py               # Main CLI entry point
│   ├── processor.py          # Processing commands
│   └── loader.py             # Loading commands
├── config/                   # Configuration
│   ├── __init__.py
│   └── factory.py            # Configuration factory
├── services/                 # Service interfaces
│   ├── __init__.py
│   ├── s3.py                 # S3 service
│   ├── entity_resolution.py  # Entity Resolution service
│   ├── snowflake.py          # Snowflake service
│   └── ...                   # Other services
├── processor/                # Data processing
│   ├── __init__.py
│   └── processor.py          # Processing logic
└── loader/                   # Data loading
    ├── __init__.py
    └── loader.py             # Loading logic
```

## Design Patterns

The solution uses several key design patterns:

1. **Dependency Injection**: Services receive their configuration through constructor injection
2. **Command Pattern**: CLI commands encapsulate operations as objects
3. **Service Layer**: Clean separation between business logic and external services
4. **Factory Pattern**: Configuration factory creates and validates settings
5. **Decorator Pattern**: Error handling decorators for consistent error management

## Security Considerations

The solution implements several security best practices:

1. **Least Privilege**: IAM roles with minimal permissions
2. **Encryption**: Data encrypted at rest in S3 and in transit
3. **Credential Management**: Sensitive credentials stored in AWS Secrets Manager
4. **Input Validation**: All user inputs validated before use
5. **Audit Logging**: Comprehensive logging for security auditing
