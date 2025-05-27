#!/usr/bin/env python3

from rocrate.rocrate import ROCrate
import json
import zipfile
from pathlib import Path
import sys
import os
import ast
import yaml
import shutil

# importing the zipfile module
from zipfile import ZipFile

def find_files_os_walk(directory, type_of_file):
    """
    Find type_of_file files using os.walk()
    
    Args:
        directory (str): Root directory to search
        type_of_file (str): prefix to look for (e.g. ".ga")
    
    Returns:
        list: List of full paths to type_of_file files
    """
    find_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(type_of_file):
                full_path = os.path.join(root, file)
                find_files.append(full_path)
    
    return find_files

def get_datasets_info(filename, inputs_encoded_ids, outputs_encoded_ids):
    # Parse datasets file for actual input files
    inputs_names = []
    outputs_names = []
    try:
        with open(filename) as f:
            datasets = json.load(f)
            for dataset in datasets:
                for encoded_id in inputs_encoded_ids:
                    if dataset["encoded_id"] == encoded_id["dataset_id"]:
                        inputs_names.append(dataset["file_name"])
                for encoded_id in outputs_encoded_ids:
                    if dataset["encoded_id"] == encoded_id["dataset_id"]:
                        outputs_names.append(dataset["file_name"])
            return inputs_names, outputs_names
    except Exception as e:
        print(f"Error reading dataset data: {e}")
                    
def get_invocation_info(filename):
    # Parse invocation file for actual execution parameters
    try:
        with open(filename) as f:
            invocation_data = json.load(f)[0]
                
        print(f"Execution Status: {invocation_data.get('state')}")
        print(f"Executed: {invocation_data.get('create_time')}")

        workflow_parameters = []
        # Extract workflow input parameters
        for input_parameter in invocation_data.get('input_parameters', []): 
            if "WorkflowRequestInputParameter" in input_parameter.values():
                if input_parameter["value"] != "false":
                  workflow_parameters.append( ast.literal_eval(input_parameter["value"]))

        # Extract actual parameters used
        actual_params = {}
        for step_state in invocation_data.get('step_states', []):
            step_value = step_state.get('value', {})
            step_index = step_state.get('order_index')
            
            for param_name, param_value in step_value.items(): 
                if not param_name.startswith('__') and param_name not in ['chromInfo', 'dbkey']:
                    # Clean parameter values
                    if isinstance(param_value, str) and param_value.startswith('"') and param_value.endswith('"'):
                        param_value = param_value[1:-1]
                    elif isinstance(param_value, str) and param_value.startswith('{'):
                        try:
                            param_value = json.loads(param_value)
                        except:
                            pass 

                    actual_params[param_name] = param_value

        # Get input/output dataset info
        input_datasets = []
        for inp_ds in invocation_data.get('input_datasets', []):
            dataset_id = inp_ds.get('dataset', {}).get('encoded_id')
            input_datasets.append({
                'dataset_id': dataset_id,
                'order': inp_ds.get('order_index', 0)
            })

        output_datasets = []
        for out_ds in invocation_data.get('output_datasets', []):
            dataset_id = out_ds.get('dataset', {}).get('encoded_id')
            label = out_ds.get('workflow_output', {}).get('label')
            output_datasets.append({
                'dataset_id': dataset_id,
                'label': label,
                'order': out_ds.get('order_index', 0)
            })

        #print(actual_params)
        #print(input_datasets)
        #print(output_datasets)
        return input_datasets, actual_params, workflow_parameters, output_datasets
    except Exception as e:
        print(f"Error reading invocation data: {e}")
        actual_params = {}
        input_datasets = []
        output_datasets = []
        workflow_parameters = []

def prepare_jobfile(ifilenames, ofilenames, workflow, jobfile, odir, 
                              rjob_filename, rworkflow_filename):
    try:
        print(workflow)
        shutil.copy(workflow, rworkflow_filename)
        print(f"Workflow copied successfully in {rworkflow_filename}")
        
        # Set input filenames
        ifilenames_with_odir = []
        for ifilename in ifilenames:
            ifilenames_with_odir.append(odir + "/" + ifilename)
        
        # Set output filenames
        ofilenames_with_odir = []
        for ofilename in ofilenames:
            ofilenames_with_odir.append(odir + "/" + ofilename)

        # Read jobfile (yml)
        with open(jobfile, 'r') as f:
            data_jobfile = yaml.load(f, Loader=yaml.SafeLoader)[0] # Assume one element in the returned list

            job_section = data_jobfile.get('job', {})
            output_section = data_jobfile.get('outputs', {})
            print("Reading job section")
            for key, value in job_section.items():
                if isinstance(value, dict) and 'path' in value:
                    # You could add extra checks here, e.g., value['class'] == 'File'
                    print(f"Updating path under key: {key} and value: {value}")
                    if value["class"] == "File":
                        value["path"] = ifilenames_with_odir.pop(0)
                else:
                    print("Parameter: ", key)

            for key, value in output_section.items():
                if isinstance(value, dict) and 'path' in value:
                    print(f"Updating path under key: {key} and value: {value}")
                    value["path"] = ofilenames_with_odir.pop(0)
            
            with open(rjob_filename, 'w') as f:
                yaml.dump(job_section, f, sort_keys=False)
            
    except Exception as e:
        print(f"Error writing job file: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python prepare_inputs_and_parameters.py <rocrate.zip> <output_dir>")
        print("Example: python prepare_inputs_and_parameters.py downloaded_rocrate/d5430aa5-7a8b-44fe-8d21-6a7c80ac36d4.zip downloaded_workflows")
        sys.exit(1)
    
    rocrate_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    try:
        workflows = []
        invocations = []
        datasets = []
        jobfiles = []
        # unloading the *.zip and creating a zip object
        with ZipFile(rocrate_path, 'r') as zObject:
        # Extracting all the members of the zip 
        # into a specific location.
            zObject.extractall(output_dir)
        
            workflows = find_files_os_walk(output_dir, ".ga")
            invocations = find_files_os_walk(output_dir, "invocation_attrs.txt")
            datasets = find_files_os_walk(output_dir, "datasets_attrs.txt")
            jobparams = find_files_os_walk(output_dir, "jobs_attrs.txt")
            jobfiles = find_files_os_walk(output_dir, ".yml")

        print("Extracting information from invocation attribute file")
        # we assume one single invocation file. If more, we process the first one only.
        input_datasets, actual_params, workflow_params, output_datasets = get_invocation_info(invocations[0])

        print("Extracting information from dataset attribute file")
        # We assume one single datasets_attrs.txt file
        input_filenames, output_filenames = get_datasets_info(datasets[0], input_datasets, output_datasets)

        print("Extracting information from job attribute file")    
        # We assume one single jobfile.      
        prepare_jobfile(input_filenames, output_filenames, workflows[0], jobfiles[0], output_dir, 
                              "workflow_input_params.yml", "workflow.ga")
        
    except FileNotFoundError:
        print(f"Error: {rocrate_path} not found")
        print("Make sure climate.rocrate.zip is in the current directory")
    except Exception as e:
        print(f"Error: {e}")
