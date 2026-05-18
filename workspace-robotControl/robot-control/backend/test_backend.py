"""
Einfacher Test
"""
from app.core.commands import parse_command
from app.core.controller import controller


print(" Teste Backend...")
print()

# Test 1: Command Parser
print("1. Command Parser")
cmd = parse_command("forward 2.0")
print(f"   'forward 2.0' -> {cmd}")

cmd = parse_command("stop")
print(f"   'stop' -> {cmd}")
print()

# Test 2: Controller
print("2. Controller")
controller.execute_command("forward 2.0")
controller.execute_command("left 1.5")
controller.execute_command("stop")
print()

print(" Test fertig!")
