"""Falha se a cobertura de branches (coverage.xml) ficar abaixo do mínimo."""
import sys
import xml.etree.ElementTree as ET

minimo = float(sys.argv[1]) if len(sys.argv) > 1 else 80
root = ET.parse("coverage.xml").getroot()
atual = float(root.attrib["branch-rate"]) * 100
print(f"Cobertura de branches: {atual:.1f}% (mínimo {minimo}%)")
sys.exit(0 if atual >= minimo else 1)
