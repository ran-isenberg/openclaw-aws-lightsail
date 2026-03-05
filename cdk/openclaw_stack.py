import aws_cdk as cdk
from constructs import Construct

from cdk.constructs.ai_agent import AiAgent, AiAgentProps

INSTANCE_NAME = 'openclaw-agent'
STATIC_IP_NAME = 'openclaw-agent-ip'


class OpenClawStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        availability_zone = f'{self.region}a'

        ai_agent = AiAgent(
            self,
            'Agent',
            props=AiAgentProps(
                instance_name=INSTANCE_NAME,
                availability_zone=availability_zone,
                static_ip_name=STATIC_IP_NAME,
            ),
        )

        cdk.CfnOutput(
            self,
            'DashboardUrl',
            value=cdk.Fn.join('', ['https://', ai_agent.static_ip.attr_ip_address, '/overview']),
            description='OpenClaw dashboard URL. Pair your browser via SSH first: Lightsail console > Connect using SSH.',
        )

        cdk.CfnOutput(
            self,
            'SetupGuide',
            value='https://aws.amazon.com/blogs/aws/introducing-openclaw-on-amazon-lightsail-to-run-your-autonomous-private-ai-agents/',
            description='AWS blog post with full first-time setup instructions.',
        )
