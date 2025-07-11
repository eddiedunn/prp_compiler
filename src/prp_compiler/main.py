import argparse
from pathlib import Path

from prp_compiler.manifests import generate_manifest, save_manifest
from prp_compiler.agents.planner import PlannerAgent
from prp_compiler.agents.synthesizer import SynthesizerAgent
from prp_compiler.orchestrator import Orchestrator

# Define default paths. These assume a 'agent_capabilities' directory
# in the current working directory where the command is run.
DEFAULT_TOOLS_PATH = Path("./agent_capabilities/tools")
DEFAULT_KNOWLEDGE_PATH = Path("./agent_capabilities/knowledge")
DEFAULT_SCHEMAS_PATH = Path("./agent_capabilities/schemas")
DEFAULT_MANIFEST_PATH = Path("./component_manifest.json")

def run():
    """
    Main function to run the PRP compiler from the command line.
    """
    parser = argparse.ArgumentParser(description="PRP Compiler Agentic System")
    parser.add_argument("--goal", type=str, required=True, help="The user's high-level goal for the PRP.")
    parser.add_argument("--output", type=Path, required=True, help="Path to save the generated PRP file.")
    parser.add_argument("--tools-path", type=Path, default=DEFAULT_TOOLS_PATH, help="Directory containing tool capabilities.")
    parser.add_argument("--knowledge-path", type=Path, default=DEFAULT_KNOWLEDGE_PATH, help="Directory containing knowledge files.")
    parser.add_argument("--schemas-path", type=Path, default=DEFAULT_SCHEMAS_PATH, help="Directory containing schema templates.")
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH, help="Path to save the generated manifest.")
    args = parser.parse_args()

    print("1. Generating manifests...")
    tools_manifest = generate_manifest(args.tools_path)
    knowledge_manifest = generate_manifest(args.knowledge_path)
    schemas_manifest = generate_manifest(args.schemas_path)
    save_manifest(tools_manifest, knowledge_manifest, schemas_manifest, args.manifest_path)
    print(f"   Manifests saved to {args.manifest_path}")

    print("2. Planning execution...")
    planner = PlannerAgent()
    execution_plan = planner.plan(args.goal, tools_manifest, knowledge_manifest, schemas_manifest)
    print("   Execution plan created.")

    print("3. Assembling context...")
    orchestrator = Orchestrator(tools_manifest, knowledge_manifest, schemas_manifest)
    schema_template, assembled_context = orchestrator.assemble_context(execution_plan)
    print("   Context assembled.")

    print("4. Synthesizing PRP...")
    synthesizer = SynthesizerAgent()
    final_prp = synthesizer.synthesize(schema_template, assembled_context)
    print("   PRP synthesized.")

    print(f"5. Saving PRP to {args.output}...")
    with open(args.output, "w") as f:
        f.write(final_prp)
    print("Done.")

if __name__ == "__main__":
    run()
