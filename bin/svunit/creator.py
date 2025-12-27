import argparse
import re
import sys
from pathlib import Path
from typing import Optional

class UnitTestCreator:
    def __init__(self, uut_file: Optional[str], output_file: Optional[str], 
                 class_name: Optional[str], module_name: Optional[str], if_name: Optional[str],
                 package: Optional[str], uvm: bool, overwrite: bool):
        self.uut_file = Path(uut_file) if uut_file else None
        self.output_file = Path(output_file) if output_file else None
        self.class_name = class_name
        self.module_name = module_name
        self.if_name = if_name
        self.package = package
        self.uvm = uvm
        self.overwrite = overwrite
        
        self.uut_name = None
        self.uut_type = None # 'class', 'module', 'interface'
        self.includes_already_printed = False

    def run(self):
        if not self._validate_args():
            return 1

        if not self._open_files():
            return 1

        self._process_file()
        
        return 0

    def _validate_args(self) -> bool:
        if not any([self.uut_file, self.class_name, self.module_name, self.if_name]):
            print("ERROR: The testfile was either not specified, does not exist or is not readable")
            return False

        if self.class_name:
            default_out = f"{self.class_name}_unit_test.sv"
        elif self.module_name:
            default_out = f"{self.module_name}_unit_test.sv"
        elif self.if_name:
            default_out = f"{self.if_name}_unit_test.sv"
        elif self.uut_file:
            default_out = f"{self.uut_file.stem}_unit_test.sv"
        else:
            return False

        if not self.output_file:
            self.output_file = Path(default_out)
        
        if not str(self.output_file).endswith("_unit_test.sv"):
             print(f"ERROR: The output_file '{self.output_file}' must end in '_unit_test.sv'")
             return False

        return True

    def _open_files(self) -> bool:
        if self.output_file.exists() and not self.overwrite:
            print(f"ERROR: The output file '{self.output_file}' already exists, to overwrite, use the -overwrite argument")
            return False
        return True

    def _process_file(self):
        if self.uut_file:
            try:
                with open(self.uut_file, 'r') as f:
                    content = f.read()
            except FileNotFoundError:
                print(f"Cannot Open file {self.uut_file}")
                return

            # Remove comments
            content = re.sub(r'//.*', '', content)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            # Simple parsing logic similar to Perl script
            # It seems the Perl script processes line by line but handles multi-line comments statefully.
            # Here we removed comments globally, so we can just search for patterns.
            
            # Regex patterns
            class_pattern = re.compile(r'^\s*class\s+(?:virtual\s+)?(\w+)', re.MULTILINE)
            module_pattern = re.compile(r'^\s*module\s+(?:automatic\s+|static\s+)?(\w+)', re.MULTILINE)
            interface_pattern = re.compile(r'^\s*interface\s+(?:automatic\s+|static\s+)?(\w+)', re.MULTILINE)

            # We need to handle multiple definitions in one file?
            # The Perl script seems to iterate and call CreateUnitTest for each endclass/endmodule/endinterface
            # But it also sets $uut based on the start.
            
            # Let's iterate lines to mimic the flow if we want to support multiple units in one file
            # Or we can just find all matches.
            
            # Re-reading line by line to match Perl logic more closely for multiple units
            lines = content.splitlines()
            
            current_uut = None
            current_type = None
            
            with open(self.output_file, 'w') as out:
                self.out_handle = out
                
                for line in lines:
                    # Check for start
                    m_class = class_pattern.search(line)
                    m_module = module_pattern.search(line)
                    m_if = interface_pattern.search(line)
                    
                    if m_class:
                        current_uut = m_class.group(1)
                        current_type = 'class'
                    elif m_module:
                        current_uut = m_module.group(1)
                        current_type = 'module'
                    elif m_if:
                        current_uut = m_if.group(1)
                        current_type = 'interface'
                    
                    # Check for end
                    if current_type == 'class' and re.search(r'^\s*endclass', line):
                        self._create_unit_test(current_uut, current_type)
                        current_uut = None
                        current_type = None
                    elif current_type == 'module' and re.search(r'^\s*endmodule', line):
                        self._create_unit_test(current_uut, current_type)
                        current_uut = None
                        current_type = None
                    elif current_type == 'interface' and re.search(r'^\s*endinterface', line):
                        self._create_unit_test(current_uut, current_type)
                        current_uut = None
                        current_type = None

        # If command line arguments specified the name directly
        if self.class_name:
            with open(self.output_file, 'w') as out:
                self.out_handle = out
                self._create_unit_test(self.class_name, 'class')
        elif self.module_name:
            with open(self.output_file, 'w') as out:
                self.out_handle = out
                self._create_unit_test(self.module_name, 'module')
        elif self.if_name:
            with open(self.output_file, 'w') as out:
                self.out_handle = out
                self._create_unit_test(self.if_name, 'interface')

    def _create_unit_test(self, uut_name: str, uut_type: str):
        uvm_class_name = f"{uut_name}_uvm_wrapper"
        
        if not self.includes_already_printed:
            self.out_handle.write('`include "svunit_defines.svh"\n')
            if self.uvm:
                self.out_handle.write('import uvm_pkg::*;\n')
            
            if self.package:
                self.out_handle.write(f'  import {self.package};\n')
            elif self.uut_file:
                self.out_handle.write(f'`include "{self.uut_file.name}"\n')
            
            self.includes_already_printed = True

        if self.uvm:
            self.out_handle.write('  import svunit_uvm_mock_pkg::*;\n')
        
        self.out_handle.write('\n')
        
        if self.uvm:
            self._create_uvm_class_for_test(uvm_class_name, uut_name)
            
        self.out_handle.write(f'module {uut_name}_unit_test;\n')
        self.out_handle.write('  import svunit_pkg::svunit_testcase;\n\n')
        self.out_handle.write(f'  string name = "{uut_name}_ut";\n')
        self.out_handle.write('  svunit_testcase svunit_ut;\n\n\n')
        
        self.out_handle.write('  //===================================\n')
        self.out_handle.write("  // This is the UUT that we're \n")
        self.out_handle.write('  // running the Unit Tests on\n')
        self.out_handle.write('  //===================================\n')
        
        if uut_type == 'class':
            if self.uvm:
                self.out_handle.write(f'  {uvm_class_name} my_{uut_name};\n\n\n')
            else:
                self.out_handle.write(f'  {uut_name} my_{uut_name};\n\n\n')
        else:
            if self.uvm:
                self.out_handle.write(f'  {uvm_class_name} my_{uut_name}();\n\n\n')
            else:
                self.out_handle.write(f'  {uut_name} my_{uut_name}();\n\n\n')

        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  // Build\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  function void build();\n')
        self.out_handle.write('    svunit_ut = new(name);\n')
        
        if uut_type == 'class':
            self.out_handle.write('\n')
            if self.uvm:
                self.out_handle.write(f'    my_{uut_name} = {uvm_class_name}::type_id::create("", null);\n')
                self.out_handle.write(f'\n    svunit_deactivate_uvm_component(my_{uut_name});\n')
            else:
                self.out_handle.write(f'    my_{uut_name} = new(/* New arguments if needed */);\n')
        
        self.out_handle.write('  endfunction\n\n\n')
        
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  // Setup for running the Unit Tests\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  task setup();\n')
        self.out_handle.write('    svunit_ut.setup();\n')
        self.out_handle.write('    /* Place Setup Code Here */\n\n')
        
        if self.uvm:
            self.out_handle.write(f'    svunit_activate_uvm_component(my_{uut_name});\n\n')
            self.out_handle.write('    //-----------------------------\n')
            self.out_handle.write('    // start the testing phase\n')
            self.out_handle.write('    //-----------------------------\n')
            self.out_handle.write('    svunit_uvm_test_start();\n\n\n\n')
            
        self.out_handle.write('  endtask\n\n\n')
        
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  // Here we deconstruct anything we \n')
        self.out_handle.write('  // need after running the Unit Tests\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  task teardown();\n')
        self.out_handle.write('    svunit_ut.teardown();\n')
        
        if self.uvm:
            self.out_handle.write('    //-----------------------------\n')
            self.out_handle.write('    // terminate the testing phase \n')
            self.out_handle.write('    //-----------------------------\n')
            self.out_handle.write('    svunit_uvm_test_finish();\n\n')
        
        self.out_handle.write('    /* Place Teardown Code Here */\n\n')
        
        if self.uvm:
            self.out_handle.write(f'    svunit_deactivate_uvm_component(my_{uut_name});\n')
            
        self.out_handle.write('  endtask\n\n\n')
        
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  // All tests are defined between the\n')
        self.out_handle.write('  // SVUNIT_TESTS_BEGIN/END macros\n')
        self.out_handle.write('  //\n')
        self.out_handle.write('  // Each individual test must be\n')
        self.out_handle.write('  // defined between `SVTEST(_NAME_)\n')
        self.out_handle.write('  // `SVTEST_END\n')
        self.out_handle.write('  //\n')
        self.out_handle.write('  // i.e.\n')
        self.out_handle.write('  //   `SVTEST(mytest)\n')
        self.out_handle.write('  //     <test code>\n')
        self.out_handle.write('  //   `SVTEST_END\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  `SVUNIT_TESTS_BEGIN\n\n\n\n')
        self.out_handle.write('  `SVUNIT_TESTS_END\n\n')
        self.out_handle.write('endmodule\n')

    def _create_uvm_class_for_test(self, uvm_class_name: str, uut_name: str):
        self.out_handle.write(f'class {uvm_class_name} extends {uut_name};\n\n')
        self.out_handle.write(f'  `uvm_component_utils({uvm_class_name})\n')
        self.out_handle.write(f'  function new(string name = "{uvm_class_name}", uvm_component parent);\n')
        self.out_handle.write('    super.new(name, parent);\n')
        self.out_handle.write('  endfunction\n\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  // Build\n')
        self.out_handle.write('  //===================================\n')
        self.out_handle.write('  function void build_phase(uvm_phase phase);\n')
        self.out_handle.write('     super.build_phase(phase);\n')
        self.out_handle.write('    /* Place Build Code Here */\n')
        self.out_handle.write('  endfunction\n\n')
        self.out_handle.write('  //==================================\n')
        self.out_handle.write('  // Connect\n')
        self.out_handle.write('  //=================================\n')
        self.out_handle.write('  function void connect_phase(uvm_phase phase);\n')
        self.out_handle.write('    super.connect_phase(phase);\n')
        self.out_handle.write('    /* Place Connection Code Here */\n')
        self.out_handle.write('  endfunction\n')
        self.out_handle.write('endclass\n\n')
