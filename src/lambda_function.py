import json
import boto3
import csv
import os
import re
from datetime import datetime

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'CustomerFeedback')

def analyze_feedback(feedback_text):
    prompt = f"""Look at this customer feedback and return a JSON object only, nothing else.

{{"sentiment": "Positive", "summary": "short summary here", "category": "Product Quality"}}

sentiment must be one of: Positive, Negative, Neutral
category must be one of: Product Quality, Customer Service, Shipping, Price, Other

feedback: {feedback_text}

JSON:"""

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

    print(f"Bedrock response: {response_text}")

    try:
        return json.loads(response_text)
    except:
        pass

    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])
    except:
        pass

    try:
        matches = re.findall(r'\{[^{}]*\}', response_text)
        if matches:
            return json.loads(matches[0])
    except:
        pass

    text_lower = feedback_text.lower()
    if any(w in text_lower for w in ['excellent', 'great', 'love', 'amazing', 'perfect', 'outstanding']):
        sentiment = 'Positive'
    elif any(w in text_lower for w in ['terrible', 'broken', 'worst', 'disappointed', 'poor', 'bad']):
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

    print(f"Got file: {key} from {bucket}")

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8')

    table = dynamodb.Table(TABLE_NAME)
    reader = csv.DictReader(content.splitlines())

    results = []
    for row in reader:
        customer_id = row['customer_id']
        feedback = row['feedback']

        print(f"Processing customer {customer_id}")

        try:
            analysis = analyze_feedback(feedback)
        except Exception as e:
            print(f"Error on {customer_id}: {str(e)}")
            analysis = {
                "sentiment": "Unknown",
                "summary": "could not analyze",
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
        print(f"Saved: {item}")

    return {
        'statusCode': 200,
        'body': json.dumps(f'processed {len(results)} entries')
    }