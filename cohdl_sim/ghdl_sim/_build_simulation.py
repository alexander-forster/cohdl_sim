import os
import shutil
import subprocess
from pathlib import Path


def run_command(command, *args):
    cmd_string = f"{command} {' '.join(str(arg) for arg in args)}"

    result = subprocess.run([command, *args], stdout=subprocess.PIPE)

    if result.returncode != 0:
        print(result.stderr)
        print(result.stdout)
        raise AssertionError(f"command failed: {cmd_string}")

    return result.stdout.decode()


def prepare_ghdl_simulation(
    vhdl_sources: list[str], top_module: str, build_dir=Path, copy_files=False
) -> Path:
    status, _ = subprocess.getstatusoutput("ghdl-gcc --version")
    assert status == 0, "the ghdl_sim simulator requires the ghdl backend ghdl-gcc"

    vhdl_names = []

    for source_path in vhdl_sources:
        file_name = Path(source_path).name
        vhdl_names.append(file_name)

        if copy_files:
            target_path = build_dir / file_name
            shutil.copyfile(source_path, target_path)
        else:
            assert Path(source_path).parent == build_dir

    curdir = Path(os.curdir).absolute()

    try:
        os.chdir(build_dir)
        run_command("ghdl-gcc", "-a", *vhdl_names)
        run_command("ghdl-gcc", "--bind", top_module)
        list_link = run_command("ghdl-gcc", "--list-link", top_module).split()

        version_script_path = None
        filtered_list_link = []

        VERSION_SCRIPT_PREFIX = "-Wl,--version-script="

        for arg in list_link:
            if arg.startswith(VERSION_SCRIPT_PREFIX):
                version_script_path = Path(arg.removeprefix("-Wl,--version-script="))
            else:
                filtered_list_link.append(arg)

        # generate a modified version-script to make the symbol
        # `ghdl_main` globally visible
        local_version_script = "version-script.ver"

        with open(local_version_script, "w+") as local_file:
            with open(version_script_path) as original_file:
                for line in original_file:
                    print(line, file=local_file, end="")

                    if "global:" in line:
                        print("ghdl_main;", file=local_file)

        list_link = filtered_list_link + ["-Wl,--version-script=version-script.ver"]

        out_name = f"lib{top_module}.so"

        run_command("gcc", *list_link, "-Wl,-shared,-fPIC", f"-o{out_name}")

        return Path(out_name).absolute()
    finally:
        os.chdir(curdir)
