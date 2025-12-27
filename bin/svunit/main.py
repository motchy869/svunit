import argparse
import sys
import os
from pathlib import Path
from svunit.discovery import TestDiscovery
from svunit.codegen import SvUnitCodeGen
from svunit.simulators import get_simulator, detect_simulator
from svunit.creator import UnitTestCreator

def main():
    parser = argparse.ArgumentParser(description="SVUnit Python Implementation")
    
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Create sub-command
    create_parser = subparsers.add_parser("create", help="Create a new unit test")
    create_parser.add_argument("-uvm", action="store_true", help="Generate a UVM component test template")
    create_parser.add_argument("-out", dest="output_file", help="Specifies a new default output file")
    create_parser.add_argument("-overwrite", action="store_true", help="Overwrites the output file if it already exists")
    create_parser.add_argument("-class_name", help="Generate a unit test template for a class")
    create_parser.add_argument("-module_name", help="Generate a unit test template for a module")
    create_parser.add_argument("-if_name", help="Generate a unit test template for an interface")
    create_parser.add_argument("-p", dest="package", help="Package name")
    create_parser.add_argument("uut_file", nargs="?", help="The file with the unit under test")

    # Run sub-command (default behavior if no subcommand is provided, but argparse makes it tricky to mix)
    # To maintain backward compatibility with runSVUnit arguments at the top level, we need to add them to the main parser.
    # However, argparse doesn't easily support "if no subcommand, assume 'run'".
    # We can add arguments to the main parser and check if 'command' is None.

    # Arguments compatible with runSVUnit
    parser.add_argument("-s", "--sim", dest="simulator", help="Simulator to use")
    parser.add_argument("-l", "--log", dest="logfile", default="run.log", help="Simulation log file")
    parser.add_argument("-d", "--define", action="append", help="Macro definitions")
    parser.add_argument("-f", "--filelist", action="append", help="File lists")
    parser.add_argument("-U", "--uvm", action="store_true", help="Run with UVM")
    parser.add_argument("-r", "--r_arg", action="append", help="Runtime options")
    parser.add_argument("-c", "--c_arg", action="append", help="Compile options")
    parser.add_argument("-e", "--e_arg", action="append", help="Elaboration options")
    parser.add_argument("-o", "--out", dest="outdir", default=".", help="Output directory")
    parser.add_argument("-t", "--test", action="append", dest="tests", help="Specific tests to run")
    parser.add_argument("-m", "--mixedsim", dest="vhdlfile", help="VHDL file list")
    parser.add_argument("-w", "--wavedrom", action="store_true", help="Process Wavedrom output")
    parser.add_argument("--filter", help="Filter tests")
    parser.add_argument("--directory", action="append", help="Directories to search")
    parser.add_argument("--enable-experimental", action="store_true", help="Enable experimental features")
    parser.add_argument("--list-tests", action="store_true", help="List available tests")

    args = parser.parse_args()

    if args.command == "create":
        creator = UnitTestCreator(
            uut_file=args.uut_file,
            output_file=args.output_file,
            class_name=args.class_name,
            module_name=args.module_name,
            if_name=args.if_name,
            package=args.package,
            uvm=args.uvm,
            overwrite=args.overwrite
        )
        return creator.run()

    # Default behavior: Run SVUnit
    # Setup paths
    outdir = Path(args.outdir).resolve()
    if not outdir.exists():
        outdir.mkdir(parents=True)

    svunit_install = os.environ.get("SVUNIT_INSTALL")
    if not svunit_install:
        # Assuming this script is running from bin/svunit/main.py or similar structure
        # We want the root of the repo.
        # If run via bin/runSVUnit.py, sys.path[0] might be bin/
        # Let's rely on the location of this file: bin/svunit/main.py
        # root is ../../
        svunit_install = Path(__file__).resolve().parent.parent.parent
    else:
        svunit_install = Path(svunit_install)

    # Discovery Phase
    print("Scanning for tests...")
    discovery = TestDiscovery(directories=args.directory, tests=args.tests)
    found_tests = discovery.discover()
    
    if not found_tests:
        print("No tests found.")
        return 0

    print(f"Found {len(found_tests)} tests.")
    suites = discovery.get_test_suites()
    
    # Code Generation Phase
    codegen = SvUnitCodeGen()
    generated_test_suites = []
    
    # Initialize .svunit.f
    svunit_f_path = outdir / ".svunit.f"
    with open(svunit_f_path, 'w') as f:
        f.write(f"+incdir+{Path.cwd()}\n")
        f.write(f"+incdir+{svunit_install}/svunit_base/junit-xml\n")
        f.write(f"{svunit_install}/svunit_base/junit-xml/junit_xml.sv\n")
        f.write(f"+incdir+{svunit_install}/svunit_base\n")
        f.write(f"{svunit_install}/svunit_base/svunit_pkg.sv\n")
        
        if args.uvm:
             f.write(f"+incdir+{svunit_install}/svunit_base/uvm-mock\n")
             f.write(f"{svunit_install}/svunit_base/uvm-mock/svunit_uvm_mock_pkg.sv\n")

        if args.enable_experimental:
             f.write(f"+incdir+{svunit_install}/src/experimental/sv\n")
             f.write(f"{svunit_install}/src/experimental/sv/svunit.sv\n")

        # Generate Test Suites
        for suite_dir, tests in suites.items():
            # Create a unique name for the testsuite file based on directory
            # Perl script uses: $dirID =~ s/[\/\.-]/_/g; $dirID = "." . $dirID;
            # We need to be careful about relative paths.
            try:
                rel_dir = suite_dir.relative_to(Path.cwd())
                dir_id = str(rel_dir).replace('/', '_').replace('.', '_').replace('-', '_')
            except ValueError:
                # If suite_dir is not relative to cwd (e.g. absolute path outside), use full path
                dir_id = str(suite_dir).replace('/', '_').replace('.', '_').replace('-', '_')
                # Remove leading underscore if it comes from root /
                if dir_id.startswith('_'):
                    dir_id = dir_id[1:]

            ts_filename = f".{dir_id}_testsuite.sv"
            ts_path = outdir / ts_filename
            
            print(f"Generating {ts_path} for {suite_dir}")
            codegen.create_testsuite(ts_path, tests)
            generated_test_suites.append(ts_path)
            
            # Add tests to .svunit.f
            for test in tests:
                f.write(f"{test}\n")
            
            f.write(f"+incdir+{suite_dir}\n")
            f.write(f"{ts_path}\n")

        # Generate Test Runner
        tr_path = outdir / ".testrunner.sv" # Perl script generates testrunner.sv then moves to .testrunner.sv
        print(f"Generating {tr_path}")
        codegen.create_testrunner(tr_path, generated_test_suites)
        f.write(f"{tr_path}\n")

    # Simulation Phase
    simulator = None
    if args.simulator:
        simulator = get_simulator(args.simulator)
        if not simulator:
            print(f"Error: Unknown simulator '{args.simulator}'")
            return 1
    else:
        simulator = detect_simulator()
        if not simulator:
            print("Error: Could not detect any supported simulator.")
            return 1
    
    print(f"Using simulator: {simulator.name}")
    
    simulator.set_options(
        defines=args.define,
        filelists=args.filelist,
        sim_args=args.r_arg,
        compile_args=args.c_arg,
        elab_args=args.e_arg,
        uvm=args.uvm,
        vhdl_file=args.vhdlfile,
        logfile=args.logfile,
        outdir=str(outdir),
        filter=args.filter,
        list_tests=args.list_tests
    )
    
    if not simulator.run():
        print("Simulation failed.")
        return 1

    return 0
