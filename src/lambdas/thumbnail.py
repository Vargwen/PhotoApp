import json
import boto3
import os
from PIL import Image
from io import BytesIO
from urllib.parse import unquote_plus

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('BUCKET_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME')
THUMBNAIL_SIZE = (200, 200)

def lambda_handler(event, context):
    """
    Déclenchée automatiquement quand un fichier est uploadé dans S3.
    Génère un thumbnail et met à jour DynamoDB.
    """
    
    try:
        # Récupérer les infos du fichier depuis l'event S3
        for record in event['Records']:
            # Nom du bucket et clé de l'objet
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
            
            print(f"Processing: {bucket}/{key}")
            
            # Ignorer si ce n'est pas dans le dossier 'original'
            if '/original/' not in key:
                print(f"Skipping {key} - not in original folder")
                continue
            
            # Extraire userId et photoId depuis le chemin
            # Format: userId/original/photoId.extension
            parts = key.split('/')
            user_id = parts[0]
            file_name = parts[2]  # photoId.extension
            photo_id = file_name.rsplit('.', 1)[0]  # Enlever l'extension
            file_extension = file_name.rsplit('.', 1)[1]
            
            # Télécharger l'image originale depuis S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_content = response['Body'].read()
            
            # Ouvrir l'image avec Pillow
            image = Image.open(BytesIO(image_content))
            
            # Convertir en RGB si nécessaire (pour les PNG avec transparence)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Créer le thumbnail en conservant le ratio
            image.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            
            # Sauvegarder le thumbnail en mémoire
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            # Construire la clé pour le thumbnail
            thumbnail_key = f"{user_id}/thumbnails/{photo_id}.jpg"
            
            # Upload du thumbnail dans S3
            s3_client.put_object(
                Bucket=bucket,
                Key=thumbnail_key,
                Body=buffer,
                ContentType='image/jpeg'
            )
            
            print(f"Thumbnail created: {thumbnail_key}")
            
            # Mettre à jour DynamoDB
            table = dynamodb.Table(TABLE_NAME)
            table.update_item(
                Key={
                    'userID': user_id,
                    'photoID': photo_id
                },
                UpdateExpression='SET thumbnailKey = :tk, #status = :status',
                ExpressionAttributeNames={
                    '#status': 'status'  # 'status' est un mot réservé DynamoDB
                },
                ExpressionAttributeValues={
                    ':tk': thumbnail_key,
                    ':status': 'ready'
                }
            )
            
            print(f"DynamoDB updated for photoId: {photo_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Resize completed successfully')
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        # Ne pas lever d'exception - on logge juste l'erreur
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }