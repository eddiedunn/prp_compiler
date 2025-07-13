import json
import asyncio
from pathlib import Path

import typer

from .agents.synthesizer import SynthesizerAgent
from .config import configure_gemini
from .knowledge import ChromaKnowledgeStore
from .cache import ResultCache
from .orchestrator import Orchestrator
from .primitives import PrimitiveLoader

app = typer.Typer()


@app.command()
def compile(
    goal: str = typer.Argument(..., help="The high-level goal for the PRP."),
    output_file: Path = typer.Option(
        ..., "--out", "-o", help="Path to save the generated PRP file."
    ),
    primitives_path: Path = typer.Option(
        "agent_primitives", help="Path to the agent_primitives directory."
    ),
    vector_db_path: Path = typer.Option(
        "chroma_db", help="Path to persist the vector database."
    ),
    constitution_path: Path = typer.Option(
        "CLAUDE.md", help="Path to the agent constitution file."
    ),
    cache_db_path: Path = typer.Option(
        "result_cache.sqlite", help="Path to the result cache database."
    ),
    strategy: str = typer.Option(
        None, help="Manually specify a strategy name to use."
    ),
    plan_file: Path | None = typer.Option(
        None,
        "--plan-out",
        help="Optional path to write the detailed plan/context buffer.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable real-time debug logging of the agent's loop.",
    ),
):
    """Compiles a high-fidelity PRP from a user goal."""
    try:
        typer.echo(f"🚀 Starting PRP compilation for goal: '{goal}'")
        configure_gemini()

        typer.echo("1. Loading primitives and knowledge store...")
        loader = PrimitiveLoader(primitives_path)
        knowledge_store = ChromaKnowledgeStore(persist_directory=vector_db_path)
        result_cache = ResultCache(cache_db_path)
        if not vector_db_path.exists():
            typer.secho(
                f"Warning: Knowledge store not found at {vector_db_path}. Building it now...",
                fg=typer.colors.YELLOW,
            )
            knowledge_primitives = loader.get_all("knowledge")
            knowledge_store.build(knowledge_primitives)
        else:
            knowledge_store.load()

        if constitution_path.exists():
            constitution = constitution_path.read_text()
        else:
            constitution = ""

        typer.echo("2. Running Planner Agent to gather context...")
        orchestrator = Orchestrator(loader, knowledge_store, result_cache, debug=debug)
        chosen_strategy = strategy
        schema_choice, final_context, history = orchestrator.run(
            goal,
            constitution,
            strategy_name=chosen_strategy,
        )

        if plan_file is not None:
            plan_file.parent.mkdir(parents=True, exist_ok=True)
            plan_file.write_text(json.dumps(history.get_structured_history(), indent=2))

        # Load the actual schema content based on the choice from the planner
        schema_content_str = loader.get_primitive_content("schemas", schema_choice)
        schema_json = json.loads(schema_content_str)

        typer.echo("3. Running Synthesizer Agent to generate final PRP...")
        synthesizer = SynthesizerAgent()
        final_prp_json = synthesizer.synthesize(
            schema_json, final_context, constitution
        )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(final_prp_json, f, indent=2)

        typer.secho(f"✅ Success! PRP saved to {output_file}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def build_knowledge(
    primitives_path: Path = typer.Option(
        "agent_primitives", help="Path to the agent_primitives directory."
    ),
    vector_db_path: Path = typer.Option(
        "chroma_db", help="Path to persist the vector database."
    ),
):
    """Builds or rebuilds the RAG vector store from knowledge primitives."""
    typer.echo(
        f"🔨 Building knowledge vector store from primitives in: {primitives_path}"
    )
    loader = PrimitiveLoader(primitives_path)
    knowledge_primitives = loader.get_all("knowledge")
    if not knowledge_primitives:
        typer.secho("No knowledge primitives found to build.", fg=typer.colors.YELLOW)
        return

    knowledge_store = ChromaKnowledgeStore(persist_directory=vector_db_path)
    knowledge_store.build(knowledge_primitives)
    typer.secho(
        f"✅ Knowledge vector store built at {vector_db_path}", fg=typer.colors.GREEN
    )


@app.command()
def serve(
    workers: int = typer.Option(4, help="Number of worker tasks."),
    primitives_path: Path = typer.Option("agent_primitives"),
    vector_db_path: Path = typer.Option("chroma_db"),
    constitution_path: Path = typer.Option("CLAUDE.md"),
    cache_db_path: Path = typer.Option("result_cache.sqlite"),
):
    """Runs the compiler as an async job queue service."""
    configure_gemini()
    loader = PrimitiveLoader(primitives_path)
    knowledge_store = ChromaKnowledgeStore(persist_directory=vector_db_path)
    if vector_db_path.exists():
        knowledge_store.load()
    else:
        knowledge_store.build(loader.get_all("knowledge"))
    result_cache = ResultCache(cache_db_path)

    async def worker(name: int, queue: asyncio.Queue[tuple[str, Path]]):
        while True:
            goal, out_path = await queue.get()
            typer.echo(f"Worker {name} starting: {goal}")
            orchestrator = Orchestrator(loader, knowledge_store, result_cache)
            schema_choice, final_context, _ = orchestrator.run(
                goal,
                constitution_path.read_text() if constitution_path.exists() else "",
            )
            schema_str = loader.get_primitive_content("schemas", schema_choice)
            synthesizer = SynthesizerAgent()
            prp = synthesizer.synthesize(
                json.loads(schema_str),
                final_context,
                constitution_path.read_text() if constitution_path.exists() else "",
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(prp, f, indent=2)
            typer.echo(f"Worker {name} finished: {out_path}")
            queue.task_done()

    async def main_async():
        queue: asyncio.Queue[tuple[str, Path]] = asyncio.Queue()
        tasks = [asyncio.create_task(worker(i + 1, queue)) for i in range(workers)]
        typer.echo("Server running. Enter a goal to enqueue or blank to exit.")
        while True:
            goal = await asyncio.to_thread(input, "Goal: ")
            if not goal:
                break
            output = Path(f"{goal.replace(' ', '_')}.json")
            await queue.put((goal, output))
        await queue.join()
        for t in tasks:
            t.cancel()

    asyncio.run(main_async())


def run():
    app()


if __name__ == "__main__":
    run()
