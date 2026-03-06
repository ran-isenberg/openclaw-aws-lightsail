from dataclasses import dataclass, field

import aws_cdk as cdk
import aws_cdk.aws_lightsail as lightsail
from constructs import Construct

# OpenClaw blueprint on Lightsail (Linux/Unix, app type, group: openclaw_ls)
# Verify with: aws lightsail get-blueprints --query "blueprints[?name=='OpenClaw']"
OPENCLAW_BLUEPRINT_ID = 'openclaw_ls_1_0'

# 4 GB memory plan recommended for optimal performance per AWS docs
# See: https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-quick-start-guide-openclaw.html
DEFAULT_BUNDLE_ID = 'medium_3_0'

# Default firewall: HTTPS only from anywhere, SSH restricted to RFC 5737 documentation CIDR.
# Connections to 192.0.2.0/24 will fail loudly at the network layer — callers must set their IP.
# Update SSH_ALLOWED_CIDRS to your IP range before deploying.
SSH_PORT = 22
SSH_ALLOWED_CIDRS = ['192.0.2.0/24']

DEFAULT_FIREWALL_RULES: list[dict] = [
    {'protocol': 'tcp', 'from_port': 443, 'to_port': 443, 'cidrs': ['0.0.0.0/0']},
    {'protocol': 'tcp', 'from_port': SSH_PORT, 'to_port': SSH_PORT, 'cidrs': SSH_ALLOWED_CIDRS},
]


@dataclass
class AiAgentProps:
    instance_name: str
    availability_zone: str
    static_ip_name: str
    bundle_id: str = DEFAULT_BUNDLE_ID
    blueprint_id: str = OPENCLAW_BLUEPRINT_ID
    enable_auto_snapshot: bool = True
    snapshot_time_of_day: str = '04:00'
    enable_status_alarm: bool = False
    firewall_rules: list[dict] = field(default_factory=lambda: list(DEFAULT_FIREWALL_RULES))


class AiAgent(Construct):
    """Business domain construct: deploys an OpenClaw AI agent on Lightsail.

    Pre-configured with Amazon Bedrock as the default AI model provider (Claude Sonnet 4.6).
    Includes built-in HTTPS via Let's Encrypt and device pairing authentication.

    Security notes:
    - Snapshots use AWS-managed encryption (Lightsail limitation, no customer-managed KMS support).
    - Single-AZ deployment by design for cost optimization; auto-snapshots enable recovery.
    """

    def __init__(self, scope: Construct, construct_id: str, props: AiAgentProps) -> None:
        super().__init__(scope, construct_id)

        add_ons = []
        if props.enable_auto_snapshot:
            add_ons.append(
                lightsail.CfnInstance.AddOnProperty(
                    add_on_type='AutoSnapshot',
                    auto_snapshot_add_on_request=lightsail.CfnInstance.AutoSnapshotAddOnProperty(
                        snapshot_time_of_day=props.snapshot_time_of_day,
                    ),
                )
            )

        port_configs = [
            lightsail.CfnInstance.PortProperty(
                protocol=rule['protocol'],
                from_port=rule['from_port'],
                to_port=rule['to_port'],
                cidrs=rule.get('cidrs', ['0.0.0.0/0']),
            )
            for rule in props.firewall_rules
        ]

        for rule in props.firewall_rules:
            if rule.get('from_port') == SSH_PORT and '0.0.0.0/0' in rule.get('cidrs', []):
                cdk.Annotations.of(self).add_warning(
                    'SSH port 22 is open to the world (0.0.0.0/0). Set SSH_ALLOWED_CIDRS to your IP range before deploying.'
                )

        self.instance = lightsail.CfnInstance(
            self,
            'Instance',
            instance_name=props.instance_name,
            availability_zone=props.availability_zone,
            blueprint_id=props.blueprint_id,
            bundle_id=props.bundle_id,
            add_ons=add_ons if add_ons else None,
            networking=lightsail.CfnInstance.NetworkingProperty(
                ports=port_configs,
            ),
        )

        self.static_ip = lightsail.CfnStaticIp(
            self,
            'StaticIp',
            static_ip_name=props.static_ip_name,
            attached_to=self.instance.ref,
        )

        self.static_ip.add_dependency(self.instance)

        if props.enable_status_alarm:
            lightsail.CfnAlarm(
                self,
                'StatusCheckAlarm',
                alarm_name=f'{props.instance_name}-status-check',
                metric_name='StatusCheckFailed',
                monitored_resource_name=props.instance_name,
                comparison_operator='GreaterThanOrEqualToThreshold',
                threshold=1,
                evaluation_periods=2,
                notification_enabled=True,
                notification_triggers=['ALARM'],
                contact_protocols=['Email'],
            )
