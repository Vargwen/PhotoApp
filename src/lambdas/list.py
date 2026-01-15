import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')

def lambda_handler(event, context):
    """
    Liste toutes les photos d'un utilisateur
    """
    
    try:
        # Récupérer userId depuis JWT
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub') or 'test-user-123'  # Temporaire
        
        # Query DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            KeyConditionExpression=Key('userID').eq(user_id)
        )
        
        photos = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'photos': photos,
                'count': len(photos)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }