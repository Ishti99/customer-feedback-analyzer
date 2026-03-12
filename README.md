\# Customer Feedback Analyzer



A serverless AWS pipeline that automatically analyzes customer feedback using AI.



\## Business Use Case

E-commerce businesses receive thousands of customer reviews daily. 

Manually reading and categorizing them is time-consuming and expensive. 

This system automatically analyzes feedback, categorizes sentiment, 

and stores results for business insights.



\## Architecture

```

Customer Feedback (CSV) 

→ Upload to S3 

→ Triggers Lambda 

→ Bedrock (Meta Llama) analyzes sentiment 

→ Results saved to DynamoDB

```



\## AWS Services Used

| Service | Purpose |

|---------|---------|

| Amazon S3 | Store uploaded customer feedback CSV files |

| AWS Lambda | Automatically trigger analysis when files are uploaded |

| Amazon Bedrock (Meta Llama) | Analyze and categorize feedback using AI |

| Amazon DynamoDB | Store analysis results |

| AWS CloudFormation | Deploy all infrastructure as code |



\## Project Structure

```

CustomerFeedbackAnalyzer/

├── src/

│   └── lambda\_function.py    ← Lambda function code

├── templates/

│   └── stack.yaml            ← CloudFormation template

├── sample\_data/

│   └── feedback.csv          ← Sample feedback data

└── README.md

```



\## Deployment Instructions



\### Prerequisites

\- AWS CLI installed and configured

\- Python 3.11+

\- AWS sandbox account with Bedrock access



\### Deploy Infrastructure

```bash

aws cloudformation deploy \\

&nbsp; --template-file templates/stack.yaml \\

&nbsp; --stack-name customer-feedback-analyzer \\

&nbsp; --capabilities CAPABILITY\_NAMED\_IAM \\

&nbsp; --region us-east-1

```



\### Upload Lambda Code

```bash

cd src

zip lambda.zip lambda\_function.py

aws lambda update-function-code \\

&nbsp; --function-name CustomerFeedbackAnalyzer \\

&nbsp; --zip-file fileb://lambda.zip \\

&nbsp; --region us-east-1

```



\### Test the Pipeline

```bash

aws s3 cp sample\_data/feedback.csv \\

&nbsp; s3://customer-feedback-ACCOUNT\_ID/feedback.csv \\

&nbsp; --region us-east-1

```



\## Cost Estimate

\- Total estimated cost: Less than $1.00

\- Most services fall within AWS free tier

\- Bedrock charges ~$0.01 for 15 feedback entries



\## Author

Ishtiaque - GSB 521 Capstone Project

Cal Poly

