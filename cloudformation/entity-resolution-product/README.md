# AWS Entity Resolution Service Catalog Product

This directory contains CloudFormation templates for creating an AWS Service Catalog product that provisions AWS Entity Resolution resources.

## Files

- `entity-resolution-template.yaml`: Main CloudFormation template that creates the Entity Resolution resources (matching workflow, schema mapping, IAM roles, S3 bucket)
- `service-catalog-product.yaml`: CloudFormation template that creates the Service Catalog portfolio and product

## Deployment Instructions

1. First, upload the `entity-resolution-template.yaml` file to an S3 bucket in your AWS account:

```bash
aws s3 mb s3://${AWS_ACCOUNT_ID}-templates --region ${AWS_REGION}
aws s3 cp entity-resolution-template.yaml s3://${AWS_ACCOUNT_ID}-templates/
```

2. Deploy the Service Catalog portfolio and product:

```bash
aws cloudformation create-stack \
  --stack-name entity-resolution-service-catalog \
  --template-body file://service-catalog-product.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

3. Once deployed, users with access to the Service Catalog can provision the Entity Resolution resources through the AWS Console or AWS CLI.

## Parameters

### Service Catalog Portfolio and Product Parameters

- **PortfolioName**: Name of the portfolio
- **PortfolioDescription**: Description of the portfolio
- **PortfolioOwner**: Owner of the portfolio
- **ProductName**: Name of the product
- **ProductDescription**: Description of the product
- **ProductOwner**: Owner of the product
- **ProductSupportDescription**: Support information for the product

### Entity Resolution Template Parameters

- **EntityResolutionRoleName**: Name of the IAM role for Entity Resolution
- **S3BucketName**: Name of S3 bucket to store entity data
- **MatchingWorkflowName**: Name of the Entity Resolution Matching Workflow
- **SchemaName**: Name of the Entity Resolution Schema
- **InputSchemaAttributeNames**: Comma-separated list of attribute names (e.g., id,name,email,phone,address,company)

## Outputs

- **EntityResolutionServiceRoleArn**: IAM Role ARN for Entity Resolution
- **S3BucketName**: S3 Bucket Name for Entity Resolution Data
- **MatchingWorkflowArn**: Matching Workflow ARN
- **SchemaArn**: Schema ARN

## Architecture

The deployed resources create the following architecture:

1. **IAM Role** with permissions to access S3 and CloudWatch Logs
2. **S3 Bucket** for storing input data and outputs from the matching workflow
3. **Schema Mapping** that defines the structure of your entity data
4. **Matching Workflow** that performs the entity resolution process

The Entity Resolution service uses rule-based matching to identify records that represent the same entity, creating a golden record that can be used for downstream applications.
