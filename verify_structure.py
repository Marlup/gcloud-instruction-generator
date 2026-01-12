
from backend.actions.build_actions import load_global_config, build_service_configs, load_service_commands, iter_commands, map_group_to_resource, process_service, write_single_actions_file
from pathlib import Path
import json
import backend.actions.build_actions as build_actions

def mock_write(service_config, actions_index, dry_run=False):
    if service_config.name == 'iam':
        print(f"--- Verifying IAM Structure ---")
        # Check top level
        print(f"Top level keys: {list(actions_index.keys())}")
        
        # Check for 'list-grantable-roles' directly under 'iam' (mapped from empty)
        iam_res = actions_index.get('iam', {})
        print(f"KEYS under 'iam': {list(iam_res.keys())[:10]}")
        
        if 'list-grantable-roles' in iam_res:
             print("SUCCESS: list-grantable-roles found under 'iam'")
             action = iam_res['list-grantable-roles'].get('action')
             if action:
                 print(f"SUCCESS: list-grantable-roles has action: {action['cmd'][:50]}...")
             else:
                 print("FAILURE: list-grantable-roles missing action")
        else:
             print("FAILURE: list-grantable-roles NOT found under 'iam'")

        # Check nested delete
        oauth = actions_index.get('oauth-clients', {})
        creds = oauth.get('credentials', {})
        delete = creds.get('delete', {})
        
        if 'action' in delete:
            print("SUCCESS: oauth-clients.credentials.delete has action")
        else:
            print(f"FAILURE: oauth-clients.credentials.delete structure is: {delete.keys()}")

    if service_config.name == 'scheduler':
        print(f"--- Verifying Scheduler Structure ---")
        jobs = actions_index.get('jobs', {})
        create = jobs.get('create', {})
        
        # Scheduler create has sub-commands (app-engine, http, pubsub)
        # It DOES NOT have a main create command action itself (it's a group with subcommands)
        # Wait, if gcloud scheduler jobs create is a group, it won't have __action.
        
        print(f"Jobs Create keys: {list(create.keys())}")
        if 'app-engine' in create:
            ae = create['app-engine']
            if 'action' in ae:
                print("SUCCESS: jobs.create.app-engine has action")
            else:
                print("FAILURE: jobs.create.app-engine missing action")

build_actions.write_single_actions_file = mock_write

# Mock args
class Args:
    config = "backend/config/actions_config.json"
    services = "iam,scheduler"
    dry_run = True

build_actions.parse_args = lambda: Args()
build_actions.main()
