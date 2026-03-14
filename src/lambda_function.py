import json
import boto3
import csv
import os
import re
from datetime import datetime

# Initialize AWS clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'CustomerFeedback')

def analyze_feedback(feedback_text):
    prompt = f"""<s>[INST] You are a JSON generator. Analyze the customer feedback below and return ONLY a valid JSON object with no explanation, no markdown, no extra text.

Required JSON format:
{{"sentiment": "Positive", "summary": "brief summary", "category": "Product Quality"}}

Valid sentiment values: Positive, Negative, Neutral
Valid category values: Product Quality, Customer Service, Shipping, Price, Other

Customer feedback: {feedback_text}

Return ONLY the JSON object: [/INST]"""

    body = json.dumps({
        "prompt": prompt,
        "max_gen_len": 150,
        "temperature": 0.01
    })

    response = bedrock.invoke_model(
        modelId='meta.llama3-8b-instruct-v1:0',
        body=body
    )

    result = json.loads(response['body'].read())
    response_text = result['generation'].strip()
    
    print(f"Raw Bedrock response: {response_text}")
    
    # Try multiple JSON extraction methods
    # Method 1: Direct parse
    try:
        return json.loads(response_text)
    except:
        pass
    
    # Method 2: Find first complete JSON object
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Method 3: Use regex to extract JSON
    try:
        pattern = r'\{[^{}]*\}'
        matches = re.findall(pattern, response_text)
        if matches:
            return json.loads(matches[0])
    except:
        pass
    
    # Fallback: manual sentiment detection
    text_lower = feedback_text.lower()
    if any(word in text_lower for word in ['excellent', 'great', 'love', 'amazing', 'perfect', 'outstanding']):
        sentiment = 'Positive'
    elif any(word in text_lower for word in ['terrible', 'broken', 'worst', 'disappointed', 'poor', 'bad']):
        sentiment = 'Negative'
    else:
        sentiment = 'Neutral'
        
    return {
        "sentiment": sentiment,
        "summary": feedback_text[:50],
        "category": "Other"
    }

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(f"Processing file: {key} from bucket: {bucket}")
    
    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')
    
    table = dynamodb.Table(TABLE_NAME)
    reader = csv.DictReader(content.splitlines())
    
    results = []
    for row in reader:
        customer_id = row['customer_id']
        feedback = row['feedback']
        
        print(f"Analyzing feedback for customer: {customer_id}")
        
        try:
            analysis = analyze_feedback(feedback)
        except Exception as e:
            print(f"Error analyzing feedback for {customer_id}: {str(e)}")
            analysis = {
                "sentiment": "Unknown",
                "summary": "Error during analysis",
                "category": "Other"
            }
        
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