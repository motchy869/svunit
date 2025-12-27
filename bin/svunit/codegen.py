import re
from pathlib import Path
from typing import List

class SvUnitCodeGen:
    def __init__(self):
        pass

    def _parse_unit_test_name(self, file_path: Path) -> str:
        """
        Parses the unit test file to find the module name.
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Remove comments
        # Remove // comments
        content = re.sub(r'//.*', '', content)
        # Remove /* */ comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Remove static/automatic keywords (simple approach based on Perl script)
        content = re.sub(r'\bstatic\b', '', content)
        content = re.sub(r'\bautomatic\b', '', content)

        # Find module name
        match = re.search(r'^\s*module\s+(\w+_unit_test)\s*;', content, flags=re.MULTILINE)
        if match:
            return match.group(1)
        
        return None

    def create_testsuite(self, output_file: Path, unit_tests: List[Path]):
        """
        Generates the testsuite SystemVerilog file.
        """
        class_name = output_file.stem
        # Remove leading dots if any (Perl script does s/\.//g on the class name derived from filename)
        class_name = class_name.replace('.', '')
        
        instance_name = class_name.replace('_testsuite', '_ts')

        unit_test_classes = []
        unit_test_instances = []

        for ut in unit_tests:
            module_name = self._parse_unit_test_name(ut)
            if module_name:
                unit_test_classes.append(module_name)
                unit_test_instances.append(module_name.replace('_unit_test', '_ut'))
            else:
                print(f"Warning: Could not find module name in {ut}")

        with open(output_file, 'w') as f:
            f.write(f"module {class_name};\n")
            f.write("  import svunit_pkg::svunit_testsuite;\n\n")
            f.write(f"  string name = \"{instance_name}\";\n")
            f.write("  svunit_testsuite svunit_ts;\n")
            f.write("  \n")
            f.write("  \n")
            f.write("  //===================================\n")
            f.write("  // These are the unit tests that we\n")
            f.write("  // want included in this testsuite\n")
            f.write("  //===================================\n")
            
            for cls, inst in zip(unit_test_classes, unit_test_instances):
                f.write(f"  {cls} {inst}();\n")
            
            f.write("\n\n")
            f.write("  //===================================\n")
            f.write("  // Build\n")
            f.write("  //===================================\n")
            f.write("  function void build();\n")
            
            for inst in unit_test_instances:
                f.write(f"    {inst}.build();\n")
                f.write(f"    {inst}.__register_tests();\n")
            
            f.write(f"    svunit_ts = new(name);\n")
            
            for inst in unit_test_instances:
                f.write(f"    svunit_ts.add_testcase({inst}.svunit_ut);\n")
            
            f.write("  endfunction\n\n")
            
            f.write("\n")
            f.write("  //===================================\n")
            f.write("  // Run\n")
            f.write("  //===================================\n")
            f.write("  task run();\n")
            f.write("    svunit_ts.run();\n")
            
            for inst in unit_test_instances:
                f.write(f"    {inst}.run();\n")
            
            f.write("    svunit_ts.report();\n")
            f.write("  endtask\n\n")
            f.write("endmodule\n")

    def create_testrunner(self, output_file: Path, test_suites: List[Path]):
        """
        Generates the testrunner SystemVerilog file.
        """
        class_name = "testrunner"
        
        suite_classes = []
        suite_instances = []

        for ts in test_suites:
            # Perl script logic: $item =~ s/\.sv//g; $item =~ s/\.//;
            name = ts.name
            name = name.replace('.sv', '')
            name = name.replace('.', '')
            
            suite_classes.append(name)
            suite_instances.append(name.replace('_testsuite', '_ts'))

        with open(output_file, 'w') as f:
            f.write("\n")
            f.write(f"module {class_name}();\n")
            f.write("  import svunit_pkg::svunit_testrunner;\n")
            f.write("`ifdef RUN_SVUNIT_WITH_UVM\n")
            f.write("  import uvm_pkg::*;\n")
            f.write("  import svunit_uvm_mock_pkg::svunit_uvm_test_inst;\n")
            f.write("  import svunit_uvm_mock_pkg::uvm_report_mock;\n")
            f.write("`endif\n\n")
            f.write(f"  string name = \"{class_name}\";\n")
            f.write("  svunit_testrunner svunit_tr;\n\n\n")
            f.write("  //==================================\n")
            f.write("  // These are the test suites that we\n")
            f.write("  // want included in this testrunner\n")
            f.write("  //==================================\n")
            
            for cls, inst in zip(suite_classes, suite_instances):
                f.write(f"  {cls} {inst}();\n")
            
            f.write("\n\n")
            f.write("  //===================================\n")
            f.write("  // Main\n")
            f.write("  //===================================\n")
            f.write("  initial\n")
            f.write("  begin\n")
            f.write("\n")
            f.write("    `ifdef RUN_SVUNIT_WITH_UVM_REPORT_MOCK\n")
            f.write("      uvm_report_cb::add(null, uvm_report_mock::reports);\n")
            f.write("    `endif\n")
            f.write("\n")
            f.write("    build();\n")
            f.write("\n")
            f.write("    `ifdef RUN_SVUNIT_WITH_UVM\n")
            f.write("      svunit_uvm_test_inst(\"svunit_uvm_test\");\n")
            f.write("    `endif\n")
            f.write("\n")
            f.write("    run();\n")
            f.write("    $finish();\n")
            f.write("  end\n")
            
            f.write("\n\n")
            f.write("  //===================================\n")
            f.write("  // Build\n")
            f.write("  //===================================\n")
            f.write("  function void build();\n")
            f.write("    svunit_tr = new(name);\n")
            
            for inst in suite_instances:
                f.write(f"    {inst}.build();\n")
                f.write(f"    svunit_tr.add_testsuite({inst}.svunit_ts);\n")
            
            f.write("  endfunction\n\n\n")
            
            f.write("  //===================================\n")
            f.write("  // Run\n")
            f.write("  //===================================\n")
            f.write("  task run();\n")
            
            for inst in suite_instances:
                f.write(f"    {inst}.run();\n")
            
            f.write("    svunit_tr.report();\n")
            f.write("  endtask\n")
            f.write("\n\n")
            f.write("endmodule\n")
