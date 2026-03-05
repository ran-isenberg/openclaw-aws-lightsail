import aws_cdk as cdk
from constructs import Construct

from cdk.constructs.ai_agent import AiAgent, AiAgentProps
from cdk.constructs.ai_agent_networking import AiAgentNetworking

INSTANCE_NAME = 'openclaw-agent'
STATIC_IP_NAME = 'openclaw-agent-ip'


class OpenClawStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        availability_zone = f'{self.region}a'

        ai_agent = AiAgent(
            self,
            'AiAgent',
            props=AiAgentProps(
                instance_name=INSTANCE_NAME,
                availability_zone=availability_zone,
            ),
        )

        networking = AiAgentNetworking(
            self,
            'AiAgentNetworking',
            instance=ai_agent.instance,
            static_ip_name=STATIC_IP_NAME,
        )

        cdk.CfnOutput(
            self,
            'DashboardUrl',
            value=cdk.Fn.join('', ['https://', networking.static_ip.attr_ip_address, '/overview']),
            description='OpenClaw dashboard URL. Pair your browser via SSH first: Lightsail console > Connect using SSH.',
        )

        cdk.CfnOutput(
            self,
            'NextStep',
            value=f'Open Lightsail console > Instances > {INSTANCE_NAME} > Connect using SSH to get the gateway token and pair your browser.',
        )
