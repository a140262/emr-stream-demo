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
    aws_ec2 as ec2,

)
from aws_cdk.aws_emr import CfnCluster
from lib.util.manifest_reader import load_yaml_replace_var_local
import os

class EMREC2Stack(core.NestedStack):
    # @property
    # def emr_master_sg(self):
    #     return self.master_sg

    # @property
    # def emr_slave_sg(self):
    #     return self.slave_sg

    def __init__(self, scope: core.Construct, id: str, eksvpc: ec2.IVpc, code_bucket:str, cluster_name:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'

        ###########################
        #######             #######
        #######  EMR Roles  #######
        #######             #######
        ###########################
        # emr service role
        svc_role = iam.Role(self,"EMRSVCRole",
            assumed_by=iam.ServicePrincipal("elasticmapreduce.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonElasticMapReduceRole")
            ]
        )
        _iam = load_yaml_replace_var_local(source_dir+'/app_resources/native-spark-iam-role.yaml', 
            fields= {
                "{{codeBucket}}": code_bucket
            })
        for statmnt in _iam:
            svc_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        # emr job flow role
        emr_job_flow_role = iam.Role(self,"EMRJobflowRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonElasticMapReduceforEC2Role")
            ]
        )
        # emr job flow profile
        emr_job_flow_profile = iam.CfnInstanceProfile(self,"EMRJobflowProfile",
            roles=[emr_job_flow_role.role_name],
            instance_profile_name="emrJobFlowProfile",
        )

        ####################################
        #######                      #######
        #######  Create EMR Cluster  #######
        #######                      #######
        ####################################
        CfnCluster(self,"emr_ec2_cluster",
            name=cluster_name,
            applications=[CfnCluster.ApplicationProperty(name="Spark")],
            service_role=svc_role.role_name,
            log_uri=f"s3://{code_bucket}/elasticmapreduce/",
            release_label="emr-6.2.0",
            visible_to_all_users=True,
            # note job_flow_role is an instance profile (not an iam role)
            job_flow_role=emr_job_flow_profile.instance_profile_name,
            tags=[core.CfnTag(key="project", value="emr-stream-demo")],
            instances=CfnCluster.JobFlowInstancesConfigProperty(
                termination_protected=False,
                master_instance_group=CfnCluster.InstanceGroupConfigProperty(
                    instance_count=1, 
                    instance_type="m6g.large", 
                    market="ON_DEMAND"
                ),
                core_instance_group=CfnCluster.InstanceGroupConfigProperty(
                    instance_count=1, 
                    instance_type="m6g.large", 
                    market="ON_DEMAND",
                    ebs_configuration=CfnCluster.EbsConfigurationProperty(
                        ebs_block_device_configs=[CfnCluster.EbsBlockDeviceConfigProperty(
                        volume_specification=CfnCluster.VolumeSpecificationProperty(
                            size_in_gb=100,
                            volume_type='gp2'))
                    ])
                ),
                ec2_subnet_id=eksvpc.public_subnets[0].subnet_id
            ),
            configurations=[
                # use python3 for pyspark
                CfnCluster.ConfigurationProperty(
                    classification="spark-env",
                    configurations=[
                        CfnCluster.ConfigurationProperty(
                            classification="export",
                            configuration_properties={
                                "PYSPARK_PYTHON": "/usr/bin/python3",
                                "PYSPARK_DRIVER_PYTHON": "/usr/bin/python3",
                            },
                        )
                    ],
                ),
                # dedicate cluster to single jobs
                CfnCluster.ConfigurationProperty(
                    classification="spark",
                    configuration_properties={"maximizeResourceAllocation": "true"},
                ),
            ],
            managed_scaling_policy=CfnCluster.ManagedScalingPolicyProperty(
                compute_limits=CfnCluster.ComputeLimitsProperty(
                    unit_type="Instances", 
                    maximum_capacity_units=5,
                    minimum_capacity_units=1, 
                    maximum_core_capacity_units=1,
                    maximum_on_demand_capacity_units=1
                )   
            )
        )

        # self.master_sg=emr_cluster.instances.emr_managed_master_security_group
        # self.slave_sg=emr_cluster.instances.emr_managed_slave_security_group