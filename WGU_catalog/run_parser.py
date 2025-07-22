# run_parser.py
from parse_catalog import parse_catalog

def main():
    try:
        result = parse_catalog()
        print("Parsing completed successfully")
        print("Generated files:")
        for filepath in result.get("outputs", []):
            print(f"  - {filepath}")
    except Exception as e:
        print(f"Error during parsing: {e}")
        raise

if __name__ == "__main__":
    main()