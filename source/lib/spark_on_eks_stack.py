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

from aws_cdk import core
from lib.cdk_infra.network_sg import NetworkSgConst
from lib.cdk_infra.iam_roles import IamConst
from lib.cdk_infra.eks_cluster import EksConst
from lib.cdk_infra.eks_service_account import EksSAConst
from lib.cdk_infra.eks_base_app import EksBaseAppConst
from lib.cdk_infra.s3_app_code import S3AppCodeConst
from lib.cdk_infra.spark_permission import SparkOnEksConst
from lib.util.manifest_reader import *
import os

class SparkOnEksStack(core.Stack):

    @property
    def code_bucket(self):
        return self.app_s3.code_bucket

    @property
    def eksvpc(self):
        return self.network_sg.vpc

    # @property
    # def eks_connection(self):
    #     return self._eks_connection
        
    def __init__(self, scope: core.Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 1. a new bucket to store application code
        self.app_s3 = S3AppCodeConst(self,'appcode')

        # 2. EKS base infrastructure
        self.network_sg = NetworkSgConst(self,'network-sg', eksname, self.app_s3.code_bucket)
        iam = IamConst(self,'iam_roles', eksname)
        eks_cluster = EksConst(self,'eks_cluster', eksname, self.network_sg.vpc, iam.managed_node_role, iam.admin_role)
        EksSAConst(self, 'eks_service_account', eks_cluster.my_cluster)
        EksBaseAppConst(self, 'eks_base_app', eks_cluster.my_cluster)

        # 3. Setup Spark environment, Register for EMR on EKS
        SparkOnEksConst(self,'spark_permission',eks_cluster.my_cluster, self.app_s3.code_bucket)
   