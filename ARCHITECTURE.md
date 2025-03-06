# AWS Entity Resolution Architecture

This document provides a detailed architecture overview of the AWS Entity Resolution solution. The solution enables businesses to identify and link records that represent the same entities across disparate data sources.

## System Overview

The AWS Entity Resolution solution consists of three main components:

1. **Service Catalog Product**: A CloudFormation template that provisions AWS Entity Resolution resources
2. **Terraform Pipeline**: Infrastructure as Code (IaC) for the complete entity resolution data pipeline
3. **Python CLI**: A command-line tool for operating the pipeline

```mermaid
graph TB
    subgraph "Upstream Process"
        ExternalSource[External Data Source]
        ExternalSource -->|Export Data| S3Raw[S3 Raw Data]
    end

    subgraph "Solution Boundary"
        subgraph "Components"
            CF[CloudFormation Service Catalog]
            TF[Terraform Pipeline]
            PY[Python CLI]
        end

        subgraph "Infrastructure"
            ER[AWS Entity Resolution]
            S3[Amazon S3 Results]
            GT[AWS Glue Tables]
            SF[Snowflake Destination]
            Lambda[AWS Lambda]
            SFN[AWS Step Functions]
            CW[CloudWatch]
            EnvVars[Environment Variables]
        end

        S3Raw -->|Referenced by| GT
        CF -- "Provisions" --> ER
        TF -- "Deploys" --> S3
        TF -- "Deploys" --> Lambda
        TF -- "Deploys" --> SFN
        TF -- "Deploys" --> CW
        TF -- "Configures" --> ER
        TF -- "Creates" --> GT

        PY -- "Interacts with" --> Lambda
        PY -- "Interacts with" --> SFN
        PY -- "Interacts with" --> S3
        PY -- "Interacts with" --> ER
        PY -- "Interacts with" --> GT
        PY -- "Uses" --> EnvVars
    end

    style ExternalSource fill:#90CAF9,stroke:#1565C0
    style S3Raw fill:#FFE082,stroke:#FF8F00
    style CF fill:#FFCC80,stroke:#EF6C00
    style TF fill:#81C784,stroke:#2E7D32
    style PY fill:#64B5F6,stroke:#1565C0
    style ER fill:#CE93D8,stroke:#7B1FA2
    style S3 fill:#FFE082,stroke:#FF8F00
    style GT fill:#FFE082,stroke:#FF8F00
    style SF fill:#90CAF9,stroke:#1565C0
    style Lambda fill:#FFAB91,stroke:#D84315
    style SFN fill:#FFAB91,stroke:#D84315
    style CW fill:#90CAF9,stroke:#1565C0
    style EnvVars fill:#B39DDB,stroke:#512DA8
```

## Solution Boundary and Dependencies

The Entity Resolution pipeline starts with data that has already been exported from Snowflake to S3. This upstream data movement is **not part of this solution**. The solution boundary begins with:

1. Creating AWS Glue tables that reference the S3 data exported from Snowflake
2. Using AWS Entity Resolution to match entities based on Glue tables
3. Loading the matched results to Snowflake

## Data Flow Architecture

The entity resolution data pipeline follows a sequential flow of processing and loading:

```mermaid
sequenceDiagram
    participant ExtSource as External Data Source
    participant S3Raw as S3 Raw Data
    participant GT as AWS Glue Tables
    participant ER as AWS Entity Resolution
    participant S3Results as S3 Results
    participant Lambda as AWS Lambda
    participant SFDest as Snowflake Destination
    participant StepFn as AWS Step Functions
    participant EventTrigger as Optional Event Trigger Lambda

    ExtSource->>S3Raw: Export source data (upstream process)

    rect rgb(230, 230, 250)
    note right of S3Raw: Solution Boundary Begins

    EventTrigger->>StepFn: Optional event-driven trigger
    StepFn->>Lambda: Initiate pipeline

    Lambda->>GT: Create/update Glue table
    S3Raw-->>GT: Glue table references S3 data

    Lambda->>GT: Verify Glue table is ready
    GT-->>Lambda: Table ready
    Lambda->>ER: Configure matching workflow
    Lambda->>ER: Start matching job
    ER->>GT: Read source data from Glue tables
    ER->>ER: Perform matching
    ER->>S3Results: Write matched results (with optional KMS encryption)
    S3Results-->>Lambda: Notify matching complete
    Lambda->>S3Results: Read matched data
    Lambda->>SFDest: Load golden records
    Lambda-->>StepFn: Complete pipeline

    end
```

## Component Architecture

### 1. CloudFormation Service Catalog Product

The CloudFormation template provisions AWS Entity Resolution resources and creates a Service Catalog product for easy deployment.

```mermaid
graph TB
    subgraph "Service Catalog Product"
        Template[CloudFormation Template]
        Params[Parameters]
        SC[Service Catalog]

        Template -- "Uses" --> Params
        Template -- "Creates" --> SC
    end

    subgraph "AWS Resources"
        Schema[Schema Mapping]
        Workflow[Matching Workflow]
        IAMRoles[IAM Roles]
        S3Buckets[S3 Buckets]
        IdNamespace[ID Namespace]
        MatchingRules[Matching Rules]
        GluePolicies[Glue Policies]
    end

    Template -- "Creates" --> Schema
    Template -- "Creates" --> Workflow
    Template -- "Creates" --> IAMRoles
    Template -- "Creates" --> S3Buckets
    Template -- "Creates" --> IdNamespace
    Template -- "Creates" --> MatchingRules
    Template -- "Creates" --> GluePolicies

    Schema -- "Used by" --> Workflow
    IdNamespace -- "Used by" --> Workflow
    MatchingRules -- "Used by" --> Workflow

    style Template fill:#FFCC80,stroke:#EF6C00
    style Params fill:#FFCC80,stroke:#EF6C00
    style SC fill:#FFCC80,stroke:#EF6C00
    style Schema fill:#CE93D8,stroke:#7B1FA2
    style Workflow fill:#CE93D8,stroke:#7B1FA2
    style IAMRoles fill:#B39DDB,stroke:#512DA8
    style S3Buckets fill:#FFE082,stroke:#FF8F00
    style IdNamespace fill:#CE93D8,stroke:#7B1FA2
    style MatchingRules fill:#CE93D8,stroke:#7B1FA2
    style GluePolicies fill:#B39DDB,stroke:#512DA8
```

### 2. Terraform Pipeline

The Terraform pipeline deploys the infrastructure necessary for the complete data flow:

```mermaid
graph TB
    subgraph "Terraform Modules"
        Main[Main Module]
        GlueMod[Glue Module]
        ProcessorMod[Processor Module]
        LoaderMod[Loader Module]
        OrchestratorMod[Orchestrator Module]
        MonitoringMod[Monitoring Module]
        EventTriggerMod[Event Trigger Module]
    end

    subgraph "AWS Resources"
        LambdaGlue[Glue Table Lambda]
        LambdaProcess[Process Lambda]
        LambdaLoad[Load Lambda]
        LambdaCheck[Check Status Lambda]
        LambdaNotify[Notification Lambda]
        LambdaTrigger[Event Trigger Lambda]

        S3Results[Results S3 Bucket]
        ExistingS3[Pre-created S3 Bucket]
        GlueTables[Glue Tables]
        KMSKey[KMS Key]

        StateMachine[Step Functions State Machine]

        CWDashboard[CloudWatch Dashboard]
        CWAlarms[CloudWatch Alarms]
    end

    Main -- "Uses" --> GlueMod
    Main -- "Uses" --> ProcessorMod
    Main -- "Uses" --> LoaderMod
    Main -- "Uses" --> OrchestratorMod
    Main -- "Uses" --> MonitoringMod
    Main -- "Uses" --> EventTriggerMod

    GlueMod -- "Creates" --> LambdaGlue
    GlueMod -- "Creates" --> GlueTables

    ProcessorMod -- "Creates" --> LambdaProcess
    ProcessorMod -- "Creates" --> LambdaCheck
    ProcessorMod -- "References" --> ExistingS3
    ProcessorMod -- "References" --> KMSKey

    LoaderMod -- "Creates" --> LambdaLoad
    LoaderMod -- "Creates/References" --> S3Results

    OrchestratorMod -- "Creates" --> StateMachine
    OrchestratorMod -- "Creates" --> LambdaNotify

    EventTriggerMod -- "Creates" --> LambdaTrigger

    MonitoringMod -- "Creates" --> CWDashboard
    MonitoringMod -- "Creates" --> CWAlarms

    style Main fill:#81C784,stroke:#2E7D32
    style GlueMod fill:#81C784,stroke:#2E7D32
    style ProcessorMod fill:#81C784,stroke:#2E7D32
    style LoaderMod fill:#81C784,stroke:#2E7D32
    style OrchestratorMod fill:#81C784,stroke:#2E7D32
    style MonitoringMod fill:#81C784,stroke:#2E7D32
    style EventTriggerMod fill:#81C784,stroke:#2E7D32

    style LambdaGlue fill:#FFAB91,stroke:#D84315
    style LambdaProcess fill:#FFAB91,stroke:#D84315
    style LambdaLoad fill:#FFAB91,stroke:#D84315
    style LambdaCheck fill:#FFAB91,stroke:#D84315
    style LambdaNotify fill:#FFAB91,stroke:#D84315
    style LambdaTrigger fill:#FFAB91,stroke:#D84315

    style S3Results fill:#FFE082,stroke:#FF8F00
    style ExistingS3 fill:#FFE082,stroke:#FF8F00
    style GlueTables fill:#FFE082,stroke:#FF8F00
    style KMSKey fill:#B39DDB,stroke:#512DA8

    style StateMachine fill:#FFAB91,stroke:#D84315

    style CWDashboard fill:#90CAF9,stroke:#1565C0
    style CWAlarms fill:#90CAF9,stroke:#1565C0
```

### 3. Python CLI

The Python CLI provides a user-friendly interface to interact with the AWS Entity Resolution pipeline:

```mermaid
graph TB
    subgraph "CLI Main Components"
        CLI[Main CLI]
        Config[Configuration]
        Commands[Commands]
        EnvVars[Environment Variables]
    end

    subgraph "CLI Commands"
        Glue[Glue Command]
        Process[Process Command]
        Load[Load Command]
        Pipeline[Pipeline Command]
        Status[Status Command]
        Config[Config Command]
    end

    subgraph "Utils & Services"
        AWSUtils[AWS Utilities]
        Services[AWS Services]
        Utils[Utilities]
        Types[Type Definitions]
    end

    CLI -- "Uses" --> Commands
    CLI -- "Uses" --> Config
    CLI -- "Reads" --> EnvVars
    Config -- "Uses" --> EnvVars

    Commands --> Glue
    Commands --> Process
    Commands --> Load
    Commands --> Pipeline
    Commands --> Status
    Commands --> Config

    Glue -- "Uses" --> AWSUtils
    Glue -- "Uses" --> Services
    Process -- "Uses" --> AWSUtils
    Process -- "Uses" --> Services
    Load -- "Uses" --> AWSUtils
    Load -- "Uses" --> Services
    Pipeline -- "Uses" --> AWSUtils
    Pipeline -- "Uses" --> Services

    AWSUtils -- "Uses" --> Types
    Services -- "Uses" --> Types
    Utils -- "Uses" --> Types

    style CLI fill:#64B5F6,stroke:#1565C0
    style Commands fill:#64B5F6,stroke:#1565C0
    style Config fill:#FFD54F,stroke:#FF8F00
    style EnvVars fill:#B39DDB,stroke:#512DA8

    style Glue fill:#64B5F6,stroke:#1565C0
    style Process fill:#64B5F6,stroke:#1565C0
    style Load fill:#64B5F6,stroke:#1565C0
    style Pipeline fill:#64B5F6,stroke:#1565C0
    style Status fill:#64B5F6,stroke:#1565C0
    style Config fill:#64B5F6,stroke:#1565C0

    style AWSUtils fill:#FFD54F,stroke:#FF8F00
    style Services fill:#FFD54F,stroke:#FF8F00
    style Utils fill:#FFD54F,stroke:#FF8F00
    style Types fill:#FFD54F,stroke:#FF8F00
```

## AWS Entity Resolution Workflow

The entity resolution process utilizes AWS Entity Resolution service to match and link records:

```mermaid
graph LR
    subgraph "Input Data"
        SourceA[Source A]
        SourceB[Source B]
        SourceC[Source C]
    end

    subgraph "Entity Resolution Process"
        Schema[Schema Mapping]
        Rules[Matching Rules]
        Workflow[Matching Workflow]

        Schema --> Workflow
        Rules --> Workflow
    end

    subgraph "Output Data"
        GoldenRecords[Golden Records]
        MatchGroups[Match Groups]
        UnmatchedRecords[Unmatched Records]
    end

    SourceA --> Schema
    SourceB --> Schema
    SourceC --> Schema

    Workflow --> GoldenRecords
    Workflow --> MatchGroups
    Workflow --> UnmatchedRecords

    style SourceA fill:#B2DFDB,stroke:#00796B
    style SourceB fill:#B2DFDB,stroke:#00796B
    style SourceC fill:#B2DFDB,stroke:#00796B

    style Schema fill:#CE93D8,stroke:#7B1FA2
    style Rules fill:#CE93D8,stroke:#7B1FA2
    style Workflow fill:#CE93D8,stroke:#7B1FA2

    style GoldenRecords fill:#C8E6C9,stroke:#2E7D32
    style MatchGroups fill:#C8E6C9,stroke:#2E7D32
    style UnmatchedRecords fill:#C8E6C9,stroke:#2E7D32
```

## Step Functions State Machine

The Step Functions state machine orchestrates the entity resolution pipeline:

```mermaid
stateDiagram-v2
    [*] --> Initialize

    state "External Events" as External {
        [*] --> EventTrigger
        EventTrigger --> [*]
    }

    External --> Initialize: Trigger
    Initialize --> Process
    Process --> CheckProcess

    CheckProcess --> Load: Success
    CheckProcess --> FailureState: Error

    Load --> CheckLoad

    CheckLoad --> Notify: Success
    CheckLoad --> FailureState: Error

    Notify --> [*]
    FailureState --> Notify

    state Initialize {
        [*] --> ValidateConfig
        ValidateConfig --> SetupEnvironment
        SetupEnvironment --> [*]
    }

    state Process {
        [*] --> InvokeProcessLambda
        InvokeProcessLambda --> WaitForProcessComplete
        WaitForProcessComplete --> [*]
    }

    state Load {
        [*] --> InvokeLoadLambda
        InvokeLoadLambda --> WaitForLoadComplete
        WaitForLoadComplete --> [*]
    }
```

## Security Architecture

The solution implements a comprehensive security model:

```mermaid
graph TB
    subgraph "Data Security"
        Encryption[Data Encryption]
        Access[Access Controls]
        Secrets[Secrets Management]
    end

    subgraph "Network Security"
        VPC[VPC Configuration]
        SecurityGroups[Security Groups]
        Endpoints[VPC Endpoints]
    end

    subgraph "Identity & Access"
        IAMRoles[IAM Roles]
        Policies[IAM Policies]
        LeastPrivilege[Least Privilege]
    end

    subgraph "Monitoring & Compliance"
        CloudTrail[AWS CloudTrail]
        CloudWatch[CloudWatch Logs]
        Alerting[Security Alerting]
    end

    Encryption --> S3Encryption[S3 Encryption]
    Encryption --> TransitEncryption[Transit Encryption]
    Encryption --> KMS[KMS Key Management]

    Access --> S3Policies[S3 Bucket Policies]
    Access --> ResourcePolicies[Resource Policies]

    Secrets --> SecretsManager[AWS Secrets Manager]

    IAMRoles --> LambdaRole[Lambda Execution Role]
    IAMRoles --> ERRole[Entity Resolution Role]

    Policies --> BoundaryPolicies[Permission Boundaries]
    Policies --> SCPPolicies[Service Control Policies]

    style Encryption fill:#E1BEE7,stroke:#6A1B9A
    style Access fill:#E1BEE7,stroke:#6A1B9A
    style Secrets fill:#E1BEE7,stroke:#6A1B9A
    style VPC fill:#BBDEFB,stroke:#1565C0
    style SecurityGroups fill:#BBDEFB,stroke:#1565C0
    style Endpoints fill:#BBDEFB,stroke:#1565C0
    style IAMRoles fill:#B39DDB,stroke:#512DA8
    style Policies fill:#B39DDB,stroke:#512DA8
    style LeastPrivilege fill:#B39DDB,stroke:#512DA8
    style CloudTrail fill:#90CAF9,stroke:#1565C0
    style CloudWatch fill:#90CAF9,stroke:#1565C0
    style Alerting fill:#90CAF9,stroke:#1565C0
```

## Implementation Considerations

### Scalability

The solution is designed to scale with data volume:

- Step Functions handles workflow orchestration at scale
- AWS Entity Resolution is a managed service that scales automatically
- Lambda functions automatically scale to handle concurrent requests

### Availability

The solution is designed for high availability:

- Uses managed AWS services with built-in redundancy
- Distributes resources across multiple Availability Zones
- Implements retry logic for transient failures
- Uses Step Functions to maintain workflow state

### Monitoring

Comprehensive monitoring is provided through:

- CloudWatch Dashboards with custom metrics
- CloudWatch Alarms for critical thresholds
- CloudWatch Logs for detailed logging
- Step Functions execution history
- SNS notifications for workflow events

### Cost Optimization

Cost optimization strategies include:

- Lambda functions sized appropriately for workload
- S3 lifecycle policies for aging data
- Scheduled workflows to run during off-peak hours
- Intelligent retry logic to minimize retries

## Integration Points

The solution integrates with external systems in several ways:

1. **Data Source Integration**:
   - Supports any external data source that can output to S3
   - Provides flexible options for data formats and schema mappings

2. **Snowflake Integration**:
   - Uses Snowflake Python Connector for data loading
   - Manages credentials via environment variables

3. **API Integration**:
   - Optional event-driven Lambda trigger for pipeline events
   - Exposes Lambda functions via API Gateway (optional)
   - Provides CLI interface for programmatic access
   - Supports webhook notifications for pipeline events

4. **S3 and KMS Integration**:
   - Supports pre-created S3 buckets with custom policies
   - Works with existing KMS keys for encryption

5. **Monitoring Integration**:
   - CloudWatch metrics can be integrated with existing monitoring tools
   - SNS topics can be subscribed to by external systems
   - CloudWatch Logs can be streamed to third-party logging systems
