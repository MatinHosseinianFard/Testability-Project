import re


# Represents a gate in the circuit with properties and evaluation logic
class Gate:
    def __init__(self, address, name, gate_type, fanout, fanin, faults, delay=0):
        self.address = address  # Unique identifier for the gate
        self.name = name  # Human-readable name of the gate
        self.type = gate_type  # Type of gate (e.g., AND, OR, NOT, etc.)
        self.fanout = fanout  # Number of gates this gate feeds into
        self.fanin = fanin  # Number of gates feeding into this gate
        self.faults = faults  # List of faults (e.g., stuck-at faults)
        self.delay = delay  # Propagation delay through this gate
        self.inputs = []  # References to other Gate objects that are inputs
        self.output = "U"  # Initial output state ('U' = unknown)

    # Evaluate the gate's output based on its inputs and type
    def evaluate(self):
        # Skip evaluation for input gates; their output is set by input vectors
        if self.type == "inpt":
            return

        # Retrieve current output states of all input gates
        input_values = [gate.output for gate in self.inputs]

        # Determine if inputs include unknown ('U') or high-impedance ('Z') values
        has_U = "U" in input_values
        has_Z = "Z" in input_values
        # Filter to include only valid binary inputs ('0' or '1')
        clean_inputs = [val for val in input_values if val in {"0", "1"}]

        # Logic to evaluate the gate output based on its type
        if self.type == "nand":
            if "0" in clean_inputs:
                self.output = "1"  # NAND outputs 1 if any input is 0
            elif has_U:
                self.output = "U"  # Undefined if any input is unknown
            elif has_Z:
                self.output = "Z"  # High-impedance if any input is Z
            else:
                self.output = "0"  # All inputs are 1, so output is 0

        elif self.type == "and":
            if "0" in clean_inputs:
                self.output = "0"  # AND outputs 0 if any input is 0
            elif has_U or has_Z:
                self.output = "U"  # Undefined if any input is U or Z
            else:
                self.output = "1"  # All inputs are 1, so output is 1

        elif self.type == "or":
            if "1" in clean_inputs:
                self.output = "1"  # OR outputs 1 if any input is 1
            elif has_U or has_Z:
                self.output = "U"  # Undefined if any input is U or Z
            else:
                self.output = "0"  # All inputs are 0, so output is 0

        elif self.type == "nor":
            if "1" in clean_inputs:
                self.output = "0"  # NOR outputs 0 if any input is 1
            elif has_U or has_Z:
                self.output = "U"  # Undefined if any input is U or Z
            else:
                self.output = "1"  # All inputs are 0, so output is 1

        elif self.type == "xor":
            if has_U or has_Z:
                self.output = "U"  # XOR is undefined if any input is U or Z
            else:
                xor_sum = sum(int(inp) for inp in input_values) % 2
                self.output = str(xor_sum)  # XOR outputs sum modulo 2

        elif self.type == "xnor":
            if has_U or has_Z:
                self.output = "U"  # XNOR is undefined if any input is U or Z
            else:
                xor_sum = sum(int(inp) for inp in input_values) % 2
                self.output = "1" if xor_sum == 0 else "0"  # Negation of XOR

        elif self.type == "not":
            if not input_values:
                self.output = "U"  # Undefined if no inputs are available
            elif input_values[0] in {"U", "Z"}:
                self.output = "U"  # Undefined if input is U or Z
            else:
                self.output = "0" if input_values[0] == "1" else "1"  # Negation of input

        elif self.type == "buf":
            if not input_values:
                self.output = "U"  # Undefined if no inputs are available
            else:
                self.output = input_values[0]  # Buffer outputs the same as its input

        elif self.type == "fanout":
            if not input_values:
                self.output = "U"  # Undefined if no inputs are available
            else:
                self.output = input_values[0]  # Fan-out copies its input to multiple outputs

        else:
            self.output = "U"  # Unknown gate types default to 'U'

    def __repr__(self):
        # Represent the gate's details as a string for debugging
        input_repr = ", ".join([f"{gate.name}: {gate.output}" for gate in self.inputs])
        repr_str = (
            f"Gate {self.name} (Address: {self.address})\n"
            f"  Type     : {self.type}\n"
            f"  Fan-in   : {self.fanin}\n"
            f"  Fan-out  : {self.fanout}\n"
            f"  Delay    : {self.delay}\n"
            f"  Faults   : {', '.join(self.faults) if self.faults else 'None'}\n"
            f"  Inputs   : [{input_repr}]\n"
            f"  Output   : {self.output}\n"
        )
        return repr_str


# Represents a circuit consisting of multiple interconnected gates
class Circuit:
    def __init__(self, filename):
        self.gates = {}  # Dictionary of gates in the circuit, keyed by address
        self.load_iscas_file(filename)  # Load circuit definition from ISCAS file

    # Parse the ISCAS file to initialize the circuit
    def load_iscas_file(self, filename):
        with open(filename, "r") as file:
            current_gate = None
            fanout_counter = {}  # To uniquely name fan-out branches
            for line in file:
                # Skip comments or blank lines
                if line.startswith("*") or line.strip() == "":
                    continue

                # Match and parse gate definitions
                match = re.match(r"\s+(\d+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(.*)", line)
                if match:
                    address, name, gate_type, fanout, fanin, faults = match.groups()
                    faults = [fault.strip() for fault in faults.split() if fault.strip()]
                    # Create a gate object and add it to the dictionary
                    gate = Gate(int(address), name, gate_type, int(fanout), int(fanin), faults)
                    self.gates[int(address)] = gate
                    current_gate = gate
                    continue

                # Match and parse fan-out branch definitions
                match = re.match(r"\s+(\d+)\s+(\S+)\s+from\s+(\d+)\S*\s+(.*)", line)
                if match:
                    branch_address, branch_name, source_address, faults = match.groups()
                    faults = [fault.strip() for fault in faults.split() if fault.strip()]
                    base_name = self.gates[int(source_address)].name
                    fanout_counter[base_name] = fanout_counter.get(base_name, 0) + 1
                    branch_name = f"{base_name}_{fanout_counter[base_name]}"
                    # Create a fan-out branch gate and link it to its source gate
                    branch_gate = Gate(int(branch_address), branch_name, "fanout", fanout=1, fanin=1, faults=faults)
                    branch_gate.inputs = [self.gates[int(source_address)]]
                    self.gates[int(branch_address)] = branch_gate
                    continue

                # Parse input connections and delay for gates
                if current_gate and line.strip():
                    parts = list(map(int, line.split()))
                    if len(parts) == current_gate.fanin + 1:
                        delay = parts.pop()  # Last value is the delay
                    else:
                        delay = 0  # Default delay is 0
                    # Link inputs to other gates in the circuit
                    current_gate.inputs = [self.gates[input_addr] for input_addr in parts]
                    current_gate.delay = delay  # Assign delay to the gate

    # Read test vectors from a file
    def read_test_vectors(self, filename):
        test_vectors = []  # List to hold test vectors with time steps
        with open(filename, "r") as file:
            # First line specifies input gate IDs and time label
            header = file.readline().strip().split()
            input_gates = list(map(int, header[:-1]))  # Convert gate IDs to integers

            # Read each subsequent line as a test vector
            for line in file:
                if line.strip():
                    parts = line.strip().split()
                    inputs = {input_gates[i]: parts[i] for i in range(len(input_gates))}
                    time_step = int(parts[-1])  # Time step is the last value
                    test_vectors.append((time_step, inputs))
                    print(test_vectors)
        return test_vectors

    # Simulate the circuit for a series of test vectors
    def run_simulation_for_vectors(self, test_vectors, output_filename):
        """
        Run the simulation and save results for each test vector to an output file.
        """
        all_outputs = {}  # Dictionary to store outputs at each time step

        # Process each test vector sequentially
        for time_step, input_vector in test_vectors:
            # Initialize input gates with the values from the test vector
            for address, gate in self.gates.items():
                if gate.type == "inpt":
                    gate.output = input_vector.get(address, "U")  # Default to 'U' if not in vector

            # Propagate signals through the circuit
            for gate in self.gates.values():
                gate.evaluate()

            # Collect outputs for the current time step
            all_outputs[time_step] = {
                gate.address: (gate.output, gate) for gate in self.gates.values()
            }

        # Write outputs in a vertical format
        with open(output_filename, "w") as file:
            # Write the test vectors in a better table format
            file.write("Test Vectors Table:\n")

            # Extract input gates for the header
            input_gates = list(test_vectors[0][1].keys())
            time_col_width = 8  # Width for time column
            input_col_width = 7  # Width for each input column

            # Write the header for test vectors
            header = f"{'Time'.center(time_col_width)} | " + " | ".join(
                f"inpt{gate}".center(input_col_width) for gate in input_gates
            )
            file.write(header + "\n")
            file.write("=" * (len(header)) + "\n")  # Separator line

            # Write each test vector row
            for time_step, inputs in test_vectors:
                row = f"{str(time_step).center(time_col_width)} | " + " | ".join(
                    inputs[gate].center(input_col_width) for gate in input_gates
                )
                file.write(row + "\n")

            file.write("\n")  # Add a blank line before detailed outputs

            # Write the detailed outputs in table format
            file.write("\nOutputs Table:\n")

            # Sort gates by their address for consistent ordering
            sorted_gates = sorted(self.gates.values(), key=lambda g: g.address)

            # Define column widths for proper alignment
            address_col_width = 20  # Adjust width for Gate Address column
            time_col_width = 5      # Adjust width for each time step
            header = f"{'Gate Address (Type)':<{address_col_width}} | " + " | ".join(
                f"{f't={t}'.center(time_col_width)}" for t in all_outputs.keys()
            )
            file.write(header + "\n")
            file.write("-" * (len(header)) + "\n")  # Separator line

            # Write outputs for each gate across all time steps
            for gate in sorted_gates:
                # Gate details in the first column
                gate_info = f"{gate.address}({gate.type})".ljust(address_col_width)
                outputs = " | ".join(all_outputs[t][gate.address][0].center(time_col_width) for t in all_outputs)
                file.write(f"{gate_info} | {outputs}\n")


    # Optional: Display the circuit gates and their connections
    def display_circuit(self):
        for gate in self.gates.values():
            print(gate)


# Example Usage: Load and simulate multiple circuits
files_name = ["c5.isc", "c17.isc", "notTest.isc", "4InputsAnd.isc"]
for file_name in files_name:
    circuit = Circuit(file_name)  # Load circuit definition
    test_vectors = circuit.read_test_vectors(f"test_vectors_{file_name[:-4]}.txt")  # Load test vectors
    circuit.run_simulation_for_vectors(
        test_vectors, f"simulation_results_{file_name[:-4]}.txt"
    )  # Simulate and save results
