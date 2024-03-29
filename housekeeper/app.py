import json

import boto3


def check_sagemaker_notebooks(sagemaker_client):
    running_notebooks = sagemaker_client.list_notebook_instances(
        StatusEquals='InService'
    )
    return running_notebooks['NotebookInstances']


def get_aws_regions():
    ec2_client = boto3.client('ec2')
    try:
        print("Listing regions")
        regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    except Exception as e:
        print("Failed to list regions")
        raise e
    return regions


def stop_sagemaker_notebook_instance(sagemaker_client, notebook_name):
    sagemaker_client.stop_notebook_instance(NotebookInstanceName=notebook_name)
    print("Stopped {}".format(notebook_name))


def sagemaker_notebooks(sagemaker_client):
    running_sagemaker_notebooks = check_sagemaker_notebooks(sagemaker_client)
    if len(running_sagemaker_notebooks) > 0:
        print("Found {} notebook instance running".format(len(running_sagemaker_notebooks)))
        for notebook in running_sagemaker_notebooks:
            stop_sagemaker_notebook_instance(sagemaker_client, notebook['NotebookInstanceName'])


def delete_sagemaker_studio_app(sagemaker_client, app):
    print("Deleting app {}".format(app['AppName']))
    sagemaker_client.delete_app(
        DomainId=app['DomainId'],
        UserProfileName=app['UserProfileName'],
        AppType=app['AppType'],
        AppName=app['AppName']
    )


def get_sagemaker_apps(sagemaker_client):
    response = sagemaker_client.list_apps()
    return response['Apps']


def sagemaker_studio_apps(sagemaker_client):
    apps = get_sagemaker_apps(sagemaker_client)
    if len(apps) > 0:
        for app in apps:
            if app['Status'] == 'InService':
                delete_sagemaker_studio_app(sagemaker_client, app)


def get_sagemaker_endpoints(sagemaker_client):
    response = sagemaker_client.list_endpoints(
        StatusEquals='InService'
    )
    return response['Endpoints']


def delete_sagemaker_endpoint(sagemaker_client, endpoint_name):
    print("Deleting endpoint {}".format(endpoint_name))
    sagemaker_client.delete_endpoint(
        EndpointName=endpoint_name
    )


def describe_sagemaker_monitoring_config(sagemaker_client, monitoring_schedule_name):
    monitoring = sagemaker_client.describe_monitoring_schedule(
        MonitoringScheduleName=monitoring_schedule_name
    )
    # print(monitoring['MonitoringScheduleConfig'])
    return monitoring['MonitoringScheduleConfig']


def describe_sagemaker_monitoring_schedule(sagemaker_client, endpoint_name):
    monitoring_schedule = sagemaker_client.list_monitoring_schedules(
        EndpointName=endpoint_name
    )

    schedule_configs = []
    for schedule in monitoring_schedule['MonitoringScheduleSummaries']:
        monitoring_schedule_config = describe_sagemaker_monitoring_config(sagemaker_client,
                                                                          schedule['MonitoringScheduleName'])
        schedule_configs.append({'config_name': schedule['MonitoringScheduleName'],
                                 'config': monitoring_schedule_config})

    return schedule_configs


def sagemaker_endpoints(sagemaker_client):
    endpoints = get_sagemaker_endpoints(sagemaker_client)
    if len(endpoints) > 0:
        for endpoint in endpoints:
            described_endpoint = describe_sagemaker_endpoint(sagemaker_client, endpoint['EndpointName'])
            # checking if there is a monitoring schedule to the endpoint that prevents deleting the endpoint
            described_monitoring_configs = describe_sagemaker_monitoring_schedule(sagemaker_client,
                                                                                   endpoint['EndpointName'])

            result = save_sagemaker_endpoint_config_to_dynamodb(
                described_endpoint['EndpointName'],
                described_endpoint['EndpointConfigName'],
                sagemaker_client.meta.region_name,
                described_monitoring_configs)

            if result == 0:
                delete_sagemaker_endpoint(sagemaker_client, described_endpoint['EndpointName'])


def describe_sagemaker_endpoint(sagemaker_client, endpoint_name):
    print("Describing endpoint {}".format(endpoint_name))
    response = sagemaker_client.describe_endpoint(
        EndpointName=endpoint_name
    )
    return response


def save_sagemaker_endpoint_config_to_dynamodb(endpoint_name, endpoint_config, endpoint_region, monitoring_configs):
    print("saving to dynamodb", endpoint_name, endpoint_config, endpoint_region)
    dynamodb_client = boto3.client('dynamodb')
    print(monitoring_configs)
    # print(type(monitoring_configs))
    # print(json.loads(monitoring_configs))
    # print(json.dumps(monitoring_configs))

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


def lambda_handler(event, context):
    regions = get_aws_regions()
    for region in regions:
        print("Working on region {}".format(region))
        sagemaker_client = boto3.client('sagemaker', region)
        sagemaker_notebooks(sagemaker_client)
        sagemaker_studio_apps(sagemaker_client)
        sagemaker_endpoints(sagemaker_client)


if __name__ == "__main__":
    main_event = ""
    main_context = []
    lambda_handler(main_event, main_context)
