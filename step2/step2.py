import re
import heapq


# Represents an individual gate in the circuit
class Gate:
    def __init__(self, address, name, gate_type, fanout, fanin, faults, delay=0):
        self.address = address  # Unique numerical identifier for the gate
        self.name = name  # Name of the gate
        self.type = gate_type  # Type of gate (e.g., AND, OR, NOT, etc.)
        self.fanout = fanout  # Number of gates this gate feeds into
        self.fanin = fanin  # Number of gates feeding into this gate
        self.faults = faults  # List of faults associated with this gate
        self.delay = delay  # Time delay for signal propagation through this gate
        self.inputs = []  # References to input Gate objects
        self.output = 'U'  # Initial output state ('U' represents an undefined state)
        self.scheduled_events = []  # Priority queue for scheduled output changes
        self.last_input_event_time = 0  # Time of the last input event for this gate

    # Evaluate the output of the gate based on its inputs and type
    def evaluate(self, current_time):
        # Skip evaluation for input gates as their output is directly assigned
        if self.type == 'inpt':
            return

        # Retrieve the current output states of the input gates
        input_values = [gate.output for gate in self.inputs]

        # Determine if inputs contain undefined ('U') or high-impedance ('Z') values
        has_U = 'U' in input_values
        has_Z = 'Z' in input_values
        # Filter to include only valid binary values ('0', '1')
        clean_inputs = [val for val in input_values if val in {'0', '1'}]

        # Logic for evaluating gate output based on gate type
        if self.type == 'nand':
            if '0' in clean_inputs:
                pending_output = '1'
            elif has_U:
                pending_output = 'U'
            elif has_Z:
                pending_output = 'Z'
            else:
                pending_output = '0'

        elif self.type == 'and':
            if '0' in clean_inputs:
                pending_output = '0'
            elif 'U' in input_values:
                pending_output = 'U'
            elif 'Z' in input_values:
                pending_output = 'Z'
            else:
                pending_output = '1'

        elif self.type == 'or':
            if '1' in clean_inputs:
                pending_output = '1'
            elif 'U' in input_values:
                pending_output = 'U'
            elif 'Z' in input_values:
                pending_output = 'Z'
            else:
                pending_output = '0'

        elif self.type == 'nor':
            if '1' in clean_inputs:
                pending_output = '0'
            elif 'U' in input_values:
                pending_output = 'U'
            elif 'Z' in input_values:
                pending_output = 'Z'
            else:
                pending_output = '1'

        elif self.type == 'xor':
            if has_U or has_Z:
                pending_output = 'U'
            else:
                # XOR logic: sum of binary inputs modulo 2
                xor_sum = sum(int(inp) for inp in input_values) % 2
                pending_output = str(xor_sum)

        elif self.type == 'xnor':
            if has_U or has_Z:
                pending_output = 'U'
            else:
                # XNOR logic: output is the negation of XOR
                xor_sum = sum(int(inp) for inp in input_values) % 2
                pending_output = '1' if xor_sum == 0 else '0'

        elif self.type == 'not':
            if not input_values:
                pending_output = 'U'
            elif input_values[0] == 'U':
                pending_output = 'U'
            elif input_values[0] == 'Z':
                pending_output = 'U'
            else:
                pending_output = '0' if input_values[0] == '1' else '1'

        elif self.type == 'buf':
            if not input_values:
                pending_output = 'U'
            elif input_values[0] in {'U', 'Z'}:
                pending_output = input_values[0]
            else:
                pending_output = input_values[0]

        elif self.type == 'fanout':
            if not input_values:
                pending_output = 'U'
            else:
                pending_output = input_values[0]

        else:
            # Default case: undefined output
            pending_output = 'U'

        # Calculate the time at which the output change will take effect
        event_time = current_time + self.delay

        # Remove any previously scheduled events for the same time
        self.scheduled_events = [(et, po) for et, po in self.scheduled_events if et != event_time]
        heapq.heapify(self.scheduled_events)

        # Schedule the new output event
        heapq.heappush(self.scheduled_events, (event_time, pending_output))

        # Update the time of the last input event
        self.last_input_event_time = current_time

    # Update the gate's output based on scheduled events
    def update_output(self, current_time):
        while self.scheduled_events and self.scheduled_events[0][0] <= current_time:
            event_time, output_value = heapq.heappop(self.scheduled_events)
            self.output = output_value

    def __repr__(self):
        # Represent the gate's current state as a string
        input_repr = ', '.join([f"{gate.name}: {gate.output}" for gate in self.inputs])
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


# Represents the entire circuit consisting of interconnected gates
class Circuit:
    def __init__(self, filename):
        self.gates = {}  # Dictionary to store Gate objects by their address
        self.load_iscas_file(filename)  # Load circuit description from ISCAS file

    # Parse an ISCAS file to create the circuit
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
                    # Create a Gate object and add it to the circuit
                    gate = Gate(int(address), name, gate_type, int(fanout), int(fanin), faults)
                    self.gates[int(address)] = gate
                    current_gate = gate
                    continue

                # Match lines defining a fanout branch
                match = re.match(r'\s+(\d+)\s+(\S+)\s+from\s+(\d+)\S*\s+(.*)', line)
                if match:
                    branch_address, branch_name, source_address, faults = match.groups()
                    faults = [fault.strip() for fault in faults.split() if fault.strip()]
                    base_name = self.gates[int(source_address)].name
                    fanout_counter[base_name] = fanout_counter.get(base_name, 0) + 1
                    branch_name = f"{base_name}_{fanout_counter[base_name]}"
                    # Create a fanout branch gate
                    branch_gate = Gate(int(branch_address), branch_name, 'fanout', fanout=1, fanin=1, faults=faults)
                    branch_gate.inputs = [self.gates[int(source_address)]]
                    self.gates[int(branch_address)] = branch_gate
                    continue

                # Match lines defining gate inputs and delay
                if current_gate and line.strip():
                    parts = list(map(int, line.split()))
                    if len(parts) == int(current_gate.fanin) + 1:
                        delay = parts.pop()
                    else:
                        delay = 0
                    current_gate.inputs = [self.gates[input_addr] for input_addr in parts]
                    current_gate.delay = delay

    # Read test vectors from a file
    def read_test_vectors(self, filename):
        test_vectors = []
        with open(filename, 'r') as file:
            header = file.readline().strip().split()  # Read the first line as header
            input_gates = list(map(int, header[:-1]))  # Map header to input gate addresses
            for line in file:
                if line.strip():
                    parts = line.strip().split()
                    # Parse input values and time step
                    inputs = {input_gates[i]: parts[i] for i in range(len(input_gates))}
                    time_step = int(parts[-1])
                    test_vectors.append((time_step, inputs))
        return test_vectors

    # Simulate the circuit with a set of test vectors
    def run_simulation_for_vectors(self, test_vectors, output_filename):
        timing_queue = []  # Priority queue for handling timing events
        current_test_index = 0  # Index of the current test vector
        all_outputs = {}
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

            current_time = 0  # Initialize simulation time
            last_logged_time = -1  # Last time step logged to the file
            # Continue simulation until all test vectors and events are processed
            while current_test_index < len(test_vectors) or timing_queue:
                # Determine the next event or test vector time
                next_test_time = test_vectors[current_test_index][0] if current_test_index < len(
                    test_vectors) else float('inf')
                next_queue_time = timing_queue[0][0] if timing_queue else float('inf')
                current_time = min(next_test_time, next_queue_time)

                # Process new test vector at the current time
                if current_test_index < len(test_vectors) and current_time == next_test_time:
                    _, input_vector = test_vectors[current_test_index]
                    for address, gate in self.gates.items():
                        # Update input gate outputs based on the test vector
                        if gate.type == 'inpt' and address in input_vector:
                            if gate.output != input_vector[address]:
                                gate.output = input_vector[address]
                                # gate.update_output(current_time)
                                for fanout_gate in self.gates.values():
                                    if gate in fanout_gate.inputs:
                                        fanout_gate.evaluate(current_time)
                                        heapq.heappush(timing_queue, (
                                            current_time + fanout_gate.delay, fanout_gate.address, fanout_gate))
                    current_test_index += 1

                # Process scheduled events at the current time
                while timing_queue and timing_queue[0][0] == current_time:
                    _, _, gate = heapq.heappop(timing_queue)
                    gate.update_output(current_time)
                    for fanout_gate in self.gates.values():
                        if gate in fanout_gate.inputs:
                            fanout_gate.evaluate(current_time)
                            heapq.heappush(timing_queue,
                                           (current_time + fanout_gate.delay, fanout_gate.address, fanout_gate))

                # Log results for the current time
                if current_time != last_logged_time:
                    if last_logged_time != -1 and current_time > last_logged_time + 1:
                        for t in range(last_logged_time + 1, current_time):
                            all_outputs[t] = all_outputs[t-1]
                    # Collect outputs for the current time step
                    
                    all_outputs[current_time] = {
                        gate.address: (gate.output, gate) for gate in self.gates.values()
                    }
                    
                    last_logged_time = current_time

                # Advance to the next test vector or break if no events remain
                if not timing_queue and current_test_index < len(test_vectors):
                    current_time = test_vectors[current_test_index][0]
                elif not timing_queue:
                    break

            self.save_timed_results(file, all_outputs)
            
    # Save the results of the simulation for a given time step
    def save_timed_results(self, file, all_outputs):
        
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
            gate_info = f"{gate.address}({gate.type}){f'({gate.delay})' if gate.delay!=0 else ''}".ljust(address_col_width)
            outputs = " | ".join(all_outputs[t][gate.address][0].center(time_col_width) for t in all_outputs)
            file.write(f"{gate_info} | {outputs}\n")


# Example Usage
# files_name = ["c5.isc", "c17.isc", "notTest.isc", "4InputsAnd.isc"]
files_name = ["c5.isc", "c17.isc", "notTest.isc", "4InputsAnd.isc"]
for file_name in files_name:
    # Load the circuit and run simulation for each file
    circuit = Circuit(file_name)
    test_vectors = circuit.read_test_vectors(f"test_vectors_{file_name[:-4]}.txt")
    circuit.run_simulation_for_vectors(test_vectors, f"timed_simulation_results_{file_name[:-4]}.txt")
