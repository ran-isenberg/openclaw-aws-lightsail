import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from cdk.constants import REGION
from cdk.constructs.ai_agent import SSH_PORT, AiAgent, AiAgentProps
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

    def test_auto_snapshot_uses_default_time(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'AddOns': [
                    Match.object_like(
                        {
                            'AddOnType': 'AutoSnapshot',
                            'AutoSnapshotAddOnRequest': {'SnapshotTimeOfDay': '04:00'},
                        }
                    ),
                ],
            },
        )

    def test_auto_snapshot_time_is_configurable(self):
        app = cdk.App()
        stack = cdk.Stack(app, 'SnapshotTimeTestStack')
        AiAgent(
            stack,
            'Agent',
            props=AiAgentProps(
                instance_name='test-instance',
                availability_zone='us-east-1a',
                static_ip_name='test-ip',
                snapshot_time_of_day='06:00',
            ),
        )
        template = Template.from_stack(stack)
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'AddOns': [
                    Match.object_like(
                        {
                            'AddOnType': 'AutoSnapshot',
                            'AutoSnapshotAddOnRequest': {'SnapshotTimeOfDay': '06:00'},
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
            },
        )

    def test_resource_count(self):
        template = _create_template()
        template.resource_count_is('AWS::Lightsail::Instance', 1)
        template.resource_count_is('AWS::Lightsail::StaticIp', 1)


class TestSecurity:
    def test_firewall_includes_https(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'Networking': Match.object_like(
                    {
                        'Ports': Match.array_with(
                            [
                                Match.object_like({'FromPort': 443, 'ToPort': 443, 'Protocol': 'tcp', 'Cidrs': ['0.0.0.0/0']}),
                            ]
                        ),
                    }
                ),
            },
        )

    def test_firewall_includes_ssh(self):
        template = _create_template()
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {
                'Networking': Match.object_like(
                    {
                        'Ports': Match.array_with(
                            [
                                Match.object_like({'FromPort': 22, 'ToPort': 22}),
                            ]
                        ),
                    }
                ),
            },
        )

    def test_ssh_is_not_open_to_world(self):
        template = _create_template()
        resources = template.to_json()['Resources']
        for resource in resources.values():
            if resource['Type'] != 'AWS::Lightsail::Instance':
                continue
            for port in resource['Properties']['Networking']['Ports']:
                if port.get('FromPort') == SSH_PORT:
                    assert '0.0.0.0/0' not in port.get('Cidrs', [])

    def test_no_unexpected_resource_types(self):
        """Ensure only expected resource types are created."""
        template = _create_template()
        template.resource_count_is('AWS::Lightsail::Instance', 1)
        template.resource_count_is('AWS::Lightsail::StaticIp', 1)
        # Verify no other resource types snuck in
        resources = template.to_json().get('Resources', {})
        resource_types = {r['Type'] for r in resources.values()}
        assert resource_types == {'AWS::Lightsail::Instance', 'AWS::Lightsail::StaticIp'}

    def test_tags_are_applied(self):
        app = cdk.App()
        stack = OpenClawStack(app, 'TagTestStack', env=cdk.Environment(account='123456789012', region=REGION))
        cdk.Tags.of(app).add('Project', 'OpenClaw')
        cdk.Tags.of(app).add('ManagedBy', 'CDK')
        template = Template.from_stack(stack)
        # Assert each tag independently — arrayWith is order-sensitive so single-element matchers are safer.
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {'Tags': Match.array_with([Match.object_like({'Key': 'Project', 'Value': 'OpenClaw'})])},
        )
        template.has_resource_properties(
            'AWS::Lightsail::Instance',
            {'Tags': Match.array_with([Match.object_like({'Key': 'ManagedBy', 'Value': 'CDK'})])},
        )


class TestMonitoring:
    def test_no_alarm_by_default(self):
        template = _create_template()
        template.resource_count_is('AWS::Lightsail::Alarm', 0)

    def test_status_alarm_created_when_enabled(self):
        app = cdk.App()
        stack = cdk.Stack(app, 'AlarmTestStack')
        AiAgent(
            stack,
            'Agent',
            props=AiAgentProps(
                instance_name='test-instance',
                availability_zone='us-east-1a',
                static_ip_name='test-ip',
                enable_status_alarm=True,
            ),
        )
        template = Template.from_stack(stack)
        template.resource_count_is('AWS::Lightsail::Alarm', 1)
        template.has_resource_properties(
            'AWS::Lightsail::Alarm',
            {
                'MetricName': 'StatusCheckFailed',
                'MonitoredResourceName': 'test-instance',
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'Threshold': 1,
                'EvaluationPeriods': 2,
                'NotificationEnabled': True,
                'NotificationTriggers': ['ALARM'],
                'ContactProtocols': ['Email'],
            },
        )
