# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Warming stripes with Galaxy and Bioblend

# %%
import os
import time
from urllib.parse import urljoin
import os
from collections import defaultdict

import bioblend.galaxy
import tempfile
import pooch
import json


# %%
def upload_to_history(inputs, gi, hist_hid):
    ret_uploads = []
    for input_filename in inputs:
        ret = gi.tools.upload_file(input_filename, hist_id)
        ret_uploads.append(ret)
    return ret_uploads


# %% [markdown]
# ## Input parameters

# %%
server = "https://usegalaxy.eu/"
api_key = os.environ.get("GALAXY_API_KEY")
workflow_parameters_filename = "workflow_input_params.json"

# %% [markdown]
# ## Read Workflow parameters from workflow_invocation.json

# %%
with open(workflow_parameters_filename, 'r', encoding='utf-8') as file:
            workflow_parameters = json.load(file)
print(workflow_parameters)

# %% [markdown]
# ## Connect to a Galaxy instance (here Galaxy Europe)

# %%
# Optional: Check if API key was found
if not api_key:
    raise ValueError("GALAXY_API_KEY environment variable not set")

print(f"API Key loaded: {'Yes' if api_key else 'No'}")

gi = bioblend.galaxy.GalaxyInstance(url=server, key=api_key)

# %% [markdown]
# ## Create a new history

# %%
new_hist = gi.histories.create_history(name='ScienceLive')
print(new_hist)

# %% [markdown]
# ## Import workflow to Galaxy Europe

# %%
wf = gi.workflows.import_workflow_from_local_path(workflow_parameters["workflow"])

# %%
wf_id = wf["id"]
print(wf_id)

# %% [markdown]
# ## Upload data in the history

# %%
hist_id = new_hist["id"]
hist_id

# %%
ret_uploads = upload_to_history(workflow_parameters["inputs"], gi, hist_id)

# %% [markdown]
# # Get outputs

# %%
step = 0
inputs = {}
for ret in ret_uploads:
    hda = ret['outputs'][0]
#    inputs = {idx: {'id': hda['id'], 'src': 'hda'}}
    inputs.update({str(step): {'id': hda['id'], 'src': 'hda'}})
print(inputs) # will not work when several inputs!

# %%
step = 1
params = {
    str(step): workflow_parameters["params"][0]
}

print(params)

# %%
ret = gi.workflows.invoke_workflow(wf_id, inputs=inputs, params=params, history_id=hist_id)

# %%
while True:
    history = gi.histories.show_history(hist_id, contents=True)
    states = [dataset['state'] for dataset in history]
    if all(state in ['ok', 'error'] for state in states):
        print("✅ Workflow has completed.")
        break
    else:
        print("⏳ Waiting for workflow to complete...")
        time.sleep(10)

# %% [markdown]
# ## Get RO-Crate

# %%
response = gi.invocations.get_invocation_archive(
        invocation_id = ret["id"],
        model_store_format= "rocrate.zip")

# %%
file = "climate.rocrate.zip"

with open(file, "bw") as archive:
    for chunk in response.iter_content(chunk_size=8192):
        archive.write(chunk)
        # Verify file is not empty

# %% [markdown]
# # Delete history

# %%
gi.histories.delete_history(hist_id, purge=True)

# %%

# %%

# %%
