import json
import boto3
import uuid
from datetime import datetime, timedelta
import os

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Variables d'environnement (on les configurera après)
BUCKET_NAME = os.environ.get('BUCKET_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME')

def lambda_handler(event, context):
    """
    Génère une URL pré-signée pour upload S3
    et enregistre les métadonnées dans DynamoDB
    """
    
    try:
        # Parse le body de la requête
        body = json.loads(event.get('body', '{}'))
        
        # Récupérer userId depuis le JWT (fourni par API Gateway Authorizer)
        # Dans event['requestContext']['authorizer']['claims']['sub']
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        
        # TEMPORAIRE - pour tests sans auth
        user_id = claims.get('sub') or 'test-user-123'
        
        # Récupérer les infos du fichier
        file_name = body.get('fileName')
        file_size = body.get('fileSize')
        content_type = body.get('contentType', 'image/jpeg')
        
        if not file_name or not file_size:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'fileName and fileSize are required'})
            }
        
        # Générer un ID unique pour la photo
        photo_id = str(uuid.uuid4())
        
        # Construire la clé S3 : userId/original/photoId.extension
        file_extension = file_name.split('.')[-1]
        s3_key = f"{user_id}/original/{photo_id}.{file_extension}"
        
        # Générer l'URL pré-signée (valide 5 minutes)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=300  # 5 minutes
        )
        
        # Enregistrer les métadonnées dans DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'userID': user_id,
                'photoID': photo_id,
                'uploadDate': datetime.utcnow().isoformat(),
                'fileName': file_name,
                'fileSize': file_size,
                'contentType': content_type,
                'originalKey': s3_key,
                'status': 'pending',  # pending → sera 'ready' après resize
                'thumbnailKey': ''  # Sera rempli par resize-handler
            }
        )
        
        # Retourner la réponse
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'uploadUrl': presigned_url,
                'photoId': photo_id,
                's3Key': s3_key,
                'message': 'Upload URL generated successfully'
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