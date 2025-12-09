#!/usr/bin/env python3
"""
Massive Load Testing CLI for LLM Gateway.

A CLI tool for stress-testing the LLM Gateway API with mass parallel job submission:
- Interactive provider/model selection
- Configurable test resource creation (prompts, services, flavors)
- Fire-and-forget job submission (no monitoring)
- Progress tracking during submission

Usage:
    python scripts/massive_test.py setup      # Interactive setup
    python scripts/massive_test.py create     # Create test resources
    python scripts/massive_test.py run        # Submit jobs (fire-and-forget)
    python scripts/massive_test.py cleanup    # Remove test resources
    python scripts/massive_test.py status     # Show current config
    python scripts/massive_test.py full       # Complete workflow
"""

import asyncio
import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import click
import httpx
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

# Resource prefix for test resources (easy identification and cleanup)
RESOURCE_PREFIX = "mt-"

# Configuration file location
CONFIG_FILE = Path(__file__).parent.parent / ".massive_test_config.json"
CONFIGS_DIR = Path(__file__).parent / "test_configs"
SYNTHETIC_DATA_DIR = Path(__file__).parent.parent / "tests/data/conversations/synthetic"


class MassiveTestClient:
    """Async HTTP client for LLM Gateway API."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # Provider endpoints
    async def list_providers(self) -> List[dict]:
        resp = await self.client.get(f"{self.base_url}/api/v1/providers")
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def get_provider(self, provider_id: str) -> dict:
        resp = await self.client.get(f"{self.base_url}/api/v1/providers/{provider_id}")
        resp.raise_for_status()
        return resp.json()

    # Model endpoints
    async def list_models(self, provider_id: Optional[str] = None) -> List[dict]:
        params = {}
        if provider_id:
            params["provider_id"] = provider_id
        resp = await self.client.get(f"{self.base_url}/api/v1/models", params=params)
        resp.raise_for_status()
        return resp.json().get("items", [])

    # Prompt endpoints
    async def create_prompt(self, data: dict) -> dict:
        resp = await self.client.post(f"{self.base_url}/api/v1/prompts", json=data)
        resp.raise_for_status()
        return resp.json()

    async def list_prompts(self) -> List[dict]:
        resp = await self.client.get(f"{self.base_url}/api/v1/prompts")
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def delete_prompt(self, prompt_id: str) -> None:
        resp = await self.client.delete(f"{self.base_url}/api/v1/prompts/{prompt_id}")
        resp.raise_for_status()

    # Service endpoints
    async def create_service(self, data: dict) -> dict:
        resp = await self.client.post(f"{self.base_url}/api/v1/services", json=data)
        resp.raise_for_status()
        return resp.json()

    async def list_services(self) -> List[dict]:
        resp = await self.client.get(f"{self.base_url}/api/v1/services")
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def delete_service(self, service_id: str) -> None:
        resp = await self.client.delete(f"{self.base_url}/api/v1/services/{service_id}")
        resp.raise_for_status()

    # Flavor endpoints
    async def create_flavor(self, service_id: str, data: dict) -> dict:
        resp = await self.client.post(
            f"{self.base_url}/api/v1/services/{service_id}/flavors", json=data
        )
        resp.raise_for_status()
        return resp.json()

    async def list_flavors(self) -> List[dict]:
        """List all flavors by iterating through services."""
        services = await self.list_services()
        flavors = []
        for service in services:
            for flavor in service.get("flavors", []):
                flavor["service_id"] = service["id"]
                flavors.append(flavor)
        return flavors

    async def delete_flavor(self, service_id: str, flavor_id: str) -> None:
        resp = await self.client.delete(
            f"{self.base_url}/api/v1/services/{service_id}/flavors/{flavor_id}"
        )
        resp.raise_for_status()

    # Job endpoints
    async def run_job(
        self, service_id: str, flavor_id: str, content: str, filename: str
    ) -> dict:
        """Execute a job with file upload."""
        files = {"file": (filename, content.encode(), "text/plain")}
        data = {"flavor_id": flavor_id}
        resp = await self.client.post(
            f"{self.base_url}/api/v1/services/{service_id}/run",
            files=files,
            data=data,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_job(self, job_id: str) -> dict:
        resp = await self.client.get(f"{self.base_url}/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()

    async def list_jobs(self, limit: int = 100) -> List[dict]:
        resp = await self.client.get(
            f"{self.base_url}/api/v1/jobs", params={"page_size": limit}
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


class ConfigLoader:
    """Load YAML configuration files."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir

    def load_prompts(self) -> List[dict]:
        with open(self.config_dir / "prompts.yaml") as f:
            return yaml.safe_load(f).get("prompts", [])

    def load_services(self) -> List[dict]:
        with open(self.config_dir / "services.yaml") as f:
            return yaml.safe_load(f).get("services", [])

    def load_flavors(self) -> dict:
        with open(self.config_dir / "flavors.yaml") as f:
            return yaml.safe_load(f)

    def load_scenarios(self) -> dict:
        with open(self.config_dir / "scenarios.yaml") as f:
            return yaml.safe_load(f)


class JobSubmitter:
    """Submit jobs in parallel without waiting for completion."""

    def __init__(self, client: MassiveTestClient, parallel: int = 10):
        self.client = client
        self.semaphore = asyncio.Semaphore(parallel)
        self.submitted: List[dict] = []
        self.errors: List[dict] = []

    async def submit_job(self, job_config: dict) -> dict:
        """Submit a single job with semaphore-based rate limiting."""
        async with self.semaphore:
            try:
                result = await self.client.run_job(
                    service_id=job_config["service_id"],
                    flavor_id=job_config["flavor_id"],
                    content=job_config["content"],
                    filename=job_config["filename"],
                )
                return {
                    "job_id": result.get("job_id"),
                    "service_name": job_config.get("service_name", "unknown"),
                    "flavor_name": job_config.get("flavor_name", "unknown"),
                    "status": "submitted",
                    "error": None,
                }
            except Exception as e:
                return {
                    "job_id": None,
                    "service_name": job_config.get("service_name", "unknown"),
                    "flavor_name": job_config.get("flavor_name", "unknown"),
                    "status": "error",
                    "error": str(e),
                }

    async def submit_batch(
        self,
        jobs: List[dict],
        progress_callback: Optional[Callable[[int, int, dict], None]] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """Submit a batch of jobs, return (submitted, errors)."""
        tasks = [self.submit_job(job) for job in jobs]
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            result = await coro
            if result["status"] == "submitted":
                self.submitted.append(result)
            else:
                self.errors.append(result)
            if progress_callback:
                progress_callback(i + 1, len(jobs), result)
        return self.submitted, self.errors


class ReportGenerator:
    """Generate test reports in various formats."""

    def __init__(self, results: List[dict]):
        self.results = results

    def console_summary(self, console: Console) -> None:
        """Display summary in console using Rich tables."""
        total = len(self.results)
        completed = sum(1 for r in self.results if r["status"] == "completed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")

        # Summary panel
        summary = f"""[bold green]Completed:[/] {completed}/{total}
[bold red]Failed:[/] {failed}/{total}
[bold yellow]Errors:[/] {errors}/{total}"""

        if self.results:
            durations = [r["duration_s"] for r in self.results if r.get("duration_s")]
            if durations:
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                summary += f"""

[bold]Timing:[/]
  Average: {avg_duration:.2f}s
  Min: {min_duration:.2f}s
  Max: {max_duration:.2f}s"""

        console.print(Panel(summary, title="Test Results Summary", border_style="blue"))

        # Detailed results table
        if self.results:
            table = Table(title="Job Results (Last 20)")
            table.add_column("Job ID", style="dim", max_width=12)
            table.add_column("Service")
            table.add_column("Flavor")
            table.add_column("Status")
            table.add_column("Duration", justify="right")
            table.add_column("Error", max_width=30)

            for r in self.results[-20:]:
                status_style = {
                    "completed": "green",
                    "failed": "red",
                    "error": "yellow",
                }.get(r["status"], "white")

                table.add_row(
                    (r.get("job_id") or "N/A")[:12],
                    r.get("service_name", "N/A"),
                    r.get("flavor_name", "N/A"),
                    f"[{status_style}]{r['status']}[/{status_style}]",
                    f"{r.get('duration_s', 0):.2f}s",
                    (r.get("error") or "")[:30],
                )

            console.print(table)

    def to_json(self) -> dict:
        """Export results as JSON."""
        total = len(self.results)
        completed = sum(1 for r in self.results if r["status"] == "completed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        errors = sum(1 for r in self.results if r["status"] == "error")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_jobs": total,
                "completed": completed,
                "failed": failed,
                "errors": errors,
                "success_rate": (completed / total * 100) if total > 0 else 0,
            },
            "results": self.results,
        }

    def to_csv(self) -> str:
        """Export results as CSV."""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "job_id",
                "service_name",
                "flavor_name",
                "status",
                "duration_s",
                "error",
            ],
        )
        writer.writeheader()
        for r in self.results:
            writer.writerow(
                {
                    "job_id": r.get("job_id", ""),
                    "service_name": r.get("service_name", ""),
                    "flavor_name": r.get("flavor_name", ""),
                    "status": r.get("status", ""),
                    "duration_s": r.get("duration_s", 0),
                    "error": r.get("error", ""),
                }
            )
        return output.getvalue()


def load_config() -> dict:
    """Load persistent configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save persistent configuration."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, default=str)


def get_test_data_files() -> List[Path]:
    """Get available synthetic test data files."""
    if not SYNTHETIC_DATA_DIR.exists():
        return []
    return sorted(SYNTHETIC_DATA_DIR.glob("*.txt"))


# CLI Commands

@click.group()
@click.option("--api-url", default="http://localhost:8000", envvar="API_URL", help="API base URL")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx, api_url: str, verbose: bool):
    """LLM Gateway Massive Load Testing CLI.

    A comprehensive tool for stress-testing the LLM Gateway API with
    configurable scenarios, parallel execution, and detailed reporting.
    """
    ctx.ensure_object(dict)
    ctx.obj["api_url"] = api_url
    ctx.obj["verbose"] = verbose
    ctx.obj["console"] = Console()


@cli.command()
@click.pass_context
def setup(ctx):
    """Interactive setup: select provider and model for testing."""
    console = ctx.obj["console"]
    api_url = ctx.obj["api_url"]

    async def _setup():
        async with MassiveTestClient(api_url) as client:
            # List providers
            console.print("\n[bold]Fetching providers...[/]")
            try:
                providers = await client.list_providers()
            except httpx.HTTPError as e:
                console.print(f"[red]Error fetching providers: {e}[/]")
                console.print(f"[yellow]Make sure the API is running at {api_url}[/]")
                return

            if not providers:
                console.print("[yellow]No providers found. Please create a provider first.[/]")
                return

            # Display providers
            table = Table(title="Available Providers")
            table.add_column("#", style="dim")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("ID")

            for i, p in enumerate(providers, 1):
                table.add_row(str(i), p["name"], p.get("provider_type", "N/A"), str(p["id"])[:8])

            console.print(table)

            # Select provider
            while True:
                choice = click.prompt("Select provider number", type=int)
                if 1 <= choice <= len(providers):
                    selected_provider = providers[choice - 1]
                    break
                console.print("[red]Invalid selection[/]")

            # List models for provider
            console.print(f"\n[bold]Fetching models for {selected_provider['name']}...[/]")
            models = await client.list_models(str(selected_provider["id"]))

            if not models:
                console.print("[yellow]No models found for this provider.[/]")
                return

            # Display models
            table = Table(title="Available Models")
            table.add_column("#", style="dim")
            table.add_column("Name")
            table.add_column("Identifier")
            table.add_column("Context Length")

            for i, m in enumerate(models, 1):
                table.add_row(
                    str(i),
                    m.get("model_name", "N/A"),
                    m.get("model_identifier", "N/A"),
                    str(m.get("context_length", "N/A")),
                )

            console.print(table)

            # Select model
            while True:
                choice = click.prompt("Select model number", type=int)
                if 1 <= choice <= len(models):
                    selected_model = models[choice - 1]
                    break
                console.print("[red]Invalid selection[/]")

            # Save configuration
            config = load_config()
            config["provider_id"] = str(selected_provider["id"])
            config["provider_name"] = selected_provider["name"]
            config["model_id"] = str(selected_model["id"])
            config["model_name"] = selected_model.get("model_name", "unknown")
            config["model_identifier"] = selected_model.get("model_identifier", "unknown")
            config["setup_at"] = datetime.now().isoformat()
            save_config(config)

            console.print(
                Panel(
                    f"[green]Setup complete![/]\n\n"
                    f"Provider: {selected_provider['name']}\n"
                    f"Model: {selected_model.get('model_name', 'unknown')}",
                    title="Configuration Saved",
                )
            )

    asyncio.run(_setup())


@cli.command()
@click.pass_context
def status(ctx):
    """Show current configuration status."""
    console = ctx.obj["console"]
    config = load_config()

    if not config:
        console.print("[yellow]No configuration found. Run 'setup' first.[/]")
        return

    # Configuration panel
    setup_info = f"""[bold]Provider:[/] {config.get('provider_name', 'N/A')}
[bold]Model:[/] {config.get('model_name', 'N/A')}
[bold]Model ID:[/] {config.get('model_id', 'N/A')[:8]}...
[bold]Setup at:[/] {config.get('setup_at', 'N/A')}"""

    console.print(Panel(setup_info, title="Current Configuration"))

    # Created resources
    resources = config.get("created_resources", {})
    if resources:
        table = Table(title="Created Test Resources")
        table.add_column("Type")
        table.add_column("Count")
        table.add_column("IDs")

        for res_type, ids in resources.items():
            id_preview = ", ".join(str(i)[:8] for i in ids[:3])
            if len(ids) > 3:
                id_preview += f" (+{len(ids) - 3} more)"
            table.add_row(res_type.title(), str(len(ids)), id_preview)

        console.print(table)

    # Last run info
    if config.get("last_run"):
        console.print(f"\n[dim]Last run: {config['last_run']}[/]")


@cli.command()
@click.option("--prompts/--no-prompts", default=True, help="Create prompts")
@click.option("--services/--no-services", default=True, help="Create services")
@click.option("--flavors/--no-flavors", default=True, help="Create flavors")
@click.pass_context
def create(ctx, prompts: bool, services: bool, flavors: bool):
    """Create test resources (prompts, services, flavors)."""
    console = ctx.obj["console"]
    api_url = ctx.obj["api_url"]
    config = load_config()

    if not config.get("model_id"):
        console.print("[red]No model configured. Run 'setup' first.[/]")
        return

    model_id = config["model_id"]
    loader = ConfigLoader(CONFIGS_DIR)

    async def _create():
        created = {"prompts": [], "services": [], "flavors": []}

        async with MassiveTestClient(api_url) as client:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:

                # Create prompts
                if prompts:
                    try:
                        prompt_configs = loader.load_prompts()
                        task = progress.add_task("Creating prompts...", total=len(prompt_configs))

                        for pc in prompt_configs:
                            try:
                                result = await client.create_prompt(pc)
                                created["prompts"].append(result["id"])
                                progress.advance(task)
                            except httpx.HTTPStatusError as e:
                                if ctx.obj["verbose"]:
                                    console.print(f"[yellow]Prompt creation warning: {e}[/]")
                                progress.advance(task)
                    except FileNotFoundError:
                        console.print("[yellow]prompts.yaml not found, skipping prompts[/]")

                # Create services
                if services:
                    try:
                        service_configs = loader.load_services()
                        task = progress.add_task("Creating services...", total=len(service_configs))

                        for sc in service_configs:
                            try:
                                result = await client.create_service(sc)
                                created["services"].append(result["id"])
                                progress.advance(task)
                            except httpx.HTTPStatusError as e:
                                if ctx.obj["verbose"]:
                                    console.print(f"[yellow]Service creation warning: {e}[/]")
                                progress.advance(task)
                    except FileNotFoundError:
                        console.print("[yellow]services.yaml not found, skipping services[/]")

                # Create flavors
                if flavors and created["services"]:
                    try:
                        flavor_config = loader.load_flavors()
                        flavor_templates = flavor_config.get("flavor_templates", [])

                        total_flavors = len(created["services"]) * len(flavor_templates)
                        task = progress.add_task("Creating flavors...", total=total_flavors)

                        for service_id in created["services"]:
                            for ft in flavor_templates:
                                try:
                                    flavor_data = {
                                        "name": ft["name"],
                                        "model_id": model_id,
                                        "temperature": ft.get("temperature", 0.7),
                                        "top_p": ft.get("top_p", 0.9),
                                        "processing_mode": ft.get("processing_mode", "iterative"),
                                        "is_default": ft.get("is_default", False),
                                    }

                                    # Add optional fields
                                    if ft.get("prompt_system_content"):
                                        flavor_data["prompt_system_content"] = ft["prompt_system_content"]
                                    if ft.get("prompt_user_content"):
                                        flavor_data["prompt_user_content"] = ft["prompt_user_content"]

                                    result = await client.create_flavor(service_id, flavor_data)
                                    created["flavors"].append({
                                        "id": result["id"],
                                        "service_id": service_id,
                                        "name": flavor_data["name"]
                                    })
                                    progress.advance(task)
                                except httpx.HTTPStatusError as e:
                                    if ctx.obj["verbose"]:
                                        console.print(f"[yellow]Flavor creation warning: {e}[/]")
                                    progress.advance(task)
                    except FileNotFoundError:
                        console.print("[yellow]flavors.yaml not found, skipping flavors[/]")

        # Update config
        config["created_resources"] = created
        config["created_at"] = datetime.now().isoformat()
        save_config(config)

        # Summary
        console.print(
            Panel(
                f"[green]Resources created:[/]\n"
                f"  Prompts: {len(created['prompts'])}\n"
                f"  Services: {len(created['services'])}\n"
                f"  Flavors: {len(created['flavors'])}",
                title="Creation Complete",
            )
        )

    asyncio.run(_create())


@cli.command()
@click.option("--jobs", "-j", default=10, help="Number of jobs to submit")
@click.option("--parallel", "-p", default=5, help="Max parallel submissions")
@click.option("--scenario", "-s", default="standard", help="Scenario preset (minimal, standard, comprehensive, stress)")
@click.option("--output", "-o", type=click.Choice(["console", "json", "csv"]), default="console")
@click.option("--output-file", type=click.Path(), help="Output file path (for json/csv)")
@click.pass_context
def run(ctx, jobs: int, parallel: int, scenario: str, output: str, output_file: str):
    """Submit jobs in parallel (fire-and-forget, no waiting for completion)."""
    console = ctx.obj["console"]
    api_url = ctx.obj["api_url"]
    config = load_config()

    resources = config.get("created_resources", {})
    if not resources.get("services") or not resources.get("flavors"):
        console.print("[red]No test resources found. Run 'create' first.[/]")
        return

    # Load test data files
    test_files = get_test_data_files()
    if not test_files:
        console.print("[red]No test data files found in tests/data/conversations/synthetic/[/]")
        return

    async def _run():
        async with MassiveTestClient(api_url) as client:
            # Get services and flavors
            all_services = await client.list_services()
            all_flavors = await client.list_flavors()

            # Filter to test resources only
            test_services = [s for s in all_services if s["name"].startswith(RESOURCE_PREFIX)]
            test_flavors = [f for f in all_flavors if f["name"].startswith(RESOURCE_PREFIX)]

            if not test_services:
                console.print("[yellow]No test services found (prefix: mt-)[/]")
                return

            if not test_flavors:
                console.print("[yellow]No test flavors found (prefix: mt-)[/]")
                return

            # Build job configurations
            job_configs = []
            test_content_cache = {}

            for i in range(jobs):
                # Round-robin through services and flavors
                service = test_services[i % len(test_services)]
                service_flavors = [f for f in test_flavors if f["service_id"] == service["id"]]

                if not service_flavors:
                    continue

                flavor = service_flavors[i % len(service_flavors)]
                test_file = test_files[i % len(test_files)]

                # Cache file contents
                if test_file not in test_content_cache:
                    test_content_cache[test_file] = test_file.read_text(encoding="utf-8")

                job_configs.append(
                    {
                        "service_id": service["id"],
                        "service_name": service["name"],
                        "flavor_id": flavor["id"],
                        "flavor_name": flavor["name"],
                        "content": test_content_cache[test_file],
                        "filename": test_file.name,
                    }
                )

            if not job_configs:
                console.print("[yellow]No job configurations could be built[/]")
                return

            console.print(
                Panel(
                    f"[bold]Job Submission:[/]\n"
                    f"  Jobs to submit: {len(job_configs)}\n"
                    f"  Parallel submissions: {parallel}\n"
                    f"  Services: {len(test_services)}\n"
                    f"  Flavors: {len(test_flavors)}\n"
                    f"  Test files: {len(test_files)}",
                    title=f"Scenario: {scenario}",
                )
            )

            # Submit jobs with progress
            submitter = JobSubmitter(client, parallel=parallel)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            ) as progress:
                task = progress.add_task("Submitting jobs...", total=len(job_configs))

                def update_progress(current, total, result):
                    progress.update(task, completed=current)
                    if ctx.obj["verbose"]:
                        status_icon = "[green]OK[/]" if result["status"] == "submitted" else "[red]ERR[/]"
                        console.print(f"  {status_icon} {result.get('job_id', 'N/A')[:8] if result.get('job_id') else 'N/A'} - {result.get('service_name', 'N/A')}")

                submitted, errors = await submitter.submit_batch(job_configs, update_progress)

            # Display submission summary
            submitted_count = len(submitted)
            error_count = len(errors)

            summary = f"""[bold green]Submitted:[/] {submitted_count}/{len(job_configs)}
[bold red]Errors:[/] {error_count}/{len(job_configs)}"""

            console.print(Panel(summary, title="Submission Complete", border_style="blue"))

            # Show job IDs table
            if submitted and output == "console":
                table = Table(title=f"Submitted Jobs ({min(len(submitted), 20)} shown)")
                table.add_column("Job ID", style="dim")
                table.add_column("Service")
                table.add_column("Flavor")

                for r in submitted[:20]:
                    table.add_row(
                        r.get("job_id", "N/A")[:12] if r.get("job_id") else "N/A",
                        r.get("service_name", "N/A"),
                        r.get("flavor_name", "N/A"),
                    )

                if len(submitted) > 20:
                    table.add_row("...", f"+{len(submitted) - 20} more", "")

                console.print(table)

            # Show errors if any
            if errors:
                error_table = Table(title="Submission Errors", border_style="red")
                error_table.add_column("Service")
                error_table.add_column("Flavor")
                error_table.add_column("Error", max_width=50)

                for e in errors[:10]:
                    error_table.add_row(
                        e.get("service_name", "N/A"),
                        e.get("flavor_name", "N/A"),
                        (e.get("error") or "Unknown")[:50],
                    )

                console.print(error_table)

            # Export results if requested
            all_results = submitted + errors
            if output == "json":
                json_data = {
                    "timestamp": datetime.now().isoformat(),
                    "summary": {
                        "total_jobs": len(job_configs),
                        "submitted": submitted_count,
                        "errors": error_count,
                    },
                    "submitted": submitted,
                    "errors": errors,
                }
                if output_file:
                    with open(output_file, "w") as f:
                        json.dump(json_data, f, indent=2)
                    console.print(f"[green]Results saved to {output_file}[/]")
                else:
                    console.print_json(data=json_data)
            elif output == "csv":
                csv_output = io.StringIO()
                writer = csv.DictWriter(
                    csv_output,
                    fieldnames=["job_id", "service_name", "flavor_name", "status", "error"],
                )
                writer.writeheader()
                for r in all_results:
                    writer.writerow({
                        "job_id": r.get("job_id", ""),
                        "service_name": r.get("service_name", ""),
                        "flavor_name": r.get("flavor_name", ""),
                        "status": r.get("status", ""),
                        "error": r.get("error", ""),
                    })
                csv_data = csv_output.getvalue()
                if output_file:
                    with open(output_file, "w") as f:
                        f.write(csv_data)
                    console.print(f"[green]Results saved to {output_file}[/]")
                else:
                    console.print(csv_data)

            # Update config
            config["last_run"] = datetime.now().isoformat()
            config["last_run_stats"] = {
                "total": len(job_configs),
                "submitted": submitted_count,
                "errors": error_count,
            }
            save_config(config)

            # Tip for checking job status
            if submitted:
                console.print(f"\n[dim]Tip: Check job status in the Jobs page or via API: GET /api/v1/jobs[/]")

    asyncio.run(_run())


@cli.command()
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without deleting")
@click.option("--all", "cleanup_all", is_flag=True, help="Clean up all mt- prefixed resources, not just tracked ones")
@click.pass_context
def cleanup(ctx, dry_run: bool, cleanup_all: bool):
    """Remove all test resources (prompts, services, flavors)."""
    console = ctx.obj["console"]
    api_url = ctx.obj["api_url"]
    config = load_config()

    async def _cleanup():
        async with MassiveTestClient(api_url) as client:
            to_delete = {"flavors": [], "services": [], "prompts": []}

            if cleanup_all:
                # Find all resources with mt- prefix
                console.print("[bold]Scanning for all test resources...[/]")

                services = await client.list_services()
                to_delete["services"] = [s["id"] for s in services if s["name"].startswith(RESOURCE_PREFIX)]

                # Get flavors from services (need service_id for deletion)
                flavors = await client.list_flavors()
                to_delete["flavors"] = [
                    {"id": f["id"], "service_id": f["service_id"]}
                    for f in flavors if f["name"].startswith(RESOURCE_PREFIX)
                ]

                prompts = await client.list_prompts()
                to_delete["prompts"] = [p["id"] for p in prompts if p["name"].startswith(RESOURCE_PREFIX)]
            else:
                # Use tracked resources from config
                resources = config.get("created_resources", {})
                to_delete["flavors"] = resources.get("flavors", [])  # Already has service_id
                to_delete["services"] = resources.get("services", [])
                to_delete["prompts"] = resources.get("prompts", [])

            total = sum(len(v) for v in to_delete.values())

            if total == 0:
                console.print("[yellow]No test resources to clean up.[/]")
                return

            # Summary
            summary = f"""[bold]Resources to delete:[/]
  Flavors: {len(to_delete['flavors'])}
  Services: {len(to_delete['services'])}
  Prompts: {len(to_delete['prompts'])}
  [bold]Total: {total}[/]"""

            console.print(Panel(summary, title="Cleanup Preview"))

            if dry_run:
                console.print("[yellow]Dry run - no resources deleted[/]")
                return

            # Confirm
            if not click.confirm("Proceed with deletion?"):
                console.print("[yellow]Cancelled[/]")
                return

            # Delete in order: flavors first, then services, then prompts
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:

                # Delete flavors (need service_id)
                if to_delete["flavors"]:
                    task = progress.add_task("Deleting flavors...", total=len(to_delete["flavors"]))
                    for flavor in to_delete["flavors"]:
                        try:
                            if isinstance(flavor, dict):
                                await client.delete_flavor(flavor["service_id"], flavor["id"])
                            else:
                                # Legacy format - skip (will be deleted with service)
                                pass
                        except httpx.HTTPStatusError:
                            pass  # Already deleted or not found
                        progress.advance(task)

                # Delete services
                if to_delete["services"]:
                    task = progress.add_task("Deleting services...", total=len(to_delete["services"]))
                    for sid in to_delete["services"]:
                        try:
                            await client.delete_service(sid)
                        except httpx.HTTPStatusError:
                            pass
                        progress.advance(task)

                # Delete prompts
                if to_delete["prompts"]:
                    task = progress.add_task("Deleting prompts...", total=len(to_delete["prompts"]))
                    for pid in to_delete["prompts"]:
                        try:
                            await client.delete_prompt(pid)
                        except httpx.HTTPStatusError:
                            pass
                        progress.advance(task)

            # Clear tracked resources from config
            config["created_resources"] = {"prompts": [], "services": [], "flavors": []}
            save_config(config)

            console.print("[green]Cleanup complete![/]")

    asyncio.run(_cleanup())


@cli.command()
@click.option("--jobs", "-j", default=10, help="Number of jobs to execute")
@click.option("--parallel", "-p", default=5, help="Max parallel jobs")
@click.option("--scenario", "-s", default="standard", help="Scenario preset")
@click.option("--skip-cleanup", is_flag=True, help="Skip cleanup after run")
@click.pass_context
def full(ctx, jobs: int, parallel: int, scenario: str, skip_cleanup: bool):
    """Complete workflow: setup + create + run + cleanup."""
    console = ctx.obj["console"]

    console.print(Panel("[bold]Full Test Workflow[/]", border_style="blue"))

    # Check for existing config
    config = load_config()
    if not config.get("model_id"):
        console.print("\n[bold]Step 1: Setup[/]")
        ctx.invoke(setup)

        # Reload config after setup
        config = load_config()
        if not config.get("model_id"):
            console.print("[red]Setup incomplete. Aborting.[/]")
            return
    else:
        console.print(f"\n[dim]Using existing config: {config.get('model_name', 'unknown')}[/]")

    # Create resources
    console.print("\n[bold]Step 2: Create Resources[/]")
    ctx.invoke(create)

    # Run tests
    console.print("\n[bold]Step 3: Run Tests[/]")
    ctx.invoke(run, jobs=jobs, parallel=parallel, scenario=scenario)

    # Cleanup
    if not skip_cleanup:
        console.print("\n[bold]Step 4: Cleanup[/]")
        # Auto-confirm cleanup in full mode
        ctx.invoke(cleanup, dry_run=False)
    else:
        console.print("\n[dim]Skipping cleanup (--skip-cleanup)[/]")

    console.print(Panel("[green]Full workflow complete![/]", border_style="green"))


if __name__ == "__main__":
    cli()
