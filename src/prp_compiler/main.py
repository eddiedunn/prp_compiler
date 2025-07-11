import argparse
from pathlib import Path

from prp_compiler.config import (
    configure_gemini,
    DEFAULT_KNOWLEDGE_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_SCHEMAS_PATH,
    DEFAULT_TOOLS_PATH,
    PROJECT_ROOT,
)
from prp_compiler.manifests import (
    generate_manifest,
    save_manifests,
    load_manifests,
)
from prp_compiler.agents.planner import PlannerAgent
from prp_compiler.agents.synthesizer import SynthesizerAgent
from prp_compiler.orchestrator import Orchestrator, load_constitution
from prp_compiler.utils import count_tokens




def run():
    """
    Main function to run the PRP compiler from the command line.
    """
    configure_gemini()
    parser = argparse.ArgumentParser(description="PRP Compiler Agentic System")
    parser.add_argument(
        "--goal",
        type=str,
        required=True,
        help="The user's high-level goal for the PRP.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to save the generated PRP file.",
    )
    parser.add_argument(
        "--tools-path",
        type=Path,
        default=DEFAULT_TOOLS_PATH,
        help="Directory containing tool capabilities.",
    )
    parser.add_argument(
        "--knowledge-path",
        type=Path,
        default=DEFAULT_KNOWLEDGE_PATH,
        help="Directory containing knowledge files.",
    )
    parser.add_argument(
        "--schemas-path",
        type=Path,
        default=DEFAULT_SCHEMAS_PATH,
        help="Directory containing schema templates.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Directory to save the generated manifests.",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Force regeneration of all manifests.",
    )
    args = parser.parse_args()

    manifest_files_exist = all(
        (args.manifest_path / f).exists()
        for f in ["tools_manifest.json", "knowledge_manifest.json", "schemas_manifest.json"]
    )

    if args.force_refresh or not manifest_files_exist:
        print("1. Generating and saving manifests...")
        tools_manifest = generate_manifest(args.tools_path)
        knowledge_manifest = generate_manifest(args.knowledge_path)
        schemas_manifest = generate_manifest(args.schemas_path)
        save_manifests(
            tools_manifest, knowledge_manifest, schemas_manifest, args.manifest_path
        )
        print(f"   Manifests saved to {args.manifest_path}")
    else:
        print("1. Loading manifests from cache...")
        try:
            tools_manifest, knowledge_manifest, schemas_manifest = load_manifests(
                args.manifest_path
            )
            print(f"   Manifests loaded from {args.manifest_path}")
        except IOError as e:
            print(f"[ERROR] Failed to load manifests: {e}. Forcing refresh.")
            return run() # Recurse to regenerate

    print("2. Loading constitution...")
    constitution = load_constitution(PROJECT_ROOT)
    if constitution:
        print("   Constitution loaded from CLAUDE.md.")
    else:
        print("   No constitution (CLAUDE.md) found, proceeding without it.")

    print("3. Planning execution...")
    planner = PlannerAgent()
    execution_plan = planner.plan(
        args.goal, tools_manifest, knowledge_manifest, schemas_manifest, constitution
    )
    print("   Execution plan created.")

    print("4. Assembling context...")
    orchestrator = Orchestrator(tools_manifest, knowledge_manifest, schemas_manifest)
    schema_template, assembled_context = orchestrator.assemble_context(execution_plan)
    print("   Context assembled.")

    print("4.5. Counting tokens in assembled context...")
    token_count = count_tokens(assembled_context)

    print(f"   Assembled context contains approximately {token_count} tokens.")

    # Set a reasonable limit, e.g., 100k for Gemini 1.5 Pro
    TOKEN_LIMIT = 100000
    if token_count > TOKEN_LIMIT:
        print(f"[ERROR] Assembled context ({token_count} tokens) exceeds the limit of {TOKEN_LIMIT}. Please refine your goal or reduce the number of capabilities.")
        return # Exit gracefully

    print("5. Synthesizing PRP...")
    synthesizer = SynthesizerAgent()
    final_prp = synthesizer.synthesize(schema_template, assembled_context, constitution)
    print("   PRP synthesized.")

    print(f"6. Saving PRP to {args.output}...")
    with open(args.output, "w") as f:
        f.write(final_prp)
    print("Done.")


if __name__ == "__main__":
    run()
