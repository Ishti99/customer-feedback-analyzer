import json
import boto3
import csv
import os
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

# DynamoDB table name from environment variable
TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'CustomerFeedback')

def analyze_feedback(feedback_text):
    """Send feedback to Bedrock Meta Llama for analysis"""
    
    prompt = f"""Analyze this customer feedback and respond in JSON format only:
{{
    "sentiment": "Positive or Negative or Neutral",
    "summary": "one sentence summary",
    "category": "Product Quality or Customer Service or Shipping or Price or Other"
}}

Feedback: {feedback_text}"""

    body = json.dumps({
        "prompt": prompt,
        "max_gen_len": 200,
        "temperature": 0.1
    })

    response = bedrock.invoke_model(
        modelId='meta.llama3-8b-instruct-v1:0',
        body=body
    )

    result = json.loads(response['body'].read())
    response_text = result['generation'].strip()
    
    # Extract JSON from response
    start = response_text.find('{')
    end = response_text.rfind('}') + 1
    json_str = response_text[start:end]
    
    return json.loads(json_str)

def lambda_handler(event, context):
    """Main Lambda function triggered by S3 upload"""
    
    # Get bucket and file info from S3 event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(f"Processing file: {key} from bucket: {bucket}")
    
    # Download file from S3
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    
    # Parse CSV
    table = dynamodb.Table(TABLE_NAME)
    reader = csv.DictReader(content.splitlines())
    
    results = []
    for row in reader:
        customer_id = row['customer_id']
        feedback = row['feedback']
        
        print(f"Analyzing feedback for customer: {customer_id}")
        
        # Analyze with Bedrock
        analysis = analyze_feedback(feedback)
        
        # Save to DynamoDB
        item = {
            'customer_id': customer_id,
            'timestamp': datetime.now().isoformat(),
            'feedback': feedback,
            'sentiment': analysis.get('sentiment', 'Unknown'),
            'summary': analysis.get('summary', ''),
            'category': analysis.get('category', 'Other')
        }
        
        table.put_item(Item=item)
        results.append(item)
        print(f"Saved result: {item}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Successfully analyzed {len(results)} feedback entries')
    }