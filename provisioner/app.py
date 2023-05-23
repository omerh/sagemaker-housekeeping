import json
import random

import boto3


def get_aws_regions():
    ec2_client = boto3.client('ec2')
    try:
        print("Listing regions")
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    except Exception as e:
        print("Failed to list regions")
        raise e
    return regions


def save_sagemaker_endpoint_config_to_dynamodb(endpoint_name, endpoint_config, endpoint_region, monitoring_configs):
    print("saving to dynamodb", endpoint_name, endpoint_config, endpoint_region)
    dynamodb_client = boto3.client('dynamodb')
    print(monitoring_configs)

    try:
        dynamodb_client.put_item(
            TableName='testing_sagemaker_housekeeping',
            Item={
                'endpoint_name': {'S': endpoint_name},
                'endpoint_config': {'S': endpoint_config},
                'endpoint_region': {'S': endpoint_region},
                'monitoring_config': {'S': json.dumps(monitoring_configs)},
            }
        )
    except Exception as err:
        print(err)
        return 1
    return 0


def provision_sagemaker_endpoint(endpoint_name, endpoint_region, endpoint_config):
    sagemaker_client = boto3.client('sagemaker', endpoint_region)
    response = sagemaker_client.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config
    )
    return response['EndpointArn']


def list_sagemaker_endpoints():
    dynamodb = boto3.resource('dynamodb')
    dynamodb_table = dynamodb.Table('testing_sagemaker_housekeeping')

    response = dynamodb_table.scan()
    while 'LastEvaluatedKey' in response:
        response = dynamodb_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    return response


def lambda_handler(event, context):
    endpoints_information = list_sagemaker_endpoints()
    # temp
    random_number = random.randrange(1,100000)
    for endpoint in endpoints_information['Items']:
        # endpoint_arn = provision_sagemaker_endpoint(endpoint['endpoint_name']+str(random_number),
        #                                             endpoint['endpoint_region'],
        #                                             endpoint['endpoint_config'])
        if 'monitoring_config' in endpoint:
            print("Setting monitoring schedule for {}".format(endpoint['endpoint_name']))
            for config in json.loads(endpoint['monitoring_config']):
                print(config['config_name'])
                print(config['config'])


if __name__ == "__main__":
    main_event = ""
    main_context = []
    lambda_handler(main_event, main_context)
