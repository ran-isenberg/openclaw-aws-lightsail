import aws_cdk.aws_lightsail as lightsail
from constructs import Construct


class AiAgentNetworking(Construct):
    """Business domain construct: manages networking for the OpenClaw AI agent.

    Attaches a static IP to the Lightsail instance so the HTTPS endpoint
    remains stable across instance stop/start cycles.
    """

    def __init__(self, scope: Construct, construct_id: str, instance: lightsail.CfnInstance, static_ip_name: str) -> None:
        super().__init__(scope, construct_id)

        self.static_ip = lightsail.CfnStaticIp(
            self,
            'StaticIp',
            static_ip_name=static_ip_name,
            attached_to=instance.instance_name,
        )

        self.static_ip.add_dependency(instance)
