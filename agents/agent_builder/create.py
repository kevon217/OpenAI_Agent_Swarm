import os
import json
from shared.openai_config import get_openai_client
from agents.tool_maker.tool_updater import normalize_tool

agents_path = "agents/agent_builder/agents"
client = get_openai_client()

# Check if the 'agents' folder is empty or doesn't exist
if (
    not os.path.exists(agents_path)
    or not os.path.isdir(agents_path)
    or not os.listdir(agents_path)
):
    raise ValueError('The "agents" folder is missing, not a directory, or empty.')

existing_assistants = {}

for assistant in client.beta.assistants.list(limit=100):
    existing_assistants[assistant.name] = assistant


# Iterate over each folder inside the 'agents' folder
for agent_name in os.listdir(agents_path):
    agent_folder = os.path.join(agents_path, agent_name)

    existing_files = {}
    requested_files = []
    existing_agent = {}
    if agent_name in existing_assistants:
        existing_agent = existing_assistants[agent_name]
        for file_id in existing_agent.file_ids:
            existing_file = client.files.retrieve(file_id=file_id)
            existing_files[existing_file.filename] = existing_file

    if os.path.isdir(agent_folder):
        # Read contents from the 'instructions.md' file
        instructions = ""
        instructions_file_path = os.path.join(agent_folder, "instructions.md")
        if os.path.isfile(instructions_file_path):
            with open(instructions_file_path, "r") as f:
                instructions = f.read()

        # Read contents from the 'settings.json' file
        settings = {}
        settings_file_path = os.path.join(agent_folder, "settings.json")
        if os.path.isfile(settings_file_path):
            with open(settings_file_path, "r") as f:
                settings = json.load(f)

        # Check for the 'files' subfolder and process its contents
        files = []
        files_folder = os.path.join(agent_folder, "files")
        if os.path.isdir(files_folder):
            for filename in os.listdir(files_folder):
                requested_files.append(filename)
                # Doesn't handle if file has been modified
                if filename not in existing_files:
                    file_path = os.path.join(files_folder, filename)
                    with open(file_path, "rb") as file_data:
                        # Upload each file to OpenAI
                        file_object = client.files.create(
                            file=file_data, purpose="assistants"
                        )
                        files.append({"name": filename, "id": file_object.id})
                # Extract requested tools from settings
        requested_tools = settings.get("tools", [])
        normalized_requested_tools = [normalize_tool(t) for t in requested_tools]

        print(agent_name)
        print("")
        print(instructions)
        print(requested_tools)
        if files:
            print("")
            print(f"Files: {list(map(lambda x: x['name'], files))}")

        assistant = {}

        if existing_agent:
            print(f"{agent_name} already exists... validating properties")
            update_model = existing_agent.model != settings["model"]
            update_instructions = existing_agent.instructions != instructions

            # Check if tools need to be updated
            existing_tools_set = {tool.type for tool in existing_agent.tools}
            normalized_existing_tools = [
                normalize_tool(t) for t in existing_agent.tools
            ]

            # Compare tools
            update_tools = normalized_existing_tools != normalized_requested_tools

            if update_tools:
                update_params["tools"] = requested_tools
                print(f"Updating {agent_name}'s tools")

            update_params = {}

            requested_files_set = set(requested_files)
            existing_files_set = set(existing_files.keys())

            if update_model:
                update_params["model"] = settings["model"]
            if update_instructions:
                update_params["instructions"] = instructions
            if files or requested_files_set != existing_files_set:
                retained_set = existing_files_set.intersection(requested_files_set)
                all_file_ids = []
                for key in retained_set:
                    all_file_ids.append(existing_files[key].id)
                all_file_ids += list(map(lambda x: x["id"], files))
                update_params["file_ids"] = all_file_ids
                if not any(tool.type == "retrieval" for tool in existing_agent.tools):
                    update_params["tools"] = existing_agent.tools
                    update_params["tools"].append({"type": "retrieval"})
            if update_tools:
                update_params["tools"] = requested_tools

            if len(update_params) != 0:
                print(f"Updating {agent_name}'s { ','.join(update_params.keys()) }")
                update_params["assistant_id"] = existing_agent.id
                assistant = client.beta.assistants.update(**update_params)
            else:
                print(f"{agent_name} is up to date")
        else:
            create_params = {
                "name": agent_name,
                "instructions": instructions,
                "model": settings["model"],
                "tools": settings["tools"],
            }

            # Only include 'file_ids' if there are files
            if files:
                create_params["tools"].append({"type": "retrieval"})
                create_params["file_ids"] = list(map(lambda x: x["id"], files))

            # Create the assistant using the uploaded file IDs if files exist
            assistant = client.beta.assistants.create(**create_params)
        print("***********************************************")
