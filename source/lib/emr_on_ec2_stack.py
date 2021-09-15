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
    aws_ec2 as ec2
)
from aws_cdk.aws_emr import CfnCluster
from lib.util.manifest_reader import load_yaml_replace_var_local
import os

class EMREC2Stack(core.NestedStack):
    @property
    def emr_connection(self):
        return self._emr_connection

    def __init__(self, scope: core.Construct, id: str, eksvpc: ec2.IVpc, code_bucket:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'

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
            instance_profile_name="emrJobFlowProfile_",
        )

        # create emr cluster
        emr=CfnCluster(self,"emr_ec2_cluster",
            instances=CfnCluster.JobFlowInstancesConfigProperty(
                core_instance_group=CfnCluster.InstanceGroupConfigProperty(
                    instance_count=1, instance_type="m4.large", market="SPOT"
                ),
                ec2_subnet_id=eksvpc.public_subnets[0].subnet_id,
                hadoop_version="Amazon",
                keep_job_flow_alive_when_no_steps=True,
                master_instance_group=CfnCluster.InstanceGroupConfigProperty(
                    instance_count=1, instance_type="m4.large", market="SPOT"
                ),
            ),
            # note job_flow_role is an instance profile (not an iam role)
            job_flow_role=emr_job_flow_profile.instance_profile_name,
            name="cluster_name",
            applications=[CfnCluster.ApplicationProperty(name="Spark")],
            service_role=svc_role.role_name,
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
            log_uri=f"s3://{code_bucket}/{core.Aws.REGION}/elasticmapreduce/",
            release_label="emr-6.2.0",
            visible_to_all_users=True
        )

        self._emr_connection=emr.connections