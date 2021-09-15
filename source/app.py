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

#!/usr/bin/env python3
from aws_cdk.core import (App,Tags,CfnOutput)
from lib.spark_on_eks_stack import SparkOnEksStack
from lib.emr_on_ec2_stack import EMREC2Stack
from lib.msk_stack import MSKStack

app = App()

eks_name = app.node.try_get_context('cluster_name')

# main stack
eks_stack = SparkOnEksStack(app, 'emr-on-eks', eks_name)
emr_ec2_stack = EMREC2Stack(eks_stack, 'emr-on-ec2', eks_stack.eksvpc, eks_stack.code_bucket)
msk_stack = MSKStack(eks_stack,'kafka',eks_stack.eksvpc, eks_stack.eks_connection,emr_ec2_stack.emr_connection)

Tags.of(eks_stack).add('project', 'emr-on-eks')
Tags.of(emr_ec2_stack).add('project', 'emr-on-eks')
Tags.of(msk_stack).add('project', 'emr-on-eks')

# Deployment Output
CfnOutput(eks_stack,'CODE_BUCKET', value=eks_stack.code_bucket)

app.synth()