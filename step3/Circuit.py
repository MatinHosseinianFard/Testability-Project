import re
from Gate import Gate

class Circuit:
    def __init__(self, filename):
        self.gates = {}  # Dictionary to store Gate objects by their address
        self.primary_inputs = []
        self.primary_outputs = []
        self.load_iscas_file(filename)
        self.identify_primary_ios()

    def load_iscas_file(self, filename):
        with open(filename, 'r') as file:
            current_gate = None
            fanout_counter = {}
            for line in file:
                # Ignore comments and blank lines
                if line.startswith('*') or line.strip() == '':
                    continue

                # Match lines defining a gate
                match = re.match(r'\s+(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(.*)', line)
                if match:
                    address, name, gate_type, fanout, fanin, faults = match.groups()
                    faults = [fault.strip() for fault in faults.split() if fault.strip()]
                    gate = Gate(int(address), name[:-3], gate_type, int(fanout), int(fanin), faults)
                    self.gates[int(address)] = gate
                    current_gate = gate
                    continue

                # Match fanout branch
                match = re.match(r'\s+(\d+)\s+(\S+)\s+from\s+(\d+)\S*\s+(.*)', line)
                if match:
                    branch_address, branch_name, source_address, faults = match.groups()
                    faults = [fault.strip() for fault in faults.split() if fault.strip()]
                    base_name = self.gates[int(source_address)].name
                    fanout_counter[base_name] = fanout_counter.get(base_name, 0) + 1
                    branch_name = f"{base_name}_{fanout_counter[base_name]}"
                    branch_gate = Gate(int(branch_address), branch_name, 'fanout', fanout=1, fanin=1, faults=faults)
                    branch_gate.inputs = [self.gates[int(source_address)]]
                    self.gates[int(branch_address)] = branch_gate
                    continue
                # print(self.gates)
                # Gate inputs and delay
                if current_gate and line.strip():
                    # print(line.strip())
                    parts = list(map(int, line.split()))
                    if len(parts) == int(current_gate.fanin) + 1:
                        delay = parts.pop()
                    else:
                        delay = 0
                    current_gate.inputs = [self.gates[input_addr] for input_addr in parts]
                    current_gate.delay = delay
        
        # change keys to gates name reason: for correct branch key             
        self.gates = {value.name: value for key, value in self.gates.items()}
    
    def identify_primary_ios(self):
        # Primary inputs: gates of type 'inpt'
        # Primary outputs: gates with fanout=0
        for g in self.gates.values():
            if g.type == 'inpt':
                self.primary_inputs.append(g)
            if g.fanout == 0:
                self.primary_outputs.append(g)

    def compute_scoap(self, filename):
        # Initialize input lines and gates
        for gate in self.gates.values():
            if gate.type == 'inpt':
                gate.CC0 = 1  # Inputs are easiest to control
                gate.CC1 = 1
        # Forward pass: Compute CC0 and CC1
        for gate in self.gates.values():
            # if gate.type == 'fanout':
            if gate.type == 'and':
                gate.CC0 = min(inp.CC0 for inp in gate.inputs) + 1
                gate.CC1 = sum(inp.CC1 for inp in gate.inputs) + 1
            elif gate.type == 'or':
                gate.CC0 = sum(inp.CC0 for inp in gate.inputs) + 1
                gate.CC1 = min(inp.CC1 for inp in gate.inputs) + 1
            elif gate.type == 'nand':
                gate.CC0 = sum(inp.CC1 for inp in gate.inputs) + 1
                gate.CC1 = min(inp.CC0 for inp in gate.inputs) + 1
            elif gate.type == 'nor':
                gate.CC0 = min(inp.CC1 for inp in gate.inputs) + 1
                gate.CC1 = sum(inp.CC0 for inp in gate.inputs) + 1
            elif gate.type == 'xor':
                gate.CC0 = min(gate.inputs[0].CC0 + gate.inputs[1].CC0, gate.inputs[0].CC1 + gate.inputs[1].CC1) + 1
                gate.CC1 = min(gate.inputs[0].CC1 + gate.inputs[1].CC0, gate.inputs[0].CC0 + gate.inputs[1].CC1) + 1
            elif gate.type == 'xnor':
                gate.CC0 = min(gate.inputs[0].CC1 + gate.inputs[1].CC0, gate.inputs[0].CC0 + gate.inputs[1].CC1) + 1
                gate.CC1 = min(gate.inputs[0].CC0 + gate.inputs[1].CC0, gate.inputs[0].CC1 + gate.inputs[1].CC1) + 1
            elif gate.type == 'not':
                gate.CC0 = gate.inputs[0].CC1 + 1
                gate.CC1 = gate.inputs[0].CC0 + 1
            elif gate.type == 'buf':
                gate.CC0 = gate.inputs[0].CC0
                gate.CC1 = gate.inputs[0].CC1
            elif gate.type == 'fanout':
                gate.CC0 = gate.inputs[0].CC0
                gate.CC1 = gate.inputs[0].CC1
            # print(gate)

        # # Backward pass: Compute CO
        for gate in reversed(list(self.gates.values())):
            if gate.fanout == 0:  # Outputs
                gate.CO = 0
            
            if gate.type == 'fanout':
                is_primary_output = True
                for other_gate in self.gates.values():
                    if gate in other_gate.inputs:
                        is_primary_output = False
                        break
                if is_primary_output:
                    gate.CO = 0
                else:
                    if gate.inputs[0].CO > gate.CO:
                        gate.inputs[0].CO = gate.CO
                continue

            if gate.type == 'and':
                gate.inputs[0].CO = gate.CO + gate.inputs[1].CC1 + 1
                gate.inputs[1].CO = gate.CO + gate.inputs[0].CC1 + 1
            elif gate.type == 'or':
                gate.inputs[0].CO = gate.CO + gate.inputs[1].CC0 + 1
                gate.inputs[1].CO = gate.CO + gate.inputs[0].CC0 + 1
            elif gate.type == 'nand':
                gate.inputs[0].CO = gate.CO + gate.inputs[1].CC1 + 1
                gate.inputs[1].CO = gate.CO + gate.inputs[0].CC1 + 1
            elif gate.type == 'nor':
                gate.inputs[0].CO = gate.CO + gate.inputs[1].CC0 + 1
                gate.inputs[1].CO = gate.CO + gate.inputs[0].CC0 + 1
            elif gate.type == 'xor':
                for i in range(len(gate.inputs)):
                    other_inputs = [gate.inputs[j] for j in range(len(gate.inputs)) if j != i]
                    min_other_cc = min(inp.CC0 for inp in other_inputs) + min(inp.CC1 for inp in other_inputs)
                    gate.inputs[i].CO = gate.CO + min_other_cc + 1
            elif gate.type == 'xnor':
                for i in range(len(gate.inputs)):
                    other_inputs = [gate.inputs[j] for j in range(len(gate.inputs)) if j != i]
                    min_other_cc = min(inp.CC0 for inp in other_inputs) + min(inp.CC1 for inp in other_inputs)
                    gate.inputs[i].CO = gate.CO + min_other_cc + 1

            elif gate.type == 'not':
                gate.inputs[0].CO = gate.CO + 1
            elif gate.type == 'buf':
                gate.inputs[0].CO = gate.CO + 1
            elif gate.type == 'inpt':
                continue
            
        self.save_scoap_to_file(filename)
        
    def save_scoap_to_file(self, filename):
        with open(filename, 'w') as file:
            file.write("SCOAP Results for All Lines:\n")
            for gate in self.gates.values():
                file.write(f"{gate.name}: ({gate.CC0},{gate.CC1}) {gate.CO}\n")