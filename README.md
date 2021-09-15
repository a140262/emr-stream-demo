# Spark Structured Streaming Demo with MSK and EMR

This is a project developed with Python [CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html).
It include sample data, stream producer simulator and a consumer example that can be run with both options of EMR on EC2 and EMR on EKS. 

#### Table of Contents
* [Prerequisites](#Prerequisites)
* [Deploy Infrastructure](#Deploy-infrastructure)
  * [CFN Deploy](#Deploy-CFN)
  * [Customization](#Customization)
  * [CDK Deploy](#Deploy-via-CDK)
  * [Troubleshooting](#Troubleshooting)
* [Post Deployment](#Post-Deployment)
  * [Setup Kafka client](#Setup-kafka-client)
  * [Submit & Orchestrate Job](#Submit--orchestrate-job)
    * [Submit on Argo UI](#Submit-a-job-on-argo-ui)
    * [Submit by Argo CLI](#Submit-a-job-by-argo-cli)
    * [Submit a Native Spark Job](#Submit-a-native-job-with-spark-operator)
      * [Execute a PySpark Job](#Execute-a-pyspark-job)
      * [Self-recovery Test](#Self-recovery-test)
      * [Cost Savings with Spot](#Check-Spot-instance-usage-and-cost-savings)
      * [Autoscaling & Dynamic Resource Allocation](#Autoscaling---dynamic-resource-allocation)
* [Useful commands](#Useful-commands)  
* [Clean Up](#clean-up)
* [Security](#Security)
* [License](#License)

## Prerequisites 
1. Python 3.6 or later. Download Python [here](https://www.python.org/downloads/).
2. AWS CLI version 1.
  Windows: [MSI installer](https://docs.aws.amazon.com/cli/latest/userguide/install-windows.html#install-msi-on-windows)
  Linux, macOS or Unix: [Bundled installer](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html#install-macosos-bundled)
3. The AWS CLI can communicate with services in your deployment account. Otherwise, run the following script to setup your AWS account access from a command line tool.
```bash
aws configure
```
## Deploy Infrastructure

Download the project:
```bash
git clone https://github.com/a140262/emr-stream-demo.git
cd emr-stream-demo
```

This project is set up like a standard Python project. The `source/cdk.json` file tells where the application entry point is. The provisioning takes about 30 minutes to complete. See the `troubleshooting` section if you have any deployment problem. 

Two ways to deploy:
1. AWS CloudFormation template (CFN) 
2. [AWS Cloud Development Kit (AWS CDK)](https://docs.aws.amazon.com/cdk/latest/guide/home.html).

[*^ back to top*](#Table-of-Contents)
### Deploy CFN


  |   Region  |   Launch Template |
  |  ---------------------------   |   -----------------------  |
  |  ---------------------------   |   -----------------------  |
  **Choose Your Region**| [![Deploy to AWS](source/images/00-deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?stackName=SparkOnEKS&templateURL=https://solutions-reference.s3.amazonaws.com/sql-based-etl-with-apache-spark-on-amazon-eks/v1.0.0/sql-based-etl-with-apache-spark-on-amazon-eks.template) 

* Option1: Deploy with default (recommended). The default region is **us-east-1**. 
To launch the solution in a different AWS Region, use the Region selector in the console navigation bar. 

* Option2: Fill in the parameter `jhubuser` if you want to setup a customized username for Jupyter login. 

* Option3: To ETL your own data, input the parameter `datalakebucket` by your S3 bucket. 
`NOTE: the S3 bucket must be in the same region as the deployment region.`

### Customization
You can customize the solution, such as remove a Jupyter timeout setting, then generate the CFN in your region: 
```bash
export BUCKET_NAME_PREFIX=<my-bucket-name> # bucket where customized code will reside
export AWS_REGION=<your-region>
export SOLUTION_NAME=sql-based-etl
export VERSION=v1.0.0 # version number for the customized code

./deployment/build-s3-dist.sh $BUCKET_NAME_PREFIX $SOLUTION_NAME $VERSION

# create the bucket where customized code will reside
aws s3 mb s3://$BUCKET_NAME_PREFIX-$AWS_REGION --region $AWS_REGION

# Upload deployment assets to the S3 bucket
aws s3 cp ./deployment/global-s3-assets/ s3://$BUCKET_NAME_PREFIX-$AWS_REGION/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control
aws s3 cp ./deployment/regional-s3-assets/ s3://$BUCKET_NAME_PREFIX-$AWS_REGION/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control

echo -e "\nIn web browser, paste the URL to launch the template: https://console.aws.amazon.com/cloudformation/home?region=$AWS_REGION#/stacks/quickcreate?stackName=SparkOnEKS&templateURL=https://$BUCKET_NAME_PREFIX-$AWS_REGION.s3.amazonaws.com/$SOLUTION_NAME/$VERSION/sql-based-etl-with-apache-spark-on-amazon-eks.template\n"
```

[*^ back to top*](#Table-of-Contents)
### Deploy via CDK

CDK deployment requires Node.js (>= 10.3.0) and AWS CDK Toolkit. To install Node.js visit the [node.js](https://nodejs.org/en/) website. To install CDK toolkit, follow the [instruction](https://cdkworkshop.com/15-prerequisites/500-toolkit.html). If it's the first time to deploy an AWS CDK app into an AWS account, also you need to install a [“bootstrap stack”](https://cdkworkshop.com/20-typescript/20-create-project/500-deploy.html) to your CloudFormation.

See the `troubleshooting` section, if you have a problem to deploy the application via CDK.
 
Two reasons to deploy the solution by AWS CDK:
1. CDK provides local debug feature and fail fast.
2. Convenient to customize the solution with a quicker test response. For example remove a nested stack CloudFront and enable TLS in ALB.
 
Limitation:
The CDK deployment doesn't support pre or post-deployment steps, such as zip up a lambda function.

```bash
python3 -m venv .env
```
If you are in a Windows platform, you would activate the virtualenv like this:
 
```
% .env\Scripts\activate.bat
```
After the virtualenv is created, you can use the followings to activate your virtualenv and install the required dependencies.
```bash
source .env/bin/activate
pip install -e source
```
 
* Option1: Deploy with default (recommended)
```bash
cd source
cdk deploy
```

[*^ back to top*](#Table-of-Contents)
## Troubleshooting

1. If you see the issue `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1123)`, most likely it means no default certificate authority for your Python installation on OSX. Refer to the [answer](https://stackoverflow.com/questions/52805115/0nd) installing `Install Certificates.command` should fix your local environment. Otherwise, use [Cloud9](https://aws.amazon.com/cloud9/details/) to deploy the CDK instead.

2. If an error appears during the CDK deployment: `Failed to create resource. IAM role’s policy must include the "ec2:DescribeVpcs" action`. The possible causes are: 1) you have reach the quota limits of Amazon VPC resources per Region in your AWS account. Please deploy to a different region or a different account. 2) based on this [CDK issue](https://github.com/aws/aws-cdk/issues/9027), you can retry without any changes, it will work. 3) If you are in a branch new AWS account, manually delete the AWSServiceRoleForAmazonEKS from IAM role console before the deployment. 

[*^ back to top*](#Table-of-Contents)
## Post-deployment

1. Go to a Cloud9 console, launch the pre-build IDE environment called "Kafka Client"
2. Run the script to setup Kafka Client on Cloud9 IDE.
```bash
curl https://${S3BUCKET}.s3.${AWS_REGION}.amazonaws.com/app_code/post-deployment.sh | bash
```
3. Simulate Kafka ProducerOpen a new termnial window in Cloud9, send sample data to MSK:
```bash
curl -s https://${S3BUCKET}.s3.${AWS_REGION}.amazonaws.com/app_code/data/nycTaxiRides.gz | zcat | split -l 10000 --filter="kafka_2.12-2.2.1/bin/kafka-console-producer.sh --broker-list ${MSK_SERVER} --topic taxirides; sleep 0.2" > /dev/null
```
4. Target MSK Topic consumer
```bash
kafka_2.12-2.2.1/bin/kafka-console-consumer.sh --bootstrap-server ${MSK_SERVER} --topic taxirides_output --from-beginning
```


[*^ back to top*](#Table-of-Contents)
## Useful commands

 * `kubectl get pod -n spark`                         list running Spark jobs
 * `argo submit source/example/nyctaxi-job-scheduler.yaml`  submit a spark job via Argo
 * `argo list --all-namespaces`                       show all jobs scheduled via Argo
 * `kubectl delete pod --all -n spark`                delete all Spark jobs
 * `kubectl apply -f source/app_resources/spark-template.yaml` create a reusable Spark job template

[*^ back to top*](#Table-of-Contents)
## Clean up
Run the clean-up script with your CloudFormation stack name. The default name is SparkOnEKS. If you see the error "(ResourceInUse) when calling the DeleteTargetGroup operation", simply run the script again.
```bash
cd sql-based-etl-with-apache-spark-on-amazon-eks
./deployment/delete_all.sh <OPTIONAL:stack_name>
```
Go to the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home?region=us-east-1), manually delete the remaining resources if needed.

[*^ back to top*](#Table-of-Contents)
## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License. See the [LICENSE](LICENSE.txt) file.