import json
import sys

from app.services.transcription import transcribe_audio


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python test_transcription.py uploads/test.wav", file=sys.stderr)
        return 2

    file_path = sys.argv[1]
    result = transcribe_audio(file_path)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

