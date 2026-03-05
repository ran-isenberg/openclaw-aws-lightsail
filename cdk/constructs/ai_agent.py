from dataclasses import dataclass

import aws_cdk.aws_lightsail as lightsail
from constructs import Construct

# OpenClaw blueprint on Lightsail (Linux/Unix, app type, group: openclaw_ls)
# Verify with: aws lightsail get-blueprints --query "blueprints[?name=='OpenClaw']"
OPENCLAW_BLUEPRINT_ID = 'openclaw_ls_1_0'

# 4 GB memory plan recommended for optimal performance per AWS docs
# See: https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-quick-start-guide-openclaw.html
DEFAULT_BUNDLE_ID = 'medium_3_0'


@dataclass
class AiAgentProps:
    instance_name: str
    availability_zone: str
    static_ip_name: str
    bundle_id: str = DEFAULT_BUNDLE_ID
    blueprint_id: str = OPENCLAW_BLUEPRINT_ID
    enable_auto_snapshot: bool = True


class AiAgent(Construct):
    """Business domain construct: deploys an OpenClaw AI agent on Lightsail.

    Pre-configured with Amazon Bedrock as the default AI model provider (Claude Sonnet 4.6).
    Includes built-in HTTPS via Let's Encrypt and device pairing authentication.
    """

    def __init__(self, scope: Construct, construct_id: str, props: AiAgentProps) -> None:
        super().__init__(scope, construct_id)

        add_ons = []
        if props.enable_auto_snapshot:
            add_ons.append(
                lightsail.CfnInstance.AddOnProperty(
                    add_on_type='AutoSnapshot',
                    auto_snapshot_add_on_request=lightsail.CfnInstance.AutoSnapshotAddOnProperty(
                        snapshot_time_of_day='04:00',
                    ),
                )
            )

        self.instance = lightsail.CfnInstance(
            self,
            'Instance',
            instance_name=props.instance_name,
            availability_zone=props.availability_zone,
            blueprint_id=props.blueprint_id,
            bundle_id=props.bundle_id,
            add_ons=add_ons if add_ons else None,
        )

        self.static_ip = lightsail.CfnStaticIp(
            self,
            'StaticIp',
            static_ip_name=props.static_ip_name,
            attached_to=props.instance_name,
        )

        self.static_ip.add_dependency(self.instance)
