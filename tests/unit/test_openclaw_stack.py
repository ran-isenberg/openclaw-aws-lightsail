import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from cdk.constants import REGION
from cdk.openclaw_stack import OpenClawStack


def _create_template() -> Template:
    app = cdk.App()
    stack = OpenClawStack(app, 'TestStack', env=cdk.Environment(account='123456789012', region=REGION))
    return Template.from_stack(stack)


class TestAiAgent:
    def test_instance_uses_openclaw_blueprint(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'BlueprintId': 'openclaw_ls_1_0',
                'InstanceName': 'openclaw-agent',
            },
        )

    def test_instance_uses_recommended_bundle(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'BundleId': 'medium_3_0',
            },
        )

    def test_instance_has_auto_snapshot(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'AddOns': [
                    Match.object_like(
                        {
                            'AddOnType': 'AutoSnapshot',
                        }
                    ),
                ],
            },
        )


class TestAiAgentNetworking:
    def test_static_ip_exists(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::StaticIp',
            {
                'StaticIpName': 'openclaw-agent-ip',
                'AttachedTo': 'openclaw-agent',
            },
        )

    def test_resource_count(self):
        template = _create_template()
        template.resource_count_is('AWS::Lightsail::Instance', 1)
        template.resource_count_is('AWS::Lightsail::StaticIp', 1)
