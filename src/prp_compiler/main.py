import typer
from pathlib import Path
import json
from .config import configure_gemini
from .primitives import PrimitiveLoader
from .knowledge import KnowledgeStore
from .orchestrator import Orchestrator
from .agents.synthesizer import SynthesizerAgent

app = typer.Typer()

@app.command()
def compile(
    goal: str = typer.Argument(..., help="The high-level goal for the PRP."),
    output_file: Path = typer.Option(..., "--out", "-o", help="Path to save the generated PRP file."),
    primitives_path: Path = typer.Option("agent_primitives", help="Path to the agent_primitives directory."),
    vector_db_path: Path = typer.Option("chroma_db", help="Path to persist the vector database."),
):
    """Compiles a high-fidelity PRP from a user goal."""
    typer.echo(f"🚀 Starting PRP compilation for goal: '{goal}'")
    try:
        configure_gemini()
        # Phase 1: Load primitives and knowledge
        typer.echo("1. Loading primitives and knowledge store...")
        loader = PrimitiveLoader(primitives_path)
        knowledge_store = KnowledgeStore(persist_directory=vector_db_path)
        # Check if DB exists, otherwise build it
        if not vector_db_path.exists():
            typer.echo("   Knowledge store not found. Building from primitives...")
            knowledge_primitives = loader.get_all("knowledge")
            knowledge_store.build(knowledge_primitives)
        else:
            knowledge_store.load()
        # Phase 2: Run the Planner's ReAct loop
        typer.echo("2. Running Planner Agent to gather context...")
        orchestrator = Orchestrator(loader, knowledge_store)
        schema_template_json, final_context = orchestrator.run(goal)
        # Phase 3: Run the Synthesizer
        typer.echo("3. Running Synthesizer Agent to generate final PRP...")
        synthesizer = SynthesizerAgent()
        # Load agent constitution
        constitution_path = Path("CLAUDE.md")
        constitution = constitution_path.read_text() if constitution_path.exists() else ""
        # If schema_template_json is a string, parse as JSON
        import json
        if isinstance(schema_template_json, str):
            schema_template = json.loads(schema_template_json)
        else:
            schema_template = schema_template_json
        final_prp_json = synthesizer.synthesize(schema_template, final_context, constitution)
        # Save the output
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(final_prp_json, f, indent=2)
        typer.secho(f"✅ Success! PRP saved to {output_file}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"❌ Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def build_knowledge(
    primitives_path: Path = typer.Option("agent_primitives", help="Path to the agent_primitives directory."),
    vector_db_path: Path = typer.Option("chroma_db", help="Path to persist the vector database."),
):
    """Builds or rebuilds the RAG vector store from knowledge primitives."""
    typer.echo(f"🔨 Building knowledge vector store from primitives in: {primitives_path}")
    loader = PrimitiveLoader(primitives_path)
    knowledge_primitives = loader.get_all("knowledge")
    knowledge_store = KnowledgeStore(persist_directory=vector_db_path)
    knowledge_store.build(knowledge_primitives)
    typer.secho(f"✅ Knowledge vector store built at {vector_db_path}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
