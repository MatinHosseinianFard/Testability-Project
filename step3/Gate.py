class Gate:
    def __init__(self, address, name, gate_type, fanout, fanin, faults, delay=0):
        self.address = address  # Unique identifier
        self.name = name  # Gate name
        self.type = gate_type  # Type of the gate (e.g., AND, OR, NOT)
        self.fanout = fanout  # Number of output connections
        self.fanin = fanin  # Number of input connections
        self.faults = faults  # Faults associated with the gate
        self.faulty = False  # Fault status
        self.fault_value = None  # Fault value
        self.delay = delay  # Signal propagation delay
        self.inputs = []  # Input gate references
        self.output = "U"  # Initial output state ('U' = undefined)

        # SCOAP (CC0, CC1, CO) values for fault analysis
        self.CC0 = float('inf')
        self.CC1 = float('inf')
        self.CO = float('inf')

        # Gate-specific properties (e.g., inversion, controlling values)
        GATE_PROPERTIES = {
            "not": {"inversion": 1, "non_controlling_value": "1"},
            "nand": {"inversion": 1, "non_controlling_value": "1"},
            "nor": {"inversion": 1, "non_controlling_value": "0"},
            "xnor": {"inversion": 1, "non_controlling_value": "0"},
            "and": {"inversion": 0, "non_controlling_value": "1"},
            "or": {"inversion": 0, "non_controlling_value": "0"},
            "xor": {"inversion": 0, "non_controlling_value": "0"},
            "buf": {"inversion": 0, "non_controlling_value": "1"},
            "fanout": {"inversion": 0, "non_controlling_value": "1"}
        }
        props = GATE_PROPERTIES.get(gate_type, {"inversion": 0, "non_controlling_value": "X"})
        self.inversion = props["inversion"]
        self.non_controlling_value = props["non_controlling_value"]

    # Evaluate gate output using D-algebra logic
    def d_algebra_evaluate(self):
        input_values = [gate.output for gate in self.inputs]  # Get inputs' states
        has_X = "X" in input_values  # Check for unknown values
        has_U = "U" in input_values  # Check for undefined values
        has_Z = "Z" in input_values  # Check for high-impedance values

        # Evaluate based on gate type
        if self.type == "inpt":
            pass  # Input gate, no evaluation
        elif self.type == "and":
            self.output = self.evaluate_and(input_values, has_X, has_U, has_Z)
        elif self.type == "or":
            self.output = self.evaluate_or(input_values, has_X, has_U, has_Z)
        elif self.type == "xor":
            self.output = self.evaluate_xor(input_values, has_X, has_U, has_Z)
        elif self.type == "not":
            self.output = self.evaluate_not(input_values, has_X, has_U, has_Z)
        elif self.type == "buf":
            self.output = self.evaluate_buf(input_values, has_X, has_U, has_Z)
        elif self.type == "nand":
            self.output = self.evaluate_nand(input_values, has_X, has_U, has_Z)
        elif self.type == "nor":
            self.output = self.evaluate_nor(input_values, has_X, has_U, has_Z)
        elif self.type == "xnor":
            self.output = self.evaluate_xnor(input_values, has_X, has_U, has_Z)
        elif self.type == "fanout":
            self.output = self.evaluate_fanout(input_values, has_X, has_U, has_Z)
        else:
            self.output = "X"  # Unknown gate defaults to 'X'

        # Fault injection logic
        if self.faulty:
            if self.fault_value == "1" and self.output == "0":
                self.output = "D'"
            elif self.fault_value == "0" and self.output == "1":
                self.output = "D"

    # Gate-specific evaluation functions
    def evaluate_xnor(self, input_values, has_X, has_U, has_Z):
        output = self.evaluate_xor(input_values, has_X, has_U, has_Z)
        return self.evaluate_not([output], has_X, has_U, has_Z)

    def evaluate_nor(self, input_values, has_X, has_U, has_Z):
        output = self.evaluate_or(input_values, has_X, has_U, has_Z)
        return self.evaluate_not([output], has_X, has_U, has_Z)

    def evaluate_nand(self, input_values, has_X, has_U, has_Z):
        output = self.evaluate_and(input_values, has_X, has_U, has_Z)
        return self.evaluate_not([output], has_X, has_U, has_Z)

    def evaluate_buf(self, input_values, has_X, has_U, has_Z):
        return input_values[0]

    def evaluate_fanout(self, input_values, has_X, has_U, has_Z):
        return input_values[0]

    def evaluate_not(self, input_values, has_X, has_U, has_Z):
        input_val = input_values[0]
        if has_Z or has_U:
            return "U"
        elif input_val == "D":
            return "D'"
        elif input_val == "D'":
            return "D"
        elif input_val == "1":
            return "0"
        elif input_val == "0":
            return "1"
        else:
            return "X"

    def evaluate_xor(self, input_values, has_X, has_U, has_Z):
        if has_Z or has_U:
            return "U"
        elif has_X:
            return "X"

        d_count = input_values.count("D")
        d_prime_count = input_values.count("D'")
        one_count = input_values.count("1")
        if d_count == 0 and d_prime_count == 0:
            return "1" if one_count % 2 == 1 else "0"
        elif d_count % 2 == 1 and d_prime_count % 2 == 0:
            return "D'" if one_count % 2 == 1 else "D"
        elif d_count % 2 == 1 and d_prime_count % 2 == 1:
            return "0" if one_count % 2 == 1 else "1"
        elif d_count % 2 == 0 and d_prime_count % 2 == 1:
            return "D" if one_count % 2 == 1 else "D'"
        else:
            return "0"

    def evaluate_or(self, input_values, has_X, has_U, has_Z):
        if has_Z or has_U:
            return "U"
        elif "1" in input_values:
            return "1"
        elif has_X:
            return "X"
        elif "D" in input_values and "D'" in input_values:
            return "1"
        elif "D" in input_values and all(val in ["0", "D"] for val in input_values):
            return "D"
        elif "D'" in input_values and all(val in ["0", "D'"] for val in input_values):
            return "D'"
        elif all(val == "0" for val in input_values):
            return "0"

    def evaluate_and(self, input_values, has_X, has_U, has_Z):
        if has_Z or has_U:
            return "U"
        elif "0" in input_values:
            return "0"
        elif has_X:
            return "X"
        elif "D" in input_values and "D'" in input_values:
            return "0"
        elif "D" in input_values and all(val in ["1", "D"] for val in input_values):
            return "D"
        elif "D'" in input_values and all(val in ["1", "D'"] for val in input_values):
            return "D'"
        elif all(val == "1" for val in input_values):
            return "1"
                
    def __repr__(self):
        input_repr = ', '.join([f"{gate.name}: {gate.output}" for gate in self.inputs])
        repr_str = (
            f"Gate {self.name} (Address: {self.address})\n"
            f"  Name     : {self.name}\n"
            f"  Type     : {self.type}\n"
            f"  Fan-in   : {self.fanin}\n"
            f"  Fan-out  : {self.fanout}\n"
            f"  Delay    : {self.delay}\n"
            f"  Faults   : {', '.join(self.faults) if self.faults else 'None'}\n"
            f"  Inputs   : [{input_repr}]\n"
            f"  Output   : {self.output}\n"
            f"  CC0: {self.CC0}, CC1: {self.CC1}, CO: {self.CO}\n"
        )
        return repr_str