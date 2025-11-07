
import json
import os
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

def run_agent(agent, output_dir, timeout, codebase):
    name = agent['name']
    github = agent['github']
    branch = agent['branch']
    install_cmd = agent['install_command']
    run_cmd = f"{agent['run_command']} {codebase}"
    output_file = agent['output_file']

    # Directory for the agent
    agent_dir = os.path.join(output_dir, '..', 'agents', name)
    os.makedirs(agent_dir, exist_ok=True)

    abs_output_dir = os.path.abspath(output_dir)

    try:
        # Clone or pull the repo
        if os.path.exists(os.path.join(agent_dir, '.git')):
            subprocess.run(['git', 'pull', 'origin', branch], cwd=agent_dir, check=True, timeout=timeout)
        else:
            subprocess.run(['git', 'clone', '--branch', branch, github, agent_dir], check=True, timeout=timeout)

        # Change to agent directory
        original_cwd = os.getcwd()
        os.chdir(agent_dir)

        # Install dependencies
        subprocess.run(install_cmd, shell=True, check=True, timeout=timeout)

        # Run the analysis
        subprocess.run(run_cmd, shell=True, check=True, timeout=timeout)

        # Collect output
        if os.path.exists(output_file):
            shutil.copy(output_file, os.path.join(abs_output_dir, f"{name}_output.json"))
            print(f"Collected output from {name}")
        else:
            print(f"Output file {output_file} not found for {name}")

    except subprocess.TimeoutExpired:
        print(f"Timeout for agent {name}")
    except Exception as e:
        print(f"Error running agent {name}: {e}")
    finally:
        os.chdir(original_cwd)

def main():
    config = load_config('config.json')
    output_dir = config['output_dir']
    os.makedirs(output_dir, exist_ok=True)

    codebase = os.path.abspath(config.get('codebase', '.'))
    timeout = config['other_settings']['timeout']
    parallel = config['other_settings']['parallel']

    agents = config['agents']

    if parallel:
        with ThreadPoolExecutor(max_workers=len(agents)) as executor:
            futures = [executor.submit(run_agent, agent, output_dir, timeout, codebase) for agent in agents]
            for future in as_completed(futures):
                future.result()
    else:
        for agent in agents:
            run_agent(agent, output_dir, timeout, codebase)

    print("All agents processed.")

if __name__ == "__main__":
    main()
