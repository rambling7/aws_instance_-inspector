import boto3  # need pip install
import urllib.request
import socket
import datetime

def tcp_requests(host):
  port = 53
  scan = socket.socket()
  scan.settimeout(1)
  try:
    scan.connect((host, port))
  except socket.error:
    state = 'problem'
  else:
    scan.close
    state = 'work'
  return [host, state]
  
def http_requests(host):
  try:
    code = urllib.request.urlopen("http://" + host).getcode()
  except:
    code = 'cathc except'
  state = 'work' if code == 200 else 'problem'
  return [host, state]

def check_instances(hosts):
  my_instances = {}
  for host in hosts:
    tcp_scan = tcp_requests(host)
    http_scan = http_requests(host)
    my_instances[host] = {'TCP': tcp_scan[1], 'HTTP': http_scan[1]}
  return my_instances

def get_owner_id():
  return boto3.client('sts').get_caller_identity()['Account']

def check_instances_aws_api():
  ec2 = boto3.client('ec2')
  owner_id = get_owner_id()
  Filters=[{'Name': 'owner-id', 'Values': [owner_id]}]
  response = ec2.describe_instances()
  instances = response['Reservations'][0]['Instances']
  my_instances = {}
  for instance in instances:
    PublicDnsName = instance['PublicDnsName'] 
    State = instance['State']['Name']
    try:
      Tags = instance['Tags']
      for tag in Tags:
        if str(tag['Key']) == 'Name':
          Name = tag['Value']
    except: Name=''

    InstanceId = instance['InstanceId']
    my_instances[InstanceId] = {'PublicDnsName': PublicDnsName, 'State': State, 'Name': Name}
  return my_instances
  
def get_ami_stopped_host(instances):
  for instance in instances:
    InstanceId = instance
    Name = instances[InstanceId]['Name']
    State = instances[InstanceId]['State']
    PublicDnsName = instances[InstanceId]['PublicDnsName']
    if State == 'stopped': 
      now = datetime.datetime.now()
      Description = Name + '@' + now.strftime("%Y-%m-%d")
      ec2 = boto3.client('ec2')
      ec2.create_image(Name=Name, InstanceId=InstanceId, Description=Description)
      ec2.terminate_instances(InstanceIds=[InstanceId])
      instances[InstanceId]['State'] = 'terminate'
  return instances 

def clean_amis():
  ec2 = boto3.client('ec2')
  owner_id = get_owner_id()
  Filters=[{'Name': 'owner-id', 'Values': [owner_id]}]
  response = ec2.describe_images(Filters=Filters)
  images = response['Images']
  DeleteDate = datetime.date.today() - datetime.timedelta(days=7) 
  for image in images:
    my_description_list = image['Description'].split('@')
    Name = my_description_list[0]
    CreationDate = my_description_list[1]
    deleted_ami_list = {}
    if str(CreationDate) == str(DeleteDate):
      ImageId = image['ImageId']
      ec2.deregister_image(ImageId=ImageId)
      deleted_amis_list[Name] = {'ImageId': ImageId, 'DeleteDate': DeleteDate}
  if deleted_amis_list: 
    return deleted_amis_list

if __name__ == "__main__":
  
  instances = check_instances_aws_api()
  test_instances_list = []
  print('*** current instances ***')
  for instance in instances:
    print('ID: {0} | NAME: {1} | DNS: {2} | STATE: {3}'.format(instance, instances[instance]['Name'], instances[instance]['PublicDnsName'], instances[instance]['State']))
#    if instances[instance]['PublicDnsName'] != '' : test_instances_list.append(instances[instance]['PublicDnsName'])
#   can't test it for real (now problem with domain buying)
    test_instances_list.append('google.com')
  
  if test_instances_list:
    instances_test = check_instances(test_instances_list)
    print('*** check instances ***')
    for instance in instances_test:
      print('HOST: {0} | TCP-53: {1} | HTTP: {2}'.format(instance, instances_test[instance]['TCP'], instances_test[instance]['HTTP']))
  
  print('*** stopped instances ***')
  instances = get_ami_stopped_host(instances)
  for instance in instances:
    print('ID: {0} | NAME: {1} | DNS: {2} | STATE: {3}'.format(instance, instances[instance]['Name'], instances[instance]['PublicDnsName'], instances[instance]['State']))

  deleted_amis_list={}
  deleted_amis_list = clean_amis()
  if deleted_amis_list:
    print('*** deleted amis ***')
    for ami in deleted_amis_list:
      print('NAME: {0} | AMI-ID: {1} | DELETE-DAY: {2}'.format(ami, deleted_amis_list[ami]['ImageId'], deleted_amis_list[ami]['DeleteDate']))
  
