from Circuit import Circuit
from Podem import PODEM

# Usage example
if __name__ == "__main__":
    fault_file = "test.txt"
    test_vector_file = "b_2.txt"
    circuit_file = "b_1_2.isc"

    circuit = Circuit(circuit_file)
    circuit.compute_scoap(filename="c17/SCOAP.txt")

    podem = PODEM(circuit)

    with open(fault_file, "r") as f, open(test_vector_file, "w") as out:
        # Write the header line with aligned columns
        header = "{:<10} {:<10} {}".format("net", "fault", " ".join(str(circuit.primary_inputs[i].address) for i in range(len(circuit.primary_inputs))))
        out.write(header + "\n\n")
        
        # Process faults and write results with proper formatting
        faults = [line.strip().split() for line in f.readlines()]
        for fault in faults:
            gate, fault_type = fault[0], fault[1]
            stuck_value = 1 if fault_type == "sa1" else 0
            test_vector = podem.generate_test_vector((gate, stuck_value))
            if test_vector:
                formatted_line = "{:<10} {:<10} {}".format(gate, fault_type, " ".join(test_vector))
            else:
                formatted_line = "{:<10} {:<10} none found".format(gate, fault_type)
            out.write(formatted_line + "\n")
