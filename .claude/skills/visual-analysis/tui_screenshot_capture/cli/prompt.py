"""Generate AI analysis prompts for TUI screens.

Provides the `generate-prompt` command for generating contextual prompts
that can be used with Claude Code's native multimodal vision (Read tool).
"""

from __future__ import annotations

from typing import Annotated

import typer
from loguru import logger

from tui_screenshot_capture.analysis import AnalysisType, generate_analysis_prompt
from tui_screenshot_capture.discovery import discover_screens


def register(app: typer.Typer) -> None:
    """Register generate-prompt command."""

    @app.command("generate-prompt")
    def generate_prompt(
        screens: Annotated[
            list[str] | None,
            typer.Argument(
                help="Screen name(s) to generate prompts for. Use 'all' for all screens.",
            ),
        ] = None,
        analysis_type: Annotated[
            str,
            typer.Option(
                "--type",
                "-t",
                help="Analysis type: quick, standard, data, freeze, visual, layout, full",
            ),
        ] = "standard",
        delay: Annotated[
            float | None,
            typer.Option(
                "--delay",
                "-d",
                help="Capture delay in seconds (for context in prompt)",
            ),
        ] = None,
        output_format: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Output format: text (default), json, markdown",
            ),
        ] = "text",
        image_path: Annotated[
            str | None,
            typer.Option(
                "--image-path",
                "-i",
                help="Image path pattern (use {screen} as placeholder)",
            ),
        ] = None,
    ) -> None:
        """Generate AI analysis prompts for TUI screens.

        Generates contextual prompts using dynamic widget discovery from
        actual screen code. These prompts can be used with AI vision tools.

        Examples:
            # Generate prompt for a single screen
            capture-tui generate-prompt home --type full

            # Generate prompts for multiple screens
            capture-tui generate-prompt home cluster charts --type data

            # Generate prompts for all screens
            capture-tui generate-prompt all --type freeze --delay 90

            # Generate with image path for copy-paste usage
            capture-tui generate-prompt home --image-path "/tmp/screenshots/{screen}/{screen}-090s.png"

            # Output as JSON for programmatic use
            capture-tui generate-prompt home --type full --format json

        """
        # Handle 'all' keyword
        available = discover_screens()
        if screens and len(screens) == 1 and screens[0].lower() == "all":
            screens = list(available.keys())
            logger.info(f"Generating prompts for all {len(screens)} screens")
        elif not screens:
            logger.error("Must specify at least one screen name or 'all'")
            raise typer.Exit(code=1)

        # Validate analysis type
        valid_types = [t.value for t in AnalysisType]
        if analysis_type not in valid_types:
            logger.error(f"Invalid analysis type: {analysis_type}")
            logger.info(f"Valid types: {', '.join(valid_types)}")
            raise typer.Exit(code=1)

        # Validate screens exist (reuse already-fetched available screens)
        invalid = [s for s in screens if s not in available and s != "home"]
        if invalid:
            logger.error(f"Invalid screen name(s): {', '.join(invalid)}")
            logger.info(f"Available: {', '.join(sorted(available.keys()))}")
            raise typer.Exit(code=1)

        # Generate prompts
        results: list[dict[str, str]] = []

        for screen_name in screens:
            prompt = generate_analysis_prompt(
                screen_name=screen_name,
                analysis_type=analysis_type,
                delay_seconds=delay,
            )

            # Build image path if pattern provided
            img_path = None
            if image_path:
                img_path = image_path.replace("{screen}", screen_name)

            results.append({
                "screen": screen_name,
                "analysis_type": analysis_type,
                "prompt": prompt,
                "image_path": img_path or "",
            })

        # Output based on format
        if output_format == "json":
            _output_json(results)
        elif output_format == "markdown":
            _output_markdown(results)
        else:
            _output_text(results)


def _output_text(results: list[dict[str, str]]) -> None:
    """Output prompts as plain text."""
    for i, result in enumerate(results):
        if i > 0:
            print("\n" + "=" * 70 + "\n")

        print(f"SCREEN: {result['screen'].upper()}")
        print(f"TYPE: {result['analysis_type']}")
        if result["image_path"]:
            print(f"IMAGE: {result['image_path']}")
        print("-" * 40)
        print(result["prompt"])

        # Add copy-paste ready command if image path provided
        if result["image_path"]:
            print("\n" + "-" * 40)
            print("# Copy-paste ready (Claude Code native multimodal vision):")
            print(f'Read(file_path="{result["image_path"]}")')
            print("# Then analyze using the prompt context above")


def _output_json(results: list[dict[str, str]]) -> None:
    """Output prompts as JSON."""
    import json
    print(json.dumps(results, indent=2))


def _output_markdown(results: list[dict[str, str]]) -> None:
    """Output prompts as Markdown."""
    print("# AI Analysis Prompts\n")

    for result in results:
        print(f"## {result['screen'].upper()}\n")
        print(f"**Analysis Type:** {result['analysis_type']}\n")

        if result["image_path"]:
            print(f"**Image:** `{result['image_path']}`\n")

        print("### Prompt\n")
        print("```")
        print(result["prompt"])
        print("```\n")

        if result["image_path"]:
            print("### Usage\n")
            print("```python")
            print("# Claude Code native multimodal vision - just read the image:")
            print(f'Read(file_path="{result["image_path"]}")')
            print("# Then analyze using the prompt context above")
            print("```\n")
