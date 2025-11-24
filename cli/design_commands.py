"""
Design System CLI Commands - Industry Profile Management

Commands for working with Synapse industry profiles.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.design_system.profile_loader import ProfileLoader
from core.design_system.synapse_db_connector import SynapseDBConnector
from core.design_system.generator import DesignGenerator
import json


console = Console()
design_app = typer.Typer(help="Industry profile and design system commands")


@design_app.command("list")
def list_profiles(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show details")
):
    """
    List all 140+ industry profiles.

    Examples:
        br design list
        br design list --category Healthcare
        br design list -v
    """
    try:
        loader = ProfileLoader()

        # Get summary
        summary = loader.get_summary()

        # Header
        console.print()
        console.print(Panel(
            f"[bold cyan]Industry Profiles[/bold cyan]\n\n"
            f"Total: {summary['total']} profiles\n"
            f"Full Profiles: {summary['full_profiles']}\n"
            f"Basic Profiles: {summary['basic_profiles']}",
            title="📚 Synapse Design System",
            border_style="cyan"
        ))
        console.print()

        # Filter by category if specified
        if category:
            profiles = loader.get_by_category(category)
            console.print(f"[bold]Showing {len(profiles)} profiles in category: {category}[/bold]")
            console.print()

            for profile in sorted(profiles, key=lambda p: p.name):
                if verbose:
                    console.print(f"  • [cyan]{profile.name}[/cyan] (ID: {profile.id}, NAICS: {profile.naics_code})")
                else:
                    console.print(f"  • {profile.name}")

        else:
            # Show by category
            for cat, count in sorted(summary['by_category'].items(), key=lambda x: -x[1]):
                console.print(f"[bold yellow]{cat}[/bold yellow] ({count} profiles)")

                if verbose:
                    cat_profiles = loader.get_by_category(cat)
                    for profile in sorted(cat_profiles, key=lambda p: p.name)[:5]:
                        console.print(f"  • {profile.name}")
                    if len(cat_profiles) > 5:
                        console.print(f"  ... and {len(cat_profiles) - 5} more")

                console.print()

        console.print(f"[dim]💡 Use 'br design profile <industry>' to view details[/dim]")
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("profile")
def show_profile(
    industry: str = typer.Argument(..., help="Industry ID (e.g., 'restaurant', 'msp')"),
    format: str = typer.Option("rich", "--format", "-f", help="Output format: rich, json, yaml")
):
    """
    Show detailed industry profile.

    Examples:
        br design profile restaurant
        br design profile msp-managed-service-provider
        br design profile dentist --format json
    """
    try:
        loader = ProfileLoader()
        profile = loader.load_profile(industry)

        if not profile:
            # Try search
            results = loader.search(industry)

            if not results:
                console.print(f"[red]❌ Profile not found: {industry}[/red]")
                console.print("\n[dim]💡 Use 'br design list' to see available profiles[/dim]")
                raise typer.Exit(1)

            # Show search results
            console.print(f"\n[yellow]Multiple matches found for '{industry}':[/yellow]\n")
            for result in results[:10]:
                console.print(f"  • {result.name} (ID: {result.id})")

            console.print(f"\n[dim]💡 Use the ID shown above: br design profile <id>[/dim]\n")
            raise typer.Exit(0)

        # Output in requested format
        if format == "json":
            import json
            print(json.dumps(profile.to_dict(), indent=2))

        elif format == "yaml":
            import yaml
            print(yaml.dump(profile.to_dict(), default_flow_style=False))

        else:  # rich format
            console.print()
            console.print(Panel(
                f"[bold cyan]{profile.name}[/bold cyan]\n\n"
                f"Category: {profile.category}\n"
                f"NAICS Code: {profile.naics_code}\n"
                f"Profile Type: {'Full Profile' if profile.has_full_profile else 'Basic Profile'}",
                title=f"📋 {profile.id}",
                border_style="cyan"
            ))
            console.print()

            # Keywords
            if profile.keywords:
                console.print("[bold yellow]🔍 Keywords:[/bold yellow]")
                console.print(f"  {', '.join(profile.keywords[:15])}")
                if len(profile.keywords) > 15:
                    console.print(f"  [dim]... and {len(profile.keywords) - 15} more[/dim]")
                console.print()

            # Power words (if available)
            if profile.power_words:
                console.print("[bold yellow]⚡ Power Words:[/bold yellow]")
                console.print(f"  {', '.join(profile.power_words[:20])}")
                if len(profile.power_words) > 20:
                    console.print(f"  [dim]... and {len(profile.power_words) - 20} more[/dim]")
                console.print()

            # Content themes
            if profile.content_themes:
                console.print("[bold yellow]📝 Content Themes:[/bold yellow]")
                for theme in profile.content_themes[:8]:
                    console.print(f"  • {theme}")
                if len(profile.content_themes) > 8:
                    console.print(f"  [dim]... and {len(profile.content_themes) - 8} more[/dim]")
                console.print()

            # Psychology profile
            if profile.psychology_profile:
                console.print("[bold yellow]🧠 Psychology Profile:[/bold yellow]")
                psych = profile.psychology_profile

                if 'primary_triggers' in psych:
                    console.print(f"  Triggers: {', '.join(psych['primary_triggers'])}")

                if 'urgency_level' in psych:
                    console.print(f"  Urgency: {psych['urgency_level']}")

                if 'trust_importance' in psych:
                    console.print(f"  Trust: {psych['trust_importance']}")

                console.print()

            # Pain points
            if profile.common_pain_points:
                console.print("[bold yellow]😟 Common Pain Points:[/bold yellow]")
                for point in profile.common_pain_points[:5]:
                    console.print(f"  • {point}")
                if len(profile.common_pain_points) > 5:
                    console.print(f"  [dim]... and {len(profile.common_pain_points) - 5} more[/dim]")
                console.print()

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@design_app.command("search")
def search_profiles(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results")
):
    """
    Search industry profiles by name, category, or keywords.

    Examples:
        br design search dental
        br design search "health care"
        br design search technology --limit 10
    """
    try:
        loader = ProfileLoader()
        results = loader.search(query)

        console.print()
        console.print(f"[bold]Found {len(results)} matches for '{query}':[/bold]\n")

        if not results:
            console.print("[dim]No matches found. Try a different search term.[/dim]\n")
            raise typer.Exit(0)

        # Show results
        for i, profile in enumerate(results[:limit], 1):
            console.print(f"{i:2d}. [cyan]{profile.name}[/cyan]")
            console.print(f"    ID: {profile.id}  |  Category: {profile.category}")
            console.print()

        if len(results) > limit:
            console.print(f"[dim]... and {len(results) - limit} more results[/dim]\n")

        console.print(f"[dim]💡 Use 'br design profile <id>' to view details[/dim]\n")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("generate")
def generate_config(
    industry: str = typer.Argument(..., help="Industry ID"),
    use_case: str = typer.Argument(..., help="Use case (dashboard, marketplace, etc.)"),
    output: Path = typer.Option("tailwind.config.js", "--output", "-o", help="Output file")
):
    """
    Generate tailwind.config.js for industry + use case.

    Examples:
        br design generate restaurant dashboard
        br design generate dentist booking --output config.js
    """
    try:
        loader = ProfileLoader()
        profile = loader.load_profile(industry)

        if not profile:
            console.print(f"[red]❌ Profile not found: {industry}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[yellow]⚠️  Config generation not yet implemented[/yellow]")
        console.print(f"\nPlanned features:")
        console.print(f"  • Generate Tailwind config for {profile.name}")
        console.print(f"  • Merge with {use_case} use case patterns")
        console.print(f"  • Output to {output}")
        console.print(f"\nFor now, use 'br design profile {industry}' to view profile data.\n")

        raise typer.Exit(0)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("db-list")
def db_list_industries():
    """
    List all industries from Synapse database

    Connects to live Synapse Supabase database and lists all available industries.

    Example:
        br design db-list
    """
    try:
        connector = SynapseDBConnector()
        industries = connector.list_all_industries()

        console.print(f"\n[bold]📊 {len(industries)} Industries in Synapse Database:[/bold]\n")

        for i, industry in enumerate(industries, 1):
            console.print(f"  {i:3d}. {industry}")

        console.print(f"\n[dim]💡 Use 'br design db-profile <name>' to view details[/dim]\n")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        console.print(f"[yellow]💡 Make sure Synapse credentials are in environment or /Users/byronhudson/Projects/Synapse/.env[/yellow]")
        raise typer.Exit(1)


@design_app.command("db-search")
def db_search_industries(
    query: str = typer.Argument(..., help="Search term")
):
    """
    Search industries in Synapse database

    Example:
        br design db-search health
        br design db-search "e-commerce"
    """
    try:
        connector = SynapseDBConnector()
        results = connector.search_industries(query)

        if not results:
            console.print(f"\n[yellow]No industries found matching '{query}'[/yellow]\n")
            return

        console.print(f"\n[bold]🔍 Found {len(results)} matches for '{query}':[/bold]\n")

        for result in results:
            console.print(f"  • {result}")

        console.print(f"\n[dim]💡 Use 'br design db-profile \"{results[0]}\"' to view full profile[/dim]\n")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("db-profile")
def db_show_profile(
    industry: str = typer.Argument(..., help="Industry name"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, yaml")
):
    """
    Get industry profile from Synapse database

    Example:
        br design db-profile Healthcare
        br design db-profile "E-commerce" --format json
    """
    try:
        connector = SynapseDBConnector()
        profile = connector.get_industry_profile(industry)

        if not profile:
            console.print(f"\n[red]❌ Industry '{industry}' not found in database[/red]\n")
            console.print(f"[dim]💡 Use 'br design db-search {industry}' to find similar industries[/dim]\n")
            raise typer.Exit(1)

        if format == 'json':
            console.print(json.dumps(profile, indent=2))
        elif format == 'yaml':
            import yaml
            console.print(yaml.dump(profile, default_flow_style=False))
        else:
            # Text format
            console.print(f"\n[bold cyan]Industry Profile: {profile['industry']}[/bold cyan]\n")
            console.print(f"[bold]NAICS Code:[/bold] {profile.get('naics_code', 'N/A')}")
            console.print(f"[bold]Category:[/bold] {profile.get('category', 'N/A')}")

            if profile.get('design_psychology'):
                console.print(f"\n[bold]Design Psychology:[/bold]")
                psych = profile['design_psychology']
                for key, value in psych.items():
                    console.print(f"  {key}: {value}")

            if profile.get('color_scheme'):
                console.print(f"\n[bold]Color Scheme:[/bold]")
                colors = profile['color_scheme']
                for key, value in colors.items():
                    console.print(f"  {key}: {value}")

            console.print()

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("db-generate")
def db_generate_config(
    industry: str = typer.Argument(..., help="Industry name"),
    framework: str = typer.Option("tailwind", "--framework", "-f", help="Framework: tailwind, mui, chakra"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file (optional)")
):
    """
    Generate design config from Synapse database profile

    Fetches industry profile from Synapse DB and generates framework-specific config.

    Example:
        br design db-generate Healthcare
        br design db-generate "E-commerce" --framework tailwind --output ./design/tailwind.config.js
    """
    try:
        # Fetch profile from DB
        console.print(f"\n[bold]Fetching profile for {industry}...[/bold]")
        connector = SynapseDBConnector()
        profile = connector.get_industry_profile(industry)

        if not profile:
            console.print(f"\n[red]❌ Industry '{industry}' not found in database[/red]\n")
            raise typer.Exit(1)

        console.print(f"[green]✅ Profile loaded[/green]\n")

        # Generate config
        console.print(f"[bold]Generating {framework} config...[/bold]")
        generator = DesignGenerator(framework)
        config = generator.generate_config(profile)

        # Output
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(config)
            console.print(f"\n[green]✅ Config saved to {output}[/green]\n")
        else:
            console.print("\n[bold]Generated Config:[/bold]\n")
            console.print(config)

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)


@design_app.command("export")
def export_profiles(
    output_dir: Path = typer.Option("synapse-profiles", "--output", "-o", help="Output directory")
):
    """
    Export Synapse profiles from TypeScript to YAML.

    This command connects to the Synapse database and exports all profiles.

    Examples:
        br design export
        br design export --output custom-dir
    """
    try:
        from core.design_system.synapse_connector import SynapseConnector

        synapse_path = "/Users/byronhudson/Projects/Synapse/src/data/"

        console.print()
        console.print("[bold]Exporting Synapse Profiles...[/bold]\n")

        connector = SynapseConnector(synapse_path)
        count = connector.export_to_yaml(output_dir)

        console.print()
        console.print(f"[green]✅ Exported {count} profiles to {output_dir}[/green]\n")

    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)


if __name__ == "__main__":
    design_app()
