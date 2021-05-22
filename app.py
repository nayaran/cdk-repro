#!/usr/bin/env python3
from aws_cdk import core
import aws_cdk.aws_codepipeline as codepipeline
from aws_cdk import pipelines
from aws_cdk.pipelines import CdkPipeline as cdk_pipeline
from aws_cdk import aws_codepipeline_actions as codepipeline_actions
from aws_cdk import aws_codecommit as codecommit
from aws_cdk import aws_ec2 as ec2
from aws_cdk.aws_codepipeline_actions import CodeCommitSourceAction
from aws_cdk.aws_codepipeline_actions import CodeCommitTrigger

DEV_ENV = core.Environment(account='DEV_ACCOUNT_NUMBER', region='REGION')
DEV_VPC_ID = 'DEV_VPC_ID'
DEV_SUBNET_ID = 'DEV_SUBNET_ID'

class CdkReproStack(core.Stack):
    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

class Application(core.Stage):
    def __init__(self, scope, id, *, env=None):
        super().__init__(scope, id, env=env)
        stack = CdkReproStack(self, 'CdkReproApplicationStack', env=DEV_ENV)

class Pipeline(core.Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        repo = codecommit.Repository.from_repository_name(self, 'Repo', 'cdk-repro')
        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline = cdk_pipeline(self, 'Pipeline',
                                cloud_assembly_artifact=cloud_assembly_artifact,
                                source_action=CodeCommitSourceAction(
                                                action_name='CodeCommit',
                                                output=source_artifact,
                                                repository=repo,
                                                trigger=CodeCommitTrigger.POLL),
                                synth_action=pipelines.SimpleSynthAction(
                                                source_artifact=source_artifact,
                                                cloud_assembly_artifact=cloud_assembly_artifact,
                                                install_command='npm install -g aws-cdk &&'
                                                                'pip install -r requirements.txt',
                                                synth_command='cdk synth'))
        dev_stage = pipeline.add_application_stage(Application(self, "CdkReproDevStage", env=DEV_ENV))
        vpc_dev = ec2.Vpc.from_lookup(self, 'VpcDev', vpc_id=DEV_VPC_ID)
        subnets_dev = [ec2.Subnet.from_subnet_id(self, 'SubnetDev', subnet_id=DEV_SUBNET_ID)]
        dev_it = pipelines.ShellScriptAction(vpc=vpc_dev,
                                             subnet_selection=ec2.SubnetSelection(subnets=subnets_dev),
                                             action_name="SampleIntegrationTest",
                                             commands=["echo Sample Integration Test"],
                                             run_order=dev_stage.next_sequential_run_order(),
                                             additional_artifacts=[source_artifact])
        dev_stage.add_actions(dev_it)

app = core.App()
Pipeline(app, "CdkReproPipeline", env=DEV_ENV)

app.synth()
