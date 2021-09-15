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
    aws_msk as msk,
    aws_cloud9 as cloud9,
    aws_ec2 as ec2
)

class MSKStack(core.NestedStack):

    def __init__(self, scope: core.Construct, id: str, eksvpc: ec2.IVpc, eks_connect: ec2.Connections, emr_connect: ec2.Connections, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # launch Cloud9 as Kafka client
        c9env = cloud9.Ec2Environment(self, "KafkaClientEnv", 
            vpc=eksvpc,
            ec2_environment_name="MSK_Client",
            instance_type=ec2.InstanceType('m5.large'),
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

        msk = msk.Cluster(self, "EMR-EKS-stream",
            kafka_version=msk.KafkaVersion.V2_6_1,
            vpc=eksvpc,
            number_of_broker_nodes=2,
            removal_policy=core.RemovalPolicy.DESTROY,
            ebs_storage_info= msk.EbsStorageInfo.volume_size(50),

        )

    msk.connections.allow_from(c9env.connections ,ec2.Port.all_tcp)
    msk.connections.allow_from(eks_connect, ec2.Port.all_tcp)
    msk.connections.allow_from(emr_connect, ec2.Port.all_tcp)

    core.CfnOutput(self, "Kafka_client_URL", value=c9env.ide_url)
    core.CfnOutput(self, "BootstrapBrokers", value=msk.bootstrap_brokers)
    core.CfnOutput(self, "ZookeeperConnection", value=msk.zookeeper_connection_string)