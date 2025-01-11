import json
import multiprocessing
import pystache
import re
import sys
from ruamel.yaml import YAML

def replace_template_strings(text):
    pattern = r'\$\{\{\s*([^}]+)\s*\}\}'
    replacement = r'{{{ \1 }}}'
    return re.sub(pattern, replacement, text)

def str_representer(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml = YAML()
yaml.default_flow_style = False
yaml.representer.add_representer(str, str_representer)

vtk = sys.argv[1]
os_ind = 1
py_ind = {"sdks": 0, "sources":0, "ocp":0 }

with open(f".github/workflows/build-ocp-v2.yml", "r") as f:
    y = f.read()
d = yaml.load(y)

for job in ["sdks", "sources", "ocp"]:
    config = {"env": d["env"]}

    config["matrix"] = {
        "os": d["jobs"][job]["strategy"]["matrix"]["os"][os_ind],
        "python-version": d["jobs"][job]["strategy"]["matrix"]["python-version"][py_ind[job]],
        "use-vtk": vtk,
    }
    config["matrix"].update(d["jobs"][job]["strategy"]["matrix"]["include"][os_ind])
    config["steps"] = {"cpu-count": {"outputs": {"cpu_count": multiprocessing.cpu_count()}}}

    with open(f"/tmp/job-{job}.yml", "w") as f:
        yaml.dump({job: d["jobs"][job]}, f)

    with open(f"/tmp/job-{job}.yml", 'r') as f:
        result = f.read()
        yaml_job = replace_template_strings(result)

    result = pystache.render(yaml_job, config)
    
    with open(f"Build-{job}.yml", 'w') as f:
        f.write(result)    
