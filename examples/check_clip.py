"""Print the local short-form video check for a clip."""
import argparse
import json

from python_agents.publish.video_validation import short_form_check


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="Path to the video file")
    args = parser.parse_args()
    print(json.dumps(short_form_check(args.video), indent=2))


if __name__ == "__main__":
    main()
