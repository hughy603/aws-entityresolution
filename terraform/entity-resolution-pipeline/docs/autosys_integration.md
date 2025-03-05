# Autosys Integration for AWS Entity Resolution

This guide provides instructions for integrating AWS Entity Resolution with Autosys for scheduling and monitoring long-running entity resolution jobs.

## Overview

The integration allows you to:

1. Schedule entity resolution jobs for different data domains
2. Handle long-running jobs that exceed Lambda timeouts
3. Monitor job status and handle failures
4. Generate domain-specific configuration parameters
5. Support both recurring and on-demand processing

## Prerequisites

Before setting up the integration, ensure you have:

1. Autosys Environment:
   - Autosys 12.0 or later installed
   - Proper access permissions to create and manage jobs

2. AWS Environment:
   - AWS CLI installed and configured
   - Proper IAM permissions for Step Functions and Lambda
   - Entity Resolution pipeline deployed via Terraform

3. Configuration Requirements:
   - Configuration files for each data domain
   - Network access from Autosys servers to AWS APIs

## Installation Steps

### 1. Copy Scripts to Autosys Server

Copy the following scripts to your Autosys server in a dedicated directory:

```bash
# Create directory for scripts
mkdir -p /path/to/entity-resolution-pipeline/scripts

# Copy scripts from your Terraform directory
cp terraform/entity-resolution-pipeline/scripts/run_entity_resolution.sh /path/to/entity-resolution-pipeline/scripts/
cp terraform/entity-resolution-pipeline/scripts/run_entity_resolution_domain.sh /path/to/entity-resolution-pipeline/scripts/
cp terraform/entity-resolution-pipeline/scripts/generate_entity_resolution_params.py /path/to/entity-resolution-pipeline/scripts/
cp terraform/entity-resolution-pipeline/scripts/config.json /path/to/entity-resolution-pipeline/scripts/
```

### 2. Set Up AWS Credentials

Ensure the Autosys server has appropriate AWS credentials configured:

```bash
# Create AWS profile for Autosys
mkdir -p /etc/autosys/profiles
cat > /etc/autosys/profiles/aws_profile << EOF
export AWS_PROFILE=entity-resolution
export AWS_REGION=us-east-1
export PATH=$PATH:/usr/local/bin  # Ensure AWS CLI is in path
EOF

# Set up AWS credentials (use IAM roles if possible)
aws configure --profile entity-resolution
```

### 3. Create Log Directories

Set up log directories for job output:

```bash
# Create log directories
mkdir -p /var/log/autosys/entity-resolution/{customers,products,vendors}
chmod -R 755 /var/log/autosys/entity-resolution
```

### 4. Prepare Domain Configuration

Edit the `config.json` file with appropriate values for your environment:

```bash
# Edit configuration file
vi /path/to/entity-resolution-pipeline/scripts/config.json
```

Ensure each domain has the correct:
- Project name
- S3 bucket
- Entity Resolution workflow name
- Source and target tables
- Entity attributes

### 5. Load Autosys Job Definitions

Load the job definitions into Autosys:

```bash
# Create JIL file
cp terraform/entity-resolution-pipeline/scripts/domain_entity_resolution_jobs.jil /tmp/

# Update paths in JIL file if necessary
sed -i 's|/path/to/entity-resolution-pipeline|/your/actual/path|g' /tmp/domain_entity_resolution_jobs.jil

# Load job definitions
jil < /tmp/domain_entity_resolution_jobs.jil
```

## Job Configuration

### Domain-Specific Jobs

The integration includes three domain-specific jobs with different schedules:

1. **ER_CUSTOMER_DAILY**: Runs daily at 3:00 AM Eastern
2. **ER_PRODUCT_WEEKLY**: Runs weekly on Sundays at 5:00 AM Eastern
3. **ER_VENDOR_MONTHLY**: Runs monthly at the beginning of the month

Each job uses `run_entity_resolution_domain.sh` with a specific domain parameter.

### On-Demand Job

The **ER_ON_DEMAND** job can be used for ad-hoc processing of any domain. You can override the default parameters when submitting the job:

```bash
# Run on-demand job for products with a specific date
sendevent -E CHANGE_STATUS -s ACTIVATED -J ER_ON_DEMAND -g "DOMAIN=\"products\",PROCESS_DATE=\"2023-10-15\""
```

### Sequential Job Processing

The integration includes an enhanced approach that splits entity resolution into three sequential stages to help with failure recovery:

1. **Extract Stage**: Extracts data from Snowflake to S3
2. **Process Stage**: Runs AWS Entity Resolution on the extracted data
3. **Load Stage**: Loads the matched results back to Snowflake

This sequential approach provides several key benefits:
- Allows for restart from the point of failure without repeating completed work
- Maintains state between steps using metadata files
- Provides more granular monitoring and error handling
- Optimizes resource usage by scaling each stage appropriately

#### Sequential Job Structure

Each domain has a dedicated box job containing three dependent command jobs:

```
ER_CUSTOMER_BOX
  └── ER_CUSTOMER_EXTRACT
      └── ER_CUSTOMER_PROCESS (runs when extract succeeds)
          └── ER_CUSTOMER_LOAD (runs when process succeeds)
```

Example JIL for these jobs can be found in `domain_entity_resolution_sequential_jobs.jil`.

#### Using Sequential Job Processing

To use the sequential approach:

1. Load the sequential job definitions:
   ```bash
   jil < domain_entity_resolution_sequential_jobs.jil
   ```

2. Schedule or trigger the box job:
   ```bash
   sendevent -E CHANGE_STATUS -s ACTIVATED -J ER_CUSTOMER_BOX
   ```

3. Monitor the progress through each stage:
   ```bash
   autorep -J ER_CUSTOMER_EXTRACT -d
   autorep -J ER_CUSTOMER_PROCESS -d
   autorep -J ER_CUSTOMER_LOAD -d
   ```

4. In case of failure, you can restart from a specific stage:
   ```bash
   # If process stage failed but extract completed successfully
   sendevent -E CHANGE_STATUS -s ACTIVATED -J ER_CUSTOMER_PROCESS
   ```

#### Metadata Persistence

Each stage maintains state in a metadata file:
```
/tmp/entity_resolution_metadata_${DOMAIN}_${PROCESS_DATE}.json
```

This file contains information that passes from one stage to the next, including:
- Input and output S3 paths
- Record counts and match rates
- Processing timestamps
- Table references

### Job Parameters

The following parameters can be adjusted for each job:

| Parameter | Description | Default |
|-----------|-------------|---------|
| DOMAIN | Data domain to process | varies by job |
| PROCESS_DATE | Date to process | current date |
| CONFIG_FILE | Configuration file path | config.json |
| EXECUTION_TIMEOUT | Maximum job runtime in seconds | 10800 (3 hours) |
| CHECK_INTERVAL | Status check frequency in seconds | 300 (5 minutes) |
| STAGE | Processing stage (extract, process, load) | Required parameter |

## Job Monitoring and Troubleshooting

### Monitoring Jobs

Monitor job execution through the Autosys interface or command line:

```bash
# Check job status
autorep -J ER_CUSTOMER_DAILY -d

# View job logs
cat /var/log/autosys/entity-resolution/customers/ER_CUSTOMER_DAILY.out

# Check detailed processing logs
ls -la /var/log/autosys/entity-resolution/customers/
```

### Common Issues and Solutions

1. **AWS Credentials Expired**:
   - Error: "Unable to locate credentials"
   - Solution: Refresh AWS credentials in the profile

2. **Job Timeout**:
   - Error: "Entity Resolution pipeline execution timed out"
   - Solution: Increase `EXECUTION_TIMEOUT` or split data into smaller batches

3. **Missing Configuration**:
   - Error: "Domain 'xyz' not found in configuration"
   - Solution: Add the domain to `config.json`

4. **AWS Step Functions Failure**:
   - Check Step Functions execution history in AWS Console
   - Review CloudWatch logs for the failed Lambda function

## Security Considerations

1. **AWS Credentials**: Use IAM roles with temporary credentials instead of long-term access keys where possible

2. **Permission Management**: Follow the principle of least privilege for Autosys and AWS IAM roles

3. **Logging**: Regularly rotate logs and secure access to log directories

4. **Network Security**: Ensure proper VPC and security group configurations for AWS access

## Advanced Configuration

### Job Dependencies

You can create job dependencies for complex workflows:

```
insert_job: ER_DATA_PREP job_type: c
command: /path/to/data_prep_script.sh
condition: s(ER_CUSTOMER_DAILY)
```

### Job Notifications

The Entity Resolution jobs include comprehensive notification capabilities to keep teams informed of job status:

#### Email Notification System

Email notifications are configured for:
1. **Failure Notifications**: Sent for all jobs when they fail to complete successfully
2. **Success Notifications**: Sent when the final load stage completes successfully

The notifications use variables to define email recipients, allowing for easy updates:

```
/* Email notification variables */
define_variable: ER_ADMIN_EMAIL="er-admin@example.com"
define_variable: ER_TEAM_EMAIL="er-team@example.com"
define_variable: ER_CUSTOMER_DOMAIN_EMAIL="customer-team@example.com"
```

#### Notification Strategy

The notification strategy is designed to provide actionable alerts:

1. **Targeted Notifications**: Different teams receive notifications based on the domain (customers, products, vendors)
2. **Early Failure Detection**: All stages send failure notifications for immediate awareness
3. **Success Confirmation**: Final stage sends success notifications to confirm end-to-end completion
4. **Admin Oversight**: Administrators receive all notifications for complete visibility

#### Customizing Notifications

To customize email recipients:

1. Edit the email variables at the top of the JIL file:
   ```
   define_variable: ER_ADMIN_EMAIL="your-admin@example.com"
   ```

2. Or modify individual job notifications:
   ```
   notification: success("specific-person@example.com"),fail("on-call@example.com")
   ```

3. Additional notification options:
   ```
   notification: complete("team@example.com")  /* Sends for all completions (success or failure) */
   notification: run("start-notify@example.com")  /* Sends when job starts running */
   ```

### Job Monitoring via AWS CloudWatch

Set up CloudWatch Alarms to monitor Step Functions executions:

### Data Quality Check Jobs

To ensure data integrity throughout the pipeline, implement data quality check jobs:

```jil
/* PRE-PROCESSING DATA QUALITY CHECK */
insert_job: ER_CUSTOMER_DQ_CHECK job_type: c
description: "Validate data quality before processing"
owner: autosys
alarm_if_fail: 1
box_name: ER_CUSTOMER_BOX
permission: gx,ge,wx,we
notification: fail("${ER_ADMIN_EMAIL},${ER_CUSTOMER_DOMAIN_EMAIL}")
condition: n(ER_CUSTOMER_EXTRACT)
std_out_file: "/var/log/autosys/entity-resolution/customers/ER_CUSTOMER_DQ_CHECK.out"
command: /path/to/entity-resolution-pipeline/scripts/run_data_quality_checks.sh --domain customers --stage pre-process
```

These data quality jobs perform essential validations:

1. **Pre-Process Checks**:
   - Verify minimum record count thresholds
   - Check for required fields
   - Validate data format and values
   - Detect anomalies from historical patterns

2. **Post-Process Checks**:
   - Verify match rates against acceptable thresholds
   - Check for data loss between stages
   - Compare results against historical baselines

Sample thresholds can be defined in a configuration file:

```json
{
  "customers": {
    "min_records": 1000,
    "required_fields": ["customer_id", "name", "address"],
    "min_match_rate": 60,
    "max_match_rate": 95
  }
}
```

Implementing these checks can prevent processing bad data and catch issues early.

### Job Dependency Graph and History Tracking

To better understand and visualize job dependencies and execution history, implement the following enhancements:

#### Job History Database

Create a dedicated database to track all job executions:

```sql
CREATE TABLE er_job_history (
  job_id VARCHAR(50),
  job_name VARCHAR(100),
  domain VARCHAR(50),
  stage VARCHAR(20),
  process_date DATE,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status VARCHAR(20),
  record_count INTEGER,
  duration_seconds INTEGER,
  exit_code INTEGER,
  error_message TEXT,
  metadata JSONB
);
```

The script can then log execution details to this table at the start and end of each job:

```bash
# Update job history at the beginning of execution
update_job_history_start() {
  psql -c "INSERT INTO er_job_history
           (job_id, job_name, domain, stage, process_date, start_time, status)
           VALUES ('$JOB_ID', '$JOB_NAME', '$DOMAIN', '$STAGE',
                  '$PROCESS_DATE', CURRENT_TIMESTAMP, 'RUNNING');"
}

# Update job history at the end of execution
update_job_history_end() {
  STATUS=$1
  EXIT_CODE=$2
  ERROR_MSG=$3
  RECORD_COUNT=$4
  DURATION=$5
  METADATA=$6

  psql -c "UPDATE er_job_history
           SET status='$STATUS',
               end_time=CURRENT_TIMESTAMP,
               record_count=$RECORD_COUNT,
               duration_seconds=$DURATION,
               exit_code=$EXIT_CODE,
               error_message='$ERROR_MSG',
               metadata='$METADATA'
           WHERE job_id='$JOB_ID' AND start_time=(
             SELECT MAX(start_time) FROM er_job_history WHERE job_id='$JOB_ID'
           );"
}
```

#### Job Dependency Visualization

Create a tool to visualize job dependencies using the DOT language and Graphviz:

1. Extract job dependencies from JIL files:

```bash
#!/bin/bash
# extract_job_dependencies.sh
JIL_FILE=$1
OUTPUT_DOT_FILE=$2

echo "digraph G {" > $OUTPUT_DOT_FILE
echo "  rankdir=LR;" >> $OUTPUT_DOT_FILE
echo "  node [shape=box];" >> $OUTPUT_DOT_FILE

# Extract box jobs
grep -E "^insert_job: .* job_type: BOX" $JIL_FILE | cut -d':' -f2 | cut -d' ' -f1 | while read box_job; do
  echo "  \"$box_job\" [color=blue];" >> $OUTPUT_DOT_FILE
done

# Extract job dependencies
grep -E "^box_name: " $JIL_FILE | while read line; do
  job_name=$(grep -B1 "$line" $JIL_FILE | head -1 | cut -d':' -f2 | cut -d' ' -f1)
  box_name=$(echo $line | cut -d':' -f2 | tr -d ' ')
  echo "  \"$box_name\" -> \"$job_name\";" >> $OUTPUT_DOT_FILE
done

# Extract condition dependencies
grep -E "^condition: " $JIL_FILE | while read line; do
  job_name=$(grep -B1 "$line" $JIL_FILE | head -1 | cut -d':' -f2 | cut -d' ' -f1)
  condition=$(echo $line | cut -d':' -f2 | tr -d ' ')
  # Extract job name from condition (assuming s(JOB_NAME) format)
  if [[ $condition == s\(*\) ]]; then
    dependency=$(echo $condition | sed 's/s(\(.*\))/\1/')
    echo "  \"$dependency\" -> \"$job_name\" [style=dashed];" >> $OUTPUT_DOT_FILE
  fi
done

echo "}" >> $OUTPUT_DOT_FILE
```

2. Generate the visualization:

```bash
# Generate a PNG visualization
dot -Tpng -o job_dependencies.png job_dependencies.dot

# Generate an interactive HTML visualization
dot -Tsvg -o job_dependencies.svg job_dependencies.dot
```

This visualization helps understand the job flow and can be included in documentation or dashboards.

#### Sample Job History Dashboard

Create a dashboard to visualize job execution history and identify trends:

- **Job Success Rate**: Show success/failure percentage by domain and date
- **Execution Duration**: Track how long each job takes over time
- **SLA Compliance**: Visualize how often jobs complete within SLA
- **Record Volume**: Track data volume processed over time
- **Error Frequency**: Identify most common failure reasons

The dashboard can be built using Grafana connected to the history database, or using AWS QuickSight if the metrics are stored in CloudWatch.
