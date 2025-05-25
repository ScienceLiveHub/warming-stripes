# Warming Stripes
Example to demonstrate executable nano publications:

- Nanopublication related to warming stripes 1950 - 2019, Freiburg (Germany): https://w3id.org/np/RAnqaMx3Ri3bR8yY3oiM-BeMJf8LPxidTSqyEpcHyXoLc

## Step 1: Get the workflow from an executable nanopublication

```
python galaxy_rocrate_finder.py https://w3id.org/np/RAnqaMx3Ri3bR8yY3oiM-BeMJf8LPxidTSqyEpcHyXoLc downloaded_rocrate
```

If the rocrate is found it is downloaded in `downloaded_rocrate`.

## Step 2: Prepare inputs and parameters 

```
python prepare_inputs_and_parameters.py downloaded_rocrate/d5430aa5-7a8b-44fe-8d21-6a7c80ac36d4.zip downloaded_workflows
```

## Step 3: Run workflow with prepared inputs and parameters

```
python bioblend_workflow.py
```
