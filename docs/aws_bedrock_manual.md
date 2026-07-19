# AWS Bedrock Integration Manual

## Incident: Inference Timeouts or Global API Failures
If the LLMOps platform begins experiencing 500 errors, generic exceptions, or extended latency (>10s) specifically when making generation calls to the AWS Bedrock APIs (e.g., Claude models):

**Standard Diagnosis:**
First, verify the AWS Health Dashboard. Often, Bedrock API timeouts or generic errors originate from a regional instability on the AWS side (e.g., `us-east-1` capacity issues) rather than our internal infrastructure.

**Mitigation Action (Level 1):**
1. Check the AWS Health Dashboard for the region. If there is a declared outage or "Increased Error Rates" for Amazon Bedrock, the incident is external.
2. If confirmed external, failover the traffic by updating the `AWS_REGION` environment variable from `us-east-1` to a fallback region (e.g., `us-west-2` or `eu-central-1`) and restart the deployment.
3. If no external AWS issue is reported, verify if the IAM Roles associated with the EKS pods lack `bedrock:InvokeModel` permissions.
