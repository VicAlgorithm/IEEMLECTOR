
import sys
import os

# Add the directory to path to import the module
sys.path.append(r"c:\Users\armas\OneDrive\Escritorio\LECTOR\FLUJO3_EXTRACCION")

from data_extractor import ToonExporter

class MockCell:
    def __init__(self, r, c, content):
        self.row_index = r
        self.column_index = c
        self.content = content

class MockTable:
    def __init__(self, rows, cols):
        self.cells = []
        self.column_count = cols

    def add_cell(self, r, c, content):
        self.cells.append(MockCell(r, c, content))

def run_test():
    exporter = ToonExporter()

    print("--- TEST 1: Table 1 Scenario (Key then description then Value) ---")
    t1 = MockTable(rows=10, cols=4)
    # Row 0: Key
    t1.add_cell(0, 0, "BOLETAS SOBRANTES")
    # Row 1: Instruction (ignored)
    t1.add_cell(1, 0, "Copie del apartado 2...")
    # Row 2: Value (should link to BOLETAS SOBRANTES)
    t1.add_cell(2, 3, "246")
    
    res1 = exporter.formatear_tabla_simple(t1)
    print(res1)
    print("-" * 20)

    print("--- TEST 2: Table 2 Scenario (Key : Value same row) ---")
    t2 = MockTable(rows=10, cols=4)
    t2.add_cell(0, 0, "PRI")
    t2.add_cell(0, 3, "54")
    t2.add_cell(1, 0, "PAN")
    t2.add_cell(1, 3, "23")
    
    res2 = exporter.formatear_tabla_simple(t2)
    print(res2)
    print("-" * 20)

    print("--- TEST 3: Table 3 Scenario (Complex Key then Value) ---")
    t3 = MockTable(rows=10, cols=4)
    # Row 0: Key
    # Row 0: Key - Clean
    t3.add_cell(0, 0, "TOTAL DE VOTOS SACADOS")
    # Row 1: Key - Garbage Instruction (Should be ignored)
    t3.add_cell(1, 0, "Copie del apartado 2 de la hoja de operaciones para verificar que todo esta correcto")
    # Row 2: Value (Should link to Row 0 Key)
    t3.add_cell(2, 3, "463")
    
    # Row 3: New Key
    t3.add_cell(3, 0, "COMPARATIVO")
    # Row 4: Value associated
    t3.add_cell(4, 3, "Si")
    
    res3 = exporter.formatear_tabla_simple(t3)
    print(res3)
    print("-" * 20)

if __name__ == "__main__":
    # Redirect stdout to a file
    with open("test_results.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        run_test()
        sys.stdout = sys.__stdout__
    print("Test run complete. Check test_results.txt")
