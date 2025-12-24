import myson
import json

def benchmark_tokens():
    data = [{"id": i, "name": f"Item {i}", "active": True} for i in range(1000)]
    
    json_str = json.dumps(data)
    zen_str = myson.dumps(data, zen=True)
    
    print(f"JSON size: {len(json_str)} bytes")
    print(f"Zen Grid size: {len(zen_str)} bytes")
    print(f"Reduction: {(1 - len(zen_str)/len(json_str))*100:.2f}%")

if __name__ == "__main__":
    benchmark_tokens()
