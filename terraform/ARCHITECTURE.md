# Entity Resolution Pipeline Architecture

This document describes the architecture of the Entity Resolution pipeline implemented using AWS services and Terraform modules.

## Module Structure

```mermaid
graph TB
    subgraph "Environment Modules"
        DEV[Dev Environment]
        STG[Staging Environment]
        PRD[Production Environment]
    end

    subgraph "Core Modules"
        LF[Lambda Functions]
        SF[Step Functions]
        SEC[Security]
        MON[Monitoring]
        SCH[Schema]
    end

    subgraph "Lambda Function Modules"
        LD[Load Data]
        CS[Check Status]
        PO[Process Output]
        NO[Notify]
    end

    DEV --> LF
    DEV --> SF
    DEV --> SEC
    DEV --> MON
    DEV --> SCH

    STG --> LF
    STG --> SF
    STG --> SEC
    STG --> MON
    STG --> SCH

    PRD --> LF
    PRD --> SF
    PRD --> SEC
    PRD --> MON
    PRD --> SCH

    LF --> LD
    LF --> CS
    LF --> PO
    LF --> NO
```

## Infrastructure Flow

```mermaid
graph TB
    subgraph "Data Input"
        S3[S3 Bucket] --> |Input Data| SFN
    end

    subgraph "Step Functions Workflow"
        SFN[Step Functions State Machine]
        SFN --> |Trigger| L1[Load Data Lambda]
        L1 --> |Start Job| ER[Entity Resolution Service]
        ER --> |Job Status| L2[Check Status Lambda]
        L2 --> |Complete| OUT[Process Output Lambda]
        L2 --> |In Progress| L2
        L2 --> |Failed| ERR[Notify Lambda]
    end

    subgraph "Data Processing"
        ER
    end

    subgraph "Output Handling"
        OUT --> |Results| S3OUT[S3 Output Bucket]
        ERR --> |Notifications| SNS[SNS Topic]
    end

    subgraph "Monitoring"
        CW[CloudWatch]
        L1 --> |Logs| CW
        L2 --> |Logs| CW
        ER --> |Metrics| CW
        SFN --> |Execution Logs| CW
        OUT --> |Logs| CW
        ERR --> |Logs| CW
    end

    subgraph "Security"
        IAM[IAM Roles]
        VPC[VPC]
        SG[Security Groups]
        IAM --> |Permissions| L1
        IAM --> |Permissions| L2
        IAM --> |Permissions| OUT
        IAM --> |Permissions| ERR
        VPC --> |Network| L1
        VPC --> |Network| L2
        VPC --> |Network| OUT
        SG --> |Access Control| L1
        SG --> |Access Control| L2
        SG --> |Access Control| OUT
    end
```

## Directory Structure

```
terraform/
├── modules/
│   ├── lambda-functions/
│   │   ├── load-data/
│   │   ├── check-status/
│   │   ├── process-output/
│   │   └── notify/
│   ├── step-functions/
│   ├── security/
│   ├── monitoring/
│   └── schema/
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

## Module Dependencies

Each environment module (`dev`, `staging`, `prod`) orchestrates the following components:

1. **Lambda Functions**
   - Load Data: Handles initial data ingestion
   - Check Status: Monitors job progress
   - Process Output: Handles successful job results
   - Notify: Manages error notifications

2. **Step Functions**
   - State Machine: Orchestrates the workflow
   - Error Handling: Manages failures and retries
   - Monitoring: Tracks execution status

3. **Security**
   - IAM Roles: Least privilege access
   - VPC Configuration: Network isolation
   - Security Groups: Access control

4. **Monitoring**
   - CloudWatch Logs: Centralized logging
   - CloudWatch Metrics: Performance monitoring
   - CloudWatch Alarms: Automated alerting

5. **Schema Management**
   - Version Control: Schema versioning
   - Validation: Data quality checks
   - Documentation: Schema documentation

## Security Architecture

1. **Network Security**
   - Lambda functions run in VPC
   - Security groups control access
   - VPC endpoints for AWS services

2. **Identity and Access**
   - IAM roles follow least privilege
   - Resource-based policies
   - Service-linked roles

3. **Data Protection**
   - S3 bucket encryption
   - CloudWatch log encryption
   - In-transit encryption

## Deployment Strategy

1. **Environment Separation**
   - Separate state files
   - Environment-specific variables
   - Consistent tagging

2. **State Management**
   - Remote state in S3
   - State locking with DynamoDB
   - Backup and versioning

3. **CI/CD Integration**
   - Automated testing
   - Infrastructure validation
   - Deployment approval process
