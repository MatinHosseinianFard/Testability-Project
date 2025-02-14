from collections import deque
import math

##############################################
# PODEM Algorithm Implementation
##############################################

class PODEM:
    def __init__(self, circuit):
        self.circuit = circuit  # Circuit under test
        self.fault_is_activated = False  # Tracks if the fault is activated
        self.D_Frontier = []  # Gates in the D frontier
        self.fault_gate = None  # Faulty gate
        self.fault_value = None  # Faulty value
    
    # Initialize gate outputs to unknown
    def podem_init(self):
        for g in self.circuit.gates.values():
            g.output = "X"
            
    # Reset PODEM algorithm state
    def podem_reset(self):
        self.__init__(self.circuit)
    
    # Generate the D frontier (gates with X output and D/D' input)
    def generate_d_frontier(self):
        self.D_Frontier = []
        for g in self.circuit.gates.values():
            if g.output == "X":
                if any(inp.output in ("D", "D'") for inp in g.inputs):
                    if self.x_path_check(g):
                        self.D_Frontier.append(g)
                    break

    # Check if there is an X-path from a gate to a primary output
    def x_path_check(self, gate):
        # Attempt to find a path to PO with U/D/D'
        visited = set()
        queue = deque([gate])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node in self.circuit.primary_outputs:
                return True
            # Propagate forward
            out_line_gate = node
            # Find gates that take out_line_gate as input
            for g in self.circuit.gates.values():
                if out_line_gate in g.inputs:
                    if g.output in ("X", "D", "D'"):
                        queue.append(g)
        return False

    # Check if a fault propagates to a primary output
    def success(self):
        # If any PO has D or D'
        for po in self.circuit.primary_outputs:
            if po.output in ("D", "D'"):
                return True
        return False

    # Get the opposite value of a binary value
    def oppositeVal(self, value):
        if value == "0":
            return "1"
        elif value == "1":
            return "0"
    
    # Determine the next objective gate and value
    def get_objective(self):
        if self.fault_gate.output in ("D", "D'"):
            self.fault_is_activated = True
            
        if not self.fault_is_activated:
            if self.fault_gate.output in ("1", "0"):
                return None, None
            return self.fault_gate, self.oppositeVal(self.fault_gate.fault_value)
        else:
            # Otherwise use D-frontier
            self.generate_d_frontier()
            if not self.D_Frontier:
                return (None, "X")

            # Find the gate with the smallest CO in the D frontier
            g = min(self.D_Frontier, key=lambda gate: gate.CO)

            for inp in g.inputs:
                if inp.output == "X":
                    return (inp, g.non_controlling_value)
            return (None, "X")
    
    # Find the easiest gate to satisfy based on CC0/CC1 values
    def get_easiest_to_satisfy_gate(self, objective_gate, objective_value):
        easiest_gate = None
        easiest_value = math.inf

        for gate in objective_gate.inputs:
            # Check if the gate is not set and the value is X
            if gate.output == "X":
                if objective_value == "0":
                    if gate.CC0 < easiest_value:
                        easiest_gate = gate
                        easiest_value = gate.CC0
                elif objective_value == "1":
                    if gate.CC1 < easiest_value:
                        easiest_gate = gate
                        easiest_value = gate.CC1

        return easiest_gate

    # Find the hardest gate to satisfy based on CC0/CC1 values
    def get_hardest_to_satisfy_gate(self, objective_gate, objective_value):
        hardest_gate = None
        hardest_value = -math.inf

        for gate in objective_gate.inputs:
            # Check if the gate is not set and the value is X
            if gate.output == "X":
                if objective_value == "0":
                    if gate.CC0 > hardest_value:
                        hardest_gate = gate
                        hardest_value = gate.CC0
                elif objective_value == "1":
                    if gate.CC1 > hardest_value:
                        hardest_gate = gate
                        hardest_value = gate.CC1

        return hardest_gate
    
    # Check if a gate's type satisfies a specific value
    def check_imply_gate(self, gate, value):
        if value == "1":
            if gate.type == "or" or gate.type == "nand":
                return False
            else:
                return True

        elif value == "0":
            if gate.type == "and" or gate.type == "nor":
                return False
            else:
                return True
    
    # Backtrace to find the primary input affecting the objective
    def backtrace(self, objective_gate, objective_value):
        target_pi = objective_gate
        target_pi_value = objective_value

        # Traverse backward from the objective gate
        while target_pi.type != "inpt":
            
            # TODO when adjective is the output of a xnor gate should be
            # 1 we must add cc0 a + cc0 b and cc1 a + cc1 b to see which one is easier....
            
            # If the target_pi has an inversion, flip the target_pi_value
            if target_pi.inversion:
                target_pi_value = self.oppositeVal(target_pi_value)

            if self.check_imply_gate(target_pi, target_pi_value):
                target_pi = self.get_hardest_to_satisfy_gate(objective_gate, objective_value)
            else:
                target_pi = self.get_easiest_to_satisfy_gate(objective_gate, objective_value)

            # Recursively call the function to traverse backward
            target_pi, target_pi_value = self.backtrace(target_pi, target_pi_value)

        return target_pi, target_pi_value

    # Propagate values through the circuit
    def imply(self):
        sorted_gates = sorted(self.circuit.gates.values(), key=lambda g: g.address)
        stable = False
        while not stable:
            stable = True
            old_outputs = [g.output for g in sorted_gates]
            for g in sorted_gates:
                g.d_algebra_evaluate()
            new_outputs = [g.output for g in sorted_gates]
            if new_outputs != old_outputs:
                stable = False

    # Recursive PODEM algorithm for fault detection
    def podem_recursive(self):
        # Check if the fault is successfully propagated to a primary output
        if self.success():
            return True

        # Determine the objective gate and its target value
        objective_gate, objective_value = self.get_objective()

        # If no objective can be determined, backtrack and return failure
        if objective_gate is None:
            return False

        # Backtrace from the objective gate to find the primary input affecting it
        target_pi, target_pi_value = self.backtrace(objective_gate, objective_value)
        target_pi.output = target_pi_value

        # Propagate the assigned value through the circuit
        self.imply()

        # Recursively attempt to propagate the fault with the current assignment
        if self.podem_recursive():
            return True  # Fault successfully propagated, return success

        # Backtracking: Try the opposite value for the primary input
        target_pi.output = self.oppositeVal(target_pi_value)
        self.imply()

        # Recursively attempt to propagate the fault with the new assignment
        if self.podem_recursive():
            return True

        # Backtracking: If both attempts fail, reset the primary input to unknown
        target_pi.output = "X"
        self.imply()

        # Return failure as the fault cannot be propagated with this path
        return False

    # Generate a test vector for a specific fault
    def generate_test_vector(self, fault):
        # Step 1: Initialize all gates in the circuit
        self.podem_init()
        
        # Step 2: Get the fault gate and set it as faulty with its stuck-at value
        fault_gate_address, stuck_value = fault
        self.fault_gate = self.circuit.gates.get(fault_gate_address, None)
        self.fault_gate.faulty = True
        self.fault_gate.fault_value = "1" if stuck_value == 1 else "0"
        
        # Step 3: Run the recursive PODEM algorithm to generate a test vector
        success = self.podem_recursive()
        
        # Step 4: Reset the fault gate to its original state
        self.fault_gate.faulty = False
        self.fault_gate.fault_value = None
        # Reset the circuit to its default state
        self.podem_reset()
        
        if success:
            test_vector=[]
            for g in self.circuit.primary_inputs:
                val = g.output
                if val=="D":
                    val="1"
                if val=="D'":
                    val="0"
                test_vector.append(val)
            return test_vector
        
        return None