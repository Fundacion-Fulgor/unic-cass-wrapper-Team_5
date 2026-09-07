import pathlib
import re
import sys

DELAYED = re.compile(r"^(\s*)wire\s+((?:delayed_\w+\s*,\s*)*delayed_\w+)\s*;\s*$")


def patch(text):
    out = []
    for line in text.splitlines():
        out.append(line)
        m = DELAYED.match(line)
        if m:
            indent, names = m.group(1), m.group(2)
            for name in (n.strip() for n in names.split(",")):
                out.append(f"{indent}assign {name} = {name[len('delayed_'):]};")
    return "\n".join(out) + "\n"


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text()
    patched = patch(text)
    dst.write_text(patched)
    added = patched.count("assign delayed_")
    print(f"prepare_models: {src.name} -> {dst} ({added} delayed aliases)")


if __name__ == "__main__":
    main()
