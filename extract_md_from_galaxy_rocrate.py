#!/usr/bin/env python3

from rocrate.rocrate import ROCrate
import json
import zipfile
from pathlib import Path
import sys

def extract_galaxy_workflow_info(rocrate_zip_path, output_format='console'):
    """
    Extract Galaxy workflow rerun information from RO-Crate ZIP using rocrate library.
    
    Args:
        rocrate_zip_path: Path to the RO-Crate ZIP file
        output_format: 'console' or 'markdown'
    """
    
    # Load RO-Crate
    crate = ROCrate(rocrate_zip_path)
    
    if output_format == 'markdown':
        output = []
        output.append("# Galaxy Workflow Rerun Information\n")
    else:
        print("=" * 60)
        print("GALAXY WORKFLOW RERUN INFORMATION")
        print("=" * 60)
    
    # Get workflow name from RO-Crate entities
    workflow_name = "Unknown"
    for entity in crate.get_entities():
        if hasattr(entity, 'type') and 'ComputationalWorkflow' in entity.type:
            if entity.id.endswith('.gxwf.yml'):
                workflow_name = entity.get('name', 'Unknown')
                break
    
    if output_format == 'markdown':
        output.append(f"**Workflow:** {workflow_name}\n")
    else:
        print(f"Workflow: {workflow_name}")
    
    # Get input/output definitions from RO-Crate
    formal_inputs = []
    formal_outputs = []
    
    main_workflow = None
    for entity in crate.get_entities():
        if hasattr(entity, 'type') and 'ComputationalWorkflow' in entity.type:
            if entity.id.endswith('.gxwf.yml'):
                main_workflow = entity
                break
    
    if main_workflow:
        # Get formal inputs
        inputs = main_workflow.get('input', [])
        if not isinstance(inputs, list):
            inputs = [inputs] if inputs else []
        
        for inp in inputs:
            param_id = getattr(inp, 'id', inp.get('@id') if hasattr(inp, 'get') else str(inp))
            formal_param = crate.get(param_id)
            if formal_param:
                formal_inputs.append({
                    'name': formal_param.get('name'),
                    'type': formal_param.get('additionalType'),
                    'description': formal_param.get('description', '')
                })
        
        # Get formal outputs
        outputs = main_workflow.get('output', [])
        if not isinstance(outputs, list):
            outputs = [outputs] if outputs else []
        
        for out in outputs:
            param_id = getattr(out, 'id', out.get('@id') if hasattr(out, 'get') else str(out))
            formal_param = crate.get(param_id)
            if formal_param:
                formal_outputs.append({
                    'name': formal_param.get('name'),
                    'type': formal_param.get('additionalType'),
                    'description': formal_param.get('description', '')
                })
    
    # Parse invocation file for actual execution parameters
    try:
        # Read invocation_attrs.txt from the ZIP
        with zipfile.ZipFile(rocrate_zip_path, 'r') as zip_file:
            with zip_file.open('invocation_attrs.txt') as f:
                invocation_data = json.load(f)[0]
        
        if output_format == 'markdown':
            output.append(f"**Execution Status:** {invocation_data.get('state')}\n")
            output.append(f"**Executed:** {invocation_data.get('create_time')}\n")
        else:
            print(f"Execution Status: {invocation_data.get('state')}")
            print(f"Executed: {invocation_data.get('create_time')}")
        
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
    
    except Exception as e:
        if output_format == 'markdown':
            output.append(f"**Error reading invocation data:** {e}\n")
        else:
            print(f"Error reading invocation data: {e}")
        actual_params = {}
        input_datasets = []
        output_datasets = []
    
    # Get actual file information from RO-Crate entities
    input_files = []
    output_files = []
    
    for entity in crate.get_entities():
        if hasattr(entity, 'type') and 'File' in entity.type:
            if 'datasets/' in entity.id and not entity.id.endswith('.txt'):
                file_info = {
                    'name': entity.get('name'),
                    'path': entity.id,
                    'format': entity.get('encodingFormat'),
                    'size': getattr(entity, 'contentSize', 'Unknown')
                }
                
                # Determine if input or output based on file extension/name
                if entity.id.endswith('.tabular') or entity.id.endswith('.csv'):
                    input_files.append(file_info)
                elif entity.id.endswith('.png') or entity.id.endswith('.jpg'):
                    output_files.append(file_info)
    
    # Print rerun information
    if output_format == 'markdown':
        output.append("\n## Workflow Inputs\n")
        
        output.append("### Formal Input Definitions\n")
        for inp in formal_inputs:
            output.append(f"- **{inp['name']}** ({inp['type']})")
            if inp['description']:
                output.append(f"  - Description: {inp['description']}")
            output.append("")
        
        output.append("### Actual Input Files Used\n")
        for inp_file in input_files:
            output.append(f"- **{inp_file['name']}**")
            output.append(f"  - Format: `{inp_file['format']}`")
            output.append(f"  - Path: `{inp_file['path']}`")
            output.append("")
        
        output.append("\n## Workflow Parameters\n")
        for param_name, param_value in actual_params.items():
            if isinstance(param_value, dict):
                output.append(f"- **{param_name}:**")
                for k, v in param_value.items():
                    output.append(f"  - {k}: `{v}`")
            else:
                output.append(f"- **{param_name}:** `{param_value}`")
            output.append("")
        
        output.append("\n## Workflow Outputs\n")
        
        output.append("### Formal Output Definitions\n")
        for out in formal_outputs:
            output.append(f"- **{out['name']}** ({out['type']})")
            if out['description']:
                output.append(f"  - Description: {out['description']}")
            output.append("")
        
        output.append("### Actual Output Files Generated\n")
        for out_file in output_files:
            output.append(f"- **{out_file['name']}**")
            output.append(f"  - Format: `{out_file['format']}`")
            output.append(f"  - Path: `{out_file['path']}`")
            output.append("")
        
        output.append("\n## Rerun Template\n")
        output.append(f"To rerun this workflow:\n")
        output.append(f"1. **Workflow:** {workflow_name}\n")
        
        output.append("2. **Required inputs:**")
        for inp in formal_inputs:
            output.append(f"   - {inp['name']} (type: `{inp['type']}`)")
        output.append("")
        
        output.append("3. **Parameters to set:**")
        for param_name, param_value in actual_params.items():
            if isinstance(param_value, dict):
                output.append(f"   - {param_name}:")
                for k, v in param_value.items():
                    output.append(f"     - {k}: `{v}`")
            else:
                output.append(f"   - {param_name}: `{param_value}`")
        output.append("")
        
        output.append("4. **Expected outputs:**")
        for out in formal_outputs:
            output.append(f"   - {out['name']} (type: `{out['type']}`)")
        output.append("")
        
        # Return markdown string
        markdown_content = "\n".join(output)
        return {
            'workflow_name': workflow_name,
            'formal_inputs': formal_inputs,
            'formal_outputs': formal_outputs,
            'actual_parameters': actual_params,
            'input_files': input_files,
            'output_files': output_files,
            'input_datasets': input_datasets,
            'output_datasets': output_datasets,
            'markdown': markdown_content
        }
    
    else:
        print("\n" + "=" * 60)
        print("WORKFLOW INPUTS")
        print("=" * 60)
        
        print("\nFormal Input Definitions:")
        for inp in formal_inputs:
            print(f"  • {inp['name']} ({inp['type']})")
            if inp['description']:
                print(f"    Description: {inp['description']}")
        
        print("\nActual Input Files Used:")
        for inp_file in input_files:
            print(f"  • {inp_file['name']}")
            print(f"    Format: {inp_file['format']}")
            print(f"    Path: {inp_file['path']}")
        
        print("\n" + "=" * 60)
        print("WORKFLOW PARAMETERS")
        print("=" * 60)
        
        for param_name, param_value in actual_params.items():
            print(f"  • {param_name}: {param_value}")
        
        print("\n" + "=" * 60)
        print("WORKFLOW OUTPUTS")
        print("=" * 60)
        
        print("\nFormal Output Definitions:")
        for out in formal_outputs:
            print(f"  • {out['name']} ({out['type']})")
            if out['description']:
                print(f"    Description: {out['description']}")
        
        print("\nActual Output Files Generated:")
        for out_file in output_files:
            print(f"  • {out_file['name']}")
            print(f"    Format: {out_file['format']}")
            print(f"    Path: {out_file['path']}")
        
        print("\n" + "=" * 60)
        print("RERUN TEMPLATE")
        print("=" * 60)
        
        print("\nTo rerun this workflow:")
        print(f"1. Workflow: {workflow_name}")
        print("\n2. Required inputs:")
        for inp in formal_inputs:
            print(f"   - {inp['name']} (type: {inp['type']})")
        
        print("\n3. Parameters to set:")
        for param_name, param_value in actual_params.items():
            print(f"   - {param_name}: {param_value}")
        
        print("\n4. Expected outputs:")
        for out in formal_outputs:
            print(f"   - {out['name']} (type: {out['type']})")
        
        # Return structured data for programmatic use
        return {
            'workflow_name': workflow_name,
            'formal_inputs': formal_inputs,
            'formal_outputs': formal_outputs,
            'actual_parameters': actual_params,
            'input_files': input_files,
            'output_files': output_files,
            'input_datasets': input_datasets,
            'output_datasets': output_datasets
        }

if __name__ == "__main__":
    # Use with your climate.rocrate.zip file
    if len(sys.argv) != 2:
        print("Usage: python extract_md_from_galaxy_rocrate.py <rocrate.zip>")
        print("Example: python extract_md_from_galaxy_rocrate.py climate.rocrate.zip")
        sys.exit(1)
    
    rocrate_path = sys.argv[1]
    
    try:
        # Generate console output
        print("Generating console output...")
        workflow_info = extract_galaxy_workflow_info(rocrate_path, output_format='console')
        
        # Generate markdown output
        print("\nGenerating markdown output...")
        workflow_info_md = extract_galaxy_workflow_info(rocrate_path, output_format='markdown')
        
        # Save markdown to file
        with open('workflow_rerun_info.md', 'w') as f:
            f.write(workflow_info_md['markdown'])
        
        print(f"\n✅ Markdown saved to: workflow_rerun_info.md")
        
        # Example of accessing the data programmatically
        print("\n" + "=" * 60)
        print("PROGRAMMATIC ACCESS EXAMPLE")
        print("=" * 60)
        
        print(f"\nWorkflow Name: {workflow_info['workflow_name']}")
        print(f"Number of inputs: {len(workflow_info['formal_inputs'])}")
        print(f"Number of parameters: {len(workflow_info['actual_parameters'])}")
        print(f"Number of outputs: {len(workflow_info['formal_outputs'])}")
        
        # Key parameters for rerun
        key_params = {k: v for k, v in workflow_info['actual_parameters'].items() 
                     if k in ['variable', 'title', 'adv']}
        print(f"\nKey parameters for rerun: {key_params}")
        
        # Option to print markdown to console too
        print(f"\n" + "=" * 60)
        print("MARKDOWN OUTPUT PREVIEW")
        print("=" * 60)
        print(workflow_info_md['markdown'][:500] + "..." if len(workflow_info_md['markdown']) > 500 else workflow_info_md['markdown'])
        
    except FileNotFoundError:
        print(f"Error: {rocrate_path} not found")
        print("Make sure climate.rocrate.zip is in the current directory")
    except Exception as e:
        print(f"Error: {e}")
