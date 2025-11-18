"""
Tests for Self-Service Setup System

Comprehensive test coverage for service dependency detection and setup.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from core.self_service import (
    SelfServiceManager,
    ServiceRequirement,
    SERVICE_PATTERNS
)


# Fixtures

@pytest.fixture
def manager(tmp_path):
    """Create SelfServiceManager instance with temp directory"""
    return SelfServiceManager(str(tmp_path))


@pytest.fixture
def sample_stripe_code():
    """Sample code using Stripe"""
    return """
import stripe
from stripe import Customer, Charge

def process_payment(amount, token):
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    charge = stripe.Charge.create(
        amount=amount,
        currency='usd',
        source=token
    )
    return charge
"""


@pytest.fixture
def sample_aws_code():
    """Sample code using AWS"""
    return """
import boto3

def upload_to_s3(file_path, bucket):
    s3 = boto3.client('s3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    s3.upload_file(file_path, bucket, 'file.txt')
"""


@pytest.fixture
def sample_env_content():
    """Sample .env file content"""
    return """# Environment Variables
STRIPE_SECRET_KEY=sk_test_123456789
STRIPE_PUBLIC_KEY=pk_test_123456789
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
"""


# Test ServiceRequirement

class TestServiceRequirement:
    """Test ServiceRequirement dataclass"""

    def test_init(self):
        """ServiceRequirement initializes correctly"""
        req = ServiceRequirement(
            service="stripe",
            required=True,
            detected=True,
            configured=False,
            env_vars=['STRIPE_SECRET_KEY']
        )

        assert req.service == "stripe"
        assert req.required is True
        assert req.detected is True
        assert req.configured is False
        assert req.env_vars == ['STRIPE_SECRET_KEY']


# Test Service Detection

class TestServiceDetection:
    """Test service dependency detection"""

    def test_detect_stripe(self, manager, tmp_path, sample_stripe_code):
        """Detect Stripe usage"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        requirements = manager.detect_required_services(directories=['core'])

        assert 'stripe' in requirements
        assert requirements['stripe'].detected is True
        assert 'payments.py' in requirements['stripe'].detected_in[0]

    def test_detect_aws(self, manager, tmp_path, sample_aws_code):
        """Detect AWS usage"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "storage.py").write_text(sample_aws_code)

        requirements = manager.detect_required_services(directories=['core'])

        assert 'aws' in requirements
        assert requirements['aws'].detected is True

    def test_detect_multiple_services(self, manager, tmp_path, sample_stripe_code, sample_aws_code):
        """Detect multiple services"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)
        (code_dir / "storage.py").write_text(sample_aws_code)

        requirements = manager.detect_required_services(directories=['core'])

        assert 'stripe' in requirements
        assert 'aws' in requirements
        assert len(requirements) >= 2

    def test_detect_openai(self, manager, tmp_path):
        """Detect OpenAI usage"""
        code = """
import openai

def generate_text(prompt):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response
"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "ai.py").write_text(code)

        requirements = manager.detect_required_services(directories=['core'])

        assert 'openai' in requirements
        assert requirements['openai'].detected is True

    def test_detect_github(self, manager, tmp_path):
        """Detect GitHub API usage"""
        code = """
from github import Github

def create_issue(repo_name, title, body):
    g = Github(os.getenv('GITHUB_TOKEN'))
    repo = g.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body)
    return issue
"""
        code_dir = tmp_path / "plugins"
        code_dir.mkdir()
        (code_dir / "github.py").write_text(code)

        requirements = manager.detect_required_services(directories=['plugins'])

        assert 'github' in requirements
        assert requirements['github'].detected is True

    def test_no_services_detected(self, manager, tmp_path):
        """Handle code with no external services"""
        code = """
def simple_function():
    return "hello world"

class SimpleClass:
    pass
"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "simple.py").write_text(code)

        requirements = manager.detect_required_services(directories=['core'])

        assert len(requirements) == 0

    def test_scan_file_error_handling(self, manager, tmp_path):
        """Handle file read errors gracefully"""
        # Create a file that can't be read
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        bad_file = code_dir / "unreadable.py"
        bad_file.write_text("content")
        bad_file.chmod(0o000)  # Make unreadable

        try:
            # Should not raise exception
            manager.detect_required_services(directories=['core'])
        finally:
            # Restore permissions for cleanup
            bad_file.chmod(0o644)


# Test Environment Checking

class TestEnvironmentChecking:
    """Test environment configuration checking"""

    def test_parse_env_file(self, manager, tmp_path, sample_env_content):
        """Parse .env file correctly"""
        env_file = tmp_path / ".env"
        env_file.write_text(sample_env_content)

        env_vars = manager._parse_env_file(env_file)

        assert env_vars['STRIPE_SECRET_KEY'] == 'sk_test_123456789'
        assert env_vars['AWS_ACCESS_KEY_ID'] == 'AKIAIOSFODNN7EXAMPLE'

    def test_parse_env_file_with_comments(self, manager, tmp_path):
        """Parse .env with comments and blank lines"""
        env_content = """
# This is a comment
STRIPE_SECRET_KEY=sk_test_123

# Another comment
AWS_REGION=us-east-1

"""
        env_file = tmp_path / ".env"
        env_file.write_text(env_content)

        env_vars = manager._parse_env_file(env_file)

        assert 'STRIPE_SECRET_KEY' in env_vars
        assert 'AWS_REGION' in env_vars
        assert len(env_vars) == 2

    def test_check_environment_configured(self, manager, tmp_path, sample_stripe_code, sample_env_content):
        """Check if services are configured"""
        # Setup code and env
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        env_file = tmp_path / ".env"
        env_file.write_text(sample_env_content)

        status = manager.check_environment()

        assert 'stripe' in status
        assert status['stripe'] is True  # Should be configured

    def test_check_environment_not_configured(self, manager, tmp_path, sample_stripe_code):
        """Check services that are not configured"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        # No .env file created

        status = manager.check_environment()

        assert 'stripe' in status
        assert status['stripe'] is False  # Should not be configured


# Test Credential Prompting

class TestCredentialPrompting:
    """Test interactive credential prompting"""

    def test_prompt_for_credentials_non_interactive(self, manager):
        """Generate credential template in non-interactive mode"""
        credentials = manager.prompt_for_credentials('stripe', interactive=False)

        assert 'STRIPE_SECRET_KEY' in credentials
        assert 'STRIPE_PUBLIC_KEY' in credentials
        assert 'your_stripe' in credentials['STRIPE_SECRET_KEY'].lower()

    @patch('builtins.input', side_effect=['sk_test_123', 'pk_test_456'])
    def test_prompt_for_credentials_interactive(self, mock_input, manager, capsys):
        """Prompt for credentials interactively"""
        credentials = manager.prompt_for_credentials('stripe', interactive=True)

        assert credentials['STRIPE_SECRET_KEY'] == 'sk_test_123'
        assert credentials['STRIPE_PUBLIC_KEY'] == 'pk_test_456'

        # Verify prompts were shown
        captured = capsys.readouterr()
        assert 'Setting up Stripe' in captured.out

    def test_prompt_unknown_service(self, manager):
        """Raise error for unknown service"""
        with pytest.raises(ValueError, match="Unknown service"):
            manager.prompt_for_credentials('unknown_service')


# Test .env Template Generation

class TestEnvTemplateGeneration:
    """Test .env template generation"""

    def test_generate_env_template(self, manager, tmp_path, sample_stripe_code):
        """Generate .env.example template"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        template = manager.generate_env_template()

        assert 'STRIPE_SECRET_KEY' in template
        assert 'STRIPE_PUBLIC_KEY' in template
        assert '# Stripe Configuration' in template
        assert 'Documentation:' in template

    def test_generate_env_template_multiple_services(self, manager, tmp_path, sample_stripe_code, sample_aws_code):
        """Generate template with multiple services"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)
        (code_dir / "storage.py").write_text(sample_aws_code)

        template = manager.generate_env_template()

        assert '# Stripe Configuration' in template
        assert '# Aws Configuration' in template
        assert 'STRIPE_SECRET_KEY' in template
        assert 'AWS_ACCESS_KEY_ID' in template

    def test_generate_env_template_to_file(self, manager, tmp_path, sample_stripe_code):
        """Generate template and save to file"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        output_path = tmp_path / ".env.custom"
        template = manager.generate_env_template(output_path=str(output_path))

        assert output_path.exists()
        assert output_path.read_text() == template


# Test Credential Validation

class TestCredentialValidation:
    """Test credential format validation"""

    def test_validate_stripe_correct_format(self, manager):
        """Validate correct Stripe key format"""
        credentials = {
            'STRIPE_SECRET_KEY': 'sk_test_1234567890',
            'STRIPE_PUBLIC_KEY': 'pk_test_1234567890'
        }

        valid, message = manager.validate_credentials('stripe', credentials)

        assert valid is True
        assert 'successfully' in message.lower()

    def test_validate_stripe_incorrect_format(self, manager):
        """Detect incorrect Stripe key format"""
        credentials = {
            'STRIPE_SECRET_KEY': 'invalid_key_format',
            'STRIPE_PUBLIC_KEY': 'pk_test_valid'
        }

        valid, message = manager.validate_credentials('stripe', credentials)

        assert valid is False
        assert 'should start with' in message.lower()

    def test_validate_aws_correct_format(self, manager):
        """Validate correct AWS key format"""
        credentials = {
            'AWS_ACCESS_KEY_ID': 'AKIAIOSFODNN7EXAMPLE',  # 20 chars
            'AWS_SECRET_ACCESS_KEY': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
            'AWS_REGION': 'us-east-1'
        }

        valid, message = manager.validate_credentials('aws', credentials)

        assert valid is True

    def test_validate_aws_incorrect_key_length(self, manager):
        """Detect incorrect AWS key length"""
        credentials = {
            'AWS_ACCESS_KEY_ID': 'TOOSHORT',  # Should be 20 chars
            'AWS_SECRET_ACCESS_KEY': 'valid_secret_key',
            'AWS_REGION': 'us-east-1'
        }

        valid, message = manager.validate_credentials('aws', credentials)

        assert valid is False
        assert '20 characters' in message

    def test_validate_openai_correct_format(self, manager):
        """Validate correct OpenAI key format"""
        credentials = {
            'OPENAI_API_KEY': 'sk-1234567890abcdef1234567890abcdef'
        }

        valid, message = manager.validate_credentials('openai', credentials)

        assert valid is True

    def test_validate_openai_incorrect_format(self, manager):
        """Detect incorrect OpenAI key format"""
        credentials = {
            'OPENAI_API_KEY': 'invalid_key'
        }

        valid, message = manager.validate_credentials('openai', credentials)

        assert valid is False
        assert 'should start with sk-' in message.lower()

    def test_validate_missing_variables(self, manager):
        """Detect missing required variables"""
        credentials = {
            'STRIPE_SECRET_KEY': 'sk_test_123'
            # Missing STRIPE_PUBLIC_KEY
        }

        valid, message = manager.validate_credentials('stripe', credentials)

        assert valid is False
        assert 'Missing required variables' in message

    def test_validate_unknown_service(self, manager):
        """Handle unknown service validation"""
        valid, message = manager.validate_credentials('unknown_service')

        assert valid is False
        assert 'Unknown service' in message


# Test Service Setup

class TestServiceSetup:
    """Test complete service setup workflow"""

    @patch('builtins.input', side_effect=['sk_test_123', 'pk_test_456'])
    def test_setup_service_success(self, mock_input, manager, tmp_path):
        """Successfully set up a service"""
        success = manager.setup_service('stripe', interactive=True)

        assert success is True
        assert (tmp_path / ".env").exists()

        # Verify .env content
        env_content = (tmp_path / ".env").read_text()
        assert 'STRIPE_SECRET_KEY=sk_test_123' in env_content

    def test_setup_service_unknown(self, manager, capsys):
        """Handle unknown service"""
        success = manager.setup_service('unknown_service')

        assert success is False
        captured = capsys.readouterr()
        assert 'Unknown service' in captured.out

    def test_update_env_file(self, manager, tmp_path):
        """Update .env file with new credentials"""
        # Create existing .env
        existing_env = tmp_path / ".env"
        existing_env.write_text("EXISTING_VAR=value\n")

        credentials = {
            'NEW_VAR': 'new_value',
            'EXISTING_VAR': 'updated_value'
        }

        manager._update_env_file(credentials)

        env_content = existing_env.read_text()
        assert 'NEW_VAR=new_value' in env_content
        assert 'EXISTING_VAR=updated_value' in env_content


# Test Status Reporting

class TestStatusReporting:
    """Test setup status reporting"""

    def test_get_setup_status(self, manager, tmp_path, sample_stripe_code, sample_aws_code):
        """Get comprehensive setup status"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)
        (code_dir / "storage.py").write_text(sample_aws_code)

        status = manager.get_setup_status()

        assert status['total_services'] >= 2
        assert 'stripe' in status['services']
        assert 'aws' in status['services']
        assert isinstance(status['missing_services'], list)

    def test_generate_setup_report_no_services(self, manager):
        """Generate report when no services detected"""
        report = manager.generate_setup_report()

        assert 'No external services detected' in report
        assert '✅' in report

    def test_generate_setup_report_with_services(self, manager, tmp_path, sample_stripe_code):
        """Generate report with detected services"""
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)

        report = manager.generate_setup_report()

        assert '# Service Setup Status' in report
        assert 'Stripe' in report
        assert 'STRIPE_SECRET_KEY' in report
        assert 'br service setup' in report


# Integration Tests

class TestSelfServiceIntegration:
    """End-to-end integration tests"""

    def test_full_workflow(self, tmp_path, sample_stripe_code, sample_aws_code):
        """Full workflow: detect, validate, setup"""
        # Setup project with multiple services
        code_dir = tmp_path / "core"
        code_dir.mkdir()
        (code_dir / "payments.py").write_text(sample_stripe_code)
        (code_dir / "storage.py").write_text(sample_aws_code)

        manager = SelfServiceManager(str(tmp_path))

        # Detect services
        requirements = manager.detect_required_services()
        assert len(requirements) >= 2

        # Generate template
        template = manager.generate_env_template()
        assert 'STRIPE_SECRET_KEY' in template
        assert 'AWS_ACCESS_KEY_ID' in template

        # Check status before setup
        status = manager.get_setup_status()
        assert status['configured_services'] == 0

        # Create .env manually (simulating setup)
        env_content = """
STRIPE_SECRET_KEY=sk_test_123
STRIPE_PUBLIC_KEY=pk_test_456
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=secret
AWS_REGION=us-east-1
"""
        (tmp_path / ".env").write_text(env_content)

        # Check status after setup
        status2 = manager.get_setup_status()
        assert status2['configured_services'] > 0

    def test_service_patterns_completeness(self):
        """Verify all service patterns are well-formed"""
        for service_name, patterns in SERVICE_PATTERNS.items():
            assert 'import_patterns' in patterns
            assert 'usage_patterns' in patterns
            assert 'env_vars' in patterns
            assert 'docs_url' in patterns
            assert 'setup_instructions' in patterns

            assert len(patterns['env_vars']) > 0
            assert isinstance(patterns['env_vars'], list)
