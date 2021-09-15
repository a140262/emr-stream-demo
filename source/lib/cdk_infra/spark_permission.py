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
    aws_emrcontainers as emrc
)
from aws_cdk.aws_eks import ICluster, KubernetesManifest
from lib.util.manifest_reader import load_yaml_replace_var_local
import os

class SparkOnEksSAConst(core.Construct):

    def __init__(self,scope: core.Construct, id: str, 
        eks_cluster: ICluster, 
        code_bucket: str, 
        clust_oidc_issuer: str,
        **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'        

# //****************************************************************************************//
# //************************** SETUP PERMISSION FOR OSS SPARK JOBS *************************//
# //******* create k8s namespace, service account, and IAM role for service account ********//
# //***************************************************************************************//

        # create k8s namespace
        etl_ns = eks_cluster.add_manifest('SparkNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name": "spark",
                    "labels": {"name":"spark"}
                }
            }
        )  
        
        self._spark_sa = eks_cluster.add_service_account('NativeSparkSa',
            name='nativejob',
            namespace='spark'
        )
        self._spark_sa.node.add_dependency(etl_ns)

        _spark_rb = eks_cluster.add_manifest('sparkRoleBinding',
            load_yaml_replace_var_local(source_dir+'/app_resources/native-spark-rbac.yaml',
                fields= {
                    "{{MY_SA}}": self._spark_sa.service_account_name
                })
        )
        _spark_rb.node.add_dependency(self._spark_sa)

        _native_spark_iam = load_yaml_replace_var_local(source_dir+'/app_resources/native-spark-iam-role.yaml',
            fields={
                 "{{codeBucket}}": code_bucket
            }
        )
        for statmnt in _native_spark_iam:
            self._spark_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

# # //*************************************************************************************//
# # //******************** SETUP PERMISSION FOR EMR ON EKS   *****************************//
# # //***********************************************************************************//

        #################################
        #######                   #######
        #######   EMR Namespace   #######
        #######                   #######
        #################################
        _emr_01_name = "emr"
        emr_ns = eks_cluster.add_manifest('EMRNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name":  _emr_01_name,
                    "labels": {"name": _emr_01_name}
                }
            }
        )
        _emr_02_name = "emrserverless"
        emr_serverless_ns = eks_cluster.add_manifest('EMRFargateNamespace',{
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": { 
                    "name": _emr_02_name,
                    "labels": {"name": _emr_01_name}
                }
            }
        )

        ###########################################
        #######                             #######
        #######   k8s role for EMR on EKS   #######
        #######                             #######
        ###########################################
        _emr_rb = KubernetesManifest(self,'EMRRoleBinding',
            cluster=eks_cluster,
            manifest=load_yaml_replace_var_local(source_dir+'/app_resources/emr-rbac.yaml', 
            fields= {
                "{{NAMESPACE}}": _emr_01_name,
            }, 
            multi_resource=True)
        )
        _emr_rb.node.add_dependency(emr_ns)

        _emr_fg_rb = KubernetesManifest(self,'EMRFargateRoleBinding',
            cluster=eks_cluster,
            manifest=load_yaml_replace_var_local(source_dir+'/app_resources/emr-rbac.yaml', 
            fields= {
                "{{NAMESPACE}}": _emr_02_name
            }, 
            multi_resource=True)
        )
        _emr_fg_rb.node.add_dependency(emr_serverless_ns)

        # Create EMR on EKS job executor role
        #######################################
        #######                         #######
        #######   EMR Execution Role    #######
        #######                         #######
        #######################################
        _emr_exec_role = iam.Role(self, "EMRJobExecRole", assumed_by=iam.ServicePrincipal("eks.amazonaws.com"))
        
        # trust policy
        sub_str_like = core.CfnJson(self, "ConditionJsonIssuer",
            value={
                f"{clust_oidc_issuer}:sub": f"system:serviceaccount:{_emr_01_name}:emr-containers-sa-*-*-{core.Aws.ACCOUNT_ID}-*"
            }
        )
        _emr_exec_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRoleWithWebIdentity"],
                principals=[iam.OpenIdConnectPrincipal(eks_cluster.open_id_connect_provider, conditions={"StringLike": sub_str_like})])
        )

        aud_str_like = core.CfnJson(self,"ConditionJsonAudEMR",
            value={
                f"{clust_oidc_issuer}:aud": "sts.amazon.com"
            }
        )
        _emr_exec_role.assume_role_policy.add_statements(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRoleWithWebIdentity"],
                principals=[iam.OpenIdConnectPrincipal(eks_cluster.open_id_connect_provider, conditions={"StringEquals": aud_str_like})]
            )
        )
        # custom policy      
        _emr_iam = load_yaml_replace_var_local(source_dir+'/app_resources/emr-iam-role.yaml',
            fields={
                 "{{codeBucket}}": code_bucket
            }
        )
        for statmnt in _emr_iam:
           _emr_exec_role.add_to_policy(iam.PolicyStatement.from_json(statmnt))

        core.Tags.of(_emr_exec_role).add(key=f"eks/{eks_cluster}/type", value="emr-eks-exec-role")


        ############################################
        #######                              #######
        #######  EMR virtual Cluster Server  #######
        #######                              #######
        ############################################
        emr_vc = emrc.CfnVirtualCluster(self,"EMRCluster",
            container_provider=emrc.CfnVirtualCluster.ContainerProviderProperty(
                id=eks_cluster.cluster_name,
                info=emrc.CfnVirtualCluster.ContainerInfoProperty(
                    eks_info=emrc.CfnVirtualCluster.EksInfoProperty(namespace=_emr_01_name)),
                type="EKS"
            ),
            name="EMRCluster"
        )
        emr_vc.node.add_dependency(_emr_exec_role)
        emr_vc.node.add_dependency(emr_ns)

        emr_vc_fg = emrc.CfnVirtualCluster(self,"EMRServerlessCluster",
            container_provider=emrc.CfnVirtualCluster.ContainerProviderProperty(
                id=eks_cluster.cluster_name,
                info=emrc.CfnVirtualCluster.ContainerInfoProperty(
                    eks_info=emrc.CfnVirtualCluster.EksInfoProperty(namespace=_emr_02_name)),
                type="EKS"
            ),
            name="EMRClusterFG"
        )
        emr_vc_fg.node.add_dependency(_emr_exec_role) 
        emr_vc_fg.node.add_dependency(emr_serverless_ns) 

        core.CfnOutput(self, "VirtualClusterId",value=emr_vc.attr_id)
        core.CfnOutput(self, "FargateVirtualClusterId",value=emr_vc_fg.attr_id)
        core.CfnOutput(self, "EMREKSJobRole", value=_emr_exec_role.role_arn)
