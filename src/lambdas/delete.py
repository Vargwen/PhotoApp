import json
import boto3
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME')

def lambda_handler(event, context):
    """
    Supprime une photo de S3 et DynamoDB
    """
    
    try:
        # Récupérer userId et photoId
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        user_id = claims.get('sub') or 'test-user-123'
        
        photo_id = event.get('pathParameters', {}).get('photoId')
        
        if not photo_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'photoId is required'})
            }
        
        # Récupérer les infos de la photo depuis DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(
            Key={'userID': user_id, 'photoID': photo_id}
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Photo not found'})
            }
        
        photo = response['Item']
        
        # Supprimer de S3 (original et thumbnail)
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=photo['originalKey'])
        
        if photo.get('thumbnailKey'):
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=photo['thumbnailKey'])
        
        # Supprimer de DynamoDB
        table.delete_item(
            Key={'userID': user_id, 'photoID': photo_id}
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Photo deleted successfully'})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }