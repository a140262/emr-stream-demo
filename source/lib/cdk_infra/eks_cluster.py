######################################################################################################################
# Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                      #
#                                                                                                                   #
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
# with the License. A copy of the License is located at                                                             #
#                                                                                                                   #
#     http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                   #
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
# OR CONDITIONS OF ANY KIND, express o#implied. See the License for the specific language governing permissions     #
# and limitations under the License.  																				#                                                                              #
######################################################################################################################

from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ec2 as ec2
)
from aws_cdk.aws_iam import IRole

class EksConst(core.Construct):

    @property
    def my_cluster(self):
        return self._my_cluster

    @property
    def awsAuth(self):
        return self._my_cluster.aws_auth       

    def __init__(self, scope: core.Construct, id:str, eksname: str, eksvpc: ec2.IVpc, noderole: IRole, eks_adminrole: IRole, emr_svc_role: IRole, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 1.Create EKS cluster without node group
        self._my_cluster = eks.Cluster(self,'EKS',
                vpc= eksvpc,
                cluster_name=eksname,
                masters_role=eks_adminrole,
                output_cluster_name=True,
                version= eks.KubernetesVersion.V1_19,
                endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                default_capacity=0
        )


        # 2.Add Managed NodeGroup to EKS, compute resource to run Spark jobs
        self._my_cluster.add_nodegroup_capacity('onDemand-mn',
            nodegroup_name = 'etl-ondemand',
            node_role = noderole,
            desired_size = 1,
            max_size = 5,
            disk_size = 50,
            instance_types = [ec2.InstanceType('m5.xlarge')],
            labels = {'app':'spark', 'lifecycle':'OnDemand'},
            subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE,one_per_az=True),
            tags = {'Name':'OnDemand-'+eksname,'k8s.io/cluster-autoscaler/enabled': 'true', 'k8s.io/cluster-autoscaler/'+eksname: 'owned'}
        )  
    

        # 3. Add Spot managed NodeGroup to EKS (Run Spark exectutor on spot)
        self._my_cluster.add_nodegroup_capacity('spot-mn',
            nodegroup_name = 'etl-spot',
            node_role = noderole,
            capacity_type=eks.CapacityType.SPOT,
            desired_size = 1,
            max_size = 30,
            disk_size = 50,
            instance_types=[ec2.InstanceType("r5.xlarge"),ec2.InstanceType("r4.xlarge"),ec2.InstanceType("r5a.xlarge")],
            labels = {'app':'spark', 'lifecycle':'Ec2Spot'},
            tags = {'Name':'Spot-'+eksname, 'k8s.io/cluster-autoscaler/enabled': 'true', 'k8s.io/cluster-autoscaler/'+eksname: 'owned'}
        )

        # 4. Add Fargate NodeGroup to EKS, without setup cluster-autoscaler
        self._my_cluster.add_fargate_profile('FargateEnabled',
            selectors =[{
                "namespace": "emrserverless"
            }],
            fargate_profile_name='serverlessETL'
        )
        
        # 5. Map EMR user to IAM role
        self._my_cluster.aws_auth.add_role_mapping(emr_svc_role, groups=[], username="emr-containers")
