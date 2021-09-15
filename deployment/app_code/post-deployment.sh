#!/bin/bash

export stack_name="${1:-StreamOnEKS}"

# 1. install k8s command tools 
echo "Installing kubectl tool..."
curl -o kubectl https://amazon-eks.s3.us-west-2.amazonaws.com/1.19.6/2021-01-05/bin/linux/amd64/kubectl
chmod +x kubectl
mkdir -p $HOME/bin && mv kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin

# 2. connect to the EKS newly created
echo `aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?starts_with(OutputKey,'eksclusterEKSConfig')].OutputValue" --output text` | bash
echo "Testing EKS connection..."
kubectl get svc

# 3. Update MSK with custom configuration
echo "Update MSK configuration ..."
cat <<EoF > msk-config.txt
auto.create.topics.enable = true
log.retention.minutes = 480
zookeeper.connection.timeout.ms = 1000
log.roll.ms = 604800000
EoF
aws kafka create-configuration --name "autotopic" --description "Topic autocreation enabled; Apache ZooKeeper timeout 2000 ms; Log rolling 604800000 ms." --server-properties file://msk-config.txt

# 4. install Kafka Client
echo "Installing Kafka Client tool ..."
sudo yum install java-1.8.0
wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz
tar -xzf kafka_2.12-2.2.1.tgz

# 5. Setup AWS environment
echo "Setup AWS environment ..."
export AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
export S3BUCKET=$(aws cloudformation describe-stacks --stack-name StreamOnEKS --query "Stacks[0].Outputs[?OutputKey=='CODEBUCKET'].OutputValue" --output text)
export MSK_SERVER=$(aws cloudformation describe-stacks --stack-name StreamOnEKS --query "Stacks[0].Outputs[?OutputKey=='MSK_BROKER'].OutputValue" --output text)

echo "export AWS_REGION=${AWS_REGION}" | tee -a ~/.bash_profile
echo "export S3BUCKET=${S3BUCKET}" | tee -a ~/.bash_profile
echo "export MSK_SERVER=${MSK_SERVER}" | tee -a ~/.bash_profile
