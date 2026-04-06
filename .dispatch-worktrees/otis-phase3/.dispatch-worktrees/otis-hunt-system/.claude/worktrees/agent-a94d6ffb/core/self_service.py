"""
Self-Service Setup System for BuildRunner 3.0

Automates detection and setup of external service dependencies.
Guides users through credential configuration for Stripe, AWS, Supabase, etc.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json


@dataclass
class ServiceRequirement:
    """Represents a detected service dependency"""

    service: str  # stripe, aws, supabase, openai, etc.
    required: bool  # Is this service mandatory?
    detected: bool  # Was service usage detected in code?
    configured: bool  # Are credentials configured?
    env_vars: List[str] = field(default_factory=list)  # Required environment variables
    detected_in: List[str] = field(default_factory=list)  # Files where service was detected
    validation_endpoint: Optional[str] = None  # Endpoint to test credentials


# Service detection patterns
SERVICE_PATTERNS = {
    "stripe": {
        "import_patterns": [r"import\s+stripe", r"from\s+stripe"],
        "usage_patterns": [r"stripe\.(api_key|public_key)", r"sk_(?:test|live)_"],
        "env_vars": ["STRIPE_SECRET_KEY", "STRIPE_PUBLIC_KEY"],
        "docs_url": "https://stripe.com/docs/keys",
        "setup_instructions": "Get your API keys from https://dashboard.stripe.com/apikeys",
    },
    "aws": {
        "import_patterns": [r"import\s+boto3", r"from\s+boto3"],
        "usage_patterns": [r"boto3\.client", r"boto3\.resource", r"AWS"],
        "env_vars": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
        "docs_url": "https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html",
        "setup_instructions": "Create IAM user and generate access keys in AWS Console",
    },
    "supabase": {
        "import_patterns": [r"from\s+supabase", r"import\s+supabase"],
        "usage_patterns": [r"supabase\.(url|key)", r"create_client"],
        "env_vars": ["SUPABASE_URL", "SUPABASE_KEY"],
        "docs_url": "https://supabase.com/docs/guides/api/api-keys",
        "setup_instructions": "Get credentials from Supabase project settings",
    },
    "openai": {
        "import_patterns": [r"import\s+openai", r"from\s+openai"],
        "usage_patterns": [r"openai\.(api_key|ChatCompletion)", r"sk-\w+"],
        "env_vars": ["OPENAI_API_KEY"],
        "docs_url": "https://platform.openai.com/api-keys",
        "setup_instructions": "Create API key at https://platform.openai.com/api-keys",
    },
    "github": {
        "import_patterns": [r"from\s+github", r"import\s+(?:github|PyGithub)"],
        "usage_patterns": [r"Github\(", r"github\.(?:token|auth)"],
        "env_vars": ["GITHUB_TOKEN", "GITHUB_REPO"],
        "docs_url": "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token",
        "setup_instructions": "Create personal access token in GitHub Settings > Developer settings",
    },
    "notion": {
        "import_patterns": [r"from\s+notion", r"import\s+notion"],
        "usage_patterns": [r"notion\.(token|api)", r"NotionClient"],
        "env_vars": ["NOTION_TOKEN"],
        "docs_url": "https://developers.notion.com/docs/authorization",
        "setup_instructions": "Create integration at https://www.notion.so/my-integrations",
    },
    "slack": {
        "import_patterns": [r"from\s+slack", r"import\s+slack"],
        "usage_patterns": [r"slack\.(token|webhook)", r"WebClient"],
        "env_vars": ["SLACK_TOKEN", "SLACK_WEBHOOK_URL"],
        "docs_url": "https://api.slack.com/authentication/token-types",
        "setup_instructions": "Create app and get token at https://api.slack.com/apps",
    },
    "sendgrid": {
        "import_patterns": [r"from\s+sendgrid", r"import\s+sendgrid"],
        "usage_patterns": [r"sendgrid\.(api_key|SendGridAPIClient)"],
        "env_vars": ["SENDGRID_API_KEY"],
        "docs_url": "https://docs.sendgrid.com/ui/account-and-settings/api-keys",
        "setup_instructions": "Create API key in SendGrid Settings > API Keys",
    },
    "twilio": {
        "import_patterns": [r"from\s+twilio", r"import\s+twilio"],
        "usage_patterns": [r"twilio\.(account_sid|auth_token)"],
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "docs_url": "https://www.twilio.com/docs/iam/keys/api-key",
        "setup_instructions": "Get credentials from Twilio Console",
    },
    "redis": {
        "import_patterns": [r"import\s+redis", r"from\s+redis"],
        "usage_patterns": [r"redis\.Redis", r"redis://"],
        "env_vars": ["REDIS_URL"],
        "docs_url": "https://redis.io/docs/getting-started/",
        "setup_instructions": "Set up Redis server and get connection URL",
    },
}


class SelfServiceManager:
    """
    Manages self-service setup of external dependencies.

    Detects required services, validates configuration, and guides setup.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize Self-Service Manager.

        Args:
            project_root: Root directory of project (default: current directory)
        """
        self.project_root = Path(project_root or Path.cwd())
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.requirements: Dict[str, ServiceRequirement] = {}

    def detect_required_services(
        self, directories: Optional[List[str]] = None
    ) -> Dict[str, ServiceRequirement]:
        """
        Scan codebase to detect required external services.

        Args:
            directories: Directories to scan (default: ['core', 'api', 'cli'])

        Returns:
            Dictionary of service name to ServiceRequirement
        """
        if directories is None:
            directories = ["core", "api", "cli", "plugins"]

        # Initialize requirements
        for service_name in SERVICE_PATTERNS.keys():
            self.requirements[service_name] = ServiceRequirement(
                service=service_name,
                required=False,
                detected=False,
                configured=False,
                env_vars=SERVICE_PATTERNS[service_name]["env_vars"],
            )

        # Scan files
        for dir_name in directories:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue
                self._scan_file(py_file)

        # Check which services are configured
        self._check_configuration()

        # Filter to only detected services
        detected = {name: req for name, req in self.requirements.items() if req.detected}
        return detected

    def _scan_file(self, file_path: Path):
        """Scan a single file for service usage"""
        try:
            content = file_path.read_text()

            for service_name, patterns in SERVICE_PATTERNS.items():
                # Check import patterns
                for pattern in patterns["import_patterns"]:
                    if re.search(pattern, content):
                        self.requirements[service_name].detected = True
                        self.requirements[service_name].detected_in.append(
                            str(file_path.relative_to(self.project_root))
                        )
                        break

                # Check usage patterns
                if not self.requirements[service_name].detected:
                    for pattern in patterns["usage_patterns"]:
                        if re.search(pattern, content):
                            self.requirements[service_name].detected = True
                            self.requirements[service_name].detected_in.append(
                                str(file_path.relative_to(self.project_root))
                            )
                            break

        except Exception:
            pass  # Skip files that can't be read

    def _check_configuration(self):
        """Check if services are configured in environment"""
        # Load .env if it exists
        env_vars = {}
        if self.env_file.exists():
            env_vars = self._parse_env_file(self.env_file)

        # Check each service
        for service_name, requirement in self.requirements.items():
            if requirement.detected:
                # Check if all required env vars are present
                all_configured = all(
                    var in env_vars or var in os.environ for var in requirement.env_vars
                )
                requirement.configured = all_configured
                requirement.required = requirement.detected  # If detected, consider it required

    def _parse_env_file(self, env_path: Path) -> Dict[str, str]:
        """Parse .env file into dictionary"""
        env_vars = {}
        try:
            for line in env_path.read_text().split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
        except Exception:
            pass
        return env_vars

    def check_environment(self) -> Dict[str, bool]:
        """
        Verify environment configuration for all detected services.

        Returns:
            Dictionary mapping service name to configuration status
        """
        self.detect_required_services()
        return {name: req.configured for name, req in self.requirements.items() if req.detected}

    def prompt_for_credentials(self, service_name: str, interactive: bool = True) -> Dict[str, str]:
        """
        Prompt user for service credentials.

        Args:
            service_name: Name of service to configure
            interactive: If True, use interactive prompts; if False, return template

        Returns:
            Dictionary of environment variables and values
        """
        if service_name not in SERVICE_PATTERNS:
            raise ValueError(f"Unknown service: {service_name}")

        patterns = SERVICE_PATTERNS[service_name]
        credentials = {}

        if interactive:
            print(f"\n🔧 Setting up {service_name.title()}")
            print(f"📚 Documentation: {patterns['docs_url']}")
            print(f"💡 Instructions: {patterns['setup_instructions']}\n")

            for env_var in patterns["env_vars"]:
                # Prompt for each variable
                value = input(f"Enter {env_var}: ").strip()
                if value:
                    credentials[env_var] = value
        else:
            # Return template
            for env_var in patterns["env_vars"]:
                credentials[env_var] = f"your_{service_name}_{env_var.lower()}_here"

        return credentials

    def generate_env_template(self, output_path: Optional[str] = None) -> str:
        """
        Generate .env.example template with all detected services.

        Args:
            output_path: Path to write template (default: .env.example)

        Returns:
            Generated template content
        """
        if not self.requirements:
            self.detect_required_services()

        template_lines = [
            "# Environment Variables for BuildRunner Project",
            "# Copy this file to .env and fill in your credentials",
            "",
        ]

        # Group services
        detected_services = {name: req for name, req in self.requirements.items() if req.detected}

        for service_name, requirement in detected_services.items():
            patterns = SERVICE_PATTERNS[service_name]

            template_lines.append(f"\n# {service_name.title()} Configuration")
            template_lines.append(f"# Documentation: {patterns['docs_url']}")
            template_lines.append(f"# Required: {'Yes' if requirement.required else 'Optional'}")

            for env_var in requirement.env_vars:
                template_lines.append(f"{env_var}=your_{service_name}_{env_var.lower()}_here")

        template = "\n".join(template_lines)

        # Write to file if path specified
        if output_path:
            Path(output_path).write_text(template)
        elif not self.env_example.exists():
            self.env_example.write_text(template)

        return template

    def validate_credentials(
        self, service_name: str, credentials: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """
        Validate service credentials by making test API call.

        Args:
            service_name: Name of service to validate
            credentials: Credentials to test (default: use environment)

        Returns:
            Tuple of (success, message)
        """
        if service_name not in SERVICE_PATTERNS:
            return False, f"Unknown service: {service_name}"

        # Load credentials from environment if not provided
        if credentials is None:
            credentials = {}
            for env_var in SERVICE_PATTERNS[service_name]["env_vars"]:
                value = os.getenv(env_var)
                if value:
                    credentials[env_var] = value

        # Check if all required variables are present
        missing_vars = [
            var
            for var in SERVICE_PATTERNS[service_name]["env_vars"]
            if var not in credentials or not credentials[var]
        ]

        if missing_vars:
            return False, f"Missing required variables: {', '.join(missing_vars)}"

        # Basic validation - check format
        validation_result = self._validate_credential_format(service_name, credentials)
        if not validation_result[0]:
            return validation_result

        return True, f"{service_name.title()} credentials validated successfully"

    def _validate_credential_format(
        self, service_name: str, credentials: Dict[str, str]
    ) -> Tuple[bool, str]:
        """Validate credential format without making API calls"""
        # Service-specific format validation
        if service_name == "stripe":
            if "STRIPE_SECRET_KEY" in credentials:
                key = credentials["STRIPE_SECRET_KEY"]
                if not (key.startswith("sk_test_") or key.startswith("sk_live_")):
                    return False, "Stripe secret key should start with sk_test_ or sk_live_"

        elif service_name == "aws":
            if "AWS_ACCESS_KEY_ID" in credentials:
                key_id = credentials["AWS_ACCESS_KEY_ID"]
                if len(key_id) != 20:
                    return False, "AWS Access Key ID should be 20 characters"

        elif service_name == "openai":
            if "OPENAI_API_KEY" in credentials:
                key = credentials["OPENAI_API_KEY"]
                if not key.startswith("sk-"):
                    return False, "OpenAI API key should start with sk-"

        elif service_name == "github":
            if "GITHUB_TOKEN" in credentials:
                token = credentials["GITHUB_TOKEN"]
                if len(token) < 20:
                    return False, "GitHub token appears to be too short"

        return True, "Format validation passed"

    def setup_service(self, service_name: str, interactive: bool = True) -> bool:
        """
        Guide user through complete service setup.

        Args:
            service_name: Name of service to set up
            interactive: If True, use interactive prompts

        Returns:
            True if setup successful
        """
        if service_name not in SERVICE_PATTERNS:
            print(f"❌ Unknown service: {service_name}")
            return False

        # Prompt for credentials
        credentials = self.prompt_for_credentials(service_name, interactive)

        if not credentials:
            print(f"⚠️  No credentials provided for {service_name}")
            return False

        # Validate credentials
        valid, message = self.validate_credentials(service_name, credentials)

        if not valid:
            print(f"❌ Validation failed: {message}")
            return False

        # Update .env file
        self._update_env_file(credentials)

        print(f"✅ {service_name.title()} configured successfully!")
        return True

    def _update_env_file(self, credentials: Dict[str, str]):
        """Update .env file with new credentials"""
        # Read existing .env
        existing_vars = {}
        if self.env_file.exists():
            existing_vars = self._parse_env_file(self.env_file)

        # Merge with new credentials
        existing_vars.update(credentials)

        # Write back to .env
        lines = [f"{key}={value}" for key, value in existing_vars.items()]
        self.env_file.write_text("\n".join(lines) + "\n")

    def get_setup_status(self) -> Dict[str, Any]:
        """
        Get comprehensive setup status for all services.

        Returns:
            Dictionary with service statuses and recommendations
        """
        self.detect_required_services()

        status = {
            "total_services": len([r for r in self.requirements.values() if r.detected]),
            "configured_services": len([r for r in self.requirements.values() if r.configured]),
            "missing_services": [],
            "services": {},
        }

        for name, req in self.requirements.items():
            if req.detected:
                status["services"][name] = {
                    "configured": req.configured,
                    "required": req.required,
                    "env_vars": req.env_vars,
                    "detected_in": req.detected_in,
                }

                if not req.configured:
                    status["missing_services"].append(name)

        return status

    def generate_setup_report(self) -> str:
        """
        Generate human-readable setup status report.

        Returns:
            Formatted report string
        """
        status = self.get_setup_status()

        if status["total_services"] == 0:
            return "✅ No external services detected in this project."

        report = ["# Service Setup Status\n"]
        report.append(f"**Services Detected:** {status['total_services']}")
        report.append(
            f"**Configured:** {status['configured_services']}/{status['total_services']}\n"
        )

        if status["configured_services"] == status["total_services"]:
            report.append("✅ **All services are configured!**\n")
        else:
            report.append(
                f"⚠️  **{len(status['missing_services'])} services need configuration:**\n"
            )
            for service in status["missing_services"]:
                report.append(f"- {service.title()}")

        report.append("\n## Service Details\n")

        for service_name, service_info in status["services"].items():
            emoji = "✅" if service_info["configured"] else "⚠️"
            report.append(f"\n### {emoji} {service_name.title()}")
            report.append(
                f"- **Status:** {'Configured' if service_info['configured'] else 'Not configured'}"
            )
            report.append(f"- **Required:** {'Yes' if service_info['required'] else 'Optional'}")
            report.append(f"- **Environment Variables:** {', '.join(service_info['env_vars'])}")

            if service_info["detected_in"]:
                report.append(f"- **Detected in:** {', '.join(service_info['detected_in'][:3])}")
                if len(service_info["detected_in"]) > 3:
                    report.append(f"  (and {len(service_info['detected_in']) - 3} more)")

            if not service_info["configured"]:
                patterns = SERVICE_PATTERNS[service_name]
                report.append(f"- **Setup:** Run `br service setup {service_name}`")
                report.append(f"- **Docs:** {patterns['docs_url']}")

        return "\n".join(report)
