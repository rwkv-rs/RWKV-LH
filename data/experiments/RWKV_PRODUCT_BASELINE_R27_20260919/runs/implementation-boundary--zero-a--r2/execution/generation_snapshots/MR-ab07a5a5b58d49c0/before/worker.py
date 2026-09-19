import argparse
import json

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dir", required=True)
    args = p.parse_args()
    print(json.dumps({"ready": True, "mode": "preview"}))

if __name__ == "__main__":
    main()
