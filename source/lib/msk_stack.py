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
    aws_iam as iam,
    aws_cloud9 as cloud9,
    aws_ec2 as ec2,
    aws_msk as msk
)

class MSKStack(core.NestedStack):

    @property
    def Cloud9URL(self):
        return self._c9env.ref

    @property
    def MSKBroker(self):
        return self._msk_cluster.bootstrap_brokers


    def __init__(self, scope: core.Construct, id: str, cluster_name:str, eksvpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # launch Cloud9 as Kafka client
        self._c9env = cloud9.CfnEnvironmentEC2(self, "KafkaClientEnv", 
            name= cluster_name+"_client",
            instance_type="t3.small",
            subnet_id=eksvpc.public_subnets[0].subnet_id,
            owner_arn=iam.AccountRootPrincipal().arn,
            automatic_stop_time_minutes=60
        )
        self._c9env.apply_removal_policy(core.RemovalPolicy.DESTROY)

        # MSK Cluster Security Group
        sg_msk = ec2.SecurityGroup(self, "msk_sg",
            vpc=eksvpc, allow_all_outbound=True, security_group_name="msk_sg"
        )    
        for subnet in eksvpc.public_subnets:
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(2181), "Zookeeper Plaintext")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(2182), "Zookeeper TLS")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(9092), "Broker Plaintext")
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.tcp(9094), "Zookeeper Plaintext")
        for subnet in eksvpc.private_subnets:
            sg_msk.add_ingress_rule(ec2.Peer.ipv4(subnet.ipv4_cidr_block), ec2.Port.all_traffic(), "All private traffic")
        # # create broker node
        # bngi = CfnCluster.broker_node_group_info=CfnCluster.BrokerNodeGroupInfoProperty(
        #         client_subnets=eksvpc.select_subnets(subnet_type=ec2.SubnetType.PUBLIC).subnet_ids,
        #         security_groups=[sg_msk.security_group_id],
        #         instance_type="kafka.m5.large",
        #         storage_info= CfnCluster.StorageInfoProperty(
        #             ebs_storage_info=CfnCluster.EBSStorageInfoProperty(volume_size=100)),
        # )
        # create MSK cluster
        # self._msk_cluster = CfnCluster(self, "EMR-EKS-stream",
        #     cluster_name="EMR-EKS-demo",
        #     kafka_version="2.6.1",
        #     broker_node_group_info=bngi,
        #     number_of_broker_nodes=2,
        #     encryption_info=CfnCluster.EncryptionInfoProperty(encryption_in_transit=transit_encryption),
        #     tags =core.CfnTag(key="project", value="emr-stream-demo")
        # )
        self._msk_cluster = msk.Cluster(self, "EMR-EKS-stream",
            cluster_name=cluster_name,
            kafka_version=msk.KafkaVersion.V2_6_1,
            vpc=eksvpc,
            ebs_storage_info=msk.EbsStorageInfo(volume_size=100),
            encryption_in_transit=msk.EncryptionInTransitConfig(
                enable_in_cluster=True,
                client_broker=msk.ClientBrokerEncryption.TLS_PLAINTEXT
            ),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.SMALL),
            removal_policy=core.RemovalPolicy.DESTROY,
            security_groups=[sg_msk],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC,one_per_az=True)
        )


        # self._msk_cluster.connections.allow_from(self._c9env.connections ,ec2.Port.all_tcp)
        # self._msk_cluster.connections.allow_from(eks_connect, ec2.Port.all_tcp)
        # self._msk_cluster.connections.allow_from(emr_master_sg, ec2.Port.all_tcp)
        # self._msk_cluster.connections.allow_from(emr_slave_sg,ec2.Port.all_tcp)
